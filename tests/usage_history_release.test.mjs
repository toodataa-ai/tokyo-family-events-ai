import fs from 'node:fs';
import assert from 'node:assert/strict';
import worker from '../analytics/worker.mjs';

const content=p=>fs.readFileSync(p,'utf8');
const html=content('site/index.html'), history=content('site/usage-history.html'),
      self=content('site/self-usage.js'), metrics=content('site/usage-metrics.js'),
      historyJS=content('site/usage-history.js'),workerJS=content('analytics/worker.mjs');
const config=JSON.parse(content('site/metrics-config.json'));

assert.equal(config.enabled,true,'the live Worker endpoint must remain enabled');
assert.equal(config.endpoint,'https://tokyo-family-events-metrics.tooda-t-aa.workers.dev');
assert.match(html,/id="siteUsageValues"/);
assert.match(html,/id="siteUsageToday"/);
assert.match(html,/href="usage-history\.html"/);
assert.doesNotMatch(html,/href="source-audit\.html"/,
  'staging-only source-audit page must not be unintentionally promoted');
for(const page of ['index','search','copy']) {
 const txt=content('site/'+page+'.html');
 const pos=txt.indexOf('src="self-usage.js');
 assert.ok(pos>=0,'explicit local opt-in script '+page);
 assert.ok(txt.indexOf('src="usage-metrics.js')>pos,'own device record must be loaded first');
 assert.match(txt,/src="usage-metrics\.js\?v=20261028-today"/);
}
assert.match(metrics,/const todaySummary/);
assert.match(metrics,/data\.today/);
assert.match(metrics,/data\.totals/);
assert.match(metrics,/session_start/);
assert.match(workerJS,/path === '\/stats'/);
assert.match(workerJS,/path === '\/history'/);
assert.match(workerJS,/path === '\/collect'/);
assert.match(workerJS,/WHERE day >= \?1 AND day <= \?2/);
assert.doesNotMatch(content('analytics/schema.sql'),/visitor_id|user_id|ip_address/);
assert.match(self,/SiteSelfUsage/);
assert.match(self,/localStorage\.setItem\(ACTIVE_KEY,'yes'\)/);
assert.match(self,/localStorage\.removeItem\(COUNTS_KEY\)/);
assert.doesNotMatch(self,/fetch\(|sendBeacon|XMLHttpRequest|visitor_id|document\.cookie/);
assert.match(history,/この端末の利用メモ（任意）/);
assert.match(history,/id="usageHistoryTodayViews"/);
assert.match(history,/id="usageHistoryRange"/);
assert.match(history,/id="usageSelfEnable"/);
assert.match(history,/id="usageSelfDisable"/);
assert.match(history,/id="usageSelfClear"/);
assert.match(historyJS,/\/history\?days=/);
assert.doesNotMatch(historyJS,/\.innerHTML\s*=/);
assert.ok(typeof worker.fetch==='function');
console.log('Public v1.25: today + anonymous history + optional self-use controls, all sources intact: OK');
