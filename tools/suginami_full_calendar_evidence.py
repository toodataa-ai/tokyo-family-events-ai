#!/usr/bin/env python3
"""Read-only actual HTTP crawl of Suginami's entire 42-day official calendar.

Never publishes data or upgrades unverified candidates to confirmed events.
Used to reconcile source coverage before allowing stage -> production promotion.
"""
import argparse
import concurrent.futures
import datetime as dt
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from holiday_after_collect import inspect, fetch_url
from html.parser import HTMLParser
import re

class OfficialText(HTMLParser):
    def __init__(self):
        super().__init__(); self.segments=[]; self.skip=0; self.title=''; self.in_h1=False
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','nav','footer','svg'): self.skip+=1
        if tag=='h1':self.in_h1=True
        if tag in ('p','div','h1','h2','h3','li','td','dd','tr','br'):
            self.segments.append('\\n')
    def handle_endtag(self,tag):
        if tag in ('script','style','nav','footer','svg') and self.skip:self.skip-=1
        if tag=='h1':self.in_h1=False
        if tag in ('p','div','h1','h2','h3','li','td','dd','tr'):self.segments.append('\\n')
    def handle_data(self,text):
        if self.skip:return
        text=re.sub(r'\\s+',' ',text).strip()
        if text:
            self.segments.append(text+' ')
            if self.in_h1:self.title+=text+' '
    def content(self):
        return '\\n'.join(s.strip() for s in ''.join(self.segments).split('\\n') if s.strip())[:12000]

def fetch_detail(candidate):
    item=dict(candidate)
    response=fetch_url(item['official_url'])
    item['detail_status']=response.get('status')
    item['detail_checked_at']=response.get('checked_at')
    item['detail_sha256']=response.get('sha256')
    item['detail_http_status']=response.get('http_status')
    item['detail_error']=response.get('error')
    if response.get('status')=='checked':
        parser=OfficialText()
        parser.feed(response['body'])
        item['official_h1']=parser.title.strip()
        item['official_text']=parser.content()
    return item

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def evidence(crawl_dir, start, end, workers=6):
    days = [start + dt.timedelta(days=n) for n in range((end-start).days+1)]
    months = sorted({(day.year, day.month) for day in days})
    base = "https://www.city.suginami.tokyo.jp/cgi-bin/event_cal_multi/calendar.cgi?"
    jobs = [
        {"kind":"explicit","source_id":"suginami_calendar_all",
         "url":base+f"day={d.day}&month={d.month}&type=3&year={d.year}",
         "day":d.isoformat()}
        for d in days
    ]
    jobs += [
        {"kind":"explicit","source_id":"suginami_calendar_all",
         "url":base+f"type=2&year={year}&month={month}",
         "month":f"{year}-{month:02d}"}
        for year,month in months
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        checked = list(pool.map(inspect, jobs))
    return jobs,checked

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage-data", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--start", default="2026-10-21")
    p.add_argument("--end", default="2026-12-01")
    args=p.parse_args()
    start,end = (dt.date.fromisoformat(v) for v in (args.start,args.end))
    if not (start <= end and (end-start).days <= 50):
        raise SystemExit("Invalid date range")
    args.output.mkdir(parents=True,exist_ok=True)
    manifest=read_json(args.stage_data / "manifest.json")
    staged_events=[]
    staged_decisions=[]
    for w in manifest["weekends"]:
        week=read_json(args.stage_data / w["file"])
        staged_events.extend(week.get("events",[]))
        for f in week.get("event_files",[]):
            staged_events.extend(read_json(args.stage_data / f))
        f=args.stage_data / f"{w['sat']}-decisions.json"
        if f.exists():
            staged_decisions.extend(read_json(f).get("decisions",[]))
    known_ids={str(x.get("id","")) for x in staged_events}
    known_urls={str(x.get(k,"")).split("?")[0].rstrip("/")
                for x in staged_events for k in ("official_url","url")}
    decision_ids={str(x.get("candidate_id","")) for x in staged_decisions}
    jobs,rows=evidence(args.output,start,end)
    all_candidates={}
    stats=[]
    for job,row in zip(jobs,rows):
        candidates=row.get("candidates",[])
        stats.append({
            "day":job.get("day"),"month":job.get("month"),"url":job["url"],
            "status":row.get("status"),"http_status":row.get("http_status"),
            "checked_at":row.get("checked_at"),"error":row.get("error"),
            "sha256":row.get("sha256"),"candidate_count":len(candidates),
            "candidate_ids":[x["candidate_id"] for x in candidates],
        })
        for c in candidates:
            cid=c["candidate_id"]
            if cid not in all_candidates:
                u=str(c.get("official_url") or c.get("discovery_url") or "").split("?")[0].rstrip("/")
                all_candidates[cid]={"candidate_id":cid,"name":c.get("name"),
                                      "official_url":u,"dates":[],"month_indexes":[],
                                      "in_staged_events":cid in known_ids or u in known_urls,
                                      "in_staged_decisions":cid in decision_ids}
            if job.get("day") and job["day"] not in all_candidates[cid]["dates"]:
                all_candidates[cid]["dates"].append(job["day"])
            if job.get("month") and job["month"] not in all_candidates[cid]["month_indexes"]:
                all_candidates[cid]["month_indexes"].append(job["month"])
    # Preserve every official page ID, and actually inspect every detail URL.
    # HTTP proof is read-only; it is never treated as family-fit approval.
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        detail_rows=list(pool.map(fetch_detail,sorted(all_candidates.values(),key=lambda x:x["candidate_id"])))
    for i in range(0,len(detail_rows),25):
        (args.output/f"candidate_details_{i//25+1:02d}.json").write_text(
            json.dumps(detail_rows[i:i+25],ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
    (args.output/"all_candidate_index.json").write_text(
        json.dumps([{k:v for k,v in row.items() if k not in ("official_text",)}
                    for row in detail_rows],ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
    detail_failures=[x for x in detail_rows if x["detail_status"]!="checked"]
    failures=[x for x in stats if x["status"]!="checked"]
    missing=[c for c in all_candidates.values() if not c["in_staged_events"] and not c["in_staged_decisions"]]
    result={
        "run_scope":"read_only_actual_http_evidence_2026_suginami_full_calendar",
        "publishable":False,
        "start":str(start),"end":str(end),
        "days_scanned":sum(1 for x in stats if x["day"]),
        "monthly_indexes_scanned":sum(1 for x in stats if x["month"]),
        "failed_requests":len(failures),
        "distinct_official_candidate_ids":len(all_candidates),
        "official_detail_fetch_failures":len(detail_failures),
        "candidate_ids_needing_manual_review":len(missing),
        "no_published_data_mutation":True,
        "unreviewed_official_candidate_examples":missing[:100],
        "failures":failures,
        "checked_requests":stats,
    }
    (args.output/"summary.json").write_text(json.dumps({k:v for k,v in result.items() if k!="checked_requests"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (args.output/"http_evidence.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k not in ("unreviewed_official_candidate_examples","checked_requests")},ensure_ascii=False))
    if failures:
        print("FAIL CLOSED: official website request errors; never mark checked",file=sys.stderr)
        return 2
    if missing:
        print("FAIL CLOSED: candidate decisions not yet reconciled; do not publish",file=sys.stderr)
        return 3
    return 0

if __name__=="__main__":
    raise SystemExit(main())
