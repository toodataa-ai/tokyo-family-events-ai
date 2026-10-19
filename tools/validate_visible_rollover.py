#!/usr/bin/env python3
"""Fail if any previously published, still-current event vanishes from a week.

Verifies *logical* participation in the rolling user-visible manifest, not just
the physical presence of archived JSON. Same official event can have different
historic IDs; preserve the older source and require a visible equivalent by
normalized name + real overlap. A changed name must retain original event ID.
"""
import argparse,collections,datetime,json,re,sys
from pathlib import Path
def read(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def normalized(x):return re.sub(r"[\s　（）()「」『』]","",str(x or "")).casefold()
def load(root):
 root=Path(root); m=read(root/"manifest.json")
 rows=[]
 for week in m["weekends"]:
  doc=read(root/week["file"])
  events=list(doc.get("events") or [])
  for s in doc.get("event_files") or []:events+=read(root/s)
  for e in events:rows.append((week["sat"],week["sun"],e))
 return rows,m
def continuity(before,after,policy=None):
 old,_=load(before);new,m=load(after)
 policies=(policy or {}).get("rules") or []
 if policy is not None and (policy.get("expected_rule_count")!=len(policies)
     or len(policies)!=4 or policy.get("as_of_jst")!="2026-10-19"):
  raise ValueError("explicit once-scoped umbrella policy invalid")
 keys=[(normalized(x["name"]),x["week"]) for x in policies]
 if len(set(keys))!=len(keys):raise ValueError("duplicate waiver")
 covered_policy=[]

 each=collections.defaultdict(list)
 for sat,sun,e in new:each[sat].append(e)
 affected=[]
 for new_week in m["weekends"]:
  sat,sun=new_week["sat"],new_week["sun"]
  for prev_week,_,o in old:
   if not (str(o.get("date_start") or "")<=sun and str(o.get("date_end") or "")>=sat):
    continue
   title=normalized(o["name"]); old_id=o["id"]
   matches=[n for n in each[sat] if (n.get("id")==old_id or normalized(n.get("name"))==title)
            and (str(n.get("date_start") or "")<=sun and str(n.get("date_end") or "")>=sat)]
   if not matches:
    # Only explicitly authorized old blanket-period umbrellas can be
    # replaced by independently confirmed day-specific subprograms.
    # No program on an officially empty date is not a deleted event.
    special=next((p for p in policies if normalized(p["name"])==title
                  and p["week"]==sat),None)
    if special:
     if (not special.get("official_url","").startswith("https://")
          or not special.get("basis") or
          special["kind"] not in
            ("official_non_occurrence_in_this_week","official_subevents_cover_target_week")):
      raise ValueError("umbrella authorization has no official evidence")
     if special["kind"]=="official_non_occurrence_in_this_week":
      if special["expected_children"] or "11/7" not in special["basis"]:
       raise ValueError("no-program claim must be tied to exact dated published schedule")
      covered_policy.append({"name":o["name"],"week":sat,"kind":special["kind"]})
      continue
     expected=special["expected_children"]
     if not expected:raise ValueError("missing actual participation unit names")
     for child in expected:
      child_records=[x for x in each[sat] if normalized(x.get("name"))==normalized(child)
           and (str(x.get("date_start") or "")<=sun and str(x.get("date_end") or "")>=sat)]
      if not child_records:
       affected.append({"target_sat":sat,"original_week":prev_week,
        "original_id":old_id,"name":o["name"],"missing_required_child":child,
        "error":"official_festival_subevent_must_be_real_visible"})
     if all(any(normalized(x.get("name"))==normalized(child)
           and str(x.get("date_start") or "")<=sun
           and str(x.get("date_end") or "")>=sat for x in each[sat])
           for child in expected):
      covered_policy.append({"name":o["name"],"week":sat,"kind":special["kind"],
                             "children":expected})
     continue
    affected.append({"target_sat":sat,"original_week":prev_week,"original_id":old_id,
       "name":o["name"],"original_date_end":o.get("date_end"),
       "official_url":o.get("official_url"),"error":"still_running_legacy_event_disappeared_from_visible_week"})
 unique={tuple((r["target_sat"],r["original_id"])):r for r in affected}
 return {"verified":len(unique)==0,"missing_active_count":len(unique),
         "missing_active":list(unique.values()),"original_published_rows":len(old),
         "new_published_rows":len(new),
         "scoped_umbrella_rules_applied":[dict(name=v["name"],week=v["week"],
          kind=v["kind"]) for v in {(x["name"],x["week"]):x for x in covered_policy}.values()],
         "policy_rule_count":len(policies)}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--old",required=True)
 p.add_argument("--new",required=True);p.add_argument("--report",required=True)
 p.add_argument("--policy",type=Path)
 a=p.parse_args()
 result=continuity(a.old,a.new,read(a.policy) if a.policy else None)
 Path(a.report).parent.mkdir(parents=True,exist_ok=True)
 Path(a.report).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
 print(json.dumps(result,ensure_ascii=False))
 if not result["verified"]:sys.exit(2)
