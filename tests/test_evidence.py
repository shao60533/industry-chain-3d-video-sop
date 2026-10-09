"""12-report envelope fixtures are synthetic, never real production evidence."""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evidence
import init_job


class EvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "synthetic-job"
        init_job.initialize(self.root, content_kind="earnings", visual_style="3d")
        self.base = self.root / "G-package"
        job = evidence.load_json(self.root / "job.json")
        job.update(revision_id="synthetic-r1", producer_id="synthetic-producer")
        self.write(self.root / "job.json", job)
        self.fixture("3d")

    def write(self, path: Path, value: dict) -> dict:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) + "\n", encoding="utf-8")
        name = path.relative_to(self.base).as_posix() if path.is_relative_to(self.base) else path.name
        return {"path": name, "sha256": evidence.sha256(path)}

    def data_ref(self, name: str) -> dict:
        path = self.base / name
        path.write_text("synthetic bytes; not media", encoding="utf-8")
        return {"path": name, "sha256": evidence.sha256(path)}

    def fixture(self, style: str) -> None:
        job = evidence.load_json(self.root / "job.json")
        job["visual_style"] = style
        self.write(self.root / "job.json", job)
        video = self.root / "F-film/final.mp4"
        video.write_bytes(b"synthetic bytes; not a movie")
        self.video_hash = evidence.sha256(video)
        self.profile_hash = evidence.sha256(self.root / "C-design/safe-layout.json")
        self.bindings = {name: self.data_ref(f"{name}.txt") for name in
                         evidence.COMMON_BINDINGS | evidence.STYLE_BINDINGS[style]}
        spec = {"schema": "video-production-spec-2.2", "job_id": job["job_id"],
                "revision_id": job["revision_id"], "producer_id": job["producer_id"],
                "content_kind": job["content_kind"], "visual_style": style,
                "media": {"frames": 24}, "bindings": self.bindings,
                "requirements": {name: [f"synthetic-{name}"] for name in evidence.CHECKS}}
        spec_ref = self.write(self.base / "production-spec.json", spec)
        proof = self.data_ref("proof.txt")
        checks = {}
        for name in evidence.CHECKS:
            report = {
                "schema": "video-check-report-2.2", "check": name, "status": "passed",
                "job_id": job["job_id"], "revision_id": job["revision_id"], "spec_sha256": spec_ref["sha256"],
                "video_sha256": self.video_hash, "profile_sha256": self.profile_hash,
                "bindings": {key: ref["sha256"] for key, ref in self.bindings.items()},
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "reviewer": {"id": job["producer_id"], "kind": "agent",
                             "capabilities": list(evidence.CHECK_CAPABILITIES[name])},
                "review_mode": "self_review", "scope": ["synthetic"], "unchecked_scope": [],
                "blocking_findings": [], "observations": [{"id": f"synthetic-{name}", "status": "passed",
                    "detail": "synthetic observation, not real checking", "artifacts": [proof]}],
                "results": {key: True for key in ("full_decode", "constant_pts", "frame_count", "audio_sync",
                    "black_scan", "color_range_matrix", "input_format_uniform", "encoded_boundary_comparison")},
                "frames_scanned": 24, "device": {"actual_platform_playback": True}}
            checks[name] = {"status": "passed", "report": self.write(self.base / f"{name}.json", report)}
        self.acceptance = {"schema": "video-release-evidence-2.2", "job_id": job["job_id"],
                           "revision_id": job["revision_id"], "video_sha256": self.video_hash,
                           "profile_sha256": self.profile_hash, "spec": spec_ref,
                           "release_ready": True, "checks": checks}
        self.write(self.base / "acceptance.json", self.acceptance)

    def check(self) -> dict:
        return evidence.check_release_bindings(self.root, "G-package/acceptance.json",
                                              "F-film/final.mp4", "C-design/safe-layout.json")

    def edit_report(self, name: str, field: str, value: object) -> None:
        path = self.base / f"{name}.json"
        report = evidence.load_json(path)
        report[field] = value
        self.acceptance["checks"][name]["report"] = self.write(path, report)
        self.write(self.base / "acceptance.json", self.acceptance)

    def test_valid_envelopes_never_claim_full_checker_or_release_even_with_passed_flags(self) -> None:
        for style in ("3d", "whiteboard"):
            self.fixture(style)
            result = self.check()
            self.assertTrue(result["evidence_bindings_valid"])
            self.assertFalse(result["release_ready"])
            self.assertEqual(result["production_checks"], "pending")
            self.assertTrue(result["external_checker_required"])

    def test_missing_report_and_pending_check_fail_closed(self) -> None:
        (self.base / "cover_crop.json").unlink()
        with self.assertRaises(evidence.GateError):
            self.check()
        self.fixture("3d")
        self.acceptance["checks"]["cover_crop"]["status"] = "pending"
        self.write(self.base / "acceptance.json", self.acceptance)
        with self.assertRaisesRegex(evidence.GateError, "check_not_passed"):
            self.check()
        self.fixture("3d")
        self.edit_report("cover_crop", "status", "pending")
        with self.assertRaisesRegex(evidence.GateError, "report_not_passed"):
            self.check()

    def test_input_and_media_changes_invalidate_their_previous_sha(self) -> None:
        (self.base / "script.txt").write_text("modified source", encoding="utf-8")
        with self.assertRaisesRegex(evidence.GateError, "sha256_mismatch"):
            self.check()
        self.fixture("3d")
        (self.root / "F-film/final.mp4").write_bytes(b"new bytes")
        with self.assertRaisesRegex(evidence.GateError, "video_sha256_mismatch"):
            self.check()

    def test_rehashing_spec_cannot_make_old_reports_current(self) -> None:
        path = self.base / "production-spec.json"
        spec = evidence.load_json(path)
        spec["media"]["frames"] = 48
        self.acceptance["spec"] = self.write(path, spec)
        self.write(self.base / "acceptance.json", self.acceptance)
        with self.assertRaisesRegex(evidence.GateError, "report_spec_mismatch"):
            self.check()

    def test_wrong_type_cross_job_and_missing_dependency_fail_closed(self) -> None:
        for field, value, code in (("check", "technical", "report_type_mismatch"),
                                   ("job_id", "another", "report_binding_mismatch"),
                                   ("bindings", {}, "report_dependencies_mismatch")):
            self.fixture("3d")
            self.edit_report("source_script", field, value)
            with self.assertRaisesRegex(evidence.GateError, code):
                self.check()

    def test_future_time_false_independence_unchecked_and_missing_capability_fail(self) -> None:
        for field, value in (("checked_at", (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()),
                             ("review_mode", "independent"), ("unchecked_scope", ["not heard"]),
                             ("reviewer", {"id": "synthetic-producer", "kind": "agent", "capabilities": []})):
            self.fixture("3d")
            self.edit_report("voice_identity", field, value)
            with self.assertRaises(evidence.GateError):
                self.check()

    def test_simulated_device_and_incomplete_scan_cannot_be_passed(self) -> None:
        self.edit_report("real_device_overlay", "device", {"actual_platform_playback": False})
        with self.assertRaisesRegex(evidence.GateError, "actual_device_pending"):
            self.check()
        self.fixture("3d")
        self.edit_report("technical", "frames_scanned", 1)
        with self.assertRaisesRegex(evidence.GateError, "technical_scan_incomplete"):
            self.check()

    def test_missing_sha_and_proof_path_escape_fail(self) -> None:
        self.acceptance["checks"]["source_script"]["report"]["sha256"] = None
        self.write(self.base / "acceptance.json", self.acceptance)
        with self.assertRaisesRegex(evidence.GateError, "sha256_required"):
            self.check()
        outside = self.root / "private-proof.txt"
        outside.write_text("synthetic", encoding="utf-8")
        with self.assertRaisesRegex(evidence.GateError, "evidence_outside_package"):
            evidence.verify_ref(self.base, {"path": "../private-proof.txt", "sha256": evidence.sha256(outside)})

    def test_symlink_cannot_stand_in_for_proof(self) -> None:
        link = self.base / "link.txt"
        try:
            link.symlink_to(self.base / "proof.txt")
        except OSError:
            self.skipTest("Symlinks require platform privileges")
        with self.assertRaisesRegex(evidence.GateError, "evidence_symlink"):
            evidence.verify_ref(self.base, {"path": "link.txt", "sha256": evidence.sha256(link)})

    def test_duplicate_keys_are_rejected(self) -> None:
        path = self.base / "duplicate.json"
        path.write_text('{"status":"pending","status":"passed"}', encoding="utf-8")
        with self.assertRaisesRegex(evidence.GateError, "duplicate_json_key"):
            evidence.load_json(path)

    def test_dependencies_are_rechecked_after_all_reports(self) -> None:
        original = evidence.recheck
        def changed_before_final_check(snapshot: dict) -> None:
            (self.base / "proof.txt").write_text("replaced proof", encoding="utf-8")
            original(snapshot)
        with patch.object(evidence, "recheck", side_effect=changed_before_final_check):
            with self.assertRaisesRegex(evidence.GateError, "dependencies_changed_during_check"):
                self.check()


if __name__ == "__main__":
    unittest.main()
