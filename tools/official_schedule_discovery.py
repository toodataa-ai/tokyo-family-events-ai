#!/usr/bin/env python3
"""Discover individual festival candidates from an official multi-event HTML table.

The output is an auditable candidate feed, NOT published event data. Never mark a
source checked if fetching/parsing failed. Publishing requires separate verification.
"""
import argparse
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
import pathlib
import re
import sys
from urllib.request import Request, urlopen

SOURCE_ID = "nerima_district_festivals_2026"
SOURCE_URL = "https://www.city.nerima.tokyo.jp/kankomoyoshi/annai/omatsuri/chikusai/20260616103208700.html"
EXPECTED_TITLE = "令和8年度"
FISCAL_START_YEAR = 2026


class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.tables = []
        self.rows = None
        self.row = None
        self.cell = None
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        if tag == "table":
            if self.depth == 0:
                self.rows = []
            self.depth += 1
        elif self.depth == 1 and tag == "tr":
            self.row = []
        elif self.depth == 1 and tag in ("th", "td") and self.row is not None:
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_data(self, data):
        if not self.skip and self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        if tag in ("th", "td") and self.cell is not None and self.row is not None:
            self.row.append(re.sub(r"\s+", " ", "".join(self.cell)).strip())
            self.cell = None
        elif tag == "tr" and self.row is not None and self.depth == 1:
            self.rows.append(self.row)
            self.row = None
        elif tag == "table" and self.depth:
            self.depth -= 1
            if self.depth == 0:
                self.tables.append(self.rows)
                self.rows = None
        elif tag in ("p", "div", "li") and self.cell is not None:
            self.cell.append(" ")


def normalize(value):
    return re.sub(r"[\s　()（）・「」『』\-－]", "", value or "")


def dates_in(text):
    # Date cells can contain several days, with the month stated only once.
    cleaned = re.sub(r"（[^）]*雨[^）]*）", "", text)
    matches = re.findall(r"(?:(\d{1,2})月\s*)?(\d{1,2})日", cleaned)
    out, month = [], None
    for mm, dd in matches:
        if mm:
            month = int(mm)
        if not month:
            continue
        year = FISCAL_START_YEAR if month >= 4 else FISCAL_START_YEAR + 1
        try:
            date = dt.date(year, month, int(dd))
        except ValueError:
            continue
        if date not in out:
            out.append(date)
    return out


def extract_candidates(html, start, end):
    if EXPECTED_TITLE not in html:
        raise ValueError("Official source fiscal-year marker missing")
    table = Tables()
    table.feed(html)
    rows = next((t for t in table.tables if any("地区祭名" in " ".join(r) and "開催日" in " ".join(r) for r in t)), None)
    if not rows:
        raise ValueError("Festival date table not found")
    output = []
    seen = set()
    in_range_total = 0
    table_total = 0
    for row in rows:
        if not row or "地区祭名" in " ".join(row):
            continue
        # 7 cells: month + festival + date + time + venue + content + contact.
        # 6 cells: the month column is omitted due to an HTML rowspan.
        offset = 1 if len(row) >= 7 else 0
        if len(row) - offset < 5:
            continue
        name, days, time, venue, content = row[offset:offset + 5]
        if not ("地区祭" in name or "広場の祭典" in name):
            continue
        dates = dates_in(days)
        if not dates:
            raise ValueError("Unparseable date for " + name)
        table_total += 1
        selected = [date for date in dates if start <= date <= end]
        if not selected:
            continue
        in_range_total += 1
        if not venue:
            raise ValueError("Missing venue for " + name)
        key = (normalize(name), normalize(venue), tuple(dates))
        if key in seen:
            raise ValueError("Duplicate official table row: " + name)
        seen.add(key)
        digest = hashlib.sha256((normalize(name) + "|" + normalize(venue) + "|" + ",".join(str(d) for d in dates)).encode()).hexdigest()[:12]
        output.append({
            "candidate_id": "nerima-district-" + digest,
            "ward": "練馬区",
            "name": re.sub(r"\s+", " ", name),
            "date_start": str(min(dates)),
            "date_end": str(max(dates)),
            "dates": [str(date) for date in dates],
            "matched_dates": [str(date) for date in selected],
            "time": time or None,
            "venue": venue,
            "description": content or "",
            "price": None,
            "official_url": SOURCE_URL,
            "source": SOURCE_URL,
            "discovery_sources": [{"channel": "explicit", "source_id": SOURCE_ID, "kind": "official_multi_event_schedule", "url": SOURCE_URL}]
        })
    if table_total == 0:
        raise ValueError("Official table contains no parseable festival rows")
    return output


def check_decisions(candidates, decision_files):
    ids = set()
    for filename in decision_files:
        doc = json.loads(pathlib.Path(filename).read_text(encoding="utf-8"))
        for item in doc.get("decisions", []):
            if item.get("decision") in ("published", "excluded", "duplicate"):
                ids.add(item.get("candidate_id"))
    return [c for c in candidates if c["candidate_id"] not in ids]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--html-file", help="Offline HTML fixture, otherwise fetch official URL")
    parser.add_argument("--decision-file", action="append", default=[], help="Run decision JSON to reconcile with official candidates")
    parser.add_argument("--output", help="Save report; otherwise stdout")
    args = parser.parse_args(argv)
    report = {"source_id": SOURCE_ID, "url": SOURCE_URL, "status": "error",
              "source_checked": False, "candidate_count": 0, "candidates": [], "missing_from_decisions": []}
    try:
        start, end = dt.date.fromisoformat(args.start), dt.date.fromisoformat(args.end)
        if end < start:
            raise ValueError("end precedes start")
        if args.html_file:
            html = pathlib.Path(args.html_file).read_text(encoding="utf-8")
        else:
            with urlopen(Request(SOURCE_URL, headers={"User-Agent": "TokyoFamilyEvents/1.15 (official schedule audit)"}), timeout=30) as response:
                html = response.read().decode("utf-8")
        candidates = extract_candidates(html, start, end)
        report.update(status="checked", source_checked=True, candidate_count=len(candidates), candidates=candidates)
        if args.decision_file:
            missing = check_decisions(candidates, args.decision_file)
            report["missing_from_decisions"] = [c["candidate_id"] + ": " + c["name"] + " (" + c["venue"] + ")" for c in missing]
            if missing:
                report["status"] = "incomplete"
    except Exception as exc:
        report["error"] = str(exc)
    formatted = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        pathlib.Path(args.output).write_text(formatted + "\n", encoding="utf-8")
    else:
        print(formatted)
    return 0 if report["status"] == "checked" else 2


if __name__ == "__main__":
    sys.exit(main())
