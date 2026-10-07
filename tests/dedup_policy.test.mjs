import assert from 'node:assert/strict';
import fs from 'node:fs';

const latest=JSON.parse(fs.readFileSync('site/data/latest_prompt.json','utf8'));
const prompt=fs.readFileSync(latest.path,'utf8');

assert.equal(latest.version,'v1.11');
assert.match(prompt,/同一URLだけでは重複にしない/);
assert.match(prompt,/地区・支部・会場・公演識別子/);
assert.match(prompt,/同時開催/);

const expected=[
  ['site/data/2026-10-10-decisions.json','2026-10-10-shinagawa-eba2'],
  ['site/data/2026-10-10-decisions.json','lg-d1efd0984b'],
  ['site/data/2026-10-17-decisions.json','lg-91824e1566']
];
for(const [file,id] of expected){
  const doc=JSON.parse(fs.readFileSync(file,'utf8'));
  const row=(doc.decisions||[]).find(x=>x.candidate_id===id);
  assert.ok(row,`${id} missing`);
  assert.equal(row.decision,'published',`${id} must remain published after dedup re-audit`);
}
console.log('dedup regression guard: OK');
