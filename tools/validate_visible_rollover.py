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
def continuity(before,after):
 old,_=load(before);new,m=load(after)
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
    affected.append({"target_sat":sat,"original_week":prev_week,"original_id":old_id,
       "name":o["name"],"original_date_end":o.get("date_end"),
       "official_url":o.get("official_url"),"error":"still_running_legacy_event_disappeared_from_visible_week"})
 unique={tuple((r["target_sat"],r["original_id"])):r for r in affected}
 return {"verified":len(unique)==0,"missing_active_count":len(unique),
         "missing_active":list(unique.values()),"original_published_rows":len(old),
         "new_published_rows":len(new)}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--old",required=True)
 p.add_argument("--new",required=True);p.add_argument("--report",required=True);a=p.parse_args()
 result=continuity(a.old,a.new)
 Path(a.report).parent.mkdir(parents=True,exist_ok=True)
 Path(a.report).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
 print(json.dumps(result,ensure_ascii=False))
 if not result["verified"]:sys.exit(2)
