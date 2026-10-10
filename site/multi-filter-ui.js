import {WARDS,holidayPeriodSlots,holidayTabMeta,filterEvents,countsByWard,escapeHtml,serializeEventFilters} from './app.js';

// Shared multi-select UI for event search and copy list.
// Empty selections mean "all". Within a group use OR; across groups use AND.
const GROUPS=[
  {key:'sourceModes',param:'s',title:'取得元',items:[['ai_cross','AI探索'],['explicit','固定サイト']]},
  {key:'ratings',param:'star',title:'子連れオススメ度',items:[['3','★★★'],['2','★★'],['1','★'],['0','評価なし']]},
  {key:'prices',param:'p',title:'料金',items:[['free','無料'],['mixed','無料あり'],['paid','有料'],['unknown','料金要確認']]},
  {key:'environments',param:'e',title:'屋内・屋外',items:[['indoor','屋内'],['outdoor','屋外'],['mixed','屋内・屋外'],['unknown','場所要確認']]},
  {key:'reservations',param:'r',title:'予約・申込',items:[['none','申込不要'],['required','要事前申込'],['partial','一部要申込'],['unknown','申込要確認']]}
];
function validValues(values,allow){return new Set(values.filter(v=>allow.includes(v)));}
function initialState(params,periods){
  const dates=validValues(params.getAll('d'),periods.map(x=>x.start));
  const legacyDate=params.get('date');
  if(!dates.size && legacyDate && legacyDate!=='all'){
    const p=periods.find(x=>legacyDate>=x.start&&legacyDate<=x.end);
    if(p)dates.add(p.start);
  }
  const wards=validValues(params.getAll('w'),WARDS);
  if(!wards.size && WARDS.includes(params.get('ward')))wards.add(params.get('ward'));
  const state={dates,wards};
  for(const group of GROUPS){
    const allowed=group.items.map(x=>x[0]);
    const values=validValues(params.getAll(group.param),allowed);
    if(!values.size){
      if(group.key==='sourceModes' && allowed.includes(params.get('src'))) values.add(params.get('src'));
      if(group.key==='prices' && allowed.includes(params.get('price'))) values.add(params.get('price'));
      if(group.key==='environments' && allowed.includes(params.get('env'))) values.add(params.get('env'));
      if(group.key==='reservations' && allowed.includes(params.get('reserve'))) values.add(params.get('reserve'));
      if(group.key==='ratings'){
        const old=Number(params.get('rec')||0);
        if(old>=1&&old<=3) for(let i=old;i<=3;i++)values.add(String(i));
      }
    }
    state[group.key]=values;
  }
  return state;
}
export function createMultiFilterUI({manifest,registry,onChange,getData}){
  const $=id=>document.getElementById(id);
  const periods=holidayPeriodSlots(manifest,manifest.default);
  const state=initialState(new URLSearchParams(location.search),periods);
  const filters=()=>({
    dates:[...state.dates],wards:[...state.wards],
    ratings:[...state.ratings],prices:[...state.prices],
    environments:[...state.environments],reservations:[...state.reservations],
    sourceModes:[...state.sourceModes],
    periods:periods.filter(x=>state.dates.has(x.start)).map(x=>({start:x.start,end:x.end}))
  });
  function notify(){updateSummary();onChange();}
  function renderWeekTabs(){
    const all=!state.dates.size;
    $('weekTabs').innerHTML=`<button type="button" class="week-tab all-week-tab ${all?'active':''}" data-date="all" aria-pressed="${all}"><b>全期間</b><span>6週間</span></button>`+
      periods.map(period=>{
        const meta=holidayTabMeta(period,manifest),checked=state.dates.has(period.start);
        return `<button type="button" class="week-tab ${checked?'active':''} ${period.available?'':'pending'}" data-date="${period.start}" aria-pressed="${checked}"><b>${checked?'☑':'☐'} ${escapeHtml(meta.primary)}</b><span>${escapeHtml(meta.secondary)}</span></button>`;
      }).join('');
  }
  function renderWardChips(data){
    if(!data)return;
    const base=filterEvents(data.events,{...filters(),wards:[],registry,decisionAudit:data.decision_audit});
    const counts=countsByWard(base),all=!state.wards.size;
    $('chips').innerHTML=`<button type="button" class="chip ${all?'active':''}" data-ward="__all__" aria-pressed="${all}">すべて <span>${base.length}</span></button>`+
      WARDS.map(ward=>{
        const checked=state.wards.has(ward);
        return `<button type="button" class="chip ${checked?'active':''} ${counts[ward]===0?'zero':''}" data-ward="${escapeHtml(ward)}" aria-pressed="${checked}">${checked?'☑':'☐'} ${escapeHtml(ward)} <span>${counts[ward]}</span></button>`;
      }).join('');
  }
  function renderGroups(){
    $('filterGroups').innerHTML=GROUPS.map(group=>`<fieldset class="multi-fieldset">
      <legend>${group.title}</legend><div class="multi-option-grid">${group.items.map(([value,label])=>`
        <label class="multi-option"><input type="checkbox" data-group="${group.key}" value="${value}" ${state[group.key].has(value)?'checked':''}><span>${label}</span></label>`).join('')}</div>
    </fieldset>`).join('')+
    '<p class="multi-help">同じ項目で複数選択した場合は「いずれか」、異なる項目間は「すべて満たす」で検索します。未選択は条件なしです。「AI探索」と「固定サイト」の両方を選ぶと全件対象です。</p>';
  }
  function updateSummary(){
    const parts=[];
    if(state.dates.size)parts.push('日付'+state.dates.size);
    if(state.wards.size)parts.push('区'+state.wards.size);
    for(const group of GROUPS){if(state[group.key].size)parts.push(group.title+state[group.key].size);}
    $('filterSummary').textContent=parts.length?`（${parts.join('・')}）`:'（条件なし）';
    const reset=$('clearFiltersBtn');if(reset)reset.disabled=!parts.length;
    $('selectedHint').textContent=state.dates.size||state.wards.size?'複数選択中。日付・区の「すべて」で個別に解除できます。':'日付と区は複数選択できます。選ばない場合はすべて対象です。';
  }
  function handleWeek(e){
    const button=e.target.closest('button[data-date]');if(!button)return;
    const value=button.dataset.date;
    if(value==='all')state.dates.clear();
    else if(state.dates.has(value))state.dates.delete(value);
    else state.dates.add(value);
    $('dateInput').value='';
    notify();
  }
  function handleWard(e){
    const button=e.target.closest('button[data-ward]');if(!button)return;
    const value=button.dataset.ward;
    if(value==='__all__')state.wards.clear();
    else if(state.wards.has(value))state.wards.delete(value);
    else state.wards.add(value);
    notify();
  }
  function handleDate(){
    const date=$('dateInput').value;
    if(!date){state.dates.clear();notify();return;}
    const period=periods.find(p=>date>=p.start&&date<=p.end);
    if(!period){
      const el=$('msgBox');el.textContent='選択した日付は現在の6週間検索対象外です。';el.style.display='block';return;
    }
    state.dates.add(period.start);
    const el=$('msgBox');el.textContent='';el.style.display='none';
    notify();
  }
  function reset(){
    for(const value of Object.values(state))value.clear();
    $('dateInput').value='';
    $('searchInput').value='';
    renderGroups();notify();
  }
  $('weekTabs').addEventListener('click',handleWeek);
  $('chips').addEventListener('click',handleWard);
  $('filterGroups').addEventListener('change',e=>{
    const input=e.target.closest('input[data-group]');
    if(!input)return;
    const bucket=state[input.dataset.group];
    if(!bucket)return;
    if(input.checked)bucket.add(input.value);else bucket.delete(input.value);
    notify();
  });
  $('updateBtn').addEventListener('click',handleDate);
  $('clearFiltersBtn').addEventListener('click',reset);
  renderGroups();
  updateSummary();
  return {filters,renderWeekTabs,renderWardChips,reset,serialize:(q)=>serializeEventFilters({...filters(),q:q||''}),summary:()=>$('filterSummary').textContent};
}
