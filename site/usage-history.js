/* Daily anonymous usage chart; optional counts stay on this browser. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const fmt = n => Number.isSafeInteger(n)&&n>=0?n.toLocaleString('ja-JP'):'—';
  const safe = n => Number.isSafeInteger(n)&&n>=0?n:0;
  const sum = (d,keys) => keys.reduce((a,k)=>a+safe(d?.[k]),0);
  const pv=['page_home','page_search','page_copy'],nav=['nav_search','nav_copy'],
        copies=['copy_field','copy_all'];
  const self=()=>window.SiteSelfUsage;
  function set(id,value){$(id).textContent=value;}
  function validCounts(c){return c&&typeof c==='object'&&
    pv.concat(nav,copies,['session_start']).every(k=>Number.isSafeInteger(c[k])&&c[k]>=0);}
  function td(tr,v){const x=document.createElement('td');x.textContent=v;tr.appendChild(x);}
  // Own-browser totals are read locally for display only, never sent in a request.
  let latestRows=null;
  function renderChart(rows){
    const chart=$('usageHistoryChart'),api=self();
    const optedIn=Boolean(api?.available()&&api.enabled());
    const ownDays=optedIn?api.get():{};
    $('usageHistoryOwnLegend').hidden=!optedIn;
    $('usageHistoryOwnNote').hidden=!optedIn;
    chart.replaceChildren();
    const bars=rows.slice().reverse().slice(-30);
    const max=Math.max(1,...bars.map(row=>Math.max(
      sum(row.counts,pv),optedIn?sum(ownDays[row.day],pv):0
    )));
    for(const row of bars){
      const count=sum(row.counts,pv),hasOwn=optedIn&&
        Object.prototype.hasOwnProperty.call(ownDays,row.day);
      const ownCount=hasOwn?sum(ownDays[row.day],pv):null;
      const block=document.createElement('div');block.className='usage-history-visual-row';
      block.title=row.day+' 全体 '+fmt(count)+'回'+
        (hasOwn?' ／ このブラウザ '+fmt(ownCount)+'回':'');
      const date=document.createElement('span');date.textContent=row.day.slice(5);
      const rail=document.createElement('div');rail.className='usage-history-visual-rail';
      const bar=document.createElement('div');bar.className='usage-history-visual-bar';
      bar.style.width=(count/max*100).toFixed(1)+'%';
      bar.title=row.day+' 全体 '+fmt(count)+'回';
      rail.appendChild(bar);
      if(hasOwn){
        const ownBar=document.createElement('div');
        ownBar.className='usage-history-visual-own-bar';
        ownBar.style.width=(ownCount/max*100).toFixed(1)+'%';
        ownBar.title=row.day+' このブラウザ '+fmt(ownCount)+'回';
        rail.appendChild(ownBar);
      }
      block.append(date,rail);
      const n=document.createElement('span');n.textContent=fmt(count);block.appendChild(n);
      chart.appendChild(block);
    }
  }
  function showHistory(data,days){
    if(data?.schema_version!==1||data.days!==Number(days)||!Array.isArray(data.rows)||
      data.rows.length>Number(days)||!/^\d{4}-\d\d-\d\d$/.test(data.day_jst||''))
      throw Error('invalid history schema');
    const tbody=$('usageHistoryRows');
    tbody.replaceChildren();
    const seen=new Set();
    for(const row of data.rows){
      if(!/^\d{4}-\d\d-\d\d$/.test(row.day||'')||seen.has(row.day)||
          row.day>data.day_jst||!validCounts(row.counts))throw Error('invalid daily row');
      seen.add(row.day);
      const tr=document.createElement('tr');
      for(const v of [row.day,fmt(sum(row.counts,pv)),fmt(sum(row.counts,nav)),
                       fmt(sum(row.counts,copies)),fmt(row.counts.session_start)])td(tr,v);
      tbody.appendChild(tr);
    }
    if(!data.rows.length){const tr=document.createElement('tr');const cell=document.createElement('td');
      cell.colSpan=5;cell.textContent='この期間に記録された日付はありません（未計測を0とは扱いません）。';
      tr.appendChild(cell);tbody.appendChild(tr);}
    latestRows=data.rows;
    renderChart(latestRows);
    set('usageHistoryStatus','過去'+days+'日間のうち記録がある日：'+data.rows.length+
      '日。記録のない日を0件とはみなしません。');
  }
  function showSelf(){
    const api=self();
    if(!api?.available()){
      set('usageSelfStatus','この環境では端末内の記録を利用できません。');
      for(const id of ['usageSelfEnable','usageSelfDisable','usageSelfClear'])$(id).disabled=true;
      set('usageSelfToday','この端末の利用：記録なし');
      set('usageSelfAll','保存済みの利用：記録なし');
      if(latestRows)renderChart(latestRows);
      return;
    }
    const on=api.enabled();
    const writable=api.canWrite?.()??true;
    set('usageSelfStatus',(on?'この端末だけの利用メモ：オン':'この端末だけの利用メモ：オフ')+
      (writable?'':'（ステージングは読み取り専用。本番サイトで切り替えできます）'));
    $('usageSelfEnable').disabled=!writable||on;
    $('usageSelfDisable').disabled=!writable||!on;
    $('usageSelfClear').disabled=!writable;
    const all=api.get(),today=all[api.dayJst()]||{},days=Object.values(all);
    const total=k=>days.reduce((n,row)=>n+safe(row[k]),0);
    set('usageSelfToday','今日のこの端末：表示 '+fmt(sum(today,pv))+
      '回 ／ コピー成功 '+fmt(sum(today,copies))+'回');
    set('usageSelfAll','この端末の保存分：表示 '+fmt(pv.reduce((n,k)=>n+total(k),0))+
      '回 ／ コピー成功 '+fmt(copies.reduce((n,k)=>n+total(k),0))+'回');
    if(latestRows)renderChart(latestRows);
  }
  async function init(){
    showSelf();
    $('usageSelfEnable').addEventListener('click',()=>{self()?.setEnabled(true);showSelf();});
    $('usageSelfDisable').addEventListener('click',()=>{self()?.setEnabled(false);showSelf();});
    $('usageSelfClear').addEventListener('click',()=>{
      if(window.confirm('このブラウザの利用メモを消しますか？')){self()?.clear();showSelf();}
    });
    let endpoint;
    try {
      const configResponse=await fetch('metrics-config.json',{cache:'no-store'});
      if(!configResponse.ok)throw Error('config unavailable');
      const cfg=await configResponse.json();
      if(cfg.enabled!==true||typeof cfg.endpoint!=='string')throw Error('disabled');
      const u=new URL(cfg.endpoint);
      if(u.protocol!=='https:'||u.username||u.password||u.search||u.hash)throw Error('invalid endpoint');
      endpoint=u.href.replace(/\/+$/,'');
    }catch(_){set('usageHistoryDate','集計接続先を確認できません。');
      set('usageHistoryStatus','利用状況は確認できません（0件ではありません）。');return;}
    try {
      const res=await fetch(endpoint+'/stats',{cache:'no-store',mode:'cors',credentials:'omit'});
      if(!res.ok)throw Error('stats unavailable');
      const d=await res.json();
      if(d.schema_version!==1||!validCounts(d.today)||!validCounts(d.totals)||
        !/^\d{4}-\d\d-\d\d$/.test(d.day_jst||''))throw Error('invalid stats');
      set('usageHistoryDate','今日：'+d.day_jst+'（日本時間）');
      for(const [id,value] of [['usageHistoryTodayViews',sum(d.today,pv)],
        ['usageHistoryAllViews',sum(d.totals,pv)],
        ['usageHistoryTodaySessions',d.today.session_start],
        ['usageHistoryTodayCopy',sum(d.today,copies)],
        ['usageHistoryAllCopy',sum(d.totals,copies)],
        ['usageHistoryTodayNav',sum(d.today,nav)]])set(id,fmt(value));
    }catch(_){set('usageHistoryDate','今日・累計の利用状況を取得できません。');}
    async function refresh(){
      const days=$('usageHistoryRange').value;
      set('usageHistoryStatus','日別履歴を確認中です。');
      try{
        const res=await fetch(endpoint+'/history?days='+encodeURIComponent(days),
          {cache:'no-store',mode:'cors',credentials:'omit'});
        if(!res.ok)throw Error('history API unavailable');
        showHistory(await res.json(),days);
      }catch(_){
        set('usageHistoryStatus','日別履歴APIが未公開、または利用できません。今日と累計は引き続き表示できます。');
        latestRows=null;
        $('usageHistoryRows').replaceChildren();$('usageHistoryChart').replaceChildren();
        $('usageHistoryOwnLegend').hidden=true;$('usageHistoryOwnNote').hidden=true;
        const tr=document.createElement('tr'),cell=document.createElement('td');
        cell.colSpan=5;cell.textContent='日別履歴の接続待ちです。';tr.appendChild(cell);
        $('usageHistoryRows').appendChild(tr);
      }
    }
    $('usageHistoryRange').addEventListener('change',refresh);
    refresh();
  }
  init();
})();
