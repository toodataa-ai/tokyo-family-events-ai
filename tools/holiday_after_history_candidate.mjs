#!/usr/bin/env node
// Exact history contract used for this isolated data-only staging candidate.
// The published old history is preserved byte-for-byte as JSON entries.
import fs from 'node:fs';
import cp from 'node:child_process';
import path from 'node:path';
import {buildEntry} from './holiday_update_history.mjs';
import {applyVerification, indoorOutdoorLabel} from '../site/app.js';

const asOf='2026-10-19';
const base=process.argv[2];
if (!base || !/^[0-9a-f]{40}$/.test(base)) {
  throw Error('expected immutable data-production base SHA');
}
const dir='site/data';
const prev=(file)=>JSON.parse(cp.execFileSync('git',['show',base+':'+path.posix.join(dir,file)],{encoding:'utf8'}));
const curr=(file)=>JSON.parse(fs.readFileSync(path.join(dir,file),'utf8'));
const previousHistory=prev('update_history.json');
const currentHistory=curr('update_history.json');
if (JSON.stringify(previousHistory)!==JSON.stringify(currentHistory)) {
  throw Error('original history already modified; refused to overwrite prior records');
}
function weeks(manifest,read) {
  return manifest.weekends.map(row=>{
    const data=read(row.file);
    const events=[...(data.events||[])];
    for(const file of data.event_files||[]) {
      const part=read(file);
      if(!Array.isArray(part))throw Error('invalid event shard '+file);
      events.push(...part);
    }
    const audit=data.verification_file?read(data.verification_file):null;
    return {
      sat:row.sat,events:applyVerification(events,audit)
        .map(ev=>({...ev,indoor_outdoor:indoorOutdoorLabel(ev)}))
    };
  });
}
const before=prev('manifest.json');
const after=curr('manifest.json');
const entry=buildEntry(before,after,weeks(before,prev),weeks(after,curr),asOf,base);
if(previousHistory.history.some(x=>x.run_id===entry.run_id))throw Error('duplicate historical run_id');
entry.executed_at=new Date().toISOString();
entry.note='休日明け6週間の公式実測照合済みデータ候補（data-staging。productionは未反映）';
currentHistory.history.push(entry);
fs.writeFileSync(path.join(dir,'update_history.json'),JSON.stringify(currentHistory,null,2)+'\n');
process.stdout.write(JSON.stringify({history_run_id:entry.run_id,
  before:entry.published_unique_before,after:entry.published_unique_after,
  added:entry.added_unique,changed:entry.changed_unique,
  rolled:entry.rolled_out_unique,
  removed:entry.removed_unique})+'\n');
