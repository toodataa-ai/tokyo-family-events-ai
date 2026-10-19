#!/usr/bin/env python3
"""Additive, fail-closed Nakano official / community discovery.

Supplemental sites are not substitutes for the protected required Tamemap
source. A 403 from Tamemap remains an error. The output is discovery evidence
and unverified individual-event leads, NEVER a publication approval.
"""
from datetime import date
from html.parser import HTMLParser
import hashlib
import re
from urllib.parse import urljoin, urlsplit

from holiday_after_collect import fetch_url, VisibleLinks, digest, public_row


def months_between(start, end):
    current = start.replace(day=1)
    while current <= end:
        yield current
        current = date(current.year + (current.month == 12), current.month % 12 + 1, 1)


class DateRowLinks(HTMLParser):
    """Only links in actual HTML table rows; no generic navigation links."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.row = None
        self.anchor = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = {"text": [], "links": []}
        elif tag == "a" and self.row is not None:
            self.anchor = {"url": dict(attrs).get("href", ""), "label": ""}

    def handle_data(self, data):
        if self.row is not None:
            self.row["text"].append(data)
        if self.anchor is not None:
            self.anchor["label"] += data

    def handle_endtag(self, tag):
        if tag == "a" and self.anchor is not None:
            if self.row is not None:
                self.row["links"].append(self.anchor)
            self.anchor = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def calendar_candidates(html, page_url, month, start, end, source_id):
    month_marker = re.compile(r"%04d\s*年\s*0?%d\s*月" % (month.year, month.month))
    if not month_marker.search(html):
        raise ValueError("calendar body does not show the requested year-month")
    parser = DateRowLinks()
    parser.feed(html)
    if not parser.rows:
        raise ValueError("no HTML table rows found in official calendar")
    output, seen = [], set()
    last_day = None
    for row in parser.rows:
        txt = " ".join(row["text"])
        day_match = re.search(r"(?<!\d)(\d{1,2})\s*日(?:\s*[月火水木金土日]曜日)?", txt)
        if day_match:
            day = int(day_match.group(1))
            try:
                last_day = date(month.year, month.month, day)
            except ValueError:
                raise ValueError("invalid day in official calendar")
        if not (last_day and start <= last_day <= end):
            continue
        for link in row["links"]:
            label = " ".join(link["label"].split())
            url = urljoin(page_url, link["url"])
            host = urlsplit(url).hostname or ""
            if not label or label == "イベントはありません" or len(label) < 4:
                continue
            if not (url.startswith("https://") and host == "www.city.tokyo-nakano.lg.jp"):
                continue
            if "/event/" in url and "/calendar/" in url:
                continue
            identity = (last_day.isoformat(), url)
            if identity in seen:
                continue
            seen.add(identity)
            output.append({
                "candidate_id": "nakano-official-" + hashlib.sha256(
                    (identity[0] + "|" + identity[1]).encode()).hexdigest()[:16],
                "name": label, "ward": "中野区", "matched_dates": [last_day.isoformat()],
                "date_from_calendar": last_day.isoformat(),
                "discovery_url": url, "source_page": page_url,
                "status": "unverified", "calendar_day_needs_detail_confirmation": True,
                "discovered_via": {"channel": "supplemental_official",
                                   "source_id": source_id, "ward": "中野区",
                                   "search_url": page_url}
            })
    return output


def community_listing_links(html, page_url):
    """Capture actual Shakyo result pages without dropping titles like おもちゃDAY."""
    parser = VisibleLinks()
    parser.feed(html)
    seen, output = set(), []
    for link in parser.links:
        label = " ".join(link["name"].split())
        url = urljoin(page_url, link["href"])
        parsed = urlsplit(url)
        if (parsed.hostname != "nakanoshakyo.com"
                or not parsed.path.startswith("/nakanoinfo/")
                or "/result" not in parsed.path
                or len(label) < 3 or url in seen):
            continue
        seen.add(url)
        output.append({"candidate_id": "shakyo-" + digest(url),
                       "name": label, "discovery_url": url})
    return output


def collect_supplemental(plan, config, fetcher=None):
    start, end = date.fromisoformat(plan["target_start"]), date.fromisoformat(plan["target_end"])
    if end < start or len(plan.get("weekends", [])) != 6:
        raise ValueError("invalid rolling horizon")
    checks = []
    candidates = []
    for source in config["sources"]:
        if source.get("ward") != "中野区":
            raise ValueError("supplement is restricted to Nakano")
        if source["kind"] == "official_calendar":
            for month in months_between(start, end):
                urls = [source["month_path"].replace("{YYYY}", str(month.year)).replace("{MM}", f"{month.month:02d}"),
                        source["current_path"]]
                row = {"source_id": source["id"], "ward": "中野区", "month": month.isoformat()[:7],
                       "required_for_supplement": source["required_for_supplement"],
                       "status": "error", "attempts": [], "candidate_count": 0}
                for url in dict.fromkeys(urls):
                    response = fetch_url(url, fetcher=fetcher, attempts=2)
                    row["attempts"].append(public_row(response))
                    if response["status"] != "checked":
                        continue
                    try:
                        extracted = calendar_candidates(response["body"], url, month, start, end, source["id"])
                    except ValueError as error:
                        row["attempts"][-1]["parse_error"] = str(error)
                        continue
                    row.update(status="checked", search_url=url, checked_at=response["checked_at"],
                               candidate_count=len(extracted),
                               candidate_ids=[c["candidate_id"] for c in extracted])
                    candidates.extend(extracted)
                    break
                if row["status"] != "checked":
                    row["error"] = "no verified current-month HTML table after candidate URLs"
                checks.append(row)
        elif source["kind"] == "listing":
            for url in source["search_urls"]:
                response = fetch_url(url, fetcher=fetcher)
                row = {"source_id": source["id"], "ward": "中野区",
                       "required_for_supplement": source["required_for_supplement"],
                       "status": response["status"], "search_url": url,
                       "checked_at": response["checked_at"], "attempts": [public_row(response)]}
                if response["status"] == "checked":
                    links = community_listing_links(response["body"], url)
                    row["candidate_count"] = len(links)
                    row["candidate_ids"] = []
                    for link in links:
                        link.update(ward="中野区", status="unverified",
                                    date_unverified=True,
                                    discovered_via={"channel": "supplemental_community",
                                                    "source_id": source["id"], "ward": "中野区",
                                                    "search_url": url})
                        candidates.append(link)
                        row["candidate_ids"].append(link["candidate_id"])
                else:
                    row["error"] = response.get("error")
                checks.append(row)
        else:
            raise ValueError("unsupported supplemental source kind: " + str(source["kind"]))
    failures = [c for c in checks if c["required_for_supplement"] and c["status"] != "checked"]
    return {"source_checks": checks, "candidates": candidates,
            "supplemental_success": len(checks) - len(failures),
            "supplemental_failures": failures,
            "tamemap_required_check_satisfied": False,
            "publishable": False}
