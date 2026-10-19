import fs from "node:fs";
import path from "node:path";
import {createRequire} from "node:module";
import {eventIdentityKey,applyVerification,indoorOutdoorLabel} from "../../audit/site/app.js";
const read=(p)=>JSON.parse(fs.readFileSync(p,"utf8"));
function entries(root){
 const man=read(path.join(root,"site/data/manifest.json"));
 const result=[];
 for(const w of man.weekends){
  const week=read(path.join(root,"site/data",w.file));
  let events=[...(week.events||[])];
  for(const sh of week.event_files||[])events.push(...read(path.join(root,"site/data",sh)));
  const aud=week.verification_file?read(path.join(root,"site/data",week.verification_file)):null;
  for(const ev of applyVerification(events,aud))
   result.push({week:w.sat,ev:{...ev,indoor_outdoor:indoorOutdoorLabel(ev)}});
 }
 return result;
}
const old=entries("old"),now=entries("new");
function unique(raw){
 const map=new Map();
 for(const {week,ev} of raw){
  const key=eventIdentityKey(ev);
  if(!map.has(key))map.set(key,{...ev,old_week:week,identity:key});
 }
 return map;
}
const prev=unique(old),next=unique(now);
const stagedById=new Map(now.map(x=>[x.ev.id,x.ev]));
const missing=[];
for(const [key,ev] of prev){
 if(next.has(key))continue;
 missing.push({id:ev.id,name:ev.name,ward:ev.ward,
   start:ev.date_start,end:ev.date_end,old_week:ev.old_week,
   official_url:ev.official_url||ev.url||"",
   category:ev.date_end&&ev.date_end<"2026-10-19"?"rolled_out":"potential_unapproved_removal",
   still_present_id:stagedById.has(ev.id),
   current_same_id:stagedById.has(ev.id)?{
     name:stagedById.get(ev.id).name,
     start:stagedById.get(ev.id).date_start,
     end:stagedById.get(ev.id).date_end,
     venue:stagedById.get(ev.id).venue
   }:null,
   matching_name_events:now.filter(x=>x.ev.name===ev.name).map(x=>({
      id:x.ev.id,week:x.week,date_start:x.ev.date_start,date_end:x.ev.date_end,
      venue:x.ev.venue})).slice(0,6)});
}
const history=read("new/site/data/update_history.json").history.at(-1);
const activeDropped=missing.filter(x=>x.category==="potential_unapproved_removal");
const out={old_unique:prev.size,new_unique:next.size,
  history:{before:history.published_unique_before,after:history.published_unique_after,
    rolled:history.rolled_out_unique,removed:history.removed_unique},
  missing,activeDropped,dates_in_first_week:next.size};
if(prev.size!==history.published_unique_before||next.size!==history.published_unique_after)throw Error("history mismatch");
fs.writeFileSync("audit-comparison.json",JSON.stringify(out,null,2));
console.log("HISTORY",JSON.stringify(out.history));
console.log("ACTIVE_DROPPED",JSON.stringify(activeDropped));
console.log("BASELINE_EVENT_ROWS",old.length,"STAGING_EVENT_ROWS",now.length);
if(activeDropped.length)console.log("PRESERVATION_SEMANTIC_WARNING: unique published identity absent from rolling manifest, source JSON still physically present");
