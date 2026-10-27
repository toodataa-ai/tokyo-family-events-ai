import {prepareIssues,formatJst} from "./pending-issues-model.mjs?v=20261028-1";
const byId=id=>document.getElementById(id);
function textNode(tag,text,className){
  const node=document.createElement(tag);
  if(className)node.className=className;
  node.textContent=String(text??"");
  return node;
}
function statusLine(title,value){
  const elem=textNode("div","","pending-issue-part");
  elem.appendChild(textNode("strong",title));
  elem.appendChild(textNode("p",value));
  return elem;
}
function renderCard(entry){
  const article=textNode("article","","pending-issue-card");
  const head=textNode("div","","pending-issue-card-top");
  head.appendChild(textNode("span",entry.category==="connection"?"サイトの取得に関する問題":"イベント情報の確認作業","pending-issue-kind"));
  head.appendChild(textNode("span",entry.status.label,"pending-issue-status"));
  article.appendChild(head);
  article.appendChild(textNode("h3",entry.title));
  const body=textNode("div","","pending-issue-parts");
  body.appendChild(statusLine("どんな影響がある？",entry.impact));
  body.appendChild(statusLine("いま、どうなっている？",entry.now));
  body.appendChild(statusLine("代わりにどう対応している？",entry.workaround));
  body.appendChild(statusLine("次にどうする？",entry.next));
  article.appendChild(body);
  const status=textNode("div","","pending-issue-progress");
  status.appendChild(textNode("strong","最新の確認状態："));
  status.appendChild(textNode("span",entry.status.detail));
  article.appendChild(status);
  const footer=textNode("div","","pending-issue-card-footer");
  const a=textNode("a","詳しい対応記録を見る（GitHub）");
  a.href=entry.issue_url;
  a.target="_blank";
  a.rel="noopener noreferrer";
  footer.appendChild(a);
  article.appendChild(footer);
  return article;
}
function render(model){
  const f=byId("pendingCategoryFilter").value;
  const items=model.entries.filter(x=>f==="all"||x.category===f);
  const list=byId("pendingIssueList");
  list.replaceChildren();
  for(const item of items)list.appendChild(renderCard(item));
  if(!items.length)list.appendChild(textNode("p","選択した区分の残課題はありません。"));
  byId("pendingVisibleCount").textContent=
    items.length+"件を表示（登録済みの残課題 "+model.counts.total+"件）";
}
async function getJson(path){
  const res=await fetch(path,{cache:"no-store"});
  if(!res.ok)throw new Error("HTTP "+res.status);
  return res.json();
}
async function init(){
  let model;
  try {
    const catalog=await getJson("audit/pending_issues_catalog.json");
    let audit=null;
    try{audit=await getJson("audit/fixed_sources.json");}
    catch(e){console.warn("サイト取得状況の最新監査は未取得です",e);}
    model=prepareIssues(catalog,audit);
  } catch(err){
    console.error("残課題一覧の読み込み失敗",err);
    byId("pendingIntro").textContent="現在の残課題一覧を読み込めませんでした。";
    byId("pendingCheckedAt").textContent="確認ができていないため、残課題が0件とは表示していません。";
    byId("pendingIssueList").replaceChildren(textNode("p","現在一覧を取得できません。時間をおいてもう一度お試しください。"));
    byId("pendingVisibleCount").textContent="未確認";
    return;
  }
  byId("pendingTotal").textContent=model.counts.total;
  byId("pendingConnection").textContent=model.counts.connection;
  byId("pendingVerification").textContent=model.counts.verification;
  byId("pendingIntro").textContent="イベント収集に影響する問題と、まだ確認が必要な作業を分けて掲載しています。";
  byId("pendingCheckedAt").textContent=
    "取得状況の最終監査："+(model.is_audit_current?formatJst(model.audit_checked_at):"最新結果は取得できませんでした")+
    "　／　残課題リストの確認日："+(model.catalog_reviewed_at||"未確認")+
    "。掲載内容の確認はアクセス成功と別に実施します。";
  byId("pendingCategoryFilter").addEventListener("change",()=>render(model));
  render(model);
}
init();
