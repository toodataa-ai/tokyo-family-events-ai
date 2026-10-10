import unittest
from tools.validate_official_schedule_audit import validate, WARDS

SOURCE = 'nerima_district_festivals_2026'


def setup():
    checks = [{"source_id": SOURCE, "status": "checked", "url": "https://www.city.nerima.tokyo.jp/example.html",
               "checked_at": "2026-10-10T10:00:00+09:00", "official_row_count": 1,
               "candidate_ids": ["candidate-A"], "matched_candidate_count": 1, "unmatched_official_rows": []}]
    rows = [{"ward": w, "query_logs": [{"query": w + " 祭り", "status": "checked", "checked_at": "2026-10-10T10:00:00+09:00"}],
             "source_checks": [{"url": "https://example.org/", "status": "checked", "checked_at": "2026-10-10T10:00:00+09:00"}]} for w in WARDS]
    run = {"prompt": {"version": "v1.15"}, "discovery_evidence": {"wards": rows}, "official_schedule_checks": checks}
    week = {"sat": "2026-10-10", "coverage": {"wards": [{"ward": w, "status": "checked", "queries": 1, "sources_checked": 1} for w in WARDS]}}
    decisions = {"decisions": [{"candidate_id": "candidate-A", "decision": "published"}]}
    return run, week, decisions


class AuditTests(unittest.TestCase):
    def test_good_audit(self):
        self.assertEqual(validate(*setup()), [])

    def test_missing_source_candidate_fails(self):
        r, w, d = setup()
        d["decisions"] = []
        self.assertTrue(any("reconciliation" in x for x in validate(r, w, d)))

    def test_fake_counters_and_no_evidence_fail(self):
        r, w, d = setup()
        w["coverage"]["wards"][0]["queries"] = 3
        r["discovery_evidence"]["wards"][1]["source_checks"] = []
        self.assertTrue(any("coverage.queries" in x for x in validate(r, w, d)))
        self.assertTrue(any("missing actual" in x for x in validate(r, w, d)))

    def test_historical_runs_not_retroactively_mutated(self):
        r, w, d = setup()
        r["prompt"]["version"] = "v1.5"
        r["discovery_evidence"] = {}
        self.assertEqual(validate(r, w, d), [])


if __name__ == "__main__":
    unittest.main()
