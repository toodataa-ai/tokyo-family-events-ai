// Canva handoff contract. Read-only with respect to published event data.
// No Canva credentials, tokens, or private information belong in this module.
export const CANVA_FORMAT=Object.freeze({
  schemaVersion:1,
  templateId:'DAHYo7noxKY',
  templateUrl:'https://canva.link/8zgsm5y1cwwgd5e',
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
export function buildCanvaDraft(events,ids,{coverTitle='東京23区 週末子連れイベント10選'}={}){
  const rows=selectedEvents(events,ids).map(eventDraftRow);
  const title=safeText(coverTitle).slice(0,120)||'東京23区 週末子連れイベント10選';
  const fields={COVER_TITLE:{type:'text',text:title},COVER_DATE:{type:'text',text:rows[0]?.period||''}};
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
    source_design_id:CANVA_FORMAT.templateId,
    source_design_url:CANVA_FORMAT.templateUrl,
    layout:{width:CANVA_FORMAT.width,height:CANVA_FORMAT.height,pages:CANVA_FORMAT.pages,event_slots:CANVA_FORMAT.maxEvents},
    selected_count:rows.length,selection_ids:rows.map(r=>r.id),events:rows,
    autofill_fields:fields,
    notes:[
      '元デザインは変更せず必ずコピーしてから編集する。',
      '7ページ構成は表紙1・イベント2件ずつ5ページ・締め1を基本とする。',
      'イベント本文は必ずデータに基づき、日時・金額・予約情報を推測で追加しない。',
      'タイトル基本72px、長いタイトルは見切れない範囲で64〜68pxを目安に調整する。',
      '写真URLは参照のみ。転載許諾が未確認なら画像を自動取り込みしない。',
      '完成したデザインは下書きとして保存し、公開・SNS投稿は行わない。'
    ]
  };
}
export function buildCanvaPrompt(draft){
  const items=(draft.events||[]).map((r,i)=>[
    (i+1)+'. '+r.title,
    '日付: '+r.period+(r.time?'／'+r.time:''),
    '場所: '+r.venue+'（'+r.ward+'）',
    '料金: '+(r.price||'要確認'),
    '説明: '+r.description,
    '公式: '+r.official_url,
    '画像参照: '+(r.image_reference_url||'なし')+'（許諾未確認の転載禁止）',
    '確認状態: '+r.verification_status
  ].join('\n')).join('\n\n');
  return [
    'Canva連携で投稿ドラフトを作ってください。',
    '使用する元テンプレート（変更禁止）: '+CANVA_FORMAT.templateUrl,
    'レイアウト: 1080×1350px／7ページ／1ページ目表紙／2～6ページ目は各2イベント／7ページ目締め。',
    '必ず元デザインから新しい作業用コピーを作り、コピーにだけ内容を差し込んでください。',
    '前回仕上げた配色・写真枠・配置を保持。タイトルは基本72px、長いもののみ64～68px程度にし、横幅を超えないよう調整。',
    '選択は'+draft.selected_count+'件。10件未満なら未選択枠に古いイベントを残さず、余分なイベント枠を空欄にして確認を求めてください。',
    '主催者写真の掲載許諾が不明な場合、参照URLだけ残して画像は差し替えないでください。',
    '公式情報にない日時、料金、予約情報は創作しない。公開・Instagram投稿はしない。',
    '変更後は全7ページのプレビューを確認し、保存前に承認を求めてください。',
    '以下がサイトで選んだイベント情報です。\n\n'+items
  ].join('\n');
}
export function draftAsCsv(draft){
  const columns=Object.keys(draft.autofill_fields);
  const quote=v=>'"'+String(v??'').replace(/"/g,'""').replace(/\r?\n/g,' ')+'"';
  return '\uFEFF'+columns.map(quote).join(',')+'\r\n'+columns.map(k=>quote(draft.autofill_fields[k].text)).join(',')+'\r\n';
}
