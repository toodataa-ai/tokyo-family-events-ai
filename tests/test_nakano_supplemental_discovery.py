"""Tests for additive, source-preserving Nakano alternative discovery."""
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / "tools"))
from nakano_supplemental_discovery import calendar_candidates, collect_supplemental
from holiday_after_collect import collect

MONTH = """<html><head><title>2026年11月カレンダー</title></head>
<body><h1>2026年11月カレンダー</h1><table>
<tr><th>開催日</th><th>イベント</th></tr>
<tr><td>7日 土曜日</td><td><a href="/event/2026/food.html">親子の食体験ワークショップ</a></td></tr>
<tr><td>21日 土曜日</td><td><a href="/event/2026/safety.html">子どもの防災講座</a></td></tr>
<tr><td>22日 日曜日</td><td>イベントはありません</td></tr>
<tr><td>23日 月曜日</td><td><a href="/event/2026/safety.html">子どもの防災講座</a></td></tr>
<tr><td>30日 月曜日</td><td><a href="/event/2026/outside.html">月末コンサート</a></td></tr>
</table></body></html>"""
OCT = """<html><title>2026年10月カレンダー</title><h1>2026年10月カレンダー</h1>
<table><tr><td>24日 土曜日</td><td><a href="/event/2026/oct.html">なかの子ども体験</a></td></tr></table></html>"""
COMMUNITY = """<html><title>なかの情報 イベント一覧</title><a href="/nakanoinfo/event/result/?id=3">
親子も楽しむスタンプラリー</a>
<a href="/nakanoinfo/event/result/?id=4">おもちゃDAY</a>
<a href="/contact/">イベント情報はこちら</a></html>"""
RSS = """<rss><channel><item><title>子どもイベント</title>
<link>https://www.city.tokyo-nakano.lg.jp/event/test</link></item></channel></rss>"""
INDEX = """<html><title>地区祭</title><a href="20260616103208700.html">
令和8年度 地区祭開催日程</a></html>"""
ANNUAL = """<html><title>令和8年度 地区祭開催日程</title><table>
<tr><th>開催月</th><th>地区祭名</th><th>開催日</th><th>時間</th><th>会場</th><th>内容</th><th>連絡先</th></tr>
<tr><td>11月</td><td>第一地区祭</td><td>11月29日</td><td>10時</td>
<td>小学校</td><td>ゲーム体験</td><td>問い合わせ</td></tr></table></html>"""

def fake(url):
    if "pc.tamemap.net" in url:
        raise OSError("HTTP Error 403: Forbidden")
    if "list_calendar202610.html" in url:
        raise OSError("HTTP Error 404: Not Found")
    if "list_calendar202611.html" in url:
        content = MONTH
    elif "list_calendar.html" in url:
        content = OCT
    elif "nakanoshakyo.com" in url:
        content = COMMUNITY
    elif "chikusai/index.html" in url:
        content = INDEX
    elif "chikusai/20260616103208700.html" in url:
        content = ANNUAL
    elif "format=rss" in url:
        content = RSS
    else:
        content = COMMUNITY
    return (200,content.encode("utf-8"),url,"text/html")

def plan():
    from datetime import date,timedelta
    sats=["2026-10-24","2026-10-31","2026-11-07","2026-11-14","2026-11-21","2026-11-28"]
    return {"status":"eligible","publication_permitted":False,"as_of_jst":"2026-10-19",
            "base_data_production_sha":"a"*40,"target_start":"2026-10-19","target_end":"2026-11-29",
            "weekends":[{"sat":s,"sun":(date.fromisoformat(s)+timedelta(days=1)).isoformat()}
                        for s in sats],
            "holiday_targets":[{"date":"2026-11-03","requires_independent_23_ward_search":True},
                               {"date":"2026-11-23","requires_independent_23_ward_search":True}],
            "explicit_source_checks":[{"id":"tamemap_nakano","required":True,
                                       "urls":["https://pc.tamemap.net/1311401/calendar/2026-11"]}]}
def config():
    return json.loads((Path(__file__).parents[1] / "policy/nakano_supplemental_sources.json").read_text())

class SourceTests(unittest.TestCase):
    def test_date_rows_are_distinct_and_horizon_filtered(self):
        from datetime import date
        got=calendar_candidates(MONTH,
              "https://www.city.tokyo-nakano.lg.jp/event/calendar/list_calendar202611.html",
              date(2026,11,1),date(2026,11,19),date(2026,11,29),"nakano_city_calendar_all")
        self.assertEqual(len(got),2)
        self.assertEqual([c["date_from_calendar"] for c in got],
                         ["2026-11-21","2026-11-23"])
        self.assertNotEqual(got[0]["candidate_id"],got[1]["candidate_id"])
        self.assertTrue(all(c["status"]=="unverified" for c in got))

    def test_mismatched_month_is_error(self):
        from datetime import date
        with self.assertRaisesRegex(ValueError,"year-month"):
            calendar_candidates(OCT,"https://www.city.tokyo-nakano.lg.jp/event/calendar/list_calendar.html",
                date(2026,11,1),date(2026,11,1),date(2026,11,30),"any")

    def test_404_month_uses_current_month_if_verified(self):
        r=collect_supplemental(plan(),config(),fake)
        self.assertEqual(r["supplemental_failures"],[])
        self.assertEqual(len(r["source_checks"]),6)
        oct_row=[s for s in r["source_checks"] if s.get("month")=="2026-10"]
        self.assertEqual(len(oct_row),2)
        self.assertTrue(all(s["status"]=="checked" for s in oct_row))
        self.assertTrue(all(s["search_url"].endswith("/list_calendar.html") for s in oct_row))
        self.assertTrue(all(s["attempts"][0]["status"]=="error" for s in oct_row))
        self.assertFalse(r["tamemap_required_check_satisfied"])
        self.assertFalse(r["publishable"])

    def test_short_non_keyword_community_programs_are_not_lost(self):
        from nakano_supplemental_discovery import community_listing_links
        found = community_listing_links(COMMUNITY,
                                       "https://nakanoshakyo.com/nakanoinfo/event/index.php")
        self.assertEqual(len(found), 2)
        self.assertIn("おもちゃDAY", [c["name"] for c in found])
        self.assertTrue(all(c["discovery_url"].startswith("https://nakanoshakyo.com/nakanoinfo/")
                            for c in found))

    def test_tamemap_403_preserved_even_if_supplement_succeeds(self):
        result=collect(plan(),fetcher=fake,max_workers=5,supplemental_config=config())
        self.assertTrue(any(x["id"]=="tamemap_nakano" for x in result["summary"]["required_source_failures"]))
        self.assertIn("required_explicit_url_errors",result["summary"]["blockers"])
        self.assertGreater(result["summary"]["supplemental_checked"],0)
        self.assertEqual(result["summary"]["supplemental_failures"],[])
        self.assertTrue(result["summary"]["tamemap_source_still_required"])
        self.assertFalse(result["summary"]["publishable"])
        self.assertTrue(any(c.get("date_from_calendar")=="2026-11-23" for c in result["candidate_pool"]))

if __name__=="__main__":
    unittest.main()
