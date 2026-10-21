"""Plan semantic TTS units and bind real prosody review; never asserts listening."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from evidence import finite_number, load_json, require, verify_ref

def paragraphs(text: str) -> list[str]:
    lines = text.replace('\r\n', '\n').splitlines()
    body = '\n'.join('' if re.match(r'^ {0,3}#{1,6}(?:\s|$)', line) else line for line in lines)
    return [paragraph.strip() for paragraph in re.split(r'\n\s*\n', body) if paragraph.strip()]

def plan(text: str, maximum: int = 180) -> dict:
    """Keep complete paragraphs when possible, never cut an arbitrary character count."""
    if type(maximum) is not int or maximum <= 0:
        raise ValueError('speech_maximum_invalid')
    units=[]
    for pi, paragraph in enumerate(paragraphs(text)):
        sentences=re.findall(r'[^。！？]*[。！？]+[”’」』）)]*|[^。！？]+$', paragraph)
        grouped=[];buffer=''
        for sentence in sentences:
            if buffer and len(buffer+sentence)>maximum: grouped.append(buffer);buffer=''
            buffer+=sentence
        if buffer:grouped.append(buffer)
        offset=0
        for ui,group in enumerate(grouped):
            units.append(dict(id=f'p{pi:03d}-{ui:02d}',paragraph_id=f'p{pi:03d}',text=group,
                prior_context=paragraph[:offset],
                next_context=paragraph[offset+len(group):],
                boundary_reason='paragraph_end' if ui==len(grouped)-1 else 'complete_sentence',
                boundary_review='pending',tempo_review='pending',
                long_unit_warning=len(group)>maximum))
            offset+=len(group)
    return dict(schema='video-speech-plan-1',status='planned_pending_listening',units=units,
                cache_dependencies=['original_text','spoken_text','prior_context','next_context','voice_sha256','speed','seed','pause_policy'],
                pause_policy='semantic_target_minus_measured_existing_edge_silence',paragraph_listening=[])

def validate_speech_plan(root: Path, job: dict, state: dict, snapshot: dict) -> None:
    value=load_json(verify_ref(root,state['outputs']['speech_plan'],snapshot=snapshot))
    require(value.get('schema')=='video-speech-plan-1' and value.get('status')=='reviewed','speech_plan_not_reviewed')
    expected=dict(script_sha256=state['inputs']['script']['sha256'],audio_sha256=state['outputs']['audio']['sha256'],timing_sha256=state['outputs']['timing']['sha256'])
    require(value.get('bindings')==expected,'speech_plan_binding_mismatch')
    units=value.get('units');require(isinstance(units,list) and bool(units),'speech_units_missing')
    script=verify_ref(root,state['inputs']['script'],external=True,snapshot=snapshot).read_text(encoding='utf-8')
    normalize=lambda x:re.sub(r'\s+','',x)
    require(all(isinstance(u,dict) and isinstance(u.get('text'),str) for u in units),'speech_unit_invalid')
    require(normalize(''.join(u['text'] for u in units))==normalize(''.join(paragraphs(script))),'speech_plan_text_coverage')
    require(all(isinstance(u.get('id'),str) and u['id'].strip() and isinstance(u.get('paragraph_id'),str) and u['paragraph_id'].strip() for u in units)
            and len({u.get('id') for u in units})==len(units),'speech_unit_duplicate')
    require(all(u.get('boundary_review')=='passed' and u.get('tempo_review')=='passed' and
                u.get('boundary_reason') in ('paragraph_end','complete_sentence','approved_semantic_clause') for u in units), 'speech_boundary_or_tempo_pending')
    source_paragraphs=[normalize(p) for p in paragraphs(script)]
    paragraph_index=0;offset=0
    for unit in units:
        require(paragraph_index<len(source_paragraphs),'speech_paragraph_mapping_invalid')
        source=source_paragraphs[paragraph_index];text=normalize(unit['text'])
        require(bool(text) and unit['paragraph_id']==f'p{paragraph_index:03d}' and
                source[offset:offset+len(text)]==text,'speech_paragraph_mapping_invalid')
        require(isinstance(unit.get('prior_context'),str) and isinstance(unit.get('next_context'),str) and
                normalize(unit['prior_context'])==source[:offset] and
                normalize(unit['next_context'])==source[offset+len(text):],'speech_context_mismatch')
        offset+=len(text)
        if offset==len(source):
            require(unit['boundary_reason']=='paragraph_end','speech_paragraph_end_invalid')
            paragraph_index+=1;offset=0
        else:
            require(unit['boundary_reason']!='paragraph_end' and
                    (unit['boundary_reason']!='complete_sentence' or re.search(r'[。！？][”’」』）)]*$', text) is not None),
                    'speech_sentence_boundary_invalid')
    require(paragraph_index==len(source_paragraphs) and offset==0,'speech_paragraph_mapping_invalid')
    require(value.get('pause_policy')=='semantic_target_minus_measured_existing_edge_silence','speech_pause_policy_invalid')
    listened=value.get('paragraph_listening')
    require(isinstance(listened,list) and all(isinstance(x,dict) and isinstance(x.get('paragraph_id'),str) for x in listened)
            and len(listened)==len(source_paragraphs) and
            {x['paragraph_id'] for x in listened}=={u['paragraph_id'] for u in units}, 'paragraph_listening_coverage_missing')
    for item in listened:
        require(item.get('status')=='passed' and item.get('continuous') is True and
                finite_number(item.get('start_seconds')) and finite_number(item.get('end_seconds')) and
                0<=item['start_seconds']<item['end_seconds'],'paragraph_listening_invalid')
        verify_ref(root,item.get('evidence'),snapshot=snapshot)

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        original = args.script.read_bytes()
        result = plan(original.decode("utf-8"))
        if not result["units"]:
            raise ValueError("speech_body_empty")
        result["script_sha256"] = hashlib.sha256(original).hexdigest()
        # A new plan must not replace an existing plan or the source manuscript.
        with args.out.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    except (OSError, UnicodeError, ValueError):
        print("speech_plan_input_or_output_invalid")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
