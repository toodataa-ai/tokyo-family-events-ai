import datetime as dt
import io
import json
import pathlib
import tempfile
import unittest
from contextlib import redirect_stdout

from tools.nerima_annual_resolver import LISTING_URL, fiscal_year, resolve_annual_schedule_urls
from tools.official_schedule_discovery import extract_candidates, main as discovery_main
from tools.rolling_horizon import source_targets

OLD_URL = "https://www.city.nerima.tokyo.jp/kankomoyoshi/annai/omatsuri/chikusai/20260616103208700.html"
NEW_URL = "https://www.city.nerima.tokyo.jp/kankomoyoshi/annai/omatsuri/chikusai/20270617103208700.html"
INDEX = """<html><title>地区祭</title><h1>開催日程</h1>
<a href="20260616103208700.html">令和8年度　地区祭開催日程</a>
<a href="20270617103208700.html"><span>令和9年度</span>　地区祭開催日程</a></html>"""
SCHEDULE_2027 = """<html><head><title>令和9年度　地区祭開催日程</title></head><body><table>
<tr><th>開催月</th><th>地区祭名</th><th>開催日</th><th>時間</th><th>会場</th><th>内容</th><th>連絡先</th></tr>
<tr><td>10月</td><td>光が丘地区祭</td><td>10月16日（土）<br>10月17日（日）</td><td>10時～17時</td><td>光が丘区民センター</td><td>出店と遊び</td><td></td></tr>
<tr><td>3月</td><td>第一地区祭</td><td>3月4日（土）</td><td>10時～12時</td><td>第一小学校</td><td>遊び</td><td></td></tr>
</table></body></html>"""


class AnnualDiscoveryTests(unittest.TestCase):
    def test_annual_page_uses_actual_official_2026_and_2027_links(self):
        self.assertEqual(resolve_annual_schedule_urls(INDEX, dt.date(2026, 10, 1), dt.date(2026, 10, 31)), [(2026, OLD_URL)])
        self.assertEqual(resolve_annual_schedule_urls(INDEX, dt.date(2027, 10, 1), dt.date(2027, 10, 31)), [(2027, NEW_URL)])

    def test_march_belongs_to_previous_fiscal_year(self):
        self.assertEqual(fiscal_year(dt.date(2028, 3, 4)), 2027)
        self.assertEqual(resolve_annual_schedule_urls(INDEX, dt.date(2028, 3, 1), dt.date(2028, 3, 10)), [(2027, NEW_URL)])
        self.assertEqual(resolve_annual_schedule_urls(INDEX, dt.date(2027, 3, 31), dt.date(2027, 4, 1)), [(2026, OLD_URL), (2027, NEW_URL)])

    def test_no_prior_year_fallback_for_unpublished_year(self):
        with self.assertRaisesRegex(ValueError, "2028"):
            resolve_annual_schedule_urls(INDEX, dt.date(2028, 10, 1), dt.date(2028, 11, 1))

    def test_wrong_host_or_ambiguous_year_are_blocked(self):
        malicious = INDEX.replace("20270617103208700.html", "https://evil.example/20270617103208700.html")
        with self.assertRaisesRegex(ValueError, "Untrusted"):
            resolve_annual_schedule_urls(malicious, dt.date(2027, 10, 1), dt.date(2027, 10, 31))
        duplicate = INDEX.replace("</html>", '<a href="other.html">令和9年度 地区祭開催日程</a></html>')
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            resolve_annual_schedule_urls(duplicate, dt.date(2027, 10, 1), dt.date(2027, 10, 31))

    def test_candidate_year_and_provenance(self):
        actual = extract_candidates(SCHEDULE_2027, dt.date(2027, 10, 1), dt.date(2027, 10, 31),
                                    fiscal_start_year=2027, source_url=NEW_URL)
        self.assertEqual(len(actual), 1)
        self.assertEqual(actual[0]["dates"], ["2027-10-16", "2027-10-17"])
        self.assertEqual(actual[0]["official_url"], NEW_URL)
        self.assertEqual(actual[0]["discovery_sources"][0]["url"], NEW_URL)
        march = extract_candidates(SCHEDULE_2027, dt.date(2028, 3, 1), dt.date(2028, 3, 10),
                                   fiscal_start_year=2027, source_url=NEW_URL)
        self.assertEqual(march[0]["dates"], ["2028-03-04"])
        with self.assertRaisesRegex(ValueError, "fiscal-year marker"):
            extract_candidates(SCHEDULE_2027, dt.date(2026, 10, 1), dt.date(2026, 10, 31),
                               fiscal_start_year=2026)

    def test_offline_run_and_row_evidence(self):
        with tempfile.TemporaryDirectory() as work:
            base = pathlib.Path(work)
            (base / "index.html").write_text(INDEX, encoding="utf-8")
            (base / "2027.html").write_text(SCHEDULE_2027, encoding="utf-8")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = discovery_main(["--start", "2027-10-01", "--end", "2027-10-31",
                                       "--listing-html-file", str(base / "index.html"),
                                       "--annual-html-dir", str(base)])
            self.assertEqual(code, 0)
            report = json.loads(buf.getvalue())
            self.assertEqual(report["status"], "checked")
            self.assertEqual(report["url"], LISTING_URL)
            self.assertEqual(report["resolved_pages"][0]["resolved_url"], NEW_URL)
            self.assertEqual(report["candidate_count"], 1)

    def test_planner_uses_index_not_obsolete_year_url(self):
        cfg = {"discovery_strategy": {"ai_cross_search": {"enabled": True},
                                      "explicit_sources": {"enabled": True}},
               "protected_legacy_source_ids": [],
               "explicit_sources": [{"id": "nerima_district_festivals_2026", "required": True,
                                     "enabled": True, "search_urls": [OLD_URL],
                                     "annual_listing_url": LISTING_URL}]}
        items = source_targets(cfg, dt.date(2027, 10, 1), dt.date(2027, 11, 30))
        self.assertEqual(items[0]["urls"], [LISTING_URL])
        self.assertEqual(items[0]["fiscal_years_to_resolve"], [2027])
        self.assertNotIn(OLD_URL, items[0]["urls"])


if __name__ == "__main__":
    unittest.main()
