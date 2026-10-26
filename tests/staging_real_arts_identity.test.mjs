import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {applyVerification,mergeEventsAcrossWeeks} from '../site/app.js';

// Verify both current rolling visibility and immutable historical records.
// A rolled-out week must disappear from the search, NOT from the stored corpus.
const dir=process.argv[2];
if(!dir||!fs.existsSync(path.join(dir,'manifest.json'))) throw Error('real staging data directory required');
const load=file=>JSON.parse(fs.readFileSync(path.join(dir,file),'utf8'));
const manifest=load('manifest.json');
const sourceWeek=sat=>{
  const meta=load(sat+'.json');
  const events=[...(meta.events||[]),...(meta.event_files||[]).flatMap(f=>load(f))];
  const verification=meta.verification_file?load(meta.verification_file):{};
  return {sat,events:applyVerification(events,verification),decision_audit:load(sat+'-decisions.json')};
};
const activeSats=(manifest.weekends||[]).map(w=>w.sat);
const weeks=activeSats.map(sourceWeek);
const arts=ev=>ev.ward==='練馬区'&&String(ev.name).includes('アーツ中村橋');

// The original three source records are always retained, even after the
// oldest week rolls out. Do not weaken this long-term non-deletion invariant.
const protectedSats=['2026-10-24','2026-10-31','2026-11-07'];
const original=protectedSats.map(sourceWeek);
const preserved=original.flatMap(w=>w.events).filter(arts);
assert.equal(preserved.length,3,'three original Arts Nakamurabashi rows must remain in dated files');
const venues=new Set(preserved.map(e=>String(e.venue||'').trim()));
assert.equal(venues.size,3,'original three venue aliases must remain in protected dated records');

// Only those source rows within the rolling search manifest should be visible.
const active=weeks.flatMap(w=>w.events).filter(arts);
const expectedSats=protectedSats.filter(sat=>activeSats.includes(sat));
assert.equal(active.length,expectedSats.length,'active Arts rows must follow rolling manifest without extra/deleted entries');
const visible=mergeEventsAcrossWeeks(weeks).filter(arts);
assert.equal(visible.length,expectedSats.length?1:0,'only one grouped Arts result when active');
if(expectedSats.length){
  assert.deepEqual(visible[0]._week_sats,expectedSats);
  assert.equal(visible[0]._identity_venues.length,expectedSats.length,'visible event must retain all active venue aliases');
}
console.log('STAGING ROLLING + HISTORICAL verified: '+preserved.length+' protected original rows; '+
  active.length+' active rows -> '+visible.length+' visible result(s); archived file intact');
