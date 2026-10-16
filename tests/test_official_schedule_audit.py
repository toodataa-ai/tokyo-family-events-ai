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

    def test_missing_required_official_source_fails(self):
        run, week, decisions = setup()
        config = {"explicit_sources": [{
            "id": "nakano_official_tourism", "enabled": True, "required": True,
            "search_urls": ["https://www.nakano-kanko.com/event/"],
            "event_row_audit_required": True,
        }]}
        errors = validate(run, week, decisions, config)
        self.assertTrue(any("required source not checked" in x for x in errors))

    def test_unmatched_official_event_row_fails(self):
        run, week, decisions = setup()
        config = {"explicit_sources": [{
            "id": "nakano_official_tourism", "enabled": True, "required": True,
            "search_urls": ["https://www.nakano-kanko.com/event/"],
            "event_row_audit_required": True,
        }]}
        run["explicit_source_checks"] = [{
            "source_id": "nakano_official_tourism", "status": "checked",
            "search_url": "https://www.nakano-kanko.com/event/",
            "checked_at": "2026-10-16T23:00:00+09:00",
            "official_row_count": 1, "candidate_count": 1,
            "candidate_ids": ["missing-Komafes"], "unmatched_official_rows": [],
        }]
        errors = validate(run, week, decisions, config)
        self.assertTrue(any("unreconciled official event rows" in x for x in errors))

    def test_historical_runs_not_retroactively_mutated(self):
        r, w, d = setup()
        r["prompt"]["version"] = "v1.5"
        r["discovery_evidence"] = {}
        self.assertEqual(validate(r, w, d), [])


if __name__ == "__main__":
    unittest.main()
