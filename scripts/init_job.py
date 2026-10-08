"""Initialize a new, unapproved production job without overwriting any files."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from runtime import ROOT, safe_message

STAGES = ("A-reference", "B-script", "C-design", "D-audio", "E-model", "F-film", "G-package", "H-publish")


def initialize(output: Path) -> None:
    output = output.expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("任务目录已存在；请使用新目录，原产物不会被覆盖")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Resolve directory aliases before calculating links (macOS /var is a symlink).
    output = output.parent.resolve() / output.name
    with tempfile.TemporaryDirectory(prefix=".video-job-", dir=output.parent) as temporary:
        stage = Path(temporary) / "job"
        shutil.copytree(ROOT / "templates/next-episode", stage / "templates")
        # Keep links to skill documentation valid when a job lives elsewhere.
        for document in (stage / "templates").glob("*.md"):
            def relocate(match: re.Match) -> str:
                label, target = match.groups()
                if not target.startswith("../../docs/"):
                    return match.group(0)
                reference = ROOT / "docs" / target.removeprefix("../../docs/")
                try:
                    link = Path(os.path.relpath(reference, output / "templates")).as_posix()
                except ValueError:  # Windows jobs may be on another drive.
                    link = reference.as_uri()
                return f"[{label}]({link})"
            text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", relocate, document.read_text(encoding="utf-8"))
            document.write_text(text, encoding="utf-8")
        for name in STAGES:
            (stage / name).mkdir()
        job = json.loads((stage / "templates/job.template.json").read_text(encoding="utf-8"))
        job["job_id"] = output.name
        (stage / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        shutil.copy2(ROOT / "profiles/safe-layout.default.json", stage / "C-design/safe-layout.json")
        (stage / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")
        (stage / "START-HERE.md").write_text(
            "# 新任务\n\n填写 job.json 的完整来源、主题和实际选择。"
            "templates/ 保存空白工作底稿；默认 produce_only，验收保持 pending。"
            "安装技能内的 docs/codex-workflow.md 是执行入口。"
            "任务含私人原文、音色和平台记录，不提交公开仓库。\n", encoding="utf-8"
        )
        # Reserve the final directory atomically; a concurrent job cannot be replaced.
        output.mkdir(exist_ok=False)
        for item in stage.iterdir():
            item.rename(output / item.name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        initialize(args.output)
    except (OSError, ValueError) as exc:
        print(safe_message(str(exc)))
        return 1
    print("新任务已建立；模式 produce_only，质量状态 pending。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
