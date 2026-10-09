"""Doctor regressions; synthetic adapters do not prove a real render."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import doctor


class DoctorTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.font = self.root / "synthetic-font.ttf"
        self.font.write_bytes(b"synthetic font selection proof, not a CJK font")

    def test_explicit_font_and_collection_index_override_saved_configuration(self) -> None:
        with patch.dict(os.environ, {"VIDEO_SOP_FONT": str(self.font), "VIDEO_SOP_FONT_INDEX": "2"}), \
             patch.object(doctor, "config", return_value={"font": "unused", "font_index": 1}), \
             patch.object(doctor, "find_tool", return_value=None), \
             patch.object(doctor, "check_font", return_value={"passed": True}) as check:
            report = doctor.inspect_environment()
        self.assertTrue(report["checks"]["pillow_font"]["passed"])
        check.assert_called_once_with(self.font, 2, None)

    def test_missing_explicit_font_never_falls_back_to_saved_font(self) -> None:
        with patch.dict(os.environ, {"VIDEO_SOP_FONT": str(self.root / "missing")}), \
             patch.object(doctor, "config", return_value={"font": str(self.font)}), \
             patch.object(doctor, "find_tool", return_value=None):
            report = doctor.inspect_environment()
        self.assertFalse(report["ready"])
        self.assertFalse(report["checks"]["pillow_font"]["passed"])
        self.assertNotIn(str(self.root), json.dumps(report))

    def test_latin_only_font_cannot_pass_using_missing_glyph_boxes(self) -> None:
        latin = ImageFont.load_default()
        with patch.object(ImageFont, "truetype", return_value=latin), \
             patch.object(doctor, "config", return_value={"font": str(self.font)}), \
             patch.object(doctor, "find_tool", return_value=None):
            report = doctor.inspect_environment()
        self.assertFalse(report["checks"]["pillow_font"]["passed"])
        self.assertRegex(report["checks"]["pillow_font"]["reason"], "中文.*字形")

    def test_positive_text_bbox_without_actual_pixels_cannot_pass(self) -> None:
        draw = SimpleNamespace(textbbox=lambda *a, **k: (0, 0, 300, 40), text=lambda *a, **k: None)
        class Glyph(bytes):
            size = (1, 1)
        class SyntheticFont:
            def getmask(self, text, **kwargs):
                return Glyph([1 if text == "\U0010ffff" else 2])
        with patch.object(ImageFont, "truetype", return_value=SyntheticFont()), \
             patch.object(ImageDraw, "Draw", return_value=draw), \
             patch.object(doctor, "config", return_value={"font": str(self.font)}), \
             patch.object(doctor, "find_tool", return_value=None):
            report = doctor.inspect_environment()
        self.assertFalse(report["checks"]["pillow_font"]["passed"])
        self.assertRegex(report["checks"]["pillow_font"]["reason"], "像素.*墨迹")

    def test_minimal_cpu_render_does_not_require_optional_denoiser(self) -> None:
        scene = SimpleNamespace(
            cycles=SimpleNamespace(device="GPU", samples=64, use_denoising=True),
            render=SimpleNamespace(image_settings=SimpleNamespace()),
        )
        calls = []
        def render(**kwargs):
            if scene.cycles.use_denoising:
                raise RuntimeError("Failed to denoise, build has no OpenImageDenoise support")
            calls.append((scene.render.engine, scene.cycles.device, scene.cycles.samples))
        bpy = SimpleNamespace(context=SimpleNamespace(scene=scene),
                              ops=SimpleNamespace(wm=SimpleNamespace(save_as_mainfile=lambda **kwargs: None),
                                                  render=SimpleNamespace(render=render)))
        with patch.dict(sys.modules, {"bpy": bpy}), patch.object(sys, "argv", ["blender", "--", str(self.root)]):
            exec(doctor.BLENDER_SMOKE, {})
        self.assertEqual(calls, [("CYCLES", "CPU", 1)])
        self.assertFalse(scene.cycles.use_denoising)

    def test_uniform_corrupt_and_wrong_size_render_outputs_are_rejected(self) -> None:
        frame = self.root / "frame.png"
        for kind in ("uniform", "corrupt", "wrong_size", "transparent"):
            with self.subTest(kind=kind):
                if kind == "corrupt":
                    frame.write_bytes(b"not a PNG")
                elif kind == "wrong_size":
                    Image.new("RGB", (32, 32)).save(frame)
                elif kind == "transparent":
                    image = Image.new("RGBA", (64, 64))
                    image.putpixel((0, 0), (255, 255, 255, 0))
                    image.save(frame)
                else:
                    Image.new("RGB", (64, 64)).save(frame)
                with self.assertRaises((RuntimeError, OSError)):
                    doctor.check_render_frame(frame)

    def test_decoded_nonuniform_render_pixels_are_version_bound(self) -> None:
        frame = self.root / "frame.png"
        image = Image.new("RGB", (64, 64))
        ImageDraw.Draw(image).rectangle((16, 16, 48, 48), fill=(128, 64, 255))
        image.save(frame)
        result = doctor.check_render_frame(frame)
        self.assertEqual(result["size"], [64, 64])
        self.assertTrue(result["nonuniform_pixels"])
        self.assertEqual(len(result["pixels_sha256"]), 64)
        image.putpixel((0, 0), (255, 255, 255))
        image.save(frame)
        self.assertNotEqual(result["pixels_sha256"], doctor.check_render_frame(frame)["pixels_sha256"])

    def test_existing_artifact_directory_is_never_overwritten(self) -> None:
        target = self.root / "existing"
        target.mkdir()
        proof = target / "frame.png"
        proof.write_bytes(b"existing proof")
        with self.assertRaisesRegex(RuntimeError, "证据目录已存在"):
            doctor.inspect_environment(artifacts_dir=target)
        self.assertEqual(proof.read_bytes(), b"existing proof")

    def test_missing_pillow_keeps_font_and_render_checks_failed(self) -> None:
        with patch.dict(sys.modules, {"PIL": None}), \
             patch.object(doctor, "config", return_value={}), \
             patch.object(doctor, "find_tool", return_value="synthetic-tool"), \
             patch.object(doctor, "run", return_value="4.3.2"), \
             patch.object(doctor, "smoke_test", side_effect=ImportError("synthetic missing Pillow")):
            report = doctor.inspect_environment(smoke=True)
        self.assertFalse(report["ready"])
        self.assertFalse(report["checks"]["pillow_font"]["passed"])
        self.assertFalse(report["checks"]["smoke"]["passed"])
        self.assertEqual(report["film_acceptance"], "pending")


if __name__ == "__main__":
    unittest.main()
