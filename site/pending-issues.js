import {prepareIssues,formatJst} from "./pending-issues-model.mjs?v=20261114-status-1";
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
  article.dataset.workStatus=entry.work_status;
  const head=textNode("div","","pending-issue-card-top");
  head.appendChild(textNode("span",entry.category==="connection"?"サイトの取得に関する問題":"イベント情報の確認作業","pending-issue-kind"));
  head.appendChild(textNode("span",entry.status.label,"pending-issue-status"));
  article.appendChild(head);
  article.appendChild(textNode("h3",entry.title));
  const body=textNode("div","","pending-issue-parts");
  if(entry.work_status==="completed"){
    body.appendChild(statusLine("完了した対応",entry.now));
    body.appendChild(statusLine("完了とした範囲",entry.completed_scope));
    body.appendChild(statusLine("確認日",entry.completed_at));
  }else{
    body.appendChild(statusLine("どんな影響がある？",entry.impact));
    body.appendChild(statusLine("現在残っていること",entry.now));
    body.appendChild(statusLine("代わりの対応",entry.workaround));
    body.appendChild(statusLine("今後の対応",entry.next));
  }
  article.appendChild(body);
  if(entry.retrieval_status){
    article.appendChild(statusLine("サイトへの接続（作業状況とは別）",
      entry.retrieval_status.label+"。"+entry.retrieval_status.detail));
  }
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
  const items=model.remaining.filter(x=>f==="all"||x.category===f);
  const list=byId("pendingIssueList");
  list.replaceChildren();
  for(const item of items)list.appendChild(renderCard(item));
  if(!items.length)list.appendChild(textNode("p","選択した区分の残課題はありません。"));
  const completed=byId("completedIssueList");
  completed.replaceChildren(...model.completed.map(renderCard));
  byId("completedIssueCount").textContent=model.counts.completed;
  byId("pendingVisibleCount").textContent=
    items.length+"項目を表示（現在の残課題 "+model.counts.total+"項目。完了した対応は含みません）";
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
    byId("completedIssueCount").textContent="未確認";
    byId("completedIssueList").replaceChildren(textNode("p","完了した対応の記録も取得できませんでした。"));
    return;
  }
  byId("pendingTotal").textContent=model.counts.total;
  byId("pendingConnection").textContent=model.counts.pending;
  byId("pendingVerification").textContent=model.counts.deferred;
  byId("pendingIntro").textContent="現在の残課題と、対応が完了した記録を分けています。件数は課題のまとまりで、候補数や取得できないページ数とは異なります。";
  byId("pendingCheckedAt").textContent=
    "取得状況の最終監査："+(model.is_audit_current?formatJst(model.audit_checked_at):"最新結果は取得できませんでした")+
    "　／　対応リストの確認日："+(model.catalog_reviewed_at||"未確認")+
    "。掲載内容の確認はアクセス成功と別に実施します。";
  byId("pendingCategoryFilter").addEventListener("change",()=>render(model));
  render(model);
}
init();
