"""Regression tests: no synthetic checks, real date expansion, fiscal table rows."""
import datetime as dt
from pathlib import Path
import sys
import unittest
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from holiday_after_collect import (fetch_url, inspect, rss_items, html_links, build_jobs,
                                   annual_report, collect, holiday_calendar_candidates, holiday_calendar_jobs)

INDEX = """<html><title>地区祭</title><a href="20260616103208700.html">
令和8年度 地区祭開催日程</a></html>"""
ANNUAL = """<html><head><title>令和8年度 地区祭開催日程</title></head><body>
<table><tr><th>開催月</th><th>地区祭名</th><th>開催日</th>
<th>時間</th><th>会場</th><th>内容</th><th>連絡先</th></tr>
<tr><td>11月</td><td>第一地区祭（豊玉南小学校）</td><td>11月29日</td>
<td>10時～12時</td><td>豊玉南小学校</td><td>もちつき、昔遊び</td><td></td></tr>
</table></body></html>"""
RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><item><title>親子で楽しむ体験フェス</title>
<link>https://www.example.org/event/2026</link></item></channel></rss>"""
GENERAL = """<html><head><title>自治体イベント一覧</title></head><body>
<a href="/events/2026/">子どもと楽しむ体験イベント2026</a>
<a href="/other">トップ</a></body></html>"""


def fake_fetch(url):
    if url.endswith("/chikusai/index.html"):
        body = INDEX
    elif url.endswith("/chikusai/20260616103208700.html"):
        body = ANNUAL
    elif "format=rss" in url:
        body = RSS
    else:
        body = GENERAL
    return 200, body.encode("utf-8"), url, "text/html; charset=utf-8"


def example_plan():
    return {
        "status": "eligible", "publication_permitted": False, "as_of_jst": "2026-10-19",
        "base_data_production_sha": "a" * 40,
        "target_start": "2026-10-19", "target_end": "2026-11-29",
        "weekends": [{"sat": day} for day in (
            "2026-10-24", "2026-10-31", "2026-11-07",
            "2026-11-14", "2026-11-21", "2026-11-28")],
        "holiday_targets": [{"date": "2026-11-03", "requires_independent_23_ward_search": True},
                            {"date": "2026-11-23", "requires_independent_23_ward_search": True}],
        "explicit_source_checks": [
            {"id": "nerima_district_festivals_2026", "required": True,
             "annual_listing_url":
             "https://www.city.nerima.tokyo.jp/kankomoyoshi/annai/omatsuri/chikusai/index.html",
             "urls": ["https://www.city.nerima.tokyo.jp/kankomoyoshi/annai/omatsuri/chikusai/index.html"]},
            {"id": "sample", "required": True,
             "urls": ["https://www.example.org/official"]}
        ]
    }


class HolidayAfterCollectTests(unittest.TestCase):
    def test_all_23_wards_separate_and_queries_date_variable(self):
        jobs = build_jobs(example_plan())
        q = [r for r in jobs if r["kind"] == "ai_cross"]
        h = [r for r in jobs if r["kind"] == "holiday_ai_cross"]
        self.assertEqual(len(q), 23 * 6 * 3)
        self.assertEqual(len(h), 23 * 2 * 3)
        self.assertEqual(len({x["query"] for x in h}), len(h))
        self.assertTrue(all("2026-11-03" in x["query"] or "2026-11-23" in x["query"] for x in h))
        self.assertTrue(any("2026年11月28日" in x["query"] for x in q))
        self.assertEqual({x["ward"] for x in q}, {x["ward"] for x in h})
        self.assertEqual(len([x for x in jobs if x["kind"] == "explicit"]), 2)
        self.assertEqual(len([x for x in jobs if x["kind"] == "holiday_calendar"]), 10)
        self.assertTrue(any("list_calendar202611.html" in x["url"] for x in jobs))

    def test_official_calendar_daily_links_are_scoped_to_holiday_only(self):
        url = "https://www.city.toshima.lg.jp/cgi-bin/event_cal/calendar.cgi?day=3&month=11&type=3&year=2026"
        html = """<html><title>イベントカレンダー</title>
        <a href="/site/home.html">11月の予定</a>
        <a href="/125/bunka/bunka/2607020838.html">みんなのステージ2026 ダンスの部
        2026年11月3日（火曜日） ～ 2026年11月3日（火曜日）</a>
        <a href="/not-nov3">親子祭り 2026年11月4日（水曜日）</a>
        <a href="https://www.evil.example.com">イベント 2026年11月3日（火曜日）</a>
        </html>"""
        found = holiday_calendar_candidates(html, url, "2026-11-03", "daily")
        self.assertEqual(len(found), 1)
        self.assertIn("みんなのステージ", found[0]["name"])
        self.assertEqual(found[0]["matched_dates"], ["2026-11-03"])
        self.assertTrue(found[0]["date_unverified"])
        self.assertEqual(found[0]["source_kind"], "official_calendar_candidate_only")

    def test_nerima_monthly_calendar_only_picks_november_third_row(self):
        url = "https://www.city.nerima.tokyo.jp/kankomoyoshi/event/calendar/list_calendar202611.html"
        html = """<html><table>
        <tr><th>日</th><th>曜日</th><th>イベント</th></tr>
        <tr><td>2日</td><td>月曜日</td><td><a href="/not-this-day">別日親子イベント</a></td></tr>
        <tr><td>3日</td><td>火曜日</td><td><a href="/kankomoyoshi/bunka/neriotofes/neriotofes2026.html">ねりおと♪フェスティバル2026</a>
        <a href="/kankomoyoshi/sports/oshirase/nerisupo2022.html">ねりすぽフェスティバル</a></td></tr>
        <tr><td>4日</td><td>水曜日</td><td><a href="/not-this-day-either">別の親子イベント</a></td></tr>
        </table></html>"""
        found = holiday_calendar_candidates(html, url, "2026-11-03", "monthly")
        self.assertEqual(len(found), 2)
        self.assertTrue(all(x["matched_dates"] == ["2026-11-03"] for x in found))
        self.assertFalse(any("別日" in x["name"] for x in found))
        self.assertEqual(len(holiday_calendar_jobs(
            {"date": "2026-11-03", "requires_independent_23_ward_search": True})), 5)

    def test_tamemap_new_arrival_collects_unverified_titles_without_dates(self):
        from holiday_after_collect import tamemap_new_arrival_leads
        url = ("https://pc.tamemap.net/1311401/new_arrival?"
               "lat=35.7089745&lng=139.6630981&level=5000&locale=ja")
        html = """<html><h1>イベントの新着一覧</h1>
        <section><h3>絵本の読み聞かせの会</h3>
        <p>投稿者 : ポプラ文庫絵本の会</p><span>2時間前</span></section>
        <section><h3>杜の文化祭</h3><p>投稿者 : ZEROキッズ</p>
        <span>1日前</span></section></html>"""
        found = tamemap_new_arrival_leads(html, url)
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]["name"], "絵本の読み聞かせの会")
        self.assertEqual(found[0]["poster"], "ポプラ文庫絵本の会")
        self.assertEqual(found[1]["name"], "杜の文化祭")
        self.assertEqual(found[1]["matched_dates"], [])
        self.assertTrue(all(x["date_unverified"] and not x["publication_approved"]
                            and not x["primary_source_verified"] for x in found))
        row = inspect({"kind": "explicit", "source_id": "tamemap_nakano",
                       "url": url}, lambda u: (200, html.encode(), u, "text/html"))
        self.assertEqual(row["status"], "checked")
        self.assertEqual(row["candidate_link_count"], 2)
        self.assertEqual(row["candidate_status"], "unverified_title_leads")

    def test_tamemap_calendar_forbidden_stays_error_while_new_arrival_succeeds(self):
        new_url = ("https://pc.tamemap.net/1311401/new_arrival?"
                   "lat=35.7089745&lng=139.6630981&level=5000&locale=ja")
        cal = "https://pc.tamemap.net/1311401/calendar/2026-11"
        html = "<h1>イベントの新着一覧</h1><h3>こども工作体験</h3>"
        def fetch(url):
            if "/calendar/" in url:
                return 403, b"forbidden", url, "text/html"
            return 200, html.encode(), url, "text/html"
        a = inspect({"kind": "explicit", "source_id": "tamemap_nakano",
                     "url": cal}, fetch)
        b = inspect({"kind": "explicit", "source_id": "tamemap_nakano",
                     "url": new_url}, fetch)
        self.assertEqual(a["status"], "error")
        self.assertEqual(b["status"], "checked")
        self.assertEqual(len(b["candidates"]), 1)
        self.assertNotIn("matched_dates", a.get("candidates", [{}])[0] if a["candidates"] else {})

    def test_tamemap_new_arrival_missing_titles_is_not_zero_event_success(self):
        from holiday_after_collect import tamemap_new_arrival_leads
        u = "https://pc.tamemap.net/1311401/new_arrival"
        with self.assertRaisesRegex(ValueError, "no visible event"):
            tamemap_new_arrival_leads("<h1>イベントの新着一覧</h1>", u)
        with self.assertRaisesRegex(ValueError, "not a Tamemap"):
            tamemap_new_arrival_leads("<h3>こども祭り</h3>", u)

    def test_failed_fetch_never_checked(self):
        def down(url):
            raise OSError("official origin unavailable")
        row = fetch_url("https://www.example.org/official", down, attempts=1)
        self.assertEqual(row["status"], "error")
        self.assertIn("origin unavailable", row["error"])

    def test_non_200_cannot_pass(self):
        row = fetch_url("https://www.example.org/", lambda url: (403, b"forbidden", url, "text/html"), attempts=1)
        self.assertEqual(row["status"], "error")

    def test_html_link_heuristic_is_unverified_only(self):
        title, links = html_links(GENERAL, "https://www.example.org/")
        self.assertIn("一覧", title)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["discovery_url"], "https://www.example.org/events/2026/")

    def test_valid_empty_rss_is_measured_zero_not_fetch_failure(self):
        r = inspect({"kind": "ai_cross", "ward": "港区",
                     "url": "https://www.bing.com/search?format=rss&q=x"},
                    lambda url: (200, b"<rss><channel/></rss>", url, "application/rss+xml"))
        self.assertEqual(r["status"], "checked")
        self.assertEqual(r["candidate_link_count"], 0)

    def test_html_error_page_is_not_a_checked_rss(self):
        r = inspect({"kind": "ai_cross", "ward": "港区",
                     "url": "https://www.bing.com/search?format=rss&q=x"},
                    lambda url: (200, b"<html><title>Blocked</title></html>", url, "text/html"))
        self.assertEqual(r["status"], "error")

    def test_search_engine_topic_drift_is_not_an_event_lead(self):
        bad = """<rss><channel>
        <item><title>WhatsApp - Official Site</title>
        <link>https://www.whatsapp.com/</link></item>
        <item><title>PESSIMISTIC | dictionary definition</title>
        <link>https://dictionary.cambridge.org/english/pessimistic</link></item>
        <item><title>親子で楽しむ中野区防災イベント2026</title>
        <link>https://www.city.tokyo-nakano.lg.jp/event/2026.html</link></item>
        <item><title>Future AI Event in Nevada</title>
        <link>https://www.elsewhere.com/ev</link></item>
        </channel></rss>"""
        counts = {}
        found = rss_items(bad, counts)
        self.assertEqual(len(found), 1)
        self.assertEqual(counts["search_results_total"], 4)
        self.assertEqual(counts["search_results_rejected_irrelevant"], 3)
        self.assertIn("中野区", found[0]["name"])

    def test_ward_aware_rss_rejects_japanese_overseas_events(self):
        rss = """<rss><channel>
        <item><title>アメリカ11月のおすすめ観光文化体験</title>
        <link>https://www.travel-in-usa.jp/events</link></item>
        <item><title>WhatsApp 日本語イベント</title>
        <link>https://www.whatsapp.com/?lang=ja</link></item>
        <item><title>練馬区こども祭り2026</title>
        <link>https://www.city.nerima.tokyo.jp/event/2026.html</link></item>
        <item><title>親子科学体験教室</title>
        <link>https://www.city.nerima.tokyo.jp/event/science.html</link></item>
        </channel></rss>"""
        counts = {}
        got = rss_items(rss, counts, ward="練馬区")
        self.assertEqual(len(got), 2)
        self.assertEqual(counts["search_results_rejected_irrelevant"], 2)
        self.assertTrue(all("city.nerima.tokyo.jp" in x["discovery_url"] for x in got))

    def test_taiwan_taitung_and_banqiao_not_mistaken_for_tokyo_wards(self):
        data = """<rss><channel>
        <item><title>2026台東景點推薦！親子室内行程</title>
        <link>https://fullfenblog.tw/taitung-lazy-bag/</link></item>
        <item><title>板橋景點一日遊，親子必去</title>
        <link>https://myjourney.tw/banqiao-attractions/</link></item>
        <item><title>台東区こども体験イベント</title>
        <link>https://www.city.taito.lg.jp/event</link></item>
        </channel></rss>"""
        audit = {}
        found = rss_items(data, audit, ward="台東区")
        self.assertEqual(len(found), 1)
        self.assertEqual(audit["search_results_rejected_irrelevant"], 2)
        self.assertEqual(found[0]["discovery_url"], "https://www.city.taito.lg.jp/event")

    def test_annual_rows_remain_unverified_and_pending_decision(self):
        url = "https://www.city.nerima.tokyo.jp/kankomoyoshi/annai/omatsuri/chikusai/index.html"
        result = annual_report({
            "source_id": "nerima_district_festivals_2026",
            "url": url, "target_start": "2026-10-19", "target_end": "2026-11-29"},
            {"status": "checked"}, fake_fetch)
        self.assertEqual(result["status"], "checked", result.get("error"))
        self.assertEqual(result["official_row_count"], 1)
        self.assertEqual(result["decision_reconciliation"], "pending")
        self.assertEqual(result["candidates"][0]["date_start"], "2026-11-29")

    def test_collector_never_authorizes_publication(self):
        result = collect(example_plan(), fake_fetch, max_workers=4)
        self.assertFalse(result["summary"]["publishable"])
        self.assertIn("unverified_candidate_decisions_and_official_event_facts",
                      result["summary"]["blockers"])
        self.assertEqual(result["summary"]["required_source_failures"], [])
        self.assertEqual(result["summary"]["ward_failures"], [])
        self.assertEqual(result["summary"]["annual_schedule"][0]["official_row_count"], 1)
        self.assertGreater(len(result["candidate_pool"]), 0)
        self.assertTrue(all(c.get("status") == "unverified"
                            for c in result["candidate_pool"]))


if __name__ == "__main__":
    unittest.main()
