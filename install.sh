#!/usr/bin/env bash
# macOS / Debian / Ubuntu bootstrap; installs no credentials or account state.
set -euo pipefail

sop_ref="${VIDEO_SOP_REF:-main}"
sop_tmp=""
cleanup() { if [[ -n "$sop_tmp" ]]; then rm -rf "$sop_tmp"; fi; }
trap cleanup EXIT
fail() { printf '%s\n' "$1" >&2; exit 1; }

[[ "$sop_ref" =~ ^[A-Za-z0-9._-]+$ ]] || fail "版本必须为分支名、标签或提交 SHA。"
sop_skip=0
for sop_arg in "$@"; do
  case "$sop_arg" in --skip-system-deps|--dry-run) sop_skip=1 ;; esac
done

find_python() {
  local candidate
  for candidate in "${VIDEO_SOP_PYTHON:-}" python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
    if [[ -n "$candidate" ]] && command -v "$candidate" >/dev/null 2>&1; then
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
      sop_brew="$(command -v brew || true)"
      for sop_candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
        if [[ -z "$sop_brew" && -x "$sop_candidate" ]]; then sop_brew="$sop_candidate"; fi
      done
      if [[ -z "$sop_brew" ]]; then
        command -v curl >/dev/null 2>&1 || fail "缺少 macOS 系统 curl，请修复系统命令后重试。"
        sop_tmp="$(mktemp -d)"
        curl --fail --location --proto '=https' --connect-timeout 20 --max-time 120 \
          https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh -o "$sop_tmp/homebrew.sh"
        NONINTERACTIVE=1 /bin/bash "$sop_tmp/homebrew.sh"
        for sop_candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
          if [[ -x "$sop_candidate" ]]; then sop_brew="$sop_candidate"; break; fi
        done
      fi
      [[ -n "$sop_brew" ]] || fail "Homebrew 未安装完成；需要系统管理员完成初次权限设置。"
      "$sop_brew" install python
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
find_python || fail "Python 需要 3.11+；旧发行版请先升级 Python，再重新安装。"

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
"$sop_python" "$sop_source/scripts/setup.py" "$@"
