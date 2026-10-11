// Normal A/B current32 candidate, existing Ego2/p1, no fact/current edits.
const fs = await import("node:fs/promises");
const crypto = await import("node:crypto");
const path = await import("node:path");
if (path.basename(workflowRoot) !== "competitive-intelligence-workflow")
  throw Error("Explicit English project root required");
const candidateRelative = ".artifacts/1007-ab-shared-question-preview-v2";
const recipes = path.join(workflowRoot, "packets/2026-09-22-sol-delivery/evidence/1007V1");
const rawB = await fs.readFile(path.join(recipes, "qa-b-primary-matrix-preview-v1.js"));
if (crypto.createHash("sha256").update(rawB).digest("hex") !==
    "ee37c4f5709bfa27e5c5aea1484fb6c5275545d8d90b760aa831649cd3f9275e")
  throw Error("Frozen B task recipe changed");
const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
// A/B render manifest has explicit per-report counts, not the old B-only pages field.
await new AsyncFunction("taskSpace", "workflowRoot", rawB.toString().replaceAll(
  ".artifacts/1007-b-primary-matrix-preview-v1", candidateRelative)
  .replace("actual.pages !== 104", "actual.reports.B.pages !== 104"))(taskSpace, workflowRoot);
const bActual=JSON.parse(await fs.readFile(path.join(workflowRoot,candidateRelative,
  "qa/actual.json"),"utf8"));
for(const state of bActual.states.filter(s=>s.mode==="comparison")) {
  if(state.plots.flatMap(p=>p.rowIds).sort().join("|")!==state.primaryIds.slice().sort().join("|"))
    throw Error("B graph/primary query mismatch at "+state.width+" "+state.label);
}
const paired = await fs.readFile(path.join(recipes, "qa-b-question-paired-reading-v2.js"), "utf8");
await new AsyncFunction("taskSpace", "workflowRoot", "candidateRelative", paired)(
  taskSpace, workflowRoot, candidateRelative);

const out = path.join(workflowRoot, candidateRelative, "a-qa");
await fs.mkdir(out);
const page = (await taskSpace(2)).page("p1");
const home = "file://" + path.join(workflowRoot, candidateRelative, "A/clinical-portfolio.html");
const url = home + "?view=comparison&cmp=efficacy%3A%3Aq-pruritus-nrs-ge4-improvement";
const run = {state: "RUNNING_NOT_ACCEPTED", states: [], failures: [], currentWrites: 0};
async function record(label) {
  const observed = await page.evaluate(() => {
    const host = document.querySelector("#full-study-comparison");
    const table = host.querySelector(".kz-a-table-wrap").getBoundingClientRect();
    const graph = host.querySelector("#kz-chart-module").getBoundingClientRect();
    const groups = window.__CHART_GROUPS__;
    return {width: innerWidth, label: document.body.dataset.comparisonView,
      displayedIds: JSON.parse(host.dataset.displayedRowIds || "[]"),
      graphIds: groups.flatMap(g=>g.rows.map(r=>r.row_id)),
      groups: groups.map(g=>({purpose:g.comparison_purpose, kind:g.chart_type,
        values:g.rows.map(r=>r.value), aIds:g.rows.map(r=>r.a_row_id), crossTrial:g.cross_trial})),
      parallel: graph.right <= table.left + 1 && table.top < innerHeight - 200,
      tableTop:table.top, graphTop:graph.top,
      overflow:document.documentElement.scrollWidth>innerWidth+1,
      tableCanScroll:host.querySelector(".kz-a-table-wrap").scrollHeight > table.height,
      sourceOpen:!document.querySelector("#data-basis-panel").hidden};
  });
  run.states.push({state:label,...observed});
  if (observed.graphIds.slice().sort().join("|") !== observed.displayedIds.slice().sort().join("|"))
    run.failures.push(label+":"+observed.width+":graph/table current-query mismatch");
  if (!observed.parallel || observed.overflow) run.failures.push(label+":"+observed.width+":geometry");
  await page.screenshot({path:path.join(out,label+"-"+observed.width+".png")});
  await fs.writeFile(path.join(out,"actual.json"),JSON.stringify(run,null,2));
  return observed;
}
try {
  for (const width of [1440,1600,1920,2560]) {
    await page.cdp("Emulation.setDeviceMetricsOverride", {width,height:width===2560?
      1440:width===1920?1080:900,deviceScaleFactor:1,mobile:false});
    await page.goto(url,{timeout:120000});
    await page.waitForFunction(()=>window.__CHART_GROUPS__&&
      window.__CHART_GROUPS__.some(g=>g.comparison_purpose==="clinical_question_descriptive"));
    const dense=await record("dense");
    if(dense.displayedIds.length!==32||!dense.groups.some(g=>g.kind==="line"&&g.values.length===24))
      run.failures.push(width+":missing original source-local visits");
    if(!dense.groups.some(g=>g.purpose==="clinical_question_descriptive"&&!g.crossTrial&&
      g.values.slice().sort((a,b)=>a-b).join("|")==="75|78|103|111"))
      run.failures.push(width+":missing actual two-study posted-count plot");
    const target=await page.evaluate(()=>{
      const gi=window.__CHART_GROUPS__.findIndex(g=>g.comparison_purpose===
        "clinical_question_descriptive"&&g.rows.length===4);
      const el=document.querySelector("#kz-chart-"+gi);el.scrollIntoView({block:"center"});
      const chart=echarts.getInstanceByDom(el),option=chart.getOption();let found;
      option.series.forEach((s,si)=>s.data.forEach((p,di)=>{
        if(p._row_id==="eff-7a82bfadf17f4066f213")found={si,di,p};
      }));
      if(!found||found.p.value!==75)throw Error("wrong A glyph");
      const pixel=chart.convertToPixel({seriesIndex:found.si},[found.di,37.5]);
      const rect=el.getBoundingClientRect();
      return {x:rect.left+pixel[0],y:rect.top+pixel[1],id:found.p._row_id,
        aId:window.__A_COMPARISON_ROWS__[found.p._row_id].a_row_id};
    });
    await page.mouse.click(target.x,target.y,{label:"查看 A 人数原文"});
    await page.waitForFunction(()=>!document.querySelector("#data-basis-panel").hidden);
    const evidence=await page.evaluate(()=>{
      const p=document.querySelector("#data-basis-panel");return {text:p.innerText,
        links:[...p.querySelectorAll("a[href]")].map(a=>a.getAttribute("href"))};
    });
    if(!evidence.text.includes("75")||!evidence.text.includes("outcomeMeasures[2]")||
      !evidence.links.some(h=>h.includes("NCT04501679")))
      run.failures.push(width+":A source atom/link mismatch");
    const source=await record("source");source.evidence=evidence;source.clicked=target;
    await page.keyboard.press("Escape");
    const focus=await page.evaluate(()=>({closed:document.querySelector("#data-basis-panel").hidden,
      id:document.activeElement.getAttribute("data-chart-evidence-open"),
      aId:document.activeElement.getAttribute("data-evidence-row-id")}));
    if(!focus.closed||focus.id!==target.id||focus.aId!==target.aId)
      run.failures.push(width+":A exact trigger focus");
    source.focus=focus;
    await page.goto(url,{timeout:120000});
    await page.waitForFunction(()=>window.__A_COMPARISON_ROWS__&&window.__CHART_GROUPS__);
    await page.click("details[data-comparison-disclosure] > summary");
    await page.click("button[data-filter-dimension=product][data-filter-value=Nemolizumab]");
    await page.waitForFunction(()=>JSON.parse(document.querySelector("#full-study-comparison")
      .dataset.displayedRowIds||"[]").length===4);
    await page.click("details[data-comparison-disclosure] > summary");
    const filtered=await record("filtered");
    if(filtered.displayedIds.length!==4||filtered.groups.length!==1)
      run.failures.push(width+":A filter did not scope source-posted plot");
  }
  run.state=run.failures.length?"FAILED_NOT_ACCEPTED":"BOUNDED_AB_QUERY_GLYPH_GEOMETRY_PASS";
} catch(error) {run.state="FAILED_NOT_ACCEPTED";run.error=String(error);throw error;}
finally {await fs.writeFile(path.join(out,"actual.json"),JSON.stringify(run,null,2));}
console.log({state:run.state,states:run.states.length,failures:run.failures});
if(run.failures.length)throw Error(run.failures.join("; "));
