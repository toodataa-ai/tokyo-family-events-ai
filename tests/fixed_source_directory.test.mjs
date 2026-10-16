import assert from 'node:assert/strict';
import fs from 'node:fs';

const html=fs.readFileSync('site/index.html','utf8');
const css=fs.readFileSync('site/styles.css','utf8');
const sourceConfig=JSON.parse(fs.readFileSync('site/data/discovery_sources.json','utf8'));
const sources=sourceConfig.explicit_sources.filter(x=>x.enabled===true);

assert.ok(sources.length>=22,'existing fixed discovery sources must not vanish');
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
assert.match(html,/safeHttpUrl\(source\.annual_listing_url\|\|source\.base_url\|\|source\.search_urls\?\.\[0\]\)/);
assert.match(html,/escapeHtml\(source\.label/);
assert.match(html,/target="_blank" rel="noopener noreferrer"/);
assert.match(html,/catch\(error\)[\s\S]*固定サイト一覧を取得できませんでした/);
assert.match(css,/\.logic-fixed-sources-group ul/);
assert.match(css,/@media\(max-width:520px\)[^{]*\{\.logic-fixed-sources/);
for(const id of ['nakano_official_tourism','itabashi_official_festival','itabashi_tourism_festival']){
  assert.ok(sources.some(x=>x.id===id),'new official source included: '+id);
}
assert.ok(sources.some(x=>x.id==='nakano'),'legacy Nakano source retained');
assert.ok(sources.some(x=>x.id==='nerima_district_festivals_2026'),'official Nerima table retained');
console.log('Fixed-source directory visibility / dynamic source / mobile safeguards: OK ('+sources.length+' sources)');
