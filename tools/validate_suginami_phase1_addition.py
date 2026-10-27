#!/usr/bin/env python3
"""Immutable two-record Suginami first-wave event promotion gate.

Run against a data-staging candidate with --base-ref set to current
data-production SHA. Fail closed on any deletion, reassignment, altered
existing row, changed historical evidence, or extra unapproved candidate.
This does not fetch websites, approve more sources, or perform a deployment.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

PREFIX = "site/data/"
BASE_IDS = {
    "2026-10-31": ("suginami-official-22586", "https://www.city.suginami.tokyo.jp/s113/event/22586.html"),
    "2026-12-05": ("suginami-official-23878", "https://www.city.suginami.tokyo.jp/s113/event/23878.html"),
}
HISTORY_TYPE = "manual_verified_suginami_phase1_addition"
BASE = {"2026-10-31", "2026-12-05"}
ALL_FILES = {PREFIX + "manifest.json", PREFIX + "update_history.json"}
for day in BASE:
    ALL_FILES.update({
        PREFIX + day + ".json", PREFIX + day + "-run.json",
        PREFIX + day + "-decisions.json",
        PREFIX + day + "-verification.json",
        PREFIX + day + "-events-suginami-official-20261027.json",
    })


def read(path):
    return json.loads(Path(PREFIX + path).read_text(encoding="utf-8"))


def before(ref, path):
    return json.loads(subprocess.check_output(
        ["git", "show", ref + ":" + PREFIX + path], text=True))


def assert_equal(a, b, label):
    if a != b:
        raise ValueError(label + ": previously published evidence changed")


def change_count(after, old, fields, label):
    other_after = {k: v for k, v in after.items() if k not in fields}
    other_old = {k: v for k, v in old.items() if k not in fields}
    assert_equal(other_old, other_after, label + " metadata")
    for key in fields:
        if after.get(key) != old.get(key, 0) + 1:
            raise ValueError(label + "." + key + " must increase by exactly one")


def verify(base_ref):
    paths = set(subprocess.check_output(
        ["git", "diff", "--name-only", base_ref, "HEAD"], text=True).splitlines())
    if paths != ALL_FILES:
        raise ValueError("strict changed-file set mismatch: " + repr(sorted(paths ^ ALL_FILES)))

    manifest_old = before(base_ref, "manifest.json")
    manifest_new = read("manifest.json")
    assert_equal({k: v for k, v in manifest_old.items() if k not in ("weekends", "generated")},
                 {k: v for k, v in manifest_new.items() if k not in ("weekends", "generated")},
                 "manifest stable settings/holidays")
    if manifest_new["generated"] <= manifest_old["generated"]:
        raise ValueError("manifest generated timestamp not increasing")
    if len(manifest_new["weekends"]) != 6 or len(manifest_old["weekends"]) != 6:
        raise ValueError("rolling horizon must stay 6 weeks")
    old_events_by_week = {}
    for w0, w1 in zip(manifest_old["weekends"], manifest_new["weekends"]):
        if w1["sat"] != w0["sat"] or w1["sun"] != w0["sun"]:
            raise ValueError("week identity shifted")
        week = w0["sat"]
        if week in BASE:
            assert_equal({k: v for k, v in w0.items() if k != "count"},
                         {k: v for k, v in w1.items() if k != "count"},
                         week + " manifest metadata")
            if w1["count"] != w0["count"] + 1:
                raise ValueError(week + " manifest count")
        else:
            assert_equal(w0, w1, week + " untouched weekend")
        old = before(base_ref, week + ".json")
        new = read(week + ".json")
        if week not in BASE:
            assert_equal(old, new, week + " unchanged weekend file")
            continue
        shard = week + "-events-suginami-official-20261027.json"
        assert_equal(old.get("event_files", []) + [shard], new.get("event_files", []),
                     week + " new shard must only append")
        assert_equal({k: v for k, v in old.items() if k not in ("event_files", "coverage", "generated")},
                     {k: v for k, v in new.items() if k not in ("event_files", "coverage", "generated")},
                     week + " preserved metadata")
        if new.get("generated") <= old.get("generated", ""):
            raise ValueError(week + " generated timestamp")
        oc, nc = old["coverage"], new["coverage"]
        for key in ("published_count", "candidate_count"):
            if nc.get(key) != oc.get(key, 0) + 1:
                raise ValueError(week + " coverage." + key + " must add exactly one")
        assert_equal({k: v for k, v in oc.items() if k not in ("published_count", "candidate_count", "wards")},
                     {k: v for k, v in nc.items() if k not in ("published_count", "candidate_count", "wards")},
                     week + " source/coverage historical values")
        original_wards = oc["wards"]
        current_wards = nc["wards"]
        if len(original_wards) != 23 or len(current_wards) != 23:
            raise ValueError(week + " ward count")
        for a, b in zip(original_wards, current_wards):
            if a["ward"] != b["ward"]:
                raise ValueError(week + " ward list reordered")
            if a["ward"] == "杉並区":
                for key in ("published_count", "candidate_count"):
                    if b.get(key) != a.get(key, 0) + 1:
                        raise ValueError(week + " 杉並区 " + key + " counter")
                assert_equal({k: v for k, v in a.items() if k not in ("published_count", "candidate_count", "note")},
                             {k: v for k, v in b.items() if k not in ("published_count", "candidate_count", "note")},
                             week + " 杉並区 historical source evidence")
                if not str(b.get("note", "")).startswith(str(a.get("note", ""))):
                    raise ValueError(week + " original 杉並区 note mutated")
            else:
                assert_equal(a, b, week + " unrelated ward " + a["ward"])

        eid, url = BASE_IDS[week]
        events = read(shard)
        if len(events) != 1 or events[0].get("id") != eid:
            raise ValueError(week + " must add exactly one named event")
        e = events[0]
        if not (e.get("url") == url and e.get("official_url") == url and e.get("source") == url
                and e.get("ward") == "杉並区"
                and e.get("date_start") == e.get("date_end") ==
                ("2026-11-01" if week == "2026-10-31" else "2026-12-06")
                and e.get("venue") and e.get("description")
                and e.get("family_fit", {}).get("rubric_version") == "family-fit-v2"
                and e.get("reservation", {}).get("required") in (True, False)):
            raise ValueError(week + " wrong or incomplete official event data")
        if eid.endswith("23878") and (
                e["reservation"]["required"] is not True or
                "11/5" not in e["reservation"]["note"] or
                "小学生" not in e["description"] or "8組" not in e["description"]):
            raise ValueError("lottery/event age/deadline requirements missing")

        old_rows = list(old.get("events") or [])
        for f in old.get("event_files", []):
            old_rows.extend(before(base_ref, f))
        if any(v["id"] == eid or v.get("official_url") == url for v in old_rows):
            raise ValueError(week + " already published: do not duplicate")
        old_events_by_week[week] = len(old_rows)
        if len(old_rows) != old["coverage"]["published_count"]:
            raise ValueError(week + " baseline event count inconsistent")

        for suffix, rows_key, counters in (
                ("-verification.json", "events", ("total", "verified")),
                ("-decisions.json", "decisions", ("candidate_total", "published"))):
            old_proof = before(base_ref, week + suffix)
            new_proof = read(week + suffix)
            if len(new_proof[rows_key]) != len(old_proof[rows_key]) + 1:
                raise ValueError(week + suffix + " count changed wrongly")
            assert_equal(old_proof[rows_key], new_proof[rows_key][:-1],
                         week + suffix + " historical rows")
            change_count(new_proof["summary"], old_proof["summary"], counters,
                         week + suffix + " summary")
            assert_equal({k: v for k, v in old_proof.items() if k not in (rows_key, "summary")},
                         {k: v for k, v in new_proof.items() if k not in (rows_key, "summary")},
                         week + suffix + " historical metadata")
            proof = new_proof[rows_key][-1]
            if proof.get("id", proof.get("candidate_id")) != eid:
                raise ValueError(week + suffix + " new evidence ID mismatch")
            if suffix.startswith("-verification"):
                if proof.get("status") != "verified" or proof.get("source") != url:
                    raise ValueError(week + " unverified official source")
            else:
                if (proof.get("decision") != "published"
                        or proof.get("family_fit") != e.get("family_fit")
                        or not any(p.get("url") == url for p in proof.get("evidence", []))):
                    raise ValueError(week + " decision lacks matching official proof")

        old_run = before(base_ref, week + "-run.json")
        new_run = read(week + "-run.json")
        extra_key = "suginami_official_phase1_addendum"
        assert_equal({k: v for k, v in old_run.items() if k not in ("summary", extra_key)},
                     {k: v for k, v in new_run.items() if k not in ("summary", extra_key)},
                     week + " historical run")
        changed_fields = tuple(k for k in ("candidates", "published", "verified")
                               if isinstance(old_run["summary"].get(k), int))
        change_count(new_run["summary"], old_run["summary"], changed_fields,
                     week + " run summary")
        extra = new_run.get(extra_key, {})
        if (extra.get("new_event_ids") != [eid] or extra.get("official_detail") != url
                or extra.get("base_data_production_sha") != base_ref
                or extra.get("source_failures_remain_unverified") is not True):
            raise ValueError(week + " incomplete immutable run addendum")

    history_old = before(base_ref, "update_history.json")
    history_new = read("update_history.json")
    assert_equal({k: v for k, v in history_old.items() if k != "history"},
                 {k: v for k, v in history_new.items() if k != "history"},
                 "history metadata")
    assert_equal(history_old["history"], history_new["history"][:-1],
                 "history append-only")
    record = history_new["history"][-1]
    if (record.get("run_type") != HISTORY_TYPE or
            record.get("base_data_production_sha") != base_ref or
            record.get("new_event_ids") != [BASE_IDS[w][0] for w in ("2026-10-31", "2026-12-05")] or
            record.get("added_weekly_records") != 2 or
            record.get("changed_existing_records") != 0 or
            record.get("removed_weekly_records") != 0 or
            record.get("source_failures_remain_unverified") is not True):
        raise ValueError("history proof mismatch")
    print("SUGINAMI_PHASE1_GATE PASS: 2 exact new official activities, "
          "0 existing rows removed/altered, 0 old audit changes")
    print("old published counts:", old_events_by_week)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref", required=True)
    args = parser.parse_args()
    try:
        verify(args.base_ref)
    except (ValueError, KeyError, IndexError, OSError, subprocess.CalledProcessError) as exc:
        print("BLOCKER SUGINAMI_PHASE1_GATE:", exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
