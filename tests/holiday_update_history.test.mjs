import assert from 'node:assert/strict';
import {buildEntry,uniqueEvents} from '../tools/holiday_update_history.mjs';

const base='a'.repeat(40), oldManifest={generated:'2026-10-07T00:00:00+09:00'};
const saturdays=['2026-10-17','2026-10-24','2026-10-31','2026-11-07','2026-11-14','2026-11-21'];
const newManifest={generated:'2026-10-13T12:00:00+09:00',default:saturdays[0],
  rolling_horizon_weeks:6,weekends:saturdays.map(s=>({
    sat:s,sun:(()=>{const d=new Date(s+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+1);
      return d.toISOString().slice(0,10)})()}))};
const old=[{events:[
  {name:'終了イベント',date_start:'2026-10-10',date_end:'2026-10-11',venue:'公園'},
  {name:'継続イベント',date_start:'2026-11-07',date_end:'2026-11-08',venue:'館',price:'無料'},
  {name:'変更イベント',date_start:'2026-11-14',date_end:'2026-11-15',venue:'ホール',price:'有料'},
  {name:'掲載取消イベント',date_start:'2026-11-01',date_end:'2026-11-01',venue:'区民会館'},
]}];
const now=[{events:[
  {name:'継続イベント',date_start:'2026-11-07',date_end:'2026-11-08',venue:'館',price:'無料'},
  {name:'変更イベント',date_start:'2026-11-14',date_end:'2026-11-15',venue:'ホール',price:'無料'},
  {name:'新規イベント',date_start:'2026-11-21',date_end:'2026-11-22',venue:'広場'}
]}];
const result=buildEntry(oldManifest,newManifest,old,now,'2026-10-13',base);
assert.equal(result.target_end,'2026-11-23');
assert.equal(result.published_unique_before,4);
assert.equal(result.published_unique_after,3);
assert.equal(result.added_unique,1);
assert.equal(result.changed_unique,1);
assert.equal(result.removed_unique,1);
assert.equal(result.rolled_out_unique,1);
assert.equal(uniqueEvents([...now,now]).size,3);
assert.throws(()=>buildEntry(oldManifest,{...newManifest,generated:oldManifest.generated},old,now,'2026-10-13',base),/timestamp/);
assert.throws(()=>buildEntry(oldManifest,{...newManifest,weekends:newManifest.weekends.slice(0,5)},old,now,'2026-10-13',base),/6-week/);
assert.throws(()=>buildEntry(oldManifest,newManifest,old,now,'2026-10-19',base),/Saturday/);
assert.throws(()=>buildEntry(oldManifest,newManifest,old,now,'2026-10-13','broken'),/SHA/);
console.log('holiday update history generator: OK');
