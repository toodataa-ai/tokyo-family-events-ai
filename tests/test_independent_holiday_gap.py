"""Detect missing single-day official holiday events without touching published data."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_independent_holiday import audit, normalize_url

MANIFEST = {
    "weekends": [
        {"sat": "2026-10-24", "sun": "2026-10-25"},
        {"sat": "2026-10-31", "sun": "2026-11-01"},
        {"sat": "2026-11-07", "sun": "2026-11-08"}
    ],
    "holidays": [{"date": "2026-11-03", "name": "文化の日"}]
}

class HolidayGapTest(unittest.TestCase):
    def test_absence_not_hidden_by_general_multi_day_exhibition(self):
        broad = {"id": "umbrella", "name": "練馬区民文化祭",
                 "date_start": "2026-10-24", "date_end": "2026-11-23",
                 "official_url": "https://www.city.nerima.tokyo.jp/culture"}
        leads = [{"day": "2026-11-03", "name": "ねりおと♪フェスティバル2026",
                  "official_url": "https://www.city.nerima.tokyo.jp/nerioto"}]
        result = audit(MANIFEST, [broad], leads, "2026-11-03")
        self.assertEqual(result["assigned_week_sat"], "2026-10-31")
        self.assertEqual(result["published_holiday_only_count"], 0)
        self.assertEqual(result["published_broad_overlap_count"], 1)
        self.assertEqual(result["unpublished_known_leads"], 1)
        self.assertEqual(result["leads"][0]["status"], "missing_from_published_dataset")
        self.assertFalse(result["publication_permitted"])

    def test_exact_published_row_resolves_one_lead_only(self):
        rows = [
            {"id": "a", "name": "ねりおと♪フェスティバル2026",
             "date_start": "2026-11-03", "date_end": "2026-11-03",
             "official_url": "https://www.city.nerima.tokyo.jp/nerioto"},
            {"id": "b", "name": "別の長期展示",
             "date_start": "2026-10-01", "date_end": "2026-12-01"}
        ]
        leads = [
            {"day": "2026-11-03", "name": "ねりおと♪フェスティバル2026"},
            {"day": "2026-11-03", "name": "ねりすぽフェスティバル"},
            {"day": "2026-11-04", "name": "別の平日イベント"}
        ]
        result = audit(MANIFEST, rows, leads, "2026-11-03")
        self.assertEqual(result["known_leads_checked"], 2)
        self.assertEqual(result["published_holiday_only_count"], 1)
        self.assertEqual(result["unpublished_known_leads"], 1)
        self.assertEqual(result["leads"][0]["published_match_id"], "a")
        self.assertIsNone(result["leads"][1]["published_match_id"])

    def test_unregistered_weekday_is_not_admitted(self):
        with self.assertRaisesRegex(ValueError, "not an official registered holiday"):
            audit(MANIFEST, [], [], "2026-11-04")
        with self.assertRaisesRegex(ValueError, "not attached"):
            audit(MANIFEST, [], [], "2026-11-03X")

    def test_canonical_official_url_strips_query_and_www(self):
        self.assertEqual(normalize_url("https://www.city.nerima.tokyo.jp/path?ref=calendar"),
                         "city.nerima.tokyo.jp/path")


if __name__ == "__main__":
    unittest.main()
