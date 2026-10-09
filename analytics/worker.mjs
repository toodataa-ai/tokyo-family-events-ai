// Cloudflare Worker + D1: anonymous daily aggregates for Tokyo Family Events.
// No IP, user agent, referer, query string, clipboard contents, or visitor ID is stored.
export const EVENTS = Object.freeze([
  'page_home','page_search','page_copy','nav_search','nav_copy',
  'copy_field','copy_all','session_start'
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

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin');
    const path = new URL(request.url).pathname;

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
      try {
        const body = await request.text();
        if (body.length > 256) return json({error:'too_large'},413,origin);
        const payload = JSON.parse(body);
        if (!payload || typeof payload !== 'object' || !EVENT_SET.has(payload.event) ||
            Object.keys(payload).length !== 1) {
          return json({error:'invalid_event'},400,origin);
        }
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
