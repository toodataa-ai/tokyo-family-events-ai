import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import validate_non_regression as validator


class Store:
    def __init__(self, files):
        self.files = files
    def read_text(self, path):
        item = self.files.get(path)
        return json.dumps(item, ensure_ascii=False) if item is not None else None


def make_files(drop_second=False):
    dates = ["2026-10-24", "2026-10-31"]
    manifest = {"weekends": [{"sat": s, "file": s + ".json"} for s in dates]}
    files = {"site/data/manifest.json": manifest}
    for i, sat in enumerate(dates):
        same = {"id": "long-running-1", "name": "アーツ中村橋",
                "ward": "練馬区", "date_start": "2026-09-12",
                "date_end": "2026-11-08", "venue": "練馬区立美術館",
                "official_url": "https://example.jp/event/arts"}
        files["site/data/" + sat + ".json"] = {
            "sat": sat, "events": [] if (i == 1 and drop_second) else [same]
        }
    return files


class WeekScopedNonRegressionTests(unittest.TestCase):
    def run_check(self, old, current):
        output = io.StringIO()
        with patch.object(validator, "CurrentStore", lambda: Store(current)), \
             patch.object(validator, "GitStore", lambda ref: Store(old)), \
             patch.object(sys, "argv", ["validator", "--base-ref", "old", "site/data"]), \
             contextlib.redirect_stdout(output):
            result = validator.main()
        return result, output.getvalue()

    def test_same_id_across_two_weeks_does_not_look_missing(self):
        original = make_files()
        status, log = self.run_check(original, make_files())
        self.assertEqual(status, 0, log)
        self.assertIn("compared 2 previously published events", log)

    def test_missing_one_week_fails_even_if_other_week_keeps_id(self):
        status, log = self.run_check(make_files(), make_files(drop_second=True))
        self.assertEqual(status, 1)
        self.assertIn("event disappeared without auditable", log)


if __name__ == "__main__":
    unittest.main()
