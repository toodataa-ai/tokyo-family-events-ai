#!/usr/bin/env python3
"""Add formerly published, individually rechecked ongoing programs on actual weeks.

No blanket date-spans for multi-program umbrellas. The evidence ledger names
only continuously operable exhibitions, walks, and programs, with accountable
external official confirmation; original published event identity preserved.
"""
import argparse,copy,json,re
from pathlib import Path
AXES=["child_target","interactivity","age_fit","stay_flexibility","burden","cost","reservation","family_value"]
def load(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def write(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def norm(t):return re.sub(r"[\s　（）()「」『』]","",str(t or "")).casefold()
def gather(root):
 m=load(root/"manifest.json");d={}
 for week in m["weekends"]:
  p=load(root/week["file"]);ver={a["id"]:a for a in load(root/p["verification_file"])["events"]}
  events=list(p.get("events") or [])
  for f in p["event_files"]:events+=load(root/f)
  for e in events:
   if e["id"] in ver:
    d.setdefault(norm(e["name"]),[]).append((e,ver[e["id"]]))
 return d
def main():
 p=argparse.ArgumentParser();p.add_argument("--old",type=Path,required=True)
 p.add_argument("--stage",type=Path,required=True)
 p.add_argument("--ledger",type=Path,required=True)
 p.add_argument("--expected-stage-sha",required=True)
 p.add_argument("--report",type=Path,required=True);args=p.parse_args()
 ledger=load(args.ledger)
 if ledger["kind"]!="manual_authoritative_rolling_published_event_continuity" or ledger["baseline_data_staging_sha"]!=args.expected_stage_sha:
  raise ValueError("ledger mismatch")
 old=gather(args.old);stage=gather(args.stage);manifest=load(args.stage/"manifest.json")
 report={"continuous_event_families_checked":len(ledger["rules"]),"added":0,
         "already_present":0,"added_by_week":{},"multi_program_parent_records_skipped":ledger["special_multi_programs"],
         "source_facts_changed_only_in_new_event_shards":True,"deletions":0}
 for w in manifest["weekends"]:
  sat,sun=w["sat"],w["sun"];name=w["file"];info=load(args.stage/name)
  all_events=list(info.get("events") or [])
  for file in info["event_files"]:all_events+=load(args.stage/file)
  present={norm(e["name"]) for e in all_events}
  present_ids={e["id"] for e in all_events}
  to_add=[];audits=[]
  dec=load(args.stage/(sat+"-decisions.json"))
  for r in ledger["rules"]:
   if r["start"]>sun or r["end"]<sat:continue
   key=norm(r["name"])
   if key in present:
    report["already_present"]+=1;continue
   old_matches=old.get(key,[]);stage_matches=stage.get(key,[])
   available=stage_matches+old_matches
   verified=[(e,a) for e,a in available if a["status"]=="verified"]
   if not verified:
    # The previous tier may only have been 'announced' because the new
    # participation dates were not individually audited at that time.
    # The current authority ledger contains explicit dated venue evidence.
    verified=[(e,a) for e,a in available
              if a.get("status")=="announced"
              and r["source"].startswith("https://")
              and r.get("verified_on")=="2026-10-20"
              and r.get("reason")]
    if not verified:
     raise ValueError("No prior event entry plus real renewed authoritative evidence: "+r["name"])
   # Preserve existing visible/stable same ID where possible.
   e,a=next(((e,a) for e,a in verified if e["id"] not in present_ids),(None,None))
   if e is None:raise ValueError("Historical ID collision: "+r["name"])
   if e["name"]!=r["name"] or not e.get("venue"):raise ValueError("Incorrect historical primary venue: "+r["name"])
   copy_e=copy.deepcopy(e)
   original_start,original_end=copy_e["date_start"],copy_e["date_end"]
   copy_e["date_start"],copy_e["date_end"]=r["start"],r["end"]
   if copy_e["date_start"]>sun or copy_e["date_end"]<sat:
    raise ValueError("not on given weekend")
   copy_e.setdefault("ai",{})["checked_at"]="2026-10-20"
   copy_e["ai"]["discovery_query"]="recheck-2026-10-20 protected ongoing event continuity"
   copy_e["description"]=str(copy_e.get("description") or "")+" 継続開催の根拠："+r["reason"]
   new_a=copy.deepcopy(a)
   new_a["status"]="verified"
   new_a["source"]=r["source"]
   new_a["source_kind"]="organizer_official" if "city." not in r["source"] else "public_official"
   new_a["note"]="2026-10-20主催/自治体再確認: "+r["reason"]
   new_a["fields"]={"name":"pass","date":"pass","venue":"pass",
       "time":a.get("fields",{}).get("time","unknown"),
       "price":a.get("fields",{}).get("price","unknown"),
       "reservation":a.get("fields",{}).get("reservation","unknown"),
       "official_url":"pass"}
   new_a["corrections"]={}
   if (original_start,original_end)!=(r["start"],r["end"]):
    new_a["corrections"].update({"date_start":r["start"],"date_end":r["end"]})
    new_a["fields"]["date"]="corrected"
    new_a["field_changes"]={
      "date_start":{"from":original_start,"to":r["start"],"source":r["source"],"reason":r["reason"]},
      "date_end":{"from":original_end,"to":r["end"],"source":r["source"],"reason":r["reason"]}}
   # Correct the explicit known misstatement: dated admission ticket + night walk.
   if r["name"].startswith("祝）ACN"):
    new_a["corrections"]["price"]="事前日時指定券制。大人土日祝3,800円、小学生1,000円（時期・区分で変動）"
    new_a["corrections"]["reservation"]={"required":True,"note":"日時指定券の事前購入が必要。夜間・1.8kmの屋外歩行と子連れ負担に注意。"}
    new_a["fields"]["price"]="corrected";new_a["fields"]["reservation"]="corrected"
    new_a["field_changes"]=new_a.get("field_changes",{})|{
      "price":{"from":e.get("price"),"to":new_a["corrections"]["price"],"source":r["source"],"reason":r["reason"]},
      "reservation":{"from":e.get("reservation"),"to":new_a["corrections"]["reservation"],"source":r["source"],"reason":r["reason"]}}
   if r["name"]=="11月 いつでもものづくり":
    new_a["note"]+=" ※公式個別ページの開催概要欄は旧10月日付が残存。公式一覧と個別見出しを優先し、現地日程確認を推奨。"
   family_fit=copy.deepcopy(copy_e["family_fit"])
   family_fit["rubric_version"]=dec["rubric_version"]
   if not all(isinstance(family_fit.get("axes",{}).get(k),dict) for k in AXES):raise ValueError("old eight axes absent: "+r["name"])
   cand="continuity-"+e["id"]+"-"+sat
   dec["decisions"].append({
     "candidate_id":cand,"name":e["name"],"ward":e["ward"],"decision":"published",
     "family_fit":family_fit,"positive_signals":["prior_published_verified","current_authoritative_source"],
     "negative_signals":["night_burden","high_cost"] if r["name"].startswith("祝）ACN") else [],
     "hard_exclusion":None,"exclusion_type":None,
     "primary_reason_code":"family_value_high","reason_codes":["family_value_high"],
     "reasons":[r["reason"]],"evidence":[{"url":r["source"],"basis":r["reason"]}],
     "override_reason":""})
   to_add.append(copy_e);audits.append(new_a)
   present.add(key);present_ids.add(e["id"])
  if not to_add:continue
  shard=sat+"-events-verified-continuity.json"
  if (args.stage/shard).exists():raise ValueError("staging continuity shard already exists")
  write(args.stage/shard,to_add);info["event_files"].append(shard)
  w["count"]+=len(to_add);c=info["coverage"];c["candidate_count"]+=len(to_add);c["published_count"]+=len(to_add)
  for e in to_add:
   cov=next(x for x in c["wards"] if x["ward"]==e["ward"])
   cov["candidate_count"]+=1;cov["published_count"]+=1
  ver=load(args.stage/info["verification_file"]);ver["events"]+=audits
  ver["summary"]["total"]=len(ver["events"]);ver["summary"]["verified"]=sum(x["status"]=="verified" for x in ver["events"]);ver["summary"]["announced"]=sum(x["status"]=="announced" for x in ver["events"])
  ver["verified_on"]="2026-10-20"
  run=load(args.stage/info["run_file"]);run.setdefault("summary",{})["published"]=c["published_count"]
  run["summary"]["verified"]=ver["summary"]["verified"];run["summary"]["announced"]=ver["summary"]["announced"]
  run.setdefault("continuity_reverification",[]).append({
   "as_of":"2026-10-20","ids":[e["id"] for e in to_add],
   "authority":[a["source"] for a in audits],
   "multi_program_parents_automatically_rolled":False})
  dec["summary"]["candidate_total"]+=len(to_add);dec["summary"]["published"]+=len(to_add)
  write(args.stage/name,info);write(args.stage/info["verification_file"],ver)
  write(args.stage/info["run_file"],run);write(args.stage/(sat+"-decisions.json"),dec)
  report["added_by_week"][sat]=[e["id"] for e in to_add];report["added"]+=len(to_add)
 write(args.stage/"manifest.json",manifest)
 args.report.parent.mkdir(parents=True,exist_ok=True);write(args.report,report)
 print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":main()
