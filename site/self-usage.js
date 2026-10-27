/* Optional own-device counter. No ID, cookie, request body or raw activity log sent. */
(() => {
  'use strict';
  const ROOT = '/tokyo-family-events-ai/';
  const ACTIVE_KEY = 'family_events_self_usage_optin_v1';
  const COUNTS_KEY = 'family_events_self_usage_daily_v1';
  const EVENTS = new Set(['page_home','page_search','page_copy','nav_search','nav_copy',
    'copy_field_click','copy_all_click','copy_field','copy_all','session_start']);
  const production = location.origin === 'https://toodataa-ai.github.io' &&
    location.pathname.startsWith(ROOT) && !location.pathname.startsWith(ROOT+'staging/');
  // Preview reads this browser's existing localStorage only; staging never writes.
  const staging = location.origin === 'https://toodataa-ai.github.io' &&
    location.pathname.startsWith(ROOT+'staging/');
  function dayJst() {
    const parts = new Intl.DateTimeFormat('en-US',{timeZone:'Asia/Tokyo',
      year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
    const part = key => parts.find(x=>x.type===key)?.value;
    return [part('year'),part('month'),part('day')].join('-');
  }
  function available(){try {return (production||staging) && !!localStorage;}catch(_){return false;}}
  function enabled(){try {return available() && localStorage.getItem(ACTIVE_KEY)==='yes';}catch(_){return false;}}
  function get() {
    if(!available())return {};
    try {
      const data=JSON.parse(localStorage.getItem(COUNTS_KEY)||'{}');
      if(!data||typeof data!=='object'||Array.isArray(data))return {};
      const out={};
      for(const [day,counts] of Object.entries(data)){
        if(!/^\d{4}-\d{2}-\d{2}$/.test(day)||!counts||typeof counts!=='object')continue;
        const row={};
        for(const [key,n] of Object.entries(counts)){
          if(EVENTS.has(key)&&Number.isSafeInteger(n)&&n>=0)row[key]=n;
        }
        out[day]=row;
      }
      return out;
    } catch(_){return {};}
  }
  function record(event) {
    if(!production||!enabled()||!EVENTS.has(event))return;
    try {
      const data=get(),today=dayJst();
      data[today] ??= {};
      data[today][event]=(data[today][event]||0)+1;
      // Bound storage, preserving newest 365 observed dates.
      for(const day of Object.keys(data).sort().reverse().slice(365))delete data[day];
      localStorage.setItem(COUNTS_KEY,JSON.stringify(data));
    } catch(_){/* privacy mode/storage full; ignore; never interrupt site */}
  }
  function setEnabled(yes) {
    if(!production||!available())return false;
    try{
      if(yes)localStorage.setItem(ACTIVE_KEY,'yes');
      else localStorage.removeItem(ACTIVE_KEY);
      return enabled()===Boolean(yes);
    }catch(_){return false;}
  }
  function clear(){
    if(!production||!available())return;
    try{localStorage.removeItem(COUNTS_KEY);}catch(_){}
  }
  window.SiteSelfUsage=Object.freeze({enabled,get,record,setEnabled,clear,available,dayJst,canWrite:()=>production});
})();
