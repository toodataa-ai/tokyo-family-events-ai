#!/usr/bin/env python3
"""Add only individually sourced new Tokyo-family event units to 6-week staging.

Requires an explicit dated, venue-and-family-fit source ledger. No existing
event, ID, audit decision, historical shard, prompt or source registry removed.
"""
import argparse,copy,json,re
from collections import Counter
from datetime import datetime,date
from pathlib import Path
from urllib.parse import urlsplit

AXES=("child_target","interactivity","age_fit","stay_flexibility","burden","cost","reservation","family_value")
def load(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def dump(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def guard_ledger(items,expected_sha):
 if items.get("kind")!="manually_primary_source_rechecked_individual_participation_units" or items.get("baseline_stage_expected_sha")!=expected_sha:raise ValueError("ledger identity does not match pre-reviewed stage")
 if items.get("expected_primary_source_count")!=len(items.get("events",[])) or not items["events"]:raise ValueError("source ledger count mismatch")
 seen=set()
 for r in items["events"]:
  if r["id"] in seen:raise ValueError("duplicate ledger IDs")
  seen.add(r["id"])
  if len(r["tags"])!=8 or any(not x for x in r["tags"]):raise ValueError("all eight axes need written independent reason")
  if r["grade"] not in ("A","B","C"):raise ValueError("invalid family fit")
  if not r["source"].startswith("https://") or not urlsplit(r["source"]).hostname:raise ValueError("non-HTTPS source")
  start,end=date.fromisoformat(r["from"]),date.fromisoformat(r["to"])
  if start>end or not r["venue"] or not r["date_venue_evidence"]:raise ValueError("missing individual official date/venue basis")
  if r["reservation"]["required"] not in (True,False,None):raise ValueError("invalid booking")
def make_event(r,run_date):
 profile={
 "rubric_version":"family-fit-v2","grade":r["grade"],"overall":r["grade"],
 "reason":r["tags"][7],"axes":{}}
 axes_grades={"child_target":r["grade"],"interactivity":r["grade"],
 "age_fit":"B" if "制限" in r["tags"][2] else r["grade"],
 "stay_flexibility":"B","burden":"B","cost":"B" if "有料" in r["price"] else "A",
 "reservation":"B" if r["reservation"]["required"] else "A" if r["reservation"]["required"] is False else "unknown",
 "family_value":r["grade"]}
 if r["id"]=="official-2026-edogawa-parasports":
  axes_grades["age_fit"]="C";axes_grades["child_target"]="B"
 if r["id"]=="official-2026-urban-agriculture-pre":
  axes_grades["child_target"]="B";axes_grades["interactivity"]="B"
 if r["id"]=="official-2026-lumina-nogata":
  axes_grades["interactivity"]="C"
 for axis,reason in zip(AXES,r["tags"]):
  profile["axes"][axis]={"grade":axes_grades[axis],"reason":reason}
 start,end=date.fromisoformat(r["from"]),date.fromisoformat(r["to"])
 period=f"{start.month}/{start.day}" if start==end else f"{start.month}/{start.day}〜{end.month}/{end.day}"
 return {
  "id":r["id"],"ward":r["ward"],"name":r["name"],
  "url":r["source"],"official_url":r["source"],"source":r["source"],
  "image":None,"period":period,"date_start":r["from"],"date_end":r["to"],
  "time":r["time"],"venue":r["venue"],"price":r["price"],
  "description":r["description"],"categories":r["categories"],
  "family_fit":profile,"reservation":r["reservation"],
  "indoor_outdoor":r["indoor_outdoor"],
  "ai":{"checked_at":run_date,"confidence":"high",
        "discovery_query":"manual official primary-source verification"}
 }
def main():
 p=argparse.ArgumentParser();p.add_argument("--data-dir",type=Path,required=True)
 p.add_argument("--ledger",type=Path,required=True);p.add_argument("--report",type=Path,required=True)
 p.add_argument("--expected-stage-sha",required=True)
 args=p.parse_args()
 ledger=load(args.ledger);guard_ledger(ledger,args.expected_stage_sha)
 directory=args.data_dir;man=load(directory/"manifest.json")
 report={"ledger_count":len(ledger["events"]),"added":0,"skipped_existing":0,"reviewed_sources":[],
         "added_by_week":{},"original_files_deleted":0}
 for w in man["weekends"]:
  sat,sun=w["sat"],w["sun"]
  rows=[r for r in ledger["events"] if r["from"]<=sun and r["to"]>=sat]
  if not rows:continue
  week=load(directory/w["file"]);existing=[]
  for sh in week["event_files"]:existing+=load(directory/sh)
  existing+=week.get("events",[])
  existing_id={e["id"] for e in existing}
  norm=lambda x:re.sub(r"[\s　（）()]","",(x or "")).casefold()
  seen_name={(norm(e["name"]),e["date_start"]) for e in existing}
  to_add=[]
  for r in rows:
   if r["id"] in existing_id or (norm(r["name"]),r["from"]) in seen_name:
    report["skipped_existing"]+=1;continue
   ev=make_event(r,"2026-10-20")
   to_add.append(ev)
   existing_id.add(r["id"]);seen_name.add((norm(r["name"]),r["from"]))
  if not to_add:continue
  shard=sat+"-events-manual-festival-subprograms.json"
  if shard in week["event_files"] or (directory/shard).exists():raise ValueError("collision with existing shard")
  week["event_files"].append(shard)
  w["count"]+=len(to_add)
  c=week["coverage"];c["candidate_count"]+=len(to_add);c["published_count"]+=len(to_add)
  for e in to_add:
   ward=next(x for x in c["wards"] if x["ward"]==e["ward"])
   ward["candidate_count"]+=1;ward["published_count"]+=1
  verify=load(directory/week["verification_file"])
  decisions=load(directory/(sat+"-decisions.json"))
  run=load(directory/week["run_file"])
  for e in to_add:
   r=next(z for z in rows if z["id"]==e["id"])
   event_note="2026-10-20公式照合: "+r["date_venue_evidence"]
   verify["events"].append({
    "id":e["id"],"status":"verified" if w["publication_tier"]=="full" else "announced",
    "source":r["source"],"source_kind":r["source_kind"],
    "fields":{"name":"pass","date":"pass","venue":"pass","time":"pass" if r["time"] else "unknown",
              "price":"unknown" if "未記載" in r["price"] or "不明" in r["price"] else "pass",
              "reservation":"unknown" if r["reservation"]["required"] is None else "pass",
              "official_url":"pass"},
    "corrections":{},"note":event_note+"。"+r["reservation"]["note"]
   })
   fit=copy.deepcopy(e["family_fit"]);fit["rubric_version"]=decisions["rubric_version"]
   published={
    "candidate_id":"manual-primary-"+e["id"]+"-"+sat,
    "name":e["name"],"ward":e["ward"],"decision":"published",
    "family_fit":fit,"hard_exclusion":None,"exclusion_type":None,
    "primary_reason_code":"family_value_high","reason_codes":["family_value_high"],
    "reasons":[r["date_venue_evidence"],r["description"]],
    "evidence":[{"url":r["source"],"basis":r["date_venue_evidence"]}],
    "positive_signals":["confirmed_official_day_venue","family_compatible"],
    "negative_signals":(["reservation_difficult"] if r["reservation"]["required"] else []),
    "override_reason":""
   }
   decisions["decisions"].append(published)
  decisions["summary"]["published"]+=len(to_add)
  decisions["summary"]["candidate_total"]+=len(to_add)
  verify["summary"]["total"]=len(verify["events"])
  verify["summary"]["verified"]=sum(x["status"]=="verified" for x in verify["events"])
  verify["summary"]["announced"]=sum(x["status"]=="announced" for x in verify["events"])
  verify["verified_on"]="2026-10-20"
  run["summary"]["published"]=c["published_count"]
  run["summary"]["verified"]=verify["summary"]["verified"]
  run["summary"]["announced"]=verify["summary"]["announced"]
  run.setdefault("individual_primary_official_additions",[]).append({
   "verified_on":"2026-10-20","participation_unit_ids":[e["id"] for e in to_add],
   "evidence_sources":[e["official_url"] for e in to_add],
   "source_ledger_path":"research/official_verified_new_events_20261020.json"})
  dump(directory/shard,to_add);dump(directory/w["file"],week)
  dump(directory/week["verification_file"],verify)
  dump(directory/(sat+"-decisions.json"),decisions)
  dump(directory/week["run_file"],run)
  report["added"]+=len(to_add)
  report["added_by_week"][sat]=[e["id"] for e in to_add]
 for r in ledger["events"]:
  if not any(r["id"] in x for x in report["added_by_week"].values()):
   raise ValueError("official lead not included in any target week: "+r["id"])
  report["reviewed_sources"].append({"id":r["id"],"official_url":r["source"],
                                    "dates":[r["from"],r["to"]],
                                    "provenance":r["date_venue_evidence"]})
 if report["added"] <len(ledger["events"]):raise ValueError("expected at least one event per approved participation unit")
 dump(directory/"manifest.json",man)
 args.report.parent.mkdir(parents=True,exist_ok=True)
 dump(args.report,report)
 print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":main()
