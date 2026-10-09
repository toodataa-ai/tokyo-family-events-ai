/* Anonymous aggregate usage metrics. Disabled until a metrics endpoint is configured.
 * Never record staging, query strings, event names, personal data or identifiers.
 */
(() => {
  'use strict';
  const ROOT = '/tokyo-family-events-ai/';
  const PAGES = Object.freeze({
    [ROOT]: 'page_home',
    [ROOT + 'index.html']: 'page_home',
    [ROOT + 'search.html']: 'page_search',
    [ROOT + 'copy.html']: 'page_copy'
  });
  const pageEvent = PAGES[location.pathname] || null;
  const production = location.origin === 'https://toodataa-ai.github.io' && !!pageEvent;
  const summary = document.getElementById('siteUsageValues');
  const pending = [];
  let endpoint = '';
  let configured = false;
  let initialized = false;

  function setStatus(value) {
    if (summary) summary.textContent = value;
  }

  function dispatch(event) {
    if (!configured || !production) return;
    const body = JSON.stringify({event});
    try {
      if (navigator.sendBeacon && navigator.sendBeacon(endpoint + '/collect', new Blob([body], {type:'text/plain'}))) return;
    } catch (_) { /* use fetch fallback */ }
    fetch(endpoint + '/collect', {
      method:'POST', mode:'cors', credentials:'omit',
      headers:{'Content-Type':'text/plain'}, body, keepalive:true
    }).catch(() => {});
  }

  function track(event) {
    if (!Object.values(PAGES).includes(event) &&
        !['nav_search','nav_copy','copy_field_click','copy_all_click','copy_field','copy_all','session_start'].includes(event)) return;
    if (!production) return;
    if (!initialized) {
      if (pending.length < 25) pending.push(event);
      return;
    }
    dispatch(event);
  }
  window.SiteMetrics = Object.freeze({track});

  function formatCount(value) {
    const count = Number(value);
    return Number.isSafeInteger(count) && count >= 0 ? count.toLocaleString('ja-JP') : '―';
  }

  async function showTotals() {
    if (!summary) return;
    try {
      const response = await fetch(endpoint + '/stats', {cache:'no-store', mode:'cors', credentials:'omit'});
      if (!response.ok) throw new Error('stats unavailable');
      const data = await response.json();
      if (data.schema_version !== 1 || !data.totals) throw new Error('invalid metrics schema');
      const n = name => {
        const value = data.totals[name] === undefined ? 0 : data.totals[name];
        if (!Number.isSafeInteger(value) || value < 0) throw new Error('invalid count');
        return value;
      };
      const views = n('page_home') + n('page_search') + n('page_copy');
      const copy = n('copy_field') + n('copy_all');
      const attempts = n('copy_field_click') + n('copy_all_click');
      summary.textContent = '表示 ' + formatCount(views) +
        ' ／ イベントへ ' + formatCount(n('nav_search')) +
        ' ／ コピペへ ' + formatCount(n('nav_copy')) +
        ' ／ コピー押下 ' + formatCount(attempts) +
        '（個別 ' + formatCount(n('copy_field_click')) + '・一括 ' + formatCount(n('copy_all_click')) + '）' +
        ' ／ 成功 ' + formatCount(copy) +
        '（個別 ' + formatCount(n('copy_field')) + '・一括 ' + formatCount(n('copy_all')) + '）' +
        ' ／ セッション目安 ' + formatCount(n('session_start'));
    } catch (_) {
      setStatus('集計データを取得できません');
    }
  }

  function trackSession() {
    try {
      const date = new Date().toLocaleDateString('en-CA', {timeZone:'Asia/Tokyo'});
      const key = 'family_events_metrics_session_' + date;
      if (sessionStorage.getItem(key) !== '1') {
        sessionStorage.setItem(key, '1');
        track('session_start');
      }
    } catch (_) { /* blocked storage: skip estimated session count */ }
  }

  document.addEventListener('click', event => {
    const el = event.target.closest('a[href], button#copyBtn');
    if (!el || event.defaultPrevented) return;
    if (el.matches('button#copyBtn')) {
      track('nav_copy');
      return;
    }
    const href = el.getAttribute('href');
    if (!href || href.startsWith('#')) return;
    try {
      const target = new URL(href, document.baseURI);
      if (target.origin !== location.origin) return;
      if (target.pathname === ROOT + 'search.html') track('nav_search');
      if (target.pathname === ROOT + 'copy.html') track('nav_copy');
    } catch (_) { /* invalid href */ }
  }, {capture:true});

  (async () => {
    if (!production) {
      setStatus('ステージング・開発環境は集計対象外');
      initialized = true;
      return;
    }
    try {
      const response = await fetch(new URL('metrics-config.json', document.baseURI), {cache:'no-store'});
      if (!response.ok) throw new Error('metrics config unavailable');
      const config = await response.json();
      if (config.enabled !== true || typeof config.endpoint !== 'string') {
        setStatus('計測準備中');
        return;
      }
      const url = new URL(config.endpoint);
      if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash) {
        throw new Error('invalid endpoint');
      }
      endpoint = url.href.replace(/\/+$/, '');
      configured = true;
      trackSession();
      dispatch(pageEvent);
      if (summary) await showTotals();
    } catch (_) {
      setStatus('計測の設定を確認してください');
    } finally {
      initialized = true;
      if (configured) pending.splice(0).forEach(dispatch);
      else pending.length = 0;
    }
  })();
})();
