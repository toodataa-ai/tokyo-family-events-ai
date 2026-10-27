#!/usr/bin/env python3
"""First-phase read-only source coverage: Nerima annual district festivals and Suginami calendar.

Consumes real source-evidence artifacts from the existing specialized crawlers;
no web fetch is performed by the reconciler and no published file is changed.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import sys

try:
    from .source_coverage_reconcile import load_published, reconcile, read_json
except ImportError:
    from source_coverage_reconcile import load_published, reconcile, read_json


def nerima_input(report_file):
    if not report_file or not Path(report_file).exists():
        return [], "error", None, {"blocker": "missing Nerima official annual source report"}
    doc = read_json(report_file)
    if doc.get("status") != "checked" or doc.get("source_checked") is not True:
        return [], "error", None, {"blocker": doc.get("error", "official annual source failed")}
    candidates = doc.get("candidates")
    count = doc.get("candidate_count")
    pages = doc.get("resolved_pages") or []
    if (not isinstance(candidates, list) or not isinstance(count, int) or count != len(candidates)
            or not pages or any(not p.get("resolved_url") for p in pages)):
        return [], "error", None, {"blocker": "incomplete annual fiscal-year evidence"}
    return candidates, "checked", count, {"resolved_pages": pages, "official_listing_url": doc.get("official_listing_url")}


def suginami_input(evidence_dir, start, end):
    if not evidence_dir:
        return [], "error", None, {"blocker": "missing Suginami 42-day source evidence"}
    root = Path(evidence_dir)
    try:
        index = read_json(root / "all_candidate_index.json")
        http = read_json(root / "http_evidence.json")
    except (OSError, ValueError) as err:
        return [], "error", None, {"blocker": "source artifact unreadable: " + str(err)}
    days = {(start + dt.timedelta(days=i)).isoformat() for i in range((end - start).days + 1)}
    months = {d[:7] for d in days}
    observed = http.get("checked_requests") or []
    day_rows = [r for r in observed if r.get("day")]
    month_rows = [r for r in observed if r.get("month")]
    actual_days = [r["day"] for r in day_rows]
    actual_months = [r["month"] for r in month_rows]
    problems = []
    if http.get("start") != str(start) or http.get("end") != str(end):
        problems.append("crawl period does not match manifest horizon")
    if set(actual_days) != days or len(actual_days) != len(days):
        problems.append("missing, duplicate or extra daily calendar page")
    if set(actual_months) != months or len(actual_months) != len(months):
        problems.append("missing, duplicate or extra monthly calendar index")
    if any(row.get("status") != "checked" for row in observed):
        problems.append("source HTTP/parse failure")
    if http.get("failed_requests") or http.get("official_detail_fetch_failures"):
        problems.append("source/detail fetch failures")
    if not isinstance(index, list) or http.get("distinct_official_candidate_ids") != len(index):
        problems.append("official candidate index/count mismatch")
    if isinstance(index, list) and any(c.get("detail_status") != "checked" for c in index):
        problems.append("event detail was not verified as accessible")
    if problems:
        return [], "error", None, {"blocker": "; ".join(problems),
                                  "failed_requests": http.get("failed_requests")}
    # Monthly-only leads have no reliable date. They must be inspected, never
    # quietly classified as published based on the whole site or month alone.
    return index, "checked", len(index), {
        "days_scanned": len(day_rows), "monthly_indexes_scanned": len(month_rows),
        "detail_pages_checked": len(index)}


def audit(published_dir, *, nerima_report=None, suginami_evidence_dir=None, sources=("nerima", "suginami")):
    snapshot = load_published(published_dir)
    start, end = dt.date.fromisoformat(snapshot["start"]), dt.date.fromisoformat(snapshot["end"])
    outputs = []
    if "nerima" in sources:
        candidates, status, count, notes = nerima_input(nerima_report)
        outputs.append(reconcile("nerima_district_festivals_2026", candidates, snapshot,
                                 source_status=status, expected_count=count, source_notes=notes))
    if "suginami" in sources:
        candidates, status, count, notes = suginami_input(suginami_evidence_dir, start, end)
        outputs.append(reconcile("suginami_calendar_all", candidates, snapshot,
                                 source_status=status, expected_count=count, source_notes=notes))
    # Source errors are not converted to candidate_count=0 or a valid pass.
    return {"schema_version": 1, "audit_mode": "read_only", "horizon": [str(start), str(end)],
            "sources": outputs, "status": "complete" if outputs and all(s["status"] == "complete" for s in outputs)
            else "incomplete"}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--published-dir", type=Path, required=True)
    p.add_argument("--nerima-report", type=Path)
    p.add_argument("--suginami-evidence-dir", type=Path)
    p.add_argument("--sources", choices=["both", "nerima", "suginami"], default="both")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--strict", action="store_true")
    args = p.parse_args(argv)
    sources = ("nerima", "suginami") if args.sources == "both" else (args.sources,)
    try:
        result = audit(args.published_dir, nerima_report=args.nerima_report,
                       suginami_evidence_dir=args.suginami_evidence_dir, sources=sources)
    except (OSError, ValueError, KeyError, TypeError) as err:
        result = {"schema_version": 1, "status": "error", "error": str(err),
                  "audit_mode": "read_only", "sources": []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "sources": [
        {"source_id": s["source_id"], "status": s["status"],
         "candidate_count": s.get("candidate_count"), "unreconciled": s.get("unreconciled_count"),
         "breakdown": s.get("breakdown")} for s in result.get("sources", [])]},
        ensure_ascii=False))
    return 1 if args.strict and result["status"] != "complete" else 0


if __name__ == "__main__":
    sys.exit(main())
