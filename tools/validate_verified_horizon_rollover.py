#!/usr/bin/env python3
"""Fail-closed audit of the Dec 05 six-week partial-verified rollover.

The prior 2026-10-26 source failures remain blocked and visible; they never
become checked or zero events. Only 14 verified individual source programs and
14 protected carryovers may enter the new sixth week.
"""
import argparse,collections,copy,json,pathlib,subprocess,sys

BASE='a7446aca567ca74c936c2039867fcf5fd3b07e34'
SATS=['2026-10-31','2026-11-07','2026-11-14','2026-11-21','2026-11-28','2026-12-05']
TIERS=['full','full','preview','preview','announcement','announcement']
WARDS=['千代田区','中央区','港区','新宿区','文京区','台東区','墨田区','江東区','品川区','目黒区','大田区','世田谷区','渋谷区','中野区','杉並区','豊島区','北区','荒川区','板橋区','練馬区','足立区','葛飾区','江戸川区']

def load(path):return json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
def same(a,b,label):
 if a!=b:raise ValueError('PROTECTED_DATA_CHANGED: '+label)

def validate(root,main,evidence,base=BASE):
 if base!=BASE:raise ValueError('unapproved immutable baseline')
 root=pathlib.Path(root); main=pathlib.Path(main); evidence=pathlib.Path(evidence)
 if not all((evidence/f).is_file() for f in ['requests.json','review_packet.json','plan.json']):raise ValueError('missing independently captured source evidence')
 receipts=load(evidence/'requests.json');packet=load(evidence/'review_packet.json');plan=load(evidence/'plan.json')
 if plan.get('as_of_jst')!='2026-10-26' or plan.get('target_end')!='2026-12-06':raise ValueError('wrong date-scoped source run')
 if len(receipts)!=663 or sum(r.get('status')=='checked' for r in receipts)!=658:raise ValueError('source totals tampered')
 failures=[r for r in receipts if r.get('kind')=='explicit' and r.get('status')!='checked']
 if len(failures)!=5:raise ValueError('required source errors are not five')
 failkeys=[(x.get('source_id'),x.get('url')) for x in failures]
 if len(set(failkeys))!=5 or collections.Counter(x[0] for x in failkeys)!=collections.Counter({'tamemap_nakano':3,'itabashi_tourism_festival':1,'iterrace':1}):raise ValueError('unapproved source error substitution')
 d=root
 def cur(f):return load(d/f)
 def old(f):
  p=subprocess.run(['git','show',base+':site/data/'+f],capture_output=True,text=True,check=True)
  return json.loads(p.stdout)
 before,after=old('manifest.json'),cur('manifest.json')
 same([x['sat'] for x in before['weekends']],['2026-10-24',*SATS[:5]],'baseline weeks')
 same([x['sat'] for x in after['weekends']],SATS,'new six-week window')
 if after['default']!='2026-10-31' or after.get('rolling_horizon_weeks')!=6:raise ValueError('bad default or week count')
 same(after.get('holidays'),before.get('holidays'),'holiday data')
 same(after.get('holiday_source'),before.get('holiday_source'),'official holiday provenance')
 if after.get('generated')==before.get('generated'):raise ValueError('history timestamp unchanged')
 changed=set(subprocess.check_output(['git','diff','--name-only',base],text=True).splitlines())
 untracked=set(subprocess.check_output(['git','ls-files','--others','--exclude-standard'],text=True).splitlines())
 changed |= untracked
 expected={'site/data/manifest.json','site/data/update_history.json','site/data/2026-11-07-verification.json'}
 expected|={f'site/data/{sat}{suffix}' for sat in SATS[:5] for suffix in ('.json','-run.json')}
 expected|={'site/data/2026-12-05'+suffix for suffix in ('.json','-verification.json','-decisions.json','-run.json','-events-official-verified.json','-events-preserved-carryover.json')}
 if changed!=expected:raise ValueError('changed paths outside exact rollover scope: '+str(sorted(changed.symmetric_difference(expected))))
 for i,(entry,tier) in enumerate(zip(after['weekends'],TIERS)):
  if entry.get('horizon_index')!=i+1 or entry.get('publication_tier')!=tier:raise ValueError('incorrect six-week tier promotion')
  data=cur(entry['file']);run=cur(data['run_file'])
  if data.get('horizon_index')!=i+1 or data.get('publication_tier')!=tier:raise ValueError('inconsistent dated week tier')
  if run.get('horizon_index')!=i+1 or run.get('publication_tier')!=tier:raise ValueError('inconsistent dated run tier')
  if i<5:
   old_entry=next(w for w in before['weekends'] if w['sat']==entry['sat'])
   same(entry.get('count'),old_entry.get('count'),'existing count')
   existing=old(entry['file'])
   same(data.get('event_files'),existing.get('event_files'),'old week source shards')
   same(data.get('coverage'),existing.get('coverage'),'old coverage data')
   same(data.get('events'),existing.get('events'),'old inline events')
   for shard in existing['event_files']:same(cur(shard),old(shard),'untouched protected shard '+shard)
   if i!=1:same(cur(entry['sat']+'-verification.json'),old(entry['sat']+'-verification.json'),'unrelated verification')
   runold=old(data['run_file'])
   for key,val in runold.items():
    if key in ('publication_tier','horizon_index','summary','full_tier_recheck'):continue
    same(run.get(key),val,'pre-existing source and run evidence '+entry['sat']+':'+key)
  else:
   if entry['count']!=28 or data['coverage']['published_count']!=28:raise ValueError('new week event count not 28')
   if run.get('mode')!='verified-horizon-subset' or run.get('prompt',{}).get('version')!='v1.15':raise ValueError('not latest policy')
   if len(data.get('coverage',{}).get('wards',[]))!=23:raise ValueError('not all 23 ward status rows')
   if run.get('read_only_evidence',{}).get('artifact_id')!=12621285469:raise ValueError('untrusted evidence artifact')
   if run.get('source_debt',{}).get('pending_failures')!=packet['required_source_failures']:raise ValueError('five failures altered or removed')
   for ward in WARDS:
    wr=next((x for x in run['discovery_evidence']['wards'] if x['ward']==ward),None)
    if not wr:raise ValueError('missing ward: '+ward)
    queried=[r for r in receipts if r.get('kind')=='ai_cross' and r.get('ward')==ward and r.get('week')=='2026-12-05']
    rootchecks=[r for r in receipts if r.get('kind')=='ward_official' and r.get('ward')==ward]
    if len(queried)!=3 or len(rootchecks)!=1 or any(x['status']!='checked' for x in queried+rootchecks):raise ValueError('unproven ward HTTP coverage '+ward)
    if [(q['url'],q['sha256']) for q in wr['query_logs']]!=[(q['url'],q['sha256']) for q in queried]:raise ValueError('not exact original query hashes '+ward)
    if [(q['url'],q['sha256']) for q in wr['source_checks']]!=[(q['url'],q['sha256']) for q in rootchecks]:raise ValueError('not exact original ward source hash '+ward)
   expected_explicit=[(r.get('source_id'),r.get('url'),r.get('status')) for r in receipts if r.get('kind')=='explicit']
   actual_explicit=[(r.get('source_id'),r.get('search_url'),r.get('status')) for r in run['explicit_source_checks']]
   same(actual_explicit,expected_explicit,'exact 78 explicit source successes and five failures')
 # The full tier promotion must be narrowly limited to 11 already announced rows.
 oldv=old('2026-11-07-verification.json');newv=cur('2026-11-07-verification.json')
 review=load(main/'research/third_batch_nov07_full_tier_rechecks.json')
 review_ids={x['id'] for x in review['rechecked']}
 announce_ids={x['id'] for x in oldv['events'] if x['status']=='announced'}
 same(review_ids,announce_ids,'11 independently reviewed full-tier identities')
 oldrows={x['id']:x for x in oldv['events']}
 for row in newv['events']:
  before_row=oldrows[row['id']]
  if row['id'] in review_ids:
   if row['status']!='verified' or not row['source'].startswith('https://'):raise ValueError('invalid promoted row '+row['id'])
   if row['source']!=next(x['official_url'] for x in review['rechecked'] if x['id']==row['id']):raise ValueError('full-tier source detail mismatch')
   for k,v in before_row.items():
    if k in ('status','source','review_note'):continue
    same(row.get(k),v,'old verification facts '+row['id'])
  else:same(row,before_row,'unrelated old verified row '+row['id'])
 if newv['summary']['verified']!=oldv['summary']['verified']+11 or newv['summary']['announced']!=0:raise ValueError('full tier migration is incomplete')
 # All 14 source-derived names and 14 old carryovers, same primary event facts.
 created=load(main/'research/third_batch_20261205_verified_shard.json')
 originals=load(main/'research/third_batch_20261205_carryover_preservation.json')
 fresh=cur('2026-12-05-events-official-verified.json');kept=cur('2026-12-05-events-preserved-carryover.json')
 if len(fresh)!=14 or len(kept)!=14:raise ValueError('new and carryover count must be 14 each')
 same(fresh,created['records'],'official event record changed after review')
 for item,ev in zip(originals['items'],kept):
  prior=next(x for x in old(item['source_file']) if x['id']==item['id'])
  same(ev,prior,'altered prior carryover '+item['id'])
 if len(set(x['name'] for x in fresh+kept))!=28:raise ValueError('same participation event published twice')
 if len(set(x['id'] for x in fresh+kept))!=28:raise ValueError('duplicate event ID')
 v=cur('2026-12-05-verification.json');decisions=cur('2026-12-05-decisions.json')
 if {x['id'] for x in v['events']}!={x['id'] for x in fresh+kept}:raise ValueError('verification coverage incomplete')
 if {x['candidate_id'] for x in decisions['decisions']}!={x['id'] for x in fresh+kept}:raise ValueError('decision identity coverage incomplete')
 if any(x['decision']!='published' or x['family_fit'].get('rubric_version')!='family-fit-v2' for x in decisions['decisions']):raise ValueError('new program lacks v2 decision')
 oh=old('update_history.json');nh=cur('update_history.json')
 if len(nh['history'])!=len(oh['history'])+1 or nh['history'][:-1]!=oh['history']:raise ValueError('protected published history changed')
 h=nh['history'][-1]
 if any((h.get('run_type')!='verified_horizon_subset',h.get('base_data_production_sha')!=BASE,h.get('new_official_independent_records')!=14,h.get('preserved_carryover_records')!=14,h.get('unverified_required_source_failures')!=5)):
  raise ValueError('history lacks exact additive documented source debt')
 print('VERIFIED_HORIZON_PROOF_PASS','14 new, 14 protected carryovers, 11 full-tier source rechecks, 23 ward HTTP checks, 5 explicitly unresolved source failures')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--data-dir',default='site/data');p.add_argument('--main-dir',required=True);p.add_argument('--evidence-dir',required=True);p.add_argument('--base-ref',default=BASE)
 a=p.parse_args()
 try:validate(a.data_dir,a.main_dir,a.evidence_dir,a.base_ref)
 except (ValueError,KeyError,IndexError,TypeError,subprocess.CalledProcessError) as exc:
  print('VERIFIED_HORIZON_PROOF_BLOCKED:',exc,file=sys.stderr);sys.exit(1)