"""Review packet is non-publishable; IDs and old event records are protected."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from holiday_after_review_packet import build_packet, event_identity, is_overlapping, attached_weekday_holidays


def plan():
    sats = ["2026-10-24", "2026-10-31", "2026-11-07",
            "2026-11-14", "2026-11-21", "2026-11-28"]
    from datetime import date, timedelta
    return {"status": "eligible", "as_of_jst": "2026-10-19",
            "base_data_production_sha": "a" * 40,
            "weekends": [{"sat": sat, "sun": (date.fromisoformat(sat) + timedelta(days=1)).isoformat(),
                          "publication_tier": "preview"} for sat in sats],
            "holiday_targets": [{"date": "2026-11-23"}]}


class HolidayAfterReviewPacketTests(unittest.TestCase):
    def test_identity_casefold_unicode_and_dates(self):
        e = {"name": "  ＡＢＣ　フェス ", "date_start": "2026-11-01",
             "date_end": "2026-11-01", "venue": " 豊島区 "}
        self.assertEqual(event_identity(e),
                         event_identity({**e, "name": "abc フェス", "venue": "豊島区"}))

    def test_long_event_is_review_candidate_not_verified(self):
        self.assertTrue(is_overlapping({
            "date_start": "2026-10-10", "date_end": "2026-12-10"},
            "2026-11-21", "2026-11-22"))
        self.assertFalse(is_overlapping({
            "date_start": "2026-10-10", "date_end": "2026-10-12"},
            "2026-11-21", "2026-11-22"))

    def test_protected_week_ids_and_independent_holiday(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = {"id": "old-one", "name": "秋の展示", "date_start": "2026-10-01",
                        "date_end": "2026-12-01", "venue": "区立美術館",
                        "official_url": "https://www.example.org/museum"}
            (root / "2026-10-24.json").write_text(json.dumps({"events": [original]}))
            (root / "manifest.json").write_text(json.dumps(
                {"weekends": [{"sat": "2026-10-24", "file": "2026-10-24.json"}]}))
            candidates = [{
                "candidate_id": "rss-new", "name": "親子イベント",
                "status": "unverified", "discovered_via": {
                    "ward": "練馬区", "query": "練馬区 2026-11-23 祝日 親子",
                    "search_url": "https://www.bing.com/search?format=rss"}}]
            evidence = {"summary": {"publishable": False,
                                    "base_data_production_sha": "a" * 40, "wards": {}},
                        "candidate_pool": candidates}
            packet = build_packet(plan(), root, evidence)
            self.assertFalse(packet["publication_permitted"])
            self.assertEqual(packet["published_week_file_changes"], 0)
            self.assertEqual(packet["weeks"][0]["protected_prior_event_ids"], ["old-one"])
            self.assertEqual(packet["weeks"][4]["carryover_review_count"], 1)
            self.assertTrue(packet["weeks"][4]["carryover_needs_daily_confirmation"])
            self.assertEqual(packet["weeks"][4]["suggested_discoveries_count"], 1)

    def test_tuesday_november_third_is_never_lost_or_assigned_to_next_week(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "manifest.json").write_text(json.dumps({"weekends": []}))
            revised = plan()
            revised["holiday_targets"].append({"date": "2026-11-03", "name": "文化の日"})
            self.assertEqual(
                attached_weekday_holidays(revised["weekends"][1], revised["holiday_targets"],
                                          revised["weekends"][2]["sat"]), ["2026-11-03"])
            self.assertEqual(
                attached_weekday_holidays(revised["weekends"][2], revised["holiday_targets"],
                                          revised["weekends"][3]["sat"]), [])
            candidate = {"candidate_id": "nov3-official", "name": "ねりおと♪フェスティバル2026",
                         "matched_dates": ["2026-11-03"], "status": "unverified",
                         "discovered_via": {
                             "ward": "練馬区", "source_id": "nerima",
                             "search_url": "https://www.city.nerima.tokyo.jp/"}}
            candidate_query = {"candidate_id": "nov3-ai", "name": "ねりすぽ",
                               "status": "unverified",
                               "discovered_via": {
                                   "ward": "練馬区", "query": "練馬区 2026-11-03 子ども",
                                   "search_url": "https://www.bing.com/search?format=rss"}}
            evidence = {"summary": {"publishable": False,
                                    "base_data_production_sha": "a" * 40, "wards": {}},
                        "candidate_pool": [candidate, candidate_query]}
            packet = build_packet(revised, root, evidence)
            october = packet["weeks"][1]
            november = packet["weeks"][2]
            self.assertEqual(october["attached_weekday_holidays"], ["2026-11-03"])
            self.assertEqual(october["suggested_discoveries_count"], 2)
            self.assertEqual(october["holiday_leads_by_date"]["2026-11-03"]["candidate_count"], 2)
            self.assertEqual(november["suggested_discoveries_count"], 0)
            holiday = next(h for h in packet["independent_holiday_reviews"] if h["date"] == "2026-11-03")
            self.assertEqual(holiday["assigned_week_sat"], "2026-10-31")
            self.assertTrue(holiday["candidate_handoff_complete"])
            self.assertFalse(packet["publication_permitted"])

    def test_forged_publishable_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "cannot authorize"):
                build_packet(plan(), Path(d), {"summary": {
                    "publishable": True, "base_data_production_sha": "a" * 40}, "candidate_pool": []})


if __name__ == "__main__":
    unittest.main()
