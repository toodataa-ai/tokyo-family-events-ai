#!/usr/bin/env python3
"""Fail-closed immutable audit of six official 2026-10-31/11-01/11-03 additions.
Baseline required-source fetch errors are preserved exactly, never declared verified.
"""
import argparse,json,subprocess,sys
from pathlib import Path

WEEK='2026-10-31'
SHARD=WEEK+'-events-verified-subset-2026-10-27.json'
DIR='site/data/'
ALLOWED={DIR+n for n in ('manifest.json','update_history.json',WEEK+'.json',
    WEEK+'-verification.json',WEEK+'-decisions.json',WEEK+'-run.json',SHARD)}
SOURCE_URLS={
 'weekly-20261027-koto-ecocle':'https://www.city.koto.lg.jp/380291/ekokkuru/event/r8/2026akinoekokkurumatsuri.html',
 'weekly-20261027-koto-toyosu':'https://www.city.koto.lg.jp/281053/kodomo/hokago/jidokan/asobiba.html',
 'weekly-20261027-adachi-clay':'https://www.galaxcity.jp/future-creation-hall/event/20261103-009189.html',
 'weekly-20261027-katsushika-museum':'https://www.museum.city.katsushika.lg.jp/event/2026/10/113-4.php',
 'weekly-20261027-edogawa-sports':'https://www.edogawa-spocen.com/event/43860/',
 'weekly-20261027-nakano-oshiri':'https://oshiri-tantei.com/events/2026071801b.html'
}
WARDS={'江東区':2,'中野区':1,'江戸川区':1,'葛飾区':1,'足立区':1}

def current(name):return json.loads((Path(DIR)/name).read_text(encoding='utf-8'))
def previous(base,name):
 return json.loads(subprocess.check_output(['git','show',base+':'+DIR+name],text=True))
def require(condition, message):
 if not condition:raise ValueError(message)
def check(base):
 changed=set(subprocess.check_output(['git','diff','--name-only',base,'HEAD'],text=True).splitlines())
 require(changed==ALLOWED,'changed file allowlist mismatch: '+str(changed^ALLOWED))
 oldmanifest,newmanifest=previous(base,'manifest.json'),current('manifest.json')
 require(oldmanifest['weekends'][1:]==newmanifest['weekends'][1:],'unrelated weekend changed')
 require(oldmanifest['weekends'][0]['count']+6==newmanifest['weekends'][0]['count'],'wrong week count')
 for k in oldmanifest:
  if k not in ('weekends','generated'):require(oldmanifest[k]==newmanifest[k],'manifest field changed: '+k)
 require(len(oldmanifest['weekends'])==len(newmanifest['weekends'])==6,'six-week horizon changed')
 for k in oldmanifest['weekends'][0]:
  if k!='count':require(oldmanifest['weekends'][0][k]==newmanifest['weekends'][0][k],'week meta changed')
 oldweek,newweek=previous(base,WEEK+'.json'),current(WEEK+'.json')
 allowed={'event_files','coverage','generated'}
 for k in oldweek:
  if k not in allowed:require(oldweek[k]==newweek[k],'week metadata changed '+k)
 require(newweek['event_files']==oldweek['event_files']+[SHARD],'new event file not appended exactly')
 for k in oldweek['coverage']:
  if k in ('candidate_count','published_count','wards'):continue
  require(newweek['coverage'][k]==oldweek['coverage'][k],'source check counters modified '+k)
 for k in ('candidate_count','published_count'):
  require(newweek['coverage'][k]==oldweek['coverage'][k]+6,'coverage totals incorrect '+k)
 for oldrow,newrow in zip(oldweek['coverage']['wards'],newweek['coverage']['wards']):
  require(oldrow['ward']==newrow['ward'],'ward order changed')
  extra=WARDS.get(oldrow['ward'],0)
  for k in oldrow:
   if k in ('candidate_count','published_count'):
    require(newrow[k]==oldrow[k]+extra,'ward count incorrect '+k)
   elif k=='note' and extra:
    require(str(newrow[k]).startswith(str(oldrow[k])),'prior source note altered')
   else:require(newrow[k]==oldrow[k],'source coverage changed '+str(oldrow['ward'])+':'+k)
 newevents=current(SHARD)
 require(len(newevents)==6,'exactly six records required')
 require(len({e.get('id') for e in newevents})==6,'duplicate new IDs')
 require({e.get('id'):e.get('official_url') for e in newevents}==SOURCE_URLS,'official URL and ID mismatch')
 for e in newevents:
  require('2026-10-31'<=e['date_start']<=e['date_end']<='2026-11-03','event outside target dates')
  require(e.get('name') and e.get('ward') and e.get('venue') and e.get('time') and e.get('source')==e['official_url'],'incomplete event facts')
  require(e.get('image','')=='','image not independently verified; do not assign a thumbnail')
  require(e.get('reservation',{}).get('required') in (True,False),'unknown reservation boolean')
  require(e.get('family_fit',{}).get('rubric_version')=='family-fit-v2','family-fit v2 missing')
 for shard in oldweek['event_files']:
  require(current(shard)==previous(base,shard),'existing event shard mutated '+shard)
 require(oldweek.get('events',[])==newweek.get('events',[]),'old inline event mutated')
 oldverify,newverify=previous(base,WEEK+'-verification.json'),current(WEEK+'-verification.json')
 require(newverify['events'][:len(oldverify['events'])]==oldverify['events'],'old verification rows changed')
 require(len(newverify['events'])==len(oldverify['events'])+6,'new verification count')
 require(newverify['summary']['total']==oldverify['summary']['total']+6 and
         newverify['summary']['verified']==oldverify['summary']['verified']+6,'new verification summary mismatch')
 for x in newverify['events'][len(oldverify['events']):]:
  require(x.get('status')=='verified' and x.get('source')==SOURCE_URLS.get(x.get('id')),
          'unverified/mismatched official evidence')
 olddec,newdec=previous(base,WEEK+'-decisions.json'),current(WEEK+'-decisions.json')
 require(newdec['decisions'][:len(olddec['decisions'])]==olddec['decisions'],'old decision rows changed')
 require(len(newdec['decisions'])==len(olddec['decisions'])+6,'new decision count')
 require(newdec['summary']['candidate_total']==olddec['summary']['candidate_total']+6 and
         newdec['summary']['published']==olddec['summary']['published']+6,'decision summary mismatch')
 for row in newdec['decisions'][len(olddec['decisions']):]:
  require(row.get('decision')=='published' and row.get('candidate_id') in SOURCE_URLS
          and any(x.get('url')==SOURCE_URLS[row['candidate_id']] for x in row.get('evidence',[])),
          'unverified published decision')
 oldrun,newrun=previous(base,WEEK+'-run.json'),current(WEEK+'-run.json')
 for k in oldrun:
  if k not in ('summary','verified_subset_addendum'):require(newrun[k]==oldrun[k],'previous run source evidence changed '+k)
 for k in ('published','verified'):
  require(newrun['summary'][k]==oldrun['summary'][k]+6,'wrong run summary '+k)
 addon=newrun.get('verified_subset_addendum',{})
 require(addon.get('base_data_production_sha')==base and
         set(addon.get('new_event_ids',[]))==set(SOURCE_URLS) and
         addon.get('source_failures_remain_unverified')==True,'run addendum lacks proof')
 oldhist,newhist=previous(base,'update_history.json'),current('update_history.json')
 require(oldhist['history']==newhist['history'][:-1],'prior history removed/edited')
 require(len(newhist['history'])==len(oldhist['history'])+1,'history must append one')
 h=newhist['history'][-1]
 require(h.get('run_type')=='manual_verified_week_holiday_addition' and
   h.get('as_of_jst')=='2026-10-27' and h.get('base_data_production_sha')==base
   and h.get('added_weekly_records')==6 and h.get('old_event_ids_removed')==0
   and h.get('old_event_records_changed')==0
   and set(h.get('new_event_ids',[]))==set(SOURCE_URLS),'wrong verified history')
 # Preserve all prior six-week data files and the exact formerly failing sources.
 import importlib.util
 path=Path(__file__).with_name('validate_official_schedule_audit.py')
 spec=importlib.util.spec_from_file_location('source_check',path)
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 config=current('discovery_sources.json');old_errors=[];new_errors=[]
 for w in oldmanifest['weekends']:
  o=previous(base,w['file']);n=current(w['file'])
  orun=previous(base,o['run_file']);nrun=current(n['run_file'])
  odd=previous(base,orun['source_data']['decision_file'])
  ndd=current(nrun['source_data']['decision_file'])
  old_errors+=mod.validate(orun,o,odd,config,())
  new_errors+=mod.validate(nrun,n,ndd,config,())
 require(old_errors==new_errors,'new or changed source audit errors: '+str(new_errors))
 print('SOURCE_AUDIT_OLD_DEBT_UNCHANGED',len(old_errors))
 print('FOURTH_BATCH_VERIFIED_ADDITIVE_PASS',len(newevents),'records, zero prior edits/deletions')

def main():
 p=argparse.ArgumentParser();p.add_argument('--base-ref',required=True);args=p.parse_args()
 try:
  require(len(args.base_ref)==40 and all(c in '0123456789abcdef' for c in args.base_ref),'baseline SHA invalid')
  check(args.base_ref)
 except (ValueError,KeyError,OSError,subprocess.CalledProcessError) as e:
  print('BLOCKER FOURTH_BATCH_GATE',str(e),file=sys.stderr);return 1
 return 0
if __name__=='__main__':sys.exit(main())
