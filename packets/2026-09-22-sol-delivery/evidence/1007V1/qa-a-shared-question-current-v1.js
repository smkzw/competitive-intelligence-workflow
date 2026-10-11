// Existing Ego2/p1; source-canvas focus when present, same-fact fallback if replaced.
const fs = await import("node:fs/promises");
const path = await import("node:path");
const candidateRelative = ".artifacts/1007-ab-shared-question-preview-v3";
const out = path.join(workflowRoot, candidateRelative, "a-qa-v2");
await fs.mkdir(out);
const page = (await taskSpace(2)).page("p1");
const url = "file://" + path.join(workflowRoot, candidateRelative,
  "A/clinical-portfolio.html") +
  "?view=comparison&cmp=efficacy%3A%3Aq-pruritus-nrs-ge4-improvement";
const run = {state:"RUNNING_NOT_ACCEPTED",states:[],failures:[],currentWrites:0};
async function record(label) {
  const state = await page.evaluate(() => {
    const host=document.querySelector("#full-study-comparison");
    const table=host.querySelector(".kz-a-table-wrap").getBoundingClientRect();
    const graph=host.querySelector("#kz-chart-module").getBoundingClientRect();
    return {width:innerWidth,
      displayedIds:JSON.parse(host.dataset.displayedRowIds||"[]"),
      graphIds:window.__CHART_GROUPS__.flatMap(g=>g.rows.map(r=>r.row_id)),
      groups:window.__CHART_GROUPS__.map((g,i)=>({purpose:g.comparison_purpose,
        kind:document.querySelector("#kz-chart-"+i).dataset.chartType,
        values:g.rows.map(r=>r.value),crossTrial:g.cross_trial})),
      parallel:graph.right<=table.left+1 && table.top<innerHeight-200,
      graphTop:graph.top,tableTop:table.top,
      overflow:document.documentElement.scrollWidth>innerWidth+1,
      sourceOpen:!document.querySelector("#data-basis-panel").hidden};
  });
  state.state=label;
  run.states.push(state);
  if(state.graphIds.slice().sort().join("|")!==state.displayedIds.slice().sort().join("|"))
    run.failures.push(label+":"+state.width+":graph/table query mismatch");
  if(!state.parallel||state.overflow)run.failures.push(label+":"+state.width+":geometry");
  await page.screenshot({path:path.join(out,label+"-"+state.width+".png")});
  return state;
}
try {
  for(const width of [1440,1600,1920,2560]) {
    await page.cdp("Emulation.setDeviceMetricsOverride",{width,
      height:width===2560?1440:width===1920?1080:900,deviceScaleFactor:1,mobile:false});
    await page.goto(url,{timeout:120000});
    await page.waitForFunction(()=>window.__CHART_GROUPS__&&
      window.__CHART_GROUPS__.some(g=>g.comparison_purpose==="clinical_question_descriptive"));
    const dense=await record("dense");
    if(dense.displayedIds.length!==32||!dense.groups.some(g=>g.kind==="line"&&g.values.length===24))
      run.failures.push(width+":original line missing");
    if(!dense.groups.some(g=>g.purpose==="clinical_question_descriptive"&&!g.crossTrial&&
      g.values.slice().sort((a,b)=>a-b).join("|")==="75|78|103|111"))
      run.failures.push(width+":posted count graph missing");
    const target=await page.evaluate(()=>{
      const index=window.__CHART_GROUPS__.findIndex(g=>g.comparison_purpose===
        "clinical_question_descriptive"&&g.rows.length===4);
      const el=document.querySelector("#kz-chart-"+index);
      el.scrollIntoView({block:"center"});
      const chart=echarts.getInstanceByDom(el),option=chart.getOption();let found;
      option.series.forEach((s,si)=>s.data.forEach((p,di)=>{
        if(p._row_id==="eff-7a82bfadf17f4066f213")found={si,di,p};
      }));
      if(!found||found.p.value!==75)throw Error("Wrong source glyph");
      const pixel=chart.convertToPixel({seriesIndex:found.si},[found.di,37.5]);
      const box=el.getBoundingClientRect(),x=box.left+pixel[0],y=box.top+pixel[1];
      window.__QA_A_SOURCE_TRIGGER__=document.elementFromPoint(x,y);
      return {x,y,id:found.p._row_id,
        aId:window.__A_COMPARISON_ROWS__[found.p._row_id].a_row_id};
    });
    await page.mouse.click(target.x,target.y,{label:"查看真实75例原文"});
    await page.waitForFunction(()=>!document.querySelector("#data-basis-panel").hidden);
    const source=await record("source");
    source.clicked=target;
    source.evidence=await page.evaluate(()=>{
      const panel=document.querySelector("#data-basis-panel");
      return {text:panel.innerText,links:[...panel.querySelectorAll("a[href]")]
        .map(a=>a.getAttribute("href"))};
    });
    if(!source.evidence.text.includes("75")||!source.evidence.text.includes("outcomeMeasures[2]")||
      !source.evidence.links.some(h=>h.includes("NCT04501679")))
      run.failures.push(width+":source mismatch");
    await page.keyboard.press("Escape");
    source.focus=await page.evaluate(()=>{
      const trigger=window.__QA_A_SOURCE_TRIGGER__,active=document.activeElement;
      return {closed:document.querySelector("#data-basis-panel").hidden,
        id:active.getAttribute("data-chart-evidence-open"),
        aId:active.getAttribute("data-evidence-row-id"),
        triggerConnected:!!trigger&&trigger.isConnected,
        triggerVisible:!!trigger&&trigger.isConnected&&trigger.checkVisibility(),
        sameTrigger:active===trigger,tag:active.tagName,
        triggerTag:trigger&&trigger.tagName,
        triggerFact:trigger&&trigger.getAttribute("data-evidence-row-id")};
    });
    if(!source.focus.closed||source.focus.aId!==target.aId||
      (source.focus.triggerConnected&&source.focus.triggerVisible&&!source.focus.sameTrigger))
      run.failures.push(width+":original-or-same-fact focus mismatch");
    await page.goto(url,{timeout:120000});
    await page.waitForFunction(()=>window.__A_COMPARISON_ROWS__&&window.__CHART_GROUPS__);
    for(const selector of ["details[data-comparison-disclosure]",
      "details[data-filter-dimension=product]"]) {
      await page.evaluate(selector=>document.querySelector(selector+" > summary")
        .scrollIntoView({block:"center"}),selector);
      if(!await page.evaluate(selector=>document.querySelector(selector).open,selector))
        await page.click(selector+" > summary");
    }
    await page.click("[data-filter-dimension=product] button[data-filter-value=Nemolizumab]");
    await page.waitForFunction(()=>JSON.parse(document.querySelector("#full-study-comparison")
      .dataset.displayedRowIds||"[]").length===4);
    await page.click("details[data-comparison-disclosure] > summary");
    const filtered=await record("filtered");
    if(filtered.displayedIds.length!==4||filtered.groups.length!==1)
      run.failures.push(width+":filtered graph mismatch");
  }
  run.state=run.failures.length?"FAILED_NOT_ACCEPTED":"BOUNDED_A_QUERY_SOURCE_FOCUS_PASS";
}catch(error){run.state="FAILED_NOT_ACCEPTED";run.error=String(error);throw error;}
finally{await fs.writeFile(path.join(out,"actual.json"),JSON.stringify(run,null,2));}
console.log({state:run.state,states:run.states.length,failures:run.failures});
if(run.failures.length)throw Error(run.failures.join("; "));
