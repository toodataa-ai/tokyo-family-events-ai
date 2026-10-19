#!/usr/bin/env python3
"""Restore proven already-published event IDs into each applicable future week.

Inputs: immutable data-production and already approved data-staging candidates.
Outputs: existing data-staging checkout files only, with additive shards/audits.
No inference from mere 'long-running' span: this tool has an explicit organizer
source + previously verified event-ID allowlist approved for carryover review.
"""
import argparse
import copy
from datetime import date,timedelta
import json
from pathlib import Path
import re

IDS={
    "v15-51c3d03b1d28": {
        "name":"Kids meet × Studio oowa「こうえん」～あの子のスペースをつくる～",
        "source":"https://www.inclusion-art.jp/archive/interactive/2026/20261010-390.html",
        "confirmed_until":"2026-11-08",
        "reason":"主催者公式で10月10日～11月8日、交流スペースのプログラム期間を確認。元の公開ID・審査結果を継承。",
    },
    "legacy-gap-2026-10-10-zannen3": {
        "name":"サンシャイン水族館 特別展「ざんねんないきもの展３」",
        "source":"https://sunshinecity.jp/aquarium/event_performance/event/entry-36530.html",
        "confirmed_until":"2026-11-23",
        "reason":"サンシャイン水族館公式で3月13日～11月23日、展示開催期間を確認。休業日・営業時間は公式案内を参照。",
    }
}
def load(path):return json.loads(path.read_text(encoding="utf-8"))
def save(path,val):path.write_text(json.dumps(val,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def main():
    a=argparse.ArgumentParser();a.add_argument("--previous",type=Path,required=True)
    a.add_argument("--staging",type=Path,required=True)
    a.add_argument("--report",type=Path,required=True);args=a.parse_args()
    old=args.previous; root=args.staging
    m=load(root/"manifest.json")
    before=load(old/"2026-10-10.json")
    events=[]
    for sh in before["event_files"]:events+=load(old/sh)
    baseline={ev["id"]:ev for ev in events}
    original_ver={v["id"]:v for v in load(old/"2026-10-10-verification.json")["events"]}
    evidence={x["candidate_id"]:x for x in load(old/"2026-10-10-decisions.json")["decisions"]}
    original_decision_by_name={x["name"]:x for x in evidence.values() if x.get("decision")=="published"}
    for key,record in IDS.items():
        ev=baseline.get(key)
        if not ev or ev["name"]!=record["name"] or ev["official_url"]!=record["source"]:
            raise ValueError("Old immutable event does not match verified organizer source "+key)
        if ev["date_end"]!=record["confirmed_until"] or original_ver[key]["status"]!="verified":
            raise ValueError("Official duration or old verified source changed "+key)
        if not original_decision_by_name.get(ev["name"]):
            raise ValueError("No original published review decision "+key)
    report={"kind":"protected_identical_published_id_carryover","previous_files_unchanged":True,
            "scoped_ids":list(IDS),"weeks":[],"other_discovered_candidates_untouched":True}
    for i,entry in enumerate(m["weekends"]):
        sat,sun=entry["sat"],entry["sun"]
        changed=[]
        data=load(root/entry["file"])
        evs=list(data.get("events",[]))
        for sh in data.get("event_files",[]):evs+=load(root/sh)
        existing={e["id"] for e in evs}
        additions=[]
        v=load(root/data["verification_file"])
        r=load(root/data["run_file"])
        dec_path=root/f"{sat}-decisions.json"
        d=load(dec_path)
        for eid,rule in IDS.items():
            event=baseline[eid]
            if not (event["date_start"]<=sun and event["date_end"]>=sat):
                continue
            if eid in existing:
                continue
            new=copy.deepcopy(event)
            additions.append(new)
            vrow=copy.deepcopy(original_ver[eid])
            vrow["note"]=(vrow.get("note") or "")+"（2026-10-20ローリング引継再確認）"+rule["reason"]
            vrow["source"]=rule["source"]
            v["events"].append(vrow)
            original=copy.deepcopy(original_decision_by_name[new["name"]])
            original["candidate_id"]="carryover-"+eid+"-"+sat
            original["family_fit"]["rubric_version"]=d["rubric_version"]
            original["reasons"]=[rule["reason"]]
            original["evidence"]=[{"url":rule["source"],"basis":rule["reason"]}]
            original["review_note"]="過去の公開済み公式確認を維持し、10/20時点の主催者開催期間を再確認。"
            # Never discard the eight existing axes or their reasons.
            original.setdefault("primary_reason_code","family_value_high")
            original.setdefault("reason_codes",["family_value_high"])
            original.setdefault("positive_signals",["official_venue_published"])
            original.setdefault("negative_signals",[])
            original.setdefault("hard_exclusion",None)
            original.setdefault("exclusion_type",None)
            original.setdefault("override_reason","")
            original["decision"]="published"
            d["decisions"].append(original)
            changed.append(eid)
            existing.add(eid)
        if additions:
            extra=f"{sat}-events-carryover.json"
            if (root/extra).exists() or extra in data["event_files"]:raise ValueError("Carryover shard exists: "+extra)
            save(root/extra,additions)
            data["event_files"].append(extra)
            data["coverage"]["published_count"]+=len(additions)
            data["coverage"]["candidate_count"]+=len(additions)
            for ev in additions:
                wrow=next(x for x in data["coverage"]["wards"] if x["ward"]==ev["ward"])
                wrow["candidate_count"]+=1
                wrow["published_count"]+=1
            entry["count"]+=len(additions)
            v["summary"]["total"]=len(v["events"])
            v["summary"]["verified"]=sum(x["status"]=="verified" for x in v["events"])
            v["summary"]["announced"]=sum(x["status"]=="announced" for x in v["events"])
            v["verified_on"]="2026-10-20"
            r.setdefault("summary",{})["published"]=data["coverage"]["published_count"]
            r["summary"]["verified"]=v["summary"]["verified"]
            r["summary"]["announced"]=v["summary"]["announced"]
            r.setdefault("carryover_organizer_rechecks",[]).append({"date":"2026-10-20",
                   "published_old_ids":changed,"official_sources":[IDS[x]["source"] for x in changed]})
            d["summary"]["published"]+=len(additions)
            d["summary"]["candidate_total"]+=len(additions)
            save(root/entry["file"],data)
            save(root/data["verification_file"],v)
            save(root/data["run_file"],r)
            save(dec_path,d)
        report["weeks"].append({"sat":sat,"carried_over_published_old_event_ids":changed})
    expected={
       "2026-10-24":list(IDS),
       "2026-10-31":list(IDS),
       "2026-11-07":list(IDS),
       "2026-11-14":["legacy-gap-2026-10-10-zannen3"],
       "2026-11-21":["legacy-gap-2026-10-10-zannen3"],
       "2026-11-28":[]
    }
    for w in report["weeks"]:
        if w["carried_over_published_old_event_ids"]!=expected[w["sat"]]:
            raise ValueError("Mismatch in explicit organizer dates or unexpected previous participation:"+str(w))
    save(root/"manifest.json",m)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    save(args.report,report)
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":main()
