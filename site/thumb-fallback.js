/* Fallback thumbnail for events without a usable photo: category icon on a soft gradient + small ward label. */
(function(root){
  const CATS=[
    ['craft','🎨','#f6c7a6','#f08c6b',/工作|ものづくり|クラフト|ワークショップ|製作|作ろう|つくろう|作り|ぬりえ|塗り絵|折り紙|スタンプ|ペーパー|バッジ|おえかき|絵/],
    ['science','🔬','#b9dcf2','#5aa6d6',/科学|実験|理科|サイエンス|プラネタリウム|天文|星|宇宙|ロボット|プログラミング|プラネ/],
    ['book','📚','#f3dca2','#d9a93c',/読み聞かせ|おはなし|お話|絵本|図書|本の|紙芝居|ブック|読書|よみきかせ|かみしばい/],
    ['music','🎵','#e3c9ef','#a56fc4',/音楽|コンサート|演奏|ライブ|リズム|歌|うた|楽器|ミュージカル|合唱|ギター|オーケストラ|ピアノ|ダンス/],
    ['sport','⚽','#c4e8c6','#5eb36a',/スポーツ|運動|体操|サッカー|野球|ヨガ|スケボー|スケート|ランニング|ウォーク|パラ|体験教室|体力|ボッチャ|カヌー/],
    ['nature','🌳','#cfe8b8','#7bb560',/公園|自然|生き物|観察|いきもの|昆虫|ホタル|ほたる|どんぐり|植物|森|水族館|動物園|ビーチ|海|川|探鳥|バードウォッチ|探検|ガーデン/],
    ['vehicle','🚃','#cbd9ee','#6c8fc9',/電車|トレイン|プラレール|鉄道|乗り物|のりもの|バス|飛行機|ヒコーキ|新幹線|車両|ミニカー/],
    ['festival','🎪','#f7c9cf','#e9808f',/祭|フェス|まつり|マルシェ|イベント|縁日|クリスマス|サンタ|もちつき|餅つき|ハロウィン|フェスタ|フェスティバル/],
    ['play','🧸','#fde0b5','#f0a850',/あそび|遊び|プレイ|親子|ひろば|広場|おもちゃ|ベビー|赤ちゃん|ママ|パパ|児童館|キッズ|子育て|ふれあい|体験/],
    ['museum','🏛️','#d9d4ee','#8a7fc4',/博物館|美術館|展|ミュージアム|アート|着物|歴史|文化|伝統|資料館|郷土/]
  ];
  const DEFAULT=['default','🎈','#cfe0ee','#7fa3c4'];
  function pick(ev){
    const t=[ev&&ev.name,ev&&ev.title,ev&&ev.description,ev&&ev.venue].filter(Boolean).join(' ');
    for(const c of CATS) if(c[4].test(t)) return c;
    return DEFAULT;
  }
  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
  function html(ev){
    const c=pick(ev),ward=String((ev&&ev.ward)||'').replace(/区$/,'');
    return '<div class="thumb ph ph-cat event-list-thumb" style="background:linear-gradient(135deg,'+c[2]+','+c[3]+')" data-cat="'+c[0]+'"><span class="ph-icon" aria-hidden="true">'+c[1]+'</span>'+(ward?'<span class="ph-ward">'+esc(ward)+'</span>':'')+'</div>';
  }
  root.ThumbFallback={html:html,pick:pick};
})(typeof window!=='undefined'?window:globalThis);
