import assert from 'node:assert/strict';
import {todayJst,visibleQuickPeriods,currentAndFutureWindow,createMultiFilterUI} from '../site/multi-filter-ui.js';
import {saturdayOf,filterEvents} from '../site/app.js';

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
const currentSat=saturdayOf(now),base=new Date(currentSat+'T00:00:00Z');
const weekShift=n=>new Date(base.getTime()+n*86400000).toISOString().slice(0,10);
const oldSat=weekShift(-7);
globalThis.location.search='?d='+oldSat;
const manifest={default:oldSat,rolling_horizon_weeks:6,weekends:Array.from({length:6},(_,i)=>({
  sat:weekShift(-7+i*7),sun:weekShift(-6+i*7),publication_tier:'full'}))};
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


// All-period should begin at this weekend and include events still running.
const actualEnd=weekShift(29);
const currentWindow=currentAndFutureWindow([
 {kind:'weekend',start:oldSat,end:weekShift(-6)},
 {kind:'weekend',start:currentSat,end:weekShift(1)},
 {kind:'weekend',start:weekShift(28),end:actualEnd}
],now);
assert.deepEqual(currentWindow,{start:currentSat,end:actualEnd});
assert.deepEqual(currentAndFutureWindow(periods,'2026-10-14'),{start:'2026-10-17',end:'2026-11-08'});
assert.deepEqual(currentAndFutureWindow(periods,'2026-10-18'),{start:'2026-10-17',end:'2026-11-08'});
assert.deepEqual(currentAndFutureWindow(periods,'2026-10-19'),{start:'2026-10-24',end:'2026-11-08'});
assert.deepEqual(currentAndFutureWindow(periods,'2026-12-01'),{start:'9999-12-31',end:'9999-12-31'});
assert.deepEqual(currentAndFutureWindow([],'2026-10-14'),{start:'9999-12-31',end:'9999-12-31'});
// Explicit previous-week filter has precedence over the default cutoff.
assert.deepEqual(ui.filters().periods,[{start:oldSat,end:weekShift(-6)}]);
assert.deepEqual(ui.filters().dates,[oldSat]);
// Clicking the all-period shortcut removes the historical selection, but not records.
const mockClick=date=>({target:{closest(){return {dataset:{date}}}}});
for(const fn of el('weekTabs').listeners.click)fn(mockClick('all'));
assert.deepEqual(ui.filters().dates,[]);
assert.equal(ui.filters().periods[0].start,currentSat);
assert.equal(ui.filters().periods[0].end,weekShift(29));
assert.equal(el('dateInput').value,'');
assert.match(el('weekTabs').innerHTML,/今週末から/);
const mockEvents=[
 {name:'終了済みイベント',date_start:oldSat,date_end:weekShift(-6)},
 {name:'長期イベント',date_start:oldSat,date_end:weekShift(14)},
 {name:'今週末イベント',date_start:currentSat,date_end:weekShift(1)},
 {name:'未来イベント',date_start:weekShift(21),date_end:weekShift(21)}
];
assert.deepEqual(filterEvents(mockEvents,ui.filters()).map(x=>x.name),
 ['長期イベント','今週末イベント','未来イベント']);
const allWindow=ui.filters().periods;
assert.equal(filterEvents(mockEvents,{periods:allWindow,wards:['杉並区']}).length,0);
el('dateInput').value=oldSat;
for(const fn of el('updateBtn').listeners.click)fn();
assert.deepEqual(ui.filters().dates,[oldSat]);
assert.equal(filterEvents(mockEvents,ui.filters())[0].name,'終了済みイベント');
assert.equal(filterEvents(mockEvents,ui.filters()).length,2);
for(const fn of el('weekTabs').listeners.click)fn(mockClick('all'));
assert.deepEqual(ui.filters().dates,[]);
assert.equal(el('dateInput').value,'');
console.log('All period starts this weekend; historical filters and long-running events preserved');
