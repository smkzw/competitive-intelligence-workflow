// Ordinary frozen current32 C candidate; existing Ego2/p1, no facts/config/current writes.
const fs=await import('node:fs/promises'),path=await import('node:path');
const root=path.join(workflowRoot,'.artifacts/1007-abc-task-geometry-v2');
const actual=JSON.parse(await fs.readFile(path.join(root,'actual.json'),'utf8'));
if(actual.current_writes!==0||actual.reports.C.pages!==16)throw Error('Normal C render required');
const out=path.join(root,'c-qa');await fs.mkdir(out);
const page=(await taskSpace(2)).page('p1'),home='file://'+path.join(root,'C/overview.html');
const run={state:'RUNNING_NOT_ACCEPTED',states:[],failures:[],currentWrites:0};
async function record(label){
 const state=await page.evaluate(()=>{
  const summary=document.querySelector('[aria-label="设计概要"]');
  const observations=window.REPORT_C.observations;
  const items=summary?[...summary.querySelectorAll('li')].map(n=>({text:n.innerText,
   ids:[...n.querySelectorAll('[data-evidence-open]')].map(b=>b.dataset.evidenceOpen),
   disclosureOpen:n.querySelector('details').open})):[];
  const ids=[...document.querySelectorAll('[data-criterion-row-id]')]
   .map(n=>n.dataset.criterionRowId);
  const valid=new Set(observations.map(r=>r.row_id));
  return {width:innerWidth,mode:document.body.getAttribute('data-c-view'),items,
   currentIds:ids,originalObservationCount:observations.length,
   sourceIdsValid:items.every(i=>i.ids.every(id=>valid.has(id))),
   summaryVisible:!!summary&&summary.checkVisibility(),
   overflow:document.documentElement.scrollWidth>innerWidth+1,
   lecture:document.body.innerText.includes('不把并列描述当成临床等价')};
 });
 state.label=label;run.states.push(state);
 if(state.overflow||state.lecture||!state.sourceIdsValid)run.failures.push(label+state.width+':reading/source');
 await page.screenshot({path:path.join(out,label+'-'+state.width+'.png')});
 return state;
}
try{
 for(const width of [1440,1600,1920,2560]){
  await page.cdp('Emulation.setDeviceMetricsOverride',{width,
   height:width===2560?1440:width===1920?1080:900,deviceScaleFactor:1,mobile:false});
  await page.goto(home,{timeout:120000});
  await page.waitForFunction(()=>window.__EVIDENCE_DRAWER__&&window.REPORT_C);
  const summary=await record('home');
  if(!summary.summaryVisible||summary.items.length!==2||
     summary.items.some(i=>i.disclosureOpen||i.text.length>360)||
     !summary.items[0].text.includes('随机分配')||!summary.items[0].text.includes('平行分组')||
     !summary.items[1].text.includes('第24周'))run.failures.push(width+':substantive design summary');
  const selector='[aria-label="设计概要"] li:first-child details > summary';
  await page.evaluate(s=>document.querySelector(s).scrollIntoView({block:'center'}),selector);
  await page.click(selector);
  const target=await page.evaluate(()=>{
   const button=document.querySelector('[aria-label="设计概要"] button[data-evidence-open]');
   window.__QA_C_SUMMARY_TRIGGER__=button;button.scrollIntoView({block:'center'});
   const box=button.getBoundingClientRect();
   return {x:box.left+box.width/2,y:box.top+box.height/2,id:button.dataset.evidenceOpen};
  });
  await page.mouse.click(target.x,target.y,{label:'打开设计概要的真实依据'});
  await page.waitForFunction(()=>!document.querySelector('#kz-evidence-drawer').hidden);
  const source=await record('source');
  source.evidence=await page.evaluate(()=>document.querySelector('#kz-evidence-drawer').innerText);
  if(!source.evidence.includes('原文定位'))run.failures.push(width+':source locator');
  await page.keyboard.press('Escape');
  source.focus=await page.evaluate(()=>({closed:document.querySelector('#kz-evidence-drawer').hidden,
   same:document.activeElement===window.__QA_C_SUMMARY_TRIGGER__}));
  if(!source.focus.closed||!source.focus.same)run.failures.push(width+':summary focus');
  await page.goto(home+'?view=comparison',{timeout:120000});
  await page.waitForFunction(()=>document.querySelector('#kz-c-criteria-search'));
  const dense=await record('comparison');
  if(dense.summaryVisible||!dense.currentIds.length)run.failures.push(width+':task separation');
  await page.fill('#kz-c-criteria-search','NCT04501666');
  await page.waitForFunction(()=>new URLSearchParams(location.search).get('criteria_q')==='NCT04501666');
  const filtered=await record('filtered');
  if(!filtered.currentIds.length||filtered.currentIds.length>=dense.currentIds.length||
     filtered.currentIds.some(id=>!id.toLowerCase().includes('nct04501666')))
   run.failures.push(width+':real study filter');
 }
 run.state=run.failures.length?'FAILED_NOT_ACCEPTED':'BOUNDED_C_SUMMARY_COMPARISON_SOURCE_PASS';
}catch(error){run.state='FAILED_NOT_ACCEPTED';run.error=String(error);throw error;}
finally{await fs.writeFile(path.join(out,'actual.json'),JSON.stringify(run,null,2));}
console.log({state:run.state,states:run.states.length,failures:run.failures});
if(run.failures.length)throw Error(run.failures.join('; '));
