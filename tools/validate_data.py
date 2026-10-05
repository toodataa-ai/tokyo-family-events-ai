#!/usr/bin/env python3
import argparse, datetime, json, pathlib, re, sys
from collections import Counter
from urllib.parse import urlsplit, urlunsplit

WARDS = [
    '千代田区','中央区','港区','新宿区','文京区','台東区','墨田区','江東区','品川区','目黒区','大田区',
    '世田谷区','渋谷区','中野区','杉並区','豊島区','北区','荒川区','板橋区','練馬区','足立区','葛飾区','江戸川区'
]
HTTP_RE = re.compile(r'^https?://', re.I)
FIELD_STATES = {'pass','corrected','unknown','not_applicable'}
CORE_VERIFIED_FIELDS = ('name','date','venue')


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


def merge_corrections(ev, corrections):
    out = dict(ev)
    if not isinstance(corrections, dict):
        return out
    for key, value in corrections.items():
        if key in ('family_fit','reservation','ai') and isinstance(value, dict):
            base = out.get(key) if isinstance(out.get(key), dict) else {}
            out[key] = {**base, **value}
        else:
            out[key] = value
    return out


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


def load_and_apply_verification(path, data, events, strict=False):
    errors, warnings = [], []
    filename = data.get('verification_file')
    if not filename:
        if strict:
            errors.append(f'{path}: strict mode requires verification_file')
        return events, None, errors, warnings
    if not isinstance(filename, str) or not filename.endswith('.json') or '/' in filename or '\\' in filename:
        errors.append(f'{path}: invalid verification_file {filename!r}')
        return events, None, errors, warnings

    audit_path = path.parent / filename
    if not audit_path.exists():
        errors.append(f'{path}: missing verification file {audit_path}')
        return events, None, errors, warnings
    try:
        audit = json.loads(audit_path.read_text(encoding='utf-8'))
    except Exception as exc:
        errors.append(f'{path}: invalid verification JSON {audit_path}: {exc}')
        return events, None, errors, warnings

    verified_on = iso_date(audit.get('verified_on'))
    if not verified_on:
        errors.append(f'{audit_path}: verified_on must be YYYY-MM-DD')

    rows = audit.get('events') or []
    if not isinstance(rows, list):
        errors.append(f'{audit_path}: events must be an array')
        rows = []

    by_id = {}
    for i, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            errors.append(f'{audit_path}: verification #{i} must be object')
            continue
        eid = row.get('id')
        if not eid:
            errors.append(f'{audit_path}: verification #{i} missing id')
            continue
        if eid in by_id:
            errors.append(f'{audit_path}: duplicate verification id {eid}')
            continue
        by_id[eid] = row
        if strict and row.get('status') != 'verified':
            errors.append(f'{audit_path}: {eid} is not verified')
        source = row.get('source')
        if not source or not HTTP_RE.match(str(source)):
            errors.append(f'{audit_path}: {eid} requires http(s) verification source')
        fields = row.get('fields')
        if not isinstance(fields, dict):
            errors.append(f'{audit_path}: {eid} fields must be object')
            fields = {}
        for key, state in fields.items():
            if state not in FIELD_STATES:
                errors.append(f'{audit_path}: {eid} invalid field state {key}={state}')
        if strict:
            for key in CORE_VERIFIED_FIELDS:
                if fields.get(key) not in ('pass','corrected'):
                    errors.append(f'{audit_path}: {eid} core field {key} must be pass/corrected')
        corrections = row.get('corrections') or {}
        if not isinstance(corrections, dict):
            errors.append(f'{audit_path}: {eid} corrections must be object')

    event_ids = [ev.get('id') for ev in events if isinstance(ev, dict) and ev.get('id')]
    event_id_set = set(event_ids)
    missing = [eid for eid in event_ids if eid not in by_id]
    extra = [eid for eid in by_id if eid not in event_id_set]
    if missing:
        errors.append(f'{audit_path}: verification missing event ids: {missing}')
    if extra:
        errors.append(f'{audit_path}: verification contains unknown event ids: {extra}')

    corrected = []
    for ev in events:
        if not isinstance(ev, dict):
            corrected.append(ev)
            continue
        row = by_id.get(ev.get('id'))
        if not row:
            corrected.append(ev)
            continue
        merged = merge_corrections(ev, row.get('corrections') or {})
        merged['verification'] = {
            'status': row.get('status'),
            'source': row.get('source'),
            'source_kind': row.get('source_kind'),
            'fields': row.get('fields') or {},
            'note': row.get('note') or '',
            'verified_on': audit.get('verified_on')
        }
        corrected.append(merged)

    summary = audit.get('summary') or {}
    verified_count = sum(1 for r in rows if isinstance(r, dict) and r.get('status') == 'verified')
    if summary.get('total') != len(events):
        errors.append(f'{audit_path}: summary.total={summary.get("total")} != events={len(events)}')
    if summary.get('verified') != verified_count:
        errors.append(f'{audit_path}: summary.verified={summary.get("verified")} != verified rows={verified_count}')
    if strict and verified_count != len(events):
        errors.append(f'{audit_path}: strict mode requires all {len(events)} events verified, got {verified_count}')

    print(f'VERIFICATION {path.name}: {verified_count}/{len(events)} verified ({audit.get("verified_on")})')
    return corrected, audit, errors, warnings


def validate_week(path, strict=False, min_image_coverage=0.0):
    errors, warnings = [], []
    data, events, load_errors = load_week(path)
    errors.extend(load_errors)
    events, audit, verify_errors, verify_warnings = load_and_apply_verification(path, data, events, strict)
    errors.extend(verify_errors)
    warnings.extend(verify_warnings)
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
    image_count = 0
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
        if ev.get('image') and HTTP_RE.match(str(ev.get('image'))):
            image_count += 1

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
        if not ev.get('image'):
            warnings.append(f'{prefix}: thumbnail image is missing')

    for ward in WARDS:
        expected = ward_rows.get(ward, {}).get('published_count') or 0
        actual = actual_by_ward[ward]
        if expected != actual:
            errors.append(f'{path}: {ward} published_count={expected} != actual events={actual}')

    image_coverage = (image_count / len(events)) if events else 1.0
    if min_image_coverage and image_coverage < min_image_coverage:
        errors.append(
            f'{path}: thumbnail coverage {image_count}/{len(events)}={image_coverage:.1%} '
            f'is below required {min_image_coverage:.0%}'
        )
    print(f'IMAGE COVERAGE {path.name}: {image_count}/{len(events)} ({image_coverage:.1%})')

    return errors, warnings, len(events)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('data_dir', type=pathlib.Path)
    ap.add_argument('--strict', action='store_true')
    ap.add_argument('--min-image-coverage', type=float, default=0.0)
    args = ap.parse_args()

    if not 0.0 <= args.min_image_coverage <= 1.0:
        print('ERROR: --min-image-coverage must be between 0 and 1')
        return 2

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
        e, w, event_count = validate_week(p, args.strict, args.min_image_coverage)
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
