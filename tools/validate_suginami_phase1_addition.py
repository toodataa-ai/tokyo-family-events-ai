#!/usr/bin/env python3
"""Strict non-destructive data-only gate for two official Suginami activities.

Prevents silent changes to original event records, collection logs, source
errors, other wards, and the original decisions or verification evidence.
Run only against immutable baseline data-production SHA.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from html.parser import HTMLParser
from urllib.request import Request, urlopen

ROOT = "site/data/"
IDS = {
    "2026-10-31": {
        "id": "suginami-official-22586",
        "url": "https://www.city.suginami.tokyo.jp/s113/event/22586.html",
        "date": "2026-11-01", "name": "昔の農家の暮らし体験（郷土博物館）",
        "venue": "杉並区立郷土博物館 古民家の庭（杉並区大宮1-20-8）",
        "time": "14:00〜16:00（雨天中止）",
        "source_tokens": ["2026年11月1日", "郷土博物館", "午後2時", "観覧料100円"],
        "reservation": False,
        "rubric": "family-fit-v1",
    },
    "2026-12-05": {
        "id": "suginami-official-23878",
        "url": "https://www.city.suginami.tokyo.jp/s113/event/23878.html",
        "date": "2026-12-06", "name": "稲わらでお正月飾りをつくろう（郷土博物館）",
        "venue": "杉並区立郷土博物館 古民家（杉並区大宮1-20-8）",
        "time": "10:00〜12:00",
        "source_tokens": ["2026年12月6日", "郷土博物館", "小学生", "8組", "11月5日"],
        "reservation": True,
        "rubric": "family-fit-v2",
    },
}
ALLOWED = {ROOT + k for k in ("manifest.json", "update_history.json")}
for week in IDS:
    ALLOWED.update(ROOT + week + suffix for suffix in (
        ".json", "-run.json", "-verification.json", "-decisions.json",
        "-events-suginami-official-20261027.json"))


def read_current(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_old(base, path):
    return json.loads(subprocess.check_output(
        ["git", "show", f"{base}:{path}"], text=True, encoding="utf-8"))


def same(a, b, message):
    if a != b:
        raise ValueError("PRE-EXISTING RECORD ALTERED: " + message)


def validate(base, *, check_live=True):
    changed = set(subprocess.check_output(
        ["git", "diff", "--name-only", base, "HEAD"], text=True).splitlines())
    if changed != ALLOWED:
        raise ValueError("unexpected file delta: " + repr(sorted(changed ^ ALLOWED)))
    old_manifest, manifest = (reader(ROOT+"manifest.json") for reader in
                              (lambda path: read_old(base, path), read_current))
    old_count = {w["sat"]: w["count"] for w in old_manifest["weekends"]}
    same({k:v for k,v in old_manifest.items() if k not in ("generated", "weekends")},
         {k:v for k,v in manifest.items() if k not in ("generated", "weekends")},
         "manifest metadata")
    if manifest["generated"] <= old_manifest["generated"]:
        raise ValueError("manifest generation timestamp did not advance")
    for before, after in zip(old_manifest["weekends"], manifest["weekends"]):
        week = before["sat"]
        same({k:v for k,v in before.items() if k != "count"},
             {k:v for k,v in after.items() if k != "count"},
             "weekend metadata " + week)
        if after["count"] != before["count"] + (1 if week in IDS else 0):
            raise ValueError("manifest count mismatch " + week)
    if len(manifest["weekends"]) != len(old_manifest["weekends"]) == 6:
        raise ValueError("wrong rolling horizon")

    for week, cfg in IDS.items():
        shard = week + "-events-suginami-official-20261027.json"
        before_week = read_old(base, ROOT+week+".json")
        new_week = read_current(ROOT+week+".json")
        same({k:v for k,v in before_week.items() if k not in
              ("generated","coverage","event_files")},
             {k:v for k,v in new_week.items() if k not in
              ("generated","coverage","event_files")}, week + " week metadata")
        same(before_week["event_files"]+[shard], new_week["event_files"], week+" shards")
        if new_week["generated"] <= before_week["generated"]:
            raise ValueError("week timestamp must advance " + week)
        events = read_current(ROOT+shard)
        if not isinstance(events, list) or len(events) != 1:
            raise ValueError("exactly one new event required per week")
        ev = events[0]
        for k, expected in (("id",cfg["id"]),("ward","杉並区"),
                            ("name",cfg["name"]),("date_start",cfg["date"]),
                            ("date_end",cfg["date"]),("venue",cfg["venue"]),
                            ("official_url",cfg["url"]),("url",cfg["url"]),
                            ("source",cfg["url"]),("time",cfg["time"]),
                            ("image",None)):
            same(expected, ev.get(k), f"new {cfg['id']} {k}")
        if ev.get("reservation",{}).get("required") is not cfg["reservation"]:
            raise ValueError("official reservation state mismatch " + cfg["id"])
        if ev.get("family_fit",{}).get("rubric_version") != cfg["rubric"]:
            raise ValueError("new activity has wrong family-fit rubric")
        if len((ev.get("family_fit") or {}).get("axes", {})) != 8:
            raise ValueError("must justify all eight family-fit axes")
        if cfg["id"].endswith("23878") and (
                "11/5" not in ev.get("reservation",{}).get("note","") or
                "8組" not in ev.get("description","")):
            raise ValueError("restricted workshop must show booking deadline and lottery capacity")
        old_cov, new_cov = before_week["coverage"], new_week["coverage"]
        for field, value in old_cov.items():
            if field not in ("candidate_count","published_count","wards"):
                same(value, new_cov.get(field), week+" coverage."+field)
        for field in ("candidate_count","published_count"):
            if new_cov[field] != old_cov[field]+1:
                raise ValueError("coverage count not +1: "+week+":"+field)
        old_wards = old_cov["wards"]; new_wards = new_cov["wards"]
        if len(old_wards)!=len(new_wards):
            raise ValueError("ward membership changed "+week)
        for a,b in zip(old_wards,new_wards):
            if a["ward"]!="杉並区":
                same(a,b,"unrelated ward coverage")
            else:
                same({k:v for k,v in a.items() if k not in ("note","candidate_count","published_count")},
                     {k:v for k,v in b.items() if k not in ("note","candidate_count","published_count")},
                     "Suginami historical source-check metadata")
                for field in ("candidate_count","published_count"):
                    if b[field]!=a[field]+1:
                        raise ValueError("Suginami per-ward count wrong "+field)
                if not b.get("note","").startswith(a.get("note","")):
                    raise ValueError("Suginami ward historical note changed")
        verify_path=ROOT+week+"-verification.json"
        old_v, now_v = read_old(base,verify_path),read_current(verify_path)
        same(old_v["events"],now_v["events"][:-1],week+" prior verification")
        same({k:v for k,v in old_v.items() if k not in ("events","summary")},
             {k:v for k,v in now_v.items() if k not in ("events","summary")},
             week+" verification metadata")
        for field, value in old_v["summary"].items():
            expect=value+1 if field in ("total","verified") else value
            same(expect,now_v["summary"].get(field),week+" verification."+field)
        vr=now_v["events"][-1]
        if not (vr["id"]==ev["id"] and vr["status"]=="verified" and vr["source"]==cfg["url"]
                and vr["source_kind"]=="public_official" and
                all(vr.get("fields",{}).get(f)=="pass" for f in ("name","date","venue","reservation","official_url"))):
            raise ValueError("new verification is not primary-source checked")
        decision_path=ROOT+week+"-decisions.json"
        old_d,now_d=read_old(base,decision_path),read_current(decision_path)
        same(old_d["decisions"],now_d["decisions"][:-1],week+" old decisions")
        same({k:v for k,v in old_d.items() if k not in ("decisions","summary")},
             {k:v for k,v in now_d.items() if k not in ("decisions","summary")},
             week+" decision metadata")
        for field,value in old_d["summary"].items():
            expect=value+1 if field in ("candidate_total","published") else value
            same(expect,now_d["summary"].get(field),week+" decision summary."+field)
        dr=now_d["decisions"][-1]
        if not (dr["candidate_id"]==ev["id"] and dr["name"]==ev["name"]
                and dr["decision"]=="published" and
                dr["family_fit"]==ev["family_fit"] and
                any(r.get("url")==cfg["url"] for r in dr.get("evidence",[]))):
            raise ValueError("published decision lacks matching official proof")
        run_path=ROOT+week+"-run.json"
        old_run,now_run=read_old(base,run_path),read_current(run_path)
        same(old_run,{k:v for k,v in now_run.items() if k!="suginami_official_phase1_addendum"
                      and k!="summary"} | {"summary":old_run["summary"]},week+" original run")
        for field,value in old_run["summary"].items():
            expect=value+1 if field in ("candidates","published","verified") and isinstance(value,int) else value
            same(expect,now_run["summary"].get(field),week+" run summary."+field)
        addition=now_run.get("suginami_official_phase1_addendum",{})
        if not (addition.get("base_data_production_sha")==base and
                addition.get("new_event_ids")==[cfg["id"]] and
                addition.get("new_shard")==shard and
                addition.get("source_failures_remain_unverified") is True):
            raise ValueError("incomplete historical-provenance addendum")

    old_history=read_old(base,ROOT+"update_history.json")
    new_history=read_current(ROOT+"update_history.json")
    same(old_history["history"],new_history["history"][:-1],"historic update log")
    same(old_history.get("schema_version"),new_history.get("schema_version"),"history version")
    change=new_history["history"][-1]
    if not (change.get("run_type")=="manual_verified_suginami_phase1_addition"
            and change.get("base_data_production_sha")==base
            and change.get("status")=="official_verified_addition"
            and change.get("added_weekly_records")==2
            and change.get("changed_existing_records")==0
            and change.get("removed_weekly_records")==0
            and change.get("source_failures_remain_unverified") is True
            and change.get("new_event_ids")==[x["id"] for x in IDS.values()]):
        raise ValueError("release history addendum cannot prove additive-only updates")
    if check_live:
        class VisibleText(HTMLParser):
            def __init__(self):
                super().__init__();self.out=[]
            def handle_data(self,text):
                self.out.append(text)
        for cfg in IDS.values():
            with urlopen(Request(cfg["url"],headers={"User-Agent":"TokyoFamilyEvents official primary proof gate"}),timeout=25) as response:
                if response.status!=200:
                    raise ValueError("official detail HTTP failure")
                html=response.read(4_000_000).decode("utf-8")
            parser=VisibleText();parser.feed(html)
            body="".join(x.strip() for x in parser.out)
            for token in (cfg["name"],*cfg["source_tokens"]):
                if "".join(token.split()) not in "".join(body.split()):
                    raise ValueError(f"official source mismatch {cfg['id']}: {token}")
    print("PASS: Suginami two official individual activities, no earlier data/event/decision/source changes")
    return True


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base-ref",required=True)
    p.add_argument("--skip-live",action="store_true")
    args=p.parse_args()
    try:
        validate(args.base_ref,check_live=not args.skip_live)
    except Exception as exc:
        print("BLOCKER: SUGINAMI_PHASE1_ADD_ONLY:",exc,file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    sys.exit(main())
