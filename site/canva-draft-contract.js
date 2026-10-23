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
  coverFontSize:80,coverCountFontSize:158,coverSuffixFontSize:78,
  coverCaptionFontSize:82,eventDateFontSize:54,eventThreeLineDateFontSize:52,
  eventBodyTargetMin:50,eventBodyTargetMax:54,
  eventTitleLayoutPolicy:'single_line_first_max_fit_v1',
  width:1080,height:1350,pages:7,maxEvents:10,
  selectionStorageKey:'tokyo-family-events-canva-selection-v1'
});

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

export function buildCanvaDraft(events,ids,{coverTitle='東京23区 週末子連れイベント10選',coverDate=''}={}){
  const rows=classifyCanvaImageCandidates(selectedEvents(events,ids).map(eventDraftRow));
  const title=safeText(coverTitle).slice(0,120)||'東京23区 週末子連れイベント10選';
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
    original_template_id:CANVA_FORMAT.templateId,
    original_template_url:CANVA_FORMAT.templateUrl,
    golden_layout_contract:CANVA_FORMAT.goldenContractUrl,
    layout:{width:CANVA_FORMAT.width,height:CANVA_FORMAT.height,pages:CANVA_FORMAT.pages,event_slots:CANVA_FORMAT.maxEvents,event_title_policy:CANVA_FORMAT.eventTitleLayoutPolicy},
    selected_count:rows.length,selection_ids:rows.map(r=>r.id),events:rows,
    image_review:{permission:'unconfirmed',candidate_count:rows.filter(r=>r.image_candidate_status==='event_image_candidate').length,needs_review_count:rows.filter(r=>r.image_candidate_status!=='event_image_candidate').length},
    autofill_fields:fields,
    notes:[
      '承認済みGolden Masterを毎回新しい別IDの作業用コピーに複製。Golden Master・初期テンプレート・過去版は変更禁止。',
      '7ページ構成は表紙1・イベント2件ずつ5ページ・締め1を基本とする。',
      'イベント紹介タイトルは1行優先。旧版から引き継いだ手動改行を解除し、全文を維持して実フレーム幅で最大サイズを計測。不要な2行禁止、2行は1行で読みやすく収まらない時だけ。表紙と日時54pxは独立。',
      'イベント本文は必ずデータに基づき、日時・金額・予約情報を推測で追加しない。',
      '表紙の東京23区は80px、10選の数字158px・選78px、下部キャッチ82pxを固定。イベント紹介の日時は54px、3行のみ52px例外。本文は50〜54px優先、本文が収まらなければ事実を保った短文化後に縮小。',
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
export function renderCanvaPromptTemplate(template,draft){
  if(typeof template!=='string'||!template.trim())throw new Error('Canva指示テンプレートを読み込めません');
  const fields={
    TEMPLATE_URL:CANVA_FORMAT.templateUrl,
    GOLDEN_MASTER_URL:CANVA_FORMAT.goldenMasterUrl,
    GOLDEN_MASTER_ID:CANVA_FORMAT.goldenMasterId,
    GOLDEN_CONTRACT_URL:CANVA_FORMAT.goldenContractUrl,
    COVER_DATE:draft.autofill_fields?.COVER_DATE?.text||'未指定（投稿対象週末を要確認）',
    SELECTED_COUNT:String(draft.selected_count),
    COVER_TITLE:draft.autofill_fields?.COVER_TITLE?.text||'',
    EVENT_BLOCKS:eventPromptBlocks(draft)
  };
  const output=template.replace(/\{\{(TEMPLATE_URL|GOLDEN_MASTER_URL|GOLDEN_MASTER_ID|GOLDEN_CONTRACT_URL|COVER_DATE|SELECTED_COUNT|COVER_TITLE|EVENT_BLOCKS)\}\}/g,(_,key)=>fields[key]);
  if(/\{\{[A-Z_]+\}\}/.test(output))throw new Error('未定義のCanva指示変数があります');
  return output;
}
// Backward-compatible programmatic helper. The browser handoff uses the canonical .txt.
export function buildCanvaPrompt(draft,template){
  if(template!==undefined)return renderCanvaPromptTemplate(template,draft);
  return [
    'Canva連携で投稿ドラフトを作ってください。',
    '旧元テンプレート（変更禁止）: '+CANVA_FORMAT.templateUrl,
    '今後の複製元は承認済みGolden Master（変更禁止）: '+CANVA_FORMAT.goldenMasterUrl,
    'レイアウト契約: '+CANVA_FORMAT.goldenContractUrl,
    '必ず元デザインから新しい作業用コピーを作り、以前の保存版を変更しないでください。',
    '1行タイトルは80〜82px。イベントの日時は基本54px、3行のみ52px。本文は50〜54pxを優先し、収まらなければ37〜46pxの範囲まで段階調整。表紙は基準版のサイズと位置を維持する。',
    '未選択イベント枠は枠ごと非表示。画像には出典：サイト名と参照元URLを記録。',
    '汎用OGP・サイトロゴなどはイベント画像か確認し、画像には出典を付けてください。',
    'Canva品質基準 https://github.com/toodataa-ai/tokyo-family-events-ai/blob/main/docs/canva_visual_quality_contract_v1.md のG01〜G08を確認し全7ページプレビューと再チェックを実施。',
    '同じ役割のフォント・文字サイズ・行間を揃え、文字の欠け・要素重なりゼロを確認。フォントファミリー未検証なら未検証と明記。',
    '掲載許諾が不明なら公開・Instagram投稿はしない。',
    '全7ページのプレビューを確認し、作業用コピーに確定保存。その後、保存済み本体を読み直して旧イベント残存ゼロ・表紙の文字切れゼロを監査してから編集リンクを返してください。',
    '表紙の日付（元版から流用禁止）：'+(draft.autofill_fields?.COVER_DATE?.text||'未指定、要確認'),
    '選択件数：'+draft.selected_count+'件。表紙タイトル：'+(draft.autofill_fields?.COVER_TITLE?.text||''),
    eventPromptBlocks(draft)
  ].join('\n');
}
export function draftAsCsv(draft){
  const columns=Object.keys(draft.autofill_fields);
  const quote=v=>'"'+String(v??'').replace(/"/g,'""').replace(/\r?\n/g,' ')+'"';
  return '\uFEFF'+columns.map(quote).join(',')+'\r\n'+columns.map(k=>quote(draft.autofill_fields[k].text)).join(',')+'\r\n';
}
