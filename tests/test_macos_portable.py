"""macOS installs from pinned downloads into the skill directory: no Homebrew, no administrator password."""

from __future__ import annotations

import contextlib
import io
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import runtime
import setup


class MacPortableTests(unittest.TestCase):
    # Progress lines are Chinese; a Windows CI console code page cannot encode them, so they are captured.
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.destination = Path(self.temporary.name) / "skill"

    def test_every_mac_download_is_https_and_pinned(self) -> None:
        self.assertEqual(set(setup.MAC_TOOLS), {"arm64", "x64"})
        for table in setup.MAC_TOOLS.values():
            self.assertEqual(set(table), {"blender", "ffmpeg", "ffprobe"})
            for name, (source, checksum) in table.items():
                self.assertRegex(checksum, r"^[0-9a-f]{64}$")
                if name != "blender":
                    self.assertTrue(source.startswith("https://"))
                    self.assertNotIn("latest", source)

    def test_missing_mac_tools_come_from_pinned_downloads_without_a_package_manager(self) -> None:
        downloads, commands = [], []

        def download(url: str, output: Path, checksum: str | None = None, limit: int = 900) -> None:
            downloads.append((url, checksum))
            if output.suffix == ".zip":
                with zipfile.ZipFile(output, "w") as bundle:
                    bundle.writestr(output.stem, "binary")
            else:
                output.write_bytes(b"image")

        def run(args: list[str], timeout: int = 180) -> str:
            commands.append(args)
            if args[0].endswith("ditto"):
                (Path(args[2]) / "Contents/MacOS").mkdir(parents=True)
                (Path(args[2]) / "Contents/MacOS/Blender").write_text("blender")
            return ""

        with patch.object(setup.platform, "system", return_value="Darwin"), \
             patch.object(setup.platform, "machine", return_value="arm64"), \
             patch.object(setup, "download", download), patch.object(setup, "run", run), \
             patch.object(setup.subprocess, "run") as detach, contextlib.redirect_stdout(io.StringIO()):
            extra = setup.install_system_tools(self.destination, ["blender", "ffmpeg", "ffprobe"])
        table = setup.MAC_TOOLS["arm64"]
        self.assertEqual({checksum for _, checksum in downloads}, {checksum for _, checksum in table.values()})
        self.assertTrue(all(url.startswith("https://") for url, _ in downloads))
        tools = self.destination / ".local/tools"
        self.assertEqual(Path(extra["ffmpeg"]), tools / "ffmpeg/ffmpeg")
        self.assertEqual(Path(extra["ffprobe"]), tools / "ffmpeg/ffprobe")
        self.assertEqual(Path(extra["blender"]), tools / "Blender.app/Contents/MacOS/Blender")
        self.assertTrue(all(Path(path).is_file() for path in extra.values()))
        used = " ".join(" ".join(args) for args in commands)
        self.assertNotRegex(used, r"brew|sudo")
        self.assertTrue(detach.called and "detach" in detach.call_args.args[0])

    def test_only_missing_tools_are_downloaded(self) -> None:
        downloads = []

        def download(url: str, output: Path, checksum: str | None = None, limit: int = 900) -> None:
            downloads.append(url)
            with zipfile.ZipFile(output, "w") as bundle:
                bundle.writestr(output.stem, "binary")

        with patch.object(setup.platform, "system", return_value="Darwin"), \
             patch.object(setup.platform, "machine", return_value="x86_64"), patch.object(setup, "download", download), \
             contextlib.redirect_stdout(io.StringIO()):
            extra = setup.install_system_tools(self.destination, ["ffprobe"])
        self.assertEqual(list(extra), ["ffprobe"])
        self.assertEqual(downloads, [setup.MAC_TOOLS["x64"]["ffprobe"][0]])

    def test_unknown_mac_architecture_fails_before_downloading(self) -> None:
        with patch.object(setup.platform, "system", return_value="Darwin"), \
             patch.object(setup.platform, "machine", return_value="riscv64"), \
             patch.object(setup, "download") as download, self.assertRaises(RuntimeError):
            setup.install_system_tools(self.destination, ["ffmpeg"])
        download.assert_not_called()

    def test_environments_are_built_from_the_bundled_python_when_present(self) -> None:
        self.assertEqual(setup.base_python(self.destination), sys.executable)
        bundled = self.destination / ".local/tools/python/bin/python3"
        bundled.parent.mkdir(parents=True)
        bundled.write_text("python")
        self.assertEqual(setup.base_python(self.destination), str(bundled))
        with patch.object(setup, "run", return_value="") as run:
            setup.create_environment(self.destination / ".venv", self.destination)
        self.assertEqual(run.call_args.args[0][:3], [str(bundled), "-m", "venv"])

    def test_bootstrap_script_pins_python_and_never_installs_homebrew(self) -> None:
        text = (runtime.ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertNotRegex(text, r"brew install|Homebrew/install")
        self.assertEqual(len(re.findall(r"sop_py_sha=[0-9a-f]{64}\b", text)), 2)
        self.assertIn("shasum -a 256", text)
        self.assertIn("--python-archive", text)


if __name__ == "__main__":
    unittest.main()
