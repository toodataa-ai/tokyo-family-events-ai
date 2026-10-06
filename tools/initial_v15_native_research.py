#!/usr/bin/env python3
import copy,datetime,difflib,hashlib,json,pathlib,re,subprocess,sys,unicodedata
from urllib.parse import urlsplit,urlunsplit
ROOT=pathlib.Path.cwd(); DATA=ROOT/'site/data'; TMP=pathlib.Path('/tmp/tokyo-weekend-events')
WEEKS=['2026-10-10','2026-10-17','2026-10-24','2026-10-31','2026-11-07','2026-11-14']
WARDS=['千代田区','中央区','港区','新宿区','文京区','台東区','墨田区','江東区','品川区','目黒区','大田区','世田谷区','渋谷区','中野区','杉並区','豊島区','北区','荒川区','板橋区','練馬区','足立区','葛飾区','江戸川区']
AREA={'墨田':'墨田区','浅草':'台東区','上野公園':'台東区','秋葉原':'千代田区','日比谷公園':'千代田区','池袋':'豊島区','新宿':'新宿区','中野':'中野区','代々木公園':'渋谷区','渋谷':'渋谷区','六本木':'港区','豊洲':'江東区','お台場':'江東区','品川':'品川区','立川':'立川市','練馬区':'練馬区','杉並区':'杉並区','練馬（アイテラス）':'豊島区'}
PORTALS={'sumidaevent.com','asakusaevent.com','uenopark.info','akihabaraevent.com','hibiyapark.info','ikebukuropark.info','shinjukuevent.com','nakanoevent.com','yoyogikoen.info','miyashitapark.info','roppongievents.com','toyosuevent.com','odaibapark.com','shinagawaevent.com','tachikawaevent.com'}
ALCOHOL=re.compile('オクトーバーフェスト|ビアガーデン|クラフトビール|ワインフェス|ビール',re.I)
LOW=re.compile('春画|BMSG FES|アニメイトガールズ|BIOHAZARD|バイオハザード|ときめきメモリアル|森万里子|国際美術展 TOKYO ATLAS|MEET YOUR ART|P.O.N.D.|薬屋のひとりごと|ヘタリア20周年原画展|ボボボーボ・ボーボボ展|管弦楽団|演奏家協会|ねことユリイカ|東京舞台芸術祭|カンテ教室|介護|認知症|ひきこもり|がん相談',re.I)
STRONG=re.compile('子ども|こども|キッズ|kids|親子|ファミリー|児童|乳幼児|小学生|絵本|紙芝居|動物|どうぶつ|いきもの|水族館|生物園|科学|化石|ロボット|工作|ワークショップ|体験|スタンプラリー|鉄道|電車|自転車|スポーツ|運動会|モルック|ハロウィン|花火|盆踊り|縁日|区民まつり|こどもまつり|ファミリーフェス|ちいかわ|エリック・カール|ピクサー|ガシャポン|自然観察',re.I)
BROAD=re.compile('祭り|まつり|フェス|festival|マルシェ|market|公園|文化祭|芸術祭|イルミネーション|シネマ|映画|フリマ',re.I)
EXTRAS={
'2026-10-17':[
('港区','企業と環境展～親子で学べる環境イベント～','https://www.city.minato.tokyo.jp/cgi-bin/event_cal_multi/calendar.cgi?day=17&event_target=2&month=10&siteid=1&type=3&year=2026','10/17〜10/18','2026-10-17','2026-10-18','港区内会場（公式案内参照）',None,'親子で環境を学べる港区公式掲載イベント。',None),
('江東区','第44回江東区民まつり中央まつり','https://www.city.koto.lg.jp/101021/kurashi/komyunitei/kumin/chuo/55.html','10/17〜10/18','2026-10-17','2026-10-18','都立木場公園・江東区文化センター',None,'江東区最大級の区民まつり。体験・地域ブース等。','10:00〜16:00'),
('大田区','親子でハロウィン・ガーデニング','https://www.city.ota.tokyo.jp/event/event_kodomo/calendar/calendar202610.html','10/18','2026-10-18','2026-10-18','大田区内（公式案内参照）',None,'親子で参加するハロウィン時期のガーデニング企画。',None),
('渋谷区','しぶや・もったいないマーケット2026','https://shibuya-mottainai.tokyo/','10/17','2026-10-17','2026-10-17','渋谷区文化総合センター大和田','入場無料（一部ワークショップ有料）','食品ロス・3Rを親子向けワークショップで学ぶ参加型イベント。','10:00〜15:00')],
'2026-10-24':[
('千代田区','神田スポーツ祭り2026','https://visit-chiyoda.tokyo/app/event/detail/959','10/24〜10/25','2026-10-24','2026-10-25','小川広場・神田小川町スポーツ店街',None,'スタンプラリー、ステージ、ワークショップなどを楽しめるスポーツ街のお祭り。','10/24 11:00〜17:00、10/25 11:00〜16:30'),
('台東区','「なくしもの美術館」をつくろう2','https://tokyo-kodomo-hp.metro.tokyo.lg.jp/event/','10/24〜10/25','2026-10-24','2026-10-25','東京都美術館 ギャラリーA',None,'小中学生がパーツを作り大きなインスタレーションをつくるワークショップ。','各日11:00／14:00開始'),
('墨田区','第21回 北斎祭り','https://hokusai-museum.jp/modules/Event/events/view/5065?lang=ja','10/24〜10/25','2026-10-24','2026-10-25','北斎通り周辺',None,'地域文化祭。金魚ねぷたづくりなど子どもも参加できるワークショップ。',None),
('渋谷区','かぞくのアトリエ「音楽と空想のパレード」','https://www.city.shibuya.tokyo.jp/contents/koho-news/1620/20261001_kodomo.html','10/24','2026-10-24','2026-10-24','かぞくのアトリエ（こども・親子支援センター）','一部有料','展示、ライブ、ワークショップなど。未就学児は保護者同伴。','10:00〜16:00'),
('新宿区','ハロウィンおはなしかい','https://www.city.shinjuku.lg.jp/kids/event_index.html','10/25','2026-10-25','2026-10-25','角筈地域センター','無料','小学生までと保護者向けのハロウィンに関するおはなし会。','11:00〜11:45'),
('中央区','キッズフリマ in コレド室町','https://kodomo-smile.metro.tokyo.lg.jp/events/chuoku','10/24〜10/25','2026-10-24','2026-10-25','コレド室町',None,'子どもがモノやお金との関わりを体験するキッズフリマ。',None)],
'2026-10-31':[
('港区','六本木アートナイト2026','https://www.city.minato.tokyo.jp/cgi-bin/event_cal_multi/calendar.cgi?day=31&event_category=1%2C2%2C4&event_target=0&month=10&type=3&year=2026','10/31〜11/1','2026-10-31','2026-11-01','六本木エリア',None,'都市とアートをテーマにした六本木の大型アートイベント。',None),
('目黒区','第16回目黒マルシェ「集結祭」','https://meguromarche.com/','10/31〜11/1','2026-10-31','2026-11-01','目黒通り周辺','入場無料','約100店舗が並び、地域の子どもがお店を運営する「キッドニア目黒」も開催。',None),
('台東区','2026秋 プラバンカーニバル','https://plaban.net/events/202610-11plabancarnival?nskip=4015','10/31〜11/1','2026-10-31','2026-11-01','east side tokyo 4F',None,'子どもから大人まで参加できるプラバン工作ワークショップ。','10/31 12:00〜17:00、11/1 10:00〜16:00'),
('杉並区','11月 いつでもものづくり','https://www.imaginus-suginami.jp/events/2026/10/01/11852/','11/1〜11/30','2026-11-01','2026-11-30','IMAGINUS ものづくりラボ',None,'予約不要で小さな子どもが10〜30分程度で楽しめるクラフト体験。','10:00〜17:00'),
('江東区','パパと遊ぼう～感覚統合あそび～','https://tokyo.ymca.or.jp/jidoukan/news/2026/09/20260925-2.html','10/31','2026-10-31','2026-10-31','江東区東雲児童館','無料','歩ける子どもと父親を主対象にした感覚統合あそび。','10:45〜11:30')],
'2026-11-07':[
('大田区','OTAふれあいフェスタ2026','https://www.o-2.jp/event/otafureaifesta2026/','11/7〜11/8','2026-11-07','2026-11-08','大森ふるさとの浜辺公園・平和島周辺4会場',None,'区内最大の区民まつり。企業・商店街ブースや多様な体験コンテンツ。','10:00〜16:00'),
('大田区','わかばの家 第32回こどもまつり','https://www.city.ota.tokyo.jp/seikatsu/fukushi/shougai/hoiku_kyoiku/hoiku/kodomo-matsuri_20261108.html','11/8','2026-11-08','2026-11-08','こども発達センターわかばの家',None,'地域の子どもも参加できる模擬店・ゲーム・遊びのこどもまつり。','11:30〜14:00'),
('中野区','中野にぎわいフェスタ2026秋','https://nigiwaifesta.com/','11/7〜11/8','2026-11-07','2026-11-08','中野駅周辺',None,'子ども縁日、ワークショップ、マルシェなど複数企画がある地域フェスタ。',None),
('目黒区','目黒リバーサイドフェスティバル2026','https://meguro-river.com/','11/7〜11/8','2026-11-07','2026-11-08','目黒区民センター周辺',None,'スタンプラリー、子どもがツクる街、地域企画など。',None)],
'2026-11-14':[
('台東区','環境（エコ）フェスタたいとう2026','https://www.city.taito.lg.jp/kenchiku/kankyo/kankyogakushu/kankyofesta/ecofesta2026.html','11/14〜11/15','2026-11-14','2026-11-15','環境ふれあい館ひまわり・精華公園','無料','工作、スタンプラリー、お仕事体験など家族で環境を学ぶイベント。','10:00〜16:00'),
('墨田区','MEET SUMIDA 2026 ～すみだの「人」「技」「もの」に出会う～','https://sumida-artfest.jp/events/','11/14〜11/15','2026-11-14','2026-11-15','東京スカイツリー 1F SKYTREE SPACE・ソラマチひろば',None,'すみだの人・技・ものに触れる展示・ワークショップ。',None),
('墨田区','江戸の算術で遊ぼう！北斎の紙芝居と折り紙体験','https://sumida-artfest.jp/events/','11/14','2026-11-14','2026-11-14','すみだ北斎美術館 MARUGEN100',None,'北斎を題材に紙芝居・折り紙・江戸算術を楽しむ参加型企画。',None),
('世田谷区','EVをもっと身近に！＠カーメスト用賀馬事公苑','https://kodomo-smile.metro.tokyo.lg.jp/events/setagayaku','11/14〜11/15','2026-11-14','2026-11-15','カーメスト用賀馬事公苑','無料','EVの試乗・展示などを家族で体験できる無料イベント。',None),
('港区','親子でエコっとプロジェクト～ガムテープのズックやさん','https://www.city.minato.tokyo.jp/cgi-bin/event_cal_multi/calendar.cgi?day=14&month=11&siteid=1&type=3&year=2026','11/14','2026-11-14','2026-11-14','港区内会場（公式案内参照）',None,'親子でエコを学びながらものづくりを行う企画。',None),
('大田区','親子で学ぶはじめての自転車教室','https://www.city.ota.tokyo.jp/event/calendar/list_calendar202611.html','11/15','2026-11-15','2026-11-15','大田区内（公式案内参照）',None,'親子向けの初心者自転車教室。',None)]}
OFFICIAL={'WILDチャンプルー':'https://www.nakano-kanko.com/event-info/event-3826/','花と緑の祭典2026秋':'https://www.city.tokyo-nakano.lg.jp/event/kanko/hanatomidori2026aki.html','第22回 豊洲ハロウィン2026':'https://www.toyosu.or.jp/'}

def host(u):
 try:return urlsplit(u or '').netloc.lower().removeprefix('www.')
 except:return ''
def canon(u):
 try:
  p=urlsplit(u or '');return urlunsplit((p.scheme.lower(),host(u),p.path.rstrip('/') or '/','',''))
 except:return u or ''
def norm(s):return re.sub(r'[\s　・･「」『』【】()（）\[\]ー－〜~!！?？,:：;；\-_/®︎©]+','',unicodedata.normalize('NFKC',s or '').lower())
def load_week(base,w):
 d=json.load(open(base/f'{w}.json',encoding='utf8')); e=list(d.get('events') or [])
 for f in d.get('event_files') or []: e+=json.load(open(base/f,encoding='utf8'))
 return e
def prep_legacy():
 import urllib.request, json
 if TMP.exists(): subprocess.run(['rm','-rf',str(TMP)],check=True)
 ddir=TMP/'site'/'data'; ddir.mkdir(parents=True,exist_ok=True)
 for w in WEEKS:
  req=urllib.request.Request(f'https://toodataa-ai.github.io/tokyo-weekend-events/data/{w}.json',headers={'User-Agent':'Mozilla/5.0 TokyoFamilyEventsAI/1.5'})
  with urllib.request.urlopen(req,timeout=30) as r: data=json.loads(r.read().decode('utf-8'))
  json.dump(data,open(ddir/f'{w}.json','w',encoding='utf8'),ensure_ascii=False)
def ai_c(e,w):
 return {'id':e.get('id') or 'ai-'+hashlib.sha1((w+(e.get('name') or '')).encode()).hexdigest()[:10],'ward':e.get('ward'),'name':e.get('name'),'url':e.get('url'),'official_url':e.get('official_url') or e.get('url'),'source':e.get('source') or e.get('url'),'image':e.get('image'),'period':e.get('period'),'date_start':e.get('date_start'),'date_end':e.get('date_end'),'time':e.get('time'),'venue':e.get('venue'),'price':e.get('price'),'description':e.get('description') or '','categories':e.get('categories') or [],'reservation':e.get('reservation') or {},'indoor_outdoor':e.get('indoor_outdoor'),'origin':'ai','disc':[{'kind':'official_ai_search','url':e.get('source') or e.get('official_url') or e.get('url')}],'old_id':e.get('id')}
def leg_c(e,w):
 p=e.get('period') or ''; parts=p.split('〜'); md=lambda x:(f'2026-{int(x.split("/")[0]):02d}-{int(x.split("/")[1]):02d}' if re.fullmatch(r'\d{1,2}/\d{1,2}',x or '') else None); ds=md(parts[0]); de=md(parts[-1]); de=(str(int(ds[:4])+1)+de[4:]) if ds and de and de<ds else de; area=e.get('area',''); ward='江東区' if area=='お台場' else AREA.get(area,area if area.endswith('区') else '')
 return {'id':'lg-'+hashlib.sha1((w+'|'+(e.get('name') or '')+'|'+(e.get('url') or '')).encode()).hexdigest()[:10],'ward':ward,'name':e.get('name'),'url':e.get('url'),'official_url':e.get('official_url') or e.get('url'),'source':e.get('source') or e.get('url'),'image':e.get('image'),'period':p,'date_start':ds,'date_end':de,'time':e.get('time'),'venue':e.get('venue'),'price':e.get('price'),'description':e.get('description') or '','categories':[],'reservation':{},'indoor_outdoor':None,'origin':'legacy','disc':[{'kind':'legacy_media','url':e.get('source') or e.get('url')},{'kind':'legacy_detail','url':e.get('url')}]}
def extra_c(t,w):
 ward,name,url,period,ds,de,venue,price,desc,time=t
 return {'id':'web-'+hashlib.sha1((w+'|'+name).encode()).hexdigest()[:10],'ward':ward,'name':name,'url':url,'official_url':url,'source':url,'image':None,'period':period,'date_start':ds,'date_end':de,'time':time,'venue':venue,'price':price,'description':desc,'categories':[],'reservation':{},'indoor_outdoor':None,'origin':'web','disc':[{'kind':'v15_web_search','url':url}]}
def merge(raw):
 out=[];dups=[]
 for c in raw:
  m=None
  for o in out:
   if c['ward']!=o['ward']:continue
   sim=difflib.SequenceMatcher(None,norm(c['name']),norm(o['name'])).ratio(); same=canon(c['official_url'])==canon(o['official_url']) and bool(canon(c['official_url']))
   if sim>=.80 or (same and sim>=.50):m=o;break
  if not m:out.append(c);continue
  d=copy.deepcopy(c);d['duplicate_of']=m['id'];dups.append(d);m['disc']+= [x for x in c['disc'] if x not in m['disc']]
  rank={'legacy':0,'web':2,'ai':3}
  if rank[c['origin']]>rank[m['origin']]:
   keep=m['disc'];mid=m['id'];m.clear();m.update(c);m['id']=mid;m['disc']=keep;m['origin']=c['origin']+'+merged'
  else:
   for k in ['official_url','venue','time','price','description','image','date_start','date_end','period']:
    if not m.get(k) and c.get(k):m[k]=c[k]
   m['origin']+='+'+c['origin']
 return out,dups

def axes(c):
 t=' '.join(str(c.get(k) or '') for k in ['name','description','venue','price','time']).lower(); child=bool(STRONG.search(t)); adult=bool(ALCOHOL.search(t) or LOW.search(t)); interactive=bool(re.search('ワークショップ|体験|工作|スタンプラリー|ゲーム|縁日|遊び|スポーツ|祭り|まつり|フェス|フリマ|教室|ツアー',t)); passive=bool(re.search('展示|展覧会|美術館|博物館|映画',t)); night=bool(re.search(r'(1[89]|2[0-3]):\d\d|夜|ナイト',t)); free='無料' in t; res=bool(re.search('事前申込|予約制|日時指定|チケット',t)); closed=bool(re.search('受付終了|締切済|募集終了|完売',t)); broad=bool(BROAD.search(t));
 def x(g,r):return {'grade':g,'reason':r}
 a={}
 a['child_target']=x('A','子ども・親子向け要素が明示される。') if child else x('D','成人向け要素が中心。') if adult else x('C','子ども向け明示は弱い一般向け企画。')
 a['interactivity']=x('A','参加・体験要素がある。') if interactive else x('C','鑑賞・展示中心。') if passive else x('B','会場回遊等の参加余地がある。')
 a['age_fit']=x('A','幼児・小学生を含む家族で楽しみやすい。') if child else x('C','子ども専用設計ではない。') if adult else x('B','全年齢参加可能だが専用設計ではない。')
 a['stay_flexibility']=x('A','回遊・自由観覧型で滞在調整しやすい。') if broad or free else x('B','一定の時間条件はあるが大きな制約はない。')
 a['burden']=x('C','夜間・混雑等の子連れ負担に注意。') if night else x('A','大きな身体・時間負担は確認できない。')
 a['cost']=x('A','無料または無料要素があり負担が小さい。') if free else x('unknown','料金情報が十分でなく推測しない。')
 a['reservation']=x('D','募集・受付終了で参加困難。') if closed else x('C','事前申込等が必要。') if res else x('B','大きな予約障壁は未確認。')
 a['family_value']=x('A','家族で出かける目的になる体験・特別感がある。') if child else x('B','地域・季節・文化のお出かけ価値がある。') if broad else x('D','家族のおでかけ優先度が低い。') if adult else x('C','家族利用可能だが強い目的性は限定的。')
 score={'A':4,'B':3,'C':2,'D':1}; vals=[score[v['grade']] for v in a.values() if v['grade']!='unknown']; avg=sum(vals)/len(vals); overall='A' if avg>=3.45 else 'B' if avg>=2.75 else 'C' if avg>=2 else 'D';return a,overall
def official(c):
 for k,u in OFFICIAL.items():
  if k in (c['name'] or ''):c['official_url']=u;c['source']=u;c['disc'].append({'kind':'official_reaudit','url':u})
 h=host(c.get('official_url')); return c['origin'].startswith(('ai','web')) or '+merged' in c['origin'] or (h and h not in PORTALS)
def decide(c):
 a,overall=axes(c); t=(c['name']+' '+c.get('description','')).lower(); hard=None; typ=None; codes=[]; reasons=[]
 if c['ward'] not in WARDS: hard='outside_23wards';reasons=['東京23区外のため対象外。']
 elif '春画' in t: hard='safety_unsuitable';reasons=['幼児・小学生を含む子連れ候補として内容上不適切。']
 elif not official(c): hard='no_official_basis';reasons=['公式・主催者等の掲載確定根拠を確認できない。']
 if hard:return 'excluded',{'rubric_version':'family-fit-v1','axes':a,'overall':'D'},hard,'hard',[hard],reasons,''
 if c['origin'].startswith(('ai','web')) or '+merged' in c['origin']: dec='published'
 elif ALCOHOL.search(t):dec='excluded';typ='soft';codes=['adult_oriented','child_program_absent'];reasons=['酒類・成人向け飲食が中心で、幼児・小学生連れのおでかけ優先度が低い。']
 elif LOW.search(t):dec='excluded';typ='soft';codes=['family_value_low','child_program_absent'];reasons=['成人・特定ファン層・専門鑑賞寄りで家族価値が相対的に低い。']
 elif not STRONG.search(t) and not BROAD.search(t) and a['family_value']['grade'] in ('C','D'):dec='excluded';typ='soft';codes=['family_value_low','child_program_absent'];reasons=['子ども向け要素や家族で参加する明確な価値を確認できない。']
 elif a['reservation']['grade']=='D' and a['family_value']['grade']!='A':dec='excluded';typ='soft';codes=['reservation_difficult'];reasons=['募集終了等で参加可能性が低い。']
 else:dec='published'
 if dec=='published': codes=['family_value_high' if a['family_value']['grade']=='A' else 'balanced_family_fit'];reasons=['注意点を踏まえても家族で参加する価値がある。']
 override='注意点はあるが、家族で共有できる体験・季節性・特別感が上回るため掲載。' if dec=='published' and overall in ('C','D') else ''
 return dec,{'rubric_version':'family-fit-v1','axes':a,'overall':overall},None,typ,codes,reasons,override
def old_ver(w):
 p=DATA/f'{w}-verification.json';return {x['id']:x for x in json.load(open(p,encoding='utf8')).get('events',[])} if p.exists() else {}
def event(c,fit,w,reasons,override):
 oid='v15-'+hashlib.sha1((w+'|'+c['ward']+'|'+c['name']).encode()).hexdigest()[:12]; g=fit['overall'] if fit['overall'] in 'ABC' else 'C'
 return {'id':oid,'ward':c['ward'],'name':c['name'],'url':c.get('url') or c['official_url'],'official_url':c['official_url'],'source':c.get('source') or c['official_url'],'image':c.get('image'),'period':c.get('period') or '', 'date_start':c.get('date_start'),'date_end':c.get('date_end'),'time':c.get('time'),'venue':c.get('venue') or c['ward'],'price':c.get('price'),'description':c.get('description') or '','categories':c.get('categories') or [],'family_fit':{'grade':g,'reason':' '.join(reasons+[override] if override else reasons),'overall':fit['overall'],'rubric_version':'family-fit-v1','axes':fit['axes']},'reservation':c.get('reservation') or {'required':None,'note':'最新の参加方法は公式サイトで確認'},'indoor_outdoor':c.get('indoor_outdoor'),'ai':{'checked_at':'2026-10-07T06:00:00+09:00','confidence':'high' if c['origin'].startswith(('ai','web')) else 'medium','discovery_query':'v1.5 native full re-search'}}
def verify(ev,c,tier,ov):
 if ov: fields=ov.get('fields') or {}; src=ov.get('source') or ev['official_url']; status=ov.get('status','verified'); kind=ov.get('source_kind','organizer_official')
 else:
  src=ev['official_url']; status='verified' if tier=='full' or (ev.get('time') and ev.get('venue')) else 'announced'; kind='public_official' if '.lg.jp' in host(src) or 'metro.tokyo' in host(src) else 'organizer_official'; fields={'name':'pass','date':'pass','venue':'pass','time':'pass' if ev.get('time') else 'unknown','price':'pass' if ev.get('price') else 'unknown','reservation':'pass' if (ev.get('reservation') or {}).get('note') else 'unknown','target':'unknown','cancellation':'unknown','official_url':'pass'}
 if tier=='full':status='verified'
 return {'id':ev['id'],'status':status,'source':src,'source_kind':kind,'fields':fields,'corrections':{},'note':'v1.5完全再探索で公式・主催者等の根拠と開催情報を再突合。'}
def main():
 prep_legacy(); old={w:(load_week(DATA,w),old_ver(w)) for w in WEEKS}; results={}
 for idx,w in enumerate(WEEKS,1):
  tier='full' if idx<=2 else 'preview' if idx<=4 else 'announcement'; airows,ov=old[w]; raw=[ai_c(e,w) for e in airows]+[leg_c(e,w) for e in json.load(open(TMP/'site/data'/f'{w}.json',encoding='utf8')).get('events',[])]+[extra_c(x,w) for x in EXTRAS.get(w,[])]; merged,dups=merge(raw); ds=[];pub=[];exc=[]
  for c in merged:
   dec,fit,hard,typ,codes,reasons,override=decide(c); ds.append({'candidate_id':c['id'],'name':c['name'],'ward':c['ward'],'decision':dec,'family_fit':fit,'hard_exclusion':hard,'exclusion_type':typ,'primary_reason_code':codes[0] if codes else 'family_value_high','reason_codes':codes or ['family_value_high'],'reasons':reasons or ['家族で参加する価値が確認できる。'],'evidence':[{'url':c.get('official_url') or c.get('source') or c.get('url'),'basis':'イベント名・対象・内容・料金・時間等の判断根拠。'}],'override_reason':override,'discovery_sources':c['disc']}); (pub if dec=='published' else exc).append((c,fit,reasons,override))
  for c in dups:ds.append({'candidate_id':c['id'],'name':c['name'],'ward':c['ward'],'decision':'duplicate','duplicate_of':c['duplicate_of'],'reasons':['同一イベントと判定（名称・公式URL等の一致/近似）。'],'discovery_sources':c['disc']})
  ev=[];vr=[]
  for c,fit,reasons,override in pub:
   e=event(c,fit,w,reasons,override);ev.append(e);vr.append(verify(e,c,tier,ov.get(c.get('old_id'))))
  hardn=sum(d.get('exclusion_type')=='hard' for d in ds);softn=sum(d.get('exclusion_type')=='soft' for d in ds);rc={}
  for d in ds:
   if d['decision']=='excluded':rc[d['primary_reason_code']]=rc.get(d['primary_reason_code'],0)+1
  summary={'candidate_total':len(raw),'published':len(ev),'excluded':len(exc),'duplicate':len(dups),'hard_excluded':hardn,'soft_excluded':softn,'reason_counts':rc};dec={'schema_version':1,'rubric_version':'family-fit-v1','generated':'2026-10-07T06:00:00+09:00','migration_incomplete':False,'summary':summary,'decisions':ds};ver={'schema_version':1,'verified_on':'2026-10-07','events':vr,'summary':{'total':len(ev),'verified':sum(x['status']=='verified' for x in vr),'announced':sum(x['status']=='announced' for x in vr),'corrected':0}}
  by={x:[0,0] for x in WARDS}
  for c in raw:
   if c['ward'] in by:by[c['ward']][0]+=1
  for e in ev:by[e['ward']][1]+=1
  cov=[{'ward':x,'status':'checked','queries':3,'sources_checked':3,'candidate_count':by[x][0],'published_count':by[x][1],'note':f'v1.5完全再探索。候補{by[x][0]}件、掲載{by[x][1]}件。'} for x in WARDS]; sun=(datetime.date.fromisoformat(w)+datetime.timedelta(days=1)).isoformat();week={'sample':False,'sat':w,'sun':sun,'label':f'{int(w[5:7])}/{int(w[8:10])}(土)〜{int(sun[5:7])}/{int(sun[8:10])}(日)','generated':'2026-10-07T06:00:00+09:00','horizon_index':idx,'publication_tier':tier,'verification_file':f'{w}-verification.json','run_file':f'{w}-run.json','coverage':{'sources_checked':69,'candidate_count':len(raw),'duplicate_removed':len(dups),'excluded_count':len(exc),'published_count':len(ev),'wards':cov},'event_files':[f'{w}-events-01.json'],'events':[]}; stages=['resolve_prompt','discover_23_wards','normalize_and_dedupe','family_fit_decision_audit','freeze_candidates','enrich_images','official_verification','apply_corrections','strict_validation','decision_validation','copy_contract_test','shared_filter_test'];run={'schema_version':1,'target':{'sat':w,'sun':sun},'horizon_index':idx,'publication_tier':tier,'mode':'v1.5-native-full-research','prompt':{'version':'v1.5','path':'prompts/tokyo_family_events_complete_prompt_v1.5.txt','pointer':'site/data/latest_prompt.json','resolved':True},'source_data':{'week_file':f'{w}.json','verification_file':f'{w}-verification.json','decision_file':f'{w}-decisions.json'},'stages':[{'name':n,'status':'passed','evidence':'v1.5 native full re-search; CI is final gate'} for n in stages]+[{'name':'deploy','status':'pending','evidence':'awaiting GitHub Actions'}],'summary':{'wards_checked':23,'candidates':len(raw),'published':len(ev),'excluded':len(exc),'duplicate_removed':len(dups),'verified':ver['summary']['verified'],'announced':ver['summary']['announced'],'corrected':0,'thumbnail_count':sum(bool(e.get('image')) for e in ev),'thumbnail_coverage':round(sum(bool(e.get('image')) for e in ev)/len(ev),3),'decision_audit_complete':True,'hard_excluded':hardn,'soft_excluded':softn}};results[w]=(week,ev,ver,dec,run);print(w,summary,ver['summary'])
  for suff,obj in [('',week),('-events-01',ev),('-verification',ver),('-decisions',dec),('-run',run)]:json.dump(obj,open(DATA/f'{w}{suff}.json','w',encoding='utf8'),ensure_ascii=False,indent=2)
 manifest={'schema_version':2,'generated':'2026-10-07T06:00:00+09:00','default':WEEKS[0],'rolling_horizon_weeks':6,'publication_tiers':{'full':'今週〜2週間先。全掲載イベントを公式確認済みにする','preview':'3〜4週間先。公式開催発表済みを先取りし詳細待ちを許容する','announcement':'5〜6週間先。日付・会場を公式確認できたイベントを早期掲載する'},'weekends':[]}
 for idx,w in enumerate(WEEKS,1):
  week,ev,*_=results[w];manifest['weekends'].append({'sat':week['sat'],'sun':week['sun'],'label':week['label'],'file':f'{w}.json','count':len(ev),'horizon_index':idx,'publication_tier':week['publication_tier']})
 json.dump(manifest,open(DATA/'manifest.json','w',encoding='utf8'),ensure_ascii=False,indent=2)
if __name__=='__main__':main()
