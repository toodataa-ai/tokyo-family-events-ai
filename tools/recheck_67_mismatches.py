#!/usr/bin/env python3
"""Recheck each of the 67 Oct13 name-token alerts using actual HTTP and original event facts.
This is source triage, not a license to mark events 'verified' or publish changes.
"""
import concurrent.futures as cf
import datetime as dt
from html.parser import HTMLParser
import hashlib,json,re,sys,unicodedata
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

INPUT=Path("stage/research/2026-10-13-holiday-after-official-evidence.json")
DATA=Path("published-data/site/data")
OUT=Path("/tmp/67-verified-source-review")
OUT.mkdir(parents=True,exist_ok=True)
entries=json.loads(INPUT.read_text(encoding="utf-8"))["source_probes"]["title_token_unmatched"]
class Content(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True)
  self.hidden=0;self.title=0;self.text=[];self.titles=[];self.images=[]
 def handle_starttag(self,t,a):
  if t in ("script","style","noscript","svg"):self.hidden+=1
  if t=="title":self.title+=1
  if t=="img":
   o=dict(a);self.images.append(o.get("alt",""))
 def handle_endtag(self,t):
  if t in ("script","style","noscript","svg"):self.hidden=max(0,self.hidden-1)
  if t=="title":self.title=max(0,self.title-1)
 def handle_data(self,d):
  if self.hidden:return
  if self.title:self.titles.append(d)
  self.text.append(d)
def norm(s):
 s=unicodedata.normalize("NFKC",str(s or "")).lower()
 return re.sub(r"[^a-z0-9\u3040-\u30ff\u3400-\u9fff]","",s)
def short_name(s):
 s=re.sub(r"^(?:祝[）)]|（祝[）)])+","",s)
 s=re.sub(r"^〜?（月・祝）","",s)
 return s.strip(" 〜　")
def get(url):
 row={"url":url,"status":"error","checked_at":dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat()}
 try:
  req=Request(url,headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/128 Safari/537.36","Accept-Language":"ja-JP,ja;q=0.9"})
  with urlopen(req,timeout=20) as resp:
   raw=resp.read(1200000)
   row.update(http_status=resp.status,final_url=resp.geturl(),content_type=resp.headers.get("Content-Type",""))
  if row["http_status"]!=200:raise ValueError("status "+str(row["http_status"]))
  row["status"]="downloaded";row["sha256"]=hashlib.sha256(raw).hexdigest()
  try:ht=raw.decode("utf-8")
  except UnicodeDecodeError:ht=raw.decode("cp932","replace")
  p=Content();p.feed(ht)
  txt=" ".join(" ".join(p.text).split())
  row["page_title"]=" ".join(" ".join(p.titles).split())[:180]
  row["page_text_length"]=len(txt)
  row["page_not_found"]=any(marker in (row["page_title"]+" "+txt[:350]) for marker in (
   "ページが見つかりません","お探しのページは見つかり","404 Not Found","404エラー"))
  row["page_content_sample"]=txt[:400]
  row["_visible_normalized"]=norm(txt+" "+" ".join(p.images))
 except (URLError,HTTPError,TimeoutError,OSError,ValueError,UnicodeError) as exc:
  row["error"]=type(exc).__name__+": "+str(exc)[:230]
 return row
original={}
for w in json.loads((DATA/"manifest.json").read_text())["weekends"]:
 week=json.loads((DATA/w["file"]).read_text())
 for f in week.get("event_files",[]):
  for event in json.loads((DATA/f).read_text()):
   original[event["id"]]={"week":w["sat"],"id":event["id"],"name":event.get("name"),"ward":event.get("ward"),
     "start":event.get("date_start"),"end":event.get("date_end"),"venue":event.get("venue"),
     "official_url":event.get("official_url"),"source":event.get("source")}
urls=sorted({e["url"] for e in entries})
with cf.ThreadPoolExecutor(max_workers=8) as pool:
 pages=dict(zip(urls,pool.map(get,urls)))
overrides=[
 ("ピクサーの世界展","end_date_mismatch_confirmed","https://tickets.tbs.co.jp/mundopixar/","2026-10-12","Removal from Oct17-Nov14 weeks; exact evidence present"),
 ("HERO GATE","wrong_event_source","https://herogate.jp/about/","","Food fair page is not official music event detail"),
 ("ハロウィンナリ間ルシェ","soft_404_wrong_detail_id","https://nerimakanko.jp/event/detail.php?event_id=e000002968","","Old ID e000002933 is a missing-event page"),
 ("没後70年 茂田井武","generic_organizer_homepage","https://chihiro.jp/tokyo/exhibitions/2026/","","Organizer has dated 2026 exhibition listing"),
 ("目黒区民まつり子ども広場","unrelated_source_page","https://www.city.meguro.tokyo.jp/bunka/bunkasports/kankou/kuminmatsuri47.html","","Actual municipal festival page 2026-10-11"),
 ("子ども子育てフェスタかつしか","generic_government_article_has_event_details","https://www.city.katsushika.lg.jp/information/kouho/1042423/1042887.html","","Old page is grant program profile with festival details, city reporter direct event article better"),
 ("中里の秋さがしミッション","generic_organizer_homepage","https://www.nerimakanko.jp/event/search.php?cat=family&page=1","","Validate exact independent event timetable"),
 ("秋の自然たんけんラリー","generic_organizer_homepage","https://www.nerimakanko.jp/event/search.php?cat=family&page=1","","Tourism association has actual dates 10/14-11/23"),
]
results=[]
for alert in entries:
 source=pages[alert["url"]]
 event=original.get(alert["id"])
 if not event:raise RuntimeError("Original event missing: "+alert["id"])
 name=short_name(event["name"])
 visible=source.get("_visible_normalized","")
 name_token=norm(name)
 exact=bool(name_token and name_token in visible)
 # Segments are hints only. They must NOT be treated as full verification.
 components=[norm(t) for t in re.split(r"[（(＜<\-~〜:：!！・　／/―—\s]+",name) if len(norm(t))>=5]
 partial=[x for x in components if x in visible][:6]
 label="full_event_title_in_visible_text" if exact else ("some_title_segments_only" if partial else "no_reliable_title_match")
 if source.get("page_not_found"):label="soft_404_html"
 if source["status"]!="downloaded":label="http_fetch_failed"
 override=next(((code,url,end,note) for frag,code,url,end,note in overrides if frag in name),None)
 if override:
  label=override[0]
 record={**event,"original_url":alert["url"],"old_http_status":alert.get("http_status"),
   "checked_at":source["checked_at"],"fresh_http_status":source.get("http_status"),
   "fresh_final_url":source.get("final_url"),"page_title":source.get("page_title"),
   "page_not_found":source.get("page_not_found",False),
   "source_title_matches":exact,"matching_fragments":partial,
   "review_class":label,"review_note":"Title/HTTP findings alone do not validate event/date/venue.",
   "official_replacement_candidate":override[1] if override else None,
   "confirmed_end":override[2] if override else None,
   "manual_note":override[3] if override else None,
   "http_error":source.get("error"),"source_sha256":source.get("sha256")}
 results.append(record)
counts={}
for e in results:counts[e["review_class"]]=counts.get(e["review_class"],0)+1
summary={"checked_at":dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(),
 "records":len(results),"unique_events":len({x["name"] for x in results}),
 "unique_source_urls":len(urls),
 "source_url_successes":sum(x["status"]=="downloaded" for x in pages.values()),
 "source_url_failures":sum(x["status"]!="downloaded" for x in pages.values()),
 "classified":counts,"released":False,"completed_event_fact_verifications":False,
 "limitations":["Every record was inspected for source content with one HTTP fetch per unique URL.",
 "Title matches are indicators; name, date, venue, pricing, reservation require independent official detail check.",
 "Some root-level or JS-populated pages cannot be verified with static HTTP text.",
 "Special known resolutions come from additional first-party web research and require auditable field changes before publish."]}
report={"schema_version":1,"summary":summary,"rows":results,
 "http_pages":[{k:v for k,v in a.items() if not k.startswith("_")} for a in pages.values()]}
(OUT/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
print("RECHECK67_SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)
for x in results:print("RECHECK67_ROW",json.dumps({k:x.get(k) for k in ("id","name","week","review_class","original_url","official_replacement_candidate","fresh_http_status","page_not_found")},ensure_ascii=False),flush=True)
if len(results)!=67 or len(urls)!=42:raise RuntimeError("Input ledger changed: expected 67 records and 42 URLs")
