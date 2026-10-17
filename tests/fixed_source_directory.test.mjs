import assert from 'node:assert/strict';
import fs from 'node:fs';

const html=fs.readFileSync('site/index.html','utf8');
const css=fs.readFileSync('site/styles.css','utf8');
const sourceConfig=JSON.parse(fs.readFileSync('site/data/discovery_sources.json','utf8'));
const sources=sourceConfig.explicit_sources.filter(x=>x.enabled===true);

assert.ok(sources.length>=24,'existing fixed discovery sources must not vanish');
assert.ok(sources.every(x=>typeof x.label==='string' && x.label.trim()),'all displayed source labels need names');
assert.match(html,/id="logic"[^>]*aria-labelledby="logicTitle"/,'directory must be inside the extraction explanation');
assert.match(html,/id="fixedSourceDetails"/);
assert.match(html,/固定サイト（登録済み参照元）一覧/);
assert.match(html,/id="fixedSourceCount"/);
assert.match(html,/id="fixedSourceList"/);
assert.match(html,/loadDiscoverySources\(/,'render from live registry; no manually maintained list');
assert.match(html,/all\.filter\(source=>source && source\.enabled===true\)/);
assert.match(html,/source\.origin==='official'/);
assert.match(html,/source\.origin==='official_added'/);
assert.match(html,/従来からの固定サイト/);
assert.match(html,/追加登録した地域情報サイト/,'newly registered community sources must have their own section');
assert.match(html,/source\.origin==='manual'/,'manually added community sources must not be counted as legacy');
assert.match(html,/source\.origin==='legacy'/,'legacy section must include only legacy origins');
assert.doesNotMatch(html,/source\.origin!=='official'&&source\.origin!=='official_added'/,'non-official must not be mislabeled legacy');
assert.match(html,/その他の固定サイト（要分類）/,'new origins must remain visible instead of being mislabeled');
const originCounts = Object.groupBy(sources, source=>source.origin);
assert.equal((originCounts.official||[]).length+(originCounts.official_added||[]).length,4,'keep four official sources');
assert.equal((originCounts.legacy||[]).length,18,'only 18 previous fixed sources');
assert.equal((originCounts.manual||[]).length,2,'two newly added community sites');
assert.ok((originCounts.manual||[]).some(source=>source.id==='tamemap_nakano'));
assert.ok((originCounts.manual||[]).some(source=>source.id==='itabashi_times_event'));
assert.deepEqual([...new Set(sources.map(source=>source.id))].length,sources.length,'no source IDs duplicated');
assert.ok(sources.every(source=>['official','official_added','manual','legacy'].includes(source.origin)),'unclassified source needs a new explicit group');
assert.match(html,/safeHttpUrl\(source\.annual_listing_url\|\|source\.base_url\|\|source\.search_urls\?\.\[0\]\)/);
assert.match(html,/escapeHtml\(source\.annual_listing_label\|\|source\.label/);
assert.match(html,/target="_blank" rel="noopener noreferrer"/);
assert.match(html,/catch\(error\)[\s\S]*固定サイト一覧を取得できませんでした/);
assert.match(css,/\.logic-fixed-sources-group ul/);
assert.match(css,/@media\(max-width:520px\)[^{]*\{\.logic-fixed-sources/);
for(const id of ['nakano_official_tourism','itabashi_official_festival','itabashi_tourism_festival','tamemap_nakano','itabashi_times_event']){
  assert.ok(sources.some(x=>x.id===id),'new official source included: '+id);
}
assert.ok(sources.some(x=>x.id==='nakano'),'legacy Nakano source retained');
assert.ok(sources.some(x=>x.id==='nerima_district_festivals_2026'),'official Nerima table retained');
console.log('Fixed-source directory visibility / dynamic source / mobile safeguards: OK ('+sources.length+' sources)');
