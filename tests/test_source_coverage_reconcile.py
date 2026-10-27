import json
from pathlib import Path
import tempfile
import unittest

from tools.source_coverage_reconcile import load_published, reconcile
from tools.audit_phase1_source_coverage import audit, suginami_input


DISTRICT_URL = "https://www.city.nerima.tokyo.jp/kankomoyoshi/annai/omatsuri/chikusai/20260616103208700.html"
SUGINAMI_URL = "https://www.city.suginami.tokyo.jp/s033/event/28531.html"


def event(cid, name, day, venue, url):
    return {"id": cid, "name": name, "date_start": day, "date_end": day,
            "venue": venue, "official_url": url}


def decision(cid, decision_type="published", **extra):
    return {"candidate_id": cid, "decision": decision_type,
            "reasons": ["公式確認済み"], "evidence": [{"url": DISTRICT_URL}], **extra}


def data(root, *, published=True, decision_type="published", include_decision=True,
         district_day="2026-11-08", url=DISTRICT_URL, venue="高松小学校（練馬区）"):
    manifest = {"weekends": [
        {"sat": "2026-10-31", "sun": "2026-11-01", "file": "2026-10-31.json"},
        {"sat": "2026-11-07", "sun": "2026-11-08", "file": "2026-11-07.json"}
    ], "holidays": [{"date": "2026-11-03", "name": "文化の日"}]}
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    for week in manifest["weekends"]:
        sat = week["sat"]
        rows = ([event("nerima-district-123", "第四地区祭", district_day, venue, url)]
                if sat == "2026-11-07" and published else [])
        # A November 3 public holiday belongs to 10/31's event shard.
        if sat == "2026-10-31":
            rows = [event("sugi-1", "花と緑の井草祭り", "2026-11-03",
                          "井草森公園", SUGINAMI_URL)]
        (root / f"{sat}-events.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        (root / f"{sat}.json").write_text(
            json.dumps({"event_files": [f"{sat}-events.json"],
                        "coverage": {"published_count": len(rows)}}), encoding="utf-8")
        decisions = ([decision("nerima-district-123", decision_type)]
                     if sat == "2026-11-07" and include_decision else [])
        if sat == "2026-10-31":
            decisions = [decision("suginami-official-28531")]
        (root / f"{sat}-decisions.json").write_text(
            json.dumps({"decisions": decisions}, ensure_ascii=False), encoding="utf-8")


def district_candidate(day="2026-11-08", venue="高松小学校"):
    return {"candidate_id": "nerima-district-123", "name": "第四地区祭",
            "matched_dates": [day], "venue": venue, "official_url": DISTRICT_URL}


def sugi_candidate(dates=None):
    return {"candidate_id": "suginami-official-28531", "name": "花と緑の井草祭り",
            "dates": ["2026-11-03"] if dates is None else dates,
            "official_url": SUGINAMI_URL, "detail_status": "checked"}


class CommonParityTests(unittest.TestCase):
    def with_data(self, fn, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data(root, **kwargs)
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            result = fn(load_published(root))
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()},
                             "Audit must never mutate the published data")
            return result

    def test_district_id_date_venue_official_url_and_decision(self):
        r = self.with_data(lambda s: reconcile(
            "nerima_district_festivals_2026", [district_candidate()], s,
            source_status="checked", expected_count=1))
        self.assertEqual(r["status"], "complete")
        self.assertEqual(r["breakdown"]["published"], 1)

    def test_suginami_id_mapping_uses_exact_detail_url_on_holiday(self):
        r = self.with_data(lambda s: reconcile(
            "suginami_calendar_all", [sugi_candidate()], s, source_status="checked"))
        self.assertEqual(r["breakdown"]["published"], 1)

    def test_missing_data_despite_published_decision_is_inconsistent(self):
        r = self.with_data(lambda s: reconcile(
            "nerima_district_festivals_2026", [district_candidate()], s,
            source_status="checked"), published=False)
        self.assertEqual(r["breakdown"]["inconsistent"], 1)

    def test_excluded_without_proof_does_not_complete_coverage(self):
        def broken(s):
            for d in s["decisions"]:
                if d["decision"].get("candidate_id") == "nerima-district-123":
                    d["decision"].update(decision="excluded", evidence=[], reasons=[])
            return reconcile("nerima_district_festivals_2026",
                             [district_candidate()], s, source_status="checked")
        r = self.with_data(broken, published=False)
        self.assertEqual(r["breakdown"]["inconsistent"], 1)

    def test_proven_exclusion_counts_as_reviewed_not_publication(self):
        r = self.with_data(lambda s: reconcile(
            "nerima_district_festivals_2026", [district_candidate()], s,
            source_status="checked"), published=False, decision_type="excluded")
        self.assertEqual(r["breakdown"]["excluded"], 1)
        self.assertEqual(r["breakdown"]["published"], 0)

    def test_wrong_week_date_not_silently_accepted(self):
        r = self.with_data(lambda s: reconcile(
            "nerima_district_festivals_2026",
            [district_candidate(day="2026-11-03")], s, source_status="checked"))
        self.assertEqual(r["breakdown"]["unreviewed"], 1)

    def test_missing_venue_or_official_source_is_inconsistent(self):
        for kwargs in ({"venue": "全く違う公園"}, {"url": "https://wrong.example.test"}):
            with self.subTest(kwargs=kwargs):
                r = self.with_data(lambda s: reconcile(
                    "nerima_district_festivals_2026", [district_candidate()], s,
                    source_status="checked"), **kwargs)
                self.assertEqual(r["breakdown"]["inconsistent"], 1)

    def test_duplicate_official_ids_cannot_be_silently_deduplicated(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.with_data(lambda s: reconcile(
                "nerima_district_festivals_2026",
                [district_candidate(), district_candidate()], s, source_status="checked"))

    def test_district_address_allows_explicit_ward_prefix_but_not_wrong_school(self):
        r = self.with_data(lambda s: reconcile(
            "nerima_district_festivals_2026",
            [district_candidate(venue="高松小学校（高松3-16-1）")],
            s, source_status="checked"),
            venue="高松小学校（練馬区高松3-16-1）")
        self.assertEqual(r["breakdown"]["published"], 1)
        r = self.with_data(lambda s: reconcile(
            "nerima_district_festivals_2026",
            [district_candidate(venue="高松小学校（高松3-16-1）")],
            s, source_status="checked"),
            venue="高松小学校（練馬区高松3-16-9）")
        self.assertEqual(r["breakdown"]["inconsistent"], 1)

    def test_district_legacy_id_proven_by_official_name_venue_date_decision(self):
        def check(s):
            for e in s["events"]:
                if e["event"]["id"] == "nerima-district-123":
                    e["event"]["id"] = "v15-20261205-toyotama-district"
            for d in s["decisions"]:
                if d["decision"].get("candidate_id") == "nerima-district-123":
                    d["decision"]["candidate_id"] = "v15-20261205-toyotama-district"
            return reconcile("nerima_district_festivals_2026",
                             [district_candidate()], s, source_status="checked")
        r = self.with_data(check)
        self.assertEqual(r["breakdown"]["published"], 1)

    def test_legacy_id_collision_must_keep_distinct_festival_names(self):
        def check(s):
            for e in s["events"]:
                if e["event"]["id"] == "nerima-district-123":
                    e["event"]["id"] = "old-id"
                    e["event"]["name"] = "第一地区祭（別の小学校）"
            return reconcile("nerima_district_festivals_2026",
                             [district_candidate()], s, source_status="checked")
        r = self.with_data(check)
        self.assertEqual(r["breakdown"]["inconsistent"], 1)

    def test_suginami_organizer_alias_needs_proven_event_and_decision(self):
        candidate = {"candidate_id": "suginami-official-22661",
                     "name": "すぎなみフェスタ2026（桃井原っぱ公園ほか）",
                     "dates": ["2026-11-07"],
                     "official_url": "https://www.city.suginami.tokyo.jp/s019/event/22661.html"}
        def check(s):
            for e in s["events"]:
                if e["event"]["id"] == "nerima-district-123":
                    e["event"].update(id="official-2026-suginami-festa",
                                      name="すぎなみフェスタ2026（キッズタウン・スポーツ体験）",
                                      venue="桃井原っぱ公園（杉並区桃井3-8-1）",
                                      official_url="https://www.sugifes.com/event/",
                                      url="https://www.sugifes.com/event/")
                    e["event"]["date_start"] = "2026-11-07"
                    e["event"]["date_end"] = "2026-11-08"
            for d in s["decisions"]:
                if d["decision"].get("candidate_id") == "nerima-district-123":
                    d["decision"].update(candidate_id="manual-primary-official-2026-suginami-festa-2026-11-07",
                                         name="すぎなみフェスタ2026（キッズタウン・スポーツ体験）",
                                         evidence=[{"url": "https://www.sugifes.com/event/"}])
            return reconcile("suginami_calendar_all", [candidate], s, source_status="checked")
        r = self.with_data(check)
        self.assertEqual(r["breakdown"]["published"], 1)

    def test_source_error_never_becomes_zero_found_events(self):
        r = self.with_data(lambda s: reconcile(
            "suginami_calendar_all", [], s, source_status="error"))
        self.assertEqual(r["status"], "source_error")
        self.assertIsNone(r["candidate_count"])
        self.assertIsNone(r["unreconciled_count"])

    def test_suginami_monthly_only_is_not_claimed_as_published(self):
        r = self.with_data(lambda s: reconcile(
            "suginami_calendar_all", [sugi_candidate([])], s, source_status="checked"))
        self.assertEqual(r["breakdown"]["needs_date_review"], 1)

    def test_actual_distinct_candidates_cannot_be_overridden(self):
        with self.assertRaisesRegex(ValueError, "count"):
            self.with_data(lambda s: reconcile(
                "suginami_calendar_all", [sugi_candidate()], s,
                source_status="checked", expected_count=2))

    def test_evidence_missing_is_blocker_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data(root)
            r = audit(root, sources=("nerima", "suginami"))
            self.assertEqual(r["status"], "incomplete")
            self.assertEqual({s["status"] for s in r["sources"]}, {"source_error"})

    def test_suginami_source_requires_complete_daily_and_monthly_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "all_candidate_index.json").write_text("[]", encoding="utf-8")
            (root / "http_evidence.json").write_text(json.dumps(
                {"start": "2026-11-03", "end": "2026-11-03",
                 "distinct_official_candidate_ids": 0,
                 "failed_requests": 0, "official_detail_fetch_failures": 0,
                 "checked_requests": []}), encoding="utf-8")
            import datetime as dt
            c, status, count, notes = suginami_input(root, dt.date(2026, 11, 3), dt.date(2026, 11, 3))
            self.assertEqual(status, "error")
            self.assertIn("daily", notes["blocker"])


    def test_ordinary_weekday_is_out_of_scope_not_a_missing_event(self):
        r = self.with_data(lambda s: reconcile(
            "suginami_calendar_all",
            [{"candidate_id": "suginami-official-11111",
              "name": "平日だけの講座", "dates": ["2026-11-04"],
              "official_url": "https://www.city.suginami.tokyo.jp/s033/event/11111.html"}],
            s, source_status="checked"))
        self.assertEqual(r["status"], "complete")
        self.assertEqual(r["breakdown"]["out_of_scope"], 1)
        self.assertEqual(r["unreconciled_count"], 0)
        self.assertEqual(r["in_scope_candidate_count"], 0)

    def test_multiday_event_only_checks_saturday_sunday_and_public_holiday(self):
        r = self.with_data(lambda s: reconcile(
            "suginami_calendar_all",
            [sugi_candidate(["2026-11-02", "2026-11-03",
                             "2026-11-04", "2026-11-07"])],
            s, source_status="checked"))
        self.assertEqual(r["date_scoped_rows"], 2)
        self.assertEqual({tuple(r["dates"]) for r in r["rows"]},
                         {("2026-11-03",), ("2026-11-07",)})
        self.assertEqual(r["breakdown"]["published"], 1)
        self.assertEqual(r["breakdown"]["unreviewed"], 1)


if __name__ == "__main__":
    unittest.main()
