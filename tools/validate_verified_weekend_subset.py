#!/usr/bin/env python3
"""Strict additive, source-independent batch gate. Only one 2026-11-23 holiday.
Existing failed required source fetches remain recorded as debt; never mark checked.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

DAY = "2026-11-29"
WEEK = "2026-11-28"
SHARD = "2026-11-28-events-verified-subset-2026-11-29.json"
DIR = "site/data/"
OFFICIAL_WHITELIST = {
 "partial-20261129-nakano-precure-rally": ("https://www.city.tokyo-nakano.lg.jp/kanko/city-promotion/animemangafest2026.html",),
 "partial-20261129-edogawa-origami": ("https://www.city.edogawa.tokyo.jp/event/2611origami.html",),
 "partial-20261129-taito-bookstand": ("https://www.city.taito.lg.jp/library/kodomo/event/event11/ishi-workshop-kodomo.html",),
 "partial-20261129-setagaya-languages": ("https://celulas.or.jp/?p=8175",),
 "partial-20261129-setagaya-workfes": ("https://setagaya.event-hub.jp/",),
}

ALLOWED = {
    DIR + "manifest.json", DIR + WEEK + ".json",
    DIR + WEEK + "-verification.json", DIR + WEEK + "-decisions.json",
    DIR + WEEK + "-run.json", DIR + SHARD,
    DIR + "update_history.json",
}
FIELDS = ("name", "ward", "venue", "date_start", "date_end", "official_url",
          "source", "reservation", "family_fit")

def read_current(name):
    return json.loads((Path(DIR) / name).read_text(encoding="utf-8"))

def read_old(base, name):
    raw = subprocess.check_output(["git", "show", base + ":" + DIR + name], text=True)
    return json.loads(raw)

def bundle(read, week):
    data = read(week["file"])
    events = list(data.get("events") or [])
    for shard in data.get("event_files") or []:
        events.extend(read(shard))
    return data, events

def unchanged(old, new, description):
    if old != new:
        raise ValueError(description + " changed unexpectedly")

def verify(base):
    changed = set(subprocess.check_output(["git","diff","--name-only",base,"HEAD"],text=True).splitlines())
    if changed != ALLOWED:
        raise ValueError("unexpected paths or missing required data files: " + repr(sorted(changed ^ ALLOWED)))
    before, after = read_old(base, "manifest.json"), read_current("manifest.json")
    unchanged(before["default"], after["default"], "default weekend")
    unchanged(before["rolling_horizon_weeks"], after["rolling_horizon_weeks"], "6-week horizon")
    if len(before["weekends"]) != 6 or len(after["weekends"]) != 6:
        raise ValueError("unexpected weekend count")
    if after["generated"] <= before["generated"]:
        raise ValueError("manifest timestamp did not advance")
    old_holidays = before.get("holidays", [])
    if after.get("holidays") != old_holidays:
        raise ValueError("previous registered holidays changed")
    if after.get("holiday_source") != before.get("holiday_source"):
        raise ValueError("holiday source changed")
    added_ids = []
    for index,(old_entry,new_entry) in enumerate(zip(before["weekends"], after["weekends"])):
        old_w,old_events = bundle(lambda file:read_old(base,file),old_entry)
        new_w,new_events = bundle(read_current,new_entry)
        if index == 5:
            unchanged({k:v for k,v in old_entry.items() if k!="count"},
                      {k:v for k,v in new_entry.items() if k!="count"}, "November 21 weekend")
            if new_entry.get("count") != old_entry.get("count")+5:
                raise ValueError("wrong new week count")
            if new_w.get("event_files") != old_w.get("event_files")+[SHARD]:
                raise ValueError("new shard must be appended exactly")
            allowed_top = {"generated","coverage","event_files"}
            unchanged({k:v for k,v in old_w.items() if k not in allowed_top},
                      {k:v for k,v in new_w.items() if k not in allowed_top},
                      "existing week metadata")
            old_coverage,new_coverage=old_w["coverage"],new_w["coverage"]
            for k,v in old_coverage.items():
                if k in ("published_count","candidate_count","wards"):
                    continue
                unchanged(v,new_coverage.get(k),"unchanged coverage field "+k)
            for k in ("published_count","candidate_count"):
                if new_coverage.get(k) != old_coverage.get(k)+4:
                    raise ValueError("wrong coverage count "+k)
            for ward,addition in (("中野区",1),("江戸川区",1),("台東区",1),("世田谷区",2)):
                o=next(r for r in old_coverage["wards"] if r["ward"]==ward)
                n=next(r for r in new_coverage["wards"] if r["ward"]==ward)
                for k in o:
                    if k in ("candidate_count","published_count","note"):continue
                    unchanged(o[k],n.get(k),"source coverage mutated: "+ward)
                for k in ("candidate_count","published_count"):
                    if n.get(k)!=o[k]+addition:raise ValueError("ward count mismatch "+ward)
            for o,n in zip(old_coverage["wards"],new_coverage["wards"]):
                if o["ward"] not in ("中野区","江戸川区","台東区","世田谷区"):
                    unchanged(o,n,"unrelated ward coverage")
            if len(new_events)!=len(old_events)+5 or new_events[:len(old_events)]!=old_events:
                raise ValueError("prior event order or facts changed")
            extra=new_events[len(old_events):]
            if len({e.get("id") for e in extra})!=4 or any(e.get("id") in {x["id"] for x in old_events} for e in extra):
                raise ValueError("duplicate new event ID")
            for ev in extra:
                if not (ev.get("date_start","")<=DAY<=ev.get("date_end","")) or not all(ev.get(k) for k in FIELDS):
                    raise ValueError("missing holiday facts "+str(ev.get("id")))
                if ev.get("official_url") not in OFFICIAL_WHITELIST.get(ev.get("id"),()):
                    raise ValueError("unapproved official source or source-ID pairing "+str(ev["id"]))
                if ev.get("family_fit",{}).get("rubric_version")!="family-fit-v2":
                    raise ValueError("not family-fit-v2 "+str(ev["id"]))
                if ev.get("image") and not ev["image"].startswith("https://"):
                    raise ValueError("invalid image "+str(ev["id"]))
            added_ids=[ev["id"] for ev in extra]
            for suffix,key in (("-verification.json","events"),("-decisions.json","decisions")):
                old=read_old(base,WEEK+suffix);new=read_current(WEEK+suffix)
                if new[key][:len(old[key])]!=old[key] or len(new[key])!=len(old[key])+5:
                    raise ValueError("previous audit rows mutated "+suffix)
                changed_ids=[e.get("id") or e.get("candidate_id") for e in new[key][len(old[key]):]]
                if sorted(changed_ids)!=sorted(added_ids):
                    raise ValueError("missing new audit rows "+suffix)
                if suffix.startswith("-verification"):
                    for row in new[key][len(old[key]):]:
                        if row.get("status")!="verified" or row.get("source") not in [e["official_url"] for e in extra]:
                            raise ValueError("new evidence is not verified")
                    for field in ("total","verified"):
                        if new["summary"][field]!=old["summary"][field]+5: raise ValueError("bad verification "+field)
                else:
                    for field in ("candidate_total","published"):
                        if new["summary"][field]!=old["summary"][field]+5: raise ValueError("bad decisions "+field)
            old_run=read_old(base,WEEK+"-run.json");new_run=read_current(WEEK+"-run.json")
            for key,value in old_run.items():
                if key in ("summary","verified_subset_addendum"):continue
                unchanged(value,new_run.get(key),"original run "+key)
            for field in ("published","verified"):
                if new_run["summary"].get(field)!=old_run["summary"].get(field)+5:
                    raise ValueError("run summary not updated "+field)
            record=new_run.get("verified_subset_addendum",{})
            if record.get("new_event_ids")!=added_ids or record.get("base_data_production_sha")!=base:
                raise ValueError("addendum proof incomplete")
            if record.get("failed_required_source_urls")!=5 or record.get("source_failures_remain_unverified") is not True:
                raise ValueError("missing source-failure disclosure")
        else:
            unchanged(old_entry,new_entry,"unrelated weekend index")
            unchanged(old_w,new_w,"unrelated published week")
            unchanged(old_events,new_events,"unrelated published events")

    old_history=read_old(base,"update_history.json")
    new_history=read_current("update_history.json")
    if new_history.get("schema_version")!=old_history.get("schema_version") or new_history["history"][:-1]!=old_history["history"]:
        raise ValueError("published history not preserved")
    if len(new_history["history"])!=len(old_history["history"])+1: raise ValueError("history count")
    record=new_history["history"][-1]
    if any([record.get("run_type")!="manual_verified_weekend_subset_addition",
            record.get("status")!="official_verified_addition",
            record.get("target_weekend")!=WEEK,
            record.get("as_of_jst")!="2026-10-26",
            record.get("added_weekly_records")!=5,
            record.get("removed_weekly_records")!=0,
            record.get("changed_existing_records")!=0,
            record.get("base_data_production_sha")!=base,
            record.get("new_event_ids")!=added_ids]):
        raise ValueError("invalid history/addendum identity")

    # Existing source checks are not repaired by pretending they succeeded.
    # The old records were audited as a separate holiday-after run; new primary pages
    # have independent verification while the old baseline debt remains unchanged.
    spec=importlib.util.spec_from_file_location("source_audit",Path(__file__).with_name("validate_official_schedule_audit.py"))
    audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    policy=read_current("discovery_sources.json")
    old_errors=[];new_errors=[]
    for old_entry,new_entry in zip(before["weekends"],after["weekends"]):
        old_w=read_old(base,old_entry["file"]);new_w=read_current(new_entry["file"])
        old_run=read_old(base,old_w["run_file"]);new_run=read_current(new_w["run_file"])
        decision_file=old_run["source_data"]["decision_file"]
        old_dec=read_old(base,decision_file);new_dec=read_current(decision_file)
        old_errors+=audit.validate(old_run,old_w,old_dec,policy,())
        new_errors+=audit.validate(new_run,new_w,new_dec,policy,())
    if old_errors!=new_errors:
        raise ValueError("new or changed source audit failures: "+str(new_errors))
    # Restrict waiver to two specific historical source checks, not unknown failures.
    known={f"{w}: required source not checked: suginami_calendar_all, https://www.city.suginami.tokyo.jp/cgi-bin/event_cal_multi/calendar.cgi?type=2&year={{YYYY}}&month={{MM}}" for w in ("2026-11-21","2026-11-28")}
    # Historical Cloudflare 403 and its row-parity debt must remain errors.
    # Both occur twice in each old week (monthly calendar URLs); exact
    # old/new audit error sequence and source log objects are unchanged above.
    for week in ("2026-11-21","2026-11-28"):
        known.add(week+": required source failed: tamemap_nakano")
        known.add(week+": official event row parity mismatch: tamemap_nakano")
    if set(new_errors)-known:
        raise ValueError("unapproved historical source debt: "+repr(new_errors))
    print("SOURCE_DEBT_RETAINED_UNCHANGED",len(new_errors),*new_errors,sep="\n")
    print("VERIFIED_SUBSET_PASS",len(added_ids),"official events; all prior data and logs unchanged")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base-ref",required=True)
    args=p.parse_args()
    if len(args.base_ref)!=40 or any(c not in "0123456789abcdef" for c in args.base_ref):
        raise SystemExit("required immutable 40-character baseline SHA")
    try:verify(args.base_ref)
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        print("BLOCKER: VERIFIED_SUBSET_FAILED",exc,file=sys.stderr)
        return 1
    return 0

if __name__=="__main__":
    sys.exit(main())
