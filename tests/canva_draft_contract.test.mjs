import assert from 'node:assert/strict';
import {test} from 'node:test';
import {CANVA_FORMAT,uniqueEventIds,readCanvaSelection,saveCanvaSelection,selectedEvents,eventDraftRow,buildCanvaDraft,buildCanvaPrompt,draftAsCsv} from '../site/canva-draft-contract.js';

const event=(id,overrides={})=>({
  id,name:'親子ワークショップ '+id,ward:'中野区',period:'10/24(土)〜10/25(日)',time:'10:00〜15:00',
  venue:'中野区役所',price:'無料',description:'親子で工作を楽しむ。',
  official_url:'https://www.city.tokyo-nakano.lg.jp/events/'+id,
  image:'https://example.org/photo.jpg',
  verification:{status:'announced',source:'https://example.org/evidence'},
  ...overrides
});
function memoryStore(){
  const data=new Map();
  return {getItem:k=>data.get(k),setItem:(k,v)=>data.set(k,v)};
}
test('latest user-approved Canva template and layout stay pinned',()=>{
  assert.equal(CANVA_FORMAT.templateId,'DAHYo7noxKY');
  assert.equal(CANVA_FORMAT.templateUrl,'https://canva.link/8zgsm5y1cwwgd5e');
  assert.equal(CANVA_FORMAT.pages,7);
  assert.equal(CANVA_FORMAT.maxEvents,10);
});
test('selection is deterministic, deduplicated and capped at ten',()=>{
  const ids=Array.from({length:12},(_,i)=>'e'+i);
  assert.deepEqual(uniqueEventIds(['e0','e0',...ids]),ids.slice(0,10));
  const store=memoryStore();
  saveCanvaSelection(['e0','e1','e0'],store);
  assert.deepEqual(readCanvaSelection(store),['e0','e1']);
  store.setItem(CANVA_FORMAT.selectionStorageKey,'not-json');
  assert.deepEqual(readCanvaSelection(store),[]);
});
test('selected events preserve chosen order, without altering source data',()=>{
  const all=[event('a'),event('b')];
  const before=JSON.stringify(all);
  assert.deepEqual(selectedEvents(all,['b','missing','a']).map(e=>e.id),['b','a']);
  buildCanvaDraft(all,['b','a']);
  assert.equal(JSON.stringify(all),before);
});
test('read-only extraction preserves original title and status, no invented claims',()=>{
  const draft=buildCanvaDraft([event('a',{time:'',price:'',verification:{status:'unverified'}})],['a']);
  assert.equal(draft.selected_count,1);
  assert.equal(draft.autofill_fields.EVENT_01_TITLE.text,'親子ワークショップ a');
  assert.equal(draft.autofill_fields.EVENT_01_DATE.text,'10/24(土)〜10/25(日)');
  assert.equal(draft.autofill_fields.EVENT_01_DESCRIPTION.text,'親子で工作を楽しむ。');
  assert.equal(draft.events[0].verification_status,'unverified');
  assert.equal(draft.autofill_fields.EVENT_02_TITLE,undefined);
  assert.equal(draft.events[0].image_reference_url,'https://example.org/photo.jpg');
});
test('unsafe external URLs are dropped and images remain reference-only',()=>{
  const row=eventDraftRow(event('x',{official_url:'javascript:alert(1)',url:'https://safe.example/',image:'data:text/html,bad'}));
  assert.equal(row.official_url,'');
  assert.equal(row.image_reference_url,'');
  const draft=buildCanvaDraft([event('a')],['a']);
  assert.equal(Object.keys(draft.autofill_fields).some(k=>k.includes('IMAGE')),false);
});
test('handoff includes traceable sources and zero publication rights',()=>{
  const draft=buildCanvaDraft([event('a'),event('b')],['b','a']);
  const prompt=buildCanvaPrompt(draft);
  assert.ok(prompt.includes(CANVA_FORMAT.templateUrl));
  assert.ok(prompt.includes('元デザインから新しい作業用コピー'));
  assert.ok(prompt.includes('公開・Instagram投稿はしない'));
  assert.ok(prompt.indexOf('親子ワークショップ b')<prompt.indexOf('親子ワークショップ a'));
});
test('CSV has one header and one row, escapes quotes and protects Japanese UTF-8',()=>{
  const draft=buildCanvaDraft([event('a',{description:'親子"で"工作'})],['a']);
  const csv=draftAsCsv(draft);
  assert.ok(csv.startsWith('\uFEFF'));
  assert.ok(csv.includes('""で""'));
  assert.equal(csv.trim().split(/\r?\n/).length,2);
});
