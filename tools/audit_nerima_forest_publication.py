#!/usr/bin/env python3
"""Read-only reconciliation: each official Nerima forest festival row -> a published event.

HTTP success or 11 parsed source rows is not enough. The candidate must also be
present with the right *individual date and venue* in every target data set.
This never creates events, changes decisions, or waives failed sources.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import sys
import unicodedata
from urllib.request import Request, urlopen

try:
    from .nerima_forest_schedule import parse_schedule, SOURCE_URL
except ImportError:  # CLI invocation from tools/
    from nerima_forest_schedule import parse_schedule, SOURCE_URL


def compact(value):
    normalized = unicodedata.normalize("NFKC", str(value or ""))
    return re.sub(r"[\s「」『』()（）・,.，。、\-－]", "", normalized).lower()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def published_events(directory):
    root = Path(directory)
    manifest = read_json(root / "manifest.json")
    entries = manifest.get("weekends", [])
    if not entries:
        raise ValueError("No published weekend entries")
    all_events = {}
    for entry in entries:
        week = read_json(root / entry["file"])
        shards = list(week.get("event_files", []))
        rows = list(week.get("events", []) or [])
        for shard in shards:
            data = read_json(root / shard)
            if not isinstance(data, list):
                raise ValueError("Non-list event shard: " + shard)
            rows.extend(data)
        if len(rows) != int(week["coverage"]["published_count"]):
            raise ValueError("Published-count mismatch for " + entry["sat"])
        for event in rows:
            key = str(event.get("id", ""))
            if not key:
                raise ValueError("Missing published event ID")
            if key in all_events and event != all_events[key]["event"]:
                raise ValueError("Same published ID has conflicting contents: " + key)
            if key not in all_events:
                all_events[key] = {"event": event, "week_windows": []}
            all_events[key]["week_windows"].append((entry["sat"], entry["sun"]))
    start = dt.date.fromisoformat(entries[0]["sat"])
    end = dt.date.fromisoformat(entries[-1]["sun"])
    return start, end, all_events


def reconcile(source_html, published_directory):
    start, end, records = published_events(published_directory)
    official = parse_schedule(source_html, start, end)
    candidates = official["candidates"]
    details = []
    for row in candidates:
        date = row["date_start"]
        target_name = compact(row["name"])
        # Official venue may append location in parentheses; compare base name
        # while still requiring the venue, not merely a shared festival title.
        target_venue = compact(re.split(r"[（(]", row["venue"], maxsplit=1)[0])
        matches = []
        for event_id, entry in records.items():
            event = entry["event"]
            if not any(sat <= date <= sun for sat, sun in entry["week_windows"]):
                continue
            if not (event.get("date_start", "") <= date <= event.get("date_end", "")):
                continue
            if target_name not in compact(event.get("name")):
                continue
            if target_venue not in compact(event.get("venue")):
                continue
            origin = {event.get("official_url"), event.get("source"), event.get("url")}
            if SOURCE_URL not in origin:
                continue
            matches.append(event_id)
        state = "published" if len(matches) == 1 else ("missing" if not matches else "ambiguous")
        details.append({"date": date, "official_programme": row["name"],
                        "official_venue": row["venue"],
                        "status": state, "published_event_ids": matches})
    missing = [item for item in details if item["status"] != "published"]
    return {
        "source_url": SOURCE_URL, "official_row_count": official["official_row_count"],
        "in_horizon_official_rows": len(candidates),
        "outside_horizon_official_rows": official["outside_target_count"],
        "published_rows": len(details) - len(missing),
        "unreconciled_rows": len(missing),
        "horizon_start": str(start), "horizon_end": str(end),
        "status": "complete" if not missing else "incomplete",
        "rows": details,
        "note": "Individual date/name/venue and primary-source URL required; no publication side effects.",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--published-dir", default="site/data")
    p.add_argument("--html-file", help="Offline official HTML fixture (tests/forensics)")
    p.add_argument("--output", help="JSON audit report path")
    p.add_argument("--strict", action="store_true", help="Exit nonzero on any missing row")
    args = p.parse_args(argv)
    try:
        if args.html_file:
            html = Path(args.html_file).read_text(encoding="utf-8")
        else:
            with urlopen(Request(SOURCE_URL, headers={
                "User-Agent": "TokyoFamilyEvents/1.21 official row-publication audit"
            }), timeout=30) as response:
                html = response.read(4_000_000).decode("utf-8")
        result = reconcile(html, args.published_dir)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print("BLOCKER FOREST_PUBLICATION_AUDIT:", exc, file=sys.stderr)
        return 2
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)
    print("FOREST_OFFICIAL_TO_PUBLISHED", result["status"],
          result["published_rows"], "/", result["in_horizon_official_rows"])
    return 1 if args.strict and result["unreconciled_rows"] else 0


if __name__ == "__main__":
    sys.exit(main())
