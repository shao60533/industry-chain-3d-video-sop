"""Synthetic local evidence exercises gates; it is never film acceptance."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evidence
import init_job
import workflow


class WorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.prepare_job(Path(self.temporary.name) / "synthetic-job")

    def prepare_job(self, root: Path) -> None:
        self.root = root
        self.badcase_sequence = 0
        self.recovery_sequence = 0
        init_job.initialize(self.root)
        self.job = self.root / "job.json"
        data = self.read(self.job)
        data.update(topic="synthetic topic", content_kind="industry_chain", visual_style="whiteboard",
                    revision_id="synthetic-r1", producer_id="synthetic-producer")
        data["execution_constraints"] = {
            "cost_status": "no_paid_calls", "permission_status": "authorized",
            "evidence": self.file("A-reference/local-scope.txt", "synthetic local scope")}
        self.write(self.job, data)

    def read(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def write(self, path: Path, value: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")

    def file(self, name: str, text: str = "synthetic proof") -> dict:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return {"path": name, "sha256": evidence.sha256(path)}

    def step(self, step: str) -> dict:
        return self.read(self.job)["workflow"]["steps"][step]

    def run_action(self, action: str, step: str = "A", **kwargs) -> dict:
        return workflow.transition(self.root, action, step, **kwargs)

    def generate(self, step: str = "A") -> None:
        inputs = {key: self.file(f"inputs/{step}-{key}.txt") for key in workflow.INPUTS[step]}
        for key, (provider, field, item) in workflow.INPUT_PROVIDERS.get(step, {}).items():
            inputs[key] = self.step(provider)[field][item]
        if step == 'C':
            inputs['profile'] = {'path': 'C-design/safe-layout.json',
                                 'sha256': evidence.sha256(self.root / 'C-design/safe-layout.json')}
        self.write(self.root / "inputs.json", inputs)
        self.run_action("start", step, manifest="inputs.json")
        outputs = {key: self.file(f"outputs/{step}-{key}.txt") for key in workflow.OUTPUTS[step]}
        if step == 'C':
            self.write(self.root / outputs['shot_plan']['path'], {'frames':240,'shots':[{'shot_id':'synthetic-shot','start_frame':0,'end_frame':240}]})
            outputs['shot_plan']['sha256'] = evidence.sha256(self.root / outputs['shot_plan']['path'])
            profile = self.read(self.root / inputs['profile']['path'])
            proof = self.file('proofs/visual-node.txt', 'synthetic node proof, not a real visual review')
            contract = dict(schema='video-visual-contract-1', status='locked', job_id=self.read(self.job)['job_id'],
                            revision_id=self.read(self.job)['revision_id'], visual_style=self.read(self.job)['visual_style'],
                            bindings={k: inputs[k]['sha256'] for k in ('script', 'font', 'profile')},
                            typography={k: profile[k] for k in ('caption_alignment', 'caption_center_tolerance_px',
                                'caption_min_font_size', 'caption_max_ink_width', 'caption_max_lines', 'caption_background', 'header_min_ink_y')},
                            layout_proofs=[proof], product_references=[dict(component_id='synthetic-part',
                                source_kind='documented_principle', source_locator='synthetic fixture', applied_features=['synthetic feature'],
                                claim_boundary='not real CAD', source_asset=proof, reference_review=proof, model_comparison=proof)],
                            camera_route=[dict(shot_id='synthetic-shot', observation_goal='synthetic goal', focus_component='synthetic-part',
                                movement_reason='synthetic movement', settle_reason='read fixture', strategy='approach_open_inspect',
                                decorative_lateral_oscillation=False, previous_shot_id=None, handoff_reason='opening fixture', route_proof=proof)])
            calls=dict(schema='spoken-product-callouts-1',status='planned_for_render',job_id=self.read(self.job)['job_id'],revision_id=self.read(self.job)['revision_id'],script_sha256=inputs['script']['sha256'],callouts=[dict(id='synthetic-cue',script_anchor='synthetic proof',label_text='Synthetic part',anchor_key='synthetic-part',representation='physical_product',semantic_nodes=['synthetic-node'],start_frame=24,end_frame=120,shot_ids=['synthetic-shot'],exit_condition='fixture end')])
            self.write(self.root/'proofs/callouts.json',calls)
            contract['spoken_product_callouts']={'path':'proofs/callouts.json','sha256':evidence.sha256(self.root/'proofs/callouts.json')}
            contract['bindings'].update({k: outputs[k]['sha256'] for k in ('keyframes', 'shot_plan', 'design_lock')})
            self.write(self.root / outputs['visual_contract']['path'], contract)
            outputs['visual_contract']['sha256'] = evidence.sha256(self.root / outputs['visual_contract']['path'])
        if step == 'D':
            from speech_plan import plan
            script = (self.root / inputs['script']['path']).read_text(encoding='utf-8')
            speech = plan(script)
            speech.update(status='reviewed', bindings=dict(script_sha256=inputs['script']['sha256'],
                audio_sha256=outputs['audio']['sha256'],timing_sha256=outputs['timing']['sha256']))
            for unit in speech['units']:
                unit.update(boundary_review='passed',tempo_review='passed')
            proof=self.file('proofs/synthetic-listening.txt','synthetic test proof, never a real listening approval')
            speech['paragraph_listening']=[dict(paragraph_id=p,status='passed',continuous=True,start_seconds=i,end_seconds=i+1,evidence=proof)
                for i,p in enumerate(dict.fromkeys(u['paragraph_id'] for u in speech['units']))]
            self.write(self.root / outputs['speech_plan']['path'], speech)
            outputs['speech_plan']['sha256']=evidence.sha256(self.root / outputs['speech_plan']['path'])
        self.write(self.root / "outputs.json", outputs)
        self.run_action("record", step, manifest="outputs.json")

    def report(self, step: str = "A", approval: bool = True) -> str:
        state = self.step(step)
        job = self.read(self.job)
        requirements = workflow.requirements(step, job["visual_style"])
        proof = self.file(f"proofs/{step}.txt")
        report = {
            "schema": "video-step-evidence-1", "status": "passed", "step": step,
            "job_id": job["job_id"], "revision_id": job["revision_id"],
            "config_sha256": state["config_sha256"], "policy_sha256": job["workflow"]["policy_sha256"],
            "inputs": {key: ref["sha256"] for key, ref in state["inputs"].items()},
            "outputs": {key: ref["sha256"] for key, ref in state["outputs"].items()},
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "reviewer": {"id": job["producer_id"], "kind": "agent",
                         "capabilities": list(workflow.CAPABILITIES[step])},
            "review_mode": "self_review", "scope": requirements,
            "unchecked_scope": [], "blocking_findings": [],
            "observations": [{"id": item, "status": "passed", "detail": "synthetic observation",
                              "artifacts": [proof]} for item in requirements], "approval": None}
        if step in workflow.APPROVAL_STEPS and approval:
            decision = {
                "schema": "video-step-approval-1", "status": "accepted", "step": step,
                "job_id": job["job_id"], "revision_id": job["revision_id"],
                "inputs": report["inputs"], "outputs": report["outputs"],
                "config_sha256": report["config_sha256"], "policy_sha256": report["policy_sha256"],
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "approver": {"id": "synthetic-user", "role": "user"}, "basis": proof}
            name = f"proofs/{step}-approval.json"
            self.write(self.root / name, decision)
            report["approval"] = {"path": name, "sha256": evidence.sha256(self.root / name)}
        name = f"proofs/{step}-report.json"
        self.write(self.root / name, report)
        return name

    def accept(self, step: str = "A") -> None:
        self.run_action("accept", step, report=self.report(step))

    def test_initialization_keeps_all_checks_pending_and_one_state_source(self) -> None:
        data = self.read(self.job)
        self.assertEqual(set(data["workflow"]["steps"]), set("ABCDEFGH"))
        self.assertTrue(all(s["state"] == "pending" for s in data["workflow"]["steps"].values()))
        self.assertEqual(data["workflow"]["publication"]["status"], "not_submitted")
        self.assertFalse((self.root / "workflow.json").exists())
        self.assertFalse(data["acceptance"]["release_ready"])

    def test_audio_prosody_pending_missing_paragraph_or_changed_audio_cannot_accept(self) -> None:
        for step in 'ABC': self.generate(step); self.accept(step)
        self.generate('D'); ref=self.step('D')['outputs']['speech_plan']; path=self.root/ref['path']
        original=self.read(path)
        for kind in ('pending','coverage','binding','continuous','infinite_window','false_paragraph','context','duplicate_listening','huge_window'):
            value=copy.deepcopy(original)
            if kind=='pending':value['units'][0]['boundary_review']='pending'
            elif kind=='coverage':value['paragraph_listening']=[]
            elif kind=='binding':value['bindings']['audio_sha256']='old-audio'
            elif kind=='continuous':value['paragraph_listening'][0]['continuous']=False
            elif kind=='infinite_window':value['paragraph_listening'][0]['end_seconds']=float('inf')
            elif kind=='huge_window':value['paragraph_listening'][0]['end_seconds']=10**400
            elif kind=='false_paragraph':
                value['units'][0]['paragraph_id']='invented-paragraph'
                value['paragraph_listening'][0]['paragraph_id']='invented-paragraph'
            elif kind=='context':value['units'][0]['prior_context']='unrelated context'
            elif kind=='duplicate_listening':value['paragraph_listening'].append(copy.deepcopy(value['paragraph_listening'][0]))
            self.write(path,value);job=self.read(self.job)
            job['workflow']['steps']['D']['outputs']['speech_plan']['sha256']=evidence.sha256(path);self.write(self.job,job)
            with self.assertRaises(evidence.GateError):self.run_action('accept','D',report=self.report('D'))
        self.write(path,original);job=self.read(self.job)
        job['workflow']['steps']['D']['outputs']['speech_plan']['sha256']=evidence.sha256(path);self.write(self.job,job)
        self.accept('D')

    def test_card_uses_existing_state_and_is_read_only(self) -> None:
        original = self.job.read_bytes()
        result = workflow.card(self.root)
        self.assertEqual(result['current_step'], 'A')
        self.assertFalse(result['writes_state'])
        self.assertEqual(self.job.read_bytes(), original)
        self.assertFalse((self.root / 'workflow.json').exists())
        self.generate(); self.accept()
        self.assertEqual(workflow.card(self.root)['current_step'], 'B')

    def test_generated_requires_evidence_before_next_step_and_survives_reload(self) -> None:
        self.generate()
        self.assertEqual(self.step("A")["state"], "generated")
        with self.assertRaisesRegex(evidence.GateError, "previous_step_not_accepted"):
            self.run_action("start", "B", manifest="inputs.json")
        self.accept()
        self.assertEqual(self.step("A")["state"], "accepted")
        self.generate("B")
        self.assertIn("A.evidence", self.step("B")["inputs"])
        self.assertFalse(self.read(self.job)["acceptance"]["release_ready"])

    def test_missing_pending_wrong_identity_and_future_report_fail_closed(self) -> None:
        self.generate()
        with self.assertRaises(evidence.GateError):
            self.run_action("accept", report="proofs/missing.json")
        for field, value in (("status", "pending"), ("job_id", "other-job"),
                             ("checked_at", (datetime.now(timezone.utc) + timedelta(days=1)).isoformat())):
            name = self.report()
            report = self.read(self.root / name)
            report[field] = value
            self.write(self.root / name, report)
            with self.assertRaises(evidence.GateError):
                self.run_action("accept", report=name)
            self.assertEqual(self.step("A")["state"], "generated")
        self.accept()

    def test_input_change_invalidates_accepted_step_and_downstream_without_erasing_history(self) -> None:
        self.generate()
        self.accept()
        self.generate("B")
        (self.root / "inputs/A-source_full.txt").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(evidence.GateError, "dependencies_changed"):
            self.run_action("accept", "B", report=self.report("B"))
        self.assertEqual(self.step("A")["state"], "invalidated")
        self.assertEqual(self.step("B")["state"], "invalidated")
        self.assertIsNotNone(self.step("A")["evidence"])
        self.assertEqual(self.read(self.job)["workflow"]["history"][-1]["event"], "invalidate")

    def test_next_stage_cannot_swap_an_unapproved_script(self) -> None:
        for step in "AB":
            self.generate(step)
            self.accept(step)
        inputs = {key: self.file(f"inputs/unapproved-{key}.txt", "unapproved content")
                  for key in workflow.INPUTS["C"]}
        self.write(self.root / "inputs.json", inputs)
        with self.assertRaisesRegex(evidence.GateError, "input_does_not_match_accepted_version"):
            self.run_action("start", "C", manifest="inputs.json")
        self.assertEqual(self.step("C")["state"], "pending")

    def test_both_styles_use_same_stages_and_stop_at_external_film_checker(self) -> None:
        for style, kind in (("whiteboard", "industry_chain"), ("3d", "earnings")):
            with self.subTest(style=style):
                # Each combination gets a fresh task; no acceptance crosses tasks.
                root = self.root / style
                init_job.initialize(root, content_kind=kind, visual_style=style)
                old_root, old_job = self.root, self.job
                self.root, self.job = root, root / "job.json"
                try:
                    job = self.read(self.job)
                    job.update(topic="synthetic", producer_id="synthetic-producer", revision_id="synthetic-r1")
                    job["execution_constraints"] = {"cost_status": "no_paid_calls", "permission_status": "authorized",
                                                    "evidence": self.file("A-reference/scope.txt")}
                    self.write(self.job, job)
                    for step in "ABCDE":
                        self.generate(step)
                        self.accept(step)
                    self.generate("F")
                    with self.assertRaisesRegex(evidence.GateError, "external_checker_required"):
                        self.run_action("accept", "F", report="not-used.json")
                    for step in "GH":
                        with self.assertRaisesRegex(evidence.GateError, "external_adapter_required"):
                            self.run_action("start", step, manifest="not-used.json")
                    self.assertFalse(workflow.status(self.root)["release_ready"])
                finally:
                    self.root, self.job = old_root, old_job

    def test_proof_change_invalidates_acceptance(self) -> None:
        self.generate()
        self.accept()
        (self.root / "proofs/A.txt").write_text("different proof", encoding="utf-8")
        with self.assertRaisesRegex(evidence.GateError, "dependencies_changed"):
            self.run_action("start", "B", manifest="inputs.json")
        self.assertEqual(self.step("A")["state"], "invalidated")

    def test_content_and_style_are_independent_and_keyframe_approval_is_version_bound(self) -> None:
        for kind in workflow.CONTENT_KINDS:
            for style in workflow.VISUAL_STYLES:
                self.assertTrue(workflow.valid_selection(kind, style))
        for step in "AB":
            self.generate(step)
            self.accept(step)
        self.generate("C")
        self.assertIn("diagram_read_order", workflow.requirements("C", "whiteboard"))
        self.assertNotIn("assembly_reference", workflow.requirements("C", "whiteboard"))
        with self.assertRaisesRegex(evidence.GateError, "approval_required"):
            self.run_action("accept", "C", report=self.report("C", approval=False))
        name = self.report("C")
        report = self.read(self.root / name)
        approval = self.root / report["approval"]["path"]
        decision = self.read(approval)
        decision["outputs"]["keyframes"] = "0" * 64
        self.write(approval, decision)
        report["approval"]["sha256"] = evidence.sha256(approval)
        self.write(self.root / name, report)
        with self.assertRaisesRegex(evidence.GateError, "approval_version_mismatch"):
            self.run_action("accept", "C", report=name)
        self.accept("C")

    def test_self_review_cannot_claim_independent_review(self) -> None:
        self.generate()
        name = self.report()
        report = self.read(self.root / name)
        report["review_mode"] = "independent"
        self.write(self.root / name, report)
        with self.assertRaisesRegex(evidence.GateError, "false_independent_review"):
            self.run_action("accept", report=name)

    def test_visual_nodes_missing_or_pending_cannot_advance(self) -> None:
        for step in 'AB':
            self.generate(step); self.accept(step)
        self.generate('C')
        for change in ('missing', 'pending'):
            name = self.report('C'); report = self.read(self.root / name)
            if change == 'missing':
                report['observations'] = [x for x in report['observations'] if x['id'] != 'typography_layout_lock']
            else:
                next(x for x in report['observations'] if x['id'] == 'typography_layout_lock')['status'] = 'pending'
            self.write(self.root / name, report)
            with self.assertRaises(evidence.GateError): self.run_action('accept', 'C', report=name)
            self.assertEqual(self.step('C')['state'], 'generated')

    def test_changed_nested_reference_invalidates_accepted_design(self) -> None:
        job = self.read(self.job); job['visual_style'] = '3d'; self.write(self.job, job)
        for step in 'ABC':
            self.generate(step); self.accept(step)
        (self.root / 'proofs/visual-node.txt').write_text('changed reference', encoding='utf-8')
        self.assertTrue(workflow.status(self.root)['dependencies_stale'])

    def test_decorative_camera_motion_is_rejected(self) -> None:
        job = self.read(self.job); job['visual_style'] = '3d'; self.write(self.job, job)
        for step in 'AB': self.generate(step); self.accept(step)
        self.generate('C')
        state = self.step('C'); ref = state['outputs']['visual_contract']; file = self.root / ref['path']
        contract = self.read(file); contract['camera_route'][0]['decorative_lateral_oscillation'] = True
        self.write(file, contract)
        job = self.read(self.job); job['workflow']['steps']['C']['outputs']['visual_contract']['sha256'] = evidence.sha256(file)
        self.write(self.job, job)
        with self.assertRaisesRegex(evidence.GateError, 'camera_decorative_oscillation'):
            self.run_action('accept', 'C', report=self.report('C'))

    def prepare_callout_design(self):
        job=self.read(self.job);job['visual_style']='3d';self.write(self.job,job)
        for step in ['A','B']:
            self.generate(step);self.accept(step)
        self.generate('C')
        return self.step('C'),self.read(self.job)

    def test_missing_spoken_callout_plan_blocks_design(self):
        from visual_contract import validate_visual_contract
        state,job=self.prepare_callout_design();file=self.root/state['outputs']['visual_contract']['path'];data=self.read(file)
        data.pop('spoken_product_callouts');self.write(file,data);state['outputs']['visual_contract']['sha256']=evidence.sha256(file)
        with self.assertRaisesRegex(evidence.GateError,'spoken_callout_plan_missing'):
            validate_visual_contract(self.root,job,state,{})

    def test_bad_spoken_callout_mapping_blocks_design(self):
        from visual_contract import validate_visual_contract
        state,job=self.prepare_callout_design();file=self.root/state['outputs']['visual_contract']['path'];contract=self.read(file);ref=contract['spoken_product_callouts'];calls=self.root/ref['path'];original=self.read(calls)
        mutations=[('source_anchor','spoken_callout_source_anchor_missing'),('wrong_shot','spoken_callout_shots_invalid'),('empty_nodes','spoken_callout_nodes_missing'),('bad_frame','spoken_callout_window_invalid'),('empty_labels','spoken_callout_label_missing'),('stale_script','spoken_callout_script_mismatch')]
        for kind,error in mutations:
            with self.subTest(kind=kind):
                data=json.loads(json.dumps(original));cue=data['callouts'][0]
                if kind=='source_anchor':cue['script_anchor']='never in the current source'
                if kind=='wrong_shot':cue['shot_ids']=['unknown']
                if kind=='empty_nodes':cue['semantic_nodes']=[]
                if kind=='bad_frame':cue['start_frame']=True
                if kind=='empty_labels':cue['label_text']=''
                if kind=='stale_script':data['script_sha256']='0'*64
                self.write(calls,data);contract['spoken_product_callouts']['sha256']=evidence.sha256(calls);self.write(file,contract);state['outputs']['visual_contract']['sha256']=evidence.sha256(file)
                with self.assertRaisesRegex(evidence.GateError,error):validate_visual_contract(self.root,job,state,{})

    def test_approved_callout_plan_change_invalidates_design(self):
        self.prepare_callout_design();self.accept('C');file=self.root/'proofs/callouts.json';data=self.read(file);data['callouts'][0]['label_text']='Changed label';self.write(file,data)
        status=workflow.status(self.root);self.assertTrue(status['dependencies_stale']);self.assertEqual(status['steps']['C'],'invalidated')

    def test_visual_contract_missing_conditions_fail_closed(self) -> None:
        from visual_contract import validate_visual_contract
        job = self.read(self.job); job['visual_style'] = '3d'; self.write(self.job, job)
        for step in 'AB': self.generate(step); self.accept(step)
        self.generate('C')
        job = self.read(self.job); state = job['workflow']['steps']['C']
        file = self.root / state['outputs']['visual_contract']['path']; original = self.read(file)
        cases = [('product_references', [], 'product_reference_missing'),
                 ('camera_route', [], 'camera_route_coverage_missing'),
                 ('layout_proofs', [], 'typography_proof_missing'),
                 ('status', 'pending', 'visual_contract_not_locked')]
        for key, value, error in cases:
            with self.subTest(condition=key):
                changed = dict(original, **{key: value}); self.write(file, changed)
                state['outputs']['visual_contract']['sha256'] = evidence.sha256(file)
                with self.assertRaisesRegex(evidence.GateError, error):
                    validate_visual_contract(self.root, job, state, {})

    def test_nonfinite_or_nonnumeric_profile_cannot_lock_design(self) -> None:
        from visual_contract import validate_visual_contract
        for step in 'AB': self.generate(step); self.accept(step)
        self.generate('C')
        job = self.read(self.job); state = job['workflow']['steps']['C']
        file = self.root / state['outputs']['visual_contract']['path']; original = self.read(file)
        profile_file = self.root / state['inputs']['profile']['path']; profile = self.read(profile_file)
        for value in ('56', True, float('inf'), 10**400):
            with self.subTest(value=value):
                changed_profile = dict(profile, caption_min_font_size=value); self.write(profile_file, changed_profile)
                state['inputs']['profile']['sha256'] = evidence.sha256(profile_file)
                contract = copy.deepcopy(original)
                contract['bindings']['profile'] = state['inputs']['profile']['sha256']
                contract['typography']['caption_min_font_size'] = value; self.write(file, contract)
                state['outputs']['visual_contract']['sha256'] = evidence.sha256(file)
                with self.assertRaisesRegex(evidence.GateError, 'typography_numeric_invalid|nonfinite_json_number'):
                    validate_visual_contract(self.root, job, state, {})

    def test_pause_resume_rechecks_inputs(self) -> None:
        self.generate()
        self.run_action("pause", reason="local pause")
        self.assertEqual(self.step("A")["state"], "paused")
        self.run_action("resume")
        self.assertEqual(self.step("A")["state"], "generated")
        self.run_action("pause", reason="local pause")
        (self.root / "inputs/A-brief.txt").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(evidence.GateError, "dependencies_changed"):
            self.run_action("resume")

    def revoke_execution_evidence(self, *, delete: bool = False) -> None:
        ref = self.read(self.job)["execution_constraints"]["evidence"]
        path = self.root / ref["path"]
        if delete:
            path.unlink()
        else:
            path.write_text("synthetic revoked scope", encoding="utf-8")

    def test_authorization_revoked_after_start_prevents_output_recording(self) -> None:
        inputs = {key: self.file(f"inputs/{key}.txt") for key in workflow.INPUTS["A"]}
        self.write(self.root / "inputs.json", inputs)
        self.run_action("start", manifest="inputs.json")
        outputs = {key: self.file(f"outputs/{key}.txt") for key in workflow.OUTPUTS["A"]}
        self.write(self.root / "outputs.json", outputs)
        self.revoke_execution_evidence(delete=True)
        with self.assertRaisesRegex(evidence.GateError, "dependencies_changed"):
            self.run_action("record", manifest="outputs.json")
        self.assertEqual(self.step("A")["state"], "invalidated")

    def test_authorization_revoked_after_generation_prevents_acceptance(self) -> None:
        self.generate()
        self.revoke_execution_evidence(delete=True)
        before = self.job.read_bytes()
        summary = workflow.status(self.root)
        self.assertTrue(summary["dependencies_stale"])
        self.assertEqual(summary["steps"]["A"], "invalidated")
        self.assertEqual(self.job.read_bytes(), before)
        with self.assertRaisesRegex(evidence.GateError, "dependencies_changed"):
            self.accept()
        self.assertEqual(self.step("A")["state"], "invalidated")
        self.assertFalse(workflow.status(self.root)["release_ready"])

    def test_authorization_changed_after_acceptance_invalidates_downstream(self) -> None:
        self.generate()
        self.accept()
        self.generate("B")
        self.revoke_execution_evidence()
        self.assertTrue(workflow.status(self.root)["dependencies_stale"])
        with self.assertRaisesRegex(evidence.GateError, "dependencies_changed"):
            self.accept("B")
        self.assertEqual(self.step("A")["state"], "invalidated")
        self.assertEqual(self.step("B")["state"], "invalidated")

    def test_authorization_changed_during_pause_prevents_resume(self) -> None:
        self.generate()
        self.run_action("pause", reason="synthetic pause")
        self.revoke_execution_evidence()
        with self.assertRaisesRegex(evidence.GateError, "dependencies_changed"):
            self.run_action("resume")
        self.assertEqual(self.step("A")["state"], "invalidated")

    def badcase(self, category: str = "tool_error", step: str = "A") -> str:
        self.badcase_sequence += 1
        name = f"proofs/{step}-badcase-{self.badcase_sequence}.json"
        job = self.read(self.job)
        state = self.step(step)
        self.write(self.root / name, {
            "schema": "video-badcase-1", "job_id": job["job_id"], "revision_id": job["revision_id"],
            "step": step, "config_sha256": state["config_sha256"], "policy_sha256": job["workflow"]["policy_sha256"],
            "inputs": {key: ref["sha256"] for key, ref in state["inputs"].items()},
            "outputs": {key: ref["sha256"] for key, ref in state["outputs"].items()},
            "category": category, "expected": "synthetic expected",
            "actual": "synthetic actual", "earliest_root_cause": "synthetic cause",
            "missed_check": "synthetic missed check", "minimal_fix": "synthetic fix",
            "regression_cases": ["original_failure", "previous_success"],
            "recovery_condition": "synthetic corrected tool", "artifacts": [self.file("proofs/failure.txt")]})
        return name

    def recovery(self) -> str:
        failure = self.step("A")["failure"]
        self.recovery_sequence += 1
        name = f"proofs/recovery-{self.recovery_sequence}.json"
        self.write(self.root / name, {
            "schema": "video-recovery-evidence-1", "status": "passed",
            "failure_sha256": failure["record"]["sha256"],
            "condition": failure["recovery_condition"],
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "tests": [{"case": item, "status": "passed", "artifacts": [self.file(f"proofs/{item}.txt")]}
                      for item in ["original_failure", "previous_success"]]})
        return name

    def test_badcase_requires_original_and_success_regressions_and_limits_retry(self) -> None:
        self.generate()
        self.run_action("fail", record=self.badcase())
        self.assertEqual(self.step("A")["state"], "blocked")
        with self.assertRaisesRegex(evidence.GateError, "recovery_required"):
            self.run_action("resume")
        name = self.recovery()
        recovery = self.read(self.root / name)
        recovery["tests"] = recovery["tests"][:1]
        self.write(self.root / name, recovery)
        with self.assertRaisesRegex(evidence.GateError, "regression_missing"):
            self.run_action("resume", resolution=name)
        self.run_action("resume", resolution=self.recovery())
        self.generate()
        self.run_action("fail", record=self.badcase())
        with self.assertRaisesRegex(evidence.GateError, "retry_limit"):
            self.run_action("resume", resolution=self.recovery())

    def test_active_recovery_dependencies_remain_required_across_all_resume_states(self) -> None:
        dependencies = ("badcase", "recovery", "original_failure", "previous_success", "failure_proof")
        for phase in ("pending", "generated", "accepted", "paused"):
            for dependency in dependencies:
                with self.subTest(phase=phase, dependency=dependency):
                    self.prepare_job(Path(self.temporary.name) / f"{phase}-{dependency}")
                    self.generate()
                    self.run_action("fail", record=self.badcase())
                    failure = self.step("A")["failure"]
                    resolution = self.recovery()
                    self.run_action("resume", resolution=resolution)
                    if phase != "pending":
                        self.generate()
                    if phase == "accepted":
                        self.accept()
                    elif phase == "paused":
                        self.run_action("pause", reason="synthetic pause")
                    paths = {"badcase": failure["record"]["path"], "recovery": resolution,
                             "original_failure": "proofs/original_failure.txt",
                             "previous_success": "proofs/previous_success.txt",
                             "failure_proof": "proofs/failure.txt"}
                    (self.root / paths[dependency]).unlink()
                    summary = workflow.status(self.root)
                    self.assertTrue(summary["dependencies_stale"])
                    self.assertEqual(summary["steps"]["A"], "invalidated")
                    with self.assertRaisesRegex(evidence.GateError, "dependencies_changed"):
                        if phase == "pending":
                            self.generate()
                        elif phase == "generated":
                            self.accept()
                        elif phase == "accepted":
                            self.generate("B")
                        else:
                            self.run_action("resume")
                    self.assertEqual(self.step("A")["state"], "invalidated")
                    self.assertFalse(workflow.status(self.root)["release_ready"])

    def test_recovery_proof_modified_after_resume_cannot_support_new_work(self) -> None:
        self.generate()
        self.run_action("fail", record=self.badcase())
        self.run_action("resume", resolution=self.recovery())
        (self.root / "proofs/previous_success.txt").write_text("synthetic changed result", encoding="utf-8")
        with self.assertRaisesRegex(evidence.GateError, "dependencies_changed"):
            self.generate()

    def test_original_failure_proof_is_checked_before_failure_can_be_resumed(self) -> None:
        self.generate()
        self.run_action("fail", record=self.badcase())
        resolution = self.recovery()
        (self.root / "proofs/failure.txt").unlink()
        with self.assertRaises(evidence.GateError):
            self.run_action("resume", resolution=resolution)
        self.assertEqual(self.step("A")["state"], "blocked")

    def test_failure_flows_to_earliest_step_with_version_bound_badcase(self) -> None:
        for step in "AB":
            self.generate(step)
            self.accept(step)
        self.generate("C")
        name = self.badcase("script_error", "C")
        self.run_action("fail", "C", record=name)
        self.assertEqual(self.step("B")["state"], "blocked")
        self.assertEqual(self.step("C")["state"], "invalidated")
        self.assertEqual(self.step("B")["failure"]["return_to"], "B")
        self.assertEqual(self.step("A")["state"], "accepted")

    def test_changed_job_config_does_not_inherit_previous_acceptance(self) -> None:
        self.generate()
        self.accept()
        job = self.read(self.job)
        job["visual_style"] = "3d"
        self.write(self.job, job)
        before = self.job.read_bytes()
        summary = workflow.status(self.root)
        self.assertTrue(summary["dependencies_stale"])
        self.assertEqual(summary["steps"]["A"], "invalidated")
        self.assertEqual(self.job.read_bytes(), before)
        with self.assertRaisesRegex(evidence.GateError, "dependencies_changed"):
            self.run_action("start", "B", manifest="inputs.json")

    def test_initialized_task_is_never_replaced_by_second_initialize(self) -> None:
        self.generate()
        self.accept()
        before = self.job.read_bytes()
        with self.assertRaises(ValueError):
            init_job.initialize(self.root, content_kind="earnings", visual_style="3d")
        self.assertEqual(self.job.read_bytes(), before)

    def test_unknown_cost_and_permission_block_without_external_calls(self) -> None:
        for field, value in (("cost_status", "unknown"), ("permission_status", "unknown")):
            job = self.read(self.job)
            job["execution_constraints"][field] = value
            self.write(self.job, job)
            with self.assertRaises(evidence.GateError):
                self.generate()
            self.assertEqual(self.step("A")["state"], "blocked")
            job = self.read(self.job)
            job["execution_constraints"].update(cost_status="no_paid_calls", permission_status="authorized")
            self.write(self.job, job)
            self.run_action("resume")

    def test_policy_drift_and_unknown_submission_are_read_only(self) -> None:
        job = self.read(self.job)
        job["workflow"]["policy_sha256"] = "0" * 64
        self.write(self.job, job)
        before = self.job.read_bytes()
        self.assertEqual(workflow.status(self.root)["publication_status"], "not_submitted")
        with self.assertRaisesRegex(evidence.GateError, "policy_version_mismatch"):
            self.generate()
        self.assertEqual(self.job.read_bytes(), before)
        job["workflow"]["policy_sha256"] = workflow.policy_sha256()
        job["workflow"]["publication"]["status"] = "submission_unknown"
        self.write(self.job, job)
        before = self.job.read_bytes()
        for action in ("start", "record", "accept", "pause", "resume", "fail"):
            with self.assertRaisesRegex(evidence.GateError, "publication_read_only"):
                self.run_action(action)
        self.assertEqual(self.job.read_bytes(), before)
        self.assertEqual(workflow.status(self.root)["publication_status"], "submission_unknown")

    def test_existing_attempt_file_forces_read_only(self) -> None:
        self.file("H-publish/attempt.json")
        with self.assertRaisesRegex(evidence.GateError, "publication_read_only"):
            self.generate()

    def test_lock_cannot_be_stolen_and_failed_mutation_preserves_state(self) -> None:
        self.file(".workflow.lock")
        before = self.job.read_bytes()
        with self.assertRaisesRegex(evidence.GateError, "workflow_busy"):
            self.run_action("pause", reason="pause")
        self.assertEqual(self.job.read_bytes(), before)

    def test_new_publication_receipt_during_gate_prevents_state_commit(self) -> None:
        for kind in ("attempt", "result"):
            with self.subTest(kind=kind):
                self.prepare_job(Path(self.temporary.name) / f"receipt-{kind}")
                self.generate()
                before = self.job.read_bytes()
                original_apply = workflow.apply
                def receipt_created_after_apply(*args, **kwargs):
                    original_apply(*args, **kwargs)
                    self.file(f"H-publish/{kind}.json", "synthetic receipt; no publishing")
                with patch.object(workflow, "apply", side_effect=receipt_created_after_apply):
                    with self.assertRaisesRegex(evidence.GateError, "publication_read_only"):
                        self.accept()
                self.assertEqual(self.job.read_bytes(), before)
                self.assertEqual(self.step("A")["state"], "generated")
                self.assertTrue(workflow.status(self.root)["read_only"])

    def test_shared_job_lock_excludes_workflow_and_future_receipt_writers(self) -> None:
        before = self.job.read_bytes()
        with workflow.locked(self.root):
            with self.assertRaisesRegex(evidence.GateError, "workflow_busy"):
                self.run_action("start", manifest="unused.json")
        self.assertEqual(self.job.read_bytes(), before)
        self.assertFalse((self.root / ".workflow.lock").exists())

    def test_receipt_created_at_save_boundary_also_blocks_invalidation_writes(self) -> None:
        for action in ("accept", "invalidate"):
            with self.subTest(action=action):
                self.prepare_job(Path(self.temporary.name) / f"save-{action}")
                self.generate()
                if action == "invalidate":
                    self.accept()
                    (self.root / "inputs/A-source_full.txt").write_text("synthetic input change", encoding="utf-8")
                before = self.job.read_bytes()
                original_save = workflow.save
                def receipt_created_before_save(*args, **kwargs):
                    self.file("H-publish/attempt.json", "synthetic receipt; no publishing")
                    original_save(*args, **kwargs)
                with patch.object(workflow, "save", side_effect=receipt_created_before_save):
                    with self.assertRaisesRegex(evidence.GateError, "publication_read_only"):
                        if action == "accept":
                            self.accept()
                        else:
                            self.run_action("start", "B", manifest="unused.json")
                self.assertEqual(self.job.read_bytes(), before)
                self.assertTrue(workflow.status(self.root)["read_only"])

    def test_cli_only_outputs_safe_state_summary(self) -> None:
        result = subprocess.run([sys.executable, str(workflow.ROOT / "scripts/workflow.py"),
                                 "--job", str(self.root), "status"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["steps"]["A"], "pending")
        self.assertNotIn(str(self.root), result.stdout)


if __name__ == "__main__":
    unittest.main()
