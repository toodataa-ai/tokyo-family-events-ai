import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
import {orderedCanvaIds,insertionIndexForPointer} from '../site/canva-fluid-sort.js';
import {CANVA_FORMAT,canvaPageCount,canvaPageAssignments,uniqueEventIds,readCanvaSelection,saveCanvaSelection,moveCanvaSelection,selectedEvents,eventDraftRow,classifyCanvaImageCandidates,buildCanvaDraft,buildCanvaPrompt,renderCanvaPromptTemplate,assertCanvaTypographyTemplate,draftAsCsv} from '../site/canva-draft-contract.js';

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
  assert.equal(CANVA_FORMAT.goldenMasterId,'DAHY1F7Rv_k');
  assert.equal(CANVA_FORMAT.goldenMasterUrl,'https://www.canva.com/d/Yr0CiLUWgATkd1R');
  assert.deepEqual(CANVA_FORMAT.eventTypography,{title:55,titleNumber:68,body:36,venue:28,datetime:36});
  assert.equal(CANVA_FORMAT.coverSuffixFontSize,75);
  assert.equal(CANVA_FORMAT.coverFontSize,79);
  assert.equal(CANVA_FORMAT.coverCountFontSize,191);
  assert.equal(CANVA_FORMAT.coverDateDigitFontSize,126);
  assert.equal(CANVA_FORMAT.coverDateUnitFontSize,77);
  assert.equal(CANVA_FORMAT.coverDateHyphenFontSize,77);
  assert.equal(CANVA_FORMAT.coverCaptionFontSize,129);
  assert.equal(CANVA_FORMAT.coverSaveFontSize,44);
  assert.equal(CANVA_FORMAT.eventBodyFontFamily,'けいふぉんと');
  assert.equal(CANVA_FORMAT.closingReferenceId,'DAHYlmzKyq4');
  assert.equal(CANVA_FORMAT.closingReferencePageId,'PBKb7PtCH0dWRJyg');
  assert.equal(CANVA_FORMAT.pages,7);
  assert.equal(CANVA_FORMAT.maxPages,20);
  assert.equal(CANVA_FORMAT.maxEvents,36);
  assert.equal(CANVA_FORMAT.eventsPerPage,2);
});
test('selection is deterministic, deduplicated and capped at thirty-six',()=>{
  const ids=Array.from({length:40},(_,i)=>'e'+i);
  assert.deepEqual(uniqueEventIds(['e0','e0',...ids]),ids.slice(0,36));
  const store=memoryStore();
  saveCanvaSelection(['e0','e1','e0'],store);
  assert.deepEqual(readCanvaSelection(store),['e0','e1']);
  store.setItem(CANVA_FORMAT.selectionStorageKey,'not-json');
  assert.deepEqual(readCanvaSelection(store),[]);
});
test('one-step Canva move to any position preserves all items and exported order',()=>{
  const ids=Array.from({length:36},(_,i)=>'evt'+(i+1));
  const moved=moveCanvaSelection(ids,19,2);
  assert.equal(moved[2],'evt20');
  assert.equal(moved[3],'evt3');
  assert.equal(moved.length,36);
  assert.deepEqual(new Set(moved),new Set(ids));
  assert.equal(ids[19],'evt20','source selection is not mutated');
  assert.deepEqual(moveCanvaSelection(moved,2,35).slice(-1),['evt20']);
  assert.deepEqual(moveCanvaSelection(ids,-1,7),ids);
  const all=ids.map(id=>event(id));
  const draft=buildCanvaDraft(all,moved);
  assert.equal(draft.events[2].id,'evt20');
  assert.equal(draft.autofill_fields.EVENT_03_TITLE.text,event('evt20').name);
  assert.match(canvaPage,/data-position="1"/);
  assert.doesNotMatch(canvaPage,/draggable="true"/,'native drag is not touch-friendly');
  assert.match(canvaPage,/id="canvaListViewport"/);
  assert.match(canvaPage,/id="canvaFocusToggle"/);
  assert.match(canvaPage,/id="canvaAssistToggle"/);
});
test('compact fluid sorter retains source order and supports all 36 drop positions',()=>{
  const source=readFileSync(new URL('../site/canva-fluid-sort.js',import.meta.url),'utf8');
  const style=readFileSync(new URL('../site/canva-draft.css',import.meta.url),'utf8');
  assert.deepEqual([0,9,20,100].map(y=>insertionIndexForPointer([10,20,30],y)),[0,0,2,3]);
  const example={children:[{dataset:{id:'a'},matches:()=>true},{dataset:{id:'b'},matches:()=>true}]};
  assert.deepEqual(orderedCanvaIds(example),['a','b']);
  for(const marker of ['pointerdown','pointermove','pointerup','pointercancel','requestAnimationFrame','scrollTop','setPointerCapture','onCommit','translate3d']){
    assert.ok(source.includes(marker),'fluid gesture must use '+marker);
  }
  assert.ok(style.includes('touch-action:none'),'iPhone gesture must disable browser pan on the handle');
  assert.match(style,/\.canva-item\{grid-template-columns:44px 24px minmax\(0,1fr\) auto;min-height:46px/,'iPhone rows are tall enough for a large drag target');
  assert.match(style,/\.canva-drag-handle\{display:grid;min-width:44px;width:44px;height:44px;font-size:27px\}/,'iPhone drag handle has a minimum 44px touch target');
  assert.match(style,/\.canva-item-title\{font-size:13\.5px\}/,'title readability improves without adding a second row');
  assert.ok(style.includes('canva-sort-focus'),'fullscreen sorting style is available');
  assert.ok(style.includes('.canva-item-title'),'title-only compact layout exists');
  assert.doesNotMatch(canvaPage,/<small>\$\{escapeHtml\(ev\.ward\)\}/);
  assert.match(canvaPage,/span class="canva-item-title"/);
  assert.match(canvaPage,/createFluidCanvaSorter/);
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
  assert.match(draft.autofill_fields.COVER_DATE.text,/未指定/);
  assert.equal(draft.source_design_id,CANVA_FORMAT.goldenMasterId);
  assert.equal(draft.original_template_id,CANVA_FORMAT.templateId);
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

test('image screening blocks shared banners, generic site OG logos, and unknown permissions',()=>{
  const same='https://www.metro.tokyo.lg.jp/2026/10/images/shared.jpg';
  const e=[
    event('a',{image:'https://www.city.toshima.lg.jp/shared/site_rn2025/images/sns/logo.jpg'}),
    event('b',{image:same}),
    event('c',{image:same}),
    event('d',{image:'https://example.org/image.jpg'})
  ];
  const d=buildCanvaDraft(e,['a','b','c','d']);
  assert.deepEqual(d.events.map(r=>r.image_candidate_status),['generic_site_image','shared_or_duplicate','shared_or_duplicate','external_image_requires_review']);
  assert.equal(d.image_review.permission,'unconfirmed');
  assert.equal(Object.keys(d.autofill_fields).some(x=>x.endsWith('_IMAGE')),false);
});
test('organiser-specific image candidates are not assumed licensed for publication',()=>{
  const e=event('a',{official_url:'https://sp.minato-kagaku.tokyo/event-2026autumnexhibition/',image:'https://sp.minato-kagaku.tokyo/wp-content/uploads/2026/08/banner.jpg'});
  const d=buildCanvaDraft([e],['a']);
  assert.equal(d.events[0].image_candidate_status,'event_image_candidate');
  assert.equal(d.events[0].image_use_permission,'unconfirmed');
  assert.ok(buildCanvaPrompt(d).includes('タイトル55px／イベント番号68px／説明本文36px／場所28px／日時36px'));
  assert.ok(buildCanvaPrompt(d).includes('汎用OGP・サイトロゴ'));
});

test('exported Canva prompt carries approved hide-frame, cover-count and save rules',()=>{
  const d=buildCanvaDraft([event('a'),event('b')],['a','b'],{coverTitle:'無効な上書き指示'});
  const p=buildCanvaPrompt(d,readFileSync(new URL('../site/canva-prompt-template-v2.txt',import.meta.url),'utf8'));
  assert.ok(p.includes('表紙タイトル: 東京 週末イベント2選'));
  assert.ok(p.includes('2選'));
  assert.ok(p.includes('枠ごと非表示'));
  assert.ok(p.includes('【イベント紹介文字サイズ固定・2026-10-24最優先】'));
  assert.ok(p.includes('55pxのままで自然に改行'));
  assert.ok(p.includes('【保存後の二重検品】'));
  assert.ok(p.includes('コピー編集transactionをcommit'));
  assert.ok(p.includes('保存済み本体をget_design'));
  assert.ok(p.includes('編集URL'));
  assert.ok(p.includes('別年の写真を使わず'));
  assert.ok(!p.includes('余分なイベント枠を空欄'));
  assert.ok(!p.includes('保存前に承認を求めてください'));
});

const liveV2=readFileSync(new URL('../site/canva-prompt-template-v2.txt',import.meta.url),'utf8');
const docsV2=readFileSync(new URL('../docs/canva_prompt_template_v2.txt',import.meta.url),'utf8');
test('published Canva prompt and docs mirror remain identical',()=>{
  assert.equal(liveV2,docsV2);
  assert.ok(liveV2.includes('出典：'));
  assert.ok(liveV2.includes('日時：**36px固定**'));
  assert.ok(liveV2.includes('説明本文：**36px固定**'));
  assert.match(liveV2,/1、2、…36の番号/);
  assert.match(liveV2,/【未使用枠】全7〜20ページ/);
  assert.doesNotMatch(liveV2,/1、2、…30の番号/);
  assert.doesNotMatch(liveV2,/【未使用枠】全7〜17ページ/);
  assert.match(liveV2,/けいふぉんと.*Golden Masterの異なる書体を引き継がない/);
  assert.match(liveV2,/スラッシュ区切りでも.*固定サイズ別要素/);
});
test('real clipboard instruction renders all fields and protects absent slots',()=>{
 const d=buildCanvaDraft([event('a'),event('b')],['b','a'],{coverTitle:'東京23区 週末イベント2選'});
 const text=renderCanvaPromptTemplate(liveV2,d);
 assert.ok(text.includes('東京 週末イベント2選'));
 assert.ok(text.includes('2選'));
 assert.ok(text.includes('枠ごと非表示'));
 assert.ok(text.includes('出典：'));
 assert.ok(text.includes('日時・料金・予約条件'));
 assert.ok(text.indexOf('親子ワークショップ b')<text.indexOf('親子ワークショップ a'));
 assert.ok(!text.includes('{{'));
 assert.throws(()=>renderCanvaPromptTemplate('',d));
});

const visualQualityV1=readFileSync(new URL('../docs/canva_visual_quality_contract_v1.md',import.meta.url),'utf8');
test('Instagram example is a qualified reference, never a secretly changed template',()=>{
  assert.match(liveV2,/https:\/\/www\.instagram\.com\/p\/Dev8XdMHRvr\//);
  assert.match(liveV2,/取得できない場合は見た目を推測/);
  assert.match(liveV2,/https:\/\/canva\.link\/8zgsm5y1cwwgd5e|\{\{TEMPLATE_URL\}\}/);
  assert.match(visualQualityV1,/DAHYo7noxKY/);
  assert.match(visualQualityV1,/1080×1350px・7〜20ページ/);
  assert.match(visualQualityV1,/投稿画像を直接取得できていない/);
});
test('quality-directed exported prompt includes reproducible typography and image gates',()=>{
 const d=buildCanvaDraft([event('a'),event('b')],['b','a'],{coverTitle:'東京23区 おでかけ2選'});
 const p=renderCanvaPromptTemplate(liveV2,d);
 assert.match(p,/本文36px、会場28px、日時36px/);
 assert.match(p,/イベント番号：\*\*68px固定\*\*/);
 assert.match(p,/約幅540px/);
 assert.match(p,/写真.*重なり|重なり.*写真/);
 assert.match(p,/説明本文だけは必ず「けいふぉんと」/);
 assert.match(p,/画像.*配置.*最終表示/);
 assert.match(p,/全7ページを実画像で目視/);
 assert.match(p,/未使用.*非表示/);
 assert.match(p,/共通OGP/);
 assert.match(p,/初期テンプレート・Golden Master・以前の保存版/);
 assert.match(p,/参照元.*7ページ|参照デザイン.*7ページ/);
 assert.ok(p.indexOf('親子ワークショップ b')<p.indexOf('親子ワークショップ a'));
 assert.ok(!p.includes('{{EVENT_BLOCKS}}'));
 for(let i=1;i<=8;i++)assert.match(visualQualityV1,new RegExp('G0'+i+':'));
 assert.match(p,/G01〜G08/);
 assert.match(p,/DAHY1F7Rv_k/);
 assert.match(p,/保存済み本体をget_design/);
 assert.match(p,/日時：\*\*36px固定\*\*/);
 assert.match(p,/出典：サイト名/);
 assert.match(p,/画像出典候補ページ:/);
 assert.match(p,/公式確認根拠URL:/);
 assert.match(p,/Instagram投稿はしない/);
});

const goldenLayoutV1=readFileSync(new URL('../docs/canva_golden_layout_contract_v1.md',import.meta.url),'utf8');
const canvaPage=readFileSync(new URL('../site/canva.html',import.meta.url),'utf8');
test('next prompt pins the saved golden master rather than rebuilding from old template',()=>{
 const draft=buildCanvaDraft([event('a')],['a'],{coverDate:'10/31(土)〜11/1(日)'});
 assert.equal(draft.source_design_id,'DAHY1F7Rv_k');
 assert.equal(draft.original_template_id,'DAHYo7noxKY');
 assert.equal(draft.autofill_fields.COVER_DATE.text,'10/31(土)〜11/1(日)');
 const prompt=renderCanvaPromptTemplate(liveV2,draft);
 assert.match(prompt,/制作するデザイン|コピー元|レイアウト正本/);
 assert.match(prompt,/DAHY1F7Rv_k/);
 assert.match(prompt,/10\/31\(土\)〜11\/1\(日\)/);
 assert.match(prompt,/「東京」79px/);
 assert.match(prompt,/「選」75px/);
 assert.match(prompt,/タイトル：\*\*55px固定\*\*/);
 assert.match(prompt,/3行になっても36px/);
 assert.match(prompt,/commit後.*保存済み/);
 assert.match(prompt,/以前の保存版/);
 assert.doesNotMatch(prompt,/\{\{[A-Z_]+\}\}/);
});
test('draft never invents cover date using first long-running event',()=>{
 const d=buildCanvaDraft([event('a',{period:'9/16〜11/8'})],['a']);
 assert.match(d.autofill_fields.COVER_DATE.text,/未指定/);
 assert.ok(!d.autofill_fields.COVER_DATE.text.includes('9/16'));
 const p=renderCanvaPromptTemplate(liveV2,d);
 assert.match(p,/未指定/);
 assert.match(p,/流用禁止/);
});
test('site uses uncached pinned instruction with explicit date entry and protections',()=>{
 assert.match(canvaPage,/id="canvaCoverDate"/);
 assert.match(canvaPage,/canvaCoverDate'\)\.value/);
 assert.match(canvaPage,/20261024-fixed-cover-36-v1/);
 assert.match(canvaPage,/古いテンプレートへの自動切替は行いません/);
 assert.match(canvaPage,/Yr0CiLUWgATkd1R/);
});
test('golden layout contract locks cover safe areas, fonts and persistence',()=>{
 assert.match(goldenLayoutV1,/DAHY1F7Rv_k/);
 assert.match(goldenLayoutV1,/DAHYo7noxKY/);
 assert.match(goldenLayoutV1,/「東京」79px固定/);
 assert.match(goldenLayoutV1,/「選」75px固定/);
 assert.match(goldenLayoutV1,/日時は\*\*36px固定/);
 assert.match(goldenLayoutV1,/本文は\*\*36px固定/);
 assert.match(goldenLayoutV1,/get_design.*get_design_content.*get_design_pages/);
});

test('2026-10-24 typography is fixed for introductions and latest cover typography',()=>{
  assert.equal(CANVA_FORMAT.eventTitleLayoutPolicy,'fixed_55px_wrap_if_needed_v1');
  const d=buildCanvaDraft([event('a',{name:'中里の秋さがしミッション！'}),event('b')],['a','b'],{coverDate:'10/31(土)〜11/1(日)'});
  assert.deepEqual(d.layout.event_typography_px,{title:55,titleNumber:68,body:36,venue:28,datetime:36});
  assert.equal(d.layout.event_title_policy,'fixed_55px_wrap_if_needed_v1');
  const p=renderCanvaPromptTemplate(liveV2,d);
  assert.equal(liveV2,docsV2);
  for(const text of ['イベントタイトル：**55px固定**','イベント番号：**68px固定**','説明本文：**36px固定**','場所・会場名：**28px固定**','日時：**36px固定**']){
    assert.ok(p.includes(text),'missing contract: '+text);
  }
  assert.match(p,/1要素でも相違・未確認ならG05 NGまたは未検証/);
  assert.match(p,/保存後の二重検品/);
  assert.match(p,/全イベント枠・全対象テキスト要素/);
  assert.match(p,/サイズの自動最適化、長さに応じた縮小・拡大/);
  assert.match(p,/イベント番号68pxは表紙の「N選」とは別|表紙の「N選」とは別/);
  assert.match(p,/55pxのまま/);
  assert.ok(!p.includes('1行タイトル80〜82px'));
  assert.ok(!p.includes('日時54px'));
  assert.ok(!p.includes('本文50〜54px'));
  assert.match(goldenLayoutV1,/タイトル55px、イベント番号68px、本文36px、場所28px、日時36px/);
  assert.match(visualQualityV1,/G05: 全使用イベント枠/);
  assert.match(canvaPage,/text.includes\('【イベント紹介文字サイズ固定/);
  assert.match(p,/10\/31\(土\)〜11\/1\(日\)/);
  assert.equal(CANVA_FORMAT.coverCountFontSize,191); // latest cover count
  assert.equal(CANVA_FORMAT.coverFontSize,79);
});
test('stale or one-number-wrong external prompt cannot be rendered or copied as valid',()=>{
  const d=buildCanvaDraft([event('a')],['a']);
  assert.equal(assertCanvaTypographyTemplate(liveV2),true);
  for(const [before,after] of [
     ['イベントタイトル：**55px固定**','イベントタイトル：**54px固定**'],
     ['イベント番号：**68px固定**','イベント番号：**65px固定**'],
     ['説明本文：**36px固定**','説明本文：**35px固定**'],
     ['場所・会場名：**28px固定**','場所・会場名：**30px固定**'],
     ['日時：**36px固定**','日時：**38px固定**'],
     ['【固定pxの必須検品／G05に追加】','【検品なし】'],
     ['【保存後の二重検品】','【保存チェックなし】']
  ]){
    assert.throws(()=>renderCanvaPromptTemplate(liveV2.replace(before,after),d),/固定文字サイズ・検品契約が欠落/);
  }
});

const searchPage=readFileSync(new URL('../site/search.html',import.meta.url),'utf8');
test('selection of 36 events survives storage, share UI, JSON/CSV and 20 page Canva mapping',()=>{
  assert.match(searchPage,/Canva投稿候補 0\/36件/);
  assert.match(searchPage,/最大36件まで選択できます/);
  assert.match(searchPage,/CANVA_FORMAT\.maxEvents/);
  const all=Array.from({length:38},(_,i)=>event('event-'+String(i+1).padStart(2,'0')));
  const ids=all.map(e=>e.id);
  const store=memoryStore();
  saveCanvaSelection(ids,store);
  assert.equal(readCanvaSelection(store).length,36);
  const d=buildCanvaDraft(all,ids,{coverDate:'10/31(土)〜11/1(日)'});
  assert.equal(d.selected_count,36);
  assert.equal(d.events.length,36);
  assert.equal(d.layout.pages,20);
  assert.equal(d.layout.event_pages,18);
  assert.equal(d.layout.added_event_pages,13);
  assert.equal(d.layout.event_slots,36);
  assert.deepEqual(d.layout.event_typography_px,{title:55,titleNumber:68,body:36,venue:28,datetime:36});
  assert.equal(d.autofill_fields.COVER_TITLE.text,'東京 週末イベント36選');
  assert.equal(d.autofill_fields.EVENT_36_TITLE.text,all[35].name);
  assert.equal(d.autofill_fields.EVENT_37_TITLE,undefined);
  assert.equal(Object.keys(d.autofill_fields).length,182);
  assert.equal(draftAsCsv(d).trim().split(String.fromCharCode(13,10)).length,2);
  assert.match(canvaPageAssignments(d),/35番：19ページ上段/);
  assert.match(canvaPageAssignments(d),/36番：19ページ下段/);
  const prompt=renderCanvaPromptTemplate(liveV2,d);
  assert.match(prompt,/全20ページ/);
  assert.match(prompt,/追加紹介ページ13ページ/);
  assert.match(prompt,/最終20ページ目は参照デザイン/);
  assert.match(prompt,/36番：19ページ下段/);
  assert.ok(!prompt.includes('{{'));
});
test('page counts stay compatible with 7-page Golden Master, add only required pages',()=>{
  for(const [n,want] of [[0,7],[1,7],[9,7],[10,7],[11,8],[12,8],[19,12],[20,12],[21,13],[29,17],[30,17],[31,18],[35,20],[36,20],[37,20]]){
    assert.equal(canvaPageCount(n),want,'selected_count='+n);
  }
  const all=Array.from({length:36},(_,i)=>event('e'+i));
  for(const n of [1,10,11,29,30,35,36]){
    const d=buildCanvaDraft(all,all.slice(0,n).map(x=>x.id));
    assert.equal(d.layout.pages,canvaPageCount(n));
    assert.equal(d.layout.pages-2,d.layout.event_pages);
    assert.equal(d.layout.pages-7,d.layout.added_event_pages);
    assert.equal(d.events.length,n);
    const p=renderCanvaPromptTemplate(liveV2,d);
    assert.match(p,new RegExp('全'+d.layout.pages+'ページ'));
    assert.ok(!p.includes('{{'));
  }
});

test('QA rules and site cache reject the old adjustable font guidance',()=>{
  assert.match(canvaPage,/20261024-fixed-cover-36-v1/);
  assert.ok(canvaPage.includes("text.includes('タイトル：**55px固定**')"));
  assert.ok(canvaPage.includes("text.includes('イベント番号：**68px固定**')"));
  assert.ok(canvaPage.includes("text.includes('説明本文：**36px固定**')"));
  assert.ok(canvaPage.includes("text.includes('場所・会場名：**28px固定**')"));
  assert.ok(canvaPage.includes("text.includes('日時：**36px固定**')"));
  for(const value of ['55','68','36','28']){
    assert.match(visualQualityV1,new RegExp(value+'px'));
  }
  assert.match(visualQualityV1,/取得不能は未検証|取得できないものは未検証/);
  assert.match(goldenLayoutV1,/再取得/);
  assert.ok(!liveV2.includes('80〜82px'));
  assert.ok(!liveV2.includes('50〜54px'));
  assert.ok(!liveV2.includes('日時54px'));
});

test('36-selection cover is immutable, base plus separate reference closing stays explicit',()=>{
  const e=[event('a'),event('b')],d=buildCanvaDraft(e,['a','b'],{coverTitle:'勝手な表紙',coverDate:'11/7(土)〜11/8(日)'});
  assert.equal(d.autofill_fields.COVER_TITLE.text,'東京 週末イベント2選');
  assert.equal(d.source_design_id,'DAHY1F7Rv_k');
  assert.equal(d.closing_source_design_id,'DAHYlmzKyq4');
  assert.equal(d.closing_source_page,7);
  assert.equal(d.closing_source_page_id,'PBKb7PtCH0dWRJyg');
  assert.equal(d.closing_excluded_page_id,'PBh7x4Vd0Srrb1ly');
  assert.equal(d.layout.event_body_font_family,'けいふぉんと');
  assert.equal(d.layout.uniform_white_card_height,true);
  assert.deepEqual(d.layout.cover_typography_px,{
    city:79,date_digit:126,date_unit:77,date_hyphen:77,caption:129,save:44,count_digit:191,count_suffix:75
  });
  assert.deepEqual(d.layout.cover_fixed_labels,{city:'東京',caption:'週末イベント',save:'保存してあとから見返す'});
  assert.match(canvaPage,/readonly aria-readonly="true"/);
  const p=renderCanvaPromptTemplate(liveV2,d);
  for(const marker of ['「東京」＝**79px固定**','日付の各数字＝**126px固定**','「週末イベント」＝**129px固定**','「保存してあとから見返す」＝**44px固定**','「けいふぉんと」','白い背景','PBKb7PtCH0dWRJyg','PBh7x4Vd0Srrb1ly','DAHYlmzKyq4']){
    assert.ok(p.includes(marker),'missing:'+marker);
  }
  assert.match(p,/第6ページ.*使用禁止|6ページ目.*使用禁止|6ページ目.*使わない/);
  assert.match(p,/commit後/);
});
test('any stale latest cover, font or source-page rule is rejected before export',()=>{
 const d=buildCanvaDraft([event('a')],['a']);
 const cases=[
   ['「東京」＝**79px固定**','「東京」＝**80px固定**'],
   ['日付の各数字＝**126px固定**','日付の各数字＝**125px固定**'],
   ['日付の「月」「日」＝**77px固定**','日付の「月」「日」＝**70px固定**'],
   ['日付の区切りハイフン「-」＝**77px固定**','日付の区切りハイフン「-」＝**79px固定**'],
   ['「週末イベント」＝**129px固定**','「週末イベント」＝**128px固定**'],
   ['「保存してあとから見返す」＝**44px固定**','「保存してあとから見返す」＝**43px固定**'],
   ['数字部分＝**191px固定**','数字部分＝**190px固定**'],
   ['「選」＝**75px固定**','「選」＝**76px固定**'],
   ['本文のフォントファミリー：けいふぉんと','本文のフォントファミリー：別フォント'],
   ['PBKb7PtCH0dWRJyg','OTHER'],
   ['PBh7x4Vd0Srrb1ly','OTHER'],
   ['【白い背景長方形・全件同一高さ】','【背景は自由】']
 ];
 for(const [needle,wrong] of cases){
   assert.ok(liveV2.includes(needle));
   assert.throws(()=>renderCanvaPromptTemplate(liveV2.replace(needle,wrong),d),/固定文字サイズ・検品契約が欠落/);
 }
});

test('36-event prompt rejects hidden actionable 30/17-era instructions even with newest header',()=>{
 const d=buildCanvaDraft([event('a')],['a'],{coverDate:'11/7(土)〜11/8(日)'});
 assert.equal(assertCanvaTypographyTemplate(liveV2),true);
 for(const old of ['1、2、…30の番号','【未使用枠】全7〜17ページ']){
   assert.throws(()=>renderCanvaPromptTemplate(liveV2+'\n'+old,d),/古いCanva仕様が残存/);
 }
 const rendered=renderCanvaPromptTemplate(liveV2,d);
 assert.match(rendered,/【未使用枠】全7〜20ページ/);
 assert.match(rendered,/1、2、…36の番号/);
 assert.match(rendered,/スラッシュ区切りでも/);
 assert.match(rendered,/説明本文のfont_familyだけは最優先/);
});
