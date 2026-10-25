"""Regression: holiday-only events are valid without admitting arbitrary weekdays."""
import datetime as dt
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from validate_data import independent_holidays_by_week, overlaps_weekend_or_attached_holiday


class IndependentHolidayTest(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            "weekends": [
                {"sat": "2026-10-24", "sun": "2026-10-25"},
                {"sat": "2026-10-31", "sun": "2026-11-01"},
                {"sat": "2026-11-07", "sun": "2026-11-08"},
            ],
            "holidays": [
                {"date": "2026-11-03", "name": "文化の日"},
                {"date": "2026-11-05", "name": "test holiday"},
                {"date": "2026-10-25", "name": "weekend overlap"},
                {"date": "2026-11-14", "name": "outside this horizon"},
            ],
        }

    def test_holiday_is_attached_only_to_preceding_weekend(self):
        dates = independent_holidays_by_week(self.manifest)
        self.assertEqual(dates["2026-10-31"], [dt.date(2026, 11, 3), dt.date(2026, 11, 5)])
        self.assertEqual(dates["2026-10-24"], [])
        self.assertEqual(dates["2026-11-07"], [])

    def test_ordinary_weekdays_remain_invalid_and_edges_inclusive(self):
        sat, sun = dt.date(2026, 10, 31), dt.date(2026, 11, 1)
        allowed = [dt.date(2026, 11, 3)]
        self.assertTrue(overlaps_weekend_or_attached_holiday(dt.date(2026, 11, 3), dt.date(2026, 11, 3), sat, sun, allowed))
        self.assertTrue(overlaps_weekend_or_attached_holiday(dt.date(2026, 11, 1), dt.date(2026, 11, 1), sat, sun, allowed))
        self.assertFalse(overlaps_weekend_or_attached_holiday(dt.date(2026, 11, 2), dt.date(2026, 11, 2), sat, sun, allowed))
        self.assertFalse(overlaps_weekend_or_attached_holiday(dt.date(2026, 11, 4), dt.date(2026, 11, 4), sat, sun, allowed))
        self.assertFalse(overlaps_weekend_or_attached_holiday(dt.date(2026, 11, 3), dt.date(2026, 11, 3), dt.date(2026, 11, 7), dt.date(2026, 11, 8), []))


if __name__ == "__main__":
    unittest.main()
