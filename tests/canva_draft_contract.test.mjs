import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
import {CANVA_FORMAT,canvaPageCount,canvaPageAssignments,uniqueEventIds,readCanvaSelection,saveCanvaSelection,selectedEvents,eventDraftRow,classifyCanvaImageCandidates,buildCanvaDraft,buildCanvaPrompt,renderCanvaPromptTemplate,draftAsCsv} from '../site/canva-draft-contract.js';

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
  assert.equal(CANVA_FORMAT.eventDateFontSize,54);
  assert.equal(CANVA_FORMAT.eventThreeLineDateFontSize,52);
  assert.equal(CANVA_FORMAT.coverSuffixFontSize,78);
  assert.equal(CANVA_FORMAT.eventBodyTargetMax,54);
  assert.equal(CANVA_FORMAT.pages,7);
  assert.equal(CANVA_FORMAT.maxPages,17);
  assert.equal(CANVA_FORMAT.maxEvents,30);
  assert.equal(CANVA_FORMAT.eventsPerPage,2);
});
test('selection is deterministic, deduplicated and capped at thirty',()=>{
  const ids=Array.from({length:32},(_,i)=>'e'+i);
  assert.deepEqual(uniqueEventIds(['e0','e0',...ids]),ids.slice(0,30));
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
  assert.ok(buildCanvaPrompt(d).includes('1行タイトルは80〜82px'));
  assert.ok(buildCanvaPrompt(d).includes('汎用OGP・サイトロゴ'));
});

test('exported Canva prompt carries approved hide-frame, cover-count and save rules',()=>{
  const d=buildCanvaDraft([event('a'),event('b')],['a','b'],{coverTitle:'東京23区 週末子連れイベント2選'});
  const p=buildCanvaPrompt(d,readFileSync(new URL('../site/canva-prompt-template-v2.txt',import.meta.url),'utf8'));
  assert.ok(p.includes('表紙タイトル: 東京23区 週末子連れイベント2選'));
  assert.ok(p.includes('2選'));
  assert.ok(p.includes('枠ごと非表示'));
  assert.ok(p.includes('1行に収まる最大の文字サイズを選ぶ'));
  assert.ok(p.includes('コピーの編集transactionをcommit'));
  assert.ok(p.includes('保存済み本体をget_design'));
  assert.ok(p.includes('編集リンク'));
  assert.ok(p.includes('別年の写真を使わず'));
  assert.ok(!p.includes('余分なイベント枠を空欄'));
  assert.ok(!p.includes('保存前に承認を求めてください'));
});

const liveV2=readFileSync(new URL('../site/canva-prompt-template-v2.txt',import.meta.url),'utf8');
const docsV2=readFileSync(new URL('../docs/canva_prompt_template_v2.txt',import.meta.url),'utf8');
test('published Canva prompt and docs mirror remain identical',()=>{
  assert.equal(liveV2,docsV2);
  assert.ok(liveV2.includes('出典：'));
  assert.ok(liveV2.includes('初期目標50〜54px'));
  assert.match(liveV2,/紹介の.*日時は54px|日時は54pxを基準/);
});
test('real clipboard instruction renders all fields and protects absent slots',()=>{
 const d=buildCanvaDraft([event('a'),event('b')],['b','a'],{coverTitle:'東京23区 週末イベント2選'});
 const text=renderCanvaPromptTemplate(liveV2,d);
 assert.ok(text.includes('東京23区 週末イベント2選'));
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
  assert.match(visualQualityV1,/1080×1350px・7〜17ページ/);
  assert.match(visualQualityV1,/投稿画像を直接取得できていない/);
});
test('quality-directed exported prompt includes reproducible typography and image gates',()=>{
 const d=buildCanvaDraft([event('a'),event('b')],['b','a'],{coverTitle:'東京23区 おでかけ2選'});
 const p=renderCanvaPromptTemplate(liveV2,d);
 assert.match(p,/本文は54pxから試し/);
 assert.match(p,/2pxずつ減らす/);
 assert.match(p,/約幅540px/);
 assert.match(p,/写真.*重なり|重なり.*写真/);
 assert.match(p,/同じ基準フォントファミリー/);
 assert.match(p,/画像.*配置.*最終表示/);
 assert.match(p,/全7ページのプレビュー/);
 assert.match(p,/未使用.*非表示/);
 assert.match(p,/共通OGP/);
 assert.match(p,/初期テンプレート・Golden Master・以前の保存版/);
 assert.match(p,/画像専用\/共通\/準備中/);
 assert.ok(p.indexOf('親子ワークショップ b')<p.indexOf('親子ワークショップ a'));
 assert.ok(!p.includes('{{EVENT_BLOCKS}}'));
 for(let i=1;i<=8;i++)assert.match(visualQualityV1,new RegExp('G0'+i+':'));
 assert.match(p,/G01〜G08/);
 assert.match(p,/DAHY1F7Rv_k/);
 assert.match(p,/保存済み本体をget_design/);
 assert.match(p,/日時は54pxを基準/);
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
 assert.match(prompt,/東京23区.*x75 y196/);
 assert.match(prompt,/選.*x829 y735/);
 assert.match(prompt,/日時は54px/);
 assert.match(prompt,/3行だけ52px/);
 assert.match(prompt,/commit後の本体再読取/);
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
 assert.match(canvaPage,/20261024-max30-v1/);
 assert.match(canvaPage,/古いテンプレートへの自動切替は行いません/);
 assert.match(canvaPage,/Yr0CiLUWgATkd1R/);
});
test('golden layout contract locks cover safe areas, fonts and persistence',()=>{
 assert.match(goldenLayoutV1,/DAHY1F7Rv_k/);
 assert.match(goldenLayoutV1,/DAHYo7noxKY/);
 assert.match(goldenLayoutV1,/「東京23区」: x=75, y=196, w=460, font=80/);
 assert.match(goldenLayoutV1,/「選」: x=829, y=735, w=102, font=78/);
 assert.match(goldenLayoutV1,/日時は\*\*54px/);
 assert.match(goldenLayoutV1,/\*\*50〜54px/);
 assert.match(goldenLayoutV1,/get_design.*get_design_content.*get_design_pages/);
});

test('2026-10-24 approved single-line-first title policy survives website clipboard output and externalized mirror',()=>{
  assert.equal(CANVA_FORMAT.eventTitleLayoutPolicy,'single_line_first_max_fit_v1');
  const d=buildCanvaDraft([event('a',{name:'中里の秋さがしミッション！'}),event('b',{name:'長いタイトルを省略せず二行目へ移す場合だけ確認'})],['a','b'],{coverDate:'10/31(土)〜11/1(日)'});
  assert.equal(d.layout.event_title_policy,'single_line_first_max_fit_v1');
  const prompt=renderCanvaPromptTemplate(liveV2,d);
  assert.equal(liveV2,docsV2);
  assert.ok(prompt.includes('【タイトル最適化・2026-10-24承認済み・最優先】'));
  assert.match(prompt,/手動改行を次回へ継承してはならない/);
  assert.match(prompt,/2行にするのは/);
  assert.match(prompt,/不必要な2行が1件でもあればG05不合格/);
  assert.match(prompt,/DAHY1eRnUgU/);
  assert.match(prompt,/DAHY1F7Rv_k/);
  assert.match(prompt,/日時54px/);
  assert.match(prompt,/10\/31\(土\)〜11\/1\(日\)/);
  assert.match(canvaPage,/text\.includes\('【タイトル最適化/);
  assert.match(goldenLayoutV1,/タイトル最適化の承認済み追補/);
  assert.match(visualQualityV1,/不要2行が1件でも残ればG05不合格/);
});

const searchPage=readFileSync(new URL('../site/search.html',import.meta.url),'utf8');
test('selection of 30 events survives storage, share UI, JSON/CSV and dynamic Canva mapping',()=>{
  assert.match(searchPage,/Canva投稿候補 0\/30件/);
  assert.match(searchPage,/最大30件まで選択できます/);
  assert.match(searchPage,/CANVA_FORMAT\.maxEvents/);
  const all=Array.from({length:31},(_,i)=>event('event-'+String(i+1).padStart(2,'0')));
  const ids=all.map(e=>e.id);
  const store=memoryStore();
  saveCanvaSelection(ids,store);
  assert.equal(readCanvaSelection(store).length,30);
  const d=buildCanvaDraft(all,ids,{coverDate:'10/31(土)〜11/1(日)'});
  assert.equal(d.selected_count,30);
  assert.equal(d.events.length,30);
  assert.equal(d.layout.pages,17);
  assert.equal(d.layout.event_pages,15);
  assert.equal(d.layout.added_event_pages,10);
  assert.equal(d.layout.event_slots,30);
  assert.equal(d.autofill_fields.COVER_TITLE.text,'東京23区 週末子連れイベント30選');
  assert.equal(d.autofill_fields.EVENT_30_TITLE.text,all[29].name);
  assert.equal(d.autofill_fields.EVENT_31_TITLE,undefined);
  assert.equal(Object.keys(d.autofill_fields).length,152);
  assert.equal(draftAsCsv(d).trim().split(String.fromCharCode(13,10)).length,2);
  assert.match(canvaPageAssignments(d),/29番：16ページ上段/);
  assert.match(canvaPageAssignments(d),/30番：16ページ下段/);
  const prompt=renderCanvaPromptTemplate(liveV2,d);
  assert.match(prompt,/全17ページ/);
  assert.match(prompt,/追加紹介ページ10ページ/);
  assert.match(prompt,/最終17ページ目は締め/);
  assert.match(prompt,/30番：16ページ下段/);
  assert.ok(!prompt.includes('{{'));
});
test('page counts stay compatible with 7-page Golden Master, add only required pages',()=>{
  for(const [n,want] of [[0,7],[1,7],[9,7],[10,7],[11,8],[12,8],[19,12],[20,12],[21,13],[29,17],[30,17],[31,17]]){
    assert.equal(canvaPageCount(n),want,'selected_count='+n);
  }
  const all=Array.from({length:30},(_,i)=>event('e'+i));
  for(const n of [1,10,11,29,30]){
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
