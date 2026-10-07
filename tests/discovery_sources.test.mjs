import assert from 'node:assert/strict';
import fs from 'node:fs';

const data=JSON.parse(fs.readFileSync('site/data/discovery_sources.json','utf8'));
const latest=JSON.parse(fs.readFileSync('site/data/latest_prompt.json','utf8'));
const prompt=fs.readFileSync(latest.path,'utf8');

assert.equal(data.schema_version,3);
assert.equal(data.discovery_strategy.ai_cross_search.enabled,true);
assert.equal(data.discovery_strategy.ai_cross_search.per_ward_required,true);
assert.equal(data.discovery_strategy.explicit_sources.enabled,true);
assert.equal(data.discovery_strategy.explicit_sources.allow_future_additions,true);
assert.equal(data.discovery_strategy.explicit_sources.required_each_run,true);

const sources=data.explicit_sources||[];
const protectedIds=data.protected_legacy_source_ids||[];
assert.equal(protectedIds.length,18,'protected legacy source ids must stay at 18');
assert.ok(sources.length>=protectedIds.length,'future explicit sources may be appended');
const ids=new Set(sources.map(x=>x.id));
for(const id of protectedIds) assert.ok(ids.has(id),`missing protected legacy source: ${id}`);
assert.equal(ids.size,sources.length,'explicit source ids must be unique');

const requiredFields=data.explicit_source_schema.required_fields||[];
for(const s of sources){
  for(const field of requiredFields) assert.ok(field in s,`${s.id}: missing ${field}`);
  assert.ok(Array.isArray(s.search_urls)&&s.search_urls.length>=1,`${s.id}: search_urls required`);
}
const legacy=sources.filter(x=>x.origin==='legacy');
assert.equal(legacy.length,18,'all protected sources must remain tagged legacy');
assert.ok(legacy.every(x=>x.enabled===true && x.required===true),'legacy sources stay enabled and required');

const nerima=sources.find(x=>x.id==='nerimakanko');
assert.ok(nerima.search_urls.includes('https://www.nerimakanko.jp/event/'));
assert.ok(nerima.search_urls.includes('https://www.nerimakanko.jp/event/search.php?month={YYYY-MM}'));
const suginami=sources.find(x=>x.id==='suginami_festival');
assert.ok(suginami.search_urls.includes('https://www.city.suginami.tokyo.jp/cgi-bin/event_cal_multi/calendar.cgi?type=2&year={YYYY}&month={MM}&event_category=5&siteid=1'));

assert.equal(latest.version,'v1.10');
assert.match(prompt,/AI横断探索/);
assert.match(prompt,/explicit_sources/);
assert.match(prompt,/explicit_source_checks/);
assert.match(prompt,/新しい参照元を追加するときは explicit_sources/);
assert.match(prompt,/channel: "ai_cross" または "explicit"/);
assert.match(prompt,/source_id/);
assert.match(prompt,/管理ビュー\(admin\.html\)/);
assert.match(prompt,/indoor_outdoor/);
assert.match(prompt,/"屋内・屋外"/);
assert.match(prompt,/英語値/);
console.log(`dual discovery source policy: protected=${protectedIds.length}, explicit=${sources.length}: OK`);
