#!/usr/bin/env python3
import json, pathlib
from collections import Counter

DATA=pathlib.Path("site/data")
WEEKS=["2026-10-10","2026-10-17","2026-10-24","2026-10-31","2026-11-07","2026-11-14"]

def load(p): return json.loads(p.read_text(encoding="utf-8"))
def save(p,o): p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

for w in WEEKS:
    dp=DATA/f"{w}-decisions.json"; rp=DATA/f"{w}-run.json"
    d=load(dp); r=load(rp)
    excluded=[x for x in d.get("decisions",[]) if x.get("decision")=="excluded"]
    hard=sum(x.get("exclusion_type")=="hard" for x in excluded)
    soft=sum(x.get("exclusion_type")=="soft" for x in excluded)
    reasons=Counter((x.get("primary_reason_code") or "other") for x in excluded)
    d.setdefault("summary",{}).update({
        "hard_excluded":hard,
        "soft_excluded":soft,
        "reason_counts":dict(reasons),
    })
    r.setdefault("summary",{}).update({
        "excluded":len(excluded),
        "hard_excluded":hard,
        "soft_excluded":soft,
    })
    save(dp,d); save(rp,r)
    print(w,{"excluded":len(excluded),"hard":hard,"soft":soft,"reasons":dict(reasons)})

sp=DATA/"v16-rereview-summary.json"
s=load(sp)
s["unique_summary"]={"reviewed_unique":35,"promoted_unique":21,"kept_excluded_unique":14}
s["note"]="v1.6 targeted rereview only; full six-week rediscovery was not repeated. Per-week reviewed/promoted counts include the same multi-week event in each affected weekend."
save(sp,s)
