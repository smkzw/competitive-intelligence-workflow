// Same immutable B-v2 candidate; native PageDown works in Ego/macOS.
// Prior Control+End QA failure remains immutable under qa/; no product edits.
const fs=await import("node:fs/promises"),crypto=await import("node:crypto");
const root=globalThis.CI_WORKFLOW_ROOT;
if(!root)throw new Error("Explicit English root required");
const out=root+"/.artifacts/1007-b-unmatched-study-preview-v2";
const renderBytes=await fs.readFile(out+"/actual.json"),render=JSON.parse(renderBytes);
if(render.facts!==1505||render.current_writes!==0)throw new Error("Normal read-only preview required");
await fs.mkdir(out+"/qa-v3");
const page=(await taskSpace(2)).page("p1");
const run={state:"RUNNING_NOT_ACCEPTED",source_generation:render.source_generation,
 render_proof_sha256:crypto.createHash("sha256").update(renderBytes).digest("hex"),
 states:[],failures:[],owner_pixels:"PENDING",current_writes:0,
 limits:"One actual B page/four widths; not all-page, share, science or RC acceptance"};
async function ready(){await page.waitForFunction(()=>document.fonts.status==="loaded"&&
 document.querySelector("#full-study-comparison table tbody tr"),undefined,{timeout:120000});
 await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));}
async function inspect(label){const m=await page.evaluate(()=>{
 const h=document.querySelector("#full-study-comparison"),r=document.querySelector(".kz-b-filters");
 const q=JSON.parse(h.dataset.questionRowIds).sort();
 return {width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth,
  query:q,displayed:JSON.parse(h.dataset.displayedRowIds).sort(),
  chartIds:[...new Set(window.__CHART_GROUPS__.flatMap(g=>g.rows.map(r=>r.row_id)))].sort(),
  allStudies:window.__B_COMPARISON_WORKSPACE__.study_ids.length,
  rows:h.querySelectorAll("tbody tr").length,
  visible:[...h.querySelectorAll("tbody tr")].filter(r=>getComputedStyle(r).display!=="none").length,
  filter:{height:r.getBoundingClientRect().height,width:r.getBoundingClientRect().width,
   scrollHeight:r.scrollHeight,scrollTop:r.scrollTop,clientHeight:r.clientHeight,
   overflow:getComputedStyle(r).overflowY,font:getComputedStyle(r).fontSize},
  matrixTop:h.getBoundingClientRect().top+scrollY};});
 if(m.scrollWidth>m.width+1)run.failures.push(label+" horizontal overflow");
 if(JSON.stringify(m.query)!==JSON.stringify(m.displayed)||
 JSON.stringify(m.query)!==JSON.stringify(m.chartIds))run.failures.push(label+" scope mismatch");
 run.states.push({label,...m});await fs.writeFile(out+"/qa-v3/actual.json",JSON.stringify(run,null,2));
 return m;}
try{for(const width of [1440,1600,1920,2560]){
 await page.cdp("Emulation.setDeviceMetricsOverride",{width,height:1000,deviceScaleFactor:1,mobile:false});
 await page.goto("file://"+out+"/B/overview.html?view=comparison&cmp="+
 encodeURIComponent("efficacy::q-pruritus-nrs-ge4-improvement"),{timeout:120000});await ready();
 const initial=await inspect("matched");
 if(initial.visible!==3||initial.rows!==46||initial.query.length!==32)run.failures.push("initial membership");
 await page.screenshot({path:out+`/qa-v3/B-matched-${width}.png`});
 await page.click("[data-comparison-unmatched-toggle]");await ready();
 if((await inspect("all-related")).visible!==46)run.failures.push("native disclosure");
 await page.keyboard.press("Space");await ready();
 if((await inspect("keyboard-collapse")).visible!==3)run.failures.push("native Space collapse");
 await page.click("#kz-filter-panel > summary");await ready();
 const open=await inspect("expanded-filter");
 if(open.filter.height>421||open.filter.height<100||open.filter.overflow!=="auto"||
 open.filter.width<width*.5||open.filter.font!=="16px")run.failures.push("native filter geometry");
 if(open.matrixTop>900)run.failures.push("matrix buried by filter");
 await fs.writeFile(out+`/qa-v3/snapshot-filter-${width}.txt`,await page.snapshot());
 await page.screenshot({path:out+`/qa-v3/B-filter-${width}.png`});
 await page.focus('.kz-b-filters[role="region"]');await page.keyboard.press("PageDown");
 await page.waitForFunction(()=>document.querySelector(".kz-b-filters").scrollTop>0,
  undefined,{timeout:5000});
 const scrolled=await inspect("keyboard-filter-end");
 if(scrolled.filter.scrollHeight>scrolled.filter.clientHeight+1&&scrolled.filter.scrollTop<=0)
  run.failures.push("keyboard scroll region inaccessible");
 const last=await page.evaluate(()=>[...document.querySelectorAll('button[data-filter-dimension="trial"]')].at(-1).dataset.filterValue);
 await page.click(`button[data-filter-dimension="trial"][data-filter-value="${last}"]`);
 if(!(await page.evaluate(v=>document.querySelector(`button[data-filter-dimension="trial"][data-filter-value="${v}"]`).getAttribute("aria-pressed")==="true",last)))
  run.failures.push("last study not actionable");
 await page.click(`button[data-filter-dimension="trial"][data-filter-value="${last}"]`);await ready();
 await page.click('button[data-filter-dimension="trial"][data-filter-value="nct04501666"]');await ready();
 const filtered=await inspect("filtered");
 if(filtered.query.length!==2||filtered.visible!==1)run.failures.push("real trial filter");
 await page.screenshot({path:out+`/qa-v3/B-filtered-${width}.png`});
 await page.click('button[data-filter-dimension="trial"][data-filter-value="nct04501666"]');await ready();
 await page.click("#kz-filter-panel > summary");await ready();
 const restored=await inspect("restored");
 if(restored.query.length!==32||restored.visible!==3)run.failures.push("restore membership");
 const id=restored.query[0],trigger=`#full-study-comparison [data-evidence-open="${id}"]`;
 await page.click(trigger);await page.waitForFunction(()=>!document.querySelector("#kz-evidence-drawer").hidden);
 const original=await page.evaluate(()=>document.querySelector("#kz-evidence-drawer").innerText);
 await page.screenshot({path:out+`/qa-v3/B-source-${width}.png`});await page.keyboard.press("Escape");
 if(!original.includes("原文定位")||!(await page.evaluate(s=>document.activeElement.matches(s),trigger)))
  run.failures.push("source/Esc trigger");
 }
 if(run.failures.length)throw new Error(run.failures.join(";"));
 run.state="SCOPED_NATIVE_FILTER_DISCLOSURE_PASSED_OWNER_PIXELS_PENDING";
}catch(error){run.state="FAILED_NOT_ACCEPTED";run.error=String(error);throw error;}
finally{await fs.writeFile(out+"/qa-v3/actual.json",JSON.stringify(run,null,2));}
console.log({state:run.state,states:run.states.length,failures:run.failures});
