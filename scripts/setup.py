"""Install a self-contained Codex skill and validate its local dependencies."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile

from runtime import BLENDER_STARTUP_TIMEOUT, PILLOW_VERSION, ROOT, SKILL_NAME, find_tool, python_in, run, safe_message, version

PAYLOAD = ("SKILL.md", "agents", "docs", "profiles", "templates", "scripts", "tests", "assets",
           "requirements.txt", "LICENSE", "README.md", "AGENTS.md", "SECURITY.md",
           "CONTRIBUTING.md", "CHANGELOG.md", "install.sh", "install.ps1", ".gitignore")
FONT_COMMIT = "f8d157532fbfaeda587e826d4cd5b21a49186f7c"
FONT_URL = f"https://raw.githubusercontent.com/notofonts/noto-cjk/{FONT_COMMIT}/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"
FONT_SHA = "2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b"
BLENDER_VERSION = "4.5.14"
BLENDER_HASHES = {
    "linux-x64.tar.xz": "9ba871ff2ecd36526b77432745980b7e6664ecd0c7ca11c48849073dcfe06da3",
    "windows-x64.zip": "b9533d2397ac1984db4466fb23a7a4649391cca93f6e84209f9bcc60d071c8b9",
    "windows-arm64.zip": "0153ecefc96a0e23985e6edcdbe04e909ba2078258f4ff6a05c21d4b7c756911",
}


def default_destination() -> Path:
    base = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()
    return base / "skills" / SKILL_NAME


def guard_destination(source: Path, destination: Path) -> None:
    if destination.is_symlink():
        raise RuntimeError("技能目标不能是符号链接")
    destination = destination.resolve()
    forbidden = {Path.home().resolve(), Path.home().resolve() / ".codex", Path(destination.anchor)}
    if destination in forbidden or (destination != source and destination in source.parents):
        raise RuntimeError("请指定独立技能目录，不能覆盖用户目录或源码父目录")
    if destination == source:
        return
    if destination.exists():
        marker = destination / ".skill-installation.json"
        if not marker.is_file() or marker.is_symlink():
            raise RuntimeError("目标已存在且不是本安装器管理的技能；请使用独立 --dest 目录")
        if json.loads(marker.read_text(encoding="utf-8")).get("skill") != SKILL_NAME:
            raise RuntimeError("目标目录属于其他技能")


def copy_payload(source: Path, destination: Path) -> list[str]:
    guard_destination(source, destination)
    files: list[Path] = []
    for name in PAYLOAD:
        item = source / name
        if not item.exists():
            raise RuntimeError(f"安装包缺少 {name}")
        files += [item] if item.is_file() else [p for p in item.rglob("*") if p.is_file()]
    managed = []
    for item in files:
        relative = item.relative_to(source)
        if "__pycache__" in relative.parts or item.name == ".DS_Store":
            continue
        if item.is_symlink() or any(p.is_symlink() for p in item.parents if p != source and source in p.parents):
            raise RuntimeError("安装资源中发现符号链接，停止复制")
        target = destination / relative
        if target.is_symlink() or any(p.is_symlink() for p in target.parents if p == destination or destination in p.parents):
            raise RuntimeError("目标资源中发现符号链接，停止覆盖")
        managed.append(relative.as_posix())
    # Validate every path before writing any payload file.
    if destination != source:
        destination.mkdir(parents=True, exist_ok=True)
        for relative in managed:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / relative, target)
    return managed


def download(url: str, output: Path, checksum: str | None = None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    part = output.with_name(output.name + ".part")
    try:
        run(["curl", "--fail", "--location", "--proto", "=https", "--tlsv1.2", "--retry", "2",
             "--connect-timeout", "20", "--max-time", "900", "--output", str(part), url], timeout=920)
        if checksum:
            with part.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual != checksum:
                raise RuntimeError("下载文件 SHA256 不匹配，停止安装")
        part.replace(output)
    finally:
        part.unlink(missing_ok=True)


def extract_archive(archive: Path, destination: Path) -> None:
    """Reject traversal and links before extracting downloaded application files."""
    base = destination.resolve()
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as bundle:
            for item in bundle.infolist():
                path = (base / item.filename).resolve()
                if not path.is_relative_to(base) or (item.external_attr >> 16) & 0o170000 == 0o120000:
                    raise RuntimeError("压缩包包含不安全路径或链接")
            bundle.extractall(base)
    else:
        with tarfile.open(archive) as bundle:
            for item in bundle.getmembers():
                path = (base / item.name).resolve()
                if not path.is_relative_to(base) or item.isdev() or item.isfifo():
                    raise RuntimeError("压缩包包含不安全路径或设备")
                if item.issym() or item.islnk():
                    target = ((path.parent if item.issym() else base) / item.linkname).resolve()
                    if not target.is_relative_to(base):
                        raise RuntimeError("压缩包链接指向目标目录之外")
            if hasattr(tarfile, "data_filter"):
                bundle.extractall(base, filter="data")
            else:
                bundle.extractall(base)


def apt_prefix() -> list[str]:
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return []
    if shutil.which("sudo") is None:
        raise RuntimeError("缺少管理员权限：请由系统管理员安装依赖或配置已有工具")
    check = subprocess.run(["sudo", "-n", "true"], capture_output=True)
    if check.returncode:
        try:
            with open("/dev/tty", "r+") as terminal:
                check = subprocess.run(["sudo", "-v"], stdin=terminal, stdout=terminal, stderr=terminal)
        except OSError as exc:
            raise RuntimeError("系统依赖需要管理员权限：请先在终端运行 sudo -v，或使用 --skip-system-deps") from exc
        if check.returncode:
            raise RuntimeError("未获得系统依赖安装权限")
    return ["sudo", "-n"]


def install_system_tools(destination: Path, missing: list[str]) -> dict[str, str]:
    system = platform.system()
    extra: dict[str, str] = {}
    if system == "Darwin":
        brew = shutil.which("brew") or next((str(p) for p in (Path("/opt/homebrew/bin/brew"), Path("/usr/local/bin/brew")) if p.is_file()), None)
        if brew is None:
            print("准备官方 Homebrew 安装工具", flush=True)
            with tempfile.TemporaryDirectory(prefix="homebrew-setup-") as temporary:
                script = Path(temporary) / "install.sh"
                download("https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh", script)
                run(["env", "NONINTERACTIVE=1", "/bin/bash", str(script)], timeout=1800)
            brew = next((str(p) for p in (Path("/opt/homebrew/bin/brew"), Path("/usr/local/bin/brew")) if p.is_file()), None)
            if brew is None:
                raise RuntimeError("Homebrew 初次安装需要系统权限；请完成官方安装后重试")
        if "blender" in missing:
            run([brew, "install", "--cask", "blender"], timeout=1800)
        if any(name in missing for name in ("ffmpeg", "ffprobe")):
            run([brew, "install", "ffmpeg"], timeout=1800)
    elif system == "Linux":
        if shutil.which("apt-get") is None:
            raise RuntimeError("自动系统安装支持 Debian/Ubuntu；其他 Linux 请配置现有 Blender/FFmpeg 后加 --skip-system-deps")
        prefix = apt_prefix()
        run(prefix + ["apt-get", "update"], timeout=900)
        packages = ["libx11-6", "libxi6", "libxrender1", "libxfixes3", "libxxf86vm1", "libsm6", "libgl1", "libegl1"]
        if any(name in missing for name in ("ffmpeg", "ffprobe")):
            packages.append("ffmpeg")
        run(prefix + ["apt-get", "install", "-y"] + packages, timeout=1800)
    elif system == "Windows":
        if any(name in missing for name in ("ffmpeg", "ffprobe")):
            winget = shutil.which("winget")
            if winget is None:
                raise RuntimeError("缺少 winget，请安装 Windows App Installer 或配置已有 FFmpeg")
            run([winget, "install", "--id", "Gyan.FFmpeg", "--exact", "--source", "winget", "--silent",
                 "--accept-package-agreements", "--accept-source-agreements", "--disable-interactivity"], timeout=1800)
    else:
        raise RuntimeError("当前系统不支持自动安装")
    if "blender" in missing and system != "Darwin":
        machine = platform.machine().lower()
        architecture = "arm64" if machine in ("arm64", "aarch64") else "x64" if machine in ("amd64", "x86_64") else "unsupported"
        key = f"{system.lower()}-{architecture}.{'zip' if system == 'Windows' else 'tar.xz'}"
        if key not in BLENDER_HASHES:
            raise RuntimeError("此架构没有内置 Blender 下载项；请先安装官方 Blender 并配置 VIDEO_SOP_BLENDER")
        tools = destination / ".local/tools"
        with tempfile.TemporaryDirectory(prefix="blender-download-") as temporary:
            archive = Path(temporary) / key
            download(f"https://download.blender.org/release/Blender4.5/blender-{BLENDER_VERSION}-{key}", archive, BLENDER_HASHES[key])
            extract_archive(archive, tools)
        binaries = sorted(tools.glob("blender*/blender.exe" if system == "Windows" else "blender*/blender"))
        if not binaries:
            raise RuntimeError("Blender 解压后缺少可执行文件")
        extra["blender"] = str(binaries[-1].resolve())
    return extra


def install(destination: Path, skip_system: bool, smoke: bool) -> dict:
    if sys.version_info < (3, 11):
        raise RuntimeError("Python 需要 3.11 或更新版本，请使用统一安装入口")
    guard_destination(ROOT, destination)
    local = destination / ".local"
    environment = destination / ".venv"
    for path in (local, environment, local / "fonts", local / "tools", local / "environment.json",
                 local / "doctor.json", destination / ".skill-installation.json"):
        if path.is_symlink():
            raise RuntimeError("本地状态或虚拟环境不能是符号链接")
    managed = copy_payload(ROOT, destination)
    local.mkdir(mode=0o700, exist_ok=True)
    marker = destination / ".skill-installation.json"
    marker.write_text(json.dumps({"skill": SKILL_NAME, "managed_files": managed}, indent=2) + "\n", encoding="utf-8")
    saved = json.loads((local / "environment.json").read_text(encoding="utf-8")) if (local / "environment.json").is_file() else {}
    tools: dict[str, str] = {}
    missing = []
    for name in ("blender", "ffmpeg", "ffprobe"):
        path = find_tool(name, saved.get("tools", {}))
        if path and (name != "blender" or version(run([path, "--version"], timeout=BLENDER_STARTUP_TIMEOUT)) >= (3, 6, 0)):
            tools[name] = path
        else:
            missing.append(name)
    if missing:
        if skip_system:
            raise RuntimeError("缺少依赖：" + ", ".join(missing))
        print("安装缺少的依赖：" + ", ".join(missing), flush=True)
        extra = install_system_tools(destination, missing)
        for name in missing:
            path = find_tool(name, extra)
            if path is None:
                raise RuntimeError(f"安装后仍未找到 {name}，请检查系统软件包")
            tools[name] = path
    font = Path(os.environ.get("VIDEO_SOP_FONT", str(local / "fonts/NotoSansCJKsc-Regular.otf"))).expanduser()
    if "VIDEO_SOP_FONT" in os.environ:
        if not font.is_file():
            raise RuntimeError("指定的本地字体不存在")
    else:
        if font.is_symlink():
            raise RuntimeError("默认字体不能是符号链接")
        if not font.is_file() or hashlib.sha256(font.read_bytes()).hexdigest() != FONT_SHA:
            print("准备中文字体（固定版本与 SHA256）", flush=True)
            download(FONT_URL, font, FONT_SHA)
        license_file = font.parent / "OFL.txt"
        if license_file.is_symlink():
            raise RuntimeError("字体许可文件不能是符号链接")
        if not license_file.is_file():
            download(f"https://raw.githubusercontent.com/notofonts/noto-cjk/{FONT_COMMIT}/Sans/LICENSE", license_file)
    python = python_in(environment)
    if not python.is_file():
        print("建立独立 Python 环境", flush=True)
        try:
            venv.EnvBuilder(with_pip=True).create(environment)
        except subprocess.CalledProcessError as exc:
            if platform.system() != "Linux" or skip_system:
                raise RuntimeError("无法建立 venv，请先安装当前 Python 对应的 venv/ensurepip") from exc
            run(apt_prefix() + ["apt-get", "install", "-y", "python3-venv"], timeout=900)
            venv.EnvBuilder(with_pip=True).create(environment)
    try:
        installed = run([str(python), "-c", "import PIL; print(PIL.__version__)"], timeout=30).strip()
    except RuntimeError:
        installed = None
    if installed != PILLOW_VERSION:
        print("安装 Python 依赖", flush=True)
        run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(destination / "requirements.txt")], timeout=900)
    data = {"schema": "industry-video-local-environment-1", "tools": tools, "font": str(font.resolve())}
    (local / "environment.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    args = [str(python), str(destination / "scripts/doctor.py"), "--out", str(local / "doctor.json")]
    if smoke:
        args.append("--smoke-test")
    print("验证制作环境" + ("、实际渲染与编码" if smoke else ""), flush=True)
    report_file = local / "doctor.json"
    report_file.unlink(missing_ok=True)
    try:
        result = json.loads(run(args, timeout=600))
    except RuntimeError:
        if report_file.is_file():
            failed = json.loads(report_file.read_text(encoding="utf-8"))
            for name, item in failed.get("checks", {}).items():
                if not item.get("passed"):
                    print(safe_message(f"{name}: {item.get('reason', '未通过')}"))
        raise
    if not result["ready"]:
        raise RuntimeError("环境自检未通过；查看本地 .local/doctor.json 的未就绪项目")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=default_destination())
    parser.add_argument("--skip-system-deps", action="store_true", help="只复用现有 Blender/FFmpeg，不修改系统软件")
    parser.add_argument("--no-smoke", action="store_true", help="仅检查依赖，不执行渲染和编码")
    parser.add_argument("--dry-run", action="store_true", help="仅显示计划，不安装或写文件")
    args = parser.parse_args()
    destination = args.dest.expanduser().absolute()
    try:
        guard_destination(ROOT, destination)
        destination = destination.resolve()
        if args.dry_run:
            guard_destination(ROOT, destination)
            print(json.dumps({"skill": SKILL_NAME, "platform": platform.system(), "python": "3.11+",
                              "dependencies": ["Blender", "FFmpeg/ffprobe", f"Pillow {PILLOW_VERSION}", "Noto Sans CJK SC"],
                              "modify_system": not args.skip_system_deps, "smoke_test": not args.no_smoke}, ensure_ascii=False, indent=2))
            return 0
        report = install(destination, args.skip_system_deps, not args.no_smoke)
    except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError, zipfile.BadZipFile, tarfile.TarError) as exc:
        print("安装未完成：" + safe_message(str(exc)))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("技能已安装。下一个 Codex 回合可使用 $industry-chain-3d-video。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
