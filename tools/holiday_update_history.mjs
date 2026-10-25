#!/usr/bin/env node
// Persist a completed holiday-after DATA candidate's history before promoting it.
// The record stays in data-staging until the existing strict data-deploy CI succeeds.
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {applyVerification,eventIdentityKey,indoorOutdoorLabel} from '../site/app.js';

const fields=['ward','name','date_start','date_end','period','venue','time','price','description',
  'url','official_url','image','categories','reservation','indoor_outdoor','family_fit'];
const rel=(dataDir,file)=>path.posix.join(dataDir.replace(/\\/g,'/'),file);
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const isoDay=/^\d{4}-\d{2}-\d{2}$/;
const shaPattern=/^[0-9a-f]{40}$/;

function datePlus(day,n){
  const d=new Date(day+'T00:00:00Z');
  if(!Number.isFinite(d.getTime())||d.toISOString().slice(0,10)!==day) throw Error('invalid as-of date');
  d.setUTCDate(d.getUTCDate()+n);
  return d.toISOString().slice(0,10);
}

export function uniqueEvents(weeks){
  const map=new Map();
  for(const week of weeks){
    for(const ev of week.events||[]){
      const key=eventIdentityKey(ev);
      if(!ev.name||!key) throw Error('event missing identity');
      if(!map.has(key)) map.set(key,ev);
    }
  }
  return map;
}

function stableFacts(ev){
  return fields.map(f=>ev[f]===undefined?null:ev[f]);
}

export function buildEntry(oldManifest,newManifest,oldWeeks,newWeeks,asOf,baseSha){
  if(!shaPattern.test(baseSha)) throw Error('invalid original data-production SHA');
  if(!isoDay.test(asOf)) throw Error('invalid as-of date');
  datePlus(asOf,41);
  const list=newManifest.weekends||[];
  if(list.length!==6||newManifest.rolling_horizon_weeks!==6) throw Error('expected 6-week manifest');
  const weekday=new Date(asOf+'T00:00:00Z').getUTCDay();
  const first=datePlus(asOf,(6-weekday+7)%7);
  const startSat=list[0].sat;
  if(startSat!==first||newManifest.default!==first) throw Error('manifest does not start on planned Saturday');
  for(let i=0;i<6;i++){
    if(list[i].sat!==datePlus(first,7*i)) throw Error('non-consecutive weekend in manifest');
    if(list[i].sun!==datePlus(first,7*i+1)) throw Error('invalid Sunday in manifest');
  }
  if(!newManifest.generated||newManifest.generated===oldManifest.generated){
    throw Error('new manifest timestamp absent or unchanged');
  }
  const before=uniqueEvents(oldWeeks),after=uniqueEvents(newWeeks);
  const latest={};
  let added=0,changed=0,removed=0,rolled=0;
  for(const [key,ev] of after){
    if(!before.has(key)) added++;
    else if(!same(stableFacts(ev),stableFacts(before.get(key)))) changed++;
  }
  for(const [key,ev] of before){
    if(after.has(key)) continue;
    const end=ev.date_end||ev.date_start||'';
    if(isoDay.test(end)&&end<asOf) rolled++;
    else removed++;
  }
  Object.assign(latest,{
    run_id:'holiday-after-'+asOf+'-'+baseSha.slice(0,12),
    run_type:'holiday_after_update',as_of_jst:asOf,
    holiday_block_end:datePlus(asOf,-1),prompt_version:'v1.15',
    target_start:asOf,target_end:datePlus(asOf,41),
    previous_manifest_generated:oldManifest.generated||'',
    new_manifest_generated:newManifest.generated,
    base_data_production_sha:baseSha,
    published_unique_before:before.size,published_unique_after:after.size,
    added_unique:added,changed_unique:changed,removed_unique:removed,
    rolled_out_unique:rolled,
  });
  return latest;
}


// Strictly additive official event supplements are NOT holiday-after runs.
// This branch checks the full existing 6-week corpus and all unchanged facts.
// It cannot be used to authorize deletions, hidden rows or data publication.
export function checkStagingOfficialAddition(oldManifest,newManifest,oldWeeks,newWeeks,row,baseSha){
  if(!shaPattern.test(baseSha)||row?.base_data_production_sha!==baseSha)
    throw Error('staging addition base SHA mismatch');
  if(row.run_type!=='staging_manual_official_addition'||row.status!=='stage_candidate_only')
    throw Error('not an unpublished manual official addition');
  if(!isoDay.test(row.as_of_jst)||row.run_id!=='staging-suginami-official-two-events-'+row.as_of_jst)
    throw Error('invalid staging-only event addition identifier');
  if(!row.executed_at||!Number.isFinite(Date.parse(row.executed_at)))
    throw Error('invalid staging addition execution timestamp');
  if(!newManifest.generated||newManifest.generated===oldManifest.generated||
     !(Date.parse(newManifest.generated)>Date.parse(oldManifest.generated)))
    throw Error('staging addition manifest timestamp absent, unchanged or stale');
  if(oldManifest.default!==newManifest.default||
     oldManifest.rolling_horizon_weeks!==6||newManifest.rolling_horizon_weeks!==6||
     oldManifest.weekends?.length!==6||newManifest.weekends?.length!==6)
    throw Error('staging addition may not roll the six-week manifest');
  if(oldWeeks.length!==6||newWeeks.length!==6)
    throw Error('staging addition requires all six weeks');

  let added=0,changed=0,removed=0;
  const newIds=new Set();
  for(let i=0;i<6;i++){
    const oldEntry=oldManifest.weekends[i],newEntry=newManifest.weekends[i];
    if(oldEntry.sat!==newEntry.sat||oldEntry.sun!==newEntry.sun||
       oldEntry.file!==newEntry.file||
       oldWeeks[i].sat!==newWeeks[i].sat||oldWeeks[i].sat!==oldEntry.sat)
      throw Error('staging addition changed an existing weekend');
    const prev=new Map(),next=new Map();
    for(const e of oldWeeks[i].events){
      if(!e.id||prev.has(e.id)) throw Error('duplicate/missing previous event ID in '+oldEntry.sat);
      prev.set(e.id,e);
    }
    for(const e of newWeeks[i].events){
      if(!e.id||next.has(e.id)) throw Error('duplicate/missing new event ID in '+oldEntry.sat);
      next.set(e.id,e);
    }
    for(const [id,original] of prev){
      if(!next.has(id)){removed++;continue;}
      if(!same(stableFacts(original),stableFacts(next.get(id)))) changed++;
    }
    for(const [id,e] of next){
      if(prev.has(id)) continue;
      added++;
      if(newIds.has(id)) throw Error('new official event ID duplicated across weeks');
      newIds.add(id);
      const official=e.official_url||'';
      if(!/^https:\/\/www\.city\.suginami\.tokyo\.jp\/s\d+\/event\/\d+\.html$/.test(official)||
         e.ward!=='杉並区')
        throw Error('new record not sourced from a Suginami official detail: '+id);
      if(!e.date_start||e.date_start!==e.date_end||
         (e.date_start!=='2026-10-24'&&e.date_start!=='2026-10-25')||
         !((i===0)&&newEntry.sat==='2026-10-24'))
        throw Error('new Suginami event not in approved staging recovery weekend');
    }
    if(newEntry.count!==oldEntry.count+next.size-prev.size)
      throw Error('manifest event count differs from the new week rows');
  }
  if(added!==2||changed!==0||removed!==0||
     !newIds.has('suginami-official-28531')||!newIds.has('suginami-official-28567')||
     row.added_weekly_records!==added||
     row.changed_existing_records!==changed||row.removed_weekly_records!==removed||
     row.target_start!=='2026-10-24'||row.target_end!=='2026-10-25')
    throw Error('official staging addition must contain exactly two approved records and preserve all others');
  return {added,changed,removed,retained:oldWeeks.reduce((n,w)=>n+w.events.length,0)};
}

// Independently verified, strictly additive weekday-holiday supplement.
// Unlike rolling holiday-after refresh, it NEVER rotates/removes a week.
export function checkIndependentHolidayAddition(oldManifest,newManifest,oldWeeks,newWeeks,row,baseSha){
  if(!shaPattern.test(baseSha)||row?.base_data_production_sha!==baseSha)
    throw Error('independent holiday supplement base SHA mismatch');
  if(row?.run_type!=='manual_independent_holiday_addition'||row?.status!=='official_verified_addition')
    throw Error('invalid independent holiday addition history status');
  if(!isoDay.test(row.target_holiday)||!isoDay.test(row.as_of_jst)||
     row.run_id!=='manual-independent-holiday-'+row.target_holiday+'-'+baseSha.slice(0,12))
    throw Error('invalid independent holiday date/run identifier');
  if(!row.executed_at||!Number.isFinite(Date.parse(row.executed_at)))
    throw Error('independent holiday audit executed_at required');
  const day=row.target_holiday, dt=new Date(day+'T00:00:00Z');
  if(Number.isNaN(dt.getTime())||dt.getUTCDay()===0||dt.getUTCDay()===6)
    throw Error('independent holiday must be a valid weekday date');
  if(!(newManifest.holidays||[]).some(h=>h.date===day)||
     !(oldManifest.holidays||[]).some(h=>h.date===day))
    throw Error('independent holiday not registered in both official manifests');
  if(!newManifest.generated||newManifest.generated===oldManifest.generated||
     Date.parse(newManifest.generated)<=Date.parse(oldManifest.generated))
    throw Error('holiday supplement manifest timestamp not advanced');
  if(oldManifest.default!==newManifest.default||oldManifest.rolling_horizon_weeks!==6||
     newManifest.rolling_horizon_weeks!==6||oldWeeks.length!==6||newWeeks.length!==6)
    throw Error('holiday supplement must preserve six-week window');
  const previous=oldManifest.weekends||[],next=newManifest.weekends||[];
  if(previous.length!==6||next.length!==6) throw Error('six weekly entries required');
  let assigned=-1;
  for(let i=0;i<previous.length;i++){
    const w=previous[i],following=previous[i+1]?.sat||datePlus(w.sat,7);
    if(w.sun<day&&day<following) assigned=i;
  }
  if(assigned<0) throw Error('independent holiday not associated with a published weekend');
  let added=0;const found=[];
  for(let i=0;i<6;i++){
    const before=previous[i],after=next[i];
    if(before.sat!==after.sat||before.sun!==after.sun||before.file!==after.file||
       before.horizon_index!==after.horizon_index||
       before.publication_tier!==after.publication_tier||
       oldWeeks[i].sat!==before.sat||newWeeks[i].sat!==after.sat)
      throw Error('holiday supplement altered weekend routing');
    const oldIds=new Map(),newIds=new Map();
    for(const e of oldWeeks[i].events){
      if(!e.id||oldIds.has(e.id)) throw Error('invalid protected old event identity');
      oldIds.set(e.id,e);
    }
    for(const e of newWeeks[i].events){
      if(!e.id||newIds.has(e.id)) throw Error('invalid new event identity');
      newIds.set(e.id,e);
    }
    for(const [id,ev] of oldIds){
      if(!newIds.has(id)||!same(stableFacts(newIds.get(id)),stableFacts(ev)))
        throw Error('existing published event changed or removed: '+id);
    }
    for(const [id,ev] of newIds){
      if(oldIds.has(id))continue;
      if(i!==assigned||ev.date_start!==day||ev.date_end!==day)
        throw Error('new event outside assigned independent holiday: '+id);
      const official=String(ev.official_url||'');
      if(!/^https:\/\//.test(official)||!ev.name||!ev.venue||!ev.ward)
        throw Error('new holiday event lacks official evidence or facts: '+id);
      found.push(id);added++;
    }
    if(after.count!==before.count+newIds.size-oldIds.size)
      throw Error('weekly manifest count mismatch');
  }
  if(added<1||added>40||found.length!==new Set(found).size||
     row.added_weekly_records!==added||
     !Array.isArray(row.new_event_ids)||
     !same([...found].sort(),[...row.new_event_ids].sort())||
     row.changed_existing_records!==0||row.removed_weekly_records!==0)
    throw Error('holiday supplement count, identity, or nonregression mismatch');
  return {added,changed:0,removed:0,assigned_week:previous[assigned].sat,holiday:day};
}

function parseJson(raw,label){
  try{return JSON.parse(raw);}catch(e){throw Error('invalid JSON '+label+': '+e.message);}
}

function storeReaders(dataDir,baseRef){
  const fromCurrent=file=>parseJson(fs.readFileSync(rel(dataDir,file),'utf8'),file);
  const fromBase=file=>{
    const gitPath=rel(dataDir,file);
    const raw=execFileSync('git',['show',baseRef+':'+gitPath],{encoding:'utf8'});
    return parseJson(raw,gitPath);
  };
  return {fromCurrent,fromBase};
}

function loadWeeks(manifest,read){
  const arr=[];
  for(const entry of manifest.weekends||[]){
    const week=read(entry.file);
    const events=[...(week.events||[])];
    for(const file of week.event_files||[]){
      const rows=read(file);
      if(!Array.isArray(rows)) throw Error('invalid shard array '+file);
      events.push(...rows);
    }
    const audit=week.verification_file?read(week.verification_file):null;
    arr.push({sat:entry.sat,events:applyVerification(events,audit)
      .map(ev=>({...ev,indoor_outdoor:indoorOutdoorLabel(ev)}))});
  }
  return arr;
}

function argumentsMap(argv){
  const args={};
  for(let i=0;i<argv.length;i++){
    if(argv[i]==='--write'||argv[i]==='--check'){args.mode=argv[i].slice(2);continue;}
    if(!argv[i].startsWith('--')||i+1>=argv.length) throw Error('bad CLI arguments');
    args[argv[i].slice(2)]=argv[++i];
  }
  if(!args.mode||!shaPattern.test(args['base-ref']||'')) throw Error('--write/--check and real --base-ref SHA required');
  return args;
}

function execute(argv){
  const args=argumentsMap(argv),dataDir=args['data-dir']||'site/data',baseRef=args['base-ref'];
  const {fromCurrent,fromBase}=storeReaders(dataDir,baseRef);
  const oldManifest=fromBase('manifest.json'),newManifest=fromCurrent('manifest.json');
  const oldHistory=fromBase('update_history.json');
  const newHistory=fromCurrent('update_history.json');
  if(oldHistory.schema_version!==1||!Array.isArray(oldHistory.history)||
     newHistory.schema_version!==1||!Array.isArray(newHistory.history)){
    throw Error('invalid update_history schema');
  }
  const preserved=newHistory.history.slice(0,oldHistory.history.length);
  if(!same(preserved,oldHistory.history)) throw Error('previous published history was modified or deleted');
  if(args.mode==='write'){
    if(newHistory.history.length!==oldHistory.history.length) throw Error('candidate already contains new history');
  }
  const ids=newHistory.history.map(row=>row.run_id).filter(Boolean);
  if(new Set(ids).size!==ids.length) throw Error('duplicate run_id in update history');else if(newHistory.history.length!==oldHistory.history.length+1){
    throw Error('exactly one new verified holiday-after history row required');
  }
  const asOf=args.mode==='write'?args['as-of']:newHistory.history.at(-1)?.as_of_jst;
  if(!asOf) throw Error('missing actual as-of date');
  if(args.mode==='check' && newHistory.history.at(-1)?.run_type==='manual_independent_holiday_addition'){
    const result=checkIndependentHolidayAddition(oldManifest,newManifest,
      loadWeeks(oldManifest,fromBase),loadWeeks(newManifest,fromCurrent),
      newHistory.history.at(-1),baseRef);
    process.stdout.write('Independent holiday additive-only verified: '+
      result.holiday+' week='+result.assigned_week+' added='+result.added+
      ' prior records preserved; no other weeks altered.\n');
    return;
  }
  if(args.mode==='check' && newHistory.history.at(-1)?.run_type==='staging_manual_official_addition'){
    const rows=checkStagingOfficialAddition(oldManifest,newManifest,
      loadWeeks(oldManifest,fromBase),loadWeeks(newManifest,fromCurrent),
      newHistory.history.at(-1),baseRef);
    process.stdout.write('Strict staging-only official addition history verified: '+
      rows.added+' new, '+rows.changed+' changed, '+rows.removed+
      ' removed, '+rows.retained+' prior event rows retained. Not authorized for publication.\n');
    return;
  }
  const entry=buildEntry(oldManifest,newManifest,loadWeeks(oldManifest,fromBase),
    loadWeeks(newManifest,fromCurrent),asOf,baseRef);
  if(args.mode==='write'){
    entry.executed_at=new Date().toISOString();
    entry.note='休日明けの6週間データ更新（公式監査・CI合格時に公開）';
    newHistory.history.push(entry);
    fs.writeFileSync(rel(dataDir,'update_history.json'),JSON.stringify(newHistory,null,2)+'\n');
    process.stdout.write('Wrote holiday-after candidate history; publishing requires strict CI. '+asOf+'\n');
  }else{
    const actual=newHistory.history.at(-1);
    if(typeof actual.executed_at!=='string'||!Number.isFinite(Date.parse(actual.executed_at))){
      throw Error('history executed_at missing or invalid');
    }
    for(const [key,val] of Object.entries(entry)){
      if(!same(actual[key],val)) throw Error('history discrepancy: '+key+
        ' expected '+JSON.stringify(val)+' got '+JSON.stringify(actual[key]));
    }
    process.stdout.write('Holiday-after history matches published baseline and candidate event facts: '+
      entry.published_unique_after+' unique events\n');
  }
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  try{execute(process.argv.slice(2));}catch(e){console.error('BLOCKER:',e.message);process.exitCode=1;}
}
