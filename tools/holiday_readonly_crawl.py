#!/usr/bin/env python3
"""Read-only actual-source evidence census. Never invent completed research."""
import concurrent.futures as cf
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import quote,urljoin
from urllib.request import urlopen,Request
from urllib.error import HTTPError,URLError

OUT=Path("/tmp/tokyo-holiday-evidence");OUT.mkdir(exist_ok=True)
DATA=Path("data-src/site/data");POLICY=Path("released/site/data")
REG=json.loads((POLICY/"discovery_sources.json").read_text())
MAN=json.loads((DATA/"manifest.json").read_text())
WARDS=[("千代田区","www.city.chiyoda.lg.jp"),("中央区","www.city.chuo.lg.jp"),("港区","www.city.minato.tokyo.jp"),("新宿区","www.city.shinjuku.lg.jp"),("文京区","www.city.bunkyo.lg.jp"),("台東区","www.city.taito.lg.jp"),("墨田区","www.city.sumida.lg.jp"),("江東区","www.city.koto.lg.jp"),("品川区","www.city.shinagawa.tokyo.jp"),("目黒区","www.city.meguro.tokyo.jp"),("大田区","www.city.ota.tokyo.jp"),("世田谷区","www.city.setagaya.lg.jp"),("渋谷区","www.city.shibuya.tokyo.jp"),("中野区","www.city.tokyo-nakano.lg.jp"),("杉並区","www.city.suginami.tokyo.jp"),("豊島区","www.city.toshima.lg.jp"),("北区","www.city.kita.lg.jp"),("荒川区","www.city.arakawa.tokyo.jp"),("板橋区","www.city.itabashi.tokyo.jp"),("練馬区","www.city.nerima.tokyo.jp"),("足立区","www.city.adachi.tokyo.jp"),("葛飾区","www.city.katsushika.lg.jp"),("江戸川区","www.city.edogawa.tokyo.jp")]
class Parser(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.active=None;self.title="";self.intitle=False
 def handle_starttag(self,t,a):
  if t=="a":self.active={"href":dict(a).get("href",""),"label":""}
  if t=="title":self.intitle=True
 def handle_endtag(self,t):
  if t=="a" and self.active:
   self.active["label"]=" ".join(self.active["label"].split())[:160]
   if self.active["href"] and self.active["label"]:self.links.append(self.active)
   self.active=None
  if t=="title":self.intitle=False
 def handle_data(self,s):
  if self.intitle:self.title+=s
  if self.active:self.active["label"]+=s
def get(item):
 kind,url=item
 row={"kind":kind,"url":url,"checked_at":dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="seconds"),"status":"error"}
 try:
  rq=Request(url,headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/129 Safari/537.36","Accept-Language":"ja-JP,ja;q=0.9,en;q=0.4"})
  with urlopen(rq,timeout=17) as f:
   content=f.read(1000000);row.update(http_status=f.status,final_url=f.geturl(),content_type=f.headers.get("Content-Type",""))
  if row["http_status"]!=200:raise ValueError("HTTP status not 200")
  row.update(status="checked",bytes=len(content),sha256=hashlib.sha256(content).hexdigest())
  for enc in ("utf-8","cp932"):
   try:html=content.decode(enc);break
   except UnicodeDecodeError:continue
  else:html=content.decode("utf-8","replace")
  p=Parser();p.feed(html);row["title"]=p.title[:180];row["link_count"]=len(p.links)
  row["candidate_links"]=[{"name":x["label"],"url":urljoin(url,x["href"])} for x in p.links if any(t in x["label"] for t in ("2026","まつり","祭","フェア","子ども","こども","親子","体験","フェス","収穫"))][:90]
 except (HTTPError,URLError,TimeoutError,OSError,ValueError) as e:row["error"]=str(e)[:260]
 return row
def fetch_all(jobs):
 with cf.ThreadPoolExecutor(max_workers=9) as pool:
  out=list(pool.map(get,jobs))
 for row in out:print(json.dumps({k:v for k,v in row.items() if k!="candidate_links"},ensure_ascii=False),flush=True)
 return out
explicit=[]
for s in REG["explicit_sources"]:
 if not s.get("enabled"):continue
 for template in s["search_urls"]:
  varying=any(v in template for v in ("{YYYY-MM}","{YYYY}","{MM}"))
  for month in (("2026-10","2026-11") if varying else ("",)):
   url=template.replace("{YYYY-MM}",month).replace("{YYYY}",month[:4]).replace("{MM}",month[5:])
   explicit.append((s["id"],url))
queries=[]
for ward,host in WARDS:
 q=ward+" 2026年11月21日 22日 23日 子供 親子 イベント 祭 体験"
 queries.extend([(ward+"_search","https://www.bing.com/search?format=rss&q="+quote(q)),(ward+"_official","https://"+host+"/")])
official=set()
for w in MAN["weekends"]:
 week=json.loads((DATA/w["file"]).read_text())
 audit=json.loads((DATA/week["verification_file"]).read_text())
 for ev in audit["events"]:
  if ev.get("source","").startswith("https://"):official.add(ev["source"])
old=[("previous_official",url) for url in sorted(official)]
print("CHECK_COUNTS",json.dumps({"explicit":len(explicit),"ward_queries":len(queries),"previous_official_urls":len(old)}),flush=True)
a=fetch_all(explicit);b=fetch_all(queries);c=fetch_all(old)
required_ids={s["id"] for s in REG["explicit_sources"] if s.get("enabled") and s.get("required")}
source_errors=[{"id":x["kind"],"url":x["url"],"error":x.get("error")} for x in a if x["kind"] in required_ids and x["status"]!="checked"]
search_errors=[{"ward":x["kind"],"url":x["url"],"error":x.get("error")} for x in b if x["status"]!="checked"]
summary={"as_of":"2026-10-13","version":"v1.15","read_only":True,"candidate_generated":False,"required_sources_total":len([x for x in explicit if x[0] in required_ids]),"required_source_errors":source_errors,"ward_requests_total":len(queries),"ward_errors":search_errors,"previous_official_total":len(old),"previous_official_success":sum(x["status"]=="checked" for x in c),"limitations":["HTTP 200 never establishes event/date validity","No output is a publishable event or a completed 23-ward official verification","Never re-label previous-run evidence as new-run evidence."]}
for file,data in (("summary",summary),("explicit",a),("ward-search",b),("previous-official",c)):
 (OUT/(file+".json")).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
print("FINAL_AUDIT",json.dumps({k:v for k,v in summary.items() if k not in ("required_source_errors","ward_errors")},ensure_ascii=False),flush=True)
if source_errors or search_errors:raise SystemExit("BLOCKER: required discovery source/query not fully retrieved; see artifact")
