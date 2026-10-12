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
    run_type:'holiday-after-update',as_of_jst:asOf,
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
  }else if(newHistory.history.length!==oldHistory.history.length+1){
    throw Error('exactly one new verified holiday-after history row required');
  }
  const asOf=args.mode==='write'?args['as-of']:newHistory.history.at(-1)?.as_of_jst;
  if(!asOf) throw Error('missing actual as-of date');
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
