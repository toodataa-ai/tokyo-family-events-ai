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
    candidates=load(a.evidence/"candidate_pool.json")
    plan=load(a.evidence/"plan.json")
    def ward_evidence(sat):
        entries=[]
        for name in WARDS:
            q=[x for x in requests if x.get("ward")==name and
               ((x.get("kind")=="ai_cross" and x.get("week")==sat)
                or (x.get("kind")=="holiday_ai_cross" and
                    x.get("holiday")=="2026-11-23" and sat=="2026-11-21"))]
            sources=[x for x in requests if x.get("kind")=="ward_official" and x.get("ward")==name]
            entries.append({"ward":name,
               "query_logs":[{"query":x["query"],"url":x["url"],"checked_at":x["checked_at"],
                              "status":x["status"],"sha256":x.get("sha256"),
                              "result_count":x.get("search_results_event_leads",0)} for x in q],
               "source_checks":[{"url":x["url"],"checked_at":x["checked_at"],
                                 "status":x["status"],"sha256":x.get("sha256")} for x in sources]})
        return entries
    def explicit_source_records():
        out=[]
        for x in requests:
            if x.get("kind")!="explicit":continue
            ids=[]
            for row in candidates:
                via=row.get("discovered_via") or {}
                if via.get("source_id")==x.get("source_id") and via.get("search_url")==x.get("url"):
                    ids.append(row["candidate_id"])
            if x["source_id"]=="nerima_district_festivals_2026":
                ids=official["candidate_ids"]
            ids=list(dict.fromkeys(ids))
            result={"source_id":x["source_id"],"search_url":x["url"],
              "status":x["status"],"checked_at":x["checked_at"],
              "http_status":x.get("http_status"),
              "response_server":x.get("response_server"),
              "challenge_detected":x.get("challenge_detected"),
              "error":x.get("error"),"candidate_ids":ids,
              "candidate_count":len(ids)}
            if x["source_id"]=="nerima_district_festivals_2026":
                result.update(official_row_count=len(ids),
                              unmatched_official_rows=True,
                              resolved_pages=official.get("resolved_pages"))
            if x["source_id"]=="tamemap_nakano":
                result["exception_ref"]="tamemap-nakano-cloudflare403-20261019"
            out.append(result)
        return out
    explicit_records=explicit_source_records()
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
            ward_logs=ward_evidence(sat)
            coverage={"sources_checked":sum(
                sum(r.get("status")=="checked" for r in item["source_checks"])
                for item in ward_logs),
              "candidate_count":len(events),
              "duplicate_removed":0,"excluded_count":0,"published_count":len(events),
              "wards":[{"ward":item["ward"],
                        "status":"checked" if item["query_logs"] and
                              item["source_checks"] and
                              all(q["status"]=="checked" for q in item["query_logs"]+item["source_checks"])
                              else "error",
                        "queries":len(item["query_logs"]),
                        "sources_checked":sum(q["status"]=="checked" for q in item["source_checks"]),
                        "candidate_count":rows[item["ward"]],
                        "published_count":rows[item["ward"]],
                        "note":"Exact measured October19 holiday-after HTTP queries and official ward source logs."}
                       for item in ward_logs]}
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
                "discovery_evidence":{"wards":ward_logs},
                "official_schedule_checks":[{
                    "source_id":"nerima_district_festivals_2026",
                    "url":official["resolved_pages"][0]["resolved_url"],
                    "checked_at":official["resolved_pages"][0]["checked_at"],
                    "status":official["status"],
                    "official_row_count":official["official_row_count"],
                    "candidate_ids":official["candidate_ids"],
                    "matched_candidate_count":0,
                    "unmatched_official_rows":True,
                    "resolved_pages":official["resolved_pages"]}],
                "explicit_source_checks":explicit_records,
                "stages":[],"summary":{"published":len(events),"announced":0}})
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
                "measured_ward_query_count":sum(len(item["query_logs"]) for item in ward_logs),
                "measured_ward_source_count":sum(len(item["source_checks"]) for item in ward_logs),
                "source_checks_from_actual_http":len(explicit_records),
                "note":"Actual HTTP evidence is now connected; source-row and family-fit v2 decisions remain pending."})
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
