"""Regression tests: old published events can never vanish without approval."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECK = ROOT / "tools" / "validate_protected_events.py"
SAT = "2026-10-17"


class PreservationTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.cwd = pathlib.Path(self.t.name)
        self.data = self.cwd / "site" / "data"
        self.data.mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=self.cwd, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=self.cwd, check=True)
        subprocess.run(["git", "config", "user.name", "test"], cwd=self.cwd, check=True)
        self.events = [{"id": "baseline-1", "name": "既存イベント", "ward": "中野区"}]
        self.save()
        subprocess.run(["git", "add", "."], cwd=self.cwd, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=self.cwd, check=True)

    def write(self, name, obj):
        (self.data / name).write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

    def save(self):
        self.write("manifest.json", {"weekends": [{"sat": SAT, "file": SAT + ".json", "count": len(self.events)}]})
        self.write(SAT + ".json", {"sat": SAT, "events": self.events})
        self.write("update_history.json", {"history": [{"run_id": "original"}]})
        self.write("discovery_sources.json", {"explicit_sources": [{"id": "original", "enabled": True}]})

    def gate(self):
        return subprocess.run([sys.executable, str(CHECK), "--base-ref", "HEAD", "site/data"],
                              cwd=self.cwd, capture_output=True, text=True)

    def test_append_only_passes(self):
        self.events.append({"id": "new-2", "name": "追加イベント", "ward": "板橋区"})
        self.save()
        self.assertEqual(self.gate().returncode, 0)

    def test_single_event_deletion_fails_even_with_decision(self):
        self.events = []
        self.save()
        result = self.gate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("UNAPPROVED EVENT REMOVAL", result.stderr)

    def test_removal_of_historical_week_file_fails(self):
        (self.data / (SAT + ".json")).unlink()
        self.assertNotEqual(self.gate().returncode, 0)

    def test_rewritten_history_fails(self):
        self.write("update_history.json", {"history": []})
        self.assertIn("history", self.gate().stderr)

    def test_discovery_source_deletion_fails(self):
        self.write("discovery_sources.json", {"explicit_sources": []})
        self.assertIn("source removed", self.gate().stderr)

    def test_unapproved_ledger_inside_data_cannot_override(self):
        self.events = []
        self.save()
        self.write("approved_event_removals.json", {"approvals": [{
            "week_start": SAT, "event_id": "baseline-1", "status": "approved",
            "approval_reference": "self-approved-data", "official_evidence_url": "https://example.org"
        }]})
        self.assertNotEqual(self.gate().returncode, 0)


if __name__ == "__main__":
    unittest.main()
