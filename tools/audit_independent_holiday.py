#!/usr/bin/env python3
"""Read-only gap detection for official weekday-holiday event leads.

A long-running exhibition crossing a holiday does not prove that a separate
holiday-only festival is covered. Reporting leads does NOT publish records.
"""
import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit


def normalize(text):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(text or "")).casefold())


def normalize_url(raw):
    p = urlsplit(str(raw or ""))
    if p.scheme not in ("http", "https") or not p.hostname:
        return ""
    return p.hostname.removeprefix("www.") + p.path.rstrip("/")


def get_events(root, manifest):
    events = []
    for week in manifest.get("weekends", []):
        doc = json.loads((root / week["file"]).read_text(encoding="utf-8"))
        entries = list(doc.get("events") or [])
        for shard in doc.get("event_files") or []:
            entries += json.loads((root / shard).read_text(encoding="utf-8"))
        if len(entries) != week["count"]:
            raise ValueError(f"manifest count differs from actual data: {week['sat']}")
        events.extend(entries)
    return events


def audit(manifest, published, leads, holiday):
    day = date.fromisoformat(holiday)
    if day.weekday() >= 5:
        raise ValueError("requested date must be an independent weekday")
    if holiday not in {h.get("date") for h in manifest.get("holidays", [])}:
        raise ValueError("requested date is not an official registered holiday")
    weeks = sorted(manifest["weekends"], key=lambda w: w["sat"])
    assigned = next((w for i,w in enumerate(weeks)
                     if date.fromisoformat(w["sun"]) < day <
                     (date.fromisoformat(weeks[i+1]["sat"]) if i+1 < len(weeks)
                      else date.fromisoformat(w["sat"]) + timedelta(days=7))), None)
    if not assigned:
        raise ValueError("holiday is not attached to any published weekend")
    exact_day = [r for r in published if r.get("date_start") == holiday and r.get("date_end") == holiday]
    broad = [r for r in published if str(r.get("date_start") or "") <= holiday <= str(r.get("date_end") or "")]
    seen = set()
    queue = []
    for lead in leads:
        if lead.get("day") != holiday and lead.get("date_start") != holiday:
            continue
        name, url = normalize(lead.get("name")), normalize_url(lead.get("official_url"))
        if not name:
            raise ValueError("known lead missing title")
        if (name,url) in seen:
            continue
        seen.add((name,url))
        matched = next((r for r in published
                        if str(r.get("date_start") or "") <= holiday <= str(r.get("date_end") or "")
                        and (normalize(r.get("name")) == name
                             or (url and normalize_url(r.get("official_url")) == url))), None)
        queue.append({
            "name": lead["name"], "ward": lead.get("ward"),
            "official_url": lead.get("official_url"),
            "source_review_status": lead.get("status", "official_lead_needs_record_review"),
            "published_match_id": matched.get("id") if matched else None,
            "status": "already_published" if matched else "missing_from_published_dataset"
        })
    return {
        "date": holiday, "assigned_week_sat": assigned["sat"],
        "published_holiday_only_count": len(exact_day),
        "published_broad_overlap_count": len(broad),
        "published_overlap_is_not_proof_of_individual_holiday_program": True,
        "known_leads_checked": len(queue),
        "unpublished_known_leads": sum(r["published_match_id"] is None for r in queue),
        "leads": queue, "publication_permitted": False,
        "source_manifest_unchanged": True
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--published-dir", type=Path, required=True)
    ap.add_argument("--leads", type=Path, required=True)
    ap.add_argument("--holiday", required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    if a.output.resolve().is_relative_to(a.published_dir.resolve()):
        ap.error("refusing to write research output inside site/data")
    manifest = json.loads((a.published_dir / "manifest.json").read_text(encoding="utf-8"))
    lead_doc = json.loads(a.leads.read_text(encoding="utf-8"))
    result = audit(manifest, get_events(a.published_dir, manifest),
                   lead_doc.get("entries") or [], a.holiday)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k != "leads"}, ensure_ascii=False))
    if a.strict and result["unpublished_known_leads"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
