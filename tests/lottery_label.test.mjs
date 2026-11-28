import assert from 'node:assert/strict';
import {reservationLabel,reservationCategory} from '../site/app.js';
const ev=(required,note,description='')=>({reservation:{required,note},description});
const check=(label,list)=>{for(const e of list){
  assert.equal(reservationLabel(e),label,e.reservation.note);
  assert.equal(reservationCategory(e),'required','絞り込みの区分は変えない');
}};
check('抽選',[ev(true,'抽選事前申込'),ev(true,'各回20名・抽選。'),ev(true,'要申込（抽選）。当落連絡は11/28'),ev(true,'往復はがきで申込。抽選結果は後日通知'),
  ev(true,'抽選申込制。定員を超えた場合は市内在住の方を優先して抽選')]);
check('超過時抽選',[ev(true,'定員超過時は抽選。'),ev(true,'先着20名（超過なら抽選）'),ev(true,'定員を大幅に超えた場合は抽選'),
  ev(true,'応募多数の場合は抽選となります。抽選結果は後日'),ev(true,'申込締切11/20、定員を超えた場合は抽選（結果11/24通知）'),ev(true,'要事前申込、11/21まで','応募多数時抽選。')]);
check('要事前申込',[ev(true,'要予約。先着順（抽選なし）'),ev(true,'要予約。景品は抽選'),ev(true,'要予約。一部プログラムは抽選'),ev(true,'要予約。当日は抽選会あり'),ev(true,'要予約','来場者向けのお楽しみ抽選あり')]);
const quoted=(quote,required=true)=>({...ev(required,'申込フォームから'),family_fit:{review:{evidence:[{quote}]}}});
assert.equal(reservationLabel(quoted('定員 12名 抽選 費用')),'抽選');
assert.equal(reservationLabel(quoted('定員 ：各回１００名（抽選）')),'抽選');
assert.equal(reservationLabel(quoted('定員 12名 先着 景品の抽選')),'要事前申込');
assert.equal(reservationLabel(quoted('定員 12名 抽選',false)),'申込不要');
assert.equal(reservationLabel(quoted('申し込み多数の場合は、抽選となります。定員 各回 20人（抽選）')),'超過時抽選');
assert.equal(reservationLabel(ev(false,'景品は抽選')),'申込不要');
assert.equal(reservationLabel(ev(null,'定員超過は抽選')),'申込要確認');
console.log('PASS: 抽選 / 超過時抽選 are distinguished; prize draws and partial lotteries are not');
