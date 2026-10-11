// Normal committed B30; native desktop/filter/source actions, no facts/profile changes.
const fs=await import("node:fs/promises"),crypto=await import("node:crypto");
const root=globalThis.CI_WORKFLOW_ROOT,port=Number(globalThis.CI_WORKFLOW_EDITOR_PORT);
if(!root||!Number.isSafeInteger(port)||port<1024)throw new Error("Explicit English root/port required");
const input=root+"/.artifacts/1007-comparison-reading-current30-v1/verified.json";
const bytes=await fs.readFile(input),verified=JSON.parse(bytes);
if(verified.revision!==30||verified.facts_unchanged!==1505)throw new Error("Normal committed30 proof required");
const out=root+"/.artifacts/1007-comparison-reading-current30-qa-v1";
await fs.mkdir(out); // Exclusive; failed partial QA must be inspected, not overwritten.
const page=(await taskSpace(2)).page("p1");
const base=`http://127.0.0.1:${port}/reports/${verified.generation}/B/overview.html`;
const query="?view=comparison&cmp=efficacy%3A%3Aq-pruritus-nrs-ge4-improvement";
const run={state:"RUNNING_NOT_ACCEPTED",generation:verified.generation,revision:30,
 proof_sha256:crypto.createHash("sha256").update(bytes).digest("hex"),space:2,results:[],
 source_current_writes:0,fresh_browser:false,owner_pixels:"PENDING",limits:
 "Selected true question only; no all-page/cross-browser/universe/scientific/RC acceptance"};
async function ready(){
 await page.waitForFunction(()=>document.fonts.status==="loaded"&&
  !!document.querySelector(".kz-b-study-panel"),undefined,{timeout:120000});
 await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
}
async function inspect(state){
 const measured=await page.evaluate(()=>{
  const module=document.querySelector("#kz-chart-module"),workspace=document.querySelector("#full-study-comparison");
  return{width:innerWidth,documentWidth:document.documentElement.scrollWidth,
   revision:document.body.dataset.currentRevision,
   generation:JSON.parse(document.querySelector("#ci-current-edit").textContent).generation,
   groups:(window.__CHART_GROUPS__||[]).map(g=>({id:g.scientific_group_id,rows:g.rows.map(r=>r.row_id)})),
   questionIds:JSON.parse(workspace.dataset.questionRowIds||"[]"),
   displayedIds:JSON.parse(workspace.dataset.displayedRowIds||"[]"),
   panels:[...module.querySelectorAll(".kz-b-study-panel")].map(e=>({study:e.dataset.studyId,
    groups:e.querySelectorAll(".kz-chart-module__group").length,
    width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height})),
   values:[...module.querySelectorAll(".kz-chart-single-fact__value")].map(e=>{
    const b=e.getBoundingClientRect(),s=getComputedStyle(e);return{text:e.textContent,width:b.width,
     height:b.height,font:parseFloat(s.fontSize),line:parseFloat(s.lineHeight)};}),
   groupButtons:[...module.querySelectorAll("[data-chart-evidence-open]")].map(e=>e.dataset.rowId),
   tableIds:[...module.querySelectorAll("tr[data-row-id]")].map(e=>e.dataset.rowId),
   measurements:[...module.querySelectorAll(".kz-b-measurement-panel")].map(e=>{
    const b=e.getBoundingClientRect(),p=e.parentElement.getBoundingClientRect();
    const cards=[...e.querySelectorAll(".kz-chart-module__group")].map(c=>{
     const r=c.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};});
    return {count:e.dataset.observationCount,compact:e.classList.contains("kz-b-measurement-panel--compact"),
     x:b.x,y:b.y,width:b.width,height:b.height,parentWidth:p.width,cards};
   }),
   status:workspace.querySelector("[data-comparison-status]").textContent};
 });
 const failures=[];
 if(measured.revision!=="30"||measured.generation!==verified.generation)failures.push("current identity");
 if(measured.documentWidth>measured.width+1)failures.push("document overflow");
 const factIds=[...new Set(measured.groups.flatMap(g=>g.rows))].sort();
 if(JSON.stringify(factIds)!==JSON.stringify([...measured.questionIds].sort()))failures.push("query/frame scope");
 if(JSON.stringify(factIds)!==JSON.stringify([...new Set(measured.tableIds)].sort()))failures.push("complete table scope");
 for(const value of measured.values){
  if(value.width<140||value.font<16||value.height>value.line*5+1)failures.push("collapsed value/unit geometry");
 }
 if(state==="dense"&&(factIds.length!==32||measured.panels.length!==3))failures.push("frozen question fact/study scope");
 if(state==="filtered"&&(factIds.length!==2||measured.panels.length!==1))failures.push("native32→2 filter scope");
 if(state==="filtered"){
  const measures=measured.measurements;
  if(measures.length!==2||!measures.every(m=>m.compact&&m.width>=m.parentWidth*0.45&&
   m.cards.length===1&&m.cards[0].width>=m.width*0.9)||
   Math.abs(measures[0].y-measures[1].y)>2)failures.push("sparse measure horizontal allocation");
 }
 const record={state,...measured,failures};run.results.push(record);
 await fs.writeFile(out+"/actual.json",JSON.stringify(run,null,2));return record;
}
try{
 for(const width of [1440,1600,1920,2560]){
  await page.cdp("Emulation.setDeviceMetricsOverride",{width,height:1000,deviceScaleFactor:1,mobile:false});
  await page.goto(base+query,{timeout:120000});await ready();
  await fs.writeFile(out+`/snapshot-${width}.txt`,await page.snapshot());
  await page.screenshot({path:out+`/B-matrix-${width}.png`});
  const dense=await inspect("dense");
  await page.evaluate(()=>document.querySelector("#kz-chart-module").scrollIntoView({block:"start"}));
  await page.screenshot({path:out+`/B-panels-${width}.png`});
  const first=dense.groupButtons[0];
  if(!first)throw new Error("No real evidence trigger");
  const trigger=`#kz-chart-module [data-chart-evidence-open="${first}"]`;
  const index=await page.evaluate(selector=>document.querySelector(selector).closest(
   ".kz-chart-module__group").getAttribute("data-group-index"),trigger);
  const summary=`.kz-chart-module__group[data-group-index="${index}"] .kz-complete-table > summary`;
  await page.click(summary);await ready();
  const expanded=await page.evaluate(index=>{
   const wrapper=document.querySelector(`.kz-chart-module__group[data-group-index="${index}"]`);
   const context=wrapper.querySelector(".kz-chart-single-fact__context");
   const bounds=context.getBoundingClientRect();return{context:context.innerText,width:bounds.width,
    height:bounds.height,font:parseFloat(getComputedStyle(context).fontSize),
    full_table:wrapper.querySelector(".kz-complete-table").open};
  },index);
  dense.expanded=expanded;
  if(!expanded.full_table||expanded.width<160||expanded.font<16)dense.failures.push("expanded context geometry");
  await page.screenshot({path:out+`/B-expanded-${width}.png`});
  await page.click(summary);await ready();
  await page.click(trigger);await page.waitForFunction(()=>!document.querySelector("#kz-evidence-drawer").hidden);
  const source=await page.evaluate(()=>document.querySelector("#kz-evidence-drawer").innerText);
  await page.screenshot({path:out+`/B-source-${width}.png`});
  await page.keyboard.press("Escape");
  const focus=await page.evaluate(selector=>document.activeElement.matches(selector),trigger);
  dense.source={row_id:first,text:source,focus};
  if(!focus||!source.includes("原文定位")||source.includes("当前用户修订值\nNone"))dense.failures.push("source/focus");
  // Actual filter buttons from the prior same-contract source snapshot, not forged state.
  await page.click("#kz-filter-panel > summary");
  await page.click('button[data-filter-dimension="trial"][data-filter-value="nct04501666"]');
  await page.waitForFunction(()=>document.querySelectorAll(".kz-b-study-panel").length===1);
  await ready();await inspect("filtered");
  await page.evaluate(()=>document.querySelector("#kz-chart-module").scrollIntoView({block:"start"}));
  await page.screenshot({path:out+`/B-filtered-${width}.png`});
  // Same component returns to the full question without stale/accumulating panels.
  await page.click('button[data-filter-dimension="trial"][data-filter-value="nct04501666"]');
  await page.waitForFunction(()=>document.querySelectorAll(".kz-b-study-panel").length===3);
  await ready();await inspect("restored");
 }
 if(run.results.some(r=>r.failures.length))throw new Error("Actual geometry/interaction checks failed; read actual.json");
 run.state="SCOPED_PRODUCTION_BEHAVIOR_PASSED_OWNER_PIXELS_PENDING";
}catch(error){run.state="FAILED_NOT_ACCEPTED";run.error=String(error);throw error;}
finally{await fs.writeFile(out+"/actual.json",JSON.stringify(run,null,2));}
console.log({state:run.state,results:run.results.length,widths:[1440,1600,1920,2560]});


