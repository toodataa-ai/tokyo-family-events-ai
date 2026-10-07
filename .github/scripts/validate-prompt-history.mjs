import fs from 'node:fs';
import path from 'node:path';

const root=process.cwd();
const readJson=(p)=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const latestPath='site/data/latest_prompt.json';
const historyPath='site/data/prompt_history.json';
const latest=readJson(latestPath);
const history=readJson(historyPath);
const entries=Array.isArray(history.entries)?history.entries:[];
const errors=[];

if(!latest.version) errors.push(`${latestPath}: version is required`);
if(!latest.path) errors.push(`${latestPath}: path is required`);
if(!entries.length) errors.push(`${historyPath}: entries must not be empty`);

const seen=new Set();
const byVersion=new Map();
for(const entry of entries){
  const key=entry.version||'(missing version)';
  if(seen.has(key)) errors.push(`${historyPath}: duplicate version ${key}`);
  seen.add(key); byVersion.set(entry.version,entry);
  for(const field of ['version','date','path','summary','changes','reason']){
    if(!(field in entry)) errors.push(`${historyPath}: ${key} is missing ${field}`);
  }
  if(!Array.isArray(entry.changes)) errors.push(`${historyPath}: ${key}.changes must be an array`);
  else if(entry.source!=='baseline'&&entry.changes.length===0) errors.push(`${historyPath}: ${key}.changes must describe at least one improvement`);
  if(!entry.summary) errors.push(`${historyPath}: ${key}.summary must not be empty`);
  if(!entry.reason) errors.push(`${historyPath}: ${key}.reason must not be empty`);
  if(entry.path&&!fs.existsSync(path.join(root,entry.path))) errors.push(`${historyPath}: ${key} points to missing file ${entry.path}`);
}
const current=byVersion.get(latest.version);
if(!current) errors.push(`${historyPath}: latest version ${latest.version} has no history entry`);
else if(current.path!==latest.path) errors.push(`prompt history path mismatch for ${latest.version}: ${current.path} != ${latest.path}`);
if(latest.path&&!fs.existsSync(path.join(root,latest.path))) errors.push(`${latestPath} points to missing file ${latest.path}`);
for(const required of ['site/data/family_fit_rubric.json','site/data/family_fit_regression_cases.json','site/data/discovery_sources.json']){
  if(!fs.existsSync(path.join(root,required))) errors.push(`${required}: required by ${latest.version}`);
}

const manifest=readJson('site/data/manifest.json');
let historicalRuns=0;
for(const weekend of (manifest.weekends||[])){
  const weekFile=weekend.file;
  if(!weekFile) continue;
  const week=readJson(path.join('site/data',weekFile));
  if(week.sample===true) continue;
  if(!week.run_file){errors.push(`${weekFile}: production weekend requires run_file`);continue;}
  const runPath=path.join('site/data',week.run_file);
  if(!fs.existsSync(path.join(root,runPath))){errors.push(`${weekFile}: missing run manifest ${week.run_file}`);continue;}
  const run=readJson(runPath); const p=run.prompt||{};
  const recorded=byVersion.get(p.version);
  if(!recorded) errors.push(`${week.run_file}: prompt.version ${p.version} is not in prompt history`);
  else if(p.path!==recorded.path) errors.push(`${week.run_file}: prompt.path ${p.path} != historical path ${recorded.path}`);
  if(p.pointer!==latestPath) errors.push(`${week.run_file}: prompt.pointer must be ${latestPath}`);
  if(p.resolved!==true) errors.push(`${week.run_file}: prompt.resolved must be true`);
  if(p.version!==latest.version) historicalRuns++;
  if(['v1.5','v1.6','v1.7','v1.8','v1.9','v1.10'].includes(p.version)){
    const decisionFile=(run.source_data||{}).decision_file;
    if(!decisionFile) errors.push(`${week.run_file}: source_data.decision_file is required by ${p.version}`);
    else if(!fs.existsSync(path.join(root,'site/data',decisionFile))) errors.push(`${week.run_file}: missing decision file ${decisionFile}`);
    const required=['v1.9','v1.10'].includes(p.version)?['resolve_prompt','discover_ai_cross_search','discover_explicit_sources','normalize_and_dedupe','family_fit_decision_audit','freeze_candidates','enrich_images','official_verification','apply_corrections','strict_validation','decision_validation','family_fit_regression_test','explicit_source_coverage_test','discovery_provenance_test','copy_contract_test','shared_filter_test']:p.version==='v1.8'?['resolve_prompt','discover_ai_cross_search','discover_explicit_sources','normalize_and_dedupe','family_fit_decision_audit','freeze_candidates','enrich_images','official_verification','apply_corrections','strict_validation','decision_validation','family_fit_regression_test','explicit_source_coverage_test','copy_contract_test','shared_filter_test']:p.version==='v1.7'?['resolve_prompt','discover_23_wards','discover_legacy_sources','normalize_and_dedupe','family_fit_decision_audit','freeze_candidates','enrich_images','official_verification','apply_corrections','strict_validation','decision_validation','family_fit_regression_test','legacy_source_coverage_test','copy_contract_test','shared_filter_test']:['resolve_prompt','discover_23_wards','normalize_and_dedupe','family_fit_decision_audit','freeze_candidates','enrich_images','official_verification','apply_corrections','strict_validation','decision_validation','copy_contract_test','shared_filter_test'];
    const stages=new Map((run.stages||[]).map(s=>[s.name,s.status]));
    for(const name of required){if(stages.get(name)!=='passed') errors.push(`${week.run_file}: stage ${name} must be passed`);}
  }
}
if(errors.length){
  console.error('Prompt governance validation failed:');
  for(const error of errors) console.error(`- ${error}`);
  process.exit(1);
}
console.log(`Prompt governance OK: latest=${latest.version}, history=${entries.length}, historical_current_runs=${historicalRuns}`);
