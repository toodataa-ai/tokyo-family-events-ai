import assert from 'node:assert/strict';
import fs from 'node:fs';

const rubric=JSON.parse(fs.readFileSync('site/data/family_fit_rubric.json','utf8'));
const cases=JSON.parse(fs.readFileSync('site/data/family_fit_regression_cases.json','utf8'));

assert.equal(rubric.rubric_version,'family-fit-v2');
assert.equal(rubric.policy.overall_a_soft_exclusion_forbidden,true);
assert.equal(rubric.policy.family_value_low_cannot_be_primary_reason,true);
assert.equal(rubric.policy.child_program_absent_cannot_be_primary_reason,true);
assert.equal(rubric.policy.soft_exclusion_min_material_negatives,2);
assert.equal(rubric.policy.narrow_fandom_alone_cannot_exclude,true);
assert.equal(rubric.policy.passive_only_alone_cannot_exclude,true);
assert.equal(rubric.policy.alcohol_available_is_not_alcohol_primary,true);
assert.equal(rubric.policy.fandom_is_not_adult_oriented_by_default,true);

const material=new Set(rubric.material_negative_codes);
const severe=new Set(rubric.severe_single_factor_codes);
function canSoftExclude(overall,negative){
  if(overall==='A') return false;
  const materialCount=new Set(negative.filter(x=>material.has(x))).size;
  return materialCount>=rubric.policy.soft_exclusion_min_material_negatives || negative.some(x=>severe.has(x));
}
assert.equal(canSoftExclude('B',['child_program_absent']),false);
assert.equal(canSoftExclude('B',['narrow_fandom']),false);
assert.equal(canSoftExclude('B',['passive_only']),false);
assert.equal(canSoftExclude('B',['narrow_fandom','passive_only']),true);
assert.equal(canSoftExclude('B',['alcohol_primary']),true);
assert.equal(canSoftExclude('A',['alcohol_primary']),false);

const byName=new Map(cases.cases.map(x=>[x.name,x]));
for(const required of [
  'POP UP BOX「まんが日本昔ばなし展」',
  '北海道まるごとフェアinサンシャインシティ',
  '龍の舞',
  'Gelato Collection',
  '第2回日本食文化伝承会「いも煮会」',
  '企画展「海を渡ってきた植物の物語」',
  'アーツ中村橋 2026',
  "てんぼうパーク×ときめきメモリアル Girl's Side",
  '新宿歌舞伎町春画展WA',
  '妖怪盆踊り2026'
]) assert.ok(byName.has(required),`missing regression case: ${required}`);

assert.equal(byName.get('新宿歌舞伎町春画展WA').required_hard_code,'safety_unsuitable');
assert.equal(byName.get('妖怪盆踊り2026').required_hard_code,'outside_23wards');
console.log('family-fit-v2 policy regression: OK');
