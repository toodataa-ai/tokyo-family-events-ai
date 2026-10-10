#!/usr/bin/env python3
"""Validate v1.15+ real discovery evidence and official multi-event schedule parity.

Historical v1.5 runs are intentionally not rewritten with invented provenance.
"""
import argparse
import json
from pathlib import Path
import re
import sys

WARDS = ['千代田区','中央区','港区','新宿区','文京区','台東区','墨田区','江東区','品川区','目黒区','大田区','世田谷区','渋谷区','中野区','杉並区','豊島区','北区','荒川区','板橋区','練馬区','足立区','葛飾区','江戸川区']
SOURCE = 'nerima_district_festivals_2026'


def active_version(run):
    version = (run.get('prompt') or {}).get('version', '')
    found = re.fullmatch(r'v1\.(\d+)', version)
    return bool(found and int(found.group(1)) >= 15)


def validate(run, week, decisions):
    if not active_version(run):
        return []
    errors = []
    label = week.get('sat', '?')
    evidence = run.get('discovery_evidence') or {}
    ward_rows = evidence.get('wards') or []
    mapping = {row.get('ward'): row for row in ward_rows}
    if set(mapping) != set(WARDS) or len(ward_rows) != 23:
        errors.append(f'{label}: discovery_evidence.wards must cover all 23 wards exactly once')
    coverage = {row.get('ward'): row for row in (week.get('coverage') or {}).get('wards', [])}
    for name in WARDS:
        actual = mapping.get(name) or {}
        logs = actual.get('query_logs') or []
        sources = actual.get('source_checks') or []
        if not logs or not sources:
            errors.append(f'{label}/{name}: missing actual per-query and per-source evidence')
            continue
        if any(not r.get('query') or not r.get('checked_at') or r.get('status') not in ('checked', 'error') for r in logs):
            errors.append(f'{label}/{name}: invalid query evidence')
        if any(not r.get('url') or not r.get('checked_at') or r.get('status') not in ('checked', 'error') for r in sources):
            errors.append(f'{label}/{name}: invalid source evidence')
        c = coverage.get(name) or {}
        if c.get('queries') != len(logs):
            errors.append(f'{label}/{name}: coverage.queries differs from real query log count')
        if c.get('sources_checked') != sum(r.get('status') == 'checked' for r in sources):
            errors.append(f'{label}/{name}: coverage.sources_checked differs from successful URL checks')
        if c.get('status') == 'checked' and (any(r.get('status') == 'error' for r in sources) or any(r.get('status') == 'error' for r in logs)):
            errors.append(f'{label}/{name}: checked is forbidden when required exploration failed')
    official = [r for r in run.get('official_schedule_checks', []) if r.get('source_id') == SOURCE]
    if len(official) != 1:
        errors.append(f'{label}: expected one official_schedule_checks record for {SOURCE}')
        return errors
    item = official[0]
    for field in ('url', 'checked_at'):
        if not item.get(field):
            errors.append(f'{label}: official schedule missing {field}')
    if item.get('status') != 'checked':
        errors.append(f'{label}: official schedule not successfully checked')
    count = item.get('official_row_count')
    ids = item.get('candidate_ids')
    if not isinstance(count, int) or count < 0 or not isinstance(ids, list) or len(ids) != count or len(set(ids)) != len(ids):
        errors.append(f'{label}: official row count must equal unique candidate IDs')
        return errors
    known = {d.get('candidate_id') for d in decisions.get('decisions', []) if d.get('decision') in ('published', 'excluded', 'duplicate')}
    missing = [cid for cid in ids if cid not in known]
    if item.get('unmatched_official_rows') or missing or item.get('matched_candidate_count') != count:
        errors.append(f'{label}: incomplete official-row-to-decision reconciliation ({len(missing)} candidate IDs absent)')
    return errors


def main():
    p = argparse.ArgumentParser()
    p.add_argument('directory', type=Path)
    args = p.parse_args()
    errors = []
    manifest = json.loads((args.directory/'manifest.json').read_text(encoding='utf-8'))
    for period in manifest.get('weekends', []):
        week = json.loads((args.directory/period['file']).read_text(encoding='utf-8'))
        run = json.loads((args.directory/week['run_file']).read_text(encoding='utf-8'))
        decisions_path = args.directory/(run.get('source_data') or {}).get('decision_file', period['sat']+'-decisions.json')
        decisions = json.loads(decisions_path.read_text(encoding='utf-8'))
        errors.extend(validate(run, week, decisions))
    for error in errors:
        print('ERROR', error, file=sys.stderr)
    print(f'official schedule discovery audit: {"FAIL" if errors else "PASS"}')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
