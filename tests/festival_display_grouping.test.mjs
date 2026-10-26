import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
  NAKANO_FESTIVAL_SOURCE,NERIMA_FOREST_SOURCE,
  NAKANO_FESTIVAL_GROUP_ID,NERIMA_FOREST_GROUP_ID,
  NERIMA_FOREST_NOV03_GROUP_ID,
  NAKANO_FESTIVAL_CHILD_IDS,NERIMA_FOREST_CHILD_IDS,NERIMA_FOREST_NOV03_CHILD_IDS,
  groupFestivalDisplayEvents,groupedEventChangeCounts,
  festivalMemberSummary,isNerimaForestChild
} from '../site/festival-display-grouping.js';

const make = (id,ward,when,source)=>({
  id,name:'イベント '+id,ward,date_start:when,date_end:when,
  period:when,venue:'試験会場',time:'10:00〜11:00',price:'無料',image:'',
  official_url:source,url:source,source,description:'元の説明',
  family_fit:{overall:'A'},reservation:{required:false,note:'予約不要'}
});
const nov03=NERIMA_FOREST_NOV03_CHILD_IDS.map(id=>make(id,'練馬区','2026-11-03',NERIMA_FOREST_SOURCE));
const dec05=NERIMA_FOREST_CHILD_IDS.map(id=>make(id,'練馬区','2026-12-05',NERIMA_FOREST_SOURCE));
const nakano=NAKANO_FESTIVAL_CHILD_IDS.map(id=>make(id,'中野区','2026-12-05',NAKANO_FESTIVAL_SOURCE));
const other=make('other-same-site','練馬区','2026-12-05',NERIMA_FOREST_SOURCE);
const raw=[nov03[0],dec05[0],nakano[0],nov03[1],other,...dec05.slice(1),...nakano.slice(1)];
const frozen=JSON.stringify(raw);
const results=groupFestivalDisplayEvents(raw);
assert.equal(results.length,4,'2 day-grouped Nerima cards + 1 Nakano card + unrelated event');
assert.equal(JSON.stringify(raw),frozen,'data must not be modified or source event IDs dropped');
const nov=results.find(x=>x.id===NERIMA_FOREST_NOV03_GROUP_ID);
const dec=results.find(x=>x.id===NERIMA_FOREST_GROUP_ID);
const anime=results.find(x=>x.id===NAKANO_FESTIVAL_GROUP_ID);
assert.ok(nov&&dec&&anime,'all parent cards exist');
assert.equal(nov.date_start,'2026-11-03');assert.equal(nov.date_end,'2026-11-03');
assert.equal(nov.period,'11/3(火・祝)');assert.equal(nov._festival_members.length,2);
assert.equal(dec.date_start,'2026-12-05');assert.equal(dec._festival_members.length,3);
assert.equal(anime._festival_members.length,8);
assert.equal(festivalMemberSummary(nov),'内訳2企画');
assert.equal(festivalMemberSummary(dec),'内訳3企画');
assert.equal(groupFestivalDisplayEvents(nov03).length,1);
assert.equal(groupFestivalDisplayEvents(dec05).length,1);
assert.equal(groupFestivalDisplayEvents([...nov03,...dec05]).length,2,'two separate dates must never collapse');
assert.equal(groupFestivalDisplayEvents([nov03[0]])[0]._festival_members.length,1,'filter applies before grouping');
assert.match(festivalMemberSummary(groupFestivalDisplayEvents([nov03[0]])[0]),/条件に一致1企画/);
assert.equal(groupFestivalDisplayEvents([other])[0].id,other.id,'same source URL without known ID must not group');
assert.ok([...nov03,...dec05].every(isNerimaForestChild));
assert.equal(isNerimaForestChild(other),false);
const changes={added:new Set([nov03[0].id,dec05[0].id,nakano[0].id]),updated:new Set()};
assert.deepEqual(groupedEventChangeCounts(raw,changes),{added:3,updated:0},'one added badge per group');
assert.equal(raw.filter(e=>changes.added.has(e.id)).length,3);
for(const page of ['site/search.html','site/copy.html','site/canva.html']){
  const html=readFileSync(page,'utf8');
  assert.match(html,/groupFestivalDisplayEvents/,page+' must use grouped view');
}
const css=readFileSync('site/styles.css','utf8');
assert.match(css,/\.festival-programs\s*\{/);
assert.match(css,/\.festival-parent-tag\s*\{/);
console.log('PASS: Nerima 11/03 2 venues and 12/05 3 venues separate; Nakano 8 inside 1 parent; source and Canva IDs preserved');
