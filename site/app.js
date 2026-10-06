export const WARDS = [
  '千代田区','中央区','港区','新宿区','文京区','台東区','墨田区','江東区','品川区','目黒区','大田区',
  '世田谷区','渋谷区','中野区','杉並区','豊島区','北区','荒川区','板橋区','練馬区','足立区','葛飾区','江戸川区'
];

export const PUBLICATION_TIERS = {
  full:{label:'本番',description:'今週〜2週間先。全掲載イベントを公式確認済み'},
  preview:{label:'先取り',description:'3〜4週間先。公式発表済み、詳細待ちを含む'},
  announcement:{label:'予告',description:'5〜6週間先。日付・会場を公式確認済み'},
  planned:{label:'取得前',description:'ローリング探索の対象。次回更新で取得'}
};

export const VERIFICATION_STATES = {
  verified:{label:'✓ 公式確認済み',className:'verify-ok'},
  announced:{label:'○ 開催発表済み・詳細待ち',className:'verify-announced'},
  unverified:{label:'要確認',className:'verify-pending'}
};

export const FAMILY_FIT_AXES = {
  child_target:'子ども対象度',
  interactivity:'体験性',
  age_fit:'年齢適合',
  stay_flexibility:'滞在自由度',
  burden:'安全・負担',
  cost:'費用負担',
  reservation:'予約難易度',
  family_value:'家族価値'
};

export function isoLocal(d){
  const y=d.getFullYear(), m=String(d.getMonth()+1).padStart(2,'0'), day=String(d.getDate()).padStart(2,'0');
  return `${y}-${m}-${day}`;
}

export function addDays(dateStr,days){
  const [y,m,d]=dateStr.split('-').map(Number);
  return isoLocal(new Date(y,m-1,d+days));
}

export function defaultDate(){
  const t = new Date();
  const wd = t.getDay();
  if(wd === 6 || wd === 0) return isoLocal(t);
  return isoLocal(new Date(t.getFullYear(), t.getMonth(), t.getDate() + (6-wd)));
}

export function saturdayOf(dateStr){
  const [y,m,d] = dateStr.split('-').map(Number);
  const base = new Date(y,m-1,d);
  const wd = base.getDay();
  const diff = wd === 6 ? 0 : wd === 0 ? -1 : 6-wd;
  return isoLocal(new Date(y,m-1,d+diff));
}

export function fmtRange(sat,sun){
  const s=new Date(sat+'T00:00:00'), e=new Date(sun+'T00:00:00');
  const w=['日','月','火','水','木','金','土'];
  return `${s.getFullYear()}/${s.getMonth()+1}/${s.getDate()}(${w[s.getDay()]}) 〜 ${e.getMonth()+1}/${e.getDate()}(${w[e.getDay()]})`;
}

export function shortWeekendLabel(sat){
  const d=new Date(sat+'T00:00:00');
  return `${d.getMonth()+1}/${d.getDate()}`;
}

export function publicationTierMeta(tier){ return PUBLICATION_TIERS[tier] || PUBLICATION_TIERS.planned; }
export function verificationStateMeta(status){ return VERIFICATION_STATES[status] || VERIFICATION_STATES.unverified; }

export function rollingWeekSlots(manifest,anchorSat=''){
  const weeks=Array.isArray(manifest?.weekends)?manifest.weekends:[];
  const bySat=new Map(weeks.map(w=>[w.sat,w]));
  const horizon=Math.max(1,Number(manifest?.rolling_horizon_weeks)||6);
  const anchor=anchorSat || manifest?.default || weeks[0]?.sat || saturdayOf(defaultDate());
  const slots=[];
  for(let i=0;i<horizon;i++){
    const sat=addDays(anchor,i*7);
    const entry=bySat.get(sat)||null;
    const inferredTier=i<2?'full':i<4?'preview':'announcement';
    slots.push({sat,sun:addDays(sat,1),horizon_index:i+1,publication_tier:entry?.publication_tier||inferredTier,entry,available:!!entry});
  }
  return slots;
}

export function normalizeText(value){
  return String(value ?? '').normalize('NFKC').toLocaleLowerCase('ja-JP').replace(/\s+/g,' ').trim();
}

export function familyFitAxisRows(familyFit){
  const axes=familyFit?.axes;
  if(!axes || typeof axes!=='object') return [];
  return Object.entries(FAMILY_FIT_AXES).map(([key,label])=>{
    const item=axes[key];
    return item&&typeof item==='object'?{key,label,grade:item.grade||'unknown',reason:item.reason||''}:null;
  }).filter(Boolean);
}

export function eventSearchText(ev){
  return normalizeText([
    ev.name, ev.ward, ev.venue, ev.description, ev.price, ev.period, ev.time,
    ...(Array.isArray(ev.categories) ? ev.categories : []),
    ev.family_fit?.reason, ev.family_fit?.age, ev.family_fit?.overall,
    ...familyFitAxisRows(ev.family_fit).flatMap(x=>[x.label,x.grade,x.reason]),
    ev.reservation?.note, ev.verification?.note,
    verificationStateMeta(ev.verification?.status).label
  ].filter(Boolean).join(' '));
}

export function filterEvents(events, filters={}){
  const ward = filters.ward || '__all__';
  const q = normalizeText(filters.q || '');
  return (events || []).filter(ev => {
    if(ward !== '__all__' && ev.ward !== ward) return false;
    if(q && !eventSearchText(ev).includes(q)) return false;
    return true;
  });
}

export function countsByWard(events){
  const counts = Object.fromEntries(WARDS.map(w => [w,0]));
  (events || []).forEach(ev => { if(ev.ward in counts) counts[ev.ward] += 1; });
  return counts;
}

export function readFiltersFromUrl(){
  const p = new URLSearchParams(location.search);
  const ward = WARDS.includes(p.get('ward')) ? p.get('ward') : '__all__';
  return { date:p.get('date') || '', ward, q:p.get('q') || '' };
}

export function buildCopyUrl(filters){
  const p = new URLSearchParams();
  if(filters.date) p.set('date', filters.date);
  if(filters.ward && filters.ward !== '__all__') p.set('ward', filters.ward);
  if(filters.q) p.set('q', filters.q);
  const qs = p.toString();
  return 'copy.html' + (qs ? '?' + qs : '');
}

export function applyVerification(events, audit){
  const rows = Array.isArray(audit?.events) ? audit.events : [];
  const byId = new Map(rows.map(row => [row.id,row]));
  return (events || []).map(ev => {
    const row = byId.get(ev.id);
    if(!row) return {...ev,verification:{status:'unverified'}};
    const c = row.corrections && typeof row.corrections === 'object' ? row.corrections : {};
    const merged = {...ev,...c};
    if(c.family_fit) merged.family_fit={...(ev.family_fit||{}),...c.family_fit};
    if(c.reservation) merged.reservation={...(ev.reservation||{}),...c.reservation};
    merged.verification={status:row.status||'unverified',source:row.source||'',source_kind:row.source_kind||'',fields:row.fields||{},note:row.note||'',verified_on:audit?.verified_on||''};
    return merged;
  });
}

export async function loadManifest(){
  const res = await fetch('data/manifest.json',{cache:'no-store'});
  if(!res.ok) throw new Error(`manifest load failed: ${res.status}`);
  return res.json();
}

export async function loadWeekend(manifest,satIso){
  const entry=(manifest.weekends||[]).find(w=>w.sat===satIso);
  if(!entry) return {entry:null,data:null};
  const res=await fetch('data/'+entry.file,{cache:'no-store'});
  if(!res.ok) throw new Error(`weekend load failed: ${res.status}`);
  const data=await res.json();
  data.horizon_index=data.horizon_index || entry.horizon_index || null;
  data.publication_tier=data.publication_tier || entry.publication_tier || 'full';
  const baseEvents=Array.isArray(data.events) ? data.events : [];
  const shardFiles=Array.isArray(data.event_files) ? data.event_files : [];
  if(shardFiles.length){
    const shards=await Promise.all(shardFiles.map(async file=>{
      const r=await fetch('data/'+file,{cache:'no-store'});
      if(!r.ok) throw new Error(`event shard load failed: ${file} ${r.status}`);
      const rows=await r.json();
      if(!Array.isArray(rows)) throw new Error(`event shard is not array: ${file}`);
      return rows;
    }));
    data.events=[...baseEvents,...shards.flat()];
  }else data.events=baseEvents;

  if(data.verification_file){
    const vr=await fetch('data/'+data.verification_file,{cache:'no-store'});
    if(!vr.ok) throw new Error(`verification load failed: ${vr.status}`);
    const audit=await vr.json();
    data.verification=audit;
    data.events=applyVerification(data.events,audit);
  }else{
    data.verification=null;
    data.events=applyVerification(data.events,null);
  }

  if(data.run_file){
    const rr=await fetch('data/'+data.run_file,{cache:'no-store'});
    if(!rr.ok) throw new Error(`run manifest load failed: ${rr.status}`);
    data.run=await rr.json();
  }else data.run=null;

  const decisionFile=data.run?.source_data?.decision_file;
  if(decisionFile){
    const dr=await fetch('data/'+decisionFile,{cache:'no-store'});
    if(!dr.ok) throw new Error(`decision audit load failed: ${dr.status}`);
    data.decision_audit=await dr.json();
  }else data.decision_audit=null;
  return {entry,data};
}

export function escapeHtml(value){
  return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}

export function safeHttpUrl(value){
  try { const u = new URL(String(value || '')); return (u.protocol === 'http:' || u.protocol === 'https:') ? u.href : ''; }
  catch { return ''; }
}
