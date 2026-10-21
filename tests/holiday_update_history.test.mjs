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


import {checkStagingOfficialAddition} from '../tools/holiday_update_history.mjs';
const manualBase='b'.repeat(40);
const manualManifest={generated:'2026-10-19T17:36:28+00:00',default:'2026-10-24',rolling_horizon_weeks:6,
  weekends:['2026-10-24','2026-10-31','2026-11-07','2026-11-14','2026-11-21','2026-11-28'].map(s=>({
    sat:s,sun:new Date(Date.parse(s+'T00:00:00Z')+86400000).toISOString().slice(0,10),
    file:s+'.json',count:1}))};
const oldRows=manualManifest.weekends.map(w=>({sat:w.sat,events:[{id:'prior-'+w.sat,ward:'練馬区',name:'保存対象',date_start:w.sat,date_end:w.sun,official_url:'https://example.jp/original'}]}));
const addedRows=[
  {id:'suginami-official-28531',ward:'杉並区',name:'花と緑の井草祭り',date_start:'2026-10-24',date_end:'2026-10-24',official_url:'https://www.city.suginami.tokyo.jp/s033/event/28531.html'},
  {id:'suginami-official-28567',ward:'杉並区',name:'杉並清掃工場環境フェア2026',date_start:'2026-10-25',date_end:'2026-10-25',official_url:'https://www.city.suginami.tokyo.jp/s104/event/28567.html'},
];
const currentRows=oldRows.map((w,i)=>({...w,events:i===0?[...w.events,...addedRows]:[...w.events]}));
const manualNext={...manualManifest,generated:'2026-10-21T09:00:00+09:00',
  weekends:manualManifest.weekends.map((x,i)=>({...x,count:i===0?3:1}))};
const manualRow={run_id:'staging-suginami-official-two-events-2026-10-21',
  run_type:'staging_manual_official_addition',status:'stage_candidate_only',as_of_jst:'2026-10-21',
  executed_at:'2026-10-21T09:00:00+09:00',base_data_production_sha:manualBase,
  target_start:'2026-10-24',target_end:'2026-10-25',
  added_weekly_records:2,changed_existing_records:0,removed_weekly_records:0};
assert.deepEqual(checkStagingOfficialAddition(manualManifest,manualNext,oldRows,currentRows,manualRow,manualBase),
  {added:2,changed:0,removed:0,retained:6});
assert.throws(()=>checkStagingOfficialAddition(manualManifest,manualNext,oldRows,
  currentRows.map((w,i)=>i===1?{...w,events:[]}:w),manualRow,manualBase),/exactly two approved records|event count|preserve/);
assert.throws(()=>checkStagingOfficialAddition(manualManifest,manualNext,oldRows,
  currentRows.map((w,i)=>i===1?{...w,events:[{...w.events[0],price:'changed'}]}:w),manualRow,manualBase),/exactly two approved records/);
assert.throws(()=>checkStagingOfficialAddition(manualManifest,manualNext,oldRows,currentRows,
  {...manualRow,run_type:'holiday_after_update'},manualBase),/not an unpublished/);
console.log('strict incremental event staging history & protected weekly rows: OK');
