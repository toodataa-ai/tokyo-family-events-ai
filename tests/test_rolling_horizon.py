import datetime as dt
import importlib.util
import pathlib
import unittest

MODULE = pathlib.Path(__file__).resolve().parents[1] / "tools" / "rolling_horizon.py"
spec = importlib.util.spec_from_file_location("rolling_horizon", MODULE)
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)
SHA = "a" * 40
HOLIDAYS = {
    dt.date(2026, 1, 1): "元日", dt.date(2026, 10, 12): "スポーツの日",
    dt.date(2026, 11, 3): "文化の日", dt.date(2026, 11, 23): "勤労感謝の日",
    dt.date(2027, 1, 1): "元日", dt.date(2027, 11, 23): "勤労感謝の日",
}
MANIFEST = {"weekends": [{"sat": x, "file": x + ".json"} for x in (
    "2026-10-10", "2026-10-17", "2026-10-24",
    "2026-10-31", "2026-11-07", "2026-11-14")]}
SOURCES = {
    "discovery_strategy": {"ai_cross_search": {"enabled": True},
                           "explicit_sources": {"enabled": True}},
    "protected_legacy_source_ids": ["nerima", "suginami"],
    "explicit_sources": [
        {"id": "nerima", "required": True, "enabled": True,
         "search_urls": ["https://www.nerimakanko.jp/event/search.php?month={YYYY-MM}"]},
        {"id": "suginami", "required": True, "enabled": True,
         "search_urls": ["https://city.example.jp/calendar?year={YYYY}&month={MM}"]},
    ]
}
class RollingHorizonTests(unittest.TestCase):
    def plan(self, day, holidays=HOLIDAYS, sources=SOURCES):
        return planner.calculate(dt.date.fromisoformat(day), holidays, MANIFEST, sources, SHA)
    def test_october_holiday_block_and_six_weeks(self):
        r = self.plan("2026-10-13")
        self.assertEqual(r["status"], "eligible")
        self.assertEqual((r["holiday_block_start"], r["holiday_block_end"]),
                         ("2026-10-10", "2026-10-12"))
        self.assertEqual((r["target_start"], r["target_end"]), ("2026-10-13", "2026-11-23"))
        self.assertEqual([w["sat"] for w in r["weekends"]],
                         ["2026-10-17", "2026-10-24", "2026-10-31",
                          "2026-11-07", "2026-11-14", "2026-11-21"])
        self.assertEqual([w["publication_tier"] for w in r["weekends"]],
                         ["full", "full", "preview", "preview", "announcement", "announcement"])
        self.assertEqual(r["weekends"][-1]["action"], "discover_and_verify")
        self.assertEqual(r["weekends"][0]["action"], "re_audit")
        self.assertEqual(r["retired_week_starts"], ["2026-10-10"])
        self.assertFalse(r["publication_permitted"])
        self.assertEqual([h["date"] for h in r["holiday_targets"]],
                         ["2026-11-03", "2026-11-23"])
        self.assertTrue(all(h["requires_independent_23_ward_search"] for h in r["holiday_targets"]))
    def test_skip_other_days(self):
        for d in ("2026-10-12", "2026-10-14", "2026-10-16", "2026-10-17"):
            self.assertEqual(self.plan(d)["status"], "skipped", d)
    def test_regular_monday(self):
        self.assertEqual(self.plan("2026-10-19")["holiday_block_start"], "2026-10-17")
    def test_single_holiday_then_weekday(self):
        self.assertEqual(self.plan("2026-11-04")["holiday_block_end"], "2026-11-03")
    def test_november_three_day_weekend(self):
        self.assertEqual(self.plan("2026-11-24")["holiday_block_start"], "2026-11-21")
    def test_cross_year(self):
        r = self.plan("2026-12-28")
        self.assertEqual(r["weekends"][-1]["sat"], "2027-02-06")
        self.assertEqual(r["target_end"], "2027-02-07")
        self.assertIn("2027-01-01", [h["date"] for h in r["holiday_targets"]])
    def test_urls_expand_each_month(self):
        t = {s["id"]: s for s in self.plan("2026-10-13")["explicit_source_checks"]}
        self.assertEqual(len(t["nerima"]["urls"]), 2)
        self.assertIn("2026-11", t["nerima"]["urls"][1])
        self.assertIn("month=11", t["suginami"]["urls"][1])
        self.assertEqual(t["nerima"]["status"], "pending")
    def test_fail_closed_future_holidays(self):
        old = {k: v for k, v in HOLIDAYS.items() if k.year == 2026}
        with self.assertRaisesRegex(planner.PlanError, "2027"):
            self.plan("2026-12-28", holidays=old)
    def test_fail_closed_source_registry(self):
        broken = {**SOURCES, "explicit_sources": SOURCES["explicit_sources"][:1]}
        with self.assertRaisesRegex(planner.PlanError, "protected source"):
            self.plan("2026-10-13", sources=broken)
    def test_fail_closed_bad_sha(self):
        with self.assertRaisesRegex(planner.PlanError, "SHA"):
            planner.calculate(dt.date(2026, 10, 13), HOLIDAYS, MANIFEST, SOURCES, "abc")
    def test_shift_jis_csv(self):
        data = "国民の祝日・休日月日,国民の祝日・休日名称\n2026-10-12,スポーツの日\n"
        r = planner.parse_official_csv(data.encode("cp932"))
        self.assertEqual(r[dt.date(2026, 10, 12)], "スポーツの日")
    def test_disabled_protected_source(self):
        broken = {**SOURCES, "explicit_sources": [
            {**SOURCES["explicit_sources"][0], "enabled": False},
            SOURCES["explicit_sources"][1]]}
        with self.assertRaisesRegex(planner.PlanError, "protected source disabled"):
            self.plan("2026-10-13", sources=broken)
if __name__ == "__main__":
    unittest.main()
