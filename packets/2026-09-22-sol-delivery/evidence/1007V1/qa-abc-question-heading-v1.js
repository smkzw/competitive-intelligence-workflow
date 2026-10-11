// Normal current32-derived candidate. Revalidate the changed shared reading seam.
const fs=await import('node:fs/promises'),path=await import('node:path');
const crypto=await import('node:crypto');
const relative='.artifacts/1007-abc-question-heading-v1';
const folder=path.join(workflowRoot,relative);
const actual=JSON.parse(await fs.readFile(path.join(folder,'actual.json'),'utf8'));
if(actual.current_writes!==0||Object.keys(actual.reports).sort().join('')!=='ABC')
 throw Error('Normal render must finish before browser QA');
const raw=await fs.readFile(path.join(workflowRoot,
 'packets/2026-09-22-sol-delivery/evidence/1007V1/qa-a-shared-question-current-v1.js'));
if(crypto.createHash('sha256').update(raw).digest('hex')!==
 'd2aae27911cf63c368ba896d87ff7abc54221cc799e4b4ff4c402f2c1457f1ac')
 throw Error('Original frozen A task instrument changed');
let source=raw.toString().replaceAll('.artifacts/1007-ab-shared-question-preview-v3',relative)
 .replace('candidateRelative, "a-qa-v2"','candidateRelative, "a-qa"')
 .replace('window.__QA_A_SOURCE_TRIGGER__=document.elementFromPoint(x,y);',
 'const original=window.__A_COMPARISON_EVIDENCE__;'+
 'window.__A_COMPARISON_EVIDENCE__=function(id,trigger){'+
 'window.__QA_A_SOURCE_TRIGGER__=trigger;return original(id,trigger);};');
const marker='    const target=await page.evaluate(()=>{';
if(!source.includes(marker))throw Error('Frozen A insertion point missing');
source=source.replace(marker,`
    dense.reading=await page.evaluate(()=>{
      const module=document.querySelector('#kz-chart-module');
      return {titles:[...module.querySelectorAll('.kz-chart-group__title')]
        .filter(n=>n.checkVisibility()).map(n=>n.textContent),
        values:[...module.querySelectorAll('.kz-chart-single-fact__value')]
        .filter(n=>n.checkVisibility()).map(n=>n.textContent),
        fullTitles:[...module.querySelectorAll('.kz-chart-source-context')]
        .map(n=>({text:n.textContent,visible:n.checkVisibility(),
          inDetails:!!n.closest('.kz-complete-table')}))};
    });
    if(dense.reading.titles.some(t=>t.length>80||/Probability of Participants|报告未注明/.test(t))||
      !dense.reading.values.includes('0.67 受试者概率')||
      dense.reading.fullTitles.some(t=>t.visible||!t.inDetails)||
      !dense.reading.fullTitles.some(t=>t.text.includes('Probability of Participants')))
      run.failures.push(width+':shared expert heading or original detail lost');
`+marker);
await new(Object.getPrototypeOf(async function(){}).constructor)(
 'taskSpace','workflowRoot',source)(taskSpace,workflowRoot);
const page=(await taskSpace(2)).page('p1');
const out=path.join(folder,'bc-qa');await fs.mkdir(out);
const result={state:'RUNNING_NOT_ACCEPTED',states:[],failures:[],currentWrites:0};
try{
 for(const report of ['B','C'])for(const width of [1440,1600,1920,2560]){
  await page.cdp('Emulation.setDeviceMetricsOverride',{width,
   height:width===2560?1440:width===1920?1080:900,deviceScaleFactor:1,mobile:false});
  await page.goto('file://'+path.join(folder,report,'overview.html')+
    (report==='B'?'?view=comparison&cmp=efficacy%3A%3Aq-pruritus-nrs-ge4-improvement':''));
  await page.waitForFunction(()=>document.querySelector('[data-source-disclosure]'));
  const state=await page.evaluate(report=>{
    const body=document.body.innerText;
    const host=document.querySelector('#full-study-comparison');
    return {width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth+1,
     lecture:body.includes('不只凭适应症给出唯一或最佳设计'),
     displayed:report==='B'?JSON.parse(host.dataset.displayedRowIds||'[]'):[],
     chartIds:report==='B'?window.__CHART_GROUPS__.flatMap(g=>g.rows.map(r=>r.row_id)):[],
     titles:[...document.querySelectorAll('.kz-chart-group__title')]
      .filter(n=>n.checkVisibility()).map(n=>n.textContent)};
  },report);
  result.states.push({report,...state});
  if(state.overflow||state.lecture||state.titles.some(t=>t.length>80))
   result.failures.push(report+width+':reading or geometry');
  if(report==='B'&&(state.displayed.length!==32||
   state.displayed.slice().sort().join('|')!==state.chartIds.slice().sort().join('|')))
   result.failures.push(report+width+':query mismatch');
  await page.screenshot({path:path.join(out,report+'-'+width+'.png')});
 }
 result.state=result.failures.length?'FAILED_NOT_ACCEPTED':'BOUNDED_BC_HEADING_PASS';
}catch(error){result.state='FAILED_NOT_ACCEPTED';result.error=String(error);throw error;}
finally{await fs.writeFile(path.join(out,'actual.json'),JSON.stringify(result,null,2));}
console.log({state:result.state,states:result.states.length,failures:result.failures});
if(result.failures.length)throw Error(result.failures.join('; '));
