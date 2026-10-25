"""Future standalone holidays cannot vanish from date-scoped collection."""
import datetime as dt
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_weekday_holiday_coverage import coverage


class CoverageTest(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            "weekends": [
                {"sat": (dt.date(2026, 10, 24) + dt.timedelta(days=7 * i)).isoformat(),
                 "sun": (dt.date(2026, 10, 25) + dt.timedelta(days=7 * i)).isoformat()}
                for i in range(6)
            ],
            "holidays": [{"date": "2026-11-03", "name": "文化の日"}]
        }
        self.official = {
            dt.date(2026, 11, 3): "文化の日",
            dt.date(2026, 11, 23): "勤労感謝の日",
            dt.date(2026, 10, 12): "スポーツの日",
        }

    def test_detects_missing_nov23_even_after_nov3_added(self):
        result = coverage(self.manifest, self.official, dt.date(2026,10,26))
        self.assertFalse(result["publication_permitted"])
        self.assertEqual(result["upcoming_missing_holidays"],
                         [{"date": "2026-11-23", "name": "勤労感謝の日"}])

    def test_registering_all_official_holidays_allows_publication(self):
        self.manifest["holidays"].append({"date":"2026-11-23","name":"勤労感謝の日"})
        result = coverage(self.manifest, self.official)
        self.assertTrue(result["publication_permitted"])
        self.assertEqual(result["missing_independent_weekday_holidays"], [])

    def test_regular_weekdays_are_not_holidays(self):
        self.assertEqual(coverage(self.manifest, {}, dt.date(2026,10,26))
                         ["missing_independent_weekday_holidays"], [])

if __name__ == "__main__":
    unittest.main()
