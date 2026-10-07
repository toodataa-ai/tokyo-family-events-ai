import assert from 'node:assert/strict';
import fs from 'node:fs';

const latest=JSON.parse(fs.readFileSync('site/data/latest_prompt.json','utf8'));
const prompt=fs.readFileSync(latest.path,'utf8');
const workflow=fs.readFileSync('.github/workflows/deploy.yml','utf8');
const app=fs.readFileSync('site/app.js','utf8');

assert.equal(latest.version,'v1.13');
assert.match(prompt,/非退行・証拠拘束ガード/);
assert.match(prompt,/field_changes/);
assert.match(prompt,/前年ページ/);
assert.match(prompt,/長期開催イベント/);
assert.match(prompt,/(?:image|画像).*根拠/);
assert.ok(fs.existsSync('tools/validate_non_regression.py'));
assert.match(workflow,/fetch-depth:\s*2/);
assert.match(workflow,/Validate non-regression against previous published data/);
assert.match(app,/確認済み/);
console.log('non-regression + hallucination policy: OK');
