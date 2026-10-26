#!/usr/bin/env python3
"""Fail-closed 3-week official Nerima forest festival additive publication gate.

Keeps pre-existing source failures as failures. Requires exactly the three
specified dates and original event IDs, with no alteration of old source logs.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path("site/data")
SOURCE = "https://www.city.nerima.tokyo.jp/kurashi/shigoto/midori/shokai/nerimanomori.html"
BASE_WEEKS = {
    "2026-11-07": ("2026-11-08", "nerima-forest-20261108-nakanomiya",
                   "中ノ宮竹林こどもまつり", "中ノ宮竹林公園"),
    "2026-11-21": ("2026-11-21", "nerima-forest-20261121-minamitakamatsu",
                   "落ち葉と森の素材あそび", "南高松の森緑地"),
    "2026-11-28": ("2026-11-29", "nerima-forest-20261129-kitappara",
                   "モルックであそぼう", "きたっぱら憩いの森"),
}
EXPECTED_IDS = {v[1] for v in BASE_WEEKS.values()}
FIXED_EXISTING_IDS = {
    "official-20261103-nerima-mori-fair",
    "official-20261103-nerima-mori-leaves",
    "v15-20261205-nerima-mori-leaf",
    "v15-20261205-nerima-mori-otaka",
    "v15-20261205-nerima-mori-takamatsu",
}
PATHS = {"site/data/manifest.json", "site/data/update_history.json"}
for week in BASE_WEEKS:
    PATHS.update("site/data/" + name for name in (
        week + ".json", week + "-verification.json",
        week + "-decisions.json", week + "-run.json",
        week + "-events-nerima-forest-20261027.json"))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def old(base, name):
    return json.loads(subprocess.check_output(
        ["git", "show", base + ":site/data/" + name], text=True))


def cur(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def only_allowed_changes(before, after, keys, description):
    require({k: v for k, v in before.items() if k not in keys} ==
            {k: v for k, v in after.items() if k not in keys},
            description + " contains unapproved field change")


def check(base):
    require(re.fullmatch(r"[a-f0-9]{40}", base), "real base SHA required")
    changed = set(subprocess.check_output(
        ["git", "diff", "--name-only", base, "HEAD"], text=True).splitlines())
    require(changed == PATHS, "changed path allowlist mismatch: " +
            repr(sorted(changed ^ PATHS)))

    original_manifest, manifest = old(base, "manifest.json"), cur("manifest.json")
    only_allowed_changes(original_manifest, manifest, {"generated", "weekends"}, "manifest")
    require(len(manifest["weekends"]) == len(original_manifest["weekends"]) == 6,
            "six-week horizon must be preserved")
    for before, after in zip(original_manifest["weekends"], manifest["weekends"]):
        delta = 1 if before["sat"] in BASE_WEEKS else 0
        only_allowed_changes(before, after, {"count"}, "manifest week " + before["sat"])
        require(after["count"] == before["count"] + delta, "wrong manifest count")

    added = []
    for week, (date, eid, title, venue) in BASE_WEEKS.items():
        w0, w1 = old(base, week + ".json"), cur(week + ".json")
        shard = week + "-events-nerima-forest-20261027.json"
        only_allowed_changes(w0, w1, {"event_files", "coverage", "generated"}, "week " + week)
        require(w1["event_files"] == w0["event_files"] + [shard],
                "existing event shard order changed " + week)
        require(w1.get("events", []) == w0.get("events", []), "inline event changed")
        for key in ("candidate_count", "published_count"):
            require(w1["coverage"][key] == w0["coverage"][key] + 1, "coverage " + key)
        only_allowed_changes(w0["coverage"], w1["coverage"],
                             {"candidate_count", "published_count", "wards"}, "coverage")
        for before, after in zip(w0["coverage"]["wards"], w1["coverage"]["wards"]):
            require(before["ward"] == after["ward"], "ward row order altered")
            is_nerima = before["ward"] == "練馬区"
            only_allowed_changes(before, after,
                                 {"candidate_count", "published_count", "note"} if is_nerima else set(),
                                 "ward counts/logs")
            if is_nerima:
                for key in ("candidate_count", "published_count"):
                    require(after[key] == before[key] + 1, "Nerima count " + key)
                require(after["note"].startswith(before["note"]), "historical source note rewritten")

        rows = cur(shard)
        require(isinstance(rows, list) and len(rows) == 1, "one physical event per week")
        ev = rows[0]
        require((ev.get("id"), ev.get("date_start"), ev.get("date_end")) ==
                (eid, date, date), "new event date/id mismatch")
        require(title in ev.get("name", "") and venue in ev.get("venue", ""),
                "official event content/venue mismatch")
        require(ev.get("official_url") == ev.get("url") == ev.get("source") == SOURCE,
                "official provenance mismatch")
        require(ev.get("image", "") == "", "unverified thumbnail forbidden")
        require(ev.get("reservation", {}).get("required") is False,
                "official reservation status mismatch")
        require("無料" in ev.get("price", "") and ev.get("time") and
                ev.get("indoor_outdoor") == "屋外", "missing official participation details")

        v0, v1 = old(base, week + "-verification.json"), cur(week + "-verification.json")
        only_allowed_changes(v0, v1, {"events", "summary"}, "verification")
        require(v1["events"][:-1] == v0["events"], "old verification altered")
        require(v1["events"][-1].get("id") == eid and
                v1["events"][-1].get("status") == "verified" and
                v1["events"][-1].get("source") == SOURCE,
                "new verification lacks official evidence")
        only_allowed_changes(v0["summary"], v1["summary"], {"total", "verified"},
                             "verification summary")
        require(all(v1["summary"][k] == v0["summary"][k] + 1
                    for k in ("total", "verified")), "verification counts")

        d0, d1 = old(base, week + "-decisions.json"), cur(week + "-decisions.json")
        only_allowed_changes(d0, d1, {"decisions", "summary"}, "decision audit")
        require(d1["decisions"][:-1] == d0["decisions"], "old decision audit altered")
        decision = d1["decisions"][-1]
        require(decision.get("candidate_id") == eid and
                decision.get("decision") == "published" and
                decision.get("family_fit", {}).get("rubric_version") == d0["rubric_version"] and
                any(r.get("url") == SOURCE for r in decision.get("evidence", [])),
                "new decision missing verified provenance")
        only_allowed_changes(d0["summary"], d1["summary"],
                             {"candidate_total", "published"}, "decision summary")
        require(d1["summary"]["candidate_total"] == d0["summary"]["candidate_total"] + 1 and
                d1["summary"]["published"] == d0["summary"]["published"] + 1,
                "decision counts")

        r0, r1 = old(base, week + "-run.json"), cur(week + "-run.json")
        only_allowed_changes(r0, r1, {"summary", "forest_schedule_addendum"}, "run evidence")
        only_allowed_changes(r0["summary"], r1["summary"],
                             {"published", "verified", "candidates"}, "run summary")
        require(r1["summary"]["published"] == r0["summary"]["published"] + 1 and
                r1["summary"]["verified"] == r0["summary"]["verified"] + 1,
                "run published/verified counts")
        delta_candidates = 1 if week == "2026-11-28" else 0
        if "candidates" in r0["summary"]:
            require(r1["summary"]["candidates"] ==
                    r0["summary"]["candidates"] + delta_candidates,
                    "run candidate count")
        addendum = r1.get("forest_schedule_addendum", {})
        require(addendum.get("added_event_ids") == [eid] and
                addendum.get("base_data_production_sha") == base and
                addendum.get("source_failures_remain_unverified") is True,
                "missing scoped evidence or failed-source disclosure")
        added.append(eid)

    h0, h1 = old(base, "update_history.json"), cur("update_history.json")
    require(h0.get("schema_version") == h1.get("schema_version") and
            h1["history"][:-1] == h0["history"], "historical update log changed")
    h = h1["history"][-1]
    require(h.get("run_type") == "manual_verified_forest_schedule_addition" and
            h.get("base_data_production_sha") == base and
            h.get("source_url") == SOURCE and
            h.get("new_event_ids") == added and
            h.get("added_weekly_records") == 3 and
            h.get("old_event_ids_removed") == 0 and
            h.get("old_event_records_changed") == 0 and
            h.get("source_failures_remain_unverified") is True,
            "incomplete append-only release provenance")

    # Entire festival schedule in active horizon: existing 11/3 and 12/5
    # must coexist with all 3 newly restored individual dates.
    festival_rows = []
    for week in manifest["weekends"]:
        doc = cur(week["file"])
        for shard in doc.get("event_files", []):
            festival_rows.extend(x for x in cur(shard)
                               if x.get("official_url") == SOURCE)
    by_id = {r["id"]: r for r in festival_rows}
    require(len(by_id) == len(festival_rows), "duplicate official festival ID")
    require(EXPECTED_IDS | FIXED_EXISTING_IDS <= set(by_id),
            "existing or restored official programme missing")

    # Retain exactly the historical required-source audit debt (never turn
    # Cloudflare failures into checked or waive newly introduced source errors).
    spec = importlib.util.spec_from_file_location(
        "source_audit", Path(__file__).with_name("validate_official_schedule_audit.py"))
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    source_config = cur("discovery_sources.json")
    previous_errors, current_errors = [], []
    for entry in original_manifest["weekends"]:
        w0, w1 = old(base, entry["file"]), cur(entry["file"])
        r0, r1 = old(base, w0["run_file"]), cur(w1["run_file"])
        dfile = r0["source_data"]["decision_file"]
        previous_errors.extend(audit.validate(r0, w0, old(base, dfile), source_config, ()))
        current_errors.extend(audit.validate(r1, w1, cur(dfile), source_config, ()))
    require(previous_errors == current_errors, "required-source audit debt changed")
    print("NERIMA_FOREST_ADDITIVE_PASS", len(added),
          "records; old IDs and source failures unchanged; source debt", len(current_errors))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", required=True)
    args = parser.parse_args()
    try:
        check(args.base_ref)
        return 0
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        print("BLOCKER NERIMA_FOREST_ADDITIVE:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
