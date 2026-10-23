// Canva handoff contract. Read-only with respect to published event data.
// No Canva credentials, tokens, or private information belong in this module.
export const CANVA_FORMAT=Object.freeze({
  schemaVersion:1,
  templateId:'DAHYo7noxKY',
  templateUrl:'https://canva.link/8zgsm5y1cwwgd5e',
  // Golden Master is the user-approved, non-overflowing October 2026 result.
  // Clone it for future drafts; never modify it or the original template.
  goldenMasterId:'DAHY1F7Rv_k',
  goldenMasterUrl:'https://www.canva.com/d/Yr0CiLUWgATkd1R',
  goldenContractUrl:'https://github.com/toodataa-ai/tokyo-family-events-ai/blob/main/docs/canva_golden_layout_contract_v1.md',
  coverFontSize:79,coverCountFontSize:191,coverSuffixFontSize:75,
  coverDateDigitFontSize:126,coverDateUnitFontSize:77,coverDateHyphenFontSize:77,
  coverCaptionFontSize:129,coverSaveFontSize:44,
  coverFixedLabels:Object.freeze({city:'東京',caption:'週末イベント',save:'保存してあとから見返す'}),
  closingReferenceId:'DAHYlmzKyq4',
  closingReferenceUrl:'https://canva.link/uwsg71kb39p2t7c',
  closingReferencePage:7,closingReferencePageId:'PBKb7PtCH0dWRJyg',
  closingExcludedPage:6,closingExcludedPageId:'PBh7x4Vd0Srrb1ly',
  eventBodyFontFamily:'けいふぉんと',
  uniformWhiteCardHeight:true,
  eventTypography:Object.freeze({title:55,titleNumber:68,body:36,venue:28,datetime:36}),
  eventTitleLayoutPolicy:'fixed_55px_wrap_if_needed_v1',
  width:1080,height:1350,pages:7,maxPages:20,maxEvents:36,eventsPerPage:2,
  selectionStorageKey:'tokyo-family-events-canva-selection-v1'
});

export function canvaPageCount(count){
  const n=Math.max(0,Math.min(CANVA_FORMAT.maxEvents,Math.floor(Number(count)||0)));
  return Math.max(CANVA_FORMAT.pages,2+Math.ceil(n/CANVA_FORMAT.eventsPerPage));
}
export function uniqueEventIds(ids,max=CANVA_FORMAT.maxEvents){
  const seen=new Set();
  for(const id of Array.isArray(ids)?ids:[]){
    if(typeof id!=='string'||!id.trim()||id.length>200)continue;
    seen.add(id);
    if(seen.size>=max)break;
  }
  return [...seen];
}
export function readCanvaSelection(storage){
  try{
    const raw=storage?.getItem(CANVA_FORMAT.selectionStorageKey);
    const v=raw?JSON.parse(raw):null;
    return uniqueEventIds(Array.isArray(v)?v:v?.ids);
  }catch{return [];}
}
export function saveCanvaSelection(ids,storage){
  const safe=uniqueEventIds(ids);
  try{storage?.setItem(CANVA_FORMAT.selectionStorageKey,JSON.stringify({version:1,ids:safe}));}
  catch{/* Storage can be disabled; the query-string fallback still works. */}
  return safe;
}
function safeText(v){return typeof v==='string'?v.trim():'';}
function safeUrl(v){
  try{const u=new URL(v);return /^https?:$/.test(u.protocol)?u.href:'';}
  catch{return '';}
}
export function selectedEvents(events,ids){
  const lookup=new Map((Array.isArray(events)?events:[]).filter(e=>e?.id).map(e=>[e.id,e]));
  return uniqueEventIds(ids).map(id=>lookup.get(id)).filter(Boolean);
}
export function eventDraftRow(ev){
  const grade=ev?.family_fit?.overall||ev?.family_fit?.grade||'';
  const verification=ev?.verification?.status||'unverified';
  return {
    id:safeText(ev?.id),title:safeText(ev?.name),ward:safeText(ev?.ward),
    period:safeText(ev?.period),time:safeText(ev?.time),
    venue:safeText(ev?.venue),price:safeText(ev?.price),
    description:safeText(ev?.description),official_url:safeUrl(ev?.official_url||ev?.url),
    image_reference_url:safeUrl(ev?.image),
    verification_status:verification,verification_source:safeUrl(ev?.verification?.source),
    family_fit_grade:grade
  };
}
// Candidate analysis only: a source URL never grants publishing rights.
export function classifyCanvaImageCandidates(rows){
  const counts=new Map();
  for(const r of rows){const url=r.image_reference_url||'';if(url)counts.set(url,(counts.get(url)||0)+1);}
  return rows.map(r=>{
    const url=r.image_reference_url||'';
    let status='missing';
    if(url){
      const path=new URL(url).pathname.toLowerCase();
      if(counts.get(url)>1)status='shared_or_duplicate';
      else if(/(?:^|\/)(?:og|ogp|logo|favicon|default)(?:[._\/-]|$)|\/images\/sns\/|\/meta\/event\//.test(path))status='generic_site_image';
      else {
        try{status=new URL(r.official_url).hostname===new URL(url).hostname?'event_image_candidate':'external_image_requires_review';}
        catch{status='external_image_requires_review';}
      }
    }
    return {...r,image_candidate_status:status,image_use_permission:'unconfirmed'};
  });
}

export function buildCanvaDraft(events,ids,{coverDate=''}={}){
  const rows=classifyCanvaImageCandidates(selectedEvents(events,ids).map(eventDraftRow));
  const title=`東京 週末イベント${rows.length}選`; // Immutable cover wording; changes to selected count only.
  // A long-running first event cannot determine the weekend on the cover.
  // Force explicit confirmation instead of reusing the Golden Master's old date.
  const coverDateText=safeText(coverDate).slice(0,100);
  const fields={COVER_TITLE:{type:'text',text:title},COVER_DATE:{type:'text',text:coverDateText||'未指定（投稿対象の週末の日付を要確認）'}};
  rows.forEach((row,i)=>{
    const key='EVENT_'+String(i+1).padStart(2,'0');
    fields[key+'_TITLE']={type:'text',text:row.title};
    fields[key+'_DATE']={type:'text',text:[row.period,row.time].filter(Boolean).join(' ')};
    fields[key+'_VENUE']={type:'text',text:[row.venue,row.ward&&'（'+row.ward+'）'].filter(Boolean).join('')};
    fields[key+'_DESCRIPTION']={type:'text',text:[row.description,row.price&&'料金：'+row.price].filter(Boolean).join(' ／ ')};
    fields[key+'_SOURCE']={type:'text',text:row.official_url};
  });
  return {
    schema_version:CANVA_FORMAT.schemaVersion,
    draft_type:'canva_carousel_handoff',
    source_site:'https://toodataa-ai.github.io/tokyo-family-events-ai/',
    source_design_id:CANVA_FORMAT.goldenMasterId,
    source_design_url:CANVA_FORMAT.goldenMasterUrl,
    closing_source_design_id:CANVA_FORMAT.closingReferenceId,
    closing_source_design_url:CANVA_FORMAT.closingReferenceUrl,
    closing_source_page:CANVA_FORMAT.closingReferencePage,
    closing_source_page_id:CANVA_FORMAT.closingReferencePageId,
    closing_excluded_page_id:CANVA_FORMAT.closingExcludedPageId,
    original_template_id:CANVA_FORMAT.templateId,
    original_template_url:CANVA_FORMAT.templateUrl,
    golden_layout_contract:CANVA_FORMAT.goldenContractUrl,
    layout:{width:CANVA_FORMAT.width,height:CANVA_FORMAT.height,pages:canvaPageCount(rows.length),base_pages:CANVA_FORMAT.pages,max_pages:CANVA_FORMAT.maxPages,event_pages:canvaPageCount(rows.length)-2,added_event_pages:canvaPageCount(rows.length)-CANVA_FORMAT.pages,event_slots:CANVA_FORMAT.maxEvents,slots_per_page:CANVA_FORMAT.eventsPerPage,event_title_policy:CANVA_FORMAT.eventTitleLayoutPolicy,event_typography_px:{...CANVA_FORMAT.eventTypography},cover_typography_px:{city:CANVA_FORMAT.coverFontSize,date_digit:CANVA_FORMAT.coverDateDigitFontSize,date_unit:CANVA_FORMAT.coverDateUnitFontSize,date_hyphen:CANVA_FORMAT.coverDateHyphenFontSize,caption:CANVA_FORMAT.coverCaptionFontSize,save:CANVA_FORMAT.coverSaveFontSize,count_digit:CANVA_FORMAT.coverCountFontSize,count_suffix:CANVA_FORMAT.coverSuffixFontSize},cover_fixed_labels:{...CANVA_FORMAT.coverFixedLabels},uniform_white_card_height:CANVA_FORMAT.uniformWhiteCardHeight,event_body_font_family:CANVA_FORMAT.eventBodyFontFamily,closing_source_page_id:CANVA_FORMAT.closingReferencePageId,closing_source_page_number:CANVA_FORMAT.closingReferencePage},
    selected_count:rows.length,selection_ids:rows.map(r=>r.id),events:rows,
    image_review:{permission:'unconfirmed',candidate_count:rows.filter(r=>r.image_candidate_status==='event_image_candidate').length,needs_review_count:rows.filter(r=>r.image_candidate_status!=='event_image_candidate').length},
    autofill_fields:fields,
    notes:[
      '承認済みGolden Masterを毎回新しい別IDの作業用コピーに複製。Golden Master・初期テンプレート・過去版は変更禁止。',
      '承認済み7ページの表紙・紹介レイアウトを起点に11〜36件では紹介ページを締めの直前に追加する。1ページ2件、最多20ページ。最後は別参照デザインDAHYlmzKyq4の第7ページそのものを無変更コピーし、同デザインの6ページ目を使わない。',
      'イベント紹介の固定サイズはタイトル55px、イベント番号68px、本文36px、会場28px、日時36px。いずれも拡大縮小禁止。タイトルは55pxのまま折り返し可。',
      'イベント本文は必ずデータに基づき、日時・金額・予約情報を推測で追加しない。',
      '表紙は東京79、日付数字126、月日77、ハイフン77、週末イベント129、保存してあとから見返す44、選数字191、選75pxを固定。紹介の白背景長方形は全件同一高さ、本文けいふぉんとを要素ごとに検品。',
      '各回の表紙の日付は必ず投稿対象週末に差し替える。先頭イベントの長期開催期間や前回の10/24〜25を流用しない。',
      'イベント専用画像を最優先。共有OGP・サイトロゴ・重複画像は自動採用せず、当該公式ページでの掲載とイベントとの適合性を確認して非公開ドラフトの候補としてのみ使用できる。',
      '画像の使用権利は未確認。SNS公開・配布には権利者の許諾確認が必要。',
      '完成したデザインは下書きとして保存し、公開・SNS投稿は行わない。'
    ]
  };
}
export function eventPromptBlocks(draft){
  return (draft.events||[]).map((r,i)=>[
    (i+1)+'. '+r.title,
    '日付: '+r.period+(r.time?'／'+r.time:''),
    '場所: '+r.venue+'（'+r.ward+'）',
    '料金: '+(r.price||'要確認'),
    '説明: '+r.description,
    '公式: '+r.official_url,
    '公式確認根拠URL: '+(r.verification_source||'未確認'),
    '画像出典候補ページ: '+(r.official_url||'未確認'),
    '画像参照: '+(r.image_reference_url||'なし')+'（出典確認・公開権利は別途確認）',
    '画像判定: '+r.image_candidate_status,
    '確認状態: '+r.verification_status
  ].join('\n')).join('\n\n');
}
export function canvaPageAssignments(draft){
  return (draft.events||[]).map((r,i)=>`${i+1}番：${2+Math.floor(i/CANVA_FORMAT.eventsPerPage)}ページ${i%2?'下段':'上段'}／${r.title}`).join('\n');
}
export function assertCanvaTypographyTemplate(template){
  if(typeof template!=='string'||!template.trim())throw new Error('Canva指示テンプレートを読み込めません');
  // Reject stale templates even when a direct caller bypasses the browser's cache guard.
  const markers=['【イベント紹介文字サイズ固定・2026-10-24最優先】','イベントタイトル：**55px固定**','イベント番号：**68px固定**','説明本文：**36px固定**','場所・会場名：**28px固定**','日時：**36px固定**','【固定pxの必須検品／G05に追加】','【保存後の二重検品】','【表紙・白い背景・本文書体・ラストページ絶対契約／2026-10-24最新版／全規則より優先】','「東京」＝**79px固定**','日付の各数字＝**126px固定**','日付の「月」「日」＝**77px固定**','日付の区切りハイフン「-」＝**77px固定**','「週末イベント」＝**129px固定**','「保存してあとから見返す」＝**44px固定**','数字部分＝**191px固定**','「選」＝**75px固定**','本文のフォントファミリー：けいふぉんと','【白い背景長方形・全件同一高さ】','DAHYlmzKyq4','PBKb7PtCH0dWRJyg','PBh7x4Vd0Srrb1ly'];
  const missing=markers.filter(marker=>!template.includes(marker));
  // A correct priority header does not excuse actionable 30/17-era instructions.
  const stale=['1、2、…30の番号','【未使用枠】全7〜17ページ'];
  const conflicting=stale.filter(marker=>template.includes(marker));
  if(conflicting.length)throw new Error('古いCanva仕様が残存: '+conflicting.join(' / '));
  if(missing.length)throw new Error('固定文字サイズ・検品契約が欠落: '+missing.join(' / '));
  return true;
}
export function renderCanvaPromptTemplate(template,draft){
  assertCanvaTypographyTemplate(template);
  const fields={
    TEMPLATE_URL:CANVA_FORMAT.templateUrl,
    GOLDEN_MASTER_URL:CANVA_FORMAT.goldenMasterUrl,
    GOLDEN_MASTER_ID:CANVA_FORMAT.goldenMasterId,
    GOLDEN_CONTRACT_URL:CANVA_FORMAT.goldenContractUrl,
    COVER_DATE:draft.autofill_fields?.COVER_DATE?.text||'未指定（投稿対象週末を要確認）',
    SELECTED_COUNT:String(draft.selected_count),
    PAGE_COUNT:String(draft.layout.pages),
    EVENT_PAGE_COUNT:String(draft.layout.event_pages),
    LAST_EVENT_PAGE:String(draft.layout.event_pages+1),
    EXTRA_PAGE_COUNT:String(draft.layout.added_event_pages),
    MAX_EVENTS:String(CANVA_FORMAT.maxEvents),
    PAGE_ASSIGNMENTS:canvaPageAssignments(draft),
    COVER_TITLE:draft.autofill_fields?.COVER_TITLE?.text||'',
    EVENT_BLOCKS:eventPromptBlocks(draft)
  };
  const output=template.replace(/\{\{(TEMPLATE_URL|GOLDEN_MASTER_URL|GOLDEN_MASTER_ID|GOLDEN_CONTRACT_URL|COVER_DATE|SELECTED_COUNT|PAGE_COUNT|EVENT_PAGE_COUNT|LAST_EVENT_PAGE|EXTRA_PAGE_COUNT|MAX_EVENTS|PAGE_ASSIGNMENTS|COVER_TITLE|EVENT_BLOCKS)\}\}/g,(_,key)=>fields[key]);
  if(/\{\{[A-Z_]+\}\}/.test(output))throw new Error('未定義のCanva指示変数があります');
  return output;
}
// Backward-compatible programmatic helper. The browser handoff uses the canonical .txt.
export function buildCanvaPrompt(draft,template){
  if(template!==undefined)return renderCanvaPromptTemplate(template,draft);
  return [
    'Canva連携で投稿ドラフトを作ってください。',
    '旧元テンプレート（変更禁止）: '+CANVA_FORMAT.templateUrl,
    '表紙・紹介ページ複製元は承認済みGolden Master（変更禁止）: '+CANVA_FORMAT.goldenMasterUrl,
    '最終ページをそのままコピーする参照元（変更禁止）: '+CANVA_FORMAT.closingReferenceUrl+' の7ページ目',
    'レイアウト契約: '+CANVA_FORMAT.goldenContractUrl,
    '必ず元デザインから新しい作業用コピーを作り、以前の保存版を変更しないでください。',
    'イベント紹介のフォント厳守：タイトル55px／イベント番号68px／説明本文36px／場所28px／日時36px。長さ・行数で変更しない。',
    '表紙は東京79、日付数字126、月日77、ハイフン77、週末イベント129、保存してあとから見返す44、選数字191、選75px固定。文言も変更不可。',
    '本文けいふぉんと全件一致、全イベント白い背景四角の高さ統一、最終ページは別参照DAHYlmzKyq4第7ページの無変更コピー、参照6ページ目は使用禁止。',
    '全イベントの5種類すべてのfont_sizeとbounding boxを実測して検品。不一致・取得不能はG05不合格／未検証扱いで、完成と報告しない。commit後の保存本体も可能な限り再照合。',
    '未選択イベント枠は枠ごと非表示。画像には出典：サイト名と参照元URLを記録。',
    '汎用OGP・サイトロゴなどはイベント画像か確認し、画像には出典を付けてください。',
    'Canva品質基準 https://github.com/toodataa-ai/tokyo-family-events-ai/blob/main/docs/canva_visual_quality_contract_v1.md のG01〜G08を確認し全'+draft.layout.pages+'ページプレビューと再チェックを実施。',
    '同じ役割のフォント・文字サイズ・行間を揃え、文字の欠け・要素重なりゼロを確認。フォントファミリー未検証なら未検証と明記。',
    '掲載許諾が不明なら公開・Instagram投稿はしない。',
    '全'+draft.layout.pages+'ページのプレビューを確認し、作業用コピーに確定保存。その後、保存済み本体を読み直して旧イベント残存ゼロ・表紙の文字切れゼロを監査してから編集リンクを返してください。',
    '表紙の日付（元版から流用禁止）：'+(draft.autofill_fields?.COVER_DATE?.text||'未指定、要確認'),
    '選択件数：'+draft.selected_count+'件／全'+draft.layout.pages+'ページ。必要な紹介ページ追加数：'+draft.layout.added_event_pages+'ページ。表紙タイトル：'+(draft.autofill_fields?.COVER_TITLE?.text||''),
    eventPromptBlocks(draft)
  ].join('\n');
}
export function draftAsCsv(draft){
  const columns=Object.keys(draft.autofill_fields);
  const quote=v=>'"'+String(v??'').replace(/"/g,'""').replace(/\r?\n/g,' ')+'"';
  return '\uFEFF'+columns.map(quote).join(',')+'\r\n'+columns.map(k=>quote(draft.autofill_fields[k].text)).join(',')+'\r\n';
}
