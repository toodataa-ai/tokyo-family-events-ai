import assert from 'node:assert/strict';
import {mondayOf,recentEventChanges,changeKind,changeBadge,currentChangeCounts} from '../site/recent-event-changes.js';
const base=[
 {run_type:'manual_independent_holiday_addition',as_of_jst:'2026-10-26',new_event_ids:['nov03-1','nov03-2']},
 {run_type:'manual_verified_subset_addition',as_of_jst:'2026-10-26',new_event_ids:['nov23-1']},
 {run_type:'manual_verified_weekend_subset_addition',as_of_jst:'2026-10-27',new_event_ids:['nov29-1'],added_weekly_records:1},
 {run_type:'verified_horizon_subset',as_of_jst:'2026-10-26',new_official_independent_records:2,preserved_carryover_records:1},
 {run_type:'published_data_correction',as_of_jst:'2026-10-19',changed_unique:20},
 {run_type:'historical_review',as_of_jst:'2026-10-26',changed_unique:9}
];
const today=new Date('2026-10-27T00:00:00+09:00');
const items=recentEventChanges({history:base},{today,lastWeekNewRows:[{id:'dec05-1'},{id:'dec05-2'}]});
assert.equal(mondayOf('2026-10-27'),'2026-10-26');
assert.equal(items.added.size,6);
assert.equal(items.updated.size,0,'do not invent changed IDs from count alone');
assert.equal(changeKind({id:'nov03-1'},items),'added');
assert.equal(changeKind({id:'dec05-2'},items),'added');
assert.equal(changeKind({id:'carryover-id'},items),'');
assert.match(changeBadge({id:'nov29-1'},items),/今週追加/);
assert.equal(changeBadge({id:'carryover-id'},items),'');
const actual=currentChangeCounts([{id:'nov29-1'},{id:'dec05-2'},{id:'carryover-id'}],items);
assert.deepEqual(actual,{added:2,updated:0});
const withoutVerified=recentEventChanges({history:base},{today,lastWeekNewRows:[{id:'only-one'}]});
assert.equal(withoutVerified.added.size,4,'incomplete shard must not be trusted');
const annotated=recentEventChanges({history:[{as_of_jst:'2026-10-27',new_event_ids:['a'],changed_event_ids:['a','b']}]},{today});
assert.equal(annotated.updated.has('a'),false,'an added ID cannot also be updated');
assert.equal(annotated.updated.has('b'),true);
assert.match(changeBadge({id:'b'},annotated),/今週更新/);
const nextWeek=recentEventChanges({history:base},{today:new Date('2026-11-02T09:00:00+09:00'),lastWeekNewRows:[{id:'dec05-1'},{id:'dec05-2'}]});
assert.equal(nextWeek.added.size,0,'week badges expire automatically');
console.log('PASS weekly change markers: added identity, changed identity, no carryover, clear after new week');
