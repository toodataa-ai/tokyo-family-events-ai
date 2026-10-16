#!/usr/bin/env python3
"""Resolve Nerima district-festival schedules by fiscal year from the stable official index.

Never infer an unpublished fiscal year's URL or reinterpret prior-year schedules.
This file emits references to candidate sources only; it does not publish events.
"""
import datetime as dt
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlparse

LISTING_URL = "https://www.city.nerima.tokyo.jp/kankomoyoshi/annai/omatsuri/chikusai/index.html"
ALLOWED_HOST = "www.city.nerima.tokyo.jp"
SCHEDULE_DIRECTORY = "/kankomoyoshi/annai/omatsuri/chikusai/"


def fiscal_year(day):
    return day.year if day.month >= 4 else day.year - 1


def reiwa_year(year):
    if year < 2019:
        raise ValueError("Unsupported Japanese fiscal year")
    return "元" if year == 2019 else str(year - 2018)


class ScheduleLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.href = None
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.text = []

    def handle_data(self, data):
        if self.href is not None:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append((self.href, "".join(self.text)))
            self.href = None
            self.text = []


def resolve_annual_schedule_urls(html, start, end, listing_url=LISTING_URL):
    if end < start:
        raise ValueError("end precedes start")
    if "地区祭" not in html:
        raise ValueError("Official district festival index title missing")
    parser = ScheduleLinks()
    parser.feed(html)
    targets = range(fiscal_year(start), fiscal_year(end) + 1)
    found = {}
    for href, text in parser.links:
        normalized = re.sub(r"\s+", "", text)
        match = re.fullmatch(r"令和(元|\d+)年度地区祭開催日程", normalized)
        if not match:
            continue
        ordinal = 1 if match.group(1) == "元" else int(match.group(1))
        year = 2018 + ordinal
        url = urljoin(listing_url, href)
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
            raise ValueError("Untrusted schedule domain for fiscal year " + str(year))
        if (not parsed.path.startswith(SCHEDULE_DIRECTORY) or not parsed.path.endswith(".html")
                or parsed.path == urlparse(listing_url).path or parsed.fragment):
            raise ValueError("Invalid official schedule path for fiscal year " + str(year))
        if year in found and found[year] != url:
            raise ValueError("Conflicting official schedule URLs for fiscal year " + str(year))
        found[year] = url
    missing = [year for year in targets if year not in found]
    if missing:
        raise ValueError("Official fiscal-year schedule not published: " + ", ".join(str(y) for y in missing))
    return [(year, found[year]) for year in targets]
