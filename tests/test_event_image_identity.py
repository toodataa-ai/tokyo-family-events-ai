"""Regression tests for wrong thumbnails on multi-event official articles."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import audit_event_image_identity as audit
import enrich_images


PAGE = "https://www.koho.metro.tokyo.lg.jp/2026/10/08-moyoshi14.html"
OTHER_POSTER = "https://www.koho.metro.tokyo.lg.jp/2026/10/images/202610_moyoshi14_07.png"
RIGHT_POSTER = "https://www.koho.metro.tokyo.lg.jp/2026/10/images/202610_moyoshi14_06.jpg"


def event(eid, name, image=None, page=PAGE):
    return {"id": eid, "name": name, "official_url": page, "url": page,
            "source": page, "image": image}


class ThumbnailIdentityTests(unittest.TestCase):
    def test_detect_original_wrong_shared_event_poster(self):
        rows = [event("a", "交流フェスタ", OTHER_POSTER),
                event("b", "木と暮しのふれあい展", OTHER_POSTER)]
        errors, warnings = audit.inspect_events(rows, "2026-10-24")
        self.assertEqual(len(errors), 1)
        self.assertIn("EVENT_IMAGE_COLLISION", errors[0])
        self.assertIn("交流フェスタ", errors[0])

    def test_accept_correct_posters_on_shared_news_page(self):
        rows = [event("a", "交流フェスタ", RIGHT_POSTER),
                event("b", "木と暮しのふれあい展", OTHER_POSTER)]
        errors, warnings = audit.inspect_events(rows, "2026-10-24")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_shared_site_logo_is_only_warning_not_false_event_poster_alarm(self):
        common = "https://example.org/shared/images/sns/logo.jpg"
        errors, warnings = audit.inspect_events(
            [event("a", "企画展", common), event("b", "地域祭", common)],
            "2026-10-24"
        )
        self.assertFalse(errors)
        self.assertEqual(len(warnings), 1)

    def test_same_long_running_event_can_keep_its_image(self):
        rows = [event("a", "文化の祭典", RIGHT_POSTER),
                event("b", "文化の祭典", RIGHT_POSTER)]
        errors, _ = audit.inspect_events(rows)
        self.assertFalse(errors)

    def test_different_pages_same_image_not_unconditionally_blocked(self):
        rows = [event("a", "催しA", RIGHT_POSTER),
                event("b", "催しB", RIGHT_POSTER,
                      "https://elsewhere.example.org/different")]
        errors, _ = audit.inspect_events(rows)
        self.assertFalse(errors)

    def test_multiple_events_same_article_auto_image_is_blocked(self):
        rows = [event("a", "交流フェスタ"),
                event("b", "木と暮しのふれあい展")]
        shared = enrich_images.shared_multi_event_pages(rows)
        self.assertIn(enrich_images.canonical_page(PAGE), shared)

    def test_same_event_appears_in_different_week_without_false_block(self):
        rows = [event("a", "交流フェスタ"), event("a", "交流フェスタ")]
        self.assertEqual(enrich_images.shared_multi_event_pages(rows), set())

    def test_real_file_audit_detects_shared_poster(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "manifest.json").write_text(
                json.dumps({"weekends": [{"file": "2026-10-24.json"}]}))
            (p / "2026-10-24.json").write_text(json.dumps({
                "sat": "2026-10-24",
                "events": [event("a", "交流フェスタ", OTHER_POSTER),
                           event("b", "木と暮しのふれあい展", OTHER_POSTER)],
            }))
            errors, _ = audit.audit(p)
            self.assertEqual(len(errors), 1)


if __name__ == "__main__":
    unittest.main()
