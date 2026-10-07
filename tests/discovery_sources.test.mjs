import assert from 'node:assert/strict';
import fs from 'node:fs';

const data=JSON.parse(fs.readFileSync('site/data/discovery_sources.json','utf8'));
const latest=JSON.parse(fs.readFileSync('site/data/latest_prompt.json','utf8'));
const prompt=fs.readFileSync(latest.path,'utf8');

assert.equal(data.schema_version,2);
assert.equal(data.legacy_source_policy.required_each_run,true);
assert.equal(data.legacy_source_policy.use_search_urls_if_present,true);

const sources=data.legacy_discovery_sources||[];
assert.equal(sources.length,18,'legacy discovery source count must stay at 18');
assert.ok(sources.every(x=>x.required===true),'every legacy source must be required');
assert.ok(sources.every(x=>Array.isArray(x.search_urls)&&x.search_urls.length>=1),'every legacy source must have search_urls');

const expectedBase=[
'https://www.sumidaevent.com/','https://www.asakusaevent.com/','https://www.uenopark.info/',
'https://www.akihabaraevent.com/','https://www.hibiyapark.info/','https://www.ikebukuropark.info/',
'https://www.shinjukuevent.com/','https://www.nakanoevent.com/','https://www.yoyogikoen.info/',
'https://www.miyashitapark.info/','https://www.roppongievents.com/','https://www.toyosuevent.com/',
'https://www.odaibapark.com/','https://www.shinagawaevent.com/','https://www.tachikawaevent.com/',
'https://www.iterrace.jp/'
];
const allUrls=new Set(sources.flatMap(x=>[x.url,...x.search_urls]));
for(const url of expectedBase) assert.ok(allUrls.has(url),`missing legacy source: ${url}`);

const nerima=sources.find(x=>x.id==='nerimakanko');
assert.ok(nerima);
assert.ok(nerima.search_urls.includes('https://www.nerimakanko.jp/event/'));
assert.ok(nerima.search_urls.includes('https://www.nerimakanko.jp/event/search.php?month={YYYY-MM}'));

const suginami=sources.find(x=>x.id==='suginami_festival');
assert.ok(suginami);
assert.ok(suginami.search_urls.includes('https://www.city.suginami.tokyo.jp/cgi-bin/event_cal_multi/calendar.cgi?type=2&year={YYYY}&month={MM}&event_category=5&siteid=1'));

assert.equal(latest.version,'v1.7');
assert.match(prompt,/required=true/);
assert.match(prompt,/legacy_source_checks/);
assert.match(prompt,/nerimakanko\.jp\/event\/search\.php\?month=\{YYYY-MM\}/);
assert.match(prompt,/event_category=5/);
console.log('legacy discovery source coverage: OK');
