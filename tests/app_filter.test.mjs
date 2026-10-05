import assert from 'node:assert/strict';
import {filterEvents,normalizeText,countsByWard,applyVerification} from '../site/app.js';

const events = [
  {
    id:'suginami-plafes',
    ward:'杉並区',
    name:'高円寺プラフェス 2026秋',
    period:'10/10〜10/11',
    date_end:'2026-10-11',
    venue:'IMAGINUS',
    description:'巨大レイアウトでプラレールを走らせる親子イベント',
    categories:['電車','プラレール'],
    family_fit:{grade:'A',reason:'幼児・小学生を中心に親子で楽しめる',age:'子ども〜大人'},
    reservation:{required:true,note:'事前予約'}
  },
  {
    id:'edogawa-festival',
    ward:'江戸川区',
    name:'江戸川区民まつり',
    venue:'都立篠崎公園',
    description:'親子向け体験・動物・キッズステージ',
    categories:['祭り','動物']
  }
];

assert.equal(filterEvents(events,{ward:'杉並区',q:''}).length,1);
assert.equal(filterEvents(events,{ward:'__all__',q:'プラレール'}).length,1);
assert.equal(filterEvents(events,{ward:'杉並区',q:'IMAGINUS'}).length,1);
assert.equal(filterEvents(events,{ward:'杉並区',q:'いまじなす'}).length,0);
assert.equal(filterEvents(events,{ward:'江戸川区',q:'動物'}).length,1);
assert.equal(filterEvents(events,{ward:'杉並区',q:'動物'}).length,0);
assert.equal(normalizeText('  ＡＢＣ　１２３  '),'abc 123');

const counts=countsByWard(events);
assert.equal(counts['杉並区'],1);
assert.equal(counts['江戸川区'],1);
assert.equal(counts['中野区'],0);

const audit={
  verified_on:'2026-10-06',
  events:[{
    id:'suginami-plafes',status:'verified',source:'https://example.com/official',source_kind:'organizer_official',
    fields:{name:'pass',date:'corrected',venue:'corrected'},note:'公式確認済み',
    corrections:{period:'10/10〜10/12',date_end:'2026-10-12',venue:'IMAGINUS 3階 企画展示室'}
  }]
};
const corrected=applyVerification(events,audit);
assert.equal(corrected[0].period,'10/10〜10/12');
assert.equal(corrected[0].date_end,'2026-10-12');
assert.equal(corrected[0].venue,'IMAGINUS 3階 企画展示室');
assert.equal(corrected[0].verification.status,'verified');
assert.equal(corrected[0].verification.verified_on,'2026-10-06');
assert.equal(corrected[1].verification.status,'unverified');
assert.equal(filterEvents(corrected,{ward:'杉並区',q:'企画展示室'}).length,1);

console.log('shared filter + verification tests: OK');
