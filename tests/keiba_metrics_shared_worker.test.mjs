import test from 'node:test';
import assert from 'node:assert/strict';
import worker, {EVENTS,KEIBA_EVENTS} from '../analytics/worker.mjs';

const ORIGIN='https://toodataa-ai.github.io';
const BASE='https://tokyo-family-events-metrics.tooda-t-aa.workers.dev';
function memoryDb(){
  const eventCounts=new Map(),keibaCounts=new Map(),queries=[];
  const db={
    queries,eventCounts,keibaCounts,
    prepare(sql){
      queries.push(sql);
      const isKeiba=sql.includes('keiba_site_event_counts');
      const map=isKeiba?keibaCounts:eventCounts;
      return {
        params:[],
        bind(...params){this.params=params;return this;},
        async run(){
          if(sql.startsWith('CREATE TABLE IF NOT EXISTS keiba_site_event_counts'))return {success:true};
          assert.match(sql,/INSERT INTO /);
          const [date,event]=this.params;
          const key=date+'/'+event;
          map.set(key,(map.get(key)||0)+1);
          return {success:true};
        },
        async all(){
          const rows=[...map].map(([k,count])=>({day:k.slice(0,10),event:k.slice(11),count}));
          if(sql.includes('GROUP BY event')){
            const [day]=this.params;
            const group=new Map();
            for(const r of rows){
              const v=group.get(r.event)||{event:r.event,total:0,today:0};
              v.total+=r.count;
              if(r.day===day)v.today+=r.count;
              group.set(r.event,v);
            }
            return {results:[...group.values()]};
          }
          const [start,end]=this.params;
          return {results:rows.filter(x=>x.day>=start&&x.day<=end)};
        }
      };
    }
  };
  return db;
}
const req=(path,method='GET',body=null,origin=ORIGIN)=>{
  const headers={Origin:origin};
  if(body)headers['Content-Type']='text/plain';
  return new Request(BASE+path,{method,headers,...(body?{body:JSON.stringify(body)}:{})});
};
const json=async(request,db)=>(await worker.fetch(request,{DB:db})).json();
test('legacy event routes are untouched when /keiba namespace is activated',async()=>{
  const db=memoryDb();
  for(const event of ['page_home','copy_all','session_start']){
    assert.equal((await worker.fetch(req('/collect','POST',{event}),{DB:db})).status,200);
  }
  const before=await json(req('/stats'),db);
  const his=await json(req('/history?days=30'),db);
  assert.deepEqual(Object.keys(before.totals).sort(),EVENTS.slice().sort());
  assert.equal(before.totals.page_home,1);
  assert.equal(his.rows[0].counts.copy_all,1);

  assert.equal((await worker.fetch(req('/keiba/collect','POST',{site:'keiba-notes',event:'page_home'}),{DB:db})).status,200);
  assert.equal((await worker.fetch(req('/keiba/collect','POST',{site:'keiba-notes',event:'session_start'}),{DB:db})).status,200);
  assert.equal((await worker.fetch(req('/keiba/collect','POST',{site:'keiba-notes',event:'page_home'}),{DB:db})).status,200);

  const after=await json(req('/stats'),db);
  const last=await json(req('/history?days=30'),db);
  assert.deepEqual(after,before,'legacy event summary remains byte-for-byte logically identical');
  assert.deepEqual(last,his,'legacy event history remains intact');
  assert.equal(db.eventCounts.size,3);
  assert.equal(db.keibaCounts.size,2);
  assert.ok(db.queries.some(x=>x.startsWith('CREATE TABLE IF NOT EXISTS keiba_site_event_counts')));
  assert.ok(db.queries.every(x=>!x.includes('UPDATE event_counts')&&!x.includes('DELETE FROM')));
  const keiba=await json(req('/keiba/stats'),db);
  assert.equal(keiba.site,'keiba-notes');
  assert.equal(keiba.totals.page_home,2);
  assert.equal(keiba.totals.session_start,1);
  assert.equal(keiba.totals.page_results,0);
  assert.deepEqual(Object.keys(keiba.totals).sort(),KEIBA_EVENTS.slice().sort());
  for(const days of [7,30,90,365]){
    const data=await json(req('/keiba/history?days='+days),db);
    assert.equal(data.site,'keiba-notes');
    assert.equal(data.days,days);
    assert.equal(data.recorded_days,1);
    assert.equal(data.rows[0].counts.page_home,2);
    assert.equal(data.rows[0].counts.session_start,1);
    assert.equal(data.rows[0].counts.page_results,0);
  }
});
test('keiba endpoints are payload and origin isolated',async()=>{
  const db=memoryDb();
  const valid={site:'keiba-notes',event:'page_home'};
  for(const body of [
    {event:'page_home'}, // not a keiba payload
    {site:'tokyo-family-events-ai',event:'page_home'},
    {...valid,visitor_id:'id'},
    {...valid,event:'copy_all'}
  ]){
    const r=await worker.fetch(req('/keiba/collect','POST',body),{DB:db});
    assert.equal(r.status,400);
  }
  assert.equal((await worker.fetch(req('/keiba/collect','POST',valid,'https://malicious.invalid'),{DB:db})).status,403);
  assert.equal((await worker.fetch(req('/collect','POST',valid),{DB:db})).status,400);
  assert.equal((await worker.fetch(req('/keiba/history?days=999'),{DB:db})).status,400);
  assert.equal((await worker.fetch(req('/keiba/history?days=30&x=1'),{DB:db})).status,400);
  const opt=await worker.fetch(req('/keiba/collect','OPTIONS'),{DB:db});
  assert.equal(opt.status,204);
  assert.equal(opt.headers.get('Access-Control-Allow-Origin'),ORIGIN);
  assert.equal(db.eventCounts.size,0);
  assert.equal(db.keibaCounts.size,0);
});
test('separate keiba endpoints cannot read existing event site counts',async()=>{
  const db=memoryDb();
  const day=new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
  db.eventCounts.set(day+'/page_home',125);
  const counts=await json(req('/keiba/stats'),db);
  assert.equal(counts.totals.page_home,0);
  assert.equal(counts.today.page_home,0);
  assert.equal((await json(req('/stats'),db)).totals.page_home,125);
});
