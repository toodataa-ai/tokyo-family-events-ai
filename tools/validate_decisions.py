#!/usr/bin/env python3
import argparse, json, pathlib, re, sys
from collections import Counter

AXES=['child_target','interactivity','age_fit','stay_flexibility','burden','cost','reservation','family_value']
GRADES={'A','B','C','D','unknown'}
DECISIONS={'published','excluded','duplicate'}
HARD_CODES={'adult_only','minors_prohibited','safety_unsuitable','outside_23wards','date_mismatch','no_official_basis','cancelled_or_postponed'}
HTTP_RE=re.compile(r'^https?://',re.I)
PROMPT_RUBRIC={'v1.5':'family-fit-v1','v1.6':'family-fit-v2'}
V2_MATERIAL={'adult_oriented','narrow_fandom','specialist_content','passive_only','night_burden','crowd_burden','high_cost','reservation_difficult','age_mismatch'}
V2_SEVERE={'alcohol_primary','reservation_unavailable','late_night_primary','extreme_cost','content_intensity'}
V2_NONPRIMARY={'family_value_low','child_program_absent'}

def load_json(path): return json.loads(path.read_text(encoding='utf-8'))

def validate_decision_file(path,week,run,expected_rubric,strict=False):
    errors,warnings=[],[]
    doc=load_json(path); summary=doc.get('summary') or {}; migration=bool(doc.get('migration_incomplete'))
    if doc.get('schema_version') != 1: errors.append(f'{path}: schema_version must be 1')
    if doc.get('rubric_version') != expected_rubric: errors.append(f'{path}: rubric_version must be {expected_rubric}')
    coverage=week.get('coverage') or {}
    candidate_total=coverage.get('candidate_count'); duplicate_removed=coverage.get('duplicate_removed') or 0
    excluded=coverage.get('excluded_count') or 0; published=coverage.get('published_count') or 0
    for key,expected in {'candidate_total':candidate_total,'duplicate':duplicate_removed,'excluded':excluded,'published':published}.items():
        if isinstance(expected,int) and summary.get(key)!=expected: errors.append(f'{path}: summary.{key}={summary.get(key)!r} != coverage {expected}')
    decisions=doc.get('decisions') or []
    if not isinstance(decisions,list): errors.append(f'{path}: decisions must be an array'); decisions=[]
    if migration:
        mode=str(run.get('mode') or '')
        if 'migration' not in mode and 'initial-six-week-rollout' not in mode: errors.append(f'{path}: migration_incomplete is only allowed for migration/initial rollout runs')
        if summary.get('historical_unclassified') is None: errors.append(f'{path}: migration_incomplete requires summary.historical_unclassified')
        warnings.append(f'{path}: migration audit incomplete; historical candidate-level reasons were not stored')
    elif strict:
        if len(decisions)!=candidate_total: errors.append(f'{path}: complete audit requires {candidate_total} decisions, got {len(decisions)}')
        if published+excluded+duplicate_removed!=candidate_total: errors.append(f'{path}: candidate_total must equal published+excluded+duplicate')
    counts=Counter(); ids=set()
    for i,row in enumerate(decisions,1):
        prefix=f'{path}: decision #{i}'
        if not isinstance(row,dict): errors.append(f'{prefix} must be object'); continue
        cid=row.get('candidate_id')
        if not cid: errors.append(f'{prefix} candidate_id is required')
        elif cid in ids: errors.append(f'{prefix} duplicate candidate_id {cid}')
        else: ids.add(cid)
        decision=row.get('decision')
        if decision not in DECISIONS: errors.append(f'{prefix} invalid decision {decision!r}'); continue
        counts[decision]+=1
        if decision=='duplicate':
            if not row.get('duplicate_of'): errors.append(f'{prefix} duplicate requires duplicate_of')
            if not row.get('reasons'): errors.append(f'{prefix} duplicate requires reasons')
            continue
        fit=row.get('family_fit') or {}; axes=fit.get('axes') or {}
        if fit.get('rubric_version') != expected_rubric: errors.append(f'{prefix} family_fit.rubric_version must be {expected_rubric}')
        for axis in AXES:
            item=axes.get(axis)
            if not isinstance(item,dict): errors.append(f'{prefix} missing axis {axis}'); continue
            if item.get('grade') not in GRADES: errors.append(f'{prefix} axis {axis} invalid grade {item.get("grade")!r}')
            if not str(item.get('reason') or '').strip(): errors.append(f'{prefix} axis {axis} requires reason')
        overall=fit.get('overall')
        if overall not in GRADES: errors.append(f'{prefix} invalid overall {overall!r}')
        hard=row.get('hard_exclusion')
        if hard is not None and hard not in HARD_CODES: errors.append(f'{prefix} invalid hard_exclusion {hard!r}')
        if hard and decision!='excluded': errors.append(f'{prefix} hard exclusion requires decision=excluded')
        et=row.get('exclusion_type')
        if decision=='excluded' and et not in ('hard','soft'): errors.append(f'{prefix} excluded requires exclusion_type hard/soft')
        if et=='hard' and not hard: errors.append(f'{prefix} hard exclusion_type requires hard_exclusion')
        if et=='soft' and hard: errors.append(f'{prefix} soft exclusion_type cannot have hard_exclusion')
        reasons=row.get('reasons') or []; codes=row.get('reason_codes') or []
        if not isinstance(reasons,list) or not any(str(x).strip() for x in reasons): errors.append(f'{prefix} requires human-readable reasons')
        if not isinstance(codes,list) or not codes: errors.append(f'{prefix} requires reason_codes')
        evidence=row.get('evidence') or []
        if not isinstance(evidence,list) or not evidence: errors.append(f'{prefix} requires evidence')
        elif not any(isinstance(x,dict) and HTTP_RE.match(str(x.get('url') or '')) for x in evidence): errors.append(f'{prefix} evidence requires at least one http(s) URL')
        if decision=='published' and overall in ('C','D') and not str(row.get('override_reason') or '').strip(): errors.append(f'{prefix} published {overall} requires override_reason')

        if expected_rubric=='family-fit-v2':
            positive=row.get('positive_signals'); negative=row.get('negative_signals')
            if not isinstance(positive,list): errors.append(f'{prefix} family-fit-v2 requires positive_signals[]'); positive=[]
            if not isinstance(negative,list): errors.append(f'{prefix} family-fit-v2 requires negative_signals[]'); negative=[]
            if decision=='excluded' and et=='soft':
                primary=row.get('primary_reason_code')
                if overall=='A': errors.append(f'{prefix} family-fit-v2 forbids soft exclusion with overall=A; re-evaluate axes/decision')
                if primary in V2_NONPRIMARY: errors.append(f'{prefix} {primary} cannot be primary_reason_code in family-fit-v2')
                material=len({x for x in negative if x in V2_MATERIAL})
                severe=any(x in V2_SEVERE for x in negative)
                if material<2 and not severe:
                    errors.append(f'{prefix} soft exclusion requires >=2 material negative signals or >=1 severe signal; got material={material}, severe={severe}')
                if overall=='B' and not str(row.get('tradeoff_reason') or '').strip():
                    errors.append(f'{prefix} overall=B soft exclusion requires tradeoff_reason')
                if 'child_program_absent' in negative and len(set(negative)-{'child_program_absent','family_value_low'})==0:
                    errors.append(f'{prefix} child_program_absent cannot justify soft exclusion by itself')
                if 'narrow_fandom' in negative and len(set(negative)-{'narrow_fandom','family_value_low','child_program_absent'})==0:
                    errors.append(f'{prefix} narrow_fandom cannot justify soft exclusion by itself')
                if 'passive_only' in negative and len(set(negative)-{'passive_only','family_value_low','child_program_absent'})==0:
                    errors.append(f'{prefix} passive_only cannot justify soft exclusion by itself')
    if not migration and strict:
        for decision,expected in [('published',published),('excluded',excluded),('duplicate',duplicate_removed)]:
            if counts[decision]!=expected: errors.append(f'{path}: {decision} decision rows={counts[decision]} != summary/coverage={expected}')
    return errors,warnings

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('data_dir',nargs='?',default='site/data'); ap.add_argument('--strict',action='store_true'); args=ap.parse_args()
    data_dir=pathlib.Path(args.data_dir); manifest=load_json(data_dir/'manifest.json'); all_errors=[]; all_warnings=[]
    for required in ['family_fit_rubric.json','discovery_sources.json']:
        if not (data_dir/required).exists(): all_errors.append(f'{data_dir/required}: missing')
    for entry in manifest.get('weekends') or []:
        week_path=data_dir/entry['file']; week=load_json(week_path); run_name=week.get('run_file')
        if not run_name: all_errors.append(f'{week_path}: missing run_file'); continue
        run_path=data_dir/run_name; run=load_json(run_path); p=run.get('prompt') or {}; pv=p.get('version')
        expected=PROMPT_RUBRIC.get(pv)
        if not expected: all_errors.append(f'{run_path}: unsupported prompt.version {pv!r} for decision validator'); continue
        decision_name=(run.get('source_data') or {}).get('decision_file')
        if not decision_name: all_errors.append(f'{run_path}: source_data.decision_file is required'); continue
        decision_path=data_dir/decision_name
        if not decision_path.exists(): all_errors.append(f'{run_path}: missing decision file {decision_name}'); continue
        errors,warnings=validate_decision_file(decision_path,week,run,expected,args.strict); all_errors.extend(errors); all_warnings.extend(warnings)
        doc=load_json(decision_path); s=doc.get('summary') or {}
        print(f'DECISION {entry["file"]}: prompt={pv}, rubric={expected}, candidates={s.get("candidate_total")}, published={s.get("published")}, excluded={s.get("excluded")}, duplicate={s.get("duplicate")}, complete={not bool(doc.get("migration_incomplete"))}')
    for w in all_warnings: print('WARN:',w)
    if all_errors:
        for e in all_errors: print('ERROR:',e)
        sys.exit(1)
    print(f'OK: decision audit, {len(all_warnings)} warning(s)')
if __name__=='__main__': main()
