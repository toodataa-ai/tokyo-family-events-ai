import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

// Catch accidental template-literal HTML corruption before deployment.
// A missing '>' on event-summary-meta makes the star SVGs leave their flex
// container and appear spread across the row in iOS Safari.
for (const file of ['site/search.html','site/copy.html']) {
  const html=readFileSync(file,'utf8');
  const template=/<div class="event-summary-meta"><span class="family-stars \$\{fitClass\(grade\)\}"[^>]*>\$\{(?:copyFamilyStars|familyStars)\(grade\)\}<\/span><span class="event-date">/.test(html);
  assert.ok(template,file+': grouped stars must precede date in a valid flex container');
  assert.doesNotMatch(html,/class="event-summary-meta"\s*<span/,file+': missing close angle bracket');
  assert.doesNotMatch(html,/<div class="event-summary-meta"(?=[^>]*<)/,file+': corrupt flex wrapper');
  assert.match(html,/\$\{(?:changeBadge\(ev,changes\)|changeMark)\}<\/div>/,file+': new/updated badge stays in title, not star wrapper');
}
const css=readFileSync('site/styles.css','utf8');
assert.match(css,/\.event-summary-meta\{justify-content:space-between;width:100%;flex-wrap:nowrap\}/);
assert.match(css,/\.legend-stars,\.family-stars\{display:inline-flex;align-items:center;gap:1px;/);
assert.match(css,/\.event-summary-meta \.event-date\{text-align:right;white-space:nowrap\}/);
console.log('PASS: search/copy stars stay grouped left, date right, badges in title');
