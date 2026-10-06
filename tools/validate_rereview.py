#!/usr/bin/env python3
import argparse, json, pathlib, re, sys, unicodedata
HTTP=re.compile(r"^https?://",re.I)
MATERIAL={"adult_oriented","narrow_fandom","specialist_content","passive_only","night_burden","crowd_burden","high_cost","reservation_difficult","age_mismatch"}
SEVERE={"alcohol_primary","reservation_unavailable","late_night_primary","extreme_cost","content_intensity"}
NONPRIMARY={"family_value_low","child_program_absent"}

def load(p): return json.loads(p.read_text(encoding="utf-8"))
def norm(s):
    s=unicodedata.normalize("NFKC",s or "")
    s=re.sub(r"^祝[）)]","",s).strip()
    return re.sub(r"\s+"," ",s)
def events(data_dir,week):
    out=list(week.get("events") or [])
    for f in week.get("event_files") or []: out+=load(data_dir/f)
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("data_dir",nargs="?",default="site/data"); ap.add_argument("--strict",action="store_true"); a=ap.parse_args()
    d=pathlib.Path(a.data_dir); manifest=load(d/"manifest.json"); errors=[]; seen=0
    for ent in manifest.get("weekends") or []:
        wp=d/ent["file"]; w=load(wp); run=load(d/w["run_file"])
        rf=(run.get("source_data") or {}).get("rereview_file")
        if not rf: continue
        seen+=1; rp=d/rf
        if not rp.exists(): errors.append(f"{rf}: missing"); continue
        doc=load(rp)
        if doc.get("review_version")!="v1.6" or doc.get("rubric_version")!="family-fit-v2": errors.append(f"{rf}: invalid v1.6 review header")
        rows=doc.get("reviews") or []; s=doc.get("summary") or {}
        promoted=sum(x.get("result")=="published" for x in rows)
        kept_soft=sum(x.get("result")=="kept_excluded" and x.get("exclusion_type")=="soft" for x in rows)
        kept_hard=sum(x.get("result")=="kept_excluded" and x.get("exclusion_type")=="hard" for x in rows)
        if s.get("reviewed")!=len(rows) or s.get("promoted")!=promoted or s.get("kept_soft_excluded")!=kept_soft or s.get("kept_hard_excluded")!=kept_hard:
            errors.append(f"{rf}: summary mismatch")
        evs=events(d,w); evnames={norm(x.get("name","")) for x in evs}
        decisions=load(d/(run.get("source_data") or {}).get("decision_file"))
        bycid={x.get("candidate_id"):x for x in decisions.get("decisions") or []}
        for i,r in enumerate(rows,1):
            p=f"{rf}: review #{i}"
            if r.get("original_decision")!="excluded": errors.append(f"{p}: original_decision must be excluded")
            if r.get("result") not in ("published","kept_excluded"): errors.append(f"{p}: invalid result")
            fit=r.get("family_fit") or {}
            if fit.get("rubric_version")!="family-fit-v2": errors.append(f"{p}: family-fit-v2 required")
            axes=fit.get("axes") or {}
            for axis in ["child_target","interactivity","age_fit","stay_flexibility","burden","cost","reservation","family_value"]:
                if not isinstance(axes.get(axis),dict) or not axes[axis].get("grade") or not axes[axis].get("reason"): errors.append(f"{p}: missing axis {axis}")
            pos=r.get("positive_signals"); neg=r.get("negative_signals")
            if not isinstance(pos,list) or not isinstance(neg,list): errors.append(f"{p}: positive_signals/negative_signals arrays required"); continue
            evd=r.get("evidence") or []
            if not any(isinstance(x,dict) and HTTP.match(str(x.get("url") or "")) for x in evd): errors.append(f"{p}: evidence URL required")
            base=bycid.get(r.get("candidate_id"))
            if not base: errors.append(f"{p}: candidate not found in decision audit"); continue
            if r.get("result")=="published":
                if base.get("decision")!="published": errors.append(f"{p}: base decision must now be published")
                if norm(r.get("name","")) not in evnames: errors.append(f"{p}: promoted event missing from event data")
            else:
                if base.get("decision")!="excluded": errors.append(f"{p}: kept event must remain excluded")
                if r.get("exclusion_type")=="soft":
                    overall=fit.get("overall"); primary=r.get("primary_reason_code")
                    if overall=="A": errors.append(f"{p}: overall A cannot remain soft-excluded")
                    if primary in NONPRIMARY: errors.append(f"{p}: weak code cannot be primary reason")
                    material=len(set(neg)&MATERIAL); severe=bool(set(neg)&SEVERE)
                    if material<2 and not severe: errors.append(f"{p}: soft exclusion needs >=2 material negatives or severe factor")
                    if overall=="B" and not str(r.get("tradeoff_reason") or "").strip(): errors.append(f"{p}: overall B needs tradeoff_reason")
        print(f"REREVIEW {ent['file']}: reviewed={len(rows)}, promoted={promoted}, kept_soft={kept_soft}, kept_hard={kept_hard}")
    if not seen:
        print("REREVIEW: no patch files referenced (valid historical state)")
    if errors:
        for e in errors: print("ERROR:",e)
        sys.exit(1)
    print("OK: v1.6 targeted rereview audit")
if __name__=="__main__": main()
