// Presentation-only parent/child hierarchy. Published individual-event rows,
// official evidence, immutable identifiers, URLs, periods and saved Canva selections
// are never rewritten. Only a trusted allowlist can be grouped.
export const NAKANO_FESTIVAL_SOURCE='https://www.city.tokyo-nakano.lg.jp/kanko/city-promotion/animemangafest2026.html';
export const NERIMA_FOREST_SOURCE='https://www.city.nerima.tokyo.jp/kurashi/shigoto/midori/shokai/nerimanomori.html';
export const NAKANO_FESTIVAL_GROUP_ID='display-festival-nakano-20261205';
export const NERIMA_FOREST_GROUP_ID='display-festival-nerima-forest-20261205';
export const NERIMA_FOREST_NOV03_GROUP_ID='display-festival-nerima-forest-20261103';
export const NAKANO_FESTIVAL_CHILD_IDS=Object.freeze([
  'v15-20261205-nakano-oshiri',
  'v15-20261205-nakano-precure-show',
  'v15-20261205-nakano-screening-hakujaden',
  'v15-20261205-nakano-screening-bananya',
  'v15-20261205-nakano-screening-vanguard',
  'v15-20261205-nakano-screening-kitaro',
  'v15-20261205-nakano-student-art',
  'v15-20261205-nakano-vanguard'
]);
export const NERIMA_FOREST_NOV03_CHILD_IDS=Object.freeze([
  'official-20261103-nerima-mori-fair',
  'official-20261103-nerima-mori-leaves'
]);
export const NERIMA_FOREST_CHILD_IDS=Object.freeze([
  'v15-20261205-nerima-mori-leaf',
  'v15-20261205-nerima-mori-otaka',
  'v15-20261205-nerima-mori-takamatsu'
]);
const SPECS=Object.freeze([
  {
    id:NAKANO_FESTIVAL_GROUP_ID,source:NAKANO_FESTIVAL_SOURCE,ward:'中野区',
    date:'2026-12-05',period:'12/5(土)',
    ids:NAKANO_FESTIVAL_CHILD_IDS,
    name:'中野×杉並×豊島アニメ・マンガフェス2026（中野会場）',
    venue:'なかのZERO（小ホール・西館・本館）',
    time:'10:00〜18:00（企画により異なる）',
    price:'無料の企画あり／一部の企画は料金要確認',
    reservation:'抽選制・当日整理券・申込不要など、企画ごとに異なります。',
    description:'12月5日に中野会場で開催。プリキュアショー・おしりたんてい工作・特別上映会4枠・アート展示・カードゲームなどの企画をまとめて紹介します。申込方法は企画ごとに異なります。',
    categories:['フェスティバル','アニメ','マンガ','親子','映画','上映会','工作','カードゲーム'],
    type:'nakano'
  },
  {
    id:NERIMA_FOREST_GROUP_ID,source:NERIMA_FOREST_SOURCE,ward:'練馬区',
    date:'2026-12-05',period:'12/5(土)',
    ids:NERIMA_FOREST_CHILD_IDS,
    name:'ねりまの森こどもフェスタ2026（12月5日開催）',
    venue:'練馬区内3会場（石庭の森・大関山の森・南高松の森）',
    time:'9:30〜14:30（3会場で異なる時間に開催）',
    price:'無料',
    reservation:'予約不要・当日会場へ。雨天中止（一部除く）。各会場に駐車場なし。',
    description:'練馬区内の森で、落ち葉祭り（石庭の森）と森のおしごと体験（大関山・南高松の森）を開催。会場・時間が異なるため、詳細で参加先を確認してください。',
    categories:['フェスティバル','自然体験','落ち葉','子ども','親子','森'],
    type:'nerima'
  },
  {
    id:NERIMA_FOREST_NOV03_GROUP_ID,source:NERIMA_FOREST_SOURCE,ward:'練馬区',
    date:'2026-11-03',period:'11/3(火・祝)',
    ids:NERIMA_FOREST_NOV03_CHILD_IDS,
    name:'ねりまの森こどもフェスタ2026（11月3日開催）',
    venue:'練馬区内2会場（大関山の森・竹の子憩いの森）',
    time:'9:30〜11:30（2会場で開催）',
    price:'原則無料（一部の企画は有料）',
    reservation:'公式案内では事前予約不要。雨天中止（一部除く）。各会場に駐車場なし。',
    description:'大関山の森では秋のフェア、竹の子憩いの森では落ち葉あそびを開催。各会場の開催時間・場所を詳細で確認できます。',
    categories:['フェスティバル','自然体験','秋のフェア','落ち葉','子ども','親子','森'],
    type:'nerima'
  }
]);
const SPEC_BY_ID=new Map(SPECS.flatMap(spec=>spec.ids.map(id=>[id,spec])));
function groupFor(ev){
  if(!ev)return null;
  const spec=SPEC_BY_ID.get(ev.id);
  return spec&&ev.ward===spec.ward&&ev.date_start===spec.date&&ev.date_end===spec.date
    &&ev.official_url===spec.source?spec:null;
}
export function isNakanoFestivalChild(ev){return groupFor(ev)?.id===NAKANO_FESTIVAL_GROUP_ID;}
export function isNerimaForestChild(ev){
  return [NERIMA_FOREST_GROUP_ID,NERIMA_FOREST_NOV03_GROUP_ID].includes(groupFor(ev)?.id);
}

function makeGroup(members,spec){
  if(!members.length||!members.every(ev=>groupFor(ev)===spec))return null;
  const best=members.find(ev=>ev.family_fit?.overall==='A')||members[0];
  return {
    ...best,id:spec.id,name:spec.name,
    date_start:spec.date,date_end:spec.date,period:spec.period,
    venue:spec.venue,time:spec.time,price:spec.price,
    reservation:{required:false,note:spec.reservation},
    description:spec.description,categories:spec.categories,
    official_url:spec.source,url:spec.source,source:spec.source,
    image:members.find(ev=>ev.image)?.image||'',
    // All original child facts remain available without modifying source files.
    _festival_group:true,_festival_type:spec.type,
    _festival_members:[...members],_festival_total_programs:spec.ids.length
  };
}
export function buildNakanoFestivalGroup(members){return makeGroup(members,SPECS[0]);}
export function buildNerimaForestGroup(members){return makeGroup(members,SPECS[1]);}
export function buildNerimaForestNov03Group(members){return makeGroup(members,SPECS[2]);}
// Group only AFTER regular event filtering so a search for one specific
// workshop still yields the parent card with only that relevant activity.
// Non-group events preserve their original order and identities.
export function groupFestivalDisplayEvents(events){
  if(!Array.isArray(events))return [];
  const bySpec=new Map();
  for(const ev of events){
    const spec=groupFor(ev);
    if(spec){if(!bySpec.has(spec))bySpec.set(spec,[]);bySpec.get(spec).push(ev);}
  }
  if(!bySpec.size)return [...events];
  const displayed=[],inserted=new Set();
  for(const ev of events){
    const spec=groupFor(ev);
    if(!spec){displayed.push(ev);continue;}
    if(!inserted.has(spec.id)){
      displayed.push(makeGroup(bySpec.get(spec),spec));
      inserted.add(spec.id);
    }
  }
  return displayed;
}
export function festivalDisplayChangeKind(group,changes){
  if(!group?._festival_group)return '';
  if(group._festival_members.some(ev=>changes?.added?.has(ev.id)))return 'added';
  if(group._festival_members.some(ev=>changes?.updated?.has(ev.id)))return 'updated';
  return '';
}
export function festivalMemberSummary(group){
  if(!group?._festival_group)return '';
  const n=group._festival_members.length;
  return n===group._festival_total_programs ? '内訳'+n+'企画'
    : '条件に一致'+n+'企画（全'+group._festival_total_programs+'企画）';
}
export function groupedEventChangeCounts(events,changes){
  const counts={added:0,updated:0};
  for(const ev of groupFestivalDisplayEvents(events)){
    const kind=ev._festival_group?festivalDisplayChangeKind(ev,changes):
      changes?.added?.has(ev.id)?'added':changes?.updated?.has(ev.id)?'updated':'';
    if(kind)counts[kind]++;
  }
  return counts;
}
