import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import worker, {EVENTS} from '../analytics/worker.mjs';

function memoryDb() {
  const counts = new Map();
  return {
    prepare(sql) {
      return {
        bind(...params) {
          return {
            async run() {
              assert.match(sql, /ON CONFLICT/);
              const [day,event] = params;
              const key = day + '/' + event;
              counts.set(key,(counts.get(key) || 0) + 1);
              return {success:true};
            },
            async all() {
              if (sql.includes('SELECT day, event, count FROM event_counts')) {
                const [start,end] = params;
                return {results:[...counts.entries()]
                  .map(([key,count])=>({day:key.slice(0,10),event:key.slice(11),count}))
                  .filter(row=>row.day>=start&&row.day<=end)
                  .sort((a,b)=>b.day.localeCompare(a.day)||a.event.localeCompare(b.event))};
              }
              const [today] = params;
              const results = EVENTS.map(event => {
                const rows = [...counts.entries()].filter(([key]) => key.endsWith('/' + event));
                return {
                  event,
                  total: rows.reduce((sum,[,n]) => sum + n,0),
                  today: rows.reduce((sum,[key,n]) => sum + (key.startsWith(today + '/') ? n : 0),0)
                };
              });
              return {results};
            }
          };
        }
      };
    }
  };
}
const origin = 'https://toodataa-ai.github.io';
const url = 'https://example.workers.dev';
const request = (path,method,body,allowedOrigin=origin) => new Request(url + path,{
  method,
  headers:{Origin:allowedOrigin,'Content-Type':'text/plain'},
  ...(body === undefined ? {} : {body:JSON.stringify(body)})
});

test('collector is strictly allowlisted and aggregates only anonymous event names',async () => {
  const env = {DB:memoryDb()};
  const blocked = await worker.fetch(request('/collect','POST',{event:'copy_all'},'https://attacker.invalid'),env);
  assert.equal(blocked.status,403);
  assert.equal(blocked.headers.get('Access-Control-Allow-Origin'),null);
  const malformed = await worker.fetch(new Request(url + '/collect', {
    method:'POST',headers:{Origin:origin,'Content-Type':'text/plain'},body:'not json'
  }),env);
  assert.equal(malformed.status,400);
  const bad = await worker.fetch(request('/collect','POST',{event:'arbitrary_event'}),env);
  assert.equal(bad.status,400);
  const leaked = await worker.fetch(request('/collect','POST',{event:'copy_all',clipboard:'private'}),env);
  assert.equal(leaked.status,400);
  for(const event of ['page_home','page_search','nav_copy','copy_field_click','copy_all_click','copy_field','copy_all','session_start']) {
    const result = await worker.fetch(request('/collect','POST',{event}),env);
    assert.equal(result.status,200);
  }
  await worker.fetch(request('/collect','POST',{event:'copy_field'}),env);
  const stats = await worker.fetch(request('/stats','GET'),env);
  assert.equal(stats.status,200);
  const payload = await stats.json();
  assert.equal(payload.schema_version,1);
  assert.equal(payload.totals.copy_field,2);
  assert.equal(payload.totals.copy_all,1);
  assert.equal(payload.totals.copy_field_click,1);
  assert.equal(payload.totals.copy_all_click,1);
  assert.equal(payload.totals.page_home,1);
  assert.equal(payload.totals.nav_search,0);
  assert.equal(payload.today.copy_field,2);
  assert.match(payload.day_jst,/^\d{4}-\d\d-\d\d$/);
  assert.equal(payload.clipboard,undefined);
  assert.equal(stats.headers.get('Access-Control-Allow-Origin'),origin);
});

test('history returns bounded real daily aggregates, never visitor identities or fake missing dates',async () => {
  const env={DB:memoryDb()};
  const create=async event=>{
    const res=await worker.fetch(request('/collect','POST',{event}),env);
    assert.equal(res.status,200);
  };
  await create('page_home');await create('copy_all');await create('page_home');
  const response=await worker.fetch(request('/history?days=30','GET'),env);
  assert.equal(response.status,200);
  const result=await response.json();
  assert.equal(result.schema_version,1);
  assert.equal(result.days,30);
  assert.equal(result.rows.length,1);
  assert.equal(result.rows[0].day,result.day_jst);
  assert.equal(result.rows[0].counts.page_home,2);
  assert.equal(result.rows[0].counts.copy_all,1);
  assert.equal(result.rows[0].counts.nav_search,0);
  assert.equal(result.visitor_id,undefined);
  assert.equal(result.rows[0].ip_address,undefined);
  assert.equal(response.headers.get('Access-Control-Allow-Origin'),origin);
  for (const q of ['?days=999','?days=0','?days=30&visitor=abc','?days=30&days=7']){
    const bad=await worker.fetch(request('/history'+q,'GET'),env);
    assert.equal(bad.status,400);
  }
  const blocked=await worker.fetch(request('/history?days=7','GET',undefined,'https://evil.invalid'),env);
  assert.equal(blocked.headers.get('Access-Control-Allow-Origin'),null);
});

test('site history and own-device controls are staged safely and do not change anonymous database schema',()=>{
  const index=fs.readFileSync('site/index.html','utf8');
  const history=fs.readFileSync('site/usage-history.html','utf8');
  const js=fs.readFileSync('site/usage-history.js','utf8');
  const local=fs.readFileSync('site/self-usage.js','utf8');
  assert.match(index,/id="siteUsageToday"/);
  assert.match(index,/href="usage-history\.html"/);
  for(const p of ['index','search','copy']){
    const html=fs.readFileSync('site/'+p+'.html','utf8');
    assert.match(html,/self-usage\.js/);
    assert.match(html,/usage-metrics\.js/);
    assert.ok(html.indexOf('self-usage.js')<html.indexOf('usage-metrics.js'));
  }
  for(const id of ['usageHistoryRange','usageHistoryRows','usageSelfEnable','usageSelfDisable',
                   'usageSelfClear','usageHistoryTodayViews','usageHistoryAllViews']){
    assert.match(history,new RegExp('id="'+id+'"'));
  }
  assert.match(js,/\/history\?days=/);
  assert.match(js,/history API unavailable|history endpoint|history API|history API unavailable|history API/);
  assert.doesNotMatch(js,/\.innerHTML\s*=/);
  assert.match(local,/localStorage/);
  assert.match(local,/SiteSelfUsage/);
  assert.match(local,/setEnabled/);
  assert.match(local,/https:\/\/toodataa-ai\.github\.io/);
  assert.doesNotMatch(local,/fetch\(|sendBeacon|XMLHttpRequest|visitor_id|document\.cookie/);
  const schema=fs.readFileSync('analytics/schema.sql','utf8');
  assert.doesNotMatch(schema,/visitor_id|user_id|ip_address/);
});

test('browser instrumentation is attached only to three visible pages and copy success paths',() => {
  const html = ['index','search','copy'].map(name => fs.readFileSync('site/' + name + '.html','utf8'));
  for (const source of html) assert.match(source,/usage-metrics\.js/);
  assert.match(html[0],/id="siteUsageValues"/);
  assert.match(html[2],/recordMetric\('copy_field_click'\);try/);
  assert.match(html[2],/flash\(btn,'✓コピー済'\);recordMetric\('copy_field'\)/);
  assert.match(html[2],/flash\(btn,'✓コピーしました'\);recordMetric\('copy_all'\)/);
  const js = fs.readFileSync('site/usage-metrics.js','utf8');
  assert.match(js,/location\.origin === 'https:\/\/toodataa-ai.github\.io'/);
  assert.match(js,/const pageEvent = PAGES\[location\.pathname\]/);
  assert.match(js,/!production/);
  assert.doesNotMatch(js,/navigator\.clipboard\.read|localStorage/);
  const config=JSON.parse(fs.readFileSync('site/metrics-config.json','utf8'));
  assert.equal(typeof config.enabled,'boolean');
  if (config.enabled) {
    assert.match(config.endpoint,/^https:\/\/[a-z0-9.-]+\.workers\.dev$/);
  } else {
    assert.equal(config.endpoint,'');
  }
  assert.match(js,/const production = location\.origin === 'https:\/\/toodataa-ai\.github\.io' && !!pageEvent;/);
  assert.doesNotMatch(js,/staging\/index\.html['"]\s*:\s*'page_home'/);
});

test('storage is strictly aggregated, with no visitor identifiers',() => {
  const schema=fs.readFileSync('analytics/schema.sql','utf8');
  assert.match(schema,/PRIMARY KEY \(day, event\)/);
  assert.doesNotMatch(schema,/ip_address|user_agent|visitor_id|referer|search_query/);
});

test('clipboard still works when the telemetry callback throws',async () => {
  const html=fs.readFileSync('site/copy.html','utf8');
  const extract=name => html.split('\n').find(line => line.startsWith(name));
  const calls=[];
  const errors=[];
  const window={
    SiteMetrics:{track(){throw new Error('telemetry service failed');}},
    __visibleEvents:[{name:'Test'}]
  };
  const context={
    window,
    $(){return {textContent:'copy me'};},
    async writeClipboard(text){calls.push(text);},
    copyAllText(){return 'all fields';},
    flash(btn,label){calls.push(label);},
    showMsg(msg){errors.push(msg);}
  };
  const js=[
    extract('function recordMetric(event)'),
    extract('window.copyOne='),
    extract('window.copyAllCard=')
  ];
  for(const line of js) assert.equal(typeof line,'string');
  vm.runInNewContext(js.join('\n'),context);
  await window.copyOne('id',{});
  await window.copyAllCard(0,{});
  assert.deepEqual(calls,['copy me','✓コピー済','all fields','✓コピーしました']);
  assert.deepEqual(errors,[]);
});

test('opt-in browser usage appears only in local chart overlay and toggling off hides it',async()=>{
  const js=fs.readFileSync('site/usage-history.js','utf8');
  const html=fs.readFileSync('site/usage-history.html','utf8');
  const css=fs.readFileSync('site/usage-history.css','utf8');
  const counts=Object.fromEntries([...EVENTS].map(k=>[k,0]));
  const today={...counts,page_home:10},totals={...counts,page_home:40};
  const nodes=new Map();
  function node(tag='div'){
    return {tag,children:[],style:{},hidden:false,disabled:false,textContent:'',
      replaceChildren(...items){this.children=items;},
      appendChild(item){this.children.push(item);},
      append(...items){this.children.push(...items);},
      addEventListener(name,fn){this['on'+name]=fn;}};
  }
  const get=id=>{if(!nodes.has(id))nodes.set(id,node());return nodes.get(id);};
  get('usageHistoryRange').value='30';
  let on=true;
  const own={'2026-10-28':{page_home:3,page_search:2}},calls=[];
  const fakeFetch=async url=>{
    calls.push(url);
    if(url==='metrics-config.json')return {ok:true,json:async()=>({enabled:true,endpoint:'https://metrics.example.test'})};
    if(url.endsWith('/stats'))return {ok:true,json:async()=>({schema_version:1,day_jst:'2026-10-28',today,totals})};
    if(url.endsWith('/history?days=30'))return {ok:true,json:async()=>({schema_version:1,day_jst:'2026-10-28',days:30,rows:[{day:'2026-10-28',counts:today}]})};
    throw Error('unexpected URL: '+url);
  };
  const self={available:()=>true,enabled:()=>on,get:()=>own,dayJst:()=> '2026-10-28',
    setEnabled:yes=>(on=yes),clear:()=>{delete own['2026-10-28'];}};
  vm.runInNewContext(js,{document:{getElementById:get,createElement:node},
    window:{SiteSelfUsage:self,confirm:()=>true},fetch:fakeFetch,URL,console});
  for(let n=0;n<5;n++)await new Promise(resolve=>setImmediate(resolve));
  const chart=get('usageHistoryChart'),rail=chart.children[0].children[1];
  assert.equal(chart.children.length,1);
  assert.deepEqual(Array.from(rail.children,x=>x.className),
    ['usage-history-visual-bar','usage-history-visual-own-bar']);
  assert.equal(rail.children[0].style.width,'100.0%');
  assert.equal(rail.children[1].style.width,'50.0%');
  assert.equal(get('usageHistoryOwnLegend').hidden,false);
  assert.equal(get('usageHistoryOwnNote').hidden,false);
  assert.equal(get('usageSelfEnable').hidden,true,'already enabled button should not invite re-click');
  assert.equal(get('usageSelfDisable').hidden,false);
  assert.match(get('usageSelfStatus').textContent,/設定保存済み/);
  assert.equal(chart.children[0].children[2].textContent,'10');
  assert.equal(get('usageHistoryRows').children[0].children[1].textContent,'10');
  get('usageSelfDisable').onclick();
  assert.equal(get('usageSelfEnable').hidden,false);
  assert.equal(get('usageSelfDisable').hidden,true);
  get('usageSelfEnable').onclick();
  assert.equal(get('usageSelfEnable').hidden,true);
  assert.equal(get('usageSelfDisable').hidden,false);
  get('usageSelfDisable').onclick();
  assert.equal(get('usageHistoryOwnLegend').hidden,true);
  assert.equal(get('usageHistoryOwnNote').hidden,true);
  assert.equal(chart.children[0].children[1].children.length,1);
  assert.equal(get('usageHistoryRows').children[0].children[1].textContent,'10');
  assert.equal(calls.length,3);
  assert.ok(calls.every(url=>!url.includes('page_home')&&!url.includes('browser')));
  assert.match(html,/id="usageHistoryOwnLegend" hidden/);
  assert.match(css,/\.usage-history-visual-own-bar/);
  assert.doesNotMatch(js,/innerHTML\s*=/);
});

test('staging preview can read only this browser data without recording or changing consent',()=>{
  const src=fs.readFileSync('site/self-usage.js','utf8');
  const store=new Map([
    ['family_events_self_usage_optin_v1','yes'],
    ['family_events_self_usage_daily_v1',JSON.stringify({'2026-10-28':{page_home:3}})]
  ]);
  const localStorage={getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v),
    removeItem:k=>store.delete(k)};
  const preview={location:{origin:'https://toodataa-ai.github.io',
    pathname:'/tokyo-family-events-ai/staging/usage-history.html'},
    localStorage,window:{},Intl,Date};
  vm.runInNewContext(src,preview);
  const api=preview.window.SiteSelfUsage;
  assert.equal(api.available(),true);
  assert.equal(api.enabled(),true);
  assert.equal(api.canWrite(),false);
  assert.equal(api.get()['2026-10-28'].page_home,3);
  const before=JSON.stringify([...store]);
  api.record('page_home');
  assert.equal(api.setEnabled(false),false);
  api.clear();
  assert.equal(JSON.stringify([...store]),before,'staging must never write to browser records');
  const prod={location:{origin:'https://toodataa-ai.github.io',
    pathname:'/tokyo-family-events-ai/usage-history.html'},
    localStorage,window:{},Intl,Date};
  vm.runInNewContext(src,prod);
  assert.equal(prod.window.SiteSelfUsage.canWrite(),true);
  assert.equal(prod.window.SiteSelfUsage.enabled(),true);
});
