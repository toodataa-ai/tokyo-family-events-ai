#!/usr/bin/env python3
"""Guard event-site metrics invariants before and after sharing its D1 with keiba.
No changes to event site tables. Caller deploys separately and can rollback.
"""
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = 'https://tokyo-family-events-metrics.tooda-t-aa.workers.dev'
ORIGIN = 'https://toodataa-ai.github.io'
EVENTS = {'page_home','page_search','page_copy','nav_search','nav_copy',
          'copy_field_click','copy_all_click','copy_field','copy_all','session_start'}
KEIBA_EVENTS = {'page_home','page_this_week','page_results','page_schedule',
                'page_methodology','page_research','page_other','session_start'}
SNAPSHOT = Path('/tmp/keiba-shared-baseline.json')

def read_public(path):
    headers = {'Origin': ORIGIN, 'User-Agent': 'Mozilla/5.0 (keiba-readonly-check)'}
    req = urllib.request.Request(BASE+path, headers=headers)
    with urllib.request.urlopen(req, timeout=22) as r:
        if r.status != 200:
            raise ValueError(f'Unexpected public HTTP: {r.status}')
        return json.load(r)

def check_nonnegative(data, events):
    if not isinstance(data, dict) or set(data) != events:
        raise ValueError('Unexpected event schema / cross-site event contamination')
    if any(type(n) is not int or n < 0 for n in data.values()):
        raise ValueError('Noninteger/negative metrics returned')

def family():
    stats = read_public('/stats')
    assert stats.get('schema_version') == 1
    assert re.fullmatch(r'\d{4}-\d{2}-\d{2}',stats.get('day_jst',''))
    for k in ('today','totals'): check_nonnegative(stats.get(k), EVENTS)
    hist = read_public('/history?days=30')
    assert hist.get('schema_version') == 1 and hist.get('days') == 30
    assert isinstance(hist.get('rows'),list)
    day_rows = {}
    for row in hist['rows']:
        assert re.fullmatch(r'\d{4}-\d{2}-\d{2}',row.get('day',''))
        check_nonnegative(row.get('counts'),EVENTS)
        assert row['day'] not in day_rows
        day_rows[row['day']]=row['counts']
    return {'stats':stats,'history':day_rows}

def preflight():
    token=os.environ.get('CLOUDFLARE_API_TOKEN','')
    account=os.environ.get('CLOUDFLARE_ACCOUNT_ID','')
    if not token or not re.fullmatch('[0-9a-fA-F]{32}',account):
        sys.exit('BLOCKER: event repo Cloudflare secrets unavailable')
    uri=f'https://api.cloudflare.com/client/v4/accounts/{account}/workers/scripts/tokyo-family-events-metrics/settings'
    headers={'Authorization':'Bearer '+token,'Accept':'application/json'}
    with urllib.request.urlopen(urllib.request.Request(uri,headers=headers),timeout=20) as r:
        settings=json.load(r)
    if settings.get('success') is not True:
        sys.exit('BLOCKER: cannot validate original worker settings')
    bindings=(settings.get('result') or {}).get('bindings',[])
    if len(bindings)!=1 or bindings[0].get('name')!='DB' or bindings[0].get('type')!='d1':
        sys.exit('BLOCKER: event metrics Worker binding changed, do not deploy')
    db=bindings[0].get('database_id') or bindings[0].get('id')
    if not isinstance(db,str) or not re.fullmatch('[0-9a-fA-F-]{36}',db):
        sys.exit('BLOCKER: unknown D1 binding ID')
    cfg=Path('analytics/wrangler.toml')
    cfg.write_text('name = "tokyo-family-events-metrics"\n'
                   'main = "worker.mjs"\n'
                   'compatibility_date = "2026-10-01"\n'
                   'workers_dev = true\n'
                   'preview_urls = false\n\n'
                   '[[d1_databases]]\n'
                   'binding = "DB"\n'
                   'database_name = "tokyo-family-events-metrics"\n'
                   'database_id = "'+db+'"\n')
    baseline=family()
    SNAPSHOT.write_text(json.dumps(baseline))
    print('PASS_EVENT_METRICS_SOURCE_VERIFIED',len(EVENTS),'event types,',len(baseline['history']),'recorded days')
    print('PASS_SAME_EXISTING_D1_BINDING_NO_SCHEMA_API_MODIFICATION')

def verify():
    old=json.loads(SNAPSHOT.read_text())
    last_exc=None
    for attempt in range(12):
        try:
            new=family()
            keiba=read_public('/keiba/stats')
            assert keiba.get('schema_version')==1 and keiba.get('site')=='keiba-notes'
            assert re.fullmatch(r'\d{4}-\d{2}-\d{2}',keiba.get('day_jst',''))
            for k in ('today','totals'):check_nonnegative(keiba.get(k),KEIBA_EVENTS)
            for days in (7,30,90,365):
                history=read_public('/keiba/history?days='+str(days))
                assert history.get('schema_version')==1 and history.get('site')=='keiba-notes'
                assert history.get('days')==days
                assert isinstance(history.get('rows'),list)
                observed=set()
                for row in history['rows']:
                    assert row['day'] not in observed
                    observed.add(row['day'])
                    check_nonnegative(row.get('counts'),KEIBA_EVENTS)
            assert new['stats']['day_jst']==old['stats']['day_jst'], 'JST date changed during deploy; rerun scoped review'
            for kind in ('today','totals'):
                for key,old_v in old['stats'][kind].items():
                    assert new['stats'][kind][key]>=old_v, 'Original event counter unexpectedly decreased: '+key
            for day,counts in old['history'].items():
                assert day in new['history'], 'Original event daily history vanished'
                for key,num in counts.items():
                    assert new['history'][day][key]>=num, 'Original day metric decreased: '+day+'/'+key
            print('PASS_EVENT_ORIGINAL_DAY_TOTAL_HISTORY_NONDECREASING')
            print('PASS_KEIBA_SEPARATE_TABLE_READ_API_7_30_90_365')
            print('PASS_EVENT_WORKER_COMPATIBILITY_NO_EVENTS_DATA_DELETED')
            return
        except Exception as e:
            last_exc=e
            if attempt<11:time.sleep(3)
    raise RuntimeError('BLOCKER: post-deploy verification failed: '+type(last_exc).__name__+': '+str(last_exc))

if __name__=='__main__':
    if len(sys.argv)!=2 or sys.argv[1] not in ('preflight','verify'):
        sys.exit('Usage: python keiba_shared_validate.py preflight|verify')
    (preflight if sys.argv[1]=='preflight' else verify)()
