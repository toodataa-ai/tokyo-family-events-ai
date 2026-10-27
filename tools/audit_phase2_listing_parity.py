#!/usr/bin/env python3
"""Phase 2 read-only reconciliation of paginated/article evidence with live shards.

A news article is *not* sufficient official evidence to publish a festival.
No invented date, event card, decision, or auto-approved source.
"""
import argparse
import json
from pathlib import Path
try:
    from .source_coverage_reconcile import load_published, canonical_url, compact
except ImportError:
    from source_coverage_reconcile import load_published, canonical_url, compact


def same_link(a, b):
    return bool(canonical_url(a) and canonical_url(a) == canonical_url(b))


def reconcile_source(source, snapshot):
    sid = source["source_id"]
    seen = set()
    rows = []
    for c in source.get("candidates", []):
        cid = c["candidate_id"]
        if cid in seen:
            raise ValueError("repeated candidate identity " + cid)
        seen.add(cid)
        kind = c.get("candidate_type")
        if kind == "collection_index":
            state, matches, reason = "index_only", [], "roundup is an index, never an independent event card"
        else:
            hits = []
            for p in snapshot["events"]:
                e = p["event"]
                if not any(same_link(c.get("discovery_url"), e.get(k))
                           for k in ("source", "official_url", "url")):
                    continue
                # A source reused by many published programmes cannot by itself
                # establish a single event mapping.
                dates = set(c.get("date_hints") or [])
                if dates and not any(e.get("date_start", "") <= d <= e.get("date_end", "")
                                     for d in dates if d in p["owned_dates"]):
                    continue
                hits.append(e)
            matches = sorted({e["id"] for e in hits})
            if len(matches) > 1:
                state, reason = "ambiguous_existing_links", "source URL appears on multiple published events"
            elif len(matches) == 1:
                # Detect already-published links, but a scraped news title/date
                # is not proof that the event was verified against its organizer.
                d_matches = [p["decision"] for p in snapshot["decisions"]
                             if p["decision"].get("candidate_id") == matches[0]
                             and p["decision"].get("decision") == "published"]
                event = hits[0]
                has_official_url = bool(canonical_url(event.get("official_url")))
                verified_decision = bool(d_matches and has_official_url and
                                         any(same_link(q.get("url"), event.get("official_url"))
                                             for d in d_matches for q in d.get("evidence", [])))
                state = "existing_publication" if verified_decision else "existing_link_needs_proof"
                reason = "" if verified_decision else "published link exists but decision/primary proof not established"
            elif not c.get("date_hints"):
                state, reason = "needs_date_review", "article date not independently established"
            else:
                state, reason = "unreviewed_candidate", "no matching published source link; primary review required"
            if kind == "roundup_child_lead":
                # Children discovered only through a roundup require their own
                # date and primary source confirmation before any card.
                if state not in ("existing_publication", "existing_link_needs_proof"):
                    state = "roundup_child_unverified"
                    reason = "child link from summary; needs individual and organizer verification"
        rows.append({"candidate_id": cid, "name": c.get("name"), "discovery_url": c.get("discovery_url"),
                     "candidate_type": kind, "date_hints": c.get("date_hints", []),
                     "status": state, "matched_event_ids": matches, "reason": reason})
    stats = {s: sum(row["status"] == s for row in rows)
             for s in ("existing_publication", "existing_link_needs_proof",
                       "index_only", "unreviewed_candidate", "needs_date_review",
                       "ambiguous_existing_links", "roundup_child_unverified")}
    err = source.get("status") != "checked" or bool(source.get("failures"))
    unresolved = sum(v for k, v in stats.items() if k not in ("existing_publication", "index_only"))
    return {
        "source_id": sid,
        "status": "source_error" if err else ("complete" if not unresolved else "incomplete"),
        "candidate_count": None if err else len(rows),
        "observed_candidate_count": len(rows),
        "listing_pages": source.get("listing_pages_checked", []),
        "source_errors": source.get("failures", []),
        "breakdown": stats, "unresolved_count": None if err else unresolved,
        "rows": rows, "read_only": True,
        "publication_approvals_created": 0,
        "note": "Discovered candidates are not automatically published; collection indexes are not cards.",
    }


def audit(published_dir, input_path):
    snapshot = load_published(published_dir)
    report = json.loads(Path(input_path).read_text(encoding="utf-8"))
    if report.get("read_only") is not True or report.get("horizon") != [snapshot["start"], snapshot["end"]]:
        raise ValueError("source artifact horizon/read_only mismatch")
    sources = report.get("sources")
    if not isinstance(sources, list) or len({s["source_id"] for s in sources}) != len(sources):
        raise ValueError("missing or duplicate source evidence")
    return {"schema_version": 1, "horizon": report["horizon"], "read_only": True,
            "sources": [reconcile_source(s, snapshot) for s in sources],
            "status": "complete" if sources and all(s["status"] == "complete" for s in
                     [reconcile_source(x, snapshot) for x in sources]) else "incomplete"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--published-dir", required=True)
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--strict", action="store_true")
    args = p.parse_args()
    try:
        result = audit(args.published_dir, args.input)
    except (OSError, ValueError, KeyError, TypeError) as e:
        result = {"status": "error", "error": str(e), "read_only": True, "sources": []}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({s["source_id"]: {"status": s["status"],
          "observed_candidates": s["observed_candidate_count"],
          "unresolved": s["unresolved_count"], "breakdown": s["breakdown"]}
          for s in result.get("sources", [])}, ensure_ascii=False))
    return 1 if args.strict and result["status"] != "complete" else 0


if __name__ == "__main__":
    raise SystemExit(main())
