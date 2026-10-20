import datetime as dt
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from rolling_horizon import source_targets, PlanError
from holiday_after_collect import inspect, suginami_official_event_links


class TestSuginamiCalendar(unittest.TestCase):
    def test_all_days_included_without_mutating_legacy(self):
        sources = json.loads((ROOT / "site/data/discovery_sources.json").read_text(encoding="utf-8"))
        selected = source_targets(sources, dt.date(2026, 10, 21), dt.date(2026, 12, 1))
        all_source = next(x for x in selected if x["id"] == "suginami_calendar_all")
        self.assertEqual(len(all_source["urls"]), 45)  # 3 months + 42 calendar days
        self.assertTrue(any(x.endswith("calendar.cgi?day=24&month=10&type=3&year=2026") for x in all_source["urls"]))
        self.assertTrue(any(x.endswith("calendar.cgi?day=25&month=10&type=3&year=2026") for x in all_source["urls"]))
        legacy = next(x for x in selected if x["id"] == "suginami_festival")
        self.assertTrue(all("event_category=5" in x for x in legacy["urls"]))

    def test_missing_child_keyword_still_discovered_and_deduped_by_page_id(self):
        html = """<html><title>イベントカレンダー</title>
        <a href="/s033/event/28531.html">花と緑の井草祭り（井草森公園）  2026年10月24日（土曜日）</a>
        <a href="/s104/event/28567.html">杉並清掃工場環境フェア2026  2026年10月25日（日曜日）</a>
        <a href="/s104/event/28567.html">杉並清掃工場環境フェア2026</a>
        <a href="/s104/event/99999.html">プログラミング講座</a></html>"""
        url = "https://www.city.suginami.tokyo.jp/cgi-bin/event_cal_multi/calendar.cgi?type=3"
        found = suginami_official_event_links(html, url)
        self.assertEqual({x["candidate_id"] for x in found},
                         {"suginami-official-28531", "suginami-official-28567", "suginami-official-99999"})
        self.assertEqual(len(found), 3)

    def test_failed_request_does_not_become_empty_success(self):
        def broken(_url):
            return (403, b"Forbidden", _url, "text/html")
        row = inspect({"kind": "explicit", "source_id": "suginami_calendar_all",
                       "url": "https://www.city.suginami.tokyo.jp/cgi-bin/event_cal_multi/calendar.cgi?type=3"},
                      broken)
        self.assertEqual(row["status"], "error")
        self.assertEqual(row["candidates"], [])


    def test_daily_inspection_keeps_official_page_ids(self):
        page = """<html><title>イベントカレンダー</title>
        <a href="/s033/event/28531.html">花と緑の井草祭り</a>
        <a href="/s104/event/28567.html">杉並清掃工場環境フェア2026</a></html>"""
        def fixture(url):
            return 200, page.encode("utf-8"), url, "text/html;charset=utf-8"
        row = inspect({"kind": "explicit", "source_id": "suginami_calendar_all",
                       "url": "https://www.city.suginami.tokyo.jp/cgi-bin/event_cal_multi/calendar.cgi?type=3"},
                      fixture)
        self.assertEqual(row["status"], "checked")
        self.assertEqual(row["official_event_link_count"], 2)
        self.assertEqual({x["candidate_id"] for x in row["candidates"]},
                         {"suginami-official-28531", "suginami-official-28567"})


if __name__ == "__main__":
    unittest.main()
