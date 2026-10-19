"""Review packet is non-publishable; IDs and old event records are protected."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from holiday_after_review_packet import build_packet, event_identity, is_overlapping


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

    def test_forged_publishable_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "cannot authorize"):
                build_packet(plan(), Path(d), {"summary": {
                    "publishable": True, "base_data_production_sha": "a" * 40}, "candidate_pool": []})


if __name__ == "__main__":
    unittest.main()
