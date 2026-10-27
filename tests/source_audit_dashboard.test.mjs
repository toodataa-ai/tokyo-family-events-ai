import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const html=readFileSync('site/source-audit.html','utf8');
const js=readFileSync('site/source-audit.js','utf8');
const css=readFileSync('site/source-audit.css','utf8');
const home=readFileSync('site/index.html','utf8');
assert.match(html,/lang="ja"/);
assert.match(html,/source-audit\.js/);
assert.match(html,/登録固定サイト/);
assert.match(html,/掲載・除外照合/);
assert.match(html,/未確認/);
assert.match(js,/data\/discovery_sources\.json/);
assert.match(js,/audit\/fixed_sources\.json/);
assert.match(js,/candidate_publication_parity==='未検証'/);
assert.match(js,/event_candidates_total===null/);
assert.match(js,/登録URLを取得/);
assert.match(js,/一部取得失敗/);
assert.match(js,/取得失敗/);
assert.match(js,/監査結果なし/);
assert.match(js,/replaceChildren/);
assert.match(js,/textContent/);
assert.doesNotMatch(js,/\.innerHTML\s*=/);
assert.match(css,/"Meiryo UI"/);
assert.match(home,/source-audit\.html/);
for(const id of ['sourceAuditRows','sourceAuditSearch','sourceAuditFilter',
                 'sourceRegistered','sourceChecked','sourcePartial','sourceError',
                 'sourceAuditTime','sourceAuditScope']) {
  assert.match(html, new RegExp('id="'+id+'"'));
}
const ci=readFileSync('.github/workflows/phase3-fixed-source-dashboard.yml','utf8');
assert.match(ci,/gh workflow run deploy\.yml --ref main/);
assert.match(ci,/actions: write/);
assert.match(ci,/git add -- site\/audit\/fixed_sources\.json/);
assert.doesNotMatch(ci,/refs\/heads\/production/);
assert.match(js,/new_arrival_post_leads_observed/);
assert.match(js,/official_alternatives/);
assert.match(js,/元の障害は未解消/);
console.log('Phase3 fixed-source dashboard fail-closed contract: OK');
