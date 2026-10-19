#!/usr/bin/env python3
"""Build a non-publishable six-week DATA candidate in a temporary directory.

Never alters data-production, data-staging, production, app Version or prior
event files. Strict gates run on the result; the candidate CANNOT be promoted
until factual verification and decision audits really pass.
"""
import argparse
import copy
from collections import Counter
from datetime import datetime, timedelta, date
import json
from pathlib import Path
import shutil

KEEP_IF_OFFICIAL_RECENTLY_RECHECKED = {
    "色の引き算―白・黒・いろいろ―",
    "企画展「Made in としまの紙芝居～日本画劇が残したもの～」",
    "ユアサエボシと戦後アヴァンギャルドの変身寓話集",
    "没後70年 茂田井武とパリの画家たち　―Parisの破片(カケラ)― ＜同時開催＞ ちひろ 旅のたのしみ",
    "HIBIYA Magic Time Illumination 2026",
    "Hibiya Art Park 2026 - Timeless Phenomena 確かにありそうなもの -",
}
WARDS = ["千代田区","中央区","港区","新宿区","文京区","台東区","墨田区","江東区",
    "品川区","目黒区","大田区","世田谷区","渋谷区","中野区","杉並区",
    "豊島区","北区","荒川区","板橋区","練馬区","足立区","葛飾区","江戸川区"]
SOURCE_ISSUE="tamemap_nakano"

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))
def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n",encoding="utf-8")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--baseline",required=True,type=Path)
    p.add_argument("--evidence",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    manifest0=load(a.baseline/"manifest.json")
    manifest=copy.deepcopy(manifest0)
    a.output.mkdir(parents=True,exist_ok=True)
    shutil.copytree(a.baseline,a.output,dirs_exist_ok=True)
    summary=load(a.evidence/"summary.json")
    requests=load(a.evidence/"requests.json")
    plan=load(a.evidence/"plan.json")
    official=summary["annual_schedule"][0]
    if (plan["as_of_jst"]!="2026-10-19" or summary["base_data_production_sha"]!=
        "b1282eb0f24ec6436b1ef8cf52d3df597b262c0b"):
        raise ValueError("baseline plan discrepancy")
    if (summary.get("required_source_failures_outstanding") or
         summary.get("supplemental_failures") or len(summary.get("wards",{}))!=23 or
         len(summary.get("approved_deferred_source_errors",[]))!=2):
        raise ValueError("insufficient real source checks")
    old={row["sat"]:row for row in manifest0["weekends"]}
    existing={}
    previous_verification={}
    for prev in manifest0["weekends"]:
        week=load(a.baseline/prev["file"])
        content=list(week.get("events") or [])
        for file in week.get("event_files") or []:
            content+=load(a.baseline/file)
        audit=load(a.baseline/week["verification_file"])
        amap={x["id"]:x for x in audit.get("events",[])}
        for ev in content:
            sig=(ev.get("name"),ev.get("date_start"),ev.get("date_end"),ev.get("venue"))
            if sig not in existing or (amap.get(ev.get("id"),{}).get("status")=="verified"):
                existing[sig]=ev
                if ev.get("id") in amap:
                    previous_verification[sig]=amap[ev["id"]]
    generated=datetime.now().astimezone().isoformat(timespec="seconds")
    manifest["generated"]=generated
    manifest["default"]=plan["weekends"][0]["sat"]
    manifest["weekends"]=[]
    report={"kind":"holiday_after_staging_dryrun","run_as_of":"2026-10-19",
            "production_data_unmodified":True,"strict_pass":False,
            "candidate_is_not_publishable":True,"weeks":[],"blockers":[]}

    for i,pw in enumerate(plan["weekends"]):
        sat,sun=pw["sat"],pw["sun"]
        tier=("full" if i<2 else "preview" if i<4 else "announcement")
        weekfile=sat+".json"
        if sat in old:
            entry=copy.deepcopy(old[sat])
            week=load(a.baseline/weekfile)
            week["horizon_index"]=i+1;week["publication_tier"]=tier
            entry["horizon_index"]=i+1;entry["publication_tier"]=tier
            dump(a.output/weekfile,week)
            run=load(a.baseline/week["run_file"])
            run["horizon_index"]=i+1;run["publication_tier"]=tier
            # Preserve v1.5 historical proof rather than falsify a v1.15 re-audit.
            dump(a.output/week["run_file"],run)
            ver=load(a.baseline/week["verification_file"])
            announced=[r["id"] for r in ver.get("events",[]) if r.get("status")!="verified"]
            if announced and tier=="full":
                report["blockers"].append({"sat":sat,"kind":"full_tier_needs_individual_official_recheck",
                                           "event_ids":announced})
        else:
            events=[]
            audits=[]
            dedup=set()
            for sig, ev in existing.items():
                if ev.get("name") not in KEEP_IF_OFFICIAL_RECENTLY_RECHECKED:
                    continue
                if not (ev.get("date_start","")<=sun and ev.get("date_end","")>=sat):
                    continue
                row=previous_verification.get(sig)
                if not row or row.get("status")!="verified":
                    continue
                k=(ev.get("name"),ev.get("venue"),ev.get("date_start"))
                if k in dedup: continue
                dedup.add(k)
                events.append(copy.deepcopy(ev))
                audits.append(copy.deepcopy(row))
            events.sort(key=lambda x:(x.get("ward",""),x.get("name","")))
            rows=Counter(e["ward"] for e in events)
            coverage={"sources_checked":0,"candidate_count":len(events),
              "duplicate_removed":0,"excluded_count":0,"published_count":len(events),
              "wards":[{"ward":ward,"status":"pending","queries":0,"sources_checked":0,
                        "candidate_count":rows[ward],"published_count":rows[ward],
                        "note":"Measured source evidence exists but not yet reconciled to decision audit."}
                       for ward in WARDS]}
            week={"sample":False,"sat":sat,"sun":sun,"label":f"{int(sat[5:7])}/{int(sat[8:])}(土)〜{int(sun[5:7])}/{int(sun[8:])}(日)",
                  "generated":generated,"horizon_index":i+1,"publication_tier":tier,
                  "verification_file":sat+"-verification.json",
                  "run_file":sat+"-run.json","coverage":coverage,
                  "event_files":[sat+"-events-01.json"],"events":[]}
            dump(a.output/weekfile,week)
            dump(a.output/(sat+"-events-01.json"),events)
            dump(a.output/(sat+"-verification.json"),{
                "schema_version":1,"verified_on":"2026-10-07",
                "events":audits,"summary":{"total":len(events),"verified":len(audits),"announced":0}})
            # Explicitly reject publication: no review decisions or source logs
            # have been invented for these fresh weekend participation units.
            dump(a.output/(sat+"-run.json"),{
                "schema_version":1,"target":{"sat":sat,"sun":sun},
                "publication_tier":tier,"horizon_index":i+1,
                "mode":"temporary-read-only-unverified-candidate",
                "prompt":{"version":"v1.15",
                          "path":"prompts/tokyo_family_events_complete_prompt_v1.15.txt",
                          "pointer":"site/data/latest_prompt.json","resolved":True},
                "holiday_after":{"run_type":"holiday_after_update","as_of_jst":"2026-10-19"},
                "source_data":{"week_file":weekfile,"verification_file":sat+"-verification.json",
                               "decision_file":sat+"-decisions.json"},
                "discovery_evidence":{"wards":[]},"official_schedule_checks":[],
                "explicit_source_checks":[],"stages":[],"summary":{"published":len(events),"announced":0}})
            dump(a.output/(sat+"-decisions.json"),{
                "schema_version":1,"rubric_version":"family-fit-v2",
                "generated":generated,"migration_incomplete":False,
                "summary":{"candidate_total":len(events),"published":0,
                           "excluded":0,"duplicate":0},
                "decisions":[]})
            entry={"sat":sat,"sun":sun,"label":week["label"],"file":weekfile,
                   "count":len(events),"horizon_index":i+1,"publication_tier":tier}
            report["blockers"].append({"sat":sat,"kind":"official_fact_review_and_v2_decisions_missing",
                "initial_rechecked_historical_event_candidates":len(events),
                "note":"Do not promote or publish this subset as full coverage."})
        manifest["weekends"].append(entry)
        report["weeks"].append({"sat":sat,"tier":tier,"count":entry["count"]})
    dump(a.output/"manifest.json",manifest)
    # History is deliberately not forged because publication verification is incomplete.
    report["blockers"].append({"kind":"history_append_requires_strict_complete_candidate"})
    dump(a.output.parent/"candidate_dryrun_status.json",report)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
