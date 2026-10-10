import datetime as dt
import json
import pathlib
import tempfile
import unittest
from tools.official_schedule_discovery import extract_candidates, check_decisions

URL = "https://www.city.nerima.tokyo.jp/kankomoyoshi/annai/omatsuri/chikusai/20260616103208700.html"
FIXTURE = """<html><head><title>令和8年度　地区祭開催日程</title></head><body><table>
<tr><th>開催月</th><th>地区祭名</th><th>開催日</th><th>時間</th><th>会場</th><th>内容</th><th>連絡先</th></tr>
<tr><td>10月</td><td>光が丘地区祭</td><td>10月10日（土）<br>10月11日（日）</td><td>10時～17時</td><td>光が丘区民センター</td><td>展示、催事、模擬店</td><td></td></tr>
<tr><td></td><td>第一地区祭（南町小学校）</td><td>10月24日（土）</td><td>14時～19時</td><td>南町小学校</td><td>読み聞かせ、花火</td><td></td></tr>
<tr><td>第七地区祭（田柄）</td><td>10月18日（日）</td><td>9時30分～14時</td><td>田柄小学校</td><td>ミニSL、おみこし</td><td></td></tr>
<tr><td></td><td>第一地区祭（豊玉南小学校）</td><td>11月29日（日）</td><td>10時～12時</td><td>豊玉南小学校</td><td>ゲーム</td><td></td></tr>
</table></body></html>"""


class DiscoveryTests(unittest.TestCase):
    def test_multiple_rows_and_multiple_dates(self):
        candidates = extract_candidates(FIXTURE, dt.date(2026, 10, 10), dt.date(2026, 10, 25))
        self.assertEqual(len(candidates), 3)
        hikari = next(c for c in candidates if c["name"] == "光が丘地区祭")
        self.assertEqual(hikari["dates"], ["2026-10-10", "2026-10-11"])
        self.assertEqual(hikari["date_end"], "2026-10-11")
        self.assertEqual(hikari["discovery_sources"][0]["source_id"], "nerima_district_festivals_2026")
        self.assertIn("ミニSL", next(c["description"] for c in candidates if "田柄" in c["name"]))

    def test_fails_closed_on_missing_year_or_empty_range(self):
        with self.assertRaises(ValueError):
            extract_candidates(FIXTURE.replace("令和8年度", "令和7年度"), dt.date(2026, 10, 10), dt.date(2026, 10, 25))
        with self.assertRaises(ValueError):
            extract_candidates(FIXTURE, dt.date(2026, 12, 1), dt.date(2026, 12, 2))

    def test_missing_coverage_is_not_success(self):
        candidates = extract_candidates(FIXTURE, dt.date(2026, 10, 10), dt.date(2026, 10, 25))
        with tempfile.TemporaryDirectory() as tmp:
            file = pathlib.Path(tmp) / "decisions.json"
            file.write_text(json.dumps({"decisions": [{"candidate_id": candidates[0]["candidate_id"], "decision": "published"}]}), encoding="utf-8")
            self.assertEqual(len(check_decisions(candidates, [file])), 2)
            file.write_text(json.dumps({"decisions": [{"candidate_id": c["candidate_id"], "decision": "published"} for c in candidates]}), encoding="utf-8")
            self.assertEqual(check_decisions(candidates, [file]), [])


if __name__ == "__main__":
    unittest.main()
