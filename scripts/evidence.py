"""Local structural/SHA evidence validation, never a complete film checker."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

CHECKS = ("source_script", "company_judgments", "voice_identity", "model_coverage",
          "opening_motion_rhythm", "technical", "layout_geometry", "encoded_masked_review",
          "dynamic_playback", "voice_music_listening", "real_device_overlay", "cover_crop")
COMMON_BINDINGS = {"source_full", "script", "timing", "font", "renderer", "audio",
                   "cover", "title", "body", "layout"}
STYLE_BINDINGS = {"3d": {"model", "component_inventory"},
                  "whiteboard": {"visual_project", "visual_inventory"}}
CHECK_CAPABILITIES = {
    "source_script": {"read_source"}, "company_judgments": {"read_source"},
    "voice_identity": {"listen_audio"}, "model_coverage": {"view_images"},
    "opening_motion_rhythm": {"watch_video", "listen_audio"}, "technical": {"probe_media"},
    "layout_geometry": {"measure_layout"}, "encoded_masked_review": {"view_images"},
    "dynamic_playback": {"watch_video", "listen_audio"}, "voice_music_listening": {"listen_audio"},
    "real_device_overlay": {"actual_device"}, "cover_crop": {"view_images"}}


class GateError(ValueError):
    """A stable code keeps private file contents and paths off the console."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise GateError(code)


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def sha256(path: Path) -> str:
    try:
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError as exc:
        raise GateError("file_missing_or_unreadable") from exc


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict:
    def pairs(items: list[tuple]) -> dict:
        result = {}
        for key, value in items:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result

    def invalid_constant(value: str) -> None:
        raise GateError("nonfinite_json_number")

    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs,
                           parse_constant=invalid_constant)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GateError("json_missing_or_invalid") from exc
    require(isinstance(value, dict), "json_object_required")
    return value


def file_path(base: Path, name: str, *, external: bool = False) -> Path:
    require(nonempty(name), "file_path_required")
    base = base.resolve()
    path = Path(name)
    if not path.is_absolute():
        path = base / path
    # Directory aliases for the job root are fine; referenced links are not evidence.
    require(not any(p.is_symlink() for p in (path, *path.parents) if p != base and base in p.parents),
            "evidence_symlink")
    require(not path.is_symlink(), "evidence_symlink")
    try:
        path = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise GateError("file_missing_or_unreadable") from exc
    require(path.is_file(), "regular_file_required")
    require(external or path.is_relative_to(base), "evidence_outside_package")
    return path


def verify_ref(base: Path, ref: dict, *, external: bool = False,
               snapshot: dict[Path, str] | None = None) -> Path:
    require(isinstance(ref, dict), "file_reference_required")
    expected = ref.get("sha256")
    require(isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected) is not None,
            "sha256_required")
    path = file_path(base, ref.get("path"), external=external)
    require(sha256(path) == expected, "sha256_mismatch")
    if snapshot is not None:
        require(path not in snapshot or snapshot[path] == expected, "conflicting_file_binding")
        snapshot[path] = expected
    return path


def recheck(snapshot: dict[Path, str]) -> None:
    for path, expected in snapshot.items():
        require(sha256(path) == expected, "dependencies_changed_during_check")


def check_time(value: str) -> None:
    require(nonempty(value), "check_time_required")
    try:
        checked = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GateError("check_time_invalid") from exc
    require(checked.tzinfo is not None and checked.utcoffset() is not None, "check_time_timezone_required")
    require(checked <= datetime.now(timezone.utc), "check_time_in_future")


def review(report: dict, producer: str, capabilities: set[str]) -> None:
    require(nonempty(producer), "producer_required")
    reviewer = report.get("reviewer")
    require(isinstance(reviewer, dict) and nonempty(reviewer.get("id")), "reviewer_required")
    require(reviewer.get("kind") in ("agent", "human", "tool"), "reviewer_kind_invalid")
    actual = reviewer.get("capabilities")
    require(isinstance(actual, list) and all(nonempty(x) for x in actual), "capabilities_required")
    require(capabilities <= set(actual), "capability_missing")
    mode = report.get("review_mode")
    require(mode in ("self_review", "independent"), "review_mode_required")
    if mode == "independent":
        require(reviewer["id"] != producer, "false_independent_review")
    else:
        require(reviewer["id"] == producer, "self_review_identity_mismatch")
    check_time(report.get("checked_at"))
    require(report.get("unchecked_scope") == [], "unchecked_scope")
    require(report.get("blocking_findings") == [], "blocking_findings")
    require(bool(report.get("scope")), "scope_required")


def observations(base: Path, report: dict, required: list[str], snapshot: dict[Path, str]) -> None:
    require(isinstance(required, list) and bool(required) and all(nonempty(x) for x in required),
            "requirements_missing")
    require(len(set(required)) == len(required), "duplicate_requirement")
    items = report.get("observations")
    require(isinstance(items, list) and bool(items), "observations_missing")
    seen = set()
    for item in items:
        require(isinstance(item, dict) and nonempty(item.get("id")), "observation_id_required")
        require(item["id"] not in seen, "duplicate_observation")
        seen.add(item["id"])
        require(item.get("status") == "passed", "observation_not_passed")
        require(nonempty(item.get("detail")), "observation_detail_required")
        artifacts = item.get("artifacts")
        require(isinstance(artifacts, list) and bool(artifacts), "observation_proof_missing")
        for ref in artifacts:
            verify_ref(base, ref, snapshot=snapshot)
    require(set(required) <= seen, "observation_coverage_missing")


def check_release_bindings(root: Path, evidence_name: str, video_name: str, profile_name: str) -> dict:
    """Validate the 12 report envelopes. Never set release_ready or authorize G/H.

    Full timeline/geometry/semantic/media validation is an external checker contract.
    Relative spec/report/proof references are relative to the acceptance package.
    Original dependency bindings may be explicit external regular-file references.
    """
    root = root.resolve()
    job_path = file_path(root, "job.json")
    job_hash = sha256(job_path)
    job = load_json(job_path)
    package_file = file_path(root, evidence_name)
    base = package_file.parent
    snapshot = {job_path: job_hash, package_file: sha256(package_file)}
    video = file_path(root, video_name)
    profile = file_path(root, profile_name)
    snapshot.update({video: sha256(video), profile: sha256(profile)})
    acceptance = load_json(package_file)
    require(acceptance.get("schema") == "video-release-evidence-2.2", "acceptance_schema_invalid")
    for field in ("job_id", "revision_id"):
        require(nonempty(job.get(field)) and acceptance.get(field) == job[field], "acceptance_identity_mismatch")
    require(acceptance.get("video_sha256") == snapshot[video], "video_sha256_mismatch")
    require(acceptance.get("profile_sha256") == snapshot[profile], "profile_sha256_mismatch")
    spec_path = verify_ref(base, acceptance.get("spec"), snapshot=snapshot)
    spec = load_json(spec_path)
    require(spec.get("schema") == "video-production-spec-2.2", "spec_schema_invalid")
    for field in ("job_id", "revision_id", "content_kind", "visual_style"):
        require(nonempty(job.get(field)) and spec.get(field) == job[field], "spec_identity_mismatch")
    require(job.get("visual_style") in STYLE_BINDINGS, "visual_style_required")
    require(spec.get("producer_id") == job.get("producer_id"), "producer_identity_mismatch")
    bindings = spec.get("bindings")
    require(isinstance(bindings, dict), "bindings_missing")
    require(COMMON_BINDINGS | STYLE_BINDINGS[job["visual_style"]] <= set(bindings), "bindings_missing")
    hashes = {}
    for name, ref in bindings.items():
        verify_ref(base, ref, external=True, snapshot=snapshot)
        hashes[name] = ref["sha256"]
    requirements = spec.get("requirements")
    checks = acceptance.get("checks")
    require(isinstance(checks, dict) and set(checks) == set(CHECKS), "twelve_checks_required")
    require(isinstance(requirements, dict) and set(requirements) == set(CHECKS), "twelve_requirements_required")
    report_paths = set()
    frames = spec.get("media", {}).get("frames") if isinstance(spec.get("media"), dict) else None
    require(type(frames) is int and frames > 0, "actual_frame_count_required")
    for name in CHECKS:
        item = checks[name]
        require(isinstance(item, dict) and item.get("status") == "passed", "check_not_passed")
        report_path = verify_ref(base, item.get("report"), snapshot=snapshot)
        require(report_path not in report_paths, "separate_typed_reports_required")
        report_paths.add(report_path)
        report = load_json(report_path)
        require(report.get("schema") == "video-check-report-2.2" and report.get("check") == name,
                "report_type_mismatch")
        require(report.get("status") == "passed", "report_not_passed")
        require(report.get("spec_sha256") == acceptance["spec"]["sha256"], "report_spec_mismatch")
        for field in ("job_id", "revision_id", "video_sha256", "profile_sha256"):
            require(report.get(field) == acceptance[field], "report_binding_mismatch")
        require(report.get("bindings") == hashes, "report_dependencies_mismatch")
        review(report, spec.get("producer_id"), CHECK_CAPABILITIES[name])
        observations(base, report, requirements[name], snapshot)
        if name == "technical":
            results = report.get("results")
            keys = ("full_decode", "constant_pts", "frame_count", "audio_sync", "black_scan",
                    "color_range_matrix", "input_format_uniform", "encoded_boundary_comparison")
            require(isinstance(results, dict) and all(results.get(key) is True for key in keys),
                    "technical_results_pending")
            require(type(report.get("frames_scanned")) is int and report["frames_scanned"] == frames,
                    "technical_scan_incomplete")
        if name == "real_device_overlay":
            device = report.get("device")
            require(isinstance(device, dict) and device.get("actual_platform_playback") is True,
                    "actual_device_pending")
    recheck(snapshot)
    return {"evidence_bindings_valid": True, "release_ready": False,
            "production_checks": "pending", "external_checker_required": True}
