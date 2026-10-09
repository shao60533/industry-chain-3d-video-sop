"""Check the installed toolchain; an environment check is not film acceptance."""

from __future__ import annotations

import argparse
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import tempfile

from runtime import BLENDER_STARTUP_TIMEOUT, ROOT, config, find_tool, run, safe_message, version

BLENDER_SMOKE = '''import bpy, sys
from pathlib import Path
root = Path(sys.argv[sys.argv.index("--") + 1])
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 1
# This probe verifies a raw CPU render, not optional denoising support.
scene.cycles.use_denoising = False
scene.render.resolution_x = 64
scene.render.resolution_y = 64
scene.render.resolution_percentage = 100
scene.render.filepath = str(root / "frame.png")
scene.render.image_settings.file_format = "PNG"
bpy.ops.wm.save_as_mainfile(filepath=str(root / "smoke.blend"))
bpy.ops.render.render(write_still=True)
'''


FONT_SAMPLE = "产业链 3D · 中文数字 123.45 亿元 / 24 帧"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check_font(path: Path, index: int = 0, output: Path | None = None) -> dict:
    from PIL import Image, ImageChops, ImageDraw, ImageFont, __version__
    if not path.is_file() or isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise RuntimeError("中文字体文件或字体集合索引无效")
    font = ImageFont.truetype(str(path), 42, index=index)
    missing = font.getmask("\U0010ffff", mode="L")
    missing_signature = (missing.size, bytes(missing))
    chinese = sorted({char for char in FONT_SAMPLE if "\u4e00" <= char <= "\u9fff"})
    for char in chinese:
        mask = font.getmask(char, mode="L")
        if not any(bytes(mask)) or (mask.size, bytes(mask)) == missing_signature:
            raise RuntimeError("中文字体缺少实际字形，不能用缺字方框通过")
    box = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), FONT_SAMPLE, font=font)
    image = Image.new("RGB", (max(1, box[2] - box[0]) + 24, max(1, box[3] - box[1]) + 24), "white")
    ImageDraw.Draw(image).text((12 - box[0], 12 - box[1]), FONT_SAMPLE, font=font, fill="black")
    ink = ImageChops.invert(image.convert("L"))
    ink_box = ink.getbbox()
    if ink_box is None:
        raise RuntimeError("实际像素没有产生中文墨迹")
    result = {"passed": True, "pillow": __version__, "ink_measured": True,
              "font_sha256": digest(path), "font_index": index, "sample": FONT_SAMPLE,
              "cjk_glyphs_checked": len(chinese), "ink_bbox": list(ink_box),
              "ink_pixels": sum(ink.histogram()[1:]),
              "pixels_sha256": hashlib.sha256(image.tobytes()).hexdigest()}
    if output is not None:
        image.save(output, format="PNG")
        result["png_sha256"] = digest(output)
    return result


def check_render_frame(path: Path) -> dict:
    from PIL import Image
    with Image.open(path) as original:
        original.load()
        if original.format != "PNG" or original.size != (64, 64):
            raise RuntimeError("CPU渲染未产生预期64×64 PNG")
        if "A" in original.getbands() and original.getchannel("A").getextrema()[1] == 0:
            raise RuntimeError("CPU渲染实际像素全透明")
        image = original.convert("RGB")
    if not any(low != high for low, high in image.getextrema()):
        raise RuntimeError("CPU渲染实际像素为单色，未形成场景")
    return {"size": list(image.size), "nonuniform_pixels": True,
            "png_sha256": digest(path), "pixels_sha256": hashlib.sha256(image.tobytes()).hexdigest()}


def smoke_test(tools: dict[str, str], artifacts_dir: Path | None = None) -> dict:
    context = nullcontext(artifacts_dir) if artifacts_dir is not None else tempfile.TemporaryDirectory(prefix="industry-video-smoke-")
    with context as temporary:
        directory = Path(temporary).resolve()
        if any((directory / name).exists() for name in ("smoke.py", "frame.png", "smoke.blend", "smoke.mp4")):
            raise RuntimeError("自检产物已存在，不覆盖已有证据")
        script = directory / "smoke.py"
        script.write_text(BLENDER_SMOKE, encoding="utf-8")
        run([tools["blender"], "--background", "--factory-startup", "--disable-autoexec",
             "--python-exit-code", "1", "--python", str(script), "--", str(directory)], timeout=120)
        if not (directory / "frame.png").is_file() or not (directory / "smoke.blend").is_file():
            raise RuntimeError("Blender 未产生实际渲染和可编辑工程")
        pixels = check_render_frame(directory / "frame.png")
        run([tools["blender"], "--background", "--disable-autoexec", str(directory / "smoke.blend"),
             "--python-exit-code", "1", "--python-expr",
             "import bpy; s = bpy.context.scene; assert s.render.resolution_x == 64 and "
             "s.render.engine == 'CYCLES' and s.cycles.device == 'CPU' and not s.cycles.use_denoising"], timeout=60)
        movie = directory / "smoke.mp4"
        run([tools["ffmpeg"], "-v", "error", "-y", "-loop", "1", "-framerate", "24",
             "-i", str(directory / "frame.png"), "-f", "lavfi", "-i",
             "sine=frequency=440:sample_rate=48000:duration=1", "-t", "1",
             "-vf", "scale=in_range=pc:out_range=tv:out_color_matrix=bt709",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
             "-x264-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709:fullrange=off",
             "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709",
             "-color_trc", "bt709", str(movie)], timeout=60)
        probe = json.loads(run([tools["ffprobe"], "-v", "error", "-show_streams",
                               "-of", "json", str(movie)], timeout=30))
        video = next(item for item in probe["streams"] if item["codec_type"] == "video")
        audio = next(item for item in probe["streams"] if item["codec_type"] == "audio")
        expected = {"codec_name": "h264", "pix_fmt": "yuv420p", "color_range": "tv",
                    "color_space": "bt709", "color_transfer": "bt709", "color_primaries": "bt709"}
        if any(video.get(key) != value for key, value in expected.items()) or audio["codec_name"] != "aac":
            raise RuntimeError("H.264/AAC 或色彩编码自检失败")
        if int(video.get("nb_frames", 0)) != 24:
            raise RuntimeError("编码自检实际帧数不符合预期")
        run([tools["ffmpeg"], "-v", "error", "-i", str(movie), "-f", "null", "-"], timeout=30)
        return {"blender_cpu_render": True, "blend_reopened": True, "h264_aac_encode": True,
                "full_decode": True, "frames": 24, "gpu": "not_tested",
                "denoising": "disabled_for_minimal_cpu_probe", "render_pixels": pixels,
                "blend_sha256": digest(directory / "smoke.blend"), "movie_sha256": digest(movie)}


def inspect_environment(smoke: bool = False, artifacts_dir: Path | None = None) -> dict:
    if artifacts_dir is not None:
        if artifacts_dir.exists() or artifacts_dir.is_symlink():
            raise RuntimeError("自检证据目录已存在，请指定新目录")
        artifacts_dir.mkdir(parents=True, exist_ok=False)
    report = {"schema": "industry-video-doctor-1", "platform": platform.system(),
              "python": platform.python_version(), "checks": {}, "ready": False,
              "film_acceptance": "pending"}
    checks = report["checks"]
    checks["python"] = {"passed": sys.version_info >= (3, 11)}
    saved = config()
    tools: dict[str, str] = {}
    for name in ("blender", "ffmpeg", "ffprobe"):
        try:
            path = find_tool(name, saved.get("tools", {}))
            if path is None:
                raise RuntimeError(f"缺少 {name}")
            timeout = BLENDER_STARTUP_TIMEOUT if name == "blender" else 30
            output = run([path, "--version" if name == "blender" else "-version"], timeout=timeout)
            parsed = version(output)
            if name == "blender" and parsed < (3, 6, 0):
                raise RuntimeError("Blender 需要 3.6 或更新版本，建议维护中的 LTS")
            tools[name] = path
            checks[name] = {"passed": True, "version": ".".join(map(str, parsed))}
        except RuntimeError as exc:
            checks[name] = {"passed": False, "reason": safe_message(str(exc))}
    try:
        font_path = Path(os.environ.get("VIDEO_SOP_FONT", saved.get("font") or str(ROOT / ".local/fonts/NotoSansCJKsc-Regular.otf"))).expanduser()
        index = int(os.environ["VIDEO_SOP_FONT_INDEX"]) if "VIDEO_SOP_FONT_INDEX" in os.environ else saved.get("font_index", 0)
        checks["pillow_font"] = check_font(font_path, index, artifacts_dir / "font.png" if artifacts_dir else None)
    except ImportError:
        checks["pillow_font"] = {"passed": False, "reason": "缺少 Pillow"}
    except (OSError, ValueError, TypeError):
        checks["pillow_font"] = {"passed": False, "reason": "中文字体文件或集合索引无法加载"}
    except RuntimeError as exc:
        checks["pillow_font"] = {"passed": False, "reason": safe_message(str(exc))}
    if smoke:
        try:
            if len(tools) != 3:
                raise RuntimeError("工具未就绪，跳过渲染/编码测试")
            checks["smoke"] = {"passed": True, **smoke_test(tools, artifacts_dir)}
        except ImportError:
            checks["smoke"] = {"passed": False, "reason": "缺少 Pillow，无法核验实际渲染像素"}
        except (RuntimeError, OSError, ValueError, KeyError, StopIteration) as exc:
            checks["smoke"] = {"passed": False, "reason": safe_message(str(exc))}
    report["ready"] = all(item["passed"] for item in checks.values())
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-test", action="store_true", help="实际 CPU 渲染、重开工程并编码/解码")
    parser.add_argument("--out", type=Path, help="可选：保存不含私人路径的自检摘要")
    parser.add_argument("--artifacts-dir", type=Path, help="保留字形PNG、CPU帧、工程和编码；拒绝覆盖已有目录")
    args = parser.parse_args()
    try:
        report = inspect_environment(args.smoke_test, args.artifacts_dir)
    except (OSError, ValueError, RuntimeError) as exc:
        print(safe_message(str(exc)))
        return 1
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
