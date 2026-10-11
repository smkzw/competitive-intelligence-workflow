// One ordinary current32 render, existing Ego2/p1, real glyph/source/focus actions.
const fs=await import('node:fs/promises'),path=await import('node:path');
const crypto=await import('node:crypto');
const relative='.artifacts/1007-ab-task-geometry-v1',root=path.join(workflowRoot,relative);
const actual=JSON.parse(await fs.readFile(path.join(root,'actual.json'),'utf8'));
if(actual.current_writes!==0||Object.keys(actual.reports).sort().join('')!=='AB')
 throw Error('Complete ordinary readonly AB render first');
const raw=await fs.readFile(path.join(workflowRoot,
 'packets/2026-09-22-sol-delivery/evidence/1007V1/qa-a-shared-question-current-v1.js'));
if(crypto.createHash('sha256').update(raw).digest('hex')!==
 'd2aae27911cf63c368ba896d87ff7abc54221cc799e4b4ff4c402f2c1457f1ac')
 throw Error('Frozen A task recipe changed');
let source=raw.toString().replaceAll('.artifacts/1007-ab-shared-question-preview-v3',relative)
 .replace('candidateRelative, "a-qa-v2"','candidateRelative, "a-qa"')
 .replace('window.__QA_A_SOURCE_TRIGGER__=document.elementFromPoint(x,y);',
 'const original=window.__A_COMPARISON_EVIDENCE__;'+
 'window.__A_COMPARISON_EVIDENCE__=function(id,trigger){'+
 'window.__QA_A_SOURCE_TRIGGER__=trigger;return original(id,trigger);};');
const marker='    const target=await page.evaluate(()=>{';
if(!source.includes(marker))throw Error('Frozen A insertion missing');
source=source.replace(marker,`
    const geometry=await page.evaluate(()=>{
      const group=window.__CHART_GROUPS__[0],el=document.querySelector('#kz-chart-0');
      const plan=window.__PRESENTATION_PLAN__(group);
      return {kind:el.dataset.chartType,height:el.getBoundingClientRect().height,
        plan,mainTop:document.querySelector('.kz-a-main').getBoundingClientRect().top,
        panelTop:document.querySelector('#full-study-comparison').getBoundingClientRect().top};
    });
    dense.taskGeometry=geometry;
    if(geometry.kind!=='line'||geometry.plan.observation_count!==24||
       geometry.plan.entity_count!==1||geometry.height>320||
       geometry.panelTop-geometry.mainTop>160)
       run.failures.push(width+':trajectory-first or grid stretch');
`+marker);
await new(Object.getPrototypeOf(async function(){}).constructor)(
 'taskSpace','workflowRoot',source)(taskSpace,workflowRoot);
const page=(await taskSpace(2)).page('p1'),out=path.join(root,'b-qa');
await fs.mkdir(out);
const home='file://'+path.join(root,'B/overview.html');
const url=home+'?view=comparison&cmp=efficacy%3A%3Aq-pruritus-nrs-ge4-improvement';
const run={state:'RUNNING_NOT_ACCEPTED',states:[],failures:[],currentWrites:0};
async function record(label){
 const measured=await page.evaluate(()=>{
  const host=document.querySelector('#full-study-comparison');
  const groups=window.__CHART_GROUPS__;
  const module=document.querySelector('#kz-chart-module').getBoundingClientRect();
  const table=document.querySelector('.kz-b-comparison-details').getBoundingClientRect();
  return {width:innerWidth,ids:JSON.parse(host.dataset.displayedRowIds||'[]'),
   graphIds:groups.flatMap(g=>g.rows.map(r=>r.row_id)),
   primaryIds:[...document.querySelectorAll('[data-primary-comparison-table] button[data-row-id]')]
    .map(n=>n.dataset.rowId),
   plots:groups.map((g,i)=>{const el=document.querySelector('#kz-chart-'+i);
    const plan=window.__PRESENTATION_PLAN__(g);
    const box=el.getBoundingClientRect();return {kind:el.dataset.chartType,
      height:box.height,top:box.top,plan,ids:g.rows.map(r=>r.row_id)};}),
   inline:module.right<=table.left+1&&table.top<innerHeight-200,
   overflow:document.documentElement.scrollWidth>innerWidth+1};
 });
 run.states.push({label,...measured});
 const sorted=ids=>ids.slice().sort().join('|');
 if(measured.overflow||!measured.inline||sorted(measured.ids)!==sorted(measured.graphIds)||
    sorted(measured.ids)!==sorted(measured.primaryIds))run.failures.push(label+measured.width+':query/geometry');
 await page.screenshot({path:path.join(out,label+'-'+measured.width+'.png')});
 return measured;
}
try{
 for(const width of [1440,1600,1920,2560]){
  await page.cdp('Emulation.setDeviceMetricsOverride',{width,
   height:width===2560?1440:width===1920?1080:900,deviceScaleFactor:1,mobile:false});
  await page.goto(url,{timeout:120000});
  await page.waitForFunction(()=>window.__CHART_GROUPS__&&document.querySelector('#kz-chart-0'));
  const dense=await record('dense'),first=dense.plots[0];
  if(dense.ids.length!==32||first.kind!=='line'||first.plan.observation_count!==24||
     first.plan.entity_count!==1||first.height>320)run.failures.push(width+':trajectory-first');
  const target=await page.evaluate(()=>{
   const el=document.querySelector('#kz-chart-0');el.scrollIntoView({block:'center'});
   const chart=echarts.getInstanceByDom(el),option=chart.getOption();
   const points=option.series[0].data,point=points[points.length-1];
   if(point.value[1]!==57.7)throw Error('Wrong original timepoint');
   const pixel=chart.convertToPixel({seriesIndex:0},point.value),box=el.getBoundingClientRect();
   return {x:box.left+pixel[0],y:box.top+pixel[1],id:point._row_id};
  });
  await page.mouse.click(target.x,target.y,{label:'打开第24周真实原文'});
  await page.waitForFunction(()=>!document.querySelector('#kz-evidence-drawer').hidden);
  const source=await record('source');
  source.evidence=await page.evaluate(()=>document.querySelector('#kz-evidence-drawer').innerText);
  if(!source.evidence.includes('57.7')||!source.evidence.includes('原文定位'))
   run.failures.push(width+':source');
  await page.keyboard.press('Escape');
  source.focus=await page.evaluate(()=>({closed:document.querySelector('#kz-evidence-drawer').hidden,
   id:document.activeElement.getAttribute('data-chart-evidence-open')}));
  if(!source.focus.closed||source.focus.id!==target.id)run.failures.push(width+':focus');
  await page.goto(url,{timeout:120000});
  await page.waitForFunction(()=>window.__CHART_GROUPS__);
  await page.evaluate(()=>document.querySelector('#kz-filter-panel > summary').scrollIntoView({block:'center'}));
  await page.click('#kz-filter-panel > summary');
  await page.click('button[data-filter-dimension="trial"][data-filter-value="nct04501666"]');
  await page.waitForFunction(()=>JSON.parse(document.querySelector('#full-study-comparison')
   .dataset.displayedRowIds||'[]').length===2);
  await page.click('#kz-filter-panel > summary');
  const sparse=await record('filtered');
  if(sparse.ids.length!==2||sparse.plots.some(p=>p.kind==='line'&&p.ids.length===24))
   run.failures.push(width+':filtered fabricated trajectory');
 }
 run.state=run.failures.length?'FAILED_NOT_ACCEPTED':'BOUNDED_AB_TASK_GEOMETRY_PASS';
}catch(error){run.state='FAILED_NOT_ACCEPTED';run.error=String(error);throw error;}
finally{await fs.writeFile(path.join(out,'actual.json'),JSON.stringify(run,null,2));}
console.log({state:run.state,states:run.states.length,failures:run.failures});
if(run.failures.length)throw Error(run.failures.join('; '));
