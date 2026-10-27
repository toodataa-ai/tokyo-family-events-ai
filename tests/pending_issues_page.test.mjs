import assert from "node:assert/strict";
import fs from "node:fs";
import {prepareIssues,validateCatalog,validateAudit,issueStatus} from "../site/pending-issues-model.mjs";

const read = path => fs.readFileSync(path,"utf-8");
const catalog = JSON.parse(read("site/audit/pending_issues_catalog.json"));
const audit = JSON.parse(read("site/audit/fixed_sources.json"));
const model = prepareIssues(catalog,audit);
assert.equal(model.counts.total,6);
assert.equal(model.counts.connection,2);
assert.equal(model.counts.verification,4);
assert.equal(new Set(model.entries.map(x=>x.id)).size,6);
assert.equal(validateCatalog(catalog),true);
assert.equal(validateAudit(audit),true);
for(const entry of model.entries){
  assert.match(entry.issue_url,/^https:\/\/github\.com\/toodataa-ai\/tokyo-family-events-ai\/issues\/[0-9]+$/);
  assert.ok(entry.impact && entry.now && entry.workaround && entry.next);
  assert.ok(entry.status.label);
}
const tama = model.entries.find(x=>x.id==="tamemap-nakano");
const itabashi = model.entries.find(x=>x.id==="itabashi-tourism");
assert.equal(tama.status.label,"自動取得できません");
assert.equal(itabashi.status.label,"自動取得できません");
assert.match(itabashi.status.detail,/自治体公式サイト/);
assert.ok(model.entries.filter(x=>x.category==="verification")
             .every(x=>x.status.label==="内容を確認中"));

const unavailable = issueStatus(catalog.issues[0],null);
assert.equal(unavailable.label,"取得状況を確認できません");
assert.doesNotMatch(unavailable.label,/解決/);
const healed = structuredClone(audit);
const fixed = healed.sources.find(x=>x.source_id==="tamemap_nakano");
fixed.retrieval_status="checked";
fixed.pages_checked=fixed.pages_expected;
const status = issueStatus(catalog.issues[0],healed);
assert.equal(status.label,"接続を確認・内容の照合待ち");
assert.doesNotMatch(status.label,/解決済み/);
const partially = structuredClone(audit);
partially.sources.find(x=>x.source_id==="tamemap_nakano").retrieval_status="partial_error";
assert.equal(issueStatus(catalog.issues[0],partially).label,"一部のページが取得できません");
const unsafe = structuredClone(catalog);
unsafe.issues[0].issue_url="https://example.com/ads";
assert.throws(()=>validateCatalog(unsafe));

const home=read("site/index.html");
const page=read("site/pending-issues.html");
const js=read("site/pending-issues.js");
const css=read("site/pending-issues.css");
assert.match(home,/href="pending-issues\.html"/);
assert.match(home,/現在の残課題・対応状況/);
assert.match(home,/pending-issues\.css/);
for(const id of ["pendingTotal","pendingConnection","pendingVerification","pendingIntro",
                 "pendingIssueList","pendingVisibleCount","pendingCheckedAt","pendingCategoryFilter"]){
 assert.match(page,new RegExp('id="'+id+'"'));
}
assert.match(page,/東京23区子連れイベントAI収集/);
assert.match(page,/影響/);
assert.match(page,/取得できなかったために既存情報を消すこともありません/);
assert.match(js,/replaceChildren/);
assert.match(js,/textContent/);
assert.doesNotMatch(js,/\.innerHTML\s*=/);
assert.match(page,/aria-live/); // polite updates without untrusted HTML rendering
assert.match(css,/"Meiryo UI"/);
assert.ok(!read("site/data/discovery_sources.json").includes("pending_issues_catalog"));
console.log("Pending issues catalog, live audits, unknown/failure safety and home link: OK");
