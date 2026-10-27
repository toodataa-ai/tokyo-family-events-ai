#!/usr/bin/env python3
"""Read-only official-candidate -> decision -> actual publication reconciliation.

Reusable for official annual tables and day-by-day calendars. Never invents a
decision, treats an HTTP error as zero events, or modifies published records.
"""
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import re
import unicodedata


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def canonical_url(value):
    if not value:
        return ""
    p = urlsplit(str(value))
    if p.scheme != "https" or not p.hostname:
        return ""
    return urlunsplit((p.scheme, p.netloc.lower(), p.path.rstrip("/"), "", ""))


def compact(value):
    value = unicodedata.normalize("NFKC", str(value or ""))
    return re.sub(r"[\s()（）「」『』・、,.，。-]", "", value).lower()


def venue_matches(a, b):
    """Exact named venue, permitting ward-prefix changes in postal addresses."""
    a, b = str(a or ""), str(b or "")
    venue_a, venue_b = (compact(re.split(r"[（(]", v, 1)[0]) for v in (a, b))
    if not venue_a or venue_a != venue_b:
        return False
    address_a, address_b = (compact(v).replace("東京都", "").replace("練馬区", "")
                           .replace("杉並区", "") for v in (a, b))
    nums_a, nums_b = (re.findall(r"\d+", x) for x in (address_a, address_b))
    # Both sides have an address: inconsistent numbered addresses must fail.
    if nums_a and nums_b and nums_a[-3:] != nums_b[-3:]:
        return False
    return True


def suginami_verified_alias(candidate, event):
    """Only one independently cross-verified municipal->organizer page alias.

    Confirmed by the municipal detail page linking directly to the festival
    organizer, and identical Nov 7-8 dates and Momoi Harappa Park location.
    It must not turn individual programs into separate parent cards.
    """
    return (
        candidate.get("candidate_id") == "suginami-official-22661"
        and canonical_url(candidate.get("official_url")) ==
            "https://www.city.suginami.tokyo.jp/s019/event/22661.html"
        and event.get("id") == "official-2026-suginami-festa"
        and canonical_url(event.get("official_url")) ==
            "https://www.sugifes.com/event"
        and compact(candidate.get("name", "")).startswith(compact("すぎなみフェスタ2026"))
        and compact(event.get("name", "")).startswith(compact("すぎなみフェスタ2026"))
        and "桃井原っぱ公園" in str(event.get("venue", ""))
    )


def load_published(root):
    root = Path(root)
    manifest = read_json(root / "manifest.json")
    weeks = manifest.get("weekends", [])
    if not weeks or len({w["sat"] for w in weeks}) != len(weeks):
        raise ValueError("missing or duplicate published weekends")
    holidays = set()
    for row in manifest.get("holidays", []):
        date = dt.date.fromisoformat(row["date"])
        holidays.add(date.isoformat())
    all_events = []
    all_decisions = []
    target_dates = set()
    for w in weeks:
        sat, sun = (dt.date.fromisoformat(w[k]) for k in ("sat", "sun"))
        if sun < sat:
            raise ValueError("invalid weekend range")
        ownership = {str(sat), str(sun)}
        # An independent weekday holiday lives in the preceding weekend shard.
        ownership.update(h for h in holidays if sun < dt.date.fromisoformat(h) <= sat + dt.timedelta(days=6))
        target_dates.update(ownership)
        doc = read_json(root / w["file"])
        rows = list(doc.get("events", []) or [])
        if len(set(doc.get("event_files", []))) != len(doc.get("event_files", [])):
            raise ValueError("duplicate event shard")
        for shard in doc.get("event_files", []):
            item = read_json(root / shard)
            if not isinstance(item, list):
                raise ValueError("non-list event shard: " + shard)
            rows.extend(item)
        if len(rows) != int(doc["coverage"]["published_count"]):
            raise ValueError("published count mismatch " + w["sat"])
        ids = [str(ev["id"]) for ev in rows]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate event id in " + w["sat"])
        for ev in rows:
            all_events.append({"week": w["sat"], "owned_dates": ownership, "event": ev})
        dp = root / (w["sat"] + "-decisions.json")
        if not dp.exists():
            raise ValueError("missing decisions file " + dp.name)
        decisions = read_json(dp).get("decisions", [])
        for decision in decisions:
            all_decisions.append({"week": w["sat"], "owned_dates": ownership, "decision": decision})
    return {"manifest": manifest, "events": all_events, "decisions": all_decisions,
            "start": weeks[0]["sat"], "end": weeks[-1]["sun"],
            "target_dates": target_dates, "holidays": holidays}


def candidate_days(candidate, snapshot):
    provided = candidate.get("matched_dates") or candidate.get("dates")
    if provided is None and candidate.get("date_start") == candidate.get("date_end"):
        provided = [candidate["date_start"]]
    if not isinstance(provided, list):
        return []
    start, end = snapshot["start"], snapshot["end"]
    out = []
    for raw in provided:
        day = str(dt.date.fromisoformat(str(raw)))
        if start <= day <= end and day in snapshot["target_dates"] and day not in out:
            out.append(day)
    return out


def publication_match(candidate, event, source_id, date):
    value = event["event"]
    if not (str(value.get("date_start", "")) <= date <= str(value.get("date_end", ""))):
        return False
    if date not in event["owned_dates"]:
        return False
    cid = str(candidate["candidate_id"])
    eid = str(value.get("id", ""))
    if cid.startswith("nerima-district-") and source_id == "nerima_district_festivals_2026":
        # Exact event ID is preferred; a *legacy* ID is accepted only if
        # official URL, individually named festival, date and venue all agree.
        if eid != cid and compact(value.get("name")) != compact(candidate.get("name")):
            return False
        expected = candidate.get("official_url")
        if not expected or canonical_url(expected) not in {
                canonical_url(value.get("official_url")), canonical_url(value.get("url"))}:
            return False
        if not venue_matches(candidate.get("venue"), value.get("venue")):
            return False
        return True
    if source_id == "suginami_calendar_all":
        # The official event detail URL is a unique stronger key than title;
        # list snippets may abbreviate/rename the published display title.
        source = canonical_url(candidate.get("official_url"))
        if not source:
            return False
        return (source in {canonical_url(value.get("official_url")),
                           canonical_url(value.get("url"))} or
                suginami_verified_alias(candidate, value))
    return False


def reconcile(source_id, candidates, snapshot, *, source_status, expected_count=None, source_notes=None):
    if source_status != "checked":
        return {"source_id": source_id, "status": "source_error",
                "reason": "source retrieval/coverage was not verified",
                "source_notes": source_notes or {}, "candidate_count": None,
                "rows": [], "unreconciled_count": None}
    if not isinstance(candidates, list):
        raise ValueError("candidates must be a list")
    if expected_count is not None and expected_count != len(candidates):
        raise ValueError("source candidate count mismatch")
    ids = [str(x.get("candidate_id", "")) for x in candidates]
    if any(not x for x in ids) or len(ids) != len(set(ids)):
        raise ValueError("missing/duplicate official candidate IDs")
    rows = []
    for c in candidates:
        dates = candidate_days(c, snapshot)
        if not dates:
            raw = c.get("matched_dates") or c.get("dates")
            if raw is None and c.get("date_start") == c.get("date_end"):
                raw = [c["date_start"]]
            state = "out_of_scope" if isinstance(raw, list) and len(raw) else "needs_date_review"
            reason = ("Official event occurs on an ordinary weekday outside the published weekends/holidays"
                      if state == "out_of_scope" else "Monthly-only discovery or no trustworthy event date")
            rows.append({"candidate_id": c["candidate_id"], "name": c.get("name"),
                         "dates": [], "status": state, "matched_ids": [], "reason": reason})
            continue
        for date in dates:
            hits = {e["event"]["id"] for e in snapshot["events"]
                    if publication_match(c, e, source_id, date)}
            # A published row may use a stable *historical* ID rather than
            # an official crawler ID. Recognize its existing decision only
            # when the target event is unique and the decision matches the
            # individual event title plus the primary-source proof URL.
            matched_event = next((e["event"] for e in snapshot["events"]
                                  if e["event"]["id"] in hits and
                                  publication_match(c, e, source_id, date)), None) if len(hits) == 1 else None
            decisions = []
            for p in snapshot["decisions"]:
                d = p["decision"]
                if date not in p["owned_dates"]:
                    continue
                if d.get("candidate_id") == c["candidate_id"]:
                    decisions.append(d)
                    continue
                if (matched_event and d.get("decision") == "published" and
                        compact(d.get("name")) == compact(matched_event.get("name")) and
                        any(canonical_url(proof.get("url")) in
                            {canonical_url(matched_event.get("official_url")),
                             canonical_url(c.get("official_url"))}
                            for proof in d.get("evidence", []) if isinstance(proof, dict))):
                    decisions.append(d)
            decision_types = set(d.get("decision") for d in decisions)
            if len(hits) > 1:
                status, reason = "ambiguous", "multiple published event IDs"
            elif hits:
                if "excluded" in decision_types or "duplicate" in decision_types:
                    status, reason = "inconsistent", "publication contradicts exclusion"
                elif "published" not in decision_types:
                    status, reason = "inconsistent", "published event lacks scoped published decision"
                else:
                    status, reason = "published", ""
            elif "published" in decision_types:
                status, reason = "inconsistent", "published decision lacks matching event"
            elif len(decision_types) > 1:
                status, reason = "inconsistent", "conflicting scoped decisions"
            elif decision_types in ({"excluded"}, {"duplicate"}):
                d = next(d for d in decisions if d.get("decision") in decision_types)
                if (d.get("hard_exclusion") == "date_mismatch" or
                        not (d.get("reasons") or d.get("reason_codes")) or not d.get("evidence")):
                    status, reason = "inconsistent", "unsubstantiated or wrong-date decision"
                else:
                    status, reason = next(iter(decision_types)), ""
            else:
                status, reason = "unreviewed", "no matching published record or scoped decision"
            rows.append({"candidate_id": c["candidate_id"], "name": c.get("name"),
                         "dates": [date], "status": status, "matched_ids": sorted(hits),
                         "reason": reason})
    breakdown = {status: sum(r["status"] == status for r in rows)
                 for status in ("published", "excluded", "duplicate", "out_of_scope",
                                "unreviewed", "ambiguous", "inconsistent", "needs_date_review")}
    unresolved = sum(v for k, v in breakdown.items() if k not in ("published", "excluded", "duplicate", "out_of_scope"))
    return {"source_id": source_id, "status": "complete" if not unresolved else "incomplete",
            "candidate_count": len(candidates),
            "in_scope_candidate_count": len({r["candidate_id"] for r in rows if r["status"] != "out_of_scope"}),
            "date_scoped_rows": len([r for r in rows if r["status"] != "out_of_scope"]),
            "breakdown": breakdown, "unreconciled_count": unresolved, "source_notes": source_notes or {},
            "rows": rows, "read_only": True}
