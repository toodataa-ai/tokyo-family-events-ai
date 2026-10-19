# Tamemap Nakano: alternatives to Cloudflare-protected GitHub fetch

Date: 2026-10-20 JST. Read-only investigation, no production or data changes.

## Confirmed

1. GitHub Actions simple urllib requests to Tamemap home, calendar, robots.txt were refused by Cloudflare JavaScript challenge (403, Just a moment...). See prior diagnostic run 39275175781.
2. A supported web search service can retrieve indexed November 2026 calendar content and individual detail pages, including these concrete November entries:
   - 2026-11-22 ママほっとキッチン https://pc.tamemap.net/1311401/event/153058/2026-11-22?locale=ja
   - 2026-11-29 おひさまリトミック https://pc.tamemap.net/1311401/event/142698/2026-11-29?locale=ja
   - calendar https://pc.tamemap.net/1311401/calendar/2026-11?lat=35.7073&level=5000&lng=139.675&locale=ja
   Search-service cache is not proof of current registration availability/last-minute cancellations.
3. Actual GitHub Actions Bing RSS test of nine public site-restricted queries completed. All 9 returned zero URLs on pc.tamemap.net even where unrelated pages populated RSS. Source: https://github.com/toodataa-ai/tokyo-family-events-ai/actions/runs/39276872442 . Cannot present this GitHub RSS as a reliable substitute.
4. Accessible independent primary / community sources:
   - Nakano City November 2026 calendar: https://www.city.tokyo-nakano.lg.jp/event/calendar/list_calendar202611.html
   - Nakano City child/family calendar: https://www.city.tokyo-nakano.lg.jp/event/kosodate/calendar/list_calendar.html
   - Nakano Community Welfare Council events: https://nakanoshakyo.com/nakanoinfo/event/index.php
   - Nakano child meal programs: https://kodomohot.jimdofree.com/%E3%81%93%E3%81%A9%E3%82%82%E9%A3%9F%E5%A0%82/
   - Mamahotto third-party organizer regional center info: https://sites.google.com/view/nakanomomozono2011/home
5. Nakano City official calendar has no entry on Nov 22 in its Nov calendar, whereas Tamemap and child-meal resource list Mamahotto kitchen. Therefore, Nakano city calendar is supplementary, not an exact or comprehensive mirror of Tamemap.

## Recommended operational fallback

A. Keep tamemap_nakano registered and enabled. Do not fake successful tamemap HTTP checks or treat 403 as zero events.
B. In manual holiday-after research use indexed Tamemap candidate pages strictly as 'unverified discovery leads' and match each to organizer/ward primary sources. Do not imply automatically full-coverage.
C. Add/maintain accessible Nakano official calendar and social welfare council / verified organizer sources as independent source groups only through authorized source-policy release path (main -> staging -> user approval -> production).
D. For fully automated complete Tamemap coverage, ask Nakano City's program owner koeki@city.tokyo-nakano.lg.jp or Tamemap info@tamemap.net about official export/API or approved machine-to-machine access, not Cloudflare challenge evasion.
E. Preserve existing event records on any missing source; strict data publication remains blocked on unfulfilled protected-source evidence unless reviewed policy formally changes.

## Status

Alternative human-assisted discovery and organizer-source reconciliation: feasible and evidenced.
GitHub Actions fully automatic Tamemap coverage via currently tested Bing RSS: not feasible / zero Tamemap matches.
Authenticated data export/API: not verified available.
Data-staging, data-production, production, app Version: unchanged.
