#!/usr/bin/env python3
import argparse
import json
import pathlib
import re
import subprocess
import sys
import unicodedata
from urllib.parse import urlsplit, urlunsplit

HTTP_RE = re.compile(r"^https?://", re.I)
UNKNOWN_EXACT = {
    "", "-", "—", "不明", "未定", "未確認", "要確認", "情報なし",
    "unknown", "n/a", "na", "null", "none"
}
FACTUAL_FIELDS = ("name", "date", "time", "venue", "price", "reservation", "official_url", "indoor_outdoor")
PRESERVE_ONLY_FIELDS = ("description", "image", "source", "categories")
REMOVAL_DECISIONS = {"excluded", "duplicate"}


def norm_text(value):
    s = unicodedata.normalize("NFKC", str(value or ""))
    return re.sub(r"\s+", " ", s).strip()


def norm_key(value):
    return norm_text(value).lower()


def canonical_url(value):
    if not value:
        return ""
    try:
        p = urlsplit(str(value).strip())
        host = p.netloc.lower().removeprefix("www.")
        path = p.path.rstrip("/") or "/"
        return urlunsplit((p.scheme.lower(), host, path, p.query, ""))
    except Exception:
        return str(value).strip()


def data_path(prefix, ref):
    ref = str(ref or "")
    if ref.startswith(prefix + "/"):
        return ref
    return f"{prefix}/{ref}"


class CurrentStore:
    def read_text(self, path):
        p = pathlib.Path(path)
        return p.read_text(encoding="utf-8") if p.exists() else None


class GitStore:
    def __init__(self, ref):
        self.ref = ref

    def read_text(self, path):
        proc = subprocess.run(
            ["git", "show", f"{self.ref}:{path}"],
            check=False, capture_output=True, text=True, encoding="utf-8"
        )
        return proc.stdout if proc.returncode == 0 else None


def read_json(store, path):
    text = store.read_text(path)
    if text is None:
        return None
    return json.loads(text)


def merge_corrections(event, corrections):
    merged = dict(event)
    for key, value in (corrections or {}).items():
        if key in ("family_fit", "reservation", "ai") and isinstance(value, dict):
            base = merged.get(key) if isinstance(merged.get(key), dict) else {}
            merged[key] = {**base, **value}
        else:
            merged[key] = value
    return merged


def load_bundle(store, prefix, week_file):
    week = read_json(store, data_path(prefix, week_file))
    if not isinstance(week, dict):
        return None

    events = list(week.get("events") or [])
    for shard in week.get("event_files") or []:
        rows = read_json(store, data_path(prefix, shard))
        if isinstance(rows, list):
            events.extend(rows)

    verification_rows = {}
    verification_file = week.get("verification_file")
    if verification_file:
        audit = read_json(store, data_path(prefix, verification_file)) or {}
        verification_rows = {
            row.get("id"): row
            for row in (audit.get("events") or [])
            if isinstance(row, dict) and row.get("id")
        }
        events = [
            merge_corrections(ev, (verification_rows.get(ev.get("id")) or {}).get("corrections") or {})
            if isinstance(ev, dict) else ev
            for ev in events
        ]

    decisions = []
    run_file = week.get("run_file")
    if run_file:
        run = read_json(store, data_path(prefix, run_file)) or {}
        decision_file = ((run.get("source_data") or {}).get("decision_file"))
        if decision_file:
            audit = read_json(store, data_path(prefix, decision_file)) or {}
            decisions = [x for x in (audit.get("decisions") or []) if isinstance(x, dict)]

    return {
        "week": week,
        "events": [x for x in events if isinstance(x, dict)],
        "verification": verification_rows,
        "decisions": decisions,
    }


def field_value(event, field):
    if field == "date":
        return {
            "date_start": event.get("date_start") or "",
            "date_end": event.get("date_end") or "",
            "period": event.get("period") or "",
        }
    if field == "reservation":
        r = event.get("reservation")
        if not isinstance(r, dict):
            return {}
        return {"required": r.get("required"), "note": r.get("note") or ""}
    if field == "categories":
        return event.get("categories") or []
    return event.get(field)


def normalized_value(value):
    if isinstance(value, dict):
        return {k: normalized_value(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [normalized_value(v) for v in value]
    if isinstance(value, str):
        return norm_text(value)
    return value


def values_equal(a, b):
    return normalized_value(a) == normalized_value(b)


def informative(value):
    if isinstance(value, dict):
        if "required" in value and isinstance(value.get("required"), bool):
            return True
        return any(informative(v) for v in value.values())
    if isinstance(value, list):
        return any(informative(v) for v in value)
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    s = norm_key(value)
    if s in UNKNOWN_EXACT:
        return False
    if s.endswith("要確認") and len(s) <= 12:
        return False
    return bool(s)


def event_keys(event):
    keys = []
    eid = event.get("id")
    if eid:
        keys.append(("id", str(eid)))
    date = event.get("date_start") or event.get("period") or ""
    venue = norm_key(event.get("venue"))
    ward = norm_key(event.get("ward"))
    url = canonical_url(event.get("official_url") or event.get("url"))
    name = norm_key(event.get("name"))
    if url and date:
        keys.append(("url-date-venue", url, str(date), venue))
    if name and date:
        keys.append(("name-date-venue-ward", name, str(date), venue, ward))
    return keys


def valid_http(value):
    return bool(value and HTTP_RE.match(str(value)))


def valid_field_change(row, field):
    changes = row.get("field_changes") if isinstance(row, dict) else None
    entry = changes.get(field) if isinstance(changes, dict) else None
    if not isinstance(entry, dict):
        return False
    return (
        "from" in entry
        and "to" in entry
        and bool(norm_text(entry.get("reason")))
        and valid_http(entry.get("source"))
    )


def valid_removal(prev, decisions):
    pid = str(prev.get("id") or "")
    pname = norm_key(prev.get("name"))
    pward = norm_key(prev.get("ward"))
    candidates = []
    for row in decisions:
        if str(row.get("candidate_id") or "") == pid:
            candidates.append(row)
            continue
        if pname and norm_key(row.get("name")) == pname and norm_key(row.get("ward")) == pward:
            candidates.append(row)
    for row in candidates:
        if row.get("decision") not in REMOVAL_DECISIONS:
            continue
        evidence = row.get("evidence") or []
        has_evidence = any(isinstance(e, dict) and valid_http(e.get("url")) for e in evidence)
        reasons = [x for x in (row.get("reasons") or []) if norm_text(x)]
        if has_evidence and reasons:
            return True
    return False


def main():
    ap = argparse.ArgumentParser(description="Prevent silent loss or unsupported mutation of previously published event facts.")
    ap.add_argument("data_dir", nargs="?", default="site/data")
    ap.add_argument("--base-ref", default="HEAD^")
    args = ap.parse_args()

    prefix = pathlib.Path(args.data_dir).as_posix().rstrip("/")
    current_store = CurrentStore()
    parent_store = GitStore(args.base_ref)

    current_manifest = read_json(current_store, f"{prefix}/manifest.json")
    parent_manifest = read_json(parent_store, f"{prefix}/manifest.json")
    if not isinstance(current_manifest, dict):
        print("ERROR: current manifest is missing or invalid", file=sys.stderr)
        return 1
    if not isinstance(parent_manifest, dict):
        print(f"Non-regression check skipped: {args.base_ref} has no readable manifest.")
        return 0

    current_entries = {w.get("sat"): w for w in (current_manifest.get("weekends") or []) if isinstance(w, dict) and w.get("sat")}
    parent_entries = {w.get("sat"): w for w in (parent_manifest.get("weekends") or []) if isinstance(w, dict) and w.get("sat")}
    common_sats = sorted(set(current_entries) & set(parent_entries))

    current_bundles = []
    parent_bundles = []
    for sat in common_sats:
        cb = load_bundle(current_store, prefix, current_entries[sat].get("file"))
        pb = load_bundle(parent_store, prefix, parent_entries[sat].get("file"))
        if cb:
            current_bundles.append(cb)
        if pb:
            parent_bundles.append(pb)

    current_events = []
    current_verification = {}
    current_decisions = []
    for bundle in current_bundles:
        current_events.extend(bundle["events"])
        current_verification.update(bundle["verification"])
        current_decisions.extend(bundle["decisions"])

    by_key = {}
    for event in current_events:
        for key in event_keys(event):
            by_key.setdefault(key, []).append(event)

    matched_current_ids = set()
    errors = []
    checked = 0
    seen_previous = set()

    for bundle in parent_bundles:
        for prev in bundle["events"]:
            prev_identity = str(prev.get("id") or "") or repr(event_keys(prev))
            if prev_identity in seen_previous:
                continue
            seen_previous.add(prev_identity)

            curr = None
            for key in event_keys(prev):
                rows = by_key.get(key) or []
                available = [x for x in rows if id(x) not in matched_current_ids]
                if len(available) == 1:
                    curr = available[0]
                    break

            if curr is None:
                if not valid_removal(prev, current_decisions):
                    errors.append(
                        f"event disappeared without auditable excluded/duplicate decision: "
                        f"{prev.get('id')} {prev.get('name')}"
                    )
                continue

            matched_current_ids.add(id(curr))
            checked += 1
            row = current_verification.get(curr.get("id")) or {}

            for field in FACTUAL_FIELDS:
                before = field_value(prev, field)
                after = field_value(curr, field)
                if not informative(before) or values_equal(before, after):
                    continue
                if not valid_field_change(row, field):
                    kind = "downgrade" if not informative(after) else "change"
                    errors.append(
                        f"{curr.get('id')} {curr.get('name')}: unsupported {kind} of {field}; "
                        f"field_changes.{field} must record from/to/reason/source"
                    )

            for field in PRESERVE_ONLY_FIELDS:
                before = field_value(prev, field)
                after = field_value(curr, field)
                if informative(before) and not informative(after) and not valid_field_change(row, field):
                    errors.append(
                        f"{curr.get('id')} {curr.get('name')}: {field} regressed to empty/unknown "
                        f"without field_changes.{field} evidence"
                    )

    if errors:
        print("Non-regression validation FAILED:")
        for err in errors:
            print(f" - {err}")
        return 1

    print(
        f"Non-regression validation OK: compared {checked} previously published events "
        f"across {len(common_sats)} common weekend datasets."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
