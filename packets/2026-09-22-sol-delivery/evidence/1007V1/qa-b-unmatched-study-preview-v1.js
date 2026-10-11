// One normal B-only preview, native checkbox/filter/source actions; no current writes.
const fs=await import("node:fs/promises"),crypto=await import("node:crypto");
const root=globalThis.CI_WORKFLOW_ROOT;
if(!root)throw new Error("Explicit English root required");
const out=root+"/.artifacts/1007-b-unmatched-study-preview-v1";
const bytes=await fs.readFile(out+"/actual.json"),render=JSON.parse(bytes);
if(render.state!=="NORMAL_CURRENT30_B_PREVIEW_NOT_CURRENT_OR_ACCEPTED"||render.facts!==1505)
 throw new Error("Normal source-preserving B-only preview required");
await fs.mkdir(out+"/qa");
const page=(await taskSpace(2)).page("p1");
const run={state:"RUNNING_NOT_ACCEPTED",source_generation:render.source_generation,
 render_proof_sha256:crypto.createHash("sha256").update(bytes).digest("hex"),
 space:2,states:[],failures:[],source_current_writes:0,owner_pixels:"PENDING",
 limits:"One genuine B question/page, four widths; not all pages/current/share/science/RC acceptance"};
async function ready(){await page.waitForFunction(()=>document.fonts.status==="loaded"&&
 !!document.querySelector(".kz-b-study-panel"),undefined,{timeout:120000});
 await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));}
async function inspect(state){
 const actual=await page.evaluate(()=>{
  const host=document.querySelector("#full-study-comparison");
  const rows=[...host.querySelectorAll("tbody tr")];
  return {width:innerWidth,scrollWidth:document.documentElement.scrollWidth,
   rowCount:rows.length,visibleRows:rows.filter(r=>getComputedStyle(r).display!=="none")
    .map(r=>r.dataset.studyId),
   matched:JSON.parse(host.dataset.matchedStudyIds),unmatched:JSON.parse(host.dataset.unmatchedStudyIds),
   question:JSON.parse(host.dataset.questionRowIds).sort(),
   displayed:JSON.parse(host.dataset.displayedRowIds).sort(),
   chartIds:[...new Set(window.__CHART_GROUPS__.flatMap(g=>g.rows.map(r=>r.row_id)))].sort(),
   checkbox:host.querySelector("[data-comparison-unmatched-toggle]").checked,
   count:host.querySelector("[data-comparison-unmatched-count]").textContent,
   status:host.querySelector("[data-comparison-status]").textContent,
   tableHeight:host.querySelector("table").getBoundingClientRect().height,
   retainedStudies:window.__B_COMPARISON_WORKSPACE__.study_ids.length,
   buttons:[...host.querySelectorAll("[data-evidence-open]")].map(b=>b.dataset.evidenceOpen)};
 });
 if(actual.scrollWidth>actual.width+1)run.failures.push(state+" overflow");
 if(JSON.stringify(actual.question)!==JSON.stringify(actual.displayed)||
 JSON.stringify(actual.question)!==JSON.stringify(actual.chartIds))run.failures.push(state+" scope");
 const expanded=state==="expanded";
 if(actual.visibleRows.length!==(expanded?actual.rowCount:actual.matched.length))
  run.failures.push(state+" actual row visibility");
 if(Number(actual.count)!==actual.unmatched.length)run.failures.push(state+" actual count");
 if(state!=="filtered"&&(actual.question.length!==32||actual.matched.length!==3||
 actual.rowCount!==actual.retainedStudies))run.failures.push(state+" full membership/32facts");
 if(state==="filtered"&&(actual.question.length!==2||actual.matched.length!==1||actual.rowCount!==1))
  run.failures.push(state+" native filter");
 run.states.push({state,...actual});await fs.writeFile(out+"/qa/actual.json",JSON.stringify(run,null,2));
 return actual;
}
try{
 for(const width of [1440,1600,1920,2560]){
  await page.cdp("Emulation.setDeviceMetricsOverride",{width,height:1000,deviceScaleFactor:1,mobile:false});
  await page.goto("file://"+out+"/B/overview.html?view=comparison&cmp="+
   encodeURIComponent("efficacy::q-pruritus-nrs-ge4-improvement"),{timeout:120000});await ready();
  const collapsed=await inspect("collapsed");
  await fs.writeFile(out+`/qa/snapshot-${width}.txt`,await page.snapshot());
  await page.screenshot({path:out+`/qa/B-matched-${width}.png`});
  const toggle="[data-comparison-unmatched-toggle]";
  await page.click(toggle);await ready();const expanded=await inspect("expanded");
  await page.screenshot({path:out+`/qa/B-all-related-${width}.png`});
  if(expanded.tableHeight<=collapsed.tableHeight)run.failures.push("disclosure height not actually changed");
  await page.keyboard.press("Space");await ready();
  const keyboard=await inspect("keyboard-collapsed");
  if(keyboard.checkbox||!(await page.evaluate(s=>document.activeElement.matches(s),toggle)))
   run.failures.push("native keyboard toggle/focus");
  const id=collapsed.buttons[0],trigger=`#full-study-comparison [data-evidence-open="${id}"]`;
  await page.click(trigger);await page.waitForFunction(()=>!document.querySelector("#kz-evidence-drawer").hidden);
  const original=await page.evaluate(()=>document.querySelector("#kz-evidence-drawer").innerText);
  await page.screenshot({path:out+`/qa/B-source-${width}.png`});
  await page.keyboard.press("Escape");
  if(!original.includes("原文定位")||!(await page.evaluate(s=>document.activeElement.matches(s),trigger)))
   run.failures.push("source/Esc true trigger");
  await page.click("#kz-filter-panel > summary");
  await page.click('button[data-filter-dimension="trial"][data-filter-value="nct04501666"]');
  await page.waitForFunction(()=>document.querySelectorAll(".kz-b-study-panel").length===1);
  await ready();await inspect("filtered");await page.screenshot({path:out+`/qa/B-filtered-${width}.png`});
  await page.click('button[data-filter-dimension="trial"][data-filter-value="nct04501666"]');
  await page.waitForFunction(()=>document.querySelectorAll(".kz-b-study-panel").length===3);
  await ready();await inspect("restored");
 }
 if(run.failures.length)throw new Error(run.failures.join(";"));
 run.state="SCOPED_NATIVE_DISCLOSURE_AND_MEMBERSHIP_PASSED_OWNER_PIXELS_PENDING";
}catch(error){run.state="FAILED_NOT_ACCEPTED";run.error=String(error);throw error;}
finally{await fs.writeFile(out+"/qa/actual.json",JSON.stringify(run,null,2));}
console.log({state:run.state,states:run.states.length,failures:run.failures});
