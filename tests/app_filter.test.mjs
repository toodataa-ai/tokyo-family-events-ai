import assert from 'node:assert/strict';
import {filterEvents,normalizeText,countsByWard,applyVerification,rollingWeekSlots,publicationTierMeta,verificationStateMeta,familyFitAxisRows} from '../site/app.js';

const axes={
  child_target:{grade:'A',reason:'親子対象'},
  interactivity:{grade:'A',reason:'体験あり'},
  age_fit:{grade:'A',reason:'幼児小学生向け'},
  stay_flexibility:{grade:'B',reason:'時間枠あり'},
  burden:{grade:'A',reason:'負担小'},
  cost:{grade:'A',reason:'無料'},
  reservation:{grade:'B',reason:'事前予約'},
  family_value:{grade:'A',reason:'家族で行く価値が高い'}
};
const events=[
  {id:'suginami-plafes',ward:'杉並区',name:'高円寺プラフェス 2026秋',period:'10/10〜10/11',date_end:'2026-10-11',venue:'IMAGINUS',description:'巨大レイアウトでプラレールを走らせる親子イベント',categories:['電車','プラレール'],family_fit:{grade:'A',overall:'A',reason:'幼児・小学生を中心に親子で楽しめる',age:'子ども〜大人',axes},reservation:{required:true,note:'事前予約'}},
  {id:'edogawa-festival',ward:'江戸川区',name:'江戸川区民まつり',venue:'都立篠崎公園',description:'親子向け体験・動物・キッズステージ',categories:['祭り','動物']}
];

assert.equal(filterEvents(events,{ward:'杉並区',q:''}).length,1);
assert.equal(filterEvents(events,{ward:'__all__',q:'プラレール'}).length,1);
assert.equal(filterEvents(events,{ward:'杉並区',q:'IMAGINUS'}).length,1);
assert.equal(filterEvents(events,{ward:'杉並区',q:'いまじなす'}).length,0);
assert.equal(filterEvents(events,{ward:'江戸川区',q:'動物'}).length,1);
assert.equal(filterEvents(events,{ward:'杉並区',q:'家族価値'}).length,1);
assert.equal(filterEvents(events,{ward:'杉並区',q:'負担小'}).length,1);
assert.equal(normalizeText('  ＡＢＣ　１２３  '),'abc 123');
assert.equal(familyFitAxisRows(events[0].family_fit).length,8);
assert.equal(familyFitAxisRows(events[1].family_fit).length,0);

const counts=countsByWard(events);assert.equal(counts['杉並区'],1);assert.equal(counts['江戸川区'],1);assert.equal(counts['中野区'],0);

const audit={verified_on:'2026-10-06',events:[
  {id:'suginami-plafes',status:'verified',source:'https://example.com/official',source_kind:'organizer_official',fields:{name:'pass',date:'corrected',venue:'corrected'},note:'公式確認済み',corrections:{period:'10/10〜10/12',date_end:'2026-10-12',venue:'IMAGINUS 3階 企画展示室'}},
  {id:'edogawa-festival',status:'announced',source:'https://example.com/announcement',source_kind:'official',fields:{name:'pass',date:'pass',venue:'pass',time:'unknown',price:'unknown'},note:'開催日と会場は公式発表済み。時間と料金は後日発表。',corrections:{}}
]};
const corrected=applyVerification(events,audit);assert.equal(corrected[0].period,'10/10〜10/12');assert.equal(corrected[0].date_end,'2026-10-12');assert.equal(corrected[0].venue,'IMAGINUS 3階 企画展示室');assert.equal(corrected[0].verification.status,'verified');assert.equal(corrected[0].verification.verified_on,'2026-10-06');assert.equal(corrected[1].verification.status,'announced');assert.equal(filterEvents(corrected,{ward:'杉並区',q:'企画展示室'}).length,1);assert.equal(filterEvents(corrected,{ward:'江戸川区',q:'詳細待ち'}).length,1);

const manifest={default:'2026-10-10',rolling_horizon_weeks:6,weekends:[{sat:'2026-10-10',sun:'2026-10-11',publication_tier:'full',horizon_index:1,count:37},{sat:'2026-10-24',sun:'2026-10-25',publication_tier:'preview',horizon_index:3,count:12}]};
const slots=rollingWeekSlots(manifest);assert.equal(slots.length,6);assert.equal(slots[0].sat,'2026-10-10');assert.equal(slots[1].sat,'2026-10-17');assert.equal(slots[1].available,false);assert.equal(slots[2].publication_tier,'preview');assert.equal(slots[4].publication_tier,'announcement');assert.equal(publicationTierMeta('preview').label,'先取り');assert.equal(verificationStateMeta('verified').label,'✓ 公式確認済み');assert.equal(verificationStateMeta('announced').label,'○ 開催発表済み・詳細待ち');

console.log('shared filter + verification + rolling horizon + family-fit tests: OK');


/* LEGACY PARITY REGRESSION
   Every legacy event in overlapping weeks must be accounted for by published data
   or the decision audit. Tokyo-23-ward exclusions must retain a reason; outside-23
   entries must be explicitly excluded as outside_23wards. */
const fsParity=(await import('node:fs')).default;
const pathParity=(await import('node:path')).default;
const assertParity=(await import('node:assert/strict')).default;
const legacyBaseline=[
  {
    "sat": "2026-10-10",
    "name": "ちいかわ☆星ふるスカイツリー(R)とひみつの島",
    "area": "墨田",
    "official_url": "https://www.tokyo-skytree.jp/event/special/chiikawa/",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-10",
    "name": "すみだ五彩の芸術祭",
    "area": "墨田",
    "official_url": "https://sumida-artfest.jp",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-10",
    "name": "オクトーバーフェストin東京スカイツリータウン®︎2026",
    "area": "墨田",
    "official_url": "https://okfes.jp/202609-skytree/",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-10",
    "name": "お祭りBBQビアガーデン 浅草エキミセ屋台村",
    "area": "浅草",
    "official_url": "https://bbq.urban-earth.jp/asakusa",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-10",
    "name": "祝）いきもの超ワールド展 国立科学博物館×ダーウィンが来た！",
    "area": "上野公園",
    "official_url": "https://www.kahaku.go.jp",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-10",
    "name": "特別展「発見された東京の化石」",
    "area": "日比谷公園",
    "official_url": "https://www.library.chiyoda.tokyo.jp/information/20260705-tokyonokaseki/",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-10",
    "name": "HUMAN AND NATURE",
    "area": "日比谷公園",
    "official_url": "https://www.hibiya.tokyo-midtown.com/humanandnature.yuichihirako/",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-10",
    "name": "祝）ざんねんないきもの展３",
    "area": "池袋",
    "official_url": "https://sunshinecity.jp/file/aquarium/zannen/",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-10",
    "name": "ボボボーボ・ボーボボ展 DIVE INTO THE BO-BOBO WORLD",
    "area": "池袋",
    "official_url": "https://www.toei-anim.co.jp/lp/bo-bobo/world/",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-10",
    "name": "祝）第17回 九州観光・物産フェアin代々木2026",
    "area": "代々木公園",
    "official_url": "https://kyushu-yoyogipark.com/",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-10",
    "name": "祝）HERO GATE",
    "area": "代々木公園",
    "official_url": null,
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-10",
    "name": "TVアニメ『薬屋のひとりごと』 × 東京シティビュー 舞が織りなす幻想の世界 ―天空に響く、舞のしらべ―",
    "area": "六本木",
    "official_url": "https://kusuriya-event-roppongihills.com/",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-10",
    "name": "祝）〜（月・祝）ピクサーの世界展",
    "area": "豊洲",
    "official_url": "https://mundopixar.com/ja/cities/tokyo",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-10",
    "name": "祝）オクトーバーフェスト2026 in アーバンドック ららぽーと豊洲",
    "area": "豊洲",
    "official_url": "https://www.oktober-fest.jp/",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-10",
    "name": "祝）BMSG FES'26",
    "area": "お台場",
    "official_url": "https://bmsgfes.tokyo/",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-10",
    "name": "祝）UNI9UE PARK MARCHE’26",
    "area": "お台場",
    "official_url": "https://www.nikoand.jp/uni9ue_park_2026/",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-10",
    "name": "特別展「エリック・カールといのちの色‐同じ世界で、ちがう色‐」",
    "area": "品川",
    "official_url": "https://www.aquarium.gr.jp/news/events/31639",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-10",
    "name": "祝）妖怪盆踊り2026",
    "area": "立川",
    "official_url": "http://www.yokaibonodori.tokyo/",
    "in_scope_23wards": false
  },
  {
    "sat": "2026-10-17",
    "name": "ちいかわ☆星ふるスカイツリー(R)とひみつの島",
    "area": "墨田",
    "official_url": "https://www.tokyo-skytree.jp/event/special/chiikawa/",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-17",
    "name": "すみだ五彩の芸術祭",
    "area": "墨田",
    "official_url": "https://sumida-artfest.jp",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-17",
    "name": "オクトーバーフェストin東京スカイツリータウン®︎2026",
    "area": "墨田",
    "official_url": "https://okfes.jp/202609-skytree/",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-17",
    "name": "お祭りBBQビアガーデン 浅草エキミセ屋台村",
    "area": "浅草",
    "official_url": "https://bbq.urban-earth.jp/asakusa",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-17",
    "name": "特別展「発見された東京の化石」",
    "area": "日比谷公園",
    "official_url": "https://www.library.chiyoda.tokyo.jp/information/20260705-tokyonokaseki/",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-17",
    "name": "HUMAN AND NATURE",
    "area": "日比谷公園",
    "official_url": "https://www.hibiya.tokyo-midtown.com/humanandnature.yuichihirako/",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-17",
    "name": "祝）ざんねんないきもの展３",
    "area": "池袋",
    "official_url": "https://sunshinecity.jp/file/aquarium/zannen/",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-17",
    "name": "ボボボーボ・ボーボボ展 DIVE INTO THE BO-BOBO WORLD",
    "area": "池袋",
    "official_url": "https://www.toei-anim.co.jp/lp/bo-bobo/world/",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-17",
    "name": "カリブ・ラテンアメリカストリート代々木2026",
    "area": "代々木公園",
    "official_url": "https://wsavannast.com/events/the-caribbean-latin-america-street/",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-17",
    "name": "TVアニメ『薬屋のひとりごと』 × 東京シティビュー 舞が織りなす幻想の世界 ―天空に響く、舞のしらべ―",
    "area": "六本木",
    "official_url": "https://kusuriya-event-roppongihills.com/",
    "in_scope_23wards": true
  },
  {
    "sat": "2026-10-17",
    "name": "特別展「エリック・カールといのちの色‐同じ世界で、ちがう色‐」",
    "area": "品川",
    "official_url": "https://www.aquarium.gr.jp/news/events/31639",
    "in_scope_23wards": true
  }
];
const dataRoot=pathParity.resolve(process.cwd(),'site/data');
const normLegacyName=value=>String(value??'').normalize('NFKC').toLowerCase()
  .replace(/^祝）/,'').replace(/令和8年/g,'').replace(/2026/g,'')
  .replace(/[®︎®™'’‘"“”・\\s_\\-‐‑–—―~〜～()（）「」『』【】\\[\\]：:／/]/g,'');
const canonLegacyUrl=value=>{
  try{const u=new URL(String(value||''));return (u.hostname.replace(/^www\\./,'')+u.pathname.replace(/\\/$/,'')).toLowerCase();}
  catch{return '';}
};
const legacyNameMatch=(a,b)=>{
  const x=normLegacyName(a),y=normLegacyName(b);
  return x===y || (Math.min(x.length,y.length)>=6 && (x.includes(y)||y.includes(x)));
};
const legacyRowMatch=(legacy,row)=>{
  if(legacyNameMatch(legacy.name,row.name))return true;
  const lu=canonLegacyUrl(legacy.official_url);if(!lu)return false;
  const urls=[row.url,row.official_url,row.source,...((row.evidence||[]).map(x=>x?.url))].map(canonLegacyUrl);
  return urls.includes(lu);
};
const loadPublishedForParity=sat=>{
  const meta=JSON.parse(fsParity.readFileSync(pathParity.join(dataRoot,sat+'.json'),'utf8'));
  const rows=Array.isArray(meta.events)?[...meta.events]:[];
  for(const file of (meta.event_files||[]))rows.push(...JSON.parse(fsParity.readFileSync(pathParity.join(dataRoot,file),'utf8')));
  return rows;
};
for(const sat of [...new Set(legacyBaseline.map(x=>x.sat))]){
  const published=loadPublishedForParity(sat);
  const decisions=JSON.parse(fsParity.readFileSync(pathParity.join(dataRoot,sat+'-decisions.json'),'utf8')).decisions||[];
  for(const legacy of legacyBaseline.filter(x=>x.sat===sat)){
    const pub=published.find(row=>legacyRowMatch(legacy,row));
    const dec=decisions.find(row=>legacyRowMatch(legacy,row));
    if(legacy.in_scope_23wards){
      assertParity.ok(pub||dec,`${sat}: legacy event is unaccounted for: ${legacy.name}`);
      if(!pub){
        assertParity.ok(['excluded','duplicate'].includes(dec?.decision),`${sat}: non-published legacy event needs an audited disposition: ${legacy.name}`);
        assertParity.ok((dec?.reasons||[]).length>0,`${sat}: audited disposition needs reasons: ${legacy.name}`);
      }
    }else{
      assertParity.ok(dec,`${sat}: outside-scope legacy event needs an audit row: ${legacy.name}`);
      assertParity.equal(dec.decision,'excluded',`${sat}: outside-scope legacy event must be excluded: ${legacy.name}`);
      assertParity.equal(dec.primary_reason_code,'outside_23wards',`${sat}: outside-scope reason must be outside_23wards: ${legacy.name}`);
    }
  }
}
console.log(`legacy parity regression: ${legacyBaseline.length}/${legacyBaseline.length} rows accounted for`);
