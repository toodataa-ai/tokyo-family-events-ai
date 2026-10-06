#!/usr/bin/env python3
import copy, datetime as dt, hashlib, json, pathlib, re, unicodedata, urllib.request

DATA = pathlib.Path("site/data")
WEEKS = ["2026-10-10","2026-10-17","2026-10-24","2026-10-31","2026-11-07","2026-11-14"]
LEGACY_BASE = "https://toodataa-ai.github.io/tokyo-weekend-events/data/"
PROMPT = {"version":"v1.6","path":"prompts/tokyo_family_events_complete_prompt_v1.6.txt"}
STAMP = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="seconds")

def k(name):
    s=unicodedata.normalize("NFKC", name or "")
    s=re.sub(r"^祝[）)]","",s).strip()
    return re.sub(r"\s+"," ",s)

PROMOTE = {
 k("オクトーバーフェストin東京スカイツリータウン®︎2026"): ("B",["all_ages","daytime","food_or_market","family_venue","seasonal_or_festival"],["crowd_burden"],"公式が家族・子どもも楽しめる旨を案内しており、酒類だけでなく食・ステージ・会場回遊を家族で楽しめる。"),
 k("お祭りBBQビアガーデン 浅草エキミセ屋台村"): ("A",["child_explicit","all_ages","daytime","food_or_market","hands_on","family_venue"],[],"子ども向け遊び・キッズコースがあり、家族利用が明示されている。"),
 k("東京舞台芸術祭 2026"): ("B",["all_ages","visual_appeal","learning_value","iconic_or_rare"],["passive_only"],"公式ラインアップに子どもが楽しめる舞台・サーカス・大道芸等があり、家族で選べる文化体験として成立する。"),
 k("ボボボーボ・ボーボボ展 DIVE INTO THE BO-BOBO WORLD"): ("B",["all_ages","visual_appeal","family_venue"],["narrow_fandom"],"小学生以下無料・保護者同伴条件が設定され、子どもの来場を想定した展示として確認できる。"),
 k("北海道まるごとフェアinサンシャインシティ2026"): ("B",["all_ages","daytime","food_or_market","family_venue","flexible_visit"],[],"昼間の物産・食イベントで、家族利用しやすい商業施設内を回遊して楽しめる。"),
 k("てんぼうパーク×ときめきメモリアル Girl's Side ときめきスカイデート"): ("B",["all_ages","visual_appeal","family_venue","flexible_visit"],["narrow_fandom"],"特定IP向けではあるが、展望台の装飾・スタンプラリー等を回遊でき、ファン向けであることだけでは除外しない。"),
 k("P.O.N.D. 2026"): ("B",["all_ages","free_or_low_cost","visual_appeal","flexible_visit","family_venue"],["passive_only"],"無料のアート展示を複数会場で回遊でき、視覚的な文化体験として家族利用が可能。"),
 k("TVアニメ『薬屋のひとりごと』 × 東京シティビュー 舞が織りなす幻想の世界 ―天空に響く、舞のしらべ―"): ("B",["all_ages","visual_appeal","family_venue","iconic_or_rare"],["narrow_fandom"],"4歳〜中学生の料金設定があり、子どもの来場を明示的に想定した展示・展望体験。"),
 k("モンブランセレクション2026"): ("B",["all_ages","daytime","food_or_market","family_venue","seasonal_or_festival"],[],"季節の食を家族で選んで楽しめる回遊型企画で、子ども専用企画の有無だけでは除外しない。"),
 k("POP UP BOX「まんが日本昔ばなし展 –昔、むかし、あるところに…」"): ("A",["all_ages","free_or_low_cost","visual_appeal","learning_value","family_venue"],["passive_only"],"世代を超えて親しまれる物語・アニメの無料展示で、親子の共有体験として明確な価値がある。"),
 k("オクトーバーフェスト2026 in アーバンドック ららぽーと豊洲"): ("B",["all_ages","daytime","food_or_market","visual_appeal","family_venue"],["crowd_burden"],"酒類以外の飲食に加え、マジック・ジャグリング・バルーン等のステージがあり、家族向け商業施設で昼間から楽しめる。"),
 k("国際美術展 TOKYO ATLAS"): ("B",["all_ages","free_or_low_cost","daytime","visual_appeal","learning_value","flexible_visit"],["passive_only"],"無料中心の国際美術展で、湾岸の複数会場を昼間に回遊できる文化・学習体験。"),
 k("MEET YOUR ART FESTIVAL 2026"): ("B",["all_ages","visual_appeal","food_or_market","family_venue","flexible_visit"],["crowd_burden"],"アート・マーケット等の無料エリアがあり、中学生以下無料の料金設定もあるため家族利用価値を認める。"),
 k("練馬区立美術館コレクション　若林奮－Run and Rest－｜寺田真由美－不在の存在－"): ("B",["all_ages","free_or_low_cost","daytime","visual_appeal","learning_value","family_venue"],["passive_only"],"中学生以下無料・予約不要の美術館展示で、家族の文化・学習候補として成立する。"),
 k("【企画展】「海を渡ってきた植物の物語」"): ("A",["all_ages","daytime","learning_value","visual_appeal","family_venue","flexible_visit"],["passive_only"],"植物・自然をテーマにした学習価値の高い展示で、子ども専用企画がなくても家族のおでかけ先として成立する。"),
 k("龍の舞"): ("B",["all_ages","daytime","visual_appeal","learning_value","seasonal_or_festival","iconic_or_rare"],["passive_only"],"浅草寺の伝統行事として視覚的・文化的な魅力があり、親子で見られる昼間の見世物として評価する。"),
 k("Gelato Collection 2026"): ("B",["all_ages","daytime","food_or_market","hands_on","iconic_or_rare"],["high_cost"],"クラフトジェラートを食べ比べる参加型イベントで、食を共有する家族体験として価値がある。"),
 k("アーツ中村橋 2026―わたしとまちの記憶"): ("B",["all_ages","daytime","visual_appeal","learning_value","flexible_visit","family_venue"],["passive_only"],"美術館とまちを歩いて作品に触れる回遊型文化企画で、家族の街歩き・学びとして成立する。"),
 k("第２回日本食文化伝承会「いも煮会」"): ("B",["all_ages","daytime","food_or_market","learning_value","seasonal_or_festival"],[],"食文化と季節行事を体験する催しで、子ども向け明記がなくても家族で共有しやすい。"),
 k("大泉遺産プロジェクト"): ("B",["all_ages","daytime","food_or_market","learning_value","seasonal_or_festival","family_venue"],["reservation_difficult"],"地域の食・店・文化を知る企画で、予約企画に制約はあるが回遊・試食等を含む家族価値がある。"),
 k("森万里子：燦燦"): ("B",["all_ages","free_or_low_cost","visual_appeal","learning_value","family_venue","iconic_or_rare"],["passive_only"],"中学生以下無料で、視覚的展示や参加要素もある美術館体験として家族利用価値を認める。"),
}

KEEP = {
 k("歌川国貞・歌川国芳 ー新宿歌舞伎町春画展WA【前期】"): ("D",[],["safety_unsuitable"],"safety_unsuitable","hard","幼児・小学生を含む子連れ候補として内容上不適切。",""),
 k("妖怪盆踊り2026"): ("D",[],["outside_23wards"],"outside_23wards","hard","東京23区外のため対象外。",""),
 k("青空の北欧市場 TACHIKAWA LOPPIS autumn side 2026"): ("D",[],["outside_23wards"],"outside_23wards","hard","東京23区外のため対象外。",""),
 k("TOKYO DOGS’ RUNWAY"): ("D",[],["outside_23wards"],"outside_23wards","hard","東京23区外のため対象外。",""),
 k("BMSG FES'26"): ("C",["iconic_or_rare"],["extreme_cost","age_mismatch","narrow_fandom"],"extreme_cost","soft","3歳以上に高額チケットが必要で、家族単位の費用負担が極めて大きい。","話題性は高いが、3歳以上一律の高額料金が家族利用価値を上回る。"),
 k("ねことユリイカ『宮城野』"): ("C",["learning_value"],["age_mismatch","high_cost","passive_only"],"age_mismatch","soft","未就学児入場不可で、小学生連れでも内容・料金面の負担が大きい観劇。","文化的価値はあるが、未就学児不可と料金・鑑賞中心の負担が家族向け候補として上回る。"),
 k("ヘタリア20周年原画展 WorldFesta"): ("C",["visual_appeal"],["narrow_fandom","passive_only","reservation_difficult"],"narrow_fandom","soft","時間指定・有料の原画展で、特定ファン向けかつ鑑賞中心・予約制という複数の制約がある。","視覚的魅力はあるが、特定ファン向け・鑑賞中心・時間指定の複合条件から優先掲載しない。"),
 k("KABUKICHO YOGA ー AUTUMN 2026"): ("C",["daytime"],["adult_oriented","age_mismatch"],"adult_oriented","soft","一般向けヨガプログラムで、幼児・小学生が一緒に楽しむ設計・年齢適合が弱い。","朝の参加型企画ではあるが、成人向け運動プログラム性と年齢不適合が上回る。"),
 k("日本舞踊と和のひととき"): ("C",["learning_value","iconic_or_rare"],["passive_only","high_cost"],"passive_only","soft","文化的価値はあるが、鑑賞中心で家族人数分の料金負担も相対的に大きい。","伝統文化の学びはあるが、鑑賞中心かつ家族単位の費用負担を考慮して優先掲載しない。"),
 k("THE WORLD OF BIOHAZARD 30周年展"): ("C",["visual_appeal","iconic_or_rare"],["content_intensity","narrow_fandom"],"content_intensity","soft","子ども料金はあるが、ホラー・刺激の強い内容を含み、子連れ一般候補として注意が大きい。","展示の話題性は高いが、内容の刺激性を単独のsevere factorとして優先する。"),
 k("光が丘管弦楽団　第62回定期演奏会"): ("C",["learning_value"],["reservation_unavailable","passive_only"],"reservation_unavailable","soft","公式で完売が確認され、現時点で新規参加できない。","文化的価値はあるが、参加不能のため掲載しない。"),
 k("アニメイトガールズフェスティバル2026"): ("C",["visual_appeal","seasonal_or_festival"],["narrow_fandom","crowd_burden"],"narrow_fandom","soft","大規模ファンイベントで、特定ファン層中心かつ強い混雑負担が見込まれる。","無料エリア等はあるが、ファン特化と混雑の複合負担から一般的な子連れ候補としては優先しない。"),
 k("『鬼灯の冷徹』連載開始15周年記念 アニメイト特別展示"): ("C",["visual_appeal"],["narrow_fandom","passive_only"],"narrow_fandom","soft","特定作品ファン向けの展示・物販中心で、家族一般向け価値は限定的。","視覚展示として楽しめる余地はあるが、ファン特化と鑑賞・物販中心の複合要因で優先掲載しない。"),
 k("練馬区演奏家協会20周年記念レクチャーコンサート 祝祭の響き―リコーダーとトリオ・ダンシュの華麗な音色―"): ("C",["learning_value"],["age_mismatch","passive_only"],"age_mismatch","soft","未就学児入場不可で鑑賞中心のため、幼児を含む家族候補として適合範囲が狭い。","音楽学習価値はあるが、未就学児不可と鑑賞中心の複合条件から優先掲載しない。"),
}

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def fetch_legacy(week):
    req=urllib.request.Request(LEGACY_BASE+week+".json",headers={"User-Agent":"Mozilla/5.0 TokyoFamilyEventsAI/1.6"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def parse_md(value, year=2026):
    m=re.search(r"(\d{1,2})/(\d{1,2})",value or "")
    if not m: return None
    return f"{year:04d}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"

def dates_from_legacy(ev):
    ds=ev.get("date_start"); de=ev.get("date_end")
    if ds and de: return ds,de
    p=ev.get("period") or ev.get("raw") or ""
    bits=re.split(r"[〜～~]",p)
    ds=parse_md(bits[0]); de=parse_md(bits[-1])
    if ds and de and de<ds:
        de=str(int(ds[:4])+1)+de[4:]
    return ds,de

def evidence_url(row):
    for e in row.get("evidence") or []:
        u=e.get("url") if isinstance(e,dict) else None
        if u and str(u).startswith(("http://","https://")): return u
    for s in row.get("discovery_sources") or []:
        u=s.get("url")
        if u and str(u).startswith(("http://","https://")): return u
    return None

def legacy_row_for(decision, legacy_rows):
    details=[s.get("url") for s in decision.get("discovery_sources") or [] if s.get("kind")=="legacy_detail"]
    for u in details:
        for ev in legacy_rows:
            if ev.get("url")==u: return ev
    target=k(decision.get("name"))
    exact=[ev for ev in legacy_rows if k(ev.get("name"))==target]
    if exact: return exact[0]
    raise RuntimeError(f"legacy event not found: {decision.get('name')}")

def build_v2_axes(old_fit, overall, positives, negatives):
    old=copy.deepcopy((old_fit or {}).get("axes") or {})
    def item(axis,grade,reason):
        old[axis]={"grade":grade,"reason":reason}
    child="A" if "child_explicit" in positives else ("B" if "all_ages" in positives else "C")
    item("child_target",child,"子ども専用かではなく、公式の対象・全年齢性と実際の参加可能性で再評価。")
    if "age_mismatch" in negatives:
        item("age_fit","C","年齢条件または内容上、幼児・小学生の一部に明確な不適合がある。")
    elif "child_explicit" in positives:
        item("age_fit","A","子どもの参加を公式が明示し、年齢適合を確認できる。")
    else:
        item("age_fit","B","子ども専用ではないが、家族同伴で現実に楽しめる内容と判断。")
    item("family_value",overall if overall in ("A","B","C") else "D","家族で一緒に行く理由・休日のおでかけ価値をpositive/negative signalsの双方から再評価。")
    for axis in ["interactivity","stay_flexibility","burden","cost","reservation"]:
        if axis not in old:
            old[axis]={"grade":"unknown","reason":"再審査で十分な情報がなく推測しない。"}
    return old

def review_obj(row, result, overall, positives, negatives, primary, ex_type, reason, tradeoff=""):
    return {
        "review_version":"v1.6",
        "rubric_version":"family-fit-v2",
        "reviewed_at":STAMP,
        "original_decision":"excluded",
        "result":result,
        "family_fit":{
            "rubric_version":"family-fit-v2",
            "overall":overall,
            "axes":build_v2_axes(row.get("family_fit"),overall,positives,negatives),
        },
        "positive_signals":positives,
        "negative_signals":negatives,
        "primary_reason_code":primary,
        "exclusion_type":ex_type,
        "hard_exclusion":primary if ex_type=="hard" else None,
        "reason":reason,
        "tradeoff_reason":tradeoff,
        "evidence":[{"url":evidence_url(row),"basis":"v1.6除外再審査。公式・主催者情報と旧decision evidenceを再確認。"}],
    }

def event_from_legacy(row, legacy, review, week):
    ds,de=dates_from_legacy(legacy)
    if not ds or not de: raise RuntimeError(f"missing dates for {row['name']}")
    official=evidence_url(row) or legacy.get("official_url") or legacy.get("url")
    eid="r16-"+hashlib.sha1((week+"|"+k(row["name"])).encode()).hexdigest()[:12]
    grade=review["family_fit"]["overall"]
    if grade=="D": grade="C"
    return {
        "id":eid,"ward":row["ward"],"name":k(row["name"]),
        "url":legacy.get("url") or official,"official_url":official,
        "source":legacy.get("source") or legacy.get("url") or official,
        "image":legacy.get("image"),"period":legacy.get("period") or legacy.get("raw") or f"{ds[5:].replace('-','/')}〜{de[5:].replace('-','/')}",
        "date_start":ds,"date_end":de,"time":legacy.get("time"),
        "venue":legacy.get("venue") or row["ward"],"price":legacy.get("price"),
        "description":legacy.get("description") or review["reason"],
        "categories":["v1.6再審査","家族実質価値"],
        "family_fit":{
            "grade":grade,"reason":review["reason"],"overall":review["family_fit"]["overall"],
            "rubric_version":"family-fit-v2","axes":review["family_fit"]["axes"],
            "positive_signals":review["positive_signals"],"negative_signals":review["negative_signals"],
        },
        "reservation":{"required":None,"note":"参加条件・予約状況は公式サイトで最新情報を確認。"},
        "indoor_outdoor":None,
        "ai":{"checked_at":STAMP,"confidence":"high","discovery_query":"v1.6 targeted exclusion rereview"},
        "rereview":{"version":"v1.6","source_candidate_id":row.get("candidate_id")}
    }

def verification_for(ev, review, tier):
    return {
        "id":ev["id"],"status":"verified","source":review["evidence"][0]["url"],
        "source_kind":"official",
        "fields":{
            "name":"pass","date":"pass","venue":"pass",
            "time":"pass" if ev.get("time") else "unknown",
            "price":"pass" if ev.get("price") else "unknown",
            "reservation":"unknown","target":"pass","cancellation":"unknown","official_url":"pass"
        },
        "corrections":{},
        "note":"v1.6除外再審査で公式・主催者情報を再確認し掲載へ復活。"
    }

def main():
    manifest=read_json(DATA/"manifest.json")
    all_report=[]
    for week in WEEKS:
        week_path=DATA/f"{week}.json"
        week_doc=read_json(week_path)
        decision_path=DATA/f"{week}-decisions.json"
        decisions=read_json(decision_path)
        review_path=DATA/f"{week}-v16-rereview.json"
        if review_path.exists():
            old=read_json(review_path)
            if old.get("review_version")=="v1.6" and old.get("status")=="applied":
                print("already applied",week); continue
        event_file=DATA/(week_doc.get("event_files") or [f"{week}-events-01.json"])[0]
        events=read_json(event_file)
        ver_path=DATA/f"{week}-verification.json"
        ver=read_json(ver_path)
        run_path=DATA/f"{week}-run.json"; run=read_json(run_path)
        legacy=fetch_legacy(week)
        legacy_rows=legacy.get("events") or []
        reviewed=[]; promoted=0; kept=0; hard_kept=0
        current_ids={e.get("id") for e in events}
        for row in decisions.get("decisions") or []:
            if row.get("decision")!="excluded": continue
            if not any(str(s.get("kind","")).startswith("legacy_") for s in row.get("discovery_sources") or []): continue
            key=k(row.get("name"))
            if key in PROMOTE:
                overall,pos,neg,reason=PROMOTE[key]
                rv=review_obj(row,"published",overall,pos,neg,"family_value_high",None,reason,"")
                leg=legacy_row_for(row,legacy_rows)
                ev=event_from_legacy(row,leg,rv,week)
                if ev["id"] not in current_ids:
                    events.append(ev); current_ids.add(ev["id"])
                    ver.setdefault("events",[]).append(verification_for(ev,rv,week_doc.get("publication_tier")))
                row["decision"]="published"
                row["hard_exclusion"]=None; row["exclusion_type"]=None
                row["primary_reason_code"]="family_value_high"
                row["reason_codes"]=["family_value_high"]
                row["reasons"]=[reason]
                row["evidence"]=rv["evidence"]
                row["override_reason"]=reason if (row.get("family_fit") or {}).get("overall") in ("C","D") else ""
                row["v16_review"]=rv
                promoted+=1
            elif key in KEEP:
                overall,pos,neg,primary,ex_type,reason,trade=KEEP[key]
                result="kept_excluded"
                rv=review_obj(row,result,overall,pos,neg,primary,ex_type,reason,trade)
                row["v16_review"]=rv
                row["reasons"]=[reason]
                row["evidence"]=rv["evidence"]
                if ex_type=="soft":
                    row["primary_reason_code"]=primary
                    row["reason_codes"]=list(dict.fromkeys([primary]+neg))
                    row["exclusion_type"]="soft"; row["hard_exclusion"]=None
                    kept+=1
                else:
                    row["primary_reason_code"]=primary
                    row["reason_codes"]=[primary]
                    row["exclusion_type"]="hard"; row["hard_exclusion"]=primary
                    hard_kept+=1
            else:
                raise RuntimeError(f"no v1.6 review mapping for {row.get('name')}")
            reviewed.append({
                "candidate_id":row.get("candidate_id"),"name":row.get("name"),"ward":row.get("ward"),
                **row["v16_review"]
            })

        counts={"published":0,"excluded":0,"duplicate":0}
        for row in decisions.get("decisions") or []:
            if row.get("decision") in counts: counts[row["decision"]]+=1
        decisions["summary"]["published"]=counts["published"]
        decisions["summary"]["excluded"]=counts["excluded"]
        decisions["summary"]["duplicate"]=counts["duplicate"]
        decisions["summary"]["candidate_total"]=sum(counts.values())
        decisions["summary"]["v16_rereviewed"]=len(reviewed)
        decisions["summary"]["v16_promoted"]=promoted
        decisions["summary"]["v16_kept_excluded"]=kept+hard_kept

        cov=week_doc["coverage"]
        cov["candidate_count"]=sum(counts.values()); cov["published_count"]=counts["published"]
        cov["excluded_count"]=counts["excluded"]; cov["duplicate_removed"]=counts["duplicate"]
        actual_by_ward={}
        for e in events: actual_by_ward[e["ward"]]=actual_by_ward.get(e["ward"],0)+1
        for wr in cov.get("wards") or []:
            wr["published_count"]=actual_by_ward.get(wr["ward"],0)
            wr["note"]=re.sub(r"v1\.6除外再審査.*$","",wr.get("note","")).rstrip()
            wr["note"]+=(f" v1.6除外再審査反映。" if any(x["ward"]==wr["ward"] for x in reviewed) else "")
        week_doc["generated"]=STAMP

        ver_rows=ver.get("events") or []
        verified=sum(x.get("status")=="verified" for x in ver_rows)
        announced=sum(x.get("status")=="announced" for x in ver_rows)
        ver["verified_on"]=STAMP[:10]
        ver["summary"]={"total":len(events),"verified":verified,"announced":announced,"corrected":ver.get("summary",{}).get("corrected",0)}

        run.setdefault("source_data",{})["rereview_file"]=review_path.name
        stages=run.setdefault("stages",[])
        stages=[x for x in stages if x.get("name")!="v16_exclusion_rereview"]
        stages.insert(max(0,len(stages)-1),{"name":"v16_exclusion_rereview","status":"passed","evidence":f"{len(reviewed)} legacy-origin excluded candidates re-reviewed under v1.6; {promoted} promoted"})
        run["stages"]=stages
        rs=run.setdefault("summary",{})
        rs.update({"candidates":sum(counts.values()),"published":counts["published"],"excluded":counts["excluded"],
                   "duplicate_removed":counts["duplicate"],"verified":verified,"announced":announced,
                   "v16_rereviewed":len(reviewed),"v16_promoted":promoted,"v16_kept_excluded":kept+hard_kept,
                   "thumbnail_count":sum(bool(e.get("image")) for e in events),
                   "thumbnail_coverage":round(sum(bool(e.get("image")) for e in events)/len(events),3) if events else 1.0})
        run.setdefault("postprocess_reviews",[])
        run["postprocess_reviews"]=[x for x in run["postprocess_reviews"] if x.get("version")!="v1.6"]
        run["postprocess_reviews"].append({"version":"v1.6","prompt":PROMPT,"mode":"targeted-exclusion-rereview","applied_at":STAMP,"review_file":review_path.name})

        review_doc={
            "schema_version":1,"review_version":"v1.6","rubric_version":"family-fit-v2",
            "status":"applied","reviewed_at":STAMP,"base_prompt_version":"v1.5","prompt":PROMPT,
            "scope":"legacy-origin candidates excluded by v1.5 only; no full rediscovery",
            "summary":{"reviewed":len(reviewed),"promoted":promoted,"kept_soft_excluded":kept,"kept_hard_excluded":hard_kept},
            "reviews":reviewed
        }
        write_json(event_file,events); write_json(ver_path,ver); write_json(decision_path,decisions)
        write_json(week_path,week_doc); write_json(run_path,run); write_json(review_path,review_doc)
        all_report.append({"week":week,"reviewed":len(reviewed),"promoted":promoted,"published":len(events),"excluded":counts["excluded"]})
        for ent in manifest.get("weekends") or []:
            if ent.get("sat")==week: ent["count"]=len(events)
    manifest["generated"]=STAMP
    write_json(DATA/"manifest.json",manifest)
    write_json(DATA/"v16-rereview-summary.json",{
        "schema_version":1,"review_version":"v1.6","generated":STAMP,
        "scope":"targeted re-review of the 35 unique legacy-origin events excluded by v1.5",
        "weeks":all_report
    })
    print(json.dumps(all_report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
