#!/usr/bin/env python3
"""Build a six-week verified-subset rollover from immutable data-production.

Requires the Oct 26 read-only GitHub Actions HTTP evidence artifact. Never
promotes data by itself. Unknown source/event candidates stay unverified.
"""
import argparse, collections, copy, datetime as dt, json, pathlib

JST=dt.timezone(dt.timedelta(hours=9))
WARDS='千代田区 中央区 港区 新宿区 文京区 台東区 墨田区 江東区 品川区 目黒区 大田区 世田谷区 渋谷区 中野区 杉並区 豊島区 北区 荒川区 板橋区 練馬区 足立区 葛飾区 江戸川区'.split()
EXPECTED={'2026-10-31':('full',1),'2026-11-07':('full',2),'2026-11-14':('preview',3),'2026-11-21':('preview',4),'2026-11-28':('announcement',5),'2026-12-05':('announcement',6)}
SOURCES={
'v15-237c930495e3':'https://www.city.minato.tokyo.jp/bungeishinkou/minakore/home.html',
'v15-0c99233f00d9':'https://inclusion-art.jp/archive/event/2026/20261107-422.html',
'v15-d18ca8b4095f':'https://www.neribun.or.jp/event/detail_m.cgi?id=202606301782802063',
'v15-066e0211371b':'https://sumida-artfest.jp/',
'v15-41134e91ddc0':'https://www.city.tokyo-nakano.lg.jp/event/kanko/shotengai_nigiwaifesta2026.html',
'v15-3e409ca87678':'https://www.city.meguro.tokyo.jp/sangyoukeizai/bunkasports/kankou/riverside.html',
'official-2026-suginami-festa':'https://www.sugifes.com/event/',
'official-2026-yayoi-fukusaku':'https://nakanoshakyo.com/nakanoinfo/event/result/?did=14590',
'official-2026-shirasagi-stamp':'https://nakanoshakyo.com/nakanoinfo/event/result/?did=14585',
'official-2026-nihonbashi-komichi':'https://www.keepallsmiles.com/komichi2026',
'official-2026-haneda-museum':'https://www.o-2.jp/event/hasmhicity2026/'
}

def write(path,obj):
 path=pathlib.Path(path); path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def load(path):return json.loads(pathlib.Path(path).read_text(encoding='utf-8'))

def main(data,evidence,mainrepo,base):
 data=pathlib.Path(data); evidence=pathlib.Path(evidence); mainrepo=pathlib.Path(mainrepo)
 source=load(evidence/'requests.json')
 plan=load(evidence/'plan.json')
 packet=load(evidence/'review_packet.json')
 if plan.get('as_of_jst')!='2026-10-26' or plan.get('target_end')!='2026-12-06' or not plan.get('read_only'):
  raise ValueError('wrong provenance run or rolling window')
 if (len(source),sum(r.get('status')=='checked' for r in source))!=(663,658):
  raise ValueError('bad immutable HTTP evidence totals')
 if len(packet.get('required_source_failures') or [])!=5:
  raise ValueError('source failure evidence must stay explicit')
 new=load(mainrepo/'research/third_batch_20261205_verified_shard.json')
 carry=load(mainrepo/'research/third_batch_20261205_carryover_preservation.json')
 if new.get('record_count')!=14 or carry.get('carryover_count')!=14:
  raise ValueError('unreviewed third batch counts')
 events=copy.deepcopy(new['records'])
 names={e['name'] for e in events}
 if len(names)!=14 or len({e['id'] for e in events})!=14:raise ValueError('new event duplicates')
 # Carryover the exact published event record from its recorded historical shard.
 old=load(data/'manifest.json')
 if [w['sat'] for w in old['weekends']]!=['2026-10-24',*list(EXPECTED)[:5]]:raise ValueError('unexpected baseline manifest')
 verified={}
 for line in carry['items']:
  src=load(data/line['source_file'])
  hits=[e for e in src if e.get('id')==line['id'] and e.get('name')==line['name']]
  if len(hits)!=1:raise ValueError('missing protected carryover '+line['id'])
  ev=copy.deepcopy(hits[0])
  if not(ev['date_start']<='2026-12-06' and ev['date_end']>='2026-12-05'):
   raise ValueError('carryover not active on target weekend')
  if ev['name'] in names:raise ValueError('new source-event duplicate '+ev['name'])
  events.append(ev);names.add(ev['name'])
  v=load(data/(line['source_week']+'-verification.json'))
  verified[ev['id']]=next(x for x in v['events'] if x['id']==ev['id'])
 if len(events)!=28 or len({e['id'] for e in events})!=28:raise ValueError('missing or duplicate 12/5 event')
 # Full tier advances for Nov 7. Recheck each previously announced official event.
 v=load(data/'2026-11-07-verification.json')
 targets=[row for row in v['events'] if row['status']=='announced']
 if set(x['id'] for x in targets)!=set(SOURCES):raise ValueError('unplanned announcement upgrades')
 for row in targets:
  row['status']='verified'; row['source']=SOURCES[row['id']]
  row['review_note']='2026-10-27 official municipality/organizer detail page re-reviewed for exact date, place and participation unit; unknown secondary details retained unknown.'
 v['verified_on']='2026-10-27';v['summary']['verified']+=len(targets);v['summary']['announced']-=len(targets)
 write(data/'2026-11-07-verification.json',v)
 weekrun=load(data/'2026-11-07-run.json');weekrun['summary']['verified']+=len(targets);weekrun['summary']['announced']-=len(targets)
 weekrun['full_tier_recheck']={'reviewed_on':'2026-10-27','upgraded_ids':list(SOURCES),'official_pages':SOURCES}
 write(data/'2026-11-07-run.json',weekrun)
 # Change tier/index metadata on retained weeks, not event facts or source logs.
 for sat,(tier,index) in EXPECTED.items():
  if sat=='2026-12-05':continue
  week=load(data/(sat+'.json'))
  week['horizon_index']=index;week['publication_tier']=tier
  write(data/(sat+'.json'),week)
  run=load(data/(sat+'-run.json'))
  run['horizon_index']=index;run['publication_tier']=tier
  write(data/(sat+'-run.json'),run)
 # Reuse actual dated 2026-10-26 per-ward HTTP evidence only. Never fake checks.
 stamps={}
 for ward in WARDS:
  qr=[r for r in source if r.get('kind')=='ai_cross' and r.get('week')=='2026-12-05' and r.get('ward')==ward]
  sr=[r for r in source if r.get('kind')=='ward_official' and r.get('ward')==ward]
  if len(qr)!=3 or len(sr)!=1 or any(r.get('status')!='checked' for r in qr+sr):
   raise ValueError('failed 23-ward source truth: '+ward)
  stamps[ward]={'ward':ward,'query_logs':[{'query':r['query'],'url':r['url'],'checked_at':r['checked_at'],'status':r['status'],'sha256':r['sha256'],'result_count':r.get('search_results_event_leads',0)} for r in qr],
    'source_checks':[{'url':r['url'],'checked_at':r['checked_at'],'status':r['status'],'sha256':r['sha256']} for r in sr]}
 counts=collections.Counter(x['ward'] for x in events)
 actual=[]
 for ward in WARDS:
  count=counts[ward]
  actual.append({'ward':ward,'status':'checked','queries':3,'sources_checked':1,'candidate_count':count,'published_count':count,
    'note':'Exact 2026-10-26 per-ward source/AI query HTTP log; event selection is independent verified-subset only, not complete source coverage.'})
 # Some fixed sources were truly unreachable; report errors exactly, do not coerce them.
 explicit=[]
 for r in source:
  if r.get('kind')!='explicit':continue
  explicit.append({'source_id':r.get('source_id'),'search_url':r['url'],'checked_at':r.get('checked_at'),
                   'status':r['status'],'http_status':r.get('http_status'),
                   'sha256':r.get('sha256'),'error':r.get('error')})
 now=dt.datetime.now(JST).isoformat(timespec='seconds')
 new_week={'sample':False,'sat':'2026-12-05','sun':'2026-12-06','label':'12/5(土)〜12/6(日)',
     'generated':now,'horizon_index':6,'publication_tier':'announcement',
     'verification_file':'2026-12-05-verification.json','run_file':'2026-12-05-run.json',
     'coverage':{'sources_checked':23,'candidate_count':28,'duplicate_removed':0,'excluded_count':0,'published_count':28,'wards':actual},
     'event_files':['2026-12-05-events-official-verified.json','2026-12-05-events-preserved-carryover.json'],'events':[]}
 write(data/'2026-12-05-events-official-verified.json',events[:14]);write(data/'2026-12-05-events-preserved-carryover.json',events[14:]);write(data/'2026-12-05.json',new_week)
 verification=[]
 for e in events:
  if e['id'] in verified:
   row=copy.deepcopy(verified[e['id']]);verification.append(row);continue
  incomplete=e['id'] in {'v15-20261205-nakano-vanguard','v15-20261205-nakano-precure-show'}
  verification.append({'id':e['id'],'status':'announced' if incomplete else 'verified','source':e['official_url'],'source_kind':'public_official' if 'city.' in e['official_url'] else 'organizer_official',
    'fields':{'name':'pass','date':'pass','venue':'pass','time':'pass','price':'unknown' if '明示なし' in e.get('price','') else 'pass','reservation':'unknown' if incomplete else 'pass','official_url':'pass'},
    'corrections':{},'note':'2026-10-27 primary detail individually confirmed; website/source-specific failures stay in pending ledger.'})
 statuses=collections.Counter(x['status'] for x in verification)
 write(data/'2026-12-05-verification.json',{'schema_version':1,'verified_on':'2026-10-27','events':verification,'summary':{'total':28,'verified':statuses['verified'],'announced':statuses['announced']}})
 # Existing decisions are inherited with their unmodified family-fit-v2 evaluation.
 decisions=[]
 for e in events:
  found=None
  if e['id'] in verified:
   sat=next(z['source_week'] for z in carry['items'] if z['id']==e['id'])
   rows=load(data/(sat+'-decisions.json'))['decisions']
   found=next((x for x in rows if x.get('candidate_id') in (e['id'],'preserved-'+e['id']) or (x.get('name')==e['name'] and x.get('ward')==e['ward'] and x.get('decision')=='published')),None)
  if found is not None:
   found=copy.deepcopy(found)
   # A published earlier week can still carry a legacy v1 decision.
   # Reuse a genuine v2 evaluation of that same participation unit, never
   # auto-convert v1 grades and reasons into a fake v2 rubric.
   if (found.get('family_fit') or {}).get('rubric_version')!='family-fit-v2':
    aliases=load(data/'2026-11-07-decisions.json')['decisions']
    alt=next((x for x in aliases if x.get('name')==e['name'] and x.get('ward')==e['ward'] and x.get('decision')=='published' and (x.get('family_fit') or {}).get('rubric_version')=='family-fit-v2'),None)
    if alt is None:raise ValueError('no independently reviewed v2 decision for carryover '+e['id'])
    found=copy.deepcopy(alt)
   found['candidate_id']=e['id']
   found['name']=e['name'];found['ward']=e['ward']
   decisions.append(found);continue
  fit=e.get('family_fit') or {}
  if fit.get('rubric_version')!='family-fit-v2':raise ValueError('no v2 evaluation '+e['id'])
  decisions.append({'candidate_id':e['id'],'name':e['name'],'ward':e['ward'],'decision':'published','family_fit':fit,
   'positive_signals':['family_compatible','official_venue_published'],'negative_signals':[],
   'hard_exclusion':None,'exclusion_type':None,'primary_reason_code':'family_value_high','reason_codes':['family_value_high'],
   'reasons':['Individual organizer/municipal official evidence and family-fit review; uncertain details explicitly marked.'],
   'evidence':[{'url':e['official_url'],'basis':'2026-12-05 individual date, venue and visitor constraints'}],
   'override_reason':''})
 write(data/'2026-12-05-decisions.json',{'schema_version':1,'rubric_version':'family-fit-v2','generated':now,'migration_incomplete':False,
       'summary':{'candidate_total':28,'published':28,'excluded':0,'duplicate':0},'decisions':decisions})
 run={'schema_version':1,'target':{'sat':'2026-12-05','sun':'2026-12-06'},'publication_tier':'announcement','horizon_index':6,
     'mode':'verified-horizon-subset','prompt':{'version':'v1.15','path':'prompts/tokyo_family_events_complete_prompt_v1.15.txt','pointer':'site/data/latest_prompt.json','resolved':True},
     'holiday_after':{'run_type':'verified_horizon_subset','as_of_jst':'2026-10-26'},
     'source_data':{'week_file':'2026-12-05.json','verification_file':'2026-12-05-verification.json','decision_file':'2026-12-05-decisions.json'},
     'discovery_evidence':{'wards':[stamps[w] for w in WARDS]},
     'explicit_source_checks':explicit,
     'source_debt':{'pending_failures':packet['required_source_failures'],'all_required_enabled':True,'http_errors_are_not_zero_event_evidence':True},
     'read_only_evidence':{'run_id':40239302863,'run_attempt':2,'artifact_id':12621285469,
                           'request_count':663,'checked_requests':658,'source_failure_count':5},
     'summary':{'published':28,'verified':statuses['verified'],'announced':statuses['announced'],'candidates':28,'excluded':0,'wards_checked':23,
                'note':'Exactly 14 existing carryovers plus 14 new official programs. Unverified links outside subset remain pending.'}}
 write(data/'2026-12-05-run.json',run)
 manifest=copy.deepcopy(old)
 manifest['generated']=now
 manifest['default']='2026-10-31'
 manifest['weekends']=[]
 for sat,(tier,index) in EXPECTED.items():
  if sat=='2026-12-05':
   manifest['weekends'].append({'sat':sat,'sun':'2026-12-06','label':'12/5(土)〜12/6(日)','file':sat+'.json','count':28,'horizon_index':index,'publication_tier':tier})
  else:
   row=copy.deepcopy(next(x for x in old['weekends'] if x['sat']==sat))
   row['horizon_index']=index;row['publication_tier']=tier;manifest['weekends'].append(row)
 write(data/'manifest.json',manifest)
 history=load(data/'update_history.json');history['history'].append({
     'run_id':'verified-horizon-subset-2026-10-26-'+base[:12],
     'run_type':'verified_horizon_subset','as_of_jst':'2026-10-26',
     'base_data_production_sha':base,'previous_manifest_generated':old['generated'],'new_manifest_generated':now,
     'target_start':'2026-10-26','target_end':'2026-12-06',
     'added_weekly_records':28,'new_official_independent_records':14,'preserved_carryover_records':14,
     'old_event_ids_removed':0,'old_event_records_changed':0,'unverified_required_source_failures':5,
     'executed_at':now,'note':'Six-week partial verified-subset rollover; all old week files and records preserved; five required source HTTP errors still unresolved.'})
 write(data/'update_history.json',history)
 print(json.dumps({'status':'CANDIDATE_ONLY','new_week':28,'new_official':14,'carryover':14,'weekend_starts':[w['sat'] for w in manifest['weekends']],
 'full_tier_rechecks':len(targets),'unresolved_sources':5},ensure_ascii=False))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data-dir',required=True);p.add_argument('--evidence-dir',required=True);p.add_argument('--main-dir',required=True);p.add_argument('--baseline',required=True)
 a=p.parse_args();main(a.data_dir,a.evidence_dir,a.main_dir,a.baseline)