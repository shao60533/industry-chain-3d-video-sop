"""Check the installed toolchain; an environment check is not film acceptance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import sys
import tempfile

from runtime import ROOT, config, find_tool, run, safe_message, version

BLENDER_SMOKE = '''import bpy, sys
from pathlib import Path
root = Path(sys.argv[sys.argv.index("--") + 1])
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 1
scene.render.resolution_x = 64
scene.render.resolution_y = 64
scene.render.resolution_percentage = 100
scene.render.filepath = str(root / "frame.png")
scene.render.image_settings.file_format = "PNG"
bpy.ops.wm.save_as_mainfile(filepath=str(root / "smoke.blend"))
bpy.ops.render.render(write_still=True)
'''


def smoke_test(tools: dict[str, str]) -> dict:
    with tempfile.TemporaryDirectory(prefix="industry-video-smoke-") as temporary:
        directory = Path(temporary)
        script = directory / "smoke.py"
        script.write_text(BLENDER_SMOKE, encoding="utf-8")
        run([tools["blender"], "--background", "--factory-startup", "--disable-autoexec",
             "--python-exit-code", "1", "--python", str(script), "--", str(directory)], timeout=120)
        if not (directory / "frame.png").is_file() or not (directory / "smoke.blend").is_file():
            raise RuntimeError("Blender 未产生实际渲染和可编辑工程")
        run([tools["blender"], "--background", "--disable-autoexec", str(directory / "smoke.blend"),
             "--python-exit-code", "1", "--python-expr",
             "import bpy; assert bpy.context.scene.render.resolution_x == 64"], timeout=60)
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
                "full_decode": True, "frames": 24, "gpu": "not_tested"}


def inspect_environment(smoke: bool = False) -> dict:
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
            output = run([path, "--version" if name == "blender" else "-version"], timeout=30)
            parsed = version(output)
            if name == "blender" and parsed < (3, 6, 0):
                raise RuntimeError("Blender 需要 3.6 或更新版本，建议维护中的 LTS")
            tools[name] = path
            checks[name] = {"passed": True, "version": ".".join(map(str, parsed))}
        except RuntimeError as exc:
            checks[name] = {"passed": False, "reason": safe_message(str(exc))}
    try:
        from PIL import Image, ImageDraw, ImageFont, __version__
        font_path = saved.get("font") or str(ROOT / ".local/fonts/NotoSansCJKsc-Regular.otf")
        font = ImageFont.truetype(font_path, 42)
        image = Image.new("RGB", (400, 100))
        box = ImageDraw.Draw(image).textbbox((0, 0), "产业链 3D", font=font)
        if box[2] <= box[0] or box[3] <= box[1]:
            raise RuntimeError("中文字体没有产生字形墨迹")
        checks["pillow_font"] = {"passed": True, "pillow": __version__, "ink_measured": True}
    except (ImportError, OSError, RuntimeError):
        checks["pillow_font"] = {"passed": False, "reason": "缺少 Pillow 或可加载的中文字体"}
    if smoke:
        try:
            if len(tools) != 3:
                raise RuntimeError("工具未就绪，跳过渲染/编码测试")
            checks["smoke"] = {"passed": True, **smoke_test(tools)}
        except (RuntimeError, OSError, ValueError, KeyError, StopIteration) as exc:
            checks["smoke"] = {"passed": False, "reason": safe_message(str(exc))}
    report["ready"] = all(item["passed"] for item in checks.values())
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-test", action="store_true", help="实际 CPU 渲染、重开工程并编码/解码")
    parser.add_argument("--out", type=Path, help="可选：保存不含私人路径的自检摘要")
    args = parser.parse_args()
    try:
        report = inspect_environment(args.smoke_test)
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
