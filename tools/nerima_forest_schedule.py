#!/usr/bin/env python3
"""Read a Nerima official multi-event schedule as individual dated activities.

An HTTP 200, page title, or a single parent article is never "full coverage".
Parse the activity table, enumerate every dated row, and report both in-range
and out-of-range row counts. This only emits candidates, not publishable facts.
"""
import argparse
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
import re
from urllib.request import Request, urlopen

SOURCE_ID = "nerima_forest_festa_2026"
SOURCE_URL = "https://www.city.nerima.tokyo.jp/kurashi/shigoto/midori/shokai/nerimanomori.html"


class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.rows = None
        self.row = None
        self.cell = None
        self.depth = 0
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        if tag == "table":
            if not self.depth:
                self.rows = []
            self.depth += 1
        elif tag == "tr" and self.depth == 1:
            self.row = []
        elif tag in ("th", "td") and self.depth == 1 and self.row is not None:
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
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.depth == 1 and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        elif tag == "table" and self.depth:
            self.depth -= 1
            if not self.depth:
                self.tables.append(self.rows)
                self.rows = None
        elif tag in ("p", "div", "li") and self.cell is not None:
            self.cell.append(" ")


def parse_schedule(html, start, end, source_url=SOURCE_URL):
    if end < start:
        raise ValueError("invalid target date range")
    if "ねりまの森こどもフェスタ" not in html or "2026" not in html:
        raise ValueError("2026 Nerima forest festival title not found")
    parser = Tables()
    parser.feed(html)
    tables = [rows for rows in parser.tables if rows and
              all(h in "".join(rows[0]) for h in ("日程", "イベント内容", "場所", "区民団体名"))]
    if len(tables) != 1:
        raise ValueError("ambiguous or missing event schedule table")
    rows, found = [], set()
    for index, cells in enumerate(tables[0][1:], 1):
        if len(cells) != 4:
            raise ValueError("malformed schedule row " + str(index))
        schedule, programme, venue, organizer = cells
        hit = re.search(r"令和(\d+)年\s*(\d{1,2})月\s*(\d{1,2})日", schedule)
        if not hit:
            raise ValueError("unparseable official activity date " + str(index))
        year, month, day = 2018 + int(hit[1]), int(hit[2]), int(hit[3])
        when = dt.date(year, month, day)
        name = re.split(r"\s*[（(]", programme, 1)[0].strip()
        place = re.split(r"\s*[（(]", venue, 1)[0].strip()
        if not name or not place or not organizer:
            raise ValueError("missing organizer/name/venue " + str(index))
        identity = (when.isoformat(), name, place)
        if identity in found:
            raise ValueError("duplicate official programme row " + str(index))
        found.add(identity)
        uid = hashlib.sha256("|".join(identity).encode()).hexdigest()[:14]
        rows.append({
            "candidate_id": "nerima-forest-" + uid,
            "ward": "練馬区", "name": name, "date_start": when.isoformat(),
            "date_end": when.isoformat(), "time_note": schedule,
            "venue": venue, "description": programme,
            "organizer": organizer, "official_url": source_url,
            "discovery_sources": [{"channel": "explicit", "source_id": SOURCE_ID,
                                   "kind": "official_multi_date_event_table",
                                   "url": source_url}],
        })
    if not rows:
        raise ValueError("official forest event table has no rows")
    selected = [item for item in rows
                if start <= dt.date.fromisoformat(item["date_start"]) <= end]
    return {"status": "checked", "source_id": SOURCE_ID, "url": source_url,
            "official_row_count": len(rows), "candidate_count": len(selected),
            "candidate_ids": [r["candidate_id"] for r in selected],
            "all_rows": rows, "candidates": selected,
            "outside_target_count": len(rows) - len(selected),
            "decision_reconciliation": "pending"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--html-file")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.html_file:
        html = open(args.html_file, encoding="utf-8").read()
    else:
        with urlopen(Request(SOURCE_URL, headers={
                "User-Agent": "TokyoFamilyEvents/1.21 official forest row audit"}),
                timeout=30) as response:
            html = response.read(4000000).decode("utf-8")
    report = parse_schedule(html, dt.date.fromisoformat(args.start),
                            dt.date.fromisoformat(args.end))
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        open(args.output, "w", encoding="utf-8").write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
