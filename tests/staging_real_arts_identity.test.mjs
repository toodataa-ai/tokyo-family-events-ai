import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {applyVerification,mergeEventsAcrossWeeks} from '../site/app.js';

const dir=process.argv[2];
if(!dir||!fs.existsSync(path.join(dir,'manifest.json'))) throw Error('real staging data directory required');
const load=file=>JSON.parse(fs.readFileSync(path.join(dir,file),'utf8'));
const manifest=load('manifest.json');
const weeks=(manifest.weekends||[]).map(w=>{
  const meta=load(w.file);
  const events=[...(meta.events||[]),...(meta.event_files||[]).flatMap(f=>load(f))];
  const verification=meta.verification_file?load(meta.verification_file):{};
  return {sat:w.sat,events:applyVerification(events,verification),decision_audit:load(w.sat+'-decisions.json')};
});
const arts=ev=>ev.ward==='練馬区'&&String(ev.name).includes('アーツ中村橋');
const raw=weeks.flatMap(w=>w.events).filter(arts);
assert.equal(raw.length,3,'expected three protected source rows, never delete original event data');
const visible=mergeEventsAcrossWeeks(weeks).filter(arts);
assert.equal(visible.length,1,'staging SIX-WEEK search must show one Arts Nakamurabashi');
assert.deepEqual(visible[0]._week_sats,['2026-10-24','2026-10-31','2026-11-07']);
assert.equal(visible[0]._identity_venues.length,3,'venue aliases from verified weekly data must be retained');
console.log('STAGING FULL HORIZON verified: Arts Nakamurabashi '+raw.length+' source rows -> '+visible.length+' visible result; no rows removed');
