#!/usr/bin/env python3
"""Read-only JST holiday-after six-week refresh planner.

Does not discover, verify, edit or publish events. The released prompt and
existing data-specific validation/deployment pipeline remain authoritative.
"""
import argparse
import csv
import datetime as dt
import io
import json
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

CSV_URL = "https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv"
HOLIDAY_PAGE = "https://www8.cao.go.jp/chosei/shukujitsu/gaiyou.html"
TIERS = ("full", "full", "preview", "preview", "announcement", "announcement")

class PlanError(ValueError):
    pass

def parse_official_csv(raw):
    if isinstance(raw, bytes):
        for encoding in ("utf-8-sig", "cp932"):
            try:
                raw = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                pass
        if isinstance(raw, bytes):
            raise PlanError("cannot decode official holiday CSV")
    holidays = {}
    for row in csv.reader(io.StringIO(raw.lstrip("\ufeff"))):
        if len(row) < 2:
            continue
        try:
            day = dt.datetime.strptime(row[0].strip(), "%Y-%m-%d").date()
        except ValueError:
            continue
        name = row[1].strip()
        if not name or (day in holidays and holidays[day] != name):
            raise PlanError("invalid or conflicting holiday row: " + row[0])
        holidays[day] = name
    if not holidays:
        raise PlanError("empty or unreadable official holiday calendar")
    return holidays

def load_official_holidays(offline_csv=None):
    if offline_csv:
        raw = Path(offline_csv).read_bytes()
    else:
        request = Request(CSV_URL, headers={"User-Agent": "TokyoFamilyEvents-RollingPlanner/1.0"})
        with urlopen(request, timeout=25) as response:
            raw = response.read(3_000_000)
    return parse_official_csv(raw)

def off(day, holidays):
    return day.weekday() >= 5 or day in holidays

def last_holiday_block(day, holidays):
    if off(day, holidays) or not off(day - dt.timedelta(days=1), holidays):
        return None
    end = day - dt.timedelta(days=1)
    start = end
    for _ in range(30):
        if not off(start - dt.timedelta(days=1), holidays):
            return start, end
        start -= dt.timedelta(days=1)
    raise PlanError("holiday block longer than 30 days")

def months(start, end):
    current = start.replace(day=1)
    while current <= end:
        yield current
        current = dt.date(current.year + (current.month == 12), current.month % 12 + 1, 1)

def source_targets(config, start, end):
    strategy = config.get("discovery_strategy") or {}
    if not (strategy.get("ai_cross_search") or {}).get("enabled"):
        raise PlanError("AI cross-search disabled")
    if not (strategy.get("explicit_sources") or {}).get("enabled"):
        raise PlanError("explicit search disabled")
    entries = config.get("explicit_sources") or []
    protected = set(config.get("protected_legacy_source_ids") or [])
    existing = {entry.get("id") for entry in entries}
    if not protected <= existing:
        raise PlanError("missing protected source IDs: " + ", ".join(sorted(protected - existing)))
    targets = []
    for entry in entries:
        if entry.get("enabled") is not True:
            if entry.get("id") in protected:
                raise PlanError("protected source disabled: " + entry["id"])
            continue
        if not entry.get("id") or not entry.get("search_urls"):
            raise PlanError("enabled source missing id/search_urls")
        urls = []
        for template in entry["search_urls"]:
            if not isinstance(template, str) or not template.startswith("https://"):
                raise PlanError("unsafe source URL: " + str(template))
            variable = any(t in template for t in ("{YYYY-MM}", "{YYYY}", "{MM}"))
            for month in (months(start, end) if variable else (start,)):
                url = template.replace("{YYYY-MM}", month.strftime("%Y-%m"))
                url = url.replace("{YYYY}", str(month.year)).replace("{MM}", month.strftime("%m"))
                if "{" in url or "}" in url:
                    raise PlanError("unresolved URL placeholder for " + entry["id"])
                if url not in urls:
                    urls.append(url)
        targets.append({"id": entry["id"], "required": entry.get("required") is True,
                        "urls": urls, "status": "pending", "checked_count": 0})
    if not targets:
        raise PlanError("no enabled explicit sources")
    return targets

def calculate(day, holidays, manifest, sources, base_sha):
    if not re.fullmatch(r"[0-9a-f]{40}", base_sha or ""):
        raise PlanError("missing/invalid data-production base SHA")
    end = day + dt.timedelta(days=41)
    for year in range((day - dt.timedelta(days=31)).year, end.year + 1):
        if dt.date(year, 1, 1) not in holidays or dt.date(year, 11, 23) not in holidays:
            raise PlanError("incomplete Cabinet Office holiday year: " + str(year))
    block = last_holiday_block(day, holidays)
    common = {"schema_version": 1, "as_of_jst": day.isoformat(),
              "holiday_source": HOLIDAY_PAGE, "holiday_csv": CSV_URL,
              "base_data_production_sha": base_sha, "read_only": True,
              "app_code_changes_allowed": False, "published_version_changes_allowed": False}
    if block is None:
        return {**common, "status": "skipped",
                "reason": "not_first_weekday_after_consecutive_days_off"}
    first_sat = day + dt.timedelta(days=(5 - day.weekday()) % 7)
    previous = {w.get("sat"): w for w in manifest.get("weekends", [])}
    weeks = []
    for i, tier in enumerate(TIERS):
        sat = first_sat + dt.timedelta(weeks=i)
        sun = sat + dt.timedelta(days=1)
        if not day <= sat <= sun <= end:
            raise PlanError("weekend out of 42-day horizon")
        prior = previous.get(sat.isoformat())
        weeks.append({"sat": sat.isoformat(), "sun": sun.isoformat(),
                      "file": sat.isoformat() + ".json", "horizon_index": i + 1,
                      "publication_tier": tier, "status": "pending",
                      "action": "re_audit" if prior else "discover_and_verify",
                      "existing_file": prior.get("file") if prior else None})
    holiday_targets = [
        {"date": d.isoformat(), "name": name,
         "day_type": "weekday_holiday" if d.weekday() < 5 else "weekend_holiday",
         "requires_independent_23_ward_search": d.weekday() < 5}
        for d, name in sorted(holidays.items()) if day <= d <= end
    ]
    return {**common, "status": "eligible", "run_type": "holiday_after_update",
            "holiday_block_start": block[0].isoformat(),
            "holiday_block_end": block[1].isoformat(),
            "target_start": day.isoformat(), "target_end": end.isoformat(),
            "rolling_horizon_weeks": 6, "weekends": weeks,
            "holiday_targets": holiday_targets,
            "explicit_source_checks": source_targets(sources, day, end),
            "retired_week_starts": sorted(set(previous) - {w["sat"] for w in weeks}),
            "required_checks": ["released_prompt_governance", "AI_search_each_of_23_wards",
                "explicit_sources_each_required_URL", "official_schedule_row_parity",
                "candidate_decisions", "official_verification", "non_regression",
                "image_and_holiday_coverage", "strict_validation", "update_history",
                "data_only_deploy", "Pages_and_snapshot"],
            "candidate_status": "not_generated", "publication_permitted": False,
            "note": "Plan only. Actual research evidence and strict CI are mandatory."}

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--as-of", help="YYYY-MM-DD in JST (defaults to current JST)")
    p.add_argument("--holiday-csv-file", type=Path, help="offline official CSV for tests")
    p.add_argument("--manifest", type=Path, default=Path("site/data/manifest.json"))
    p.add_argument("--sources", type=Path, default=Path("site/data/discovery_sources.json"))
    p.add_argument("--base-data-production-sha", required=True)
    p.add_argument("--output", type=Path, help="write plan outside site/data only")
    args = p.parse_args(argv)
    try:
        day = dt.date.fromisoformat(args.as_of) if args.as_of else dt.datetime.now(ZoneInfo("Asia/Tokyo")).date()
        holidays = load_official_holidays(args.holiday_csv_file)
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        sources = json.loads(args.sources.read_text(encoding="utf-8"))
        result = calculate(day, holidays, manifest, sources, args.base_data_production_sha)
        payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            if args.output.resolve().is_relative_to(Path("site/data").resolve()):
                raise PlanError("refusing to write unverified plan into public site/data")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
        sys.stdout.write(payload)
        return 0
    except (OSError, ValueError) as error:
        print("BLOCKER: " + str(error), file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
