import assert from 'node:assert/strict';
import {filterEvents,normalizeText,countsByWard} from '../site/app.js';

const events = [
  {
    ward:'杉並区',
    name:'高円寺プラフェス 2026秋',
    venue:'IMAGINUS',
    description:'巨大レイアウトでプラレールを走らせる親子イベント',
    categories:['電車','プラレール'],
    family_fit:{reason:'幼児・小学生を中心に親子で楽しめる',age:'子ども〜大人'},
    reservation:{note:'事前予約'}
  },
  {
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

console.log('shared filter tests: OK');
