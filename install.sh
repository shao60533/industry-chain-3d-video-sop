#!/usr/bin/env bash
# macOS / Debian / Ubuntu bootstrap; installs no credentials or account state.
# macOS needs no Homebrew and no administrator password.
set -euo pipefail

sop_ref="${VIDEO_SOP_REF:-main}"
sop_tmp=""
cleanup() { if [[ -n "$sop_tmp" ]]; then rm -rf "$sop_tmp"; fi; }
trap cleanup EXIT
fail() { printf '%s\n' "$1" >&2; exit 1; }

[[ "$sop_ref" =~ ^[A-Za-z0-9._-]+$ ]] || fail "版本必须为分支名、标签或提交 SHA。"
sop_skip=0
sop_bundle=()
for sop_arg in "$@"; do
  case "$sop_arg" in --skip-system-deps|--dry-run) sop_skip=1 ;; esac
done

find_python() {
  local candidate
  for candidate in "${VIDEO_SOP_PYTHON:-}" python3 /opt/homebrew/bin/python3 /usr/local/bin/python3 \
      "${CODEX_HOME:-$HOME/.codex}/skills/industry-chain-3d-video/.local/tools/python/bin/python3"; do
    if [[ -n "$candidate" ]] && command -v "$candidate" >/dev/null 2>&1; then
      # Without Command Line Tools, /usr/bin/python3 only opens an install dialog.
      if [[ "$(uname -s)" == Darwin && "$(command -v "$candidate")" == /usr/bin/python3 ]] && ! /usr/bin/xcode-select -p >/dev/null 2>&1; then
        continue
      fi
      if "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' >/dev/null 2>&1; then
        sop_python="$(command -v "$candidate")"
        return 0
      fi
    fi
  done
  return 1
}

sop_source=""
if [[ -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]]; then
  sop_candidate="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -f "$sop_candidate/SKILL.md" && -f "$sop_candidate/scripts/setup.py" ]]; then
    sop_source="$sop_candidate"
  fi
fi

if ! find_python || ! command -v curl >/dev/null 2>&1; then
  [[ "$sop_skip" == 0 ]] || fail "请先提供 Python 3.11+ 和 curl；当前选项不修改系统。"
  case "$(uname -s)" in
    Darwin)
      # A self-contained Python from a pinned release: no Homebrew, no administrator password.
      case "$(uname -m)" in
        arm64) sop_py_arch=aarch64; sop_py_sha=1afd3983237c2a10277345f235be730e9cb49a123e0574ed252dbf3a841a24e4 ;;
        x86_64) sop_py_arch=x86_64; sop_py_sha=a46bcdeecd28ba253522b321dcb3806da1b0ff581479fc1d27e9613e3ac44764 ;;
        *) fail "不支持的 Mac 处理器架构。" ;;
      esac
      sop_tmp="$(mktemp -d)"
      sop_py_archive="$sop_tmp/python.tar.gz"
      printf '%s\n' "下载独立 Python（固定版本并核对 SHA256，不需要管理员密码）"
      curl --fail --location --proto '=https' --tlsv1.2 --retry 2 --connect-timeout 20 --max-time 900 \
        "https://github.com/astral-sh/python-build-standalone/releases/download/20261110/cpython-3.13.18%2B20261110-${sop_py_arch}-apple-darwin-install_only.tar.gz" \
        -o "$sop_py_archive"
      [[ "$(/usr/bin/shasum -a 256 "$sop_py_archive" | awk '{print $1}')" == "$sop_py_sha" ]] || fail "Python 下载文件 SHA256 不匹配，停止安装。"
      mkdir "$sop_tmp/bootstrap"
      tar -xzf "$sop_py_archive" -C "$sop_tmp/bootstrap"
      sop_python="$sop_tmp/bootstrap/python/bin/python3"
      [[ -x "$sop_python" ]] || fail "独立 Python 解压后无法使用。"
      sop_bundle=(--python-archive "$sop_py_archive")
      ;;
    Linux)
      command -v apt-get >/dev/null 2>&1 || fail "其他 Linux 请先安装 Python 3.11+、curl 和 venv。"
      sop_sudo=()
      if [[ "$(id -u)" != 0 ]]; then
        command -v sudo >/dev/null 2>&1 || fail "缺少系统依赖安装权限。"
        if ! sudo -n true 2>/dev/null; then
          if [[ -r /dev/tty ]]; then sudo -v </dev/tty; else fail "请先在终端运行 sudo -v。"; fi
        fi
        sop_sudo=(sudo -n)
      fi
      "${sop_sudo[@]}" apt-get update
      "${sop_sudo[@]}" apt-get install -y python3 python3-venv curl ca-certificates
      ;;
    *) fail "请在 macOS/Linux 使用本入口；Windows 使用 install.ps1。" ;;
  esac
fi
[[ ${#sop_bundle[@]} -gt 0 ]] || find_python || fail "Python 需要 3.11+；旧发行版请先升级 Python，再重新安装。"

if [[ -z "$sop_source" ]]; then
  if [[ -z "$sop_tmp" ]]; then sop_tmp="$(mktemp -d)"; fi
  printf '%s\n' "下载公开技能包"
  curl --fail --location --proto '=https' --tlsv1.2 --retry 2 --connect-timeout 20 --max-time 180 \
    "https://codeload.github.com/shao60533/industry-chain-3d-video-sop/zip/$sop_ref" -o "$sop_tmp/package.zip"
  "$sop_python" - "$sop_tmp/package.zip" "$sop_tmp/source" <<'PY'
from pathlib import Path
import sys, zipfile
base = Path(sys.argv[2]).resolve()
with zipfile.ZipFile(sys.argv[1]) as bundle:
    if sum(i.file_size for i in bundle.infolist()) > 128 * 1024 * 1024:
        raise SystemExit("技能包大小超过预期")
    for item in bundle.infolist():
        target = (base / item.filename).resolve()
        if not target.is_relative_to(base) or (item.external_attr >> 16) & 0o170000 == 0o120000:
            raise SystemExit("技能包包含不安全路径")
    bundle.extractall(base)
PY
  sop_source=""
  for sop_candidate in "$sop_tmp/source"/*; do
    if [[ -f "$sop_candidate/SKILL.md" && -f "$sop_candidate/scripts/setup.py" ]]; then
      [[ -z "$sop_source" ]] || fail "技能包目录不唯一。"
      sop_source="$sop_candidate"
    fi
  done
  [[ -n "$sop_source" ]] || fail "下载内容不是完整技能包。"
fi
"$sop_python" "$sop_source/scripts/setup.py" ${sop_bundle[@]+"${sop_bundle[@]}"} "$@"
