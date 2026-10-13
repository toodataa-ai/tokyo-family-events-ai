import assert from 'node:assert/strict';
import {todayJst,visibleQuickPeriods,createMultiFilterUI} from '../site/multi-filter-ui.js';

// Japan-local midnight, not browser timezone or UTC, decides when shortcuts vanish.
assert.equal(todayJst(new Date('2026-10-12T14:59:59Z')),'2026-10-12');
assert.equal(todayJst(new Date('2026-10-12T15:00:00Z')),'2026-10-13');
const periods=[
  {start:'2026-10-10',end:'2026-10-12',kind:'weekend',available:true},
  {start:'2026-10-17',end:'2026-10-18',kind:'weekend',available:true},
  {start:'2026-11-03',end:'2026-11-03',kind:'holiday',available:true},
  {start:'2026-11-07',end:'2026-11-08',kind:'weekend',available:true}
];
assert.deepEqual(visibleQuickPeriods(periods,'2026-10-12').map(p=>p.start),periods.map(p=>p.start));
assert.deepEqual(visibleQuickPeriods(periods,'2026-10-13').map(p=>p.start),['2026-10-17','2026-11-03','2026-11-07']);
assert.deepEqual(visibleQuickPeriods(periods,'2026-11-04').map(p=>p.start),['2026-11-07']);
assert.equal(periods.length,4,'shortcut display must not mutate source events/periods');

const elements=new Map();
function el(id){
  if(!elements.has(id)){
    const o={innerHTML:'',textContent:'',value:'',style:{},open:false,listeners:{},
      addEventListener(event,fn){(this.listeners[event]??=[]).push(fn)},
      querySelector(){return {addEventListener(){},focus(){}}}};
    elements.set(id,o);
  }
  return elements.get(id);
}
globalThis.document={getElementById:el,addEventListener(){}};
globalThis.location={search:'?d=2026-10-10'};
// Use 2026-10-14 locally but manifest periods need to be relative to runtime now.
const now=todayJst(),p=new Date(now+'T00:00:00Z');
const shift=n=>new Date(p.getTime()+n*86400000).toISOString().slice(0,10);
const oldSat=shift(-7),currentSat=shift(0);
globalThis.location.search='?d='+oldSat;
const manifest={default:oldSat,rolling_horizon_weeks:6,weekends:Array.from({length:6},(_,i)=>({
  sat:shift(-7+i*7),sun:shift(-6+i*7),publication_tier:'full'}))};
const ui=createMultiFilterUI({manifest,registry:{},onChange(){},getData:()=>null});
ui.renderWeekTabs();
assert(!el('weekTabs').innerHTML.includes('data-date="'+oldSat+'"'),'completed week must not appear as shortcut');
assert(el('weekTabs').innerHTML.includes('data-date="'+currentSat+'"'),'upcoming date shortcut remains');
assert(el('weekTabs').innerHTML.includes('data-date="all"'),'all-periods shortcut remains');
assert.deepEqual(ui.filters().dates,[oldSat],'historical URL date selection remains supported');
assert.equal(el('dateInput').value,oldSat,'historical URL shows date in picker');
// Past dates can still be applied manually and are preserved for review.
el('dateInput').value=oldSat;
for(const fn of el('updateBtn').listeners.click)fn();
assert.deepEqual(ui.filters().dates,[oldSat]);
assert.equal(el('dateInput').value,oldSat);
assert.equal(ui.filters().periods[0].start,oldSat);
assert.match(el('selectedHint').textContent,/日付指定/);
console.log('Past period shortcut hidden while URL/date filtering and all-period search remain available');
