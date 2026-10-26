// Presentation-only festival hierarchy. Never delete/merge the immutable event
// records, validation proof, date intervals or previously saved Canva IDs.
export const NAKANO_FESTIVAL_SOURCE='https://www.city.tokyo-nakano.lg.jp/kanko/city-promotion/animemangafest2026.html';
export const NAKANO_FESTIVAL_GROUP_ID='display-festival-nakano-20261205';
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
const CHILDREN=new Set(NAKANO_FESTIVAL_CHILD_IDS);
const festivalTitle='中野×杉並×豊島アニメ・マンガフェス2026（中野会場）';

export function isNakanoFestivalChild(ev){
  return Boolean(ev && CHILDREN.has(ev.id) && ev.ward==='中野区'
    && ev.date_start==='2026-12-05' && ev.date_end==='2026-12-05'
    && ev.official_url===NAKANO_FESTIVAL_SOURCE);
}
export function buildNakanoFestivalGroup(members){
  if(!Array.isArray(members)||!members.length||!members.every(isNakanoFestivalChild))return null;
  const best=members.find(ev=>ev.family_fit?.overall==='A')||members[0];
  // Detailed programs live in _festival_members, so the Canva description stays readable.
  return {
    ...best,
    id:NAKANO_FESTIVAL_GROUP_ID,
    name:festivalTitle,
    date_start:'2026-12-05',date_end:'2026-12-05',period:'12/5(土)',
    venue:'なかのZERO（小ホール・西館・本館）',
    time:'10:00〜18:00（企画により異なる）',
    price:'無料の企画あり／一部の企画は料金要確認',
    reservation:{required:false,note:'抽選制・当日整理券・申込不要など、企画ごとに異なります。'},
    description:'12月5日に中野会場で開催。プリキュアショー・おしりたんてい工作・特別上映会4枠・アート展示・カードゲームなど8企画をまとめて紹介します。申込方法は企画ごとに異なります。',
    categories:['フェスティバル','アニメ','マンガ','親子','映画','上映会','工作','カードゲーム'],
    official_url:NAKANO_FESTIVAL_SOURCE,url:NAKANO_FESTIVAL_SOURCE,source:NAKANO_FESTIVAL_SOURCE,
    image:members.find(ev=>ev.image)?.image||'',
    _festival_group:true,
    _festival_members:[...members],
    _festival_total_programs:NAKANO_FESTIVAL_CHILD_IDS.length
  };
}
// Called AFTER normal individual event filtering: date, age, availability,
// keyword and source filters keep their exact pre-existing semantics.
export function groupFestivalDisplayEvents(events){
  if(!Array.isArray(events))return [];
  const members=events.filter(isNakanoFestivalChild);
  if(!members.length)return [...events];
  const group=buildNakanoFestivalGroup(members);
  const out=[];
  let inserted=false;
  for(const ev of events){
    if(isNakanoFestivalChild(ev)){
      if(!inserted){out.push(group);inserted=true;}
    }else out.push(ev);
  }
  return out;
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
