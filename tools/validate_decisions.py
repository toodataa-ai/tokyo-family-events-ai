#!/usr/bin/env python3
import argparse
import json
import pathlib
import re
import sys
from collections import Counter

AXES = [
    'child_target','interactivity','age_fit','stay_flexibility',
    'burden','cost','reservation','family_value'
]
GRADES = {'A','B','C','D','unknown'}
DECISIONS = {'published','excluded','duplicate'}
HARD_CODES = {
    'adult_only','minors_prohibited','safety_unsuitable','outside_23wards',
    'date_mismatch','no_official_basis','cancelled_or_postponed'
}
HTTP_RE = re.compile(r'^https?://', re.I)


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def count_events(data_dir, week):
    events = list(week.get('events') or [])
    for name in week.get('event_files') or []:
        shard = data_dir / name
        rows = load_json(shard)
        if isinstance(rows, list):
            events.extend(rows)
    return events


def validate_decision_file(path, week, run, strict=False):
    errors, warnings = [], []
    doc = load_json(path)
    summary = doc.get('summary') or {}
    migration = bool(doc.get('migration_incomplete'))

    if doc.get('schema_version') != 1:
        errors.append(f'{path}: schema_version must be 1')
    if doc.get('rubric_version') != 'family-fit-v1':
        errors.append(f'{path}: rubric_version must be family-fit-v1')

    coverage = week.get('coverage') or {}
    candidate_total = coverage.get('candidate_count')
    duplicate_removed = coverage.get('duplicate_removed') or 0
    excluded = coverage.get('excluded_count') or 0
    published = coverage.get('published_count') or 0

    checks = {
        'candidate_total': candidate_total,
        'duplicate': duplicate_removed,
        'excluded': excluded,
        'published': published,
    }
    for key, expected in checks.items():
        if isinstance(expected, int) and summary.get(key) != expected:
            errors.append(f'{path}: summary.{key}={summary.get(key)!r} != coverage {expected}')

    decisions = doc.get('decisions') or []
    if not isinstance(decisions, list):
        errors.append(f'{path}: decisions must be an array')
        decisions = []

    if migration:
        mode = str(run.get('mode') or '')
        if 'migration' not in mode and 'initial-six-week-rollout' not in mode:
            errors.append(f'{path}: migration_incomplete is only allowed for migration/initial rollout runs')
        historical = summary.get('historical_unclassified')
        if historical is None:
            errors.append(f'{path}: migration_incomplete requires summary.historical_unclassified')
        warnings.append(f'{path}: migration audit incomplete; historical candidate-level reasons were not stored')
    elif strict:
        if len(decisions) != candidate_total:
            errors.append(f'{path}: complete v1.5 audit requires {candidate_total} decisions, got {len(decisions)}')
        if published + excluded + duplicate_removed != candidate_total:
            errors.append(
                f'{path}: candidate_total must equal published+excluded+duplicate '
                f'({candidate_total} != {published}+{excluded}+{duplicate_removed})'
            )

    counts = Counter()
    ids = set()
    for i, row in enumerate(decisions, 1):
        prefix = f'{path}: decision #{i}'
        if not isinstance(row, dict):
            errors.append(f'{prefix} must be object')
            continue
        cid = row.get('candidate_id')
        if not cid:
            errors.append(f'{prefix} candidate_id is required')
        elif cid in ids:
            errors.append(f'{prefix} duplicate candidate_id {cid}')
        else:
            ids.add(cid)
        decision = row.get('decision')
        if decision not in DECISIONS:
            errors.append(f'{prefix} invalid decision {decision!r}')
            continue
        counts[decision] += 1

        if decision == 'duplicate':
            if not row.get('duplicate_of'):
                errors.append(f'{prefix} duplicate requires duplicate_of')
            if not row.get('reasons'):
                errors.append(f'{prefix} duplicate requires reasons')
            continue

        fit = row.get('family_fit') or {}
        axes = fit.get('axes') or {}
        if fit.get('rubric_version') != 'family-fit-v1':
            errors.append(f'{prefix} family_fit.rubric_version must be family-fit-v1')
        for axis in AXES:
            item = axes.get(axis)
            if not isinstance(item, dict):
                errors.append(f'{prefix} missing axis {axis}')
                continue
            if item.get('grade') not in GRADES:
                errors.append(f'{prefix} axis {axis} invalid grade {item.get("grade")!r}')
            if not str(item.get('reason') or '').strip():
                errors.append(f'{prefix} axis {axis} requires reason')
        overall = fit.get('overall')
        if overall not in GRADES:
            errors.append(f'{prefix} invalid overall {overall!r}')

        hard = row.get('hard_exclusion')
        if hard is not None and hard not in HARD_CODES:
            errors.append(f'{prefix} invalid hard_exclusion {hard!r}')
        if hard and decision != 'excluded':
            errors.append(f'{prefix} hard exclusion requires decision=excluded')
        exclusion_type = row.get('exclusion_type')
        if decision == 'excluded' and exclusion_type not in ('hard','soft'):
            errors.append(f'{prefix} excluded requires exclusion_type hard/soft')
        if exclusion_type == 'hard' and not hard:
            errors.append(f'{prefix} hard exclusion_type requires hard_exclusion')
        if exclusion_type == 'soft' and hard:
            errors.append(f'{prefix} soft exclusion_type cannot have hard_exclusion')

        reasons = row.get('reasons') or []
        reason_codes = row.get('reason_codes') or []
        if not isinstance(reasons, list) or not any(str(x).strip() for x in reasons):
            errors.append(f'{prefix} requires human-readable reasons')
        if not isinstance(reason_codes, list) or not reason_codes:
            errors.append(f'{prefix} requires reason_codes')

        evidence = row.get('evidence') or []
        if not isinstance(evidence, list) or not evidence:
            errors.append(f'{prefix} requires evidence')
        else:
            if not any(isinstance(x, dict) and HTTP_RE.match(str(x.get('url') or '')) for x in evidence):
                errors.append(f'{prefix} evidence requires at least one http(s) URL')

        if decision == 'published' and overall in ('C','D') and not str(row.get('override_reason') or '').strip():
            errors.append(f'{prefix} published {overall} requires override_reason')

    if not migration and strict:
        for decision, expected in [('published', published), ('excluded', excluded), ('duplicate', duplicate_removed)]:
            if counts[decision] != expected:
                errors.append(f'{path}: {decision} decision rows={counts[decision]} != summary/coverage={expected}')

    return errors, warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('data_dir', nargs='?', default='site/data')
    ap.add_argument('--strict', action='store_true')
    args = ap.parse_args()
    data_dir = pathlib.Path(args.data_dir)
    manifest = load_json(data_dir / 'manifest.json')
    all_errors, all_warnings = [], []

    rubric = data_dir / 'family_fit_rubric.json'
    sources = data_dir / 'discovery_sources.json'
    if not rubric.exists():
        all_errors.append(f'{rubric}: missing')
    if not sources.exists():
        all_errors.append(f'{sources}: missing')

    for entry in manifest.get('weekends') or []:
        week_path = data_dir / entry['file']
        week = load_json(week_path)
        run_name = week.get('run_file')
        if not run_name:
            all_errors.append(f'{week_path}: missing run_file')
            continue
        run_path = data_dir / run_name
        run = load_json(run_path)
        p = run.get('prompt') or {}
        if p.get('version') != 'v1.5':
            all_errors.append(f'{run_path}: decision validator requires prompt.version v1.5')
        decision_name = (run.get('source_data') or {}).get('decision_file')
        if not decision_name:
            all_errors.append(f'{run_path}: source_data.decision_file is required')
            continue
        decision_path = data_dir / decision_name
        if not decision_path.exists():
            all_errors.append(f'{run_path}: missing decision file {decision_name}')
            continue
        errors, warnings = validate_decision_file(decision_path, week, run, args.strict)
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        doc = load_json(decision_path)
        s = doc.get('summary') or {}
        print(
            f'DECISION {entry["file"]}: candidates={s.get("candidate_total")}, '
            f'published={s.get("published")}, excluded={s.get("excluded")}, duplicate={s.get("duplicate")}, '
            f'complete={not bool(doc.get("migration_incomplete"))}'
        )

    for w in all_warnings:
        print('WARN:', w)
    if all_errors:
        for e in all_errors:
            print('ERROR:', e)
        sys.exit(1)
    print(f'OK: decision audit, {len(all_warnings)} warning(s)')

if __name__ == '__main__':
    main()
