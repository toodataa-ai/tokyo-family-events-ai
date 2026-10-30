// Cloudflare Worker + D1: anonymous daily aggregates for Tokyo Family Events.
// No IP, user agent, referer, query string, clipboard contents, or visitor ID is stored.
export const EVENTS = Object.freeze([
  'page_home','page_search','page_copy','nav_search','nav_copy',
  'copy_field_click','copy_all_click','copy_field','copy_all','session_start'
]);
const ORIGIN = 'https://toodataa-ai.github.io';
const EVENT_SET = new Set(EVENTS);

function headers(origin) {
  const out = {
    'Content-Type':'application/json; charset=utf-8',
    'Cache-Control':'no-store',
    'Vary':'Origin',
    'X-Content-Type-Options':'nosniff'
  };
  if (origin === ORIGIN) out['Access-Control-Allow-Origin'] = ORIGIN;
  return out;
}

function json(data, status, origin) {
  return new Response(JSON.stringify(data), {status, headers:headers(origin)});
}

function todayJst(now) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'
  }).formatToParts(now);
  const get = type => parts.find(part => part.type === type)?.value;
  return get('year') + '-' + get('month') + '-' + get('day');
}

// Keiba-only namespace. Never write to the existing event_counts table.
// The token may be Worker-scoped without D1 admin rights, so the bound Worker
// creates its OWN isolated table idempotently on first keiba API invocation.
export const KEIBA_EVENTS=Object.freeze([
  'page_home','page_this_week','page_results','page_schedule',
  'page_methodology','page_research','page_other','session_start'
]);
const KEIBA_EVENT_SET=new Set(KEIBA_EVENTS);
const KEIBA_TABLE='keiba_site_event_counts';
let keibaTableReady=false;
async function ensureKeibaTable(env){
  if(keibaTableReady)return;
  // Literal SQL only: user requests cannot choose a schema/table/column.
  await env.DB.prepare(
    'CREATE TABLE IF NOT EXISTS keiba_site_event_counts ('+
    'day TEXT NOT NULL, event TEXT NOT NULL CHECK (event IN ('+
    "'page_home','page_this_week','page_results','page_schedule',"+
    "'page_methodology','page_research','page_other','session_start'"+
    ')), count INTEGER NOT NULL DEFAULT 0 CHECK (count >= 0),'+
    'PRIMARY KEY (day,event))'
  ).run();
  keibaTableReady=true;
}
async function keibaApi(request,env,origin,url){
  const path=url.pathname;
  if(request.method==='OPTIONS'&&path==='/keiba/collect'){
    if(origin!==ORIGIN)return json({error:'forbidden'},403,origin);
    return new Response(null,{status:204,headers:{
      'Access-Control-Allow-Origin':ORIGIN,
      'Access-Control-Allow-Methods':'POST, OPTIONS',
      'Access-Control-Allow-Headers':'Content-Type',
      'Access-Control-Max-Age':'600','Vary':'Origin'
    }});
  }
  if(!env.DB)return json({error:'storage_unavailable'},503,origin);
  if(path==='/keiba/collect'&&request.method==='POST'){
    if(origin!==ORIGIN)return json({error:'forbidden'},403,origin);
    if(!['text/plain','application/json'].includes(
       (request.headers.get('Content-Type')||'').split(';')[0].trim()))
      return json({error:'unsupported_media_type'},415,origin);
    if(Number(request.headers.get('Content-Length')||0)>256)
      return json({error:'too_large'},413,origin);
    let payload;
    try{const raw=await request.text();if(raw.length>256)throw Error('large');payload=JSON.parse(raw);}
    catch(_){return json({error:'invalid_event'},400,origin);}
    if(!payload||typeof payload!=='object'||Array.isArray(payload)||
       Object.keys(payload).length!==2||payload.site!=='keiba-notes'||
       !KEIBA_EVENT_SET.has(payload.event))return json({error:'invalid_event'},400,origin);
    try{
      await ensureKeibaTable(env);
      await env.DB.prepare(
        'INSERT INTO keiba_site_event_counts (day,event,count) VALUES (?1,?2,1) '+
        'ON CONFLICT(day,event) DO UPDATE SET count=count+1'
      ).bind(todayJst(new Date()),payload.event).run();
      return json({ok:true,site:'keiba-notes'},200,origin);
    }catch(_){return json({error:'keiba_collection_failed'},503,origin);}
  }
  if(path==='/keiba/stats'&&request.method==='GET'){
    if(url.search)return json({error:'unexpected_query'},400,origin);
    try{
      await ensureKeibaTable(env);
      const day=todayJst(new Date());
      const records=await env.DB.prepare(
        'SELECT event,SUM(count) AS total,'+
        'SUM(CASE WHEN day=?1 THEN count ELSE 0 END) AS today '+
        'FROM keiba_site_event_counts GROUP BY event'
      ).bind(day).all();
      const totals=Object.fromEntries(KEIBA_EVENTS.map(e=>[e,0]));
      const today=Object.fromEntries(KEIBA_EVENTS.map(e=>[e,0]));
      for(const record of records.results||[]){
        if(!KEIBA_EVENT_SET.has(record.event))continue;
        const a=Number(record.total),b=Number(record.today);
        if(!Number.isSafeInteger(a)||a<0||!Number.isSafeInteger(b)||b<0)
          throw Error('Invalid counter');
        totals[record.event]=a;today[record.event]=b;
      }
      return json({schema_version:1,site:'keiba-notes',day_jst:day,totals,today},200,origin);
    }catch(_){return json({error:'keiba_stats_unavailable'},503,origin);}
  }
  if(path==='/keiba/history'&&request.method==='GET'){
    const rawDays=url.searchParams.get('days')||'30';
    if(url.searchParams.size>(url.searchParams.has('days')?1:0)||
       !['7','30','90','365'].includes(rawDays))
      return json({error:'invalid_history_range'},400,origin);
    try{
      await ensureKeibaTable(env);
      const end=todayJst(new Date());
      const startD=new Date(end+'T00:00:00Z');
      startD.setUTCDate(startD.getUTCDate()-Number(rawDays)+1);
      const start=startD.toISOString().slice(0,10);
      const records=await env.DB.prepare(
        'SELECT day,event,count FROM keiba_site_event_counts '+
        'WHERE day>=?1 AND day<=?2 ORDER BY day DESC,event'
      ).bind(start,end).all();
      const byDay=new Map();
      for(const record of records.results||[]){
        if(!/^\d{4}-\d{2}-\d{2}$/.test(record.day)||record.day<start||record.day>end||
           !KEIBA_EVENT_SET.has(record.event)||!Number.isSafeInteger(Number(record.count))||
           Number(record.count)<0)continue;
        if(!byDay.has(record.day))
          byDay.set(record.day,Object.fromEntries(KEIBA_EVENTS.map(e=>[e,0])));
        byDay.get(record.day)[record.event]+=Number(record.count);
      }
      const rows=[...byDay].sort((a,b)=>b[0].localeCompare(a[0]))
        .map(([day,counts])=>({day,counts}));
      return json({schema_version:1,site:'keiba-notes',day_jst:end,days:Number(rawDays),
        recorded_days:rows.length,rows,notes:'実測した日のみ表示。未計測日は0件扱いしない。'},200,origin);
    }catch(_){return json({error:'keiba_history_unavailable'},503,origin);}
  }
  return json({error:'not_found'},404,origin);
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin');
    const path = new URL(request.url).pathname;
    // Separate /keiba namespace. All original event-site routes remain untouched.
    if (path.startsWith('/keiba/')) return keibaApi(request,env,origin,new URL(request.url));

    if (request.method === 'OPTIONS' && path === '/collect') {
      if (origin !== ORIGIN) return json({error:'forbidden'},403,origin);
      return new Response(null, {
        status:204,
        headers:{
          'Access-Control-Allow-Origin':ORIGIN,
          'Access-Control-Allow-Methods':'POST, OPTIONS',
          'Access-Control-Allow-Headers':'Content-Type',
          'Access-Control-Max-Age':'600',
          'Vary':'Origin'
        }
      });
    }

    if (!env.DB) return json({error:'storage_unavailable'},503,origin);

    if (path === '/collect' && request.method === 'POST') {
      if (origin !== ORIGIN) return json({error:'forbidden'},403,origin);
      if (!['text/plain','application/json'].includes((request.headers.get('Content-Type') || '').split(';')[0].trim())) {
        return json({error:'unsupported_media_type'},415,origin);
      }
      if (Number(request.headers.get('Content-Length') || 0) > 256) return json({error:'too_large'},413,origin);
      let payload;
      try {
        const body = await request.text();
        if (body.length > 256) return json({error:'too_large'},413,origin);
        payload = JSON.parse(body);
      } catch (_) {
        return json({error:'invalid_event'},400,origin);
      }
      if (!payload || typeof payload !== 'object' || !EVENT_SET.has(payload.event) ||
          Object.keys(payload).length !== 1) {
        return json({error:'invalid_event'},400,origin);
      }
      try {
        const date = todayJst(new Date());
        // Single atomic upsert: concurrent requests cannot overwrite each other.
        await env.DB.prepare(
          'INSERT INTO event_counts (day, event, count) VALUES (?1, ?2, 1) ' +
          'ON CONFLICT(day, event) DO UPDATE SET count = count + 1'
        ).bind(date,payload.event).run();
        return json({ok:true},200,origin);
      } catch (_) {
        return json({error:'collection_failed'},503,origin);
      }
    }

    if (path === '/history' && request.method === 'GET') {
      const url = new URL(request.url);
      const rawDays = url.searchParams.get('days') || '30';
      // Strictly bounded public aggregate read; no visitor identity.
      if (url.searchParams.size > (url.searchParams.has('days') ? 1 : 0) ||
          !['7','30','90','365'].includes(rawDays)) {
        return json({error:'invalid_history_range'},400,origin);
      }
      try {
        const end = todayJst(new Date());
        const startDate = new Date(end + 'T00:00:00Z');
        startDate.setUTCDate(startDate.getUTCDate() - Number(rawDays) + 1);
        const start = startDate.toISOString().slice(0,10);
        const result = await env.DB.prepare(
          'SELECT day, event, count FROM event_counts ' +
          'WHERE day >= ?1 AND day <= ?2 ORDER BY day DESC, event'
        ).bind(start,end).all();
        // Only dates with actual recorded rows are returned. Never invent
        // prior history or imply that missing days have verified zero usage.
        const byDay = new Map();
        for (const row of result.results || []) {
          if (!/^\d{4}-\d{2}-\d{2}$/.test(row.day) ||
              row.day < start || row.day > end || !EVENT_SET.has(row.event) ||
              !Number.isSafeInteger(Number(row.count)) || Number(row.count) < 0) {
            continue;
          }
          if (!byDay.has(row.day)) {
            byDay.set(row.day,Object.fromEntries(EVENTS.map(event => [event,0])));
          }
          byDay.get(row.day)[row.event] += Number(row.count);
        }
        const rows = [...byDay.entries()].sort((a,b) => b[0].localeCompare(a[0]))
          .map(([day,counts]) => ({day,counts}));
        return json({schema_version:1,day_jst:end,days:Number(rawDays),
          start_day_jst:start,end_day_jst:end,recorded_days:rows.length,
          rows,notes:'記録がある日だけ表示。過去の未計測日は0件とみなさない。個人識別なし。'},
          200,origin);
      } catch (_) {
        return json({error:'history_unavailable'},503,origin);
      }
    }

    if (path === '/stats' && request.method === 'GET') {
      try {
        const date = todayJst(new Date());
        const query = 'SELECT event, SUM(count) AS total, ' +
          'SUM(CASE WHEN day = ?1 THEN count ELSE 0 END) AS today ' +
          'FROM event_counts GROUP BY event';
        const response = await env.DB.prepare(query).bind(date).all();
        const totals = Object.fromEntries(EVENTS.map(event => [event,0]));
        const today = Object.fromEntries(EVENTS.map(event => [event,0]));
        for (const row of response.results || []) {
          if (!EVENT_SET.has(row.event)) continue;
          totals[row.event] = Number(row.total) || 0;
          today[row.event] = Number(row.today) || 0;
        }
        return json({schema_version:1,day_jst:date,totals,today},200,origin);
      } catch (_) {
        return json({error:'stats_unavailable'},503,origin);
      }
    }
    return json({error:'not_found'},404,origin);
  }
};
