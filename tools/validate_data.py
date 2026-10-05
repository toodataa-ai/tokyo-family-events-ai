#!/usr/bin/env python3
import argparse, datetime, json, pathlib, re, sys
from collections import Counter
from urllib.parse import urlsplit, urlunsplit

WARDS = [
    '千代田区','中央区','港区','新宿区','文京区','台東区','墨田区','江東区','品川区','目黒区','大田区',
    '世田谷区','渋谷区','中野区','杉並区','豊島区','北区','荒川区','板橋区','練馬区','足立区','葛飾区','江戸川区'
]
HTTP_RE = re.compile(r'^https?://', re.I)


def canonical_url(value):
    if not value:
        return ''
    try:
        p = urlsplit(value.strip())
        host = p.netloc.lower().removeprefix('www.')
        path = p.path.rstrip('/') or '/'
        return urlunsplit((p.scheme.lower(), host, path, p.query, ''))
    except Exception:
        return value.strip()


def norm(value):
    return re.sub(r'\s+', '', str(value or '')).lower()


def iso_date(value):
    try:
        return datetime.date.fromisoformat(str(value))
    except Exception:
        return None


def load_week(path):
    errors = []
    data = json.loads(path.read_text(encoding='utf-8'))
    base = data.get('events')
    if base is None:
        base = []
    if not isinstance(base, list):
        errors.append(f'{path}: events must be an array')
        base = []
    events = list(base)

    shard_files = data.get('event_files') or []
    if not isinstance(shard_files, list):
        errors.append(f'{path}: event_files must be an array')
        shard_files = []
    if len(shard_files) != len(set(shard_files)):
        errors.append(f'{path}: event_files contains duplicate filenames')

    for name in shard_files:
        if not isinstance(name, str) or not name.endswith('.json') or '/' in name or '\\' in name:
            errors.append(f'{path}: invalid event shard filename {name!r}')
            continue
        shard = path.parent / name
        if not shard.exists():
            errors.append(f'{path}: missing event shard {shard}')
            continue
        try:
            rows = json.loads(shard.read_text(encoding='utf-8'))
        except Exception as exc:
            errors.append(f'{path}: invalid JSON in shard {shard}: {exc}')
            continue
        if not isinstance(rows, list):
            errors.append(f'{path}: event shard must be an array: {shard}')
            continue
        events.extend(rows)
    return data, events, errors


def validate_week(path, strict=False):
    errors, warnings = [], []
    data, events, load_errors = load_week(path)
    errors.extend(load_errors)
    coverage = data.get('coverage') or {}

    if strict and data.get('sample'):
        errors.append(f'{path}: sample=true cannot be deployed in strict mode')

    sat = iso_date(data.get('sat'))
    sun = iso_date(data.get('sun'))
    if not sat or not sun or sat > sun:
        errors.append(f'{path}: invalid sat/sun')
    elif (sun - sat).days != 1:
        warnings.append(f'{path}: weekend span is not exactly 2 days')

    wards = coverage.get('wards') or []
    ward_rows = {row.get('ward'): row for row in wards if isinstance(row, dict)}
    missing_cov = [w for w in WARDS if w not in ward_rows]
    extra_cov = [w for w in ward_rows if w not in WARDS]
    if missing_cov:
        errors.append(f'{path}: coverage missing wards: {missing_cov}')
    if extra_cov:
        errors.append(f'{path}: coverage has invalid wards: {extra_cov}')
    if len(ward_rows) != len(wards):
        errors.append(f'{path}: duplicate/invalid coverage ward rows')

    if strict:
        unchecked = [w for w in WARDS if ward_rows.get(w, {}).get('status') != 'checked']
        if unchecked:
            errors.append(f'{path}: strict mode requires checked coverage for all wards: {unchecked}')
        weak_search = [
            w for w in WARDS
            if (ward_rows.get(w, {}).get('queries') or 0) < 1
            or (ward_rows.get(w, {}).get('sources_checked') or 0) < 1
        ]
        if weak_search:
            errors.append(f'{path}: strict mode requires search/source evidence for every ward: {weak_search}')

    if coverage.get('published_count') != len(events):
        errors.append(f"{path}: coverage.published_count={coverage.get('published_count')} != events={len(events)}")
    if isinstance(coverage.get('candidate_count'), int) and coverage['candidate_count'] < len(events):
        errors.append(f"{path}: coverage.candidate_count={coverage.get('candidate_count')} < events={len(events)}")

    row_published = sum((ward_rows.get(w, {}).get('published_count') or 0) for w in WARDS)
    if row_published != len(events):
        errors.append(f'{path}: sum of ward published_count={row_published} != events={len(events)}')

    actual_by_ward = Counter()
    seen_ids, seen_urls, seen_signature = set(), {}, {}
    for i, ev in enumerate(events, 1):
        prefix = f'{path}: event #{i}'
        if not isinstance(ev, dict):
            errors.append(f'{prefix}: must be object')
            continue
        for key in ('id','ward','name','url','period','source'):
            if not ev.get(key):
                errors.append(f'{prefix}: missing required field {key}')

        ward = ev.get('ward')
        if ward and ward not in WARDS:
            errors.append(f'{prefix}: invalid ward {ward}')
        elif ward:
            actual_by_ward[ward] += 1

        for key in ('url','official_url','source','image'):
            value = ev.get(key)
            if value and not HTTP_RE.match(value):
                errors.append(f'{prefix}: {key} must be http(s): {value}')

        eid = ev.get('id')
        if eid:
            if eid in seen_ids:
                errors.append(f'{prefix}: duplicate id {eid}')
            seen_ids.add(eid)

        url_key = canonical_url(ev.get('official_url') or ev.get('url'))
        if url_key:
            if url_key in seen_urls:
                warnings.append(f'{prefix}: same canonical URL as event #{seen_urls[url_key]}: {url_key}')
            else:
                seen_urls[url_key] = i

        sig = (norm(ev.get('name')), ev.get('date_start') or ev.get('period'), norm(ev.get('venue') or ward))
        if sig[0] and sig[1]:
            if sig in seen_signature:
                errors.append(f'{prefix}: probable duplicate of event #{seen_signature[sig]} (name/date/venue)')
            else:
                seen_signature[sig] = i

        start = iso_date(ev.get('date_start'))
        end = iso_date(ev.get('date_end'))
        if strict and (not start or not end):
            errors.append(f'{prefix}: strict mode requires date_start/date_end')
        elif start and end:
            if start > end:
                errors.append(f'{prefix}: date_start is after date_end')
            if sat and sun and (end < sat or start > sun):
                errors.append(f'{prefix}: event does not overlap target weekend {sat}..{sun}')

        fit = ev.get('family_fit') or {}
        if fit.get('grade') not in ('A','B','C'):
            errors.append(f'{prefix}: family_fit.grade must be A/B/C')
        if not fit.get('reason'):
            warnings.append(f'{prefix}: family_fit.reason is empty')
        if not ev.get('venue'):
            warnings.append(f'{prefix}: venue is empty; copy output falls back to ward')
        if not ev.get('price'):
            warnings.append(f'{prefix}: price is empty; copy output uses the fixed fallback text')

    for ward in WARDS:
        expected = ward_rows.get(ward, {}).get('published_count') or 0
        actual = actual_by_ward[ward]
        if expected != actual:
            errors.append(f'{path}: {ward} published_count={expected} != actual events={actual}')

    return errors, warnings, len(events)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('data_dir', type=pathlib.Path)
    ap.add_argument('--strict', action='store_true')
    args = ap.parse_args()

    manifest_path = args.data_dir / 'manifest.json'
    if not manifest_path.exists():
        print(f'ERROR: missing {manifest_path}')
        return 2
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    errors, warnings = [], []
    weekends = manifest.get('weekends') or []
    if not weekends:
        errors.append('manifest: weekends is empty')
    if manifest.get('default') and manifest.get('default') not in {w.get('sat') for w in weekends}:
        errors.append('manifest: default does not point to a listed weekend')

    listed_files = set()
    for entry in weekends:
        filename = str(entry.get('file',''))
        if filename in listed_files:
            errors.append(f'manifest: duplicate weekend file {filename}')
        listed_files.add(filename)
        p = args.data_dir / filename
        if not p.exists():
            errors.append(f'manifest: missing data file {p}')
            continue
        e, w, event_count = validate_week(p, args.strict)
        errors.extend(e)
        warnings.extend(w)
        if entry.get('count') != event_count:
            errors.append(f"manifest: {entry.get('file')} count={entry.get('count')} != events={event_count}")

    for msg in warnings:
        print('WARN:', msg)
    for msg in errors:
        print('ERROR:', msg)
    if errors:
        print(f'FAILED: {len(errors)} error(s), {len(warnings)} warning(s)')
        return 1
    print(f'OK: {len(weekends)} weekend file(s), {len(warnings)} warning(s)')
    return 0

if __name__ == '__main__':
    sys.exit(main())
