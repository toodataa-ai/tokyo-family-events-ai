#!/usr/bin/env python3
"""Read-only individual official source verification of 6-week discovery leads.

Only structured Event evidence with a concrete date and official venue can be
automatically elevated to a review-ready factual record. No data publication,
candidate decision, status=verified, or old ID edit occurs in this tool.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.error import URLError, HTTPError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

WARDS = ("千代田区 中央区 港区 新宿区 文京区 台東区 墨田区 江東区 品川区 目黒区 "
         "大田区 世田谷区 渋谷区 中野区 杉並区 豊島区 北区 荒川区 "
         "板橋区 練馬区 足立区 葛飾区 江戸川区").split()
START, END = date(2026, 10, 19), date(2026, 11, 29)
MAX_BYTES = 850000
UA = "TokyoFamilyEventsEvidence/1.0 (+github.com/toodataa-ai/tokyo-family-events-ai)"
DATE_RE = re.compile(r"20\d{2}-\d{2}-\d{2}")
KNOWN_NAV = re.compile(r"^(?:イベント(?:カレンダー|情報|一覧)?|文化・スポーツ|イベントを探す|"
                       r"参加する|トップページ|ホーム|施設一覧|教育・子育て)$")


class Structured(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_json = False
        self.body = []
        self.title = ""
        self.in_title = False
        self.metadata = {}
        self.jsons = []
        self.visible = []
        self.script_depth = 0
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style"):
            self.script_depth += 1
        if tag == "script" and "ld+json" in attrs.get("type","").lower():
            self.in_json = True
            self.body = []
        if tag == "title":
            self.in_title = True
        if tag == "meta":
            key = attrs.get("property") or attrs.get("name") or ""
            if key in ("og:title","description","og:description","article:published_time"):
                self.metadata[key] = attrs.get("content", "")[:600]
    def handle_data(self, data):
        if self.in_json:
            self.body.append(data)
        if self.script_depth == 0 and not self.in_title:
            self.visible.append(data)
        if self.in_title:
            self.title += data
    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.script_depth = max(0, self.script_depth - 1)
        if tag == "script" and self.in_json:
            self.in_json = False
            try: self.jsons.append(json.loads("".join(self.body)))
            except (ValueError, TypeError): pass
        if tag == "title":
            self.in_title = False

def walk(value):
    if isinstance(value, dict):
        yield value
        for k, v in value.items():
            if k not in ("@context",):
                yield from walk(v)
    elif isinstance(value, list):
        for part in value:
            yield from walk(part)

def datepart(value):
    if not isinstance(value,str):
        return None
    m = DATE_RE.search(value)
    if not m:
        return None
    try:
        d = date.fromisoformat(m.group())
        return d.isoformat()
    except ValueError:
        return None

def venue_text(node):
    location = node.get("location") or {}
    if isinstance(location, list):
        location = location[0] if location else {}
    if isinstance(location, str):
        return location
    if not isinstance(location,dict):
        return ""
    addr = location.get("address") or {}
    if isinstance(addr, str):
        return " ".join([str(location.get("name") or ""), addr]).strip()
    if isinstance(addr, dict):
        return " ".join(str(x) for x in [location.get("name"),
              addr.get("addressRegion"),addr.get("addressLocality"),
              addr.get("streetAddress")] if x).strip()
    return str(location.get("name") or "")

def event_object(node):
    tp=node.get("@type") or node.get("type") or ""
    if isinstance(tp,list):
        valid=any(str(x).split("/")[-1].lower() in ("event","childrensevent","educationevent","festivalevent") for x in tp)
    else:
        valid=str(tp).split("/")[-1].lower() in ("event","childrensevent","educationevent","festivalevent")
    return valid

def validate_html(html, candidate, final_url, original):
    parsed = Structured()
    parsed.feed(html)
    raw = []
    for block in parsed.jsons:
        for node in walk(block):
            if not event_object(node):
                continue
            day=datepart(node.get("startDate"))
            if not day:
                continue
            end=datepart(node.get("endDate")) or day
            if end < START.isoformat() or day > END.isoformat():
                continue
            venue=venue_text(node)
            region_ok=any(ward in venue for ward in WARDS) or (
                "東京都" in venue or "東京" in venue)
            title=str(node.get("name") or "").strip()
            if not title or not venue or not region_ok:
                continue
            raw.append({
                "name":title[:200], "date_start":day, "date_end":end,
                "venue":venue[:300], "event_url":str(node.get("url") or final_url)[:600],
                "description":str(node.get("description") or "")[:700],
                "image":(node.get("image") if isinstance(node.get("image"),str) else None),
                "structured_source":final_url,
                "raw_startDate":node.get("startDate"),"raw_endDate":node.get("endDate"),
                "source_kind":"primary_structured_event_data"
            })
    visible = " ".join(" ".join(parsed.visible).split())[:230000]
    date_pattern = re.compile(r"(?:2026\s*[年/.-]\s*(\d{1,2})\s*[月/.-]\s*(\d{1,2})\s*日?|"
                              r"令和\s*8\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日)")
    date_snippets = []
    for match in date_pattern.finditer(visible):
        month, day = (match.group(1), match.group(2)) if match.group(1) else (match.group(3), match.group(4))
        try:
            date_string = date(2026, int(month), int(day)).isoformat()
        except ValueError:
            continue
        if not START.isoformat() <= date_string <= END.isoformat():
            continue
        if not any(item["date"] == date_string for item in date_snippets):
            date_snippets.append({"date": date_string, "context": visible[max(0,match.start()-85):match.end()+125]})
            if len(date_snippets)>=30: break
    venue_clues = []
    for match in re.finditer(r"会場|開催場所|開催地|所在地|アクセス",visible):
        clue = visible[match.start():match.end()+150]
        if any(ward in clue for ward in WARDS) or "東京都" in clue or "東京" in clue:
            venue_clues.append(clue)
            if len(venue_clues)>=6: break
    return {"target_date_mentions":date_snippets, "venue_clues":venue_clues,
            "page_title":parsed.title[:180],
            "meta_description":(parsed.metadata.get("description") or
                                parsed.metadata.get("og:description") or "")[:280],
            "structured_official_event_facts":raw}

def inspect_one(candidate):
    url=candidate.get("discovery_url") or candidate.get("source_page") or ""
    base={"candidate_id":candidate.get("candidate_id"),
          "candidate_name":candidate.get("name"),"ward":(candidate.get("discovered_via") or {}).get("ward") or candidate.get("ward"),
          "discovery_url":url,"matched_dates":candidate.get("matched_dates") or [],
          "state":"needs_manual_review","reason":"no_individual_structured_official_event_evidence",
          "source_kind":(candidate.get("discovered_via") or {}).get("channel") or
                        ("annual_official_row" if not url else "unknown")}
    if not url:
        base.update(state="official_annual_row_needs_decision",
                    reason="verified_multirow_annual_source_requires_matching_decision")
        return base
    urlparts=urlsplit(url)
    if urlparts.scheme!="https" or not urlparts.netloc:
        base.update(state="invalid_url",reason="non_https_or_missing_host")
        return base
    if urlparts.hostname in ("x.com","twitter.com","instagram.com","facebook.com"):
        base.update(state="needs_manual_review",reason="social_platform_url_not_event_facts")
        return base
    # Preserve the required Cloudflare check separately; don't retry via a bypass.
    if urlparts.hostname=="pc.tamemap.net":
        base.update(state="known_issue_source_unreachable",
                    reason="previous_Cloudflare403_not_automatic_verification")
        return base
    if KNOWN_NAV.fullmatch(str(base["candidate_name"] or "")):
        base.update(state="generic_navigation_link_requires_triage",
                    reason="index_or_category_not_an_individual_event")
        return base
    try:
        request=Request(url,headers={"User-Agent":UA,"Accept-Language":"ja,en;q=0.5"})
        with urlopen(request,timeout=10) as response:
            final=response.geturl()
            if response.status!=200:
                raise ValueError(f"HTTP {response.status}")
            if (response.headers.get("Content-Type","").split(";")[0].lower()
                    not in ("text/html","application/xhtml+xml")):
                raise ValueError("not an HTML source")
            raw=response.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES:
                raise ValueError("HTML exceeds audited size limit")
        if urlsplit(final).scheme!="https":
            raise ValueError("redirect to non-HTTPS")
        parsed=validate_html(raw.decode("utf-8","replace"),candidate,final,url)
        base.update(page_title=parsed["page_title"],
                    page_meta=parsed["meta_description"],
                    target_date_mentions=parsed["target_date_mentions"],
                    venue_clues=parsed["venue_clues"],
                    final_url=final,
                    page_sha256=hashlib.sha256(raw).hexdigest(),
                    structured_facts=parsed["structured_official_event_facts"])
        if parsed["structured_official_event_facts"]:
            base.update(state="structured_official_fact_candidate",
                        reason="structured_event_date_venue_extracted;human_fidelity_review_pending")
        elif parsed["target_date_mentions"]:
            base.update(state="has_official_date_clues_needs_manual_facts",
                        reason="source_HTML_mentions_target_date_but_venue_and_event_unit_unconfirmed")
        else:
            base.update(state="needs_manual_review",
                        reason="no_individual_dated_event_evidence_in_target_window")
    except (HTTPError,URLError,ValueError,TimeoutError,OSError) as e:
        base.update(state="source_error",reason=str(e)[:200])
    return base

def run(candidates,workers=12):
    if not 1<=workers<=16:
        raise ValueError("worker limit")
    if len(candidates)<200:
        raise ValueError("unexpectedly small source candidate set")
    with ThreadPoolExecutor(max_workers=workers) as executor:
        inspected=list(executor.map(inspect_one,candidates))
    # Record exact duplicate URL + dates without merging separate-day occurrences.
    seen={}
    for row in inspected:
        url=row.get("discovery_url") or ""
        dates=",".join(sorted(row.get("matched_dates") or []))
        key=(url, dates) if url else (row.get("candidate_id"), dates)
        if key in seen:
            row["also_seen_as_candidate_id"]=seen[key]
            row["duplicate_url_date_lead"]=True
        else:
            seen[key]=row.get("candidate_id")
            row["duplicate_url_date_lead"]=False
    from collections import Counter
    counts=dict(Counter(r["state"] for r in inspected))
    return {
        "schema_version":1,"run_date":"2026-10-20","as_of_jst":"2026-10-19",
        "status":"read_only_fact_review","published":False,
        "full_23_ward_official_review_complete":False,
        "source_candidates":len(candidates),
        "states":counts,
        "structured_official_facts":sum(len(r.get("structured_facts") or []) for r in inspected),
        "duplicate_leads":sum(r["duplicate_url_date_lead"] for r in inspected),
        "note":"No event published; no source/venue/eligibility/thumbnail/family rubric invented.",
        "rows":inspected}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True,type=Path)
    ap.add_argument("--output",required=True,type=Path)
    ap.add_argument("--workers",default=12,type=int)
    args=ap.parse_args()
    result=run(json.loads(args.input.read_text(encoding="utf-8")),args.workers)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="rows"},ensure_ascii=False))
    print("FACT CRAWL ONLY: still no publication authorization",file=sys.stderr)

if __name__=="__main__":
    main()
