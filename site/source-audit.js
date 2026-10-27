/* Read-only source audit dashboard. 200 OK is never full event coverage. */
(() => {
 'use strict';
 const $ = id => document.getElementById(id);
 const wrap = $('sourceAuditRows'), search=$('sourceAuditSearch'), filter=$('sourceAuditFilter');
 const statuses = new Set(['checked','partial_error','source_error']);
 let sources=[], audit=null;
 function txt(tag,v,cls) {
   const e=document.createElement(tag);
   if(cls)e.className=cls;
   e.textContent=String(v==null?'':v);
   return e;
 }
 function safe(u) {
   try { const p=new URL(u);return p.protocol==='https:'&&!p.username&&!p.password?p.href:null; }
   catch(_){return null;}
 }
 function a(text,url) {
   const link=safe(url);
   if(!link)return txt('span',text);
   const e=txt('a',text);e.href=link;e.target='_blank';e.rel='noopener noreferrer';return e;
 }
 function valid(x) {
   return x&&x.schema_version===1&&x.read_only===true&&x.registered_source_count===26&&
     x.summary?.full_event_row_parity_verified_by_this_report===0&&
     Array.isArray(x.sources)&&x.sources.length===sources.length&&
     sources.every((s,i)=>{
       const r=x.sources[i];
       return r.source_id===s.id&&statuses.has(r.retrieval_status)&&
         r.event_candidates_total===null&&r.candidate_publication_parity==='未検証'&&
         !(r.retrieval_status==='checked'&&r.pages_checked!==r.pages_expected);
     });
 }
 function name(r) {
   if(!r)return '監査結果なし';
   return r.retrieval_status==='checked'?'登録URLを取得':
     r.retrieval_status==='partial_error'?'一部取得失敗':'取得失敗';
 }
 function header() {
   $('sourceRegistered').textContent=String(sources.length);
   $('sourceChecked').textContent=audit?String(audit.summary.reachable_all_registered_urls):'—';
   $('sourcePartial').textContent=audit?String(audit.summary.partial_errors):'—';
   $('sourceError').textContent=audit?String(audit.summary.source_errors):'—';
   if(!audit){
     $('sourceAuditTime').textContent='全26サイトの最新監査結果はまだ公開されていません。未確認は取得成功ではありません。';
     $('sourceAuditScope').textContent='固定サイトの登録情報のみ表示しています。';
     return;
   }
   const time=new Date(audit.generated_at_jst);
   const date=Number.isNaN(time.getTime())?'日時不明':
     time.toLocaleString('ja-JP',{timeZone:'Asia/Tokyo',year:'numeric',month:'numeric',day:'numeric',
                                  hour:'2-digit',minute:'2-digit'});
   const stale=!Number.isNaN(time.getTime())&&Date.now()-time.getTime()>14*24*3600*1000;
   $('sourceAuditTime').textContent='最終確認：'+date+'（日本時間）'+(stale?'　※14日以上前の記録です':'');
   $('sourceAuditScope').textContent='対象イベント期間：'+audit.horizon.join(' 〜 ')+
      '。候補の採否・掲載照合はこのURL監査とは別の監査です。';
 }
 function card(s,r) {
   const e=document.createElement('article');e.className='source-audit-item';
   const head=txt('div','','source-audit-item-head');
   const title=document.createElement('h3');title.appendChild(a(s.label,s.base_url));
   head.appendChild(title);
   head.appendChild(txt('span',name(r),'source-audit-state '+(r?.retrieval_status||'unavailable')));
   e.appendChild(head);
   const meta=txt('div','','source-audit-meta');
   meta.appendChild(txt('div','種別：'+(r?.group||s.origin)+' / '+(s.required?'必須':'任意')));
   meta.appendChild(txt('div','取得済みURL：'+(r?String(r.pages_checked)+' / '+String(r.pages_expected??'不明'):'未確認')));
   meta.appendChild(txt('div','Web上の参考リンク：'+(Number.isInteger(r?.observed_distinct_link_leads)?
                                   String(r.observed_distinct_link_leads)+'件':'未計測')));
   const proof=txt('div','候補の掲載・除外・重複：未照合（件数不明）');proof.style.fontWeight='700';
   meta.appendChild(proof);
   meta.appendChild(txt('div',r?.detail_adapter?'専用監査：'+r.detail_adapter+'（結果は別ジョブ）':
     '個別イベント照合：追加検証が必要'));
   e.appendChild(meta);
   if(r) {
     const details=txt('details','','source-audit-details');
     details.appendChild(txt('summary','取得ページ・エラーを確認'));
     const ul=document.createElement('ul');
     for(const p of r.source_checks||[]) {
       const li=document.createElement('li');
       li.appendChild(txt('span',p.status==='checked'?'取得：':'失敗：'));
       li.appendChild(a(p.url,p.url));
       if(p.status!=='checked')li.appendChild(txt('span',' / '+(p.error||'不明')));
       ul.appendChild(li);
     }
     for(const err of r.errors||[]) {
       if((r.source_checks||[]).some(p=>p.url===err.url))continue;
       ul.appendChild(txt('li','検査異常：'+(err.error||'不明')));
     }
     if(!ul.children.length)ul.appendChild(txt('li','検査ページの明細なし'));
     details.appendChild(ul);e.appendChild(details);
   }
   return e;
 }
 function render() {
   const q=search.value.trim().toLowerCase(), f=filter.value;
   wrap.replaceChildren();
   const selected=sources.map((s,i)=>({s,r:audit?.sources?.[i]||null}))
     .filter(({s,r})=>(f==='all'||(f==='unavailable'?!r:r?.retrieval_status===f))&&
       (!q||[s.label,s.id,s.origin,r?.group,r?.detail_adapter].some(v=>
         String(v||'').toLowerCase().includes(q))));
   for(const v of selected)wrap.appendChild(card(v.s,v.r));
   if(!selected.length)wrap.appendChild(txt('p','条件に一致する固定サイトはありません。'));
   $('sourceAuditResultCount').textContent=String(selected.length)+' / '+String(sources.length)+' サイトを表示';
 }
 async function init(){
   try {
     const res=await fetch('data/discovery_sources.json',{cache:'no-store'});
     if(!res.ok)throw Error('registry fetch failure');
     const registry=await res.json();
     sources=(registry.explicit_sources||[]).filter(s=>s.enabled===true);
     if(sources.length!==26||new Set(sources.map(s=>s.id)).size!==26)throw Error('registry drift');
     try {
       const check=await fetch('audit/fixed_sources.json',{cache:'no-store'});
       if(check.ok){const result=await check.json();if(valid(result))audit=result;}
     }catch(_){audit=null;}
     header();render();
   }catch(_) {
     $('sourceAuditTime').textContent='固定サイトの登録情報を確認できませんでした。';
     wrap.replaceChildren(txt('p','取得できないため、誤って0件とは表示しません。'));
   }
 }
 search.addEventListener('input',render);
 filter.addEventListener('change',render);
 init();
})();
