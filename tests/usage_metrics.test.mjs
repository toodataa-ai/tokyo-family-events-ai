import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
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
  const bad = await worker.fetch(request('/collect','POST',{event:'arbitrary_event'}),env);
  assert.equal(bad.status,400);
  const leaked = await worker.fetch(request('/collect','POST',{event:'copy_all',clipboard:'private'}),env);
  assert.equal(leaked.status,400);
  for(const event of ['page_home','page_search','nav_copy','copy_field','copy_all','session_start']) {
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
  assert.equal(payload.totals.page_home,1);
  assert.equal(payload.totals.nav_search,0);
  assert.equal(payload.today.copy_field,2);
  assert.match(payload.day_jst,/^\d{4}-\d\d-\d\d$/);
  assert.equal(payload.clipboard,undefined);
  assert.equal(stats.headers.get('Access-Control-Allow-Origin'),origin);
});

test('browser instrumentation is attached only to three visible pages and copy success paths',() => {
  const html = ['index','search','copy'].map(name => fs.readFileSync('site/' + name + '.html','utf8'));
  for (const source of html) assert.match(source,/usage-metrics\.js/);
  assert.match(html[0],/id="siteUsageValues"/);
  assert.match(html[2],/flash\(btn,'✓コピー済'\);window\.SiteMetrics\?\.track\('copy_field'\)/);
  assert.match(html[2],/flash\(btn,'✓コピーしました'\);window\.SiteMetrics\?\.track\('copy_all'\)/);
  const js = fs.readFileSync('site/usage-metrics.js','utf8');
  assert.match(js,/location\.origin === 'https:\/\/toodataa-ai.github\.io'/);
  assert.match(js,/const pageEvent = PAGES\[location\.pathname\]/);
  assert.match(js,/!production/);
  assert.doesNotMatch(js,/navigator\.clipboard\.read|localStorage/);
  const config=JSON.parse(fs.readFileSync('site/metrics-config.json','utf8'));
  assert.equal(config.enabled,false);
  assert.equal(config.endpoint,'');
});

test('storage is strictly aggregated, with no visitor identifiers',() => {
  const schema=fs.readFileSync('analytics/schema.sql','utf8');
  assert.match(schema,/PRIMARY KEY \(day, event\)/);
  assert.doesNotMatch(schema,/ip_address|user_agent|visitor_id|referer|search_query/);
});
