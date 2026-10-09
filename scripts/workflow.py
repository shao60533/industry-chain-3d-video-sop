"""One local A-H job state; agents execute inside steps, gates control progression."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile

from evidence import (GateError, check_release_bindings, check_time, digest, file_path,
                      load_json, nonempty, observations, recheck, require, review, sha256, verify_ref)
from runtime import ROOT

VERSION = "video-workflow-1"
STEPS = tuple("ABCDEFGH")
CONTENT_KINDS = ("industry_chain", "earnings", "catalyst", "other")
VISUAL_STYLES = ("3d", "whiteboard")
APPROVAL_STEPS = {"C", "D", "E"}
INPUTS = {
    "A": {"source_full", "brief"}, "B": {"source_full", "brief"},
    "C": {"script", "font", "profile"}, "D": {"script", "voice_reference"},
    "E": {"script", "shot_plan", "audio", "timing", "font", "profile"},
    "F": {"script", "shot_plan", "audio", "timing", "font", "profile", "visual_project"}}
INPUT_PROVIDERS = {
    "B": {"source_full": ("A", "inputs", "source_full"), "brief": ("A", "inputs", "brief")},
    "C": {"script": ("B", "outputs", "script")},
    "D": {"script": ("B", "outputs", "script")},
    "E": {"script": ("B", "outputs", "script"), "shot_plan": ("C", "outputs", "shot_plan"),
          "audio": ("D", "outputs", "audio"), "timing": ("D", "outputs", "timing"),
          "font": ("C", "inputs", "font"), "profile": ("C", "inputs", "profile")}}
INPUT_PROVIDERS["F"] = {**INPUT_PROVIDERS["E"], "visual_project": ("E", "outputs", "visual_project")}
OUTPUTS = {
    "A": {"source_map", "research_notes"}, "B": {"script", "company_judgments", "question_answers"},
    "C": {"keyframes", "shot_plan", "design_lock"}, "D": {"voice_preview", "audio", "timing", "captions"},
    "E": {"visual_project", "opening_sample", "difficult_sample"}, "F": {"video", "layout"}}
CAPABILITIES = {"A": {"read_source"}, "B": {"read_source", "read_script"}, "C": {"view_images"},
                "D": {"listen_audio"}, "E": {"watch_video", "listen_audio", "view_images"}}
BASE_REQUIREMENTS = {
    "A": ["complete_source", "facts_units_dates", "scope_budget"],
    "B": ["source_script", "company_judgments", "question_answers", "same_source_exports"],
    "C": ["keyframes", "shot_methods", "deterministic_text", "no_recognizable_portraits", "font_layout"],
    "D": ["voice_identity", "numbers_names", "audio_timing"],
    "E": ["encoded_samples", "continuous_playback", "music_rhythm", "captions_focus", "masked_phone_sample"]}
STYLE_REQUIREMENTS = {
    "3d": {"C": ["assembly_reference", "functional_detail"],
           "E": ["real_explosion", "real_orbit", "real_reassembly", "saved_project_reopened"]},
    "whiteboard": {"C": ["chart_units_scale", "diagram_relations", "diagram_read_order"],
                   "E": ["progressive_reveal", "diagram_continuity", "editable_visual_project"]}}
RETURN_TO = {"fact_error": "A", "script_error": "B", "visual_error": "C",
             "audio_error": "D", "sample_error": "E"}
LOCAL_FAILURES = {"tool_error", "capability_missing", "cost_unknown", "permission_unknown"}
POLICY_FILES = ("scripts/workflow.py", "scripts/evidence.py", "docs/codex-workflow.md",
                "docs/production-sop.md", "docs/acceptance.md", "docs/publication-sop.md",
                "docs/component-scope-contract.md", "docs/visual-quality.md")


def policy_sha256() -> str:
    return digest({name: sha256(ROOT / name) for name in POLICY_FILES})


def valid_selection(content_kind: str, visual_style: str) -> bool:
    return content_kind in CONTENT_KINDS and visual_style in VISUAL_STYLES


def requirements(step: str, style: str) -> list[str]:
    require(step in BASE_REQUIREMENTS and style in VISUAL_STYLES, "step_or_style_invalid")
    return BASE_REQUIREMENTS[step] + STYLE_REQUIREMENTS[style].get(step, [])


def new_workflow() -> dict:
    return {"schema": VERSION, "policy_sha256": policy_sha256(),
            "steps": {step: {"state": "pending", "attempts": 0, "retries": 0,
                             "config_sha256": None, "inputs": {}, "outputs": {}, "evidence": None,
                             "failure": None, "blocker": None, "paused_from": None} for step in STEPS},
            "publication": {"status": "not_submitted", "attempt": None,
                            "receipt": None, "public_evidence": None}, "history": []}


def config_sha256(job: dict) -> str:
    return digest({key: value for key, value in job.items() if key != "workflow"})


def event(job: dict, name: str, step: str, **data) -> None:
    job["workflow"]["history"].append({"event": name, "step": step,
                                       "at": datetime.now(timezone.utc).isoformat(), **data})


def read_job(root: Path) -> dict:
    job = load_json(file_path(root, "job.json"))
    state = job.get("workflow")
    require(isinstance(state, dict) and state.get("schema") == VERSION, "workflow_migration_required")
    require(isinstance(state.get("steps"), dict) and set(state["steps"]) == set(STEPS), "workflow_steps_invalid")
    require(isinstance(state.get("history"), list) and isinstance(state.get("publication"), dict),
            "workflow_state_invalid")
    for entry in state["steps"].values():
        require(isinstance(entry, dict) and entry.get("state") in
                ("pending", "running", "generated", "accepted", "invalidated", "blocked", "paused"),
                "workflow_state_invalid")
        require(isinstance(entry.get("inputs"), dict) and isinstance(entry.get("outputs"), dict),
                "workflow_state_invalid")
        require(type(entry.get("retries")) is int and entry["retries"] >= 0 and
                type(entry.get("attempts")) is int and entry["attempts"] >= 0, "workflow_state_invalid")
    return job


def publication_read_only(root: Path, job: dict) -> bool:
    publication = job["workflow"]["publication"]
    # Even an old adapter's local attempt/result must prevent a new production run.
    receipts = (root / "H-publish").rglob("*.json")
    return (publication.get("status") != "not_submitted" or
            any(publication.get(key) is not None for key in ("attempt", "receipt", "public_evidence")) or
            any("attempt" in path.name.lower() or "result" in path.name.lower() for path in receipts))


def status(root: Path) -> dict:
    job = read_job(root)
    matches = job["workflow"]["policy_sha256"] == policy_sha256()
    read_only = publication_read_only(root, job)
    stale = refresh(root, job) if matches and not read_only else False
    return {"workflow": VERSION, "policy_matches": matches, "dependencies_stale": stale,
            "steps": {key: value["state"] for key, value in job["workflow"]["steps"].items()},
            "publication_status": job["workflow"]["publication"].get("status"),
            "read_only": read_only, "release_ready": False,
            "production_checks": "pending"}


def execution_allowed(root: Path, job: dict) -> None:
    constraints = job.get("execution_constraints")
    require(isinstance(constraints, dict), "execution_constraints_required")
    require(constraints.get("cost_status") == "no_paid_calls", "cost_unknown_or_paid_adapter_required")
    require(constraints.get("permission_status") == "authorized", "permission_unknown")
    verify_ref(root, constraints.get("evidence"))


def refs_from_manifest(root: Path, name: str, required: set[str], external: bool) -> dict:
    manifest = load_json(file_path(root, name))
    require(required <= set(manifest), "manifest_items_missing")
    for key, ref in manifest.items():
        require(nonempty(key) and "." not in key, "manifest_name_invalid")
        verify_ref(root, ref, external=external)
    return manifest


def validate_step(root: Path, job: dict, step: str, report_ref: dict) -> None:
    state = job["workflow"]["steps"][step]
    require(state["config_sha256"] == config_sha256(job), "job_config_changed")
    snapshot: dict[Path, str] = {}
    for field in ("inputs", "outputs"):
        require(bool(state[field]), "step_bindings_missing")
        for ref in state[field].values():
            verify_ref(root, ref, external=(field == "inputs"), snapshot=snapshot)
    report_path = verify_ref(root, report_ref, snapshot=snapshot)
    report = load_json(report_path)
    require(report.get("schema") == "video-step-evidence-1", "step_report_schema_invalid")
    require(report.get("status") == "passed", "step_report_not_passed")
    require(report.get("step") == step, "step_report_type_mismatch")
    for field in ("job_id", "revision_id"):
        require(report.get(field) == job[field], "step_report_identity_mismatch")
    require(report.get("config_sha256") == state["config_sha256"] and
            report.get("policy_sha256") == job["workflow"]["policy_sha256"], "step_report_version_mismatch")
    for field in ("inputs", "outputs"):
        require(report.get(field) == {key: ref["sha256"] for key, ref in state[field].items()},
                "step_report_binding_mismatch")
    review(report, job.get("producer_id"), CAPABILITIES[step])
    required = requirements(step, job["visual_style"])
    scope = report.get("scope")
    require(isinstance(scope, list) and all(nonempty(x) for x in scope) and set(required) <= set(scope),
            "scope_incomplete")
    observations(root, report, required, snapshot)
    if step in APPROVAL_STEPS:
        require(isinstance(report.get("approval"), dict), "approval_required")
        approval_path = verify_ref(root, report["approval"], snapshot=snapshot)
        approval = load_json(approval_path)
        require(approval.get("schema") == "video-step-approval-1" and approval.get("status") == "accepted",
                "approval_required")
        for field in ("step", "job_id", "revision_id", "config_sha256", "policy_sha256", "inputs", "outputs"):
            require(approval.get(field) == report[field], "approval_version_mismatch")
        approver = approval.get("approver")
        require(isinstance(approver, dict) and nonempty(approver.get("id")) and
                approver.get("role") in ("user", "delegated_reviewer"), "approver_required")
        require(approver["id"] != job["producer_id"], "self_review_is_not_approval")
        check_time(approval.get("approved_at"))
        verify_ref(root, approval.get("basis"), snapshot=snapshot)
    recheck(snapshot)


def invalidate(job: dict, step: str, code: str) -> None:
    previous = {}
    for key in STEPS[STEPS.index(step):]:
        state = job["workflow"]["steps"][key]
        if state["state"] != "pending":
            previous[key] = json.loads(json.dumps(state))
            state["state"] = "invalidated"
            state["blocker"] = code
    event(job, "invalidate", step, reason=code, previous=previous)


def refresh(root: Path, job: dict) -> bool:
    for step in STEPS:
        state = job["workflow"]["steps"][step]
        if state["state"] in ("pending", "invalidated") or not state["config_sha256"]:
            continue
        try:
            require(state["config_sha256"] == config_sha256(job), "job_config_changed")
            for field in ("inputs", "outputs"):
                for ref in state[field].values():
                    verify_ref(root, ref, external=(field == "inputs"))
            if state["evidence"] is not None:
                validate_step(root, job, step, state["evidence"])
        except GateError as exc:
            invalidate(job, step, str(exc))
            return True
    return False


@contextmanager
def locked(root: Path):
    path = root / ".workflow.lock"
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise GateError("workflow_busy") from exc
    try:
        os.close(descriptor)
        yield
    finally:
        path.unlink()


def save(root: Path, job: dict, original: bytes) -> None:
    path = root / "job.json"
    require(not path.is_symlink() and path.read_bytes() == original, "concurrent_job_change")
    content = (json.dumps(job, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    descriptor, name = tempfile.mkstemp(prefix=".workflow-", dir=root)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        require(path.read_bytes() == original, "concurrent_job_change")
        os.replace(temporary, path)
        require(path.read_bytes() == content, "job_readback_failed")
    finally:
        temporary.unlink(missing_ok=True)


def apply(root: Path, job: dict, action: str, step: str, **args) -> None:
    state = job["workflow"]["steps"][step]
    if action == "start":
        require(step in INPUTS, "external_adapter_required")
        require(state["state"] in ("pending", "invalidated") and state["failure"] is None,
                "step_not_startable")
        for previous in STEPS[:STEPS.index(step)]:
            require(job["workflow"]["steps"][previous]["state"] == "accepted", "previous_step_not_accepted")
        require(valid_selection(job.get("content_kind"), job.get("visual_style")), "content_and_style_required")
        for field in ("job_id", "revision_id", "topic", "producer_id"):
            require(nonempty(job.get(field)), "job_identity_required")
        execution_allowed(root, job)
        inputs = refs_from_manifest(root, args.get("manifest"), INPUTS[step], True)
        for key, (provider, field, item) in INPUT_PROVIDERS.get(step, {}).items():
            require(inputs[key]["sha256"] == job["workflow"]["steps"][provider][field][item]["sha256"],
                    "input_does_not_match_accepted_version")
        for previous in STEPS[:STEPS.index(step)]:
            prior = job["workflow"]["steps"][previous]
            inputs.update({f"{previous}.{key}": ref for key, ref in prior["outputs"].items()})
            inputs[f"{previous}.evidence"] = prior["evidence"]
        # The history retains all old bindings/evidence when work is restarted.
        event(job, "start", step, previous=json.loads(json.dumps(state)))
        state.update(state="running", inputs=inputs, outputs={}, evidence=None,
                     config_sha256=config_sha256(job), blocker=None, paused_from=None)
        state["attempts"] += 1
    elif action == "record":
        require(step in OUTPUTS and state["state"] == "running", "step_not_running")
        state["outputs"] = refs_from_manifest(root, args.get("manifest"), OUTPUTS[step], False)
        state["state"] = "generated"
        event(job, "generated", step, outputs=state["outputs"])
    elif action == "accept":
        require(step in CAPABILITIES, "external_checker_required")
        require(state["state"] == "generated", "step_not_generated")
        report_path = file_path(root, args.get("report"))
        ref = {"path": report_path.relative_to(root).as_posix(), "sha256": sha256(report_path)}
        validate_step(root, job, step, ref)
        state.update(state="accepted", evidence=ref)
        event(job, "accepted", step, evidence=ref)
    elif action == "pause":
        require(state["state"] in ("running", "generated"), "step_not_active")
        require(nonempty(args.get("reason")), "pause_reason_required")
        state.update(paused_from=state["state"], state="paused", blocker="paused")
        event(job, "pause", step, reason=args["reason"])
    elif action == "fail":
        require(state["state"] in ("running", "generated", "accepted"), "step_not_active")
        record_path = file_path(root, args.get("record"))
        record = load_json(record_path)
        require(record.get("schema") == "video-badcase-1", "badcase_schema_invalid")
        for field in ("job_id", "revision_id"):
            require(record.get(field) == job[field], "badcase_identity_mismatch")
        require(record.get("step") == step and record.get("config_sha256") == state["config_sha256"] and
                record.get("policy_sha256") == job["workflow"]["policy_sha256"], "badcase_version_mismatch")
        for field in ("inputs", "outputs"):
            require(record.get(field) == {key: ref["sha256"] for key, ref in state[field].items()},
                    "badcase_binding_mismatch")
        category = record.get("category")
        require(category in set(RETURN_TO) | LOCAL_FAILURES, "failure_category_invalid")
        for field in ("expected", "actual", "earliest_root_cause", "missed_check", "minimal_fix", "recovery_condition"):
            require(nonempty(record.get(field)), "badcase_detail_required")
        cases = record.get("regression_cases")
        require(isinstance(cases, list) and len(cases) >= 2 and all(nonempty(x) for x in cases) and
                {"original_failure", "previous_success"} <= set(cases), "regression_cases_required")
        proofs = record.get("artifacts")
        require(isinstance(proofs, list) and bool(proofs), "badcase_proof_required")
        for ref in proofs:
            verify_ref(root, ref)
        target = RETURN_TO.get(category, step)
        require(STEPS.index(target) <= STEPS.index(step), "failure_return_must_be_upstream")
        invalidate(job, target, category)
        job["workflow"]["steps"][target].update(state="blocked", failure={
            "category": category, "return_to": target, "recovery_condition": record["recovery_condition"],
            "regression_cases": cases,
            "record": {"path": record_path.relative_to(root).as_posix(), "sha256": sha256(record_path)}})
        event(job, "fail", step, return_to=target, category=category)
    elif action == "resume":
        require(state["state"] in ("paused", "blocked", "invalidated"), "step_not_resumable")
        if state["state"] == "paused":
            require(state["paused_from"] in ("running", "generated"), "pause_state_invalid")
            state.update(state=state["paused_from"], paused_from=None, blocker=None)
        elif state["failure"] is not None:
            require(state["retries"] < 1, "retry_limit")
            require(args.get("resolution") is not None, "recovery_required")
            failure = state["failure"]
            verify_ref(root, failure["record"])
            resolution_path = file_path(root, args["resolution"])
            resolution = load_json(resolution_path)
            require(resolution.get("schema") == "video-recovery-evidence-1" and resolution.get("status") == "passed",
                    "recovery_required")
            require(resolution.get("failure_sha256") == failure["record"]["sha256"] and
                    resolution.get("condition") == failure["recovery_condition"], "recovery_condition_mismatch")
            check_time(resolution.get("checked_at"))
            tests = resolution.get("tests")
            require(isinstance(tests, list) and all(isinstance(x, dict) and nonempty(x.get("case")) for x in tests),
                    "regression_missing")
            require(set(failure["regression_cases"]) <= {x["case"] for x in tests}, "regression_missing")
            for test in tests:
                require(test.get("status") == "passed", "regression_not_passed")
                require(isinstance(test.get("artifacts"), list) and bool(test["artifacts"]), "regression_proof_required")
                for ref in test["artifacts"]:
                    verify_ref(root, ref)
            execution_allowed(root, job)
            event(job, "recovery", step, failure=failure,
                  resolution={"path": resolution_path.relative_to(root).as_posix(), "sha256": sha256(resolution_path)})
            state.update(state="pending", failure=None, blocker=None, config_sha256=None,
                         inputs={}, outputs={}, evidence=None)
            state["retries"] += 1
        else:
            execution_allowed(root, job)
            event(job, "resume", step, previous=json.loads(json.dumps(state)))
            state.update(state="pending", blocker=None, config_sha256=None, inputs={}, outputs={}, evidence=None)
        event(job, "resume", step)
    else:
        raise GateError("action_invalid")


def transition(root: Path, action: str, step: str, **args) -> dict:
    root = root.resolve()
    require(step in STEPS, "step_invalid")
    with locked(root):
        original = (root / "job.json").read_bytes()
        job = read_job(root)
        require(not publication_read_only(root, job), "publication_read_only")
        require(job["workflow"].get("policy_sha256") == policy_sha256(), "policy_version_mismatch")
        if refresh(root, job):
            save(root, job, original)
            raise GateError("dependencies_changed")
        try:
            apply(root, job, action, step, **args)
        except GateError as exc:
            if action == "start" and str(exc) in ("cost_unknown_or_paid_adapter_required", "permission_unknown"):
                job["workflow"]["steps"][step].update(state="blocked", blocker=str(exc))
                event(job, "block", step, reason=str(exc))
                save(root, job, original)
            raise
        # A file replaced during a gate cannot become accepted in the saved job.
        require(not refresh(root, job), "dependencies_changed_during_transition")
        require(job["workflow"]["policy_sha256"] == policy_sha256(), "policy_version_mismatch")
        save(root, job, original)
    return status(root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("status")
    for action in ("start", "record", "accept", "pause", "fail", "resume"):
        command = commands.add_parser(action)
        command.add_argument("--step", choices=STEPS, required=True)
        if action in ("start", "record"):
            command.add_argument("--manifest", required=True)
        elif action == "accept":
            command.add_argument("--report", required=True)
        elif action == "pause":
            command.add_argument("--reason", required=True)
        elif action == "fail":
            command.add_argument("--record", required=True)
        else:
            command.add_argument("--resolution")
    check = commands.add_parser("check-release-bindings")
    check.add_argument("--evidence", required=True)
    check.add_argument("--video", required=True)
    check.add_argument("--profile", required=True)
    args = parser.parse_args()
    try:
        if args.action == "status":
            result = status(args.job)
        elif args.action == "check-release-bindings":
            result = check_release_bindings(args.job, args.evidence, args.video, args.profile)
        else:
            options = vars(args).copy()
            for key in ("job", "action", "step"):
                options.pop(key)
            result = transition(args.job, args.action, args.step, **options)
    except (GateError, OSError, ValueError, TypeError, KeyError) as exc:
        code = str(exc) if isinstance(exc, GateError) else "invalid_or_unreadable_state"
        print(json.dumps({"ok": False, "error": code, "release_ready": False}))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
