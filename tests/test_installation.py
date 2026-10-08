"""Behavioral tests for installation safety and unapproved job creation."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
import re
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import doctor
import init_job
import runtime
import setup


class InstallationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def test_default_destination_respects_codex_home(self) -> None:
        with patch.dict(os.environ, {"CODEX_HOME": str(self.directory)}):
            self.assertEqual(setup.default_destination(), self.directory / "skills" / runtime.SKILL_NAME)

    def test_never_overwrite_an_unknown_directory(self) -> None:
        target = self.directory / "existing"
        target.mkdir()
        valuable = target / "work.md"
        valuable.write_text("user work")
        with self.assertRaises(RuntimeError):
            setup.copy_payload(runtime.ROOT, target)
        self.assertEqual(valuable.read_text(), "user work")

    def test_never_install_over_home_or_source_parent(self) -> None:
        for target in (Path.home(), runtime.ROOT.parent):
            with self.assertRaises(RuntimeError):
                setup.guard_destination(runtime.ROOT, target)

    def test_copy_only_public_payload_and_preserve_local_jobs(self) -> None:
        target = self.directory / "skill"
        files = setup.copy_payload(runtime.ROOT, target)
        self.assertIn("SKILL.md", files)
        self.assertNotIn(".git/config", files)
        self.assertFalse((target / ".git").exists())
        (target / ".skill-installation.json").write_text(json.dumps({"skill": runtime.SKILL_NAME}))
        private = target / "jobs/local/work.txt"
        private.parent.mkdir(parents=True)
        private.write_text("local work")
        setup.copy_payload(runtime.ROOT, target)
        self.assertEqual(private.read_text(), "local work")

    def test_reject_target_symlink(self) -> None:
        target = self.directory / "linked"
        real = self.directory / "real"
        real.mkdir()
        try:
            target.symlink_to(real, target_is_directory=True)
        except OSError:
            self.skipTest("Symlinks require platform privileges")
        with self.assertRaises(RuntimeError):
            setup.copy_payload(runtime.ROOT, target)

    def test_reject_nested_target_link_before_any_copy(self) -> None:
        target = self.directory / "skill"
        target.mkdir()
        (target / ".skill-installation.json").write_text(json.dumps({"skill": runtime.SKILL_NAME}))
        external = self.directory / "external"
        external.mkdir()
        try:
            (target / "docs").symlink_to(external, target_is_directory=True)
        except OSError:
            self.skipTest("Symlinks require platform privileges")
        with self.assertRaises(RuntimeError):
            setup.copy_payload(runtime.ROOT, target)
        self.assertFalse((target / "SKILL.md").exists())
        self.assertEqual(list(external.iterdir()), [])

    def test_zip_traversal_does_not_escape(self) -> None:
        archive = self.directory / "bad.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("../escape", "bad")
        with self.assertRaises(RuntimeError):
            setup.extract_archive(archive, self.directory / "output")
        self.assertFalse((self.directory / "escape").exists())

    def test_tar_link_escape_is_rejected(self) -> None:
        archive = self.directory / "bad.tar.xz"
        with tarfile.open(archive, "w:xz") as bundle:
            item = tarfile.TarInfo("linked")
            item.type = tarfile.SYMTYPE
            item.linkname = "../../elsewhere"
            bundle.addfile(item)
        with self.assertRaises(RuntimeError):
            setup.extract_archive(archive, self.directory / "output")

    def test_valid_archive_extracts(self) -> None:
        archive = self.directory / "valid.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("app/hello.txt", "hello")
        setup.extract_archive(archive, self.directory / "output")
        self.assertEqual((self.directory / "output/app/hello.txt").read_text(), "hello")

    def test_checksum_mismatch_never_replaces_existing_download(self) -> None:
        target = self.directory / "artifact"
        target.write_text("old")
        def fake_download(args: list[str], timeout: int) -> str:
            Path(args[args.index("--output") + 1]).write_text("unexpected")
            return ""
        with patch.object(setup, "run", side_effect=fake_download):
            with self.assertRaises(RuntimeError):
                setup.download("https://example.invalid/file", target, "0" * 64)
        self.assertEqual(target.read_text(), "old")
        self.assertFalse(target.with_name(target.name + ".part").exists())

    def test_local_tool_override_does_not_silently_fall_back(self) -> None:
        with patch.dict(os.environ, {"VIDEO_SOP_BLENDER": str(self.directory / "absent")}):
            with self.assertRaises(RuntimeError):
                runtime.find_tool("blender")

    def test_versions_accept_lts_and_ffmpeg_output(self) -> None:
        self.assertEqual(runtime.version("Blender 4.5.14 LTS"), (4, 5, 14))
        self.assertEqual(runtime.version("ffmpeg version 8.1 Copyright"), (8, 1, 0))

    def test_console_redaction(self) -> None:
        synthetic = "ghp_" + "Z" * 32
        message = runtime.safe_message(str(Path.home() / "private") + " " + synthetic)
        self.assertNotIn(str(Path.home()), message)
        self.assertNotIn(synthetic, message)

    def test_failed_process_never_prints_raw_stderr(self) -> None:
        from subprocess import CompletedProcess
        with patch.object(runtime.subprocess, "run", return_value=CompletedProcess([], 1, "", "private details")):
            with self.assertRaisesRegex(RuntimeError, "退出 1") as caught:
                runtime.run(["example"])
        self.assertNotIn("private details", str(caught.exception))

    def test_failed_tools_keep_environment_not_ready(self) -> None:
        with patch.object(doctor, "config", return_value={}), patch.object(doctor, "find_tool", return_value=None):
            report = doctor.inspect_environment(smoke=True)
        self.assertFalse(report["ready"])
        self.assertFalse(report["checks"]["smoke"]["passed"])
        self.assertEqual(report["film_acceptance"], "pending")

    def test_new_job_is_unapproved_with_all_stages(self) -> None:
        output = self.directory / "test-product"
        init_job.initialize(output)
        job = json.loads((output / "job.json").read_text(encoding="utf-8"))
        self.assertEqual(job["job_id"], "test-product")
        self.assertEqual(job["mode"], "produce_only")
        self.assertIsNone(job["publication_authorization"])
        self.assertFalse(job["ready_to_produce"])
        for stage in init_job.STAGES:
            self.assertTrue((output / stage).is_dir())
        acceptance = json.loads((output / "templates/acceptance.template.json").read_text(encoding="utf-8"))
        self.assertTrue(all(item["status"] == "pending" for item in acceptance["checks"].values()))

    def test_existing_job_is_never_replaced(self) -> None:
        output = self.directory / "existing-job"
        output.mkdir()
        original = output / "script.md"
        original.write_text("approved work")
        with self.assertRaises(ValueError):
            init_job.initialize(output)
        self.assertEqual(original.read_text(), "approved work")

    def test_new_job_documentation_links_resolve_outside_skill(self) -> None:
        output = self.directory / "elsewhere/new-job"
        init_job.initialize(output)
        for document in (output / "templates").glob("*.md"):
            for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                if link.startswith(("http:", "https:", "file:", "#")):
                    continue
                self.assertTrue((document.parent / link).exists(), f"Broken link in {document.name}")


if __name__ == "__main__":
    unittest.main()
