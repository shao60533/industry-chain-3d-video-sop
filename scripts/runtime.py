"""Local tool discovery and bounded process execution; never log credentials."""

from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
SKILL_NAME = "industry-chain-3d-video"
PILLOW_VERSION = "12.3.0"
BLENDER_STARTUP_TIMEOUT = 120


def safe_message(value: str) -> str:
    """Keep local paths and typical credentials out of console diagnostics."""
    value = value.replace(str(Path.home()), "<home>")
    value = re.sub(r"(?:gh[pousr]_|github_pat_|sk-)[A-Za-z0-9_-]{12,}", "<redacted>", value)
    value = re.sub(r"(?i)(https?://)[^\s/@]+:[^\s/@]+@", r"\1<redacted>@", value)
    return value


def run(args: list[str], timeout: int = 180) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"{Path(args[0]).name} 无法运行或超时") from exc
    if result.returncode:
        # Third-party logs can contain paths, URLs and environment values.
        # Keep them off stdout and public reports rather than guessing at redaction.
        raise RuntimeError(f"{Path(args[0]).name} 执行失败（退出 {result.returncode}）")
    return result.stdout


def config() -> dict:
    path = ROOT / ".local/environment.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "industry-video-local-environment-1":
        raise RuntimeError("本地环境配置版本不支持，请重新运行安装器")
    return data


def find_tool(name: str, saved: dict | None = None) -> str | None:
    override = os.environ.get(f"VIDEO_SOP_{name.upper()}")
    if override:
        path = Path(override).expanduser()
        if not path.is_file():
            raise RuntimeError(f"VIDEO_SOP_{name.upper()} 指定的文件不存在")
        return str(path.resolve())
    candidates: list[Path] = []
    if saved and saved.get(name):
        candidates.append(Path(saved[name]))
    if name == "blender":
        # Prefer the real binary to GUI command wrappers, particularly on macOS.
        candidates += [
            Path("/Applications/Blender.app/Contents/MacOS/Blender"),
            Path.home() / "Applications/Blender.app/Contents/MacOS/Blender",
        ]
        if platform.system() == "Windows":
            for variable in ("ProgramFiles", "LOCALAPPDATA"):
                base = Path(os.environ.get(variable, ""))
                if str(base) != ".":
                    candidates += sorted(base.glob("Blender Foundation/Blender */blender.exe"), reverse=True)
        executable = "blender.exe" if platform.system() == "Windows" else "blender"
        candidates += sorted((ROOT / ".local/tools").glob(f"blender*/{executable}"))
    found = shutil.which(name)
    if found:
        candidates.append(Path(found))
    if platform.system() != "Windows" and name in ("ffmpeg", "ffprobe"):
        candidates += [Path(prefix) / name for prefix in ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin")]
    if platform.system() == "Windows" and name in ("ffmpeg", "ffprobe"):
        base = Path(os.environ.get("LOCALAPPDATA", ""))
        candidates += list(base.glob(f"Microsoft/WinGet/Packages/Gyan.FFmpeg_*/**/{name}.exe"))
    for path in candidates:
        if path.is_file() and (platform.system() == "Windows" or os.access(path, os.X_OK)):
            return str(path.resolve())
    return None


def version(text: str) -> tuple[int, ...]:
    match = re.search(r"\b(\d+)\.(\d+)(?:\.(\d+))?", text)
    if not match:
        raise RuntimeError("无法识别工具版本")
    return tuple(int(part) for part in match.groups(default="0"))


def python_in(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")
