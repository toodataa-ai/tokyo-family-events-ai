#!/usr/bin/env python3
"""Read-only official Suginami calendar HTTP probe. Writes diagnostics to /tmp only."""
import datetime as dt
import hashlib
import html
from html.parser import HTMLParser
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://www.city.suginami.tokyo.jp/cgi-bin/event_cal_multi/calendar.cgi"
NOW = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="seconds")

class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active = None
        self.links = []
        self.plain = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.active = {"href": dict(attrs).get("href",""),"label":""}
    def handle_data(self, data):
        self.plain.append(data)
        if self.active is not None:
            self.active["label"] += data
    def handle_endtag(self, tag):
        if tag == "a" and self.active is not None:
            self.active["label"] = " ".join(self.active["label"].split())
            if self.active["label"]:
                self.links.append(self.active)
            self.active = None

def probe(kind, url):
    h = {"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/127 Safari/537.36",
         "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
         "Accept-Language":"ja-JP,ja;q=0.9,en-US;q=0.5",
         "Referer":"https://www.city.suginami.tokyo.jp/event/index.html"}
    row={"kind":kind,"url":url,"checked_at":NOW,"status":"error"}
    data=b""
    try:
        with urlopen(Request(url,headers=h),timeout=20) as r:
            data=r.read(3_000_000)
            row.update(status_code=r.status,final_url=r.geturl(),
                       content_type=r.headers.get("Content-Type",""),
                       content_length=len(data))
    except HTTPError as e:
        data=e.read(200_000)
        row.update(status_code=e.code,final_url=e.url,
                   content_type=e.headers.get("Content-Type",""),content_length=len(data),
                   error=f"HTTP {e.code}")
    except (URLError,TimeoutError,OSError) as e:
        row["error"]=type(e).__name__ + ": " + str(e)[:450]
    if data:
        row["sha256"]=hashlib.sha256(data).hexdigest()
        enc="utf-8"
        for candidate in ("utf-8", "cp932"):
            try: body=data.decode(candidate);enc=candidate;break
            except UnicodeDecodeError: pass
        else:body=data.decode("utf-8",errors="replace");enc="utf-8-replace"
        row["encoding"]=enc
        dom=Links()
        dom.feed(body)
        text=" ".join(" ".join(dom.plain).split())
        row["title_excerpt"]=text[:350]
        row["contains_year"]= "2026年" in text or "2026 年" in text
        row["contains_omatsuri"]= "おまつり" in text
        row["contains_event_table"]= "開催日" in text and "タイトル" in text
        row["matching_links"]=[a for a in dom.links if
           ("event" in a["href"] or "event" in a["label"].lower() or "祭" in a["label"]
             or "まつり" in a["label"] or "2026" in a["href"] )][:45]
        row["all_anchor_count"]=len(dom.links)
        if "required_original" in kind:
            row["links_tail"]=dom.links[-35:]
        row["body_sample"]=text[:1200]
    if row.get("status_code")==200 and row.get("contains_year"):
        row["status"]="downloaded"
    return row

out=[]
for m in (10,11):
    queries=[
        ("required_original", [('type',2),('year',2026),('month',m),('event_category',5),('siteid',1)]),
        ("no_siteid", [('type',2),('year',2026),('month',m),('event_category',5)]),
        ("calendar_unfiltered_control",[('type',2),('year',2026),('month',m)]),
        ("category_before_dates",[('event_category',5),('month',m),('type',2),('year',2026)]),
    ]
    for kind,params in queries:
        row=probe(f"{m:02}-{kind}",BASE+"?"+urlencode(params))
        print(json.dumps({k:v for k,v in row.items() if k not in ("matching_links","body_sample","links_tail")},ensure_ascii=False),flush=True)
        if kind=="required_original":
            print("OFFICIAL_CALENDAR_LINKS "+str(m)+" "+json.dumps(row.get("links_tail",[]),ensure_ascii=False),flush=True)
        out.append(row)
os.makedirs("/tmp/suginami-calendar-probe",exist_ok=True)
with open("/tmp/suginami-calendar-probe/probe.json","w",encoding="utf-8") as f:
    json.dump({"checked_at":NOW,"results":out},f,ensure_ascii=False,indent=2)
confirmed=[x for x in out if "required_original" in x["kind"] and x["status"]=="downloaded"]
if len(confirmed)!=2:
    print("RESEARCH_BLOCKER: required category=5 URL not confirmed for both months; do not mark checked.",file=sys.stderr)
    sys.exit(2)
print("Both exact required URLs returned HTML 200; content inspection still required.",flush=True)
