"""Design-stage provenance/coverage for spoken product identification; not perception."""
from pathlib import Path
from evidence import load_json,nonempty,require,verify_ref

def validate_spoken_callouts(root:Path,job:dict,state:dict,contract:dict,plan:dict,snapshot:dict)->None:
    ref=contract.get('spoken_product_callouts')
    require(isinstance(ref,dict),'spoken_callout_plan_missing')
    data=load_json(verify_ref(root,ref,snapshot=snapshot))
    require(data.get('schema')=='spoken-product-callouts-1' and data.get('status') in ('planned_for_render','locked'),'spoken_callout_plan_not_ready')
    require(data.get('job_id')==job['job_id'] and data.get('revision_id')==job['revision_id'],'spoken_callout_identity_mismatch')
    require(data.get('script_sha256')==state['inputs']['script']['sha256'],'spoken_callout_script_mismatch')
    source=verify_ref(root,state['inputs']['script'],external=True,snapshot=snapshot).read_text(encoding='utf-8')
    cues=data.get('callouts');require(isinstance(cues,list) and bool(cues),'spoken_callout_windows_missing')
    ids=[x.get('id') for x in cues if isinstance(x,dict)]
    require(len(ids)==len(cues) and all(nonempty(x) for x in ids) and len(ids)==len(set(ids)),'spoken_callout_ids_invalid')
    shots=plan['shots'];byid={x['shot_id']:x for x in shots};frames=plan.get('frames')
    require(type(frames) is int and frames>0,'spoken_callout_timeline_missing')
    for cue in cues:
        require(nonempty(cue.get('script_anchor')) and cue['script_anchor'] in source,'spoken_callout_source_anchor_missing')
        require(nonempty(cue.get('label_text')) and nonempty(cue.get('anchor_key')),'spoken_callout_label_missing')
        require(cue.get('representation') in ('physical_product','concept_diagram'),'spoken_callout_representation_invalid')
        nodes=cue.get('semantic_nodes')
        require(isinstance(nodes,list) and bool(nodes) and all(nonempty(x) for x in nodes) and len(nodes)==len(set(nodes)),'spoken_callout_nodes_missing')
        start,end=cue.get('start_frame'),cue.get('end_frame')
        require(type(start) is int and type(end) is int and 0<=start<end<=frames,'spoken_callout_window_invalid')
        shotids=cue.get('shot_ids')
        require(isinstance(shotids,list) and bool(shotids) and len(shotids)==len(set(shotids)) and all(x in byid for x in shotids),'spoken_callout_shots_invalid')
        ranges=[]
        for key in shotids:
            shot=byid[key];a,b=shot.get('start_frame'),shot.get('end_frame')
            require(type(a) is int and type(b) is int and 0<=a<b<=frames,'spoken_callout_shot_range_invalid')
            require(a<end and b>start,'spoken_callout_wrong_shot')
            ranges.append((max(start,a),min(end,b)))
        cursor=start
        for a,b in sorted(ranges):
            require(a<=cursor,'spoken_callout_coverage_gap');cursor=max(cursor,b)
        require(cursor>=end,'spoken_callout_coverage_gap')
        require(nonempty(cue.get('exit_condition')),'spoken_callout_exit_missing')
    # Completeness and whether a named point is truly visible remain semantic/encoded checks.
