"""Original 26 fixed sources are protected; additions exist only in a runtime overlay."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from source_fallback_policy import apply_fallback_overlay
from rolling_horizon import source_targets

class FallbackOverlayTests(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads((ROOT / "site/data/discovery_sources.json").read_text(encoding="utf-8"))

    def test_original_registry_unchanged_and_both_routes_expanded_only_in_memory(self):
        before = copy.deepcopy(self.registry)
        augmented = apply_fallback_overlay(self.registry)
        self.assertEqual(self.registry, before)
        self.assertEqual(len(augmented["explicit_sources"]), len(self.registry["explicit_sources"]))
        original = {x["id"]: x for x in before["explicit_sources"]}
        modified = {x["id"]: x for x in augmented["explicit_sources"]}
        for name, prev in original.items():
            after = modified[name]
            if name not in ("tamemap_nakano", "itabashi_tourism_festival"):
                self.assertEqual(after, prev)
        self.assertEqual(len(modified["tamemap_nakano"]["search_urls"]), 2)
        self.assertEqual(len(original["tamemap_nakano"]["search_urls"]), 1)
        self.assertEqual(modified["tamemap_nakano"]["search_urls"][0],
                         original["tamemap_nakano"]["search_urls"][0])
        self.assertEqual(modified["itabashi_tourism_festival"]["fallback_source_ids"],
                         ["itabashi_official_festival"])
        self.assertTrue(modified["itabashi_tourism_festival"]["required"])
        self.assertNotIn("fallback_source_ids", original["itabashi_tourism_festival"])

    def test_rolling_targets_read_two_routes_and_preserve_original_required(self):
        registry = apply_fallback_overlay(self.registry)
        import datetime as dt
        checks=source_targets(registry, dt.date(2026,10,31),dt.date(2026,12,6))
        indexed={c["id"]:c for c in checks}
        self.assertTrue(indexed["tamemap_nakano"]["required"])
        self.assertEqual(len(indexed["tamemap_nakano"]["urls"]),4)
        self.assertTrue(any("/new_arrival" in x for x in indexed["tamemap_nakano"]["urls"]))
        self.assertEqual(len([x for x in indexed["tamemap_nakano"]["urls"] if "/calendar/" in x]),3)
        self.assertTrue(indexed["itabashi_tourism_festival"]["required"])
        self.assertEqual(indexed["itabashi_tourism_festival"]["fallback_source_ids"],
                         ["itabashi_official_festival"])

    def test_missing_original_url_is_fatal(self):
        src=copy.deepcopy(self.registry)
        x=next(s for s in src["explicit_sources"] if s["id"]=="tamemap_nakano")
        x["search_urls"]=["https://example.com/replaced"]
        with self.assertRaisesRegex(ValueError,"registered required URL"):
            apply_fallback_overlay(src)

    def test_overlay_cannot_mutate_the_original_registry(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"overlay.json"
            original=json.loads((ROOT/"policy/source_fallbacks_v1.json").read_text())
            original["sources"][0]["supplemental_search_urls"]=[
                "https://pc.tamemap.net/1311401/calendar/2026-11"]
            p.write_text(json.dumps(original))
            with self.assertRaisesRegex(ValueError,"unapproved supplemental"):
                apply_fallback_overlay(self.registry,p)
        self.assertNotIn("fallback_source_ids",
                         next(s for s in self.registry["explicit_sources"] if s["id"]=="itabashi_tourism_festival"))

if __name__ == "__main__":
    unittest.main()
