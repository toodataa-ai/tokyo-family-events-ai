#!/usr/bin/env python3
"""Guard publication against missing weekday holidays within the six-week horizon.

Reads the official Cabinet Office holiday CSV and a candidate manifest.
Never creates data or marks any event facts verified.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import sys

from rolling_horizon import load_official_holidays


def coverage(manifest, official, today=None):
    weeks = sorted(manifest.get("weekends") or [], key=lambda w: w["sat"])
    if len(weeks) != 6:
        raise ValueError("six published weekends required")
    start = dt.date.fromisoformat(weeks[0]["sat"])
    end = dt.date.fromisoformat(weeks[-1]["sun"])
    if end < start:
        raise ValueError("invalid published date horizon")
    registered = set()
    for row in manifest.get("holidays") or []:
        if isinstance(row, dict):
            value = row.get("date")
            if value:
                registered.add(dt.date.fromisoformat(value))
    missing = sorted(
        {"date": day.isoformat(), "name": name}
        for day, name in official.items()
        if start <= day <= end and day.weekday() < 5 and day not in registered
    , key=lambda x: x["date"])
    upcoming = [row for row in missing
                if today is None or row["date"] >= today.isoformat()]
    return {
        "start": start.isoformat(), "end": end.isoformat(),
        "registered_holidays": len(registered),
        "missing_independent_weekday_holidays": missing,
        "upcoming_missing_holidays": upcoming,
        "publication_permitted": not bool(missing),
        "coverage_is_calendar_only_not_event_verification": True,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--holiday-csv-file", type=Path)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--as-of", default="")
    args = ap.parse_args()
    try:
        today = dt.date.fromisoformat(args.as_of) if args.as_of else None
        actual = json.loads(args.manifest.read_text(encoding="utf-8"))
        audit = coverage(actual, load_official_holidays(args.holiday_csv_file), today)
        print(json.dumps(audit, ensure_ascii=False, indent=2))
        if args.strict and audit["missing_independent_weekday_holidays"]:
            print("BLOCKER: official weekday holidays missing from published horizon manifest", file=sys.stderr)
            return 2
    except (OSError, ValueError) as error:
        print("BLOCKER: cannot verify official holiday calendar:", error, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
