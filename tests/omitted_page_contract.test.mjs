import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const root = new URL('../', import.meta.url);
const read = path => readFileSync(new URL(path, root), 'utf8');
const page = read('site/omitted.html');
const index = read('site/index.html');
const js = read('site/omitted.js');
const data = JSON.parse(read('site/curation/suginami_review_20261022.json'));

assert.match(index, /href="omitted\.html"/, 'homepage must link to exclusion audit');
assert.match(page, /id="omittedResults"/);
assert.match(page, /id="omittedSearch"/);
assert.match(page, /id="omittedTabs"/);
assert.match(page, /id="showMore"/);
assert.match(js, /noopener noreferrer/);
assert.match(js, /replaceChildren/);

assert.equal(data.schema_version, 1);
assert.equal(data.as_of_jst, '2026-10-22');
assert.equal(data.rows.length, 310);
assert.equal(new Set(data.rows.map(r => r.id)).size, 310);
const expected = {
  '対象外': 200, '掲載候補': 95, 'ステージング既登録': 8,
  '要確認': 3, '前回のみ・再取得要': 4
};
assert.deepEqual(data.counts, expected);
for (const [status, n] of Object.entries(expected)) {
  assert.equal(data.rows.filter(x => x.status === status).length, n);
}
for (const row of data.rows) {
  assert.ok(row.id && row.title && row.reason && expected[row.status] !== undefined,
    'every row has an individual decision and explanation');
  if (row.official_url) {
    const u = new URL(row.official_url);
    assert.equal(u.protocol, 'https:');
    assert.equal(u.hostname, 'www.city.suginami.tokyo.jp');
    assert.match(u.pathname, /^\/s\d+\/event\/\d+\.html$/);
  } else {
    assert.equal(row.status, '前回のみ・再取得要', 'missing original URL must be flagged, not guessed');
  }
}
assert.equal(data.rows.filter(x => x.official_url).length, 306);
assert.equal(data.rows.find(x => x.id === 'suginami-official-27652').status, 'ステージング既登録');
assert.equal(data.rows.find(x => x.id === 'suginami-official-28531').status, 'ステージング既登録');
assert.equal(data.rows.find(x => x.id === 'suginami-official-28567').status, 'ステージング既登録');
console.log('PASS: 310 decision-page rows/links/statuses reconciled and homepage has access link.');
