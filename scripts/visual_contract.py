"""Versioned design conditions; checks provenance/coverage, never judges realism."""
from pathlib import Path
from evidence import finite_number, load_json, nonempty, require, verify_ref
from spoken_callouts import validate_spoken_callouts


def validate_visual_contract(root: Path, job: dict, state: dict, snapshot: dict) -> None:
    contract = load_json(verify_ref(root, state['outputs']['visual_contract'], snapshot=snapshot))
    require(contract.get('schema') == 'video-visual-contract-1', 'visual_contract_schema_invalid')
    require(contract.get('status') == 'locked', 'visual_contract_not_locked')
    for key in ('job_id', 'revision_id', 'visual_style'):
        require(contract.get(key) == job.get(key), 'visual_contract_identity_mismatch')
    expected = {key: state['inputs'][key]['sha256'] for key in ('script', 'font', 'profile')}
    expected.update({key: state['outputs'][key]['sha256'] for key in ('keyframes', 'shot_plan', 'design_lock')})
    require(contract.get('bindings') == expected, 'visual_contract_bindings_mismatch')
    profile = load_json(verify_ref(root, state['inputs']['profile'], external=True, snapshot=snapshot))
    typography = contract.get('typography')
    keys = ('caption_alignment', 'caption_center_tolerance_px', 'caption_min_font_size',
            'caption_max_ink_width', 'caption_max_lines', 'caption_background', 'header_min_ink_y')
    require(isinstance(typography, dict) and all(k in profile and typography.get(k) == profile[k] for k in keys),
            'typography_not_bound_to_profile')
    require(profile['caption_alignment'] == 'canvas_center' and profile['caption_background'] == 'transparent',
            'typography_style_invalid')
    numeric_keys = ('caption_min_font_size', 'caption_center_tolerance_px', 'caption_max_ink_width', 'header_min_ink_y')
    require(all(finite_number(profile[k]) for k in numeric_keys),
            'typography_numeric_invalid')
    canvas, bounds = profile.get('canvas'), profile.get('critical_bounds')
    require(isinstance(canvas, list) and len(canvas) == 2 and
            all(finite_number(x) and x > 0 for x in canvas) and
            isinstance(bounds, list) and len(bounds) == 4 and
            all(finite_number(x) for x in bounds), 'typography_geometry_invalid')
    require(profile['caption_max_lines'] == 2 and profile['caption_min_font_size'] >= 42,
            'typography_readability_invalid')
    require(type(profile['caption_center_tolerance_px']) in (int, float) and 0 <= profile['caption_center_tolerance_px'] <= 2,
            'typography_center_tolerance_invalid')
    require(type(profile['caption_max_ink_width']) in (int, float) and 0 < profile['caption_max_ink_width'] <= profile['canvas'][0],
            'typography_width_invalid')
    require(type(profile['header_min_ink_y']) in (int, float) and bounds[1] <= profile['header_min_ink_y'] < bounds[3] <= canvas[1],
            'typography_header_invalid')
    proofs = contract.get('layout_proofs')
    require(isinstance(proofs, list) and bool(proofs), 'typography_proof_missing')
    for ref in proofs:
        verify_ref(root, ref, snapshot=snapshot)
    if job['visual_style'] != '3d':
        return
    references = contract.get('product_references')
    require(isinstance(references, list) and bool(references), 'product_reference_missing')
    for item in references:
        require(isinstance(item, dict) and nonempty(item.get('component_id')) and
                item.get('source_kind') in ('official_product', 'documented_principle'), 'product_reference_invalid')
        require(nonempty(item.get('source_locator')) and isinstance(item.get('applied_features'), list) and
                bool(item['applied_features']) and all(nonempty(x) for x in item['applied_features']), 'product_feature_application_missing')
        require(nonempty(item.get('claim_boundary')), 'product_claim_boundary_missing')
        for key in ('source_asset', 'reference_review', 'model_comparison'):
            verify_ref(root, item.get(key), snapshot=snapshot)
    plan = load_json(verify_ref(root, state['outputs']['shot_plan'], snapshot=snapshot))
    shots = plan.get('shots')
    require(isinstance(shots, list) and bool(shots) and all(isinstance(x, dict) and nonempty(x.get('shot_id')) for x in shots),
            'camera_shots_missing')
    ids = [x['shot_id'] for x in shots]
    require(len(ids) == len(set(ids)), 'camera_duplicate_shot')
    route = contract.get('camera_route')
    require(isinstance(route, list) and len(route) == len(ids) and
            all(isinstance(x, dict) for x in route) and [x.get('shot_id') for x in route] == ids, 'camera_route_coverage_missing')
    for index, item in enumerate(route):
        require(all(nonempty(item.get(k)) for k in ('observation_goal', 'focus_component', 'movement_reason', 'settle_reason')),
                'camera_observation_purpose_missing')
        require(item.get('strategy') in ('approach_open_inspect', 'function_follow', 'match_cut', 'purposeful_hold'),
                'camera_strategy_invalid')
        require(item.get('decorative_lateral_oscillation') is False, 'camera_decorative_oscillation')
        require(item.get('previous_shot_id') == (ids[index-1] if index else None), 'camera_handoff_identity_mismatch')
        require(nonempty(item.get('handoff_reason')), 'camera_handoff_reason_missing')
        verify_ref(root, item.get('route_proof'), snapshot=snapshot)

    validate_spoken_callouts(root,job,state,contract,plan,snapshot)
