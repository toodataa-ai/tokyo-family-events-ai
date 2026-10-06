import assert from 'node:assert/strict';
import {filterEvents,normalizeText,countsByWard,applyVerification,rollingWeekSlots,publicationTierMeta,verificationStateMeta} from '../site/app.js';

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
  },{
    id:'edogawa-festival',status:'announced',source:'https://example.com/announcement',source_kind:'official',
    fields:{name:'pass',date:'pass',venue:'pass',time:'unknown',price:'unknown'},note:'開催日と会場は公式発表済み。時間と料金は後日発表。',
    corrections:{}
  }]
};
const corrected=applyVerification(events,audit);
assert.equal(corrected[0].period,'10/10〜10/12');
assert.equal(corrected[0].date_end,'2026-10-12');
assert.equal(corrected[0].venue,'IMAGINUS 3階 企画展示室');
assert.equal(corrected[0].verification.status,'verified');
assert.equal(corrected[0].verification.verified_on,'2026-10-06');
assert.equal(corrected[1].verification.status,'announced');
assert.equal(filterEvents(corrected,{ward:'杉並区',q:'企画展示室'}).length,1);
assert.equal(filterEvents(corrected,{ward:'江戸川区',q:'詳細待ち'}).length,1);

const manifest={
  default:'2026-10-10',
  rolling_horizon_weeks:6,
  weekends:[
    {sat:'2026-10-10',sun:'2026-10-11',publication_tier:'full',horizon_index:1,count:37},
    {sat:'2026-10-24',sun:'2026-10-25',publication_tier:'preview',horizon_index:3,count:12}
  ]
};
const slots=rollingWeekSlots(manifest);
assert.equal(slots.length,6);
assert.equal(slots[0].sat,'2026-10-10');
assert.equal(slots[1].sat,'2026-10-17');
assert.equal(slots[1].available,false);
assert.equal(slots[2].publication_tier,'preview');
assert.equal(slots[4].publication_tier,'announcement');
assert.equal(publicationTierMeta('preview').label,'先取り');
assert.equal(verificationStateMeta('verified').label,'✓ 公式確認済み');
assert.equal(verificationStateMeta('announced').label,'○ 開催発表済み・詳細待ち');

console.log('shared filter + verification + rolling horizon tests: OK');
