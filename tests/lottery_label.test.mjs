import assert from 'node:assert/strict';
import {reservationLabel,reservationCategory} from '../site/app.js';
const ev=(required,note,description='')=>({reservation:{required,note},description});
for(const e of [ev(true,'抽選事前申込'),ev(true,'各回20名・抽選。'),ev(true,'定員超過時は抽選。'),ev(true,'要事前申込、11/21まで','応募多数時抽選。')]){
  assert.equal(reservationLabel(e),'抽選');
  assert.equal(reservationCategory(e),'required','絞り込みの区分は変えない');
}
for(const e of [ev(true,'要予約。先着順（抽選なし）'),ev(true,'要予約。景品は抽選'),ev(true,'要予約。一部プログラムは抽選'),ev(true,'要予約。当日は抽選会あり'),ev(true,'要予約','来場者向けのお楽しみ抽選あり')])
  assert.equal(reservationLabel(e),'要事前申込',e.reservation.note);
const quoted=(quote,required=true)=>({...ev(required,'申込フォームから'),family_fit:{review:{evidence:[{quote}]}}});
assert.equal(reservationLabel(quoted('定員 12名 抽選 費用')),'抽選');
assert.equal(reservationLabel(quoted('定員 ：各回１００名（抽選）')),'抽選');
assert.equal(reservationLabel(quoted('定員 12名 先着 景品の抽選')),'要事前申込');
assert.equal(reservationLabel(quoted('定員 12名 抽選',false)),'申込不要');
assert.equal(reservationLabel(ev(false,'景品は抽選')),'申込不要');
assert.equal(reservationLabel(ev(null,'定員超過は抽選')),'申込要確認');
console.log('PASS: lottery events are labelled 抽選; prize draws and partial lotteries are not');
