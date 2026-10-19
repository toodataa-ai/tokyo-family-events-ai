#!/usr/bin/env python3
"""Construct reviewer worklists from published events and *unverified* crawl links.

This is a non-publishable staging artifact.  It never mutates the old manifest,
dated event records, update history or branch references.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import unicodedata


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def norm(value):
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).casefold().split())


def event_identity(ev):
    start, end = ev.get("date_start") or "", ev.get("date_end") or ""
    period = f"{start}|{end}" if start or end else norm(ev.get("period"))
    venue = norm(ev.get("venue"))
    url = ""
    for field in ("official_url", "url"):
        value = ev.get(field)
        if value:
            from urllib.parse import urlsplit
            parsed = urlsplit(value)
            if parsed.scheme == "https":
                url = parsed.hostname.removeprefix("www.") + parsed.path.rstrip("/")
                break
    return f"{norm(ev.get('name'))}|{period}|{('v:' + venue) if venue else ('u:' + url)}"


def is_overlapping(ev, start, end):
    a, b = ev.get("date_start"), ev.get("date_end") or ev.get("date_start")
    return (isinstance(a, str) and isinstance(b, str)
            and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", a))
            and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", b))
            and a <= end and b >= start)


def existing_week(data_dir, week):
    main = read_json(data_dir / week["file"])
    events = list(main.get("events") or [])
    for shard in main.get("event_files") or []:
        events.extend(read_json(data_dir / shard))
    return events


def build_packet(plan, published_dir, collected):
    if plan.get("status") != "eligible":
        raise ValueError("not an eligible holiday-after update")
    summary = collected["summary"]
    if summary.get("publishable") is not False:
        raise ValueError("crawler's unverified evidence cannot authorize publication")
    if summary.get("base_data_production_sha") != plan.get("base_data_production_sha"):
        raise ValueError("baseline SHA mismatch")
    published = read_json(published_dir / "manifest.json")
    old_weeks = {w["sat"]: w for w in published["weekends"]}
    originals = {sat: existing_week(published_dir, w) for sat, w in old_weeks.items()}
    discovered = collected["candidate_pool"]
    weekly = []
    for target in plan["weekends"]:
        sat, sun = target["sat"], target["sun"]
        already_listed = sat in originals
        if already_listed:
            prior = originals[sat]
        else:
            carried = {}
            for old_sat, rows in sorted(originals.items()):
                for ev in rows:
                    if is_overlapping(ev, sat, sun):
                        carried[event_identity(ev)] = {
                            "previous_week": old_sat, "event": ev}
            prior = [x["event"] for x in carried.values()]
        identified = {event_identity(ev) for ev in prior}
        from datetime import date, timedelta
        following_day = (date.fromisoformat(sun) + timedelta(days=1)).isoformat()
        holiday_extension = any(h.get("date") == following_day for h in plan.get("holiday_targets", []))
        target_dates = [sat, sun] + ([following_day] if holiday_extension else [])
        links = []
        for c in discovered:
            via = c.get("discovered_via") or {}
            week_ref = via.get("query") or ""
            iso_hit = any(day in week_ref for day in target_dates)
            local_hit = any(day.replace("-", "年", 1).replace("-", "月", 1) + "日" in week_ref for day in target_dates)
            if via.get("search_url") and (via.get("ward") or "").strip():
                if iso_hit or local_hit:
                    links.append(c)
            elif c.get("matched_dates") and any(sat <= day <= (following_day if holiday_extension else sun)
                                                  for day in c["matched_dates"]):
                links.append(c)
        weekly.append({
            "sat": sat, "sun": sun, "tier": target["publication_tier"],
            "existing_week": already_listed,
            "prior_published_count": len(prior) if already_listed else 0,
            "carryover_review_count": 0 if already_listed else len(prior),
            "carryover_needs_daily_confirmation": not already_listed,
            "protected_prior_event_ids": sorted({ev.get("id") for ev in prior if ev.get("id")}),
            "suggested_discoveries_count": len(links),
            "suggested_discoveries": links,
            "review_state": "needs_individual_official_event_checks_and_decisions"
        })
    return {
        "schema_version": 1, "kind": "holiday_after_reviewer_packet",
        "read_only": True, "publication_permitted": False,
        "as_of_jst": plan["as_of_jst"], "base_data_production_sha": plan["base_data_production_sha"],
        "published_history_preserved": True, "published_week_file_changes": 0,
        "required_source_failures": summary.get("required_source_failures") or [],
        "annual_schedule": summary.get("annual_schedule") or [],
        "wards": summary["wards"],
        "weeks": weekly,
        "approval_requirements": [
            "Reconcile every official schedule row with a published/excluded/duplicate decision",
            "Verify each new event's date, venue and official evidence for its participation unit",
            "Independently check both weekday holidays (November 3 and 23)",
            "Preserve each prior current-week event ID or obtain explicit removal approval",
            "Produce actual per-week 23-ward and required-source query logs",
            "Run all released strict validators, protected-event gate and npm test",
            "Append exact update history and use the unchanged data-only CI path"
        ],
        "note": "An old event spanning a target week is a review candidate, NOT proof it runs every holiday."
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--evidence-dir", type=Path, required=True)
    p.add_argument("--published-data", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    evidence = {name: read_json(args.evidence_dir / (name + ".json"))
                for name in ("summary", "candidate_pool")}
    packet = build_packet(read_json(args.plan), args.published_data, evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print("REVIEW PACKET generated; publication still blocked; weeks=%d" % len(packet["weeks"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
