"""Local voice checks that need no model: reference intake, refusal to overwrite, tamper detection."""

from __future__ import annotations

import array
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import local_voice
import runtime
import setup


def tone(seconds: float, amplitude: float = 0.2) -> array.array:
    count = round(seconds * local_voice.SAMPLE_RATE)
    return array.array("h", (round(amplitude * 32767 * math.sin(2 * math.pi * 220 * i / local_voice.SAMPLE_RATE))
                             for i in range(count)))


def converter(samples: array.array):
    def convert(source: Path, target: Path) -> None:
        local_voice.write_wav(target, samples)
    return convert


class LocalVoiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.recording = self.directory / "recording.m4a"
        self.recording.write_bytes(b"placeholder")

    def voice(self) -> Path:
        out = self.directory / "voice"
        local_voice.prepare(self.recording, "今天讲一台手机。", out, convert=converter(tone(25)))
        return out

    def test_prepare_records_hashes_and_leaves_human_checks_pending(self) -> None:
        out = self.voice()
        record = json.loads((out / "reference.json").read_text(encoding="utf-8"))
        self.assertEqual(record["audio_sha256"], local_voice.sha256(out / "reference.wav"))
        self.assertEqual(record["text_sha256"], local_voice.sha256(out / "reference.txt"))
        self.assertIs(record["uploaded"], False)
        self.assertEqual(record["transcript_matches_recording"], "pending_human_check")
        self.assertEqual(record["usage_authorization"], "pending_human_confirmation")
        self.assertEqual(record["warnings"], [])

    def test_prepare_never_overwrites_an_existing_voice(self) -> None:
        out = self.voice()
        before = local_voice.sha256(out / "reference.wav")
        with self.assertRaises(RuntimeError):
            local_voice.prepare(self.recording, "另一段文字。", out, convert=converter(tone(30)))
        self.assertEqual(local_voice.sha256(out / "reference.wav"), before)

    def test_rejected_recordings_leave_no_partial_voice(self) -> None:
        cases = {"short": tone(4), "long": tone(70), "silent": array.array("h", bytes(2 * 20 * local_voice.SAMPLE_RATE))}
        for name, samples in cases.items():
            with self.subTest(name=name):
                out = self.directory / name
                with self.assertRaises(RuntimeError):
                    local_voice.prepare(self.recording, "文字。", out, convert=converter(samples))
                self.assertFalse(out.exists())
        with self.assertRaises(RuntimeError):
            local_voice.prepare(self.recording, "   ", self.directory / "empty", convert=converter(tone(25)))
        self.assertFalse((self.directory / "empty").exists())

    def test_measure_warns_about_quiet_clipped_and_brief_recordings(self) -> None:
        quiet = local_voice.measure(tone(25, 0.015), local_voice.SAMPLE_RATE)
        self.assertTrue(any("音量偏小" in item for item in quiet["warnings"]))
        clipped = tone(25)
        for index in range(0, len(clipped), 100):
            clipped[index] = 32767
        self.assertTrue(any("爆音" in item for item in local_voice.measure(clipped, local_voice.SAMPLE_RATE)["warnings"]))
        self.assertTrue(any("偏短" in item for item in local_voice.measure(tone(12), local_voice.SAMPLE_RATE)["warnings"]))
        with self.assertRaises(RuntimeError):
            local_voice.measure(tone(25), 16000)

    def test_speak_writes_units_preview_and_pending_review(self) -> None:
        voice = self.voice()
        calls = []

        def synthesize(text: str, seed: int) -> array.array:
            calls.append((text, seed))
            return tone(1.0)

        out = self.directory / "take"
        manifest = local_voice.speak(voice, "# 标题\n\n第一段第一句。第一段第二句。\n\n第二段。", out, seed=3, synthesizer=synthesize)
        self.assertEqual([text for text, _ in calls], ["第一段第一句。第一段第二句。", "第二段。"])
        self.assertEqual({seed for _, seed in calls}, {3})
        self.assertEqual(manifest["listening_review"], "pending")
        self.assertIs(manifest["reference_uploaded"], False)
        self.assertEqual(manifest["model_revision"], local_voice.MODEL_REVISION)
        for unit in manifest["units"]:
            self.assertEqual(unit["sha256"], local_voice.sha256(out / unit["file"]))
        samples, rate = local_voice.read_wav(out / "preview.wav")
        self.assertEqual(rate, local_voice.SAMPLE_RATE)
        self.assertAlmostEqual(len(samples) / rate, 2 * 1.0 + 2 * local_voice.PARAGRAPH_PAUSE, places=2)
        with self.assertRaises(RuntimeError):
            local_voice.speak(voice, "第二段。", out, synthesizer=synthesize)

    def test_speak_refuses_a_reference_changed_after_preparation(self) -> None:
        voice = self.voice()
        (voice / "reference.txt").write_text("被改过的文字。\n", encoding="utf-8")
        out = self.directory / "take"
        with self.assertRaises(RuntimeError):
            local_voice.speak(voice, "第二段。", out, synthesizer=lambda text, seed: tone(1.0))
        self.assertFalse(out.exists())

    def test_speak_rejects_empty_text_and_bad_options_before_writing(self) -> None:
        voice = self.voice()
        out = self.directory / "take"
        for arguments in ({"text": "# 只有标题"}, {"text": "正文。", "language": "klingon"}, {"text": "正文。", "temperature": 0}):
            with self.subTest(arguments=arguments), self.assertRaises(RuntimeError):
                local_voice.speak(voice, arguments.pop("text"), out, synthesizer=lambda text, seed: tone(1.0), **arguments)
        self.assertFalse(out.exists())

    def test_installer_refuses_unsupported_platforms_before_creating_anything(self) -> None:
        target = self.directory / "skill"
        with patch.object(setup, "voice_supported", return_value=False), self.assertRaises(RuntimeError):
            setup.install_voice(target)
        self.assertFalse(target.exists())

    def test_voice_payload_and_ignore_rules(self) -> None:
        self.assertIn("requirements-voice.txt", setup.PAYLOAD)
        ignored = (runtime.ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        for rule in (".venv-voice/", "voice-references/", "recordings/", "*.wav"):
            self.assertIn(rule, ignored)
        pins = [line for line in (runtime.ROOT / "requirements-voice.txt").read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")]
        self.assertTrue(pins and all("==" in line for line in pins))
        self.assertTrue((runtime.ROOT / "templates/voice/reading-script.zh.txt").read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    unittest.main()
