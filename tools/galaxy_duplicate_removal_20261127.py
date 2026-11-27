#!/usr/bin/env python3
"""Remove 1 duplicate Galaxcity Christmas concert listing (user-approved in chat, 2026-11-27).

lead46 already published the concert from the facility page (kept); lead47 added it again from the Adachi ward page
(removed from the published list). The removal is recorded as an auditable `duplicate` decision."""
import argparse, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import suginami_addition_20261118 as S

BASE = 'dd1a847b9a91112303919227e18dff14353f3751'   # data-production after lead47 (945 active week records)
RUN_ID = 'galaxy-duplicate-removal-20261127'
# week -> shard -> [(removed id, kept id)]
REMOVALS = {
    '2026-12-19': {'2026-12-19-events-lead47-20261127.json': [('verified-20261219-adachi-galaxy-xmas-concert-2026', 'verified-20261219-galaxcity-xmas-concert-2026')]},
}
REMOVED_IDS = sorted(r for w in REMOVALS.values() for s in w.values() for r, _ in s)
REASON = '「ギャラクシティ クリスマスコンサート2026」が施設公式ページ版（既掲載）と区公式ページ版で二重に掲載されたため、後から追加した区公式ページ版を重複として取り下げた（日付・会場・開演時刻・料金が一致）。'


def evidence_url(ev):
    for k in ('official_url', 'url', 'source_url', 'source'):
        v = ev.get(k)
        if isinstance(v, str) and v.startswith('http'):
            return v
    raise ValueError('no official url for ' + str(ev.get('id')))


def build(data_dir):
    d = pathlib.Path(data_dir)
    m = S.jload(d / 'manifest.json')
    for week, shards in REMOVALS.items():
        k = sum(len(v) for v in shards.values())
        removed_events = {}
        for sh, pairs in shards.items():
            rows = S.jload(d / sh)
            ids = {r for r, _ in pairs}
            for r in rows:
                if r.get('id') in ids:
                    removed_events[r['id']] = r
            if set(removed_events) < ids:
                raise ValueError('record not found in ' + sh)
            S.jdump(d / sh, [r for r in rows if r.get('id') not in ids])
        w = S.jload(d / f'{week}.json')
        c = w['coverage']
        c['published_count'] -= k
        c['duplicate_removed'] = (c.get('duplicate_removed') or 0) + k
        for row in c['wards']:
            if row['ward'] == '足立区':
                row['published_count'] -= k
                row['note'] = (row.get('note') or '') + f' 2026-11-27 同一イベントの二重掲載{k}件を重複として取り下げ（決定記録あり）。'
        S.jdump(d / f'{week}.json', w)
        v = S.jload(d / f'{week}-verification.json')
        v['events'] = [e for e in v['events'] if e.get('id') not in removed_events]
        v['summary'] = dict(v['summary'], total=v['summary']['total'] - k, verified=v['summary']['verified'] - k)
        S.jdump(d / f'{week}-verification.json', v)
        dec = S.jload(d / f'{week}-decisions.json')
        kept = {r: kk for pairs in shards.values() for r, kk in pairs}
        for row in dec['decisions']:
            cid = row.get('candidate_id')
            if cid in removed_events:
                ev = removed_events[cid]
                row['decision'] = 'duplicate'
                row['duplicate_of'] = kept[cid]
                row['reasons'] = [REASON]
                row['evidence'] = [{'url': evidence_url(ev), 'kind': 'official_event_page', 'checked_at': '2026-11-27'}]
                row.pop('family_fit', None)
        dec['summary'] = dict(dec['summary'], published=dec['summary']['published'] - k, duplicate=dec['summary'].get('duplicate', 0) + k)
        S.jdump(d / f'{week}-decisions.json', dec)
        run = S.jload(d / f'{week}-run.json')
        run['summary'] = dict(run['summary'], published=run['summary']['published'] - k, verified=run['summary']['verified'] - k)
        S.jdump(d / f'{week}-run.json', run)
        for x in m['weekends']:
            if x['sat'] == week:
                x['count'] -= k
    m['generated'] = '2026-11-27T14:00:00+09:00'
    S.jdump(d / 'manifest.json', m)
    h = S.jload(d / 'update_history.json')
    h['history'].append({
        'run_id': RUN_ID, 'run_type': 'manual_duplicate_removal', 'status': 'duplicate_decisions_recorded', 'as_of_jst': '2026-11-27',
        'executed_at': m['generated'], 'base_data_production_sha': BASE, 'target_weekends': sorted(REMOVALS),
        'prior_active_week_records': 945, 'candidate_active_week_records': 944, 'added_weekly_records': 0,
        'new_event_ids': [], 'duplicate_decisions_recorded': REMOVED_IDS,
        'duplicate_of': {r: kk for w in REMOVALS.values() for s in w.values() for r, kk in s},
        'existing_event_records_physically_deleted': 0, 'global_source_audit_complete': False,
        'note': '二重掲載のギャラクシティ クリスマスコンサート1件（区公式ページ版）を、利用者の承認により決定記録（duplicate・重複元ID・理由・公式URL）付きで公開リストから取り下げた。'})
    S.jdump(d / 'update_history.json', h)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--data-dir', required=True); a = ap.parse_args()
    try: build(a.data_dir)
    except ValueError as e: print('ERROR:', e, file=sys.stderr); sys.exit(1)
