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
        return `<label class="week-tab ${checked?'active':''} ${period.available?'':'pending'}"><input type="checkbox" data-date="${period.start}" ${checked?'checked':''} aria-label="${escapeHtml(meta.primary)} を選択"><b>${escapeHtml(meta.primary)}</b><span>${escapeHtml(meta.secondary)}</span></label>`;
      }).join('');
  }
  function renderWardChips(data){
    if(!data)return;
    const base=filterEvents(data.events,{...filters(),wards:[],registry,decisionAudit:data.decision_audit});
    const counts=countsByWard(base),all=!state.wards.size;
    $('chips').innerHTML=`<button type="button" class="chip ${all?'active':''}" data-ward="__all__" aria-pressed="${all}">すべて <span>${base.length}</span></button>`+
      WARDS.map(ward=>{
        const checked=state.wards.has(ward);
        return `<label class="chip ${checked?'active':''} ${counts[ward]===0?'zero':''}"><input type="checkbox" data-ward="${escapeHtml(ward)}" ${checked?'checked':''}><span>${escapeHtml(ward)} ${counts[ward]}</span></label>`;
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
    // Reset is available even if only the keyword search is active.
    $('selectedHint').textContent=state.dates.size||state.wards.size?'複数選択中。日付・区の「すべて」で個別に解除できます。':'日付と区は複数選択できます。選ばない場合はすべて対象です。';
  }
  function toggleSet(bucket,value,checked){
    if(checked) bucket.add(value);else bucket.delete(value);
    notify();
  }
  function handleWeek(e){
    const input=e.target.closest('input[data-date]');if(!input)return;
    toggleSet(state.dates,input.dataset.date,input.checked);
  }
  function handleWard(e){
    const input=e.target.closest('input[data-ward]');if(!input)return;
    toggleSet(state.wards,input.dataset.ward,input.checked);
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
  $('weekTabs').addEventListener('change',handleWeek);
  $('weekTabs').addEventListener('click',e=>{
    if(!e.target.closest('button[data-date="all"]'))return;
    state.dates.clear();$('dateInput').value='';notify();
  });
  $('chips').addEventListener('change',handleWard);
  $('chips').addEventListener('click',e=>{
    if(!e.target.closest('button[data-ward="__all__"]'))return;
    state.wards.clear();notify();
  });
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
  const panel=$('filterPanel');
  const closePanel=(focusTrigger=false)=>{
    if(!panel.open)return;
    panel.open=false;
    if(focusTrigger)panel.querySelector('summary')?.focus();
  };
  // On mobile the floating panel covers its own <summary>, so keep an
  // always-visible way to dismiss it without resetting any filter state.
  $('filterCloseBtn').addEventListener('click',()=>closePanel(true));
  $('filterApplyBtn').addEventListener('click',()=>closePanel(true));
  panel.querySelector('.multi-filter-backdrop').addEventListener('click',()=>closePanel());
  document.addEventListener('pointerdown',e=>{
    if(panel.open && !panel.contains(e.target))closePanel();
  });
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'&&panel.open){e.preventDefault();closePanel(true);}
  });
  panel.addEventListener('toggle',()=>{
    if(panel.open)$('dateRefine').open=false;
  });
  $('dateRefine').addEventListener('toggle',()=>{
    if($('dateRefine').open)closePanel();
  });
  renderGroups();
  updateSummary();
  return {filters,renderWeekTabs,renderWardChips,reset,serialize:(q)=>serializeEventFilters({...filters(),q:q||''}),summary:()=>$('filterSummary').textContent};
}
