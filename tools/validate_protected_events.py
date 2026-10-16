#!/usr/bin/env python3
"""Fail-closed preservation gate for previously published child-friendly event data.

No missing/hidden previously published event is allowed without a distinct, explicit
approval record in the released application policy. The data-staging branch cannot
authorize its own removals. Old weekend files remain in the repository as archives
when they leave the rolling public manifest.
"""
import argparse
import json
import pathlib
import subprocess
import sys

from validate_non_regression import CurrentStore, GitStore, load_bundle

POLICY_APPROVALS = pathlib.Path(__file__).resolve().parents[1] / "policy" / "approved_event_removals.json"


def require_json(store, path, errors):
    raw = store.read_text(path)
    if raw is None:
        errors.append("missing preserved file: " + path)
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError) as exc:
        errors.append("invalid preserved JSON " + path + ": " + str(exc))
        return None


def approved_set(errors):
    try:
        ledger = json.loads(POLICY_APPROVALS.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append("missing or invalid released removal approval ledger: " + str(exc))
        return set()
    entries = ledger.get("approvals", [])
    if not isinstance(entries, list):
        errors.append("approvals must be an array")
        return set()
    approved = set()
    for a in entries:
        if not isinstance(a, dict) or not all([
            a.get("week_start"), a.get("event_id"),
            a.get("approval_reference"), a.get("official_evidence_url", "").startswith("https://"),
            a.get("status") == "approved",
        ]):
            errors.append("invalid removal approval: " + repr(a))
            continue
        key = (a["week_start"], str(a["event_id"]))
        if key in approved:
            errors.append("duplicate removal approval for " + str(key))
        approved.add(key)
    return approved


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base-ref", required=True, help="Previously published immutable baseline ref/SHA")
    p.add_argument("data_dir", nargs="?", default="site/data")
    args = p.parse_args()
    prefix = pathlib.Path(args.data_dir).as_posix().rstrip("/")
    previous = GitStore(args.base_ref)
    current = CurrentStore()
    errors = []
    manifest_path = prefix + "/manifest.json"
    before = require_json(previous, manifest_path, errors)
    after = require_json(current, manifest_path, errors)
    allow = approved_set(errors)
    if not isinstance(before, dict) or not isinstance(after, dict):
        print("\n".join(errors), file=sys.stderr)
        return 1

    present_weeks = {w.get("sat"): w for w in after.get("weekends", []) if isinstance(w, dict)}
    preserved = 0
    for w in before.get("weekends", []):
        if not isinstance(w, dict) or not w.get("sat") or not w.get("file"):
            errors.append("invalid previous weekend entry: " + repr(w))
            continue
        sat, prior_file = w["sat"], w["file"]
        # When a weekend rolls out of the manifest, keep the original dated files
        # on disk and compare against those historical data files.
        new_file = (present_weeks.get(sat) or {}).get("file") or prior_file
        old = load_bundle(previous, prefix, prior_file)
        new = load_bundle(current, prefix, new_file)
        if old is None or new is None:
            errors.append("missing historical week, verification or event index: " + sat)
            continue
        before_by_id = {}
        after_by_id = {}
        for e in old["events"]:
            if not e.get("id"):
                errors.append(sat + ": previous event has no ID")
            elif e["id"] in before_by_id:
                errors.append(sat + ": duplicate previous event ID " + str(e["id"]))
            before_by_id[e.get("id")] = e
        for e in new["events"]:
            if e.get("id") in after_by_id:
                errors.append(sat + ": duplicate new event ID " + str(e.get("id")))
            after_by_id[e.get("id")] = e
        for eid, event in before_by_id.items():
            if eid in after_by_id:
                preserved += 1
                continue
            if (sat, str(eid)) not in allow:
                errors.append("UNAPPROVED EVENT REMOVAL: " + sat + " / " + str(eid) +
                              " / " + str(event.get("name")))
        if sat in present_weeks:
            recorded = present_weeks[sat].get("count")
            if recorded is not None and recorded != len(new["events"]):
                errors.append(sat + ": manifest count disagrees with physical event rows")

    # Protect prior update history from replacement/truncation.
    history_path = prefix + "/update_history.json"
    old_history = require_json(previous, history_path, errors)
    new_history = require_json(current, history_path, errors)
    if isinstance(old_history, dict) and isinstance(new_history, dict):
        old_entries = old_history.get("history", [])
        new_entries = new_history.get("history", [])
        if not isinstance(old_entries, list) or not isinstance(new_entries, list) or new_entries[:len(old_entries)] != old_entries:
            errors.append("historical update_history entries were removed/reordered/changed")

    # Every registered source, including new ones, must remain enabled/configured
    # identically on future iterations. Adding sources is permitted.
    sources_path = prefix + "/discovery_sources.json"
    old_sources = previous.read_text(sources_path)
    new_sources = current.read_text(sources_path)
    if old_sources and new_sources:
        try:
            old_cfg, new_cfg = json.loads(old_sources), json.loads(new_sources)
            old_map = {x["id"]: x for x in old_cfg.get("explicit_sources", [])}
            new_map = {x["id"]: x for x in new_cfg.get("explicit_sources", [])}
            for sid, row in old_map.items():
                if sid not in new_map:
                    errors.append("previous discovery source removed: " + sid)
                elif new_map[sid] != row:
                    candidate = new_map[sid]
                    added = {"annual_listing_url", "annual_resolution_policy", "annual_listing_label"}
                    historical_unchanged = all(candidate.get(key) == value for key, value in row.items())
                    added_fields_exact = set(candidate) - set(row) == added
                    safe_annual_upgrade = (
                        sid == "nerima_district_festivals_2026"
                        and historical_unchanged and added_fields_exact
                        and candidate.get("annual_listing_url") ==
                            "https://www.city.nerima.tokyo.jp/kankomoyoshi/annai/omatsuri/chikusai/index.html"
                        and candidate.get("annual_listing_label") == "練馬区公式 地区祭（年度別開催日程）"
                        and candidate.get("annual_resolution_policy") ==
                            "resolve_fiscal_year_link_from_official_listing_fail_closed"
                    )
                    if not safe_annual_upgrade:
                        errors.append("previous discovery source changed without approval: " + sid)
        except (ValueError, KeyError, TypeError) as exc:
            errors.append("malformed discovery sources: " + str(exc))
    elif old_sources and not new_sources:
        errors.append("discovery_sources.json was removed")

    if errors:
        print("PRESERVATION GATE FAILED:", file=sys.stderr)
        for e in errors:
            print(" - " + e, file=sys.stderr)
        return 1
    print("PRESERVATION GATE PASS: %s previous dated event records retained; no unapproved removals; history intact." % preserved)
    return 0


if __name__ == "__main__":
    sys.exit(main())
