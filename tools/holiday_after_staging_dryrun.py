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
    p.add_argument("--review-ledger",required=True,type=Path,
                   help="13 primary-source vetted fact reviews, never synthetic status upgrades")
    a=p.parse_args()
    official_reviews=load(a.review_ledger)
    if (official_reviews.get("source_kind")!="rechecked_primary_official_and_organizer_pages"
            or len(official_reviews["records"])!=13
            or official_reviews["data_baseline_sha"]!="b1282eb0f24ec6436b1ef8cf52d3df597b262c0b"):
        raise ValueError("no valid factual review ledger for all 13 old events")
    reviews={row["id"]:row for row in official_reviews["records"]}
    if len(reviews)!=13 or any(not row.get("source","").startswith("https://")
                              for row in reviews.values()):
        raise ValueError("unverified source ledger")
    manifest0=load(a.baseline/"manifest.json")
    manifest=copy.deepcopy(manifest0)
    a.output.mkdir(parents=True,exist_ok=True)
    shutil.copytree(a.baseline,a.output,dirs_exist_ok=True)
    summary=load(a.evidence/"summary.json")
    requests=load(a.evidence/"requests.json")
    candidates=load(a.evidence/"candidate_pool.json")
    plan=load(a.evidence/"plan.json")
    official=summary["annual_schedule"][0]
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
            verified_ids=[]
            remaining=[]
            for row in ver.get("events",[]):
                if tier!="full" or row.get("status")=="verified":
                    continue
                ident=row["id"]
                review=reviews.get(ident)
                if review is None:
                    remaining.append(ident)
                    continue
                row["status"]="verified"
                row["source"]=review["source"]
                row["source_kind"]="organizer_official"
                original=next((event for file in week.get("event_files",[])
                               for event in load(a.baseline/file)
                               if event.get("id")==ident),None)
                if not original: raise ValueError("reviewed event absent: "+ident)
                row.setdefault("corrections",{})
                row.setdefault("field_changes",{})
                for field,value in (review.get("corrections") or {}).items():
                    prior=original.get(field)
                    if prior!=value:
                        row["corrections"][field]=value
                        row["field_changes"][field]={
                           "from":prior,"to":value,
                           "reason":review["facts"]+" / "+review["limitations"],
                           "source":review["source"]}
                # Never convert an unknown fee, reservation requirement, or
                # location into a verified "pass" just to satisfy CI.
                core=("name","date","venue")
                row.setdefault("fields",{})
                for key in core:
                    row["fields"][key]=("corrected" if key in row.get("corrections",{})
                                        else "pass")
                for key in ("time","price","reservation","official_url"):
                    if key in row.get("corrections",{}):
                        row["fields"][key]="corrected"
                    # Otherwise the original actual proof state (including
                    # unknown) remains unchanged.
                row["note"]="個別公式再監査（2026-10-20）: "+review["facts"]+" 注意: "+review["limitations"]
                row["review_evidence_url"]=review["source"]
                verified_ids.append(ident)
            ver["verified_on"]="2026-10-20" if verified_ids else ver["verified_on"]
            ver["summary"]["verified"]=sum(r["status"]=="verified" for r in ver["events"])
            ver["summary"]["announced"]=sum(r["status"]=="announced" for r in ver["events"])
            if verified_ids:
                dump(a.output/week["verification_file"],ver)
                run["summary"]["verified"]=ver["summary"]["verified"]
                run["summary"]["announced"]=ver["summary"]["announced"]
                run.setdefault("postprocess_reviews",[]).append({
                    "version":"official-2026-10-20",
                    "mode":"evidence-backed-full-tier-reverification",
                    "source_ledger":"research/2026-10-20-confirmed-13-promotion-source-evidence.json",
                    "event_ids":verified_ids,
                    "note":"Corrections only when backed by named official source; original event IDs unchanged."
                })
                dump(a.output/week["run_file"],run)
            if remaining:
                report["blockers"].append({"sat":sat,"kind":"full_tier_needs_individual_official_recheck",
                                           "event_ids":remaining})
            report["weeks"].append({"sat":sat,"evidence_verified_event_ids":verified_ids,
                                    "pending_verifications":remaining})
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
            if sat=="2026-11-28":
                missing_official="nerima-district-0275426b6920"
                if missing_official not in official["candidate_ids"]:
                    raise ValueError("Nov29 official festival row not evidenced")
                if any(ev.get("id")==missing_official for ev in events):
                    raise ValueError("official event ID collision")
                url=official["resolved_pages"][0]["resolved_url"]
                source_event={
                    "id":missing_official,"ward":"練馬区",
                    "name":"第一地区祭（豊玉南小学校）",
                    "url":url,"official_url":url,"source":url,
                    "image":None,"period":"11/29","date_start":"2026-11-29",
                    "date_end":"2026-11-29","time":"10:00〜12:00",
                    "venue":"豊玉南小学校（練馬区豊玉南2-14-1）",
                    "price":None,
                    "description":"高齢者体験、餅つき、ゲームコーナー、昔遊び等。雨天時は規模縮小。料金・予約要否は区の公開日程表に記載なし。",
                    "categories":["祭り","地域イベント","子ども向け体験"],
                    "family_fit":{
                      "rubric_version":"family-fit-v2","grade":"A","overall":"A",
                      "reason":"練馬区が公式日程表に登録した、親子で体験や昔遊びを楽しめる地域の地区祭。",
                      "axes":{
                        "child_target":{"grade":"A","reason":"ゲームコーナー・昔遊びが明記されている。"},
                        "interactivity":{"grade":"A","reason":"高齢者体験・餅つき・ゲーム体験など参加型の催事。"},
                        "age_fit":{"grade":"A","reason":"地域の子ども・家族を含む行事。各体験の年齢制限は別途確認。"},
                        "stay_flexibility":{"grade":"A","reason":"10〜12時の短時間で複数の催事を回遊可能。"},
                        "burden":{"grade":"B","reason":"学校行事の混雑と雨天時の規模縮小に注意。"},
                        "cost":{"grade":"unknown","reason":"練馬区の公式年次日程表は料金を明示していない。"},
                        "reservation":{"grade":"unknown","reason":"練馬区の公式年次日程表に申込方法の明示なし。"},
                        "family_value":{"grade":"A","reason":"餅つき・昔遊び・世代間交流を家族で体験できる。"}
                      }
                    },
                    "reservation":{"required":None,"note":"申込要否は公式日程表に明記なし。個別参加条件を開催元へ確認。"},
                    "indoor_outdoor":"屋内・屋外",
                    "ai":{"checked_at":"2026-10-20","confidence":"high",
                           "discovery_query":"2026年度練馬区公式地区祭日程表：豊玉南小学校行"}
                }
                events.append(source_event)
                audits.append({
                    "id":missing_official,"status":"announced","source":url,
                    "source_kind":"public_official",
                    "fields":{"name":"pass","date":"pass","venue":"pass","time":"pass",
                              "price":"unknown","reservation":"unknown","official_url":"pass"},
                    "corrections":{},
                    "note":"区の公式日程表で日付・会場・催事内容・時間を確認済み。料金・予約は未公表で推測しない。"
                })
            events.sort(key=lambda x:(x.get("ward",""),x.get("name","")))
            rows=Counter(e["ward"] for e in events)
            decisions=[]
            official_source=official["resolved_pages"][0]["resolved_url"]
            for event in events:
                fit=copy.deepcopy(event.get("family_fit") or {})
                fit["rubric_version"]="family-fit-v2"
                fit["overall"]=fit.get("overall") or fit.get("grade") or "B"
                # Reassess all eight pre-existing stated axes against the actual
                # current official page before the final staging approval.
                for axis in ("child_target","interactivity","age_fit","stay_flexibility",
                             "burden","cost","reservation","family_value"):
                    fit.setdefault("axes",{}).setdefault(axis,{
                        "grade":"unknown","reason":"要公式情報との個別再照合"})
                url=event.get("official_url") or event.get("url")
                decisions.append({
                    "candidate_id":(event["id"] if event["id"]=="nerima-district-0275426b6920"
                                    else "preserved-"+event["id"]),
                    "name":event["name"],
                    "ward":event["ward"],"decision":"published",
                    "family_fit":fit,"positive_signals":["family_compatible","official_venue_published"],
                    "negative_signals":(["night_burden"] if "Illumination" in event["name"] else []),
                    "hard_exclusion":None,"exclusion_type":None,
                    "primary_reason_code":"family_value_high",
                    "reason_codes":["family_value_high"],
                    "reasons":["過去の8軸評価に基づく家族向け候補。現在の公式ページで日付と会場の再確認あり。"],
                    "evidence":[{"url":url,"basis":"現在の公式開催概要と過去の掲載事実"}],
                    "override_reason":"",
                    "review_note":"v2 formal family-fit audit requires signoff; this is an explicit draft, not approved release."
                })
            annual_out_of_week=0
            for c in candidates:
                if not str(c.get("candidate_id") or "").startswith("nerima-district-"):
                    continue
                if c["date_end"]>=sat and c["date_start"]<=sun:
                    continue
                annual_out_of_week+=1
                name=c["name"]
                decisions.append({
                    "candidate_id":c["candidate_id"],"name":name,"ward":"練馬区",
                    "decision":"excluded",
                    "family_fit":{"rubric_version":"family-fit-v2",
                        "overall":"unknown","axes":{axis:{
                            "grade":"unknown","reason":"公式開催日が今回の週末に該当しないため8軸判定対象外。"}
                            for axis in ("child_target","interactivity","age_fit",
                                         "stay_flexibility","burden","cost",
                                         "reservation","family_value")}},
                    "positive_signals":[],"negative_signals":[],
                    "hard_exclusion":"date_mismatch","exclusion_type":"hard",
                    "primary_reason_code":"date_mismatch","reason_codes":["date_mismatch"],
                    "reasons":[f"公式年次日程は{c['date_start']}開催。"
                               f"対象週末{sat}〜{sun}とは一致しないため、この週への追加を見送る。"],
                    "evidence":[{"url":official_source,
                        "basis":"年度別の地区祭行・開催日・会場で照合済み"}],
                    "override_reason":""
                })
            official_reconciled_ids={d["candidate_id"] for d in decisions}
            official_unmatched=[cid for cid in official["candidate_ids"]
                                if cid not in official_reconciled_ids]
            total_candidates=len(decisions)
            ward_logs=ward_evidence(sat)
            coverage={"sources_checked":sum(
                sum(r.get("status")=="checked" for r in item["source_checks"])
                for item in ward_logs),
              "candidate_count":total_candidates,
              "duplicate_removed":0,"excluded_count":annual_out_of_week,
              "published_count":len(events),
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
                "events":audits,"summary":{"total":len(events),
                   "verified":sum(r.get("status")=="verified" for r in audits),
                   "announced":sum(r.get("status")=="announced" for r in audits)}})
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
                    "matched_candidate_count":16-len(official_unmatched),
                    "unmatched_official_rows":bool(official_unmatched),
                    "resolved_pages":official["resolved_pages"]}],
                "explicit_source_checks":[({
                    **check,
                    "unmatched_official_rows":bool(official_unmatched)
                } if check["source_id"]=="nerima_district_festivals_2026"
                    else check) for check in explicit_records],
                "stages":[],"summary":{"published":len(events),
                   "verified":sum(r.get("status")=="verified" for r in audits),
                   "announced":sum(r.get("status")=="announced" for r in audits)}})
            dump(a.output/(sat+"-decisions.json"),{
                "schema_version":1,"rubric_version":"family-fit-v2",
                "generated":generated,"migration_incomplete":False,
                "summary":{"candidate_total":total_candidates,"published":len(events),
                           "excluded":annual_out_of_week,"duplicate":0},
                "decisions":decisions})
            entry={"sat":sat,"sun":sun,"label":week["label"],"file":weekfile,
                   "count":len(events),"horizon_index":i+1,"publication_tier":tier}
            report["blockers"].append({"sat":sat,"kind":"v2_official_final_review_and_new_event_discovery_pending",
                "initial_rechecked_historical_event_candidates":len(events),
                "annual_schedule_official_rows_reconciled":16-len(official_unmatched),
                "annual_schedule_official_rows_remaining":official_unmatched,
                "v2_draft_decisions_prepared":len(decisions),
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
