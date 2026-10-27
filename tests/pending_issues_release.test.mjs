import assert from "node:assert/strict";
import fs from "node:fs";
import {prepareIssues,validateAudit,issueStatus,validateCatalog} from "../site/pending-issues-model.mjs";

const get = path => fs.readFileSync(path,"utf8");
const catalog = JSON.parse(get("site/audit/pending_issues_catalog.json"));
assert.equal(validateCatalog(catalog),true);
assert.deepEqual(catalog.issues.map(x=>x.id),[
  "tamemap-nakano","itabashi-tourism","suginami-candidates","article-leads","weekly-update"]);
for(const row of catalog.issues){
  assert.ok(row.impact && row.now && row.workaround && row.next);
  assert.match(row.issue_url,/^https:\/\/github\.com\/toodataa-ai\/tokyo-family-events-ai\/issues\/[0-9]+$/);
}
const checks=Array.from({length:26},(_,i)=>({
  source_id:i===0?"tamemap_nakano":i===1?"itabashi_tourism_festival":"other_source_"+i,
  retrieval_status:i<2?"source_error":"checked",
  candidate_publication_parity:"未検証",
  pages_expected:i<2?3:1,
  pages_checked:i<2?0:1
}));
checks[1].official_alternatives=[{source_id:"itabashi_official_festival",retrieval_status:"checked"}];
const audit={
  schema_version:1,read_only:true,registered_source_count:26,
  generated_at_jst:"2026-10-28T00:30:40+09:00",
  summary:{full_event_row_parity_verified_by_this_report:0},
  sources:checks
};
assert.equal(validateAudit(audit),true);
const result=prepareIssues(catalog,audit);
assert.equal(result.counts.total,5);
assert.equal(result.counts.connection,2);
assert.equal(result.counts.verification,3);
assert.equal(result.entries.find(x=>x.id==="tamemap-nakano").status.label,"自動取得できません");
assert.match(result.entries.find(x=>x.id==="itabashi-tourism").status.detail,/自治体公式サイト/);
assert.ok(result.entries.filter(x=>x.category==="verification").every(x=>x.status.label==="内容を確認中"));
const unavailable=issueStatus(catalog.issues[0],null);
assert.equal(unavailable.label,"取得状況を確認できません");
const healed=structuredClone(audit);
healed.sources[0].retrieval_status="checked";
healed.sources[0].pages_checked=healed.sources[0].pages_expected;
assert.equal(issueStatus(catalog.issues[0],healed).label,"接続を確認・内容の照合待ち");
assert.doesNotMatch(issueStatus(catalog.issues[0],healed).label,/解決済み/);
assert.equal(prepareIssues(catalog,null).is_audit_current,false);

const home=get("site/index.html");
const page=get("site/pending-issues.html");
const js=get("site/pending-issues.js");
const css=get("site/pending-issues.css");
assert.match(home,/href="pending-issues\.html"/);
assert.match(home,/現在の残課題・対応状況/);
assert.match(home,/pending-issues\.css/);
assert.match(js,/staging\/audit\/fixed_sources\.json/);
assert.match(js,/replaceChildren/);
assert.doesNotMatch(js,/\.innerHTML\s*=/);
assert.match(css,/"Meiryo UI"/);
assert.doesNotMatch(page,/href="source-audit\.html"/);
for(const id of ["pendingTotal","pendingConnection","pendingVerification","pendingIntro",
                 "pendingIssueList","pendingVisibleCount","pendingCheckedAt","pendingCategoryFilter"]){
 assert.match(page,new RegExp('id="'+id+'"'));
}
assert.match(page,/取得できなかったために既存情報を消すこともありません/);
console.log("v1.24 approved pending-issues isolated public candidate: PASS");
