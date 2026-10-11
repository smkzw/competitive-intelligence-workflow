// Actual old-current versus normal preview; no save, source adoption or current switch.
const fs=await import("node:fs/promises"),crypto=await import("node:crypto");
const root=globalThis.CI_WORKFLOW_ROOT,port=Number(globalThis.CI_WORKFLOW_EDITOR_PORT);
if(!root||!Number.isSafeInteger(port))throw Error("Explicit English root/editor required");
const out=root+"/.artifacts/1007-b-scalar-records-preview-v2";
const bytes=await fs.readFile(out+"/actual.json"),render=JSON.parse(bytes);
if(render.current_writes!==0||render.facts!==1505)throw Error("Normal read-only preview required");
await fs.mkdir(out+"/qa");
const page=(await taskSpace(2)).page("p1"),question="efficacy::q-pruritus-nrs-ge4-improvement";
const suffix="?view=comparison&cmp="+encodeURIComponent(question);
const old=`http://127.0.0.1:${port}/reports/${render.source_generation}/B/overview.html`;
const preview="file://"+out+"/B/overview.html";
const run={state:"RUNNING_NOT_ACCEPTED",render_proof_sha256:crypto.createHash("sha256").update(bytes).digest("hex"),
 source_generation:render.source_generation,states:[],failures:[],owner_pixels:"PENDING",
 current_source_writes:0,limits:"One real B page family, four desktop widths; not all pages/science/current/share/RC"};
async function ready(){await page.waitForFunction(()=>document.fonts.status==="loaded"&&
 document.querySelector(".kz-b-measurement-panel"),undefined,{timeout:120000});
 await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));}
async function inspect(label){const m=await page.evaluate(()=>{
 const host=document.querySelector("#full-study-comparison");
 const largest=[...document.querySelectorAll(".kz-b-measurement-panel")].sort(
  (a,b)=>Number(b.dataset.observationCount)-Number(a.dataset.observationCount))[0];
 const cards=[...largest.querySelectorAll(".kz-chart-module__group")];
 const sizes=cards.map(c=>c.getBoundingClientRect().height).sort((a,b)=>a-b);
 return {width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth+1,
  query:JSON.parse(host.dataset.questionRowIds).sort(),
  displayed:JSON.parse(host.dataset.displayedRowIds).sort(),
  chartIds:[...new Set(window.__CHART_GROUPS__.flatMap(g=>g.rows.map(r=>r.row_id)))].sort(),
  measure:largest.dataset.measurePath,count:cards.length,panelHeight:largest.getBoundingClientRect().height,
  cardMedian:sizes[Math.floor(sizes.length/2)],scalarList:largest.classList.contains("kz-b-measurement-panel--scalar-list"),
  times:cards.map(c=>c.querySelector(".kz-b-observation-time")?.textContent||""),
  values:cards.map(c=>c.querySelector(".kz-chart-single-fact__value")?.textContent||""),
  sources:cards.map(c=>c.querySelector("[data-chart-evidence-open]")?.dataset.chartEvidenceOpen||""),
  tables:cards.filter(c=>c.querySelector(".kz-complete-table table")).length,
  valueFont:getComputedStyle(cards[0].querySelector(".kz-chart-single-fact__value")).fontSize,
  timeFont:getComputedStyle(cards[0].querySelector(".kz-b-observation-time")).fontSize,
  clipped:cards.some(c=>[...c.querySelectorAll(".kz-chart-single-fact__value,.kz-b-observation-time")]
   .some(n=>n.scrollWidth>n.clientWidth+1)),
  visibleStudies:[...host.querySelectorAll("tbody tr")].filter(n=>getComputedStyle(n).display!=="none").length};});
 if(m.overflow||m.clipped)run.failures.push(label+" clipped/overflow");
 if(JSON.stringify(m.query)!==JSON.stringify(m.displayed)||JSON.stringify(m.query)!==JSON.stringify(m.chartIds))
  run.failures.push(label+" query scope");
 if(m.valueFont!=="21px"||m.timeFont!=="16px")run.failures.push(label+" font shrink");
 run.states.push({label,...m});await fs.writeFile(out+"/qa/actual.json",JSON.stringify(run,null,2));return m;}
try{for(const width of [1440,1600,1920,2560]){
 await page.cdp("Emulation.setDeviceMetricsOverride",{width,height:1000,deviceScaleFactor:1,mobile:false});
 await page.goto(old+suffix,{timeout:120000});await ready();const baseline=await inspect("old-dense");
 await page.goto(preview+suffix,{timeout:120000});await ready();
 await fs.writeFile(out+`/qa/snapshot-${width}.txt`,await page.snapshot({scope:"full_page"}));
 const dense=await inspect("preview-dense");
 if(!dense.scalarList||dense.count!==24||dense.tables!==24||dense.query.length!==32||dense.visibleStudies!==3)
  run.failures.push("real dense membership");
 for(const field of ["measure","times","values","sources","tables","query"])
  if(JSON.stringify(dense[field])!==JSON.stringify(baseline[field]))run.failures.push("changed "+field);
 if(dense.cardMedian>baseline.cardMedian*.75||dense.panelHeight>baseline.panelHeight*.8)
  run.failures.push(width+" no actual density gain");
 await page.click('.kz-b-measurement-panel--scalar-list .kz-complete-table > summary >> nth=0');await ready();
 const expanded=await inspect("expanded-record");
 if(expanded.query.length!==32||!(await page.evaluate(()=>{
  const d=document.querySelector('.kz-b-measurement-panel--scalar-list .kz-complete-table[open]');
  return !!d&&d.innerText.includes("Week")&&!!d.querySelector("table");})))run.failures.push("full context reachability");
 await page.screenshot({path:out+`/qa/B-expanded-${width}.png`});
 await page.click('.kz-b-measurement-panel--scalar-list .kz-complete-table[open] > summary');await ready();
 const target=dense.sources[0],trigger=`[data-chart-evidence-open="${target}"]`;
 await page.click(trigger);await page.waitForFunction(()=>!document.querySelector("#kz-evidence-drawer").hidden);
 const sourceText=await page.evaluate(()=>document.querySelector("#kz-evidence-drawer").innerText);
 await page.screenshot({path:out+`/qa/B-source-${width}.png`});await page.keyboard.press("Escape");
 if(!sourceText.includes("原文定位")||!(await page.evaluate(s=>document.activeElement.matches(s),trigger)))
  run.failures.push("source/Esc actual record trigger");
 run.states.push({label:"record-source",width,fact_id:target,focus_returned:true});
 await page.screenshot({path:out+`/qa/B-dense-${width}.png`});
 await page.click("#kz-filter-panel > summary");await ready();
 await page.click('button[data-filter-dimension="trial"][data-filter-value="nct04501666"]');await ready();
 const filtered=await inspect("filtered-sparse");
 if(filtered.query.length!==2||filtered.visibleStudies!==1||filtered.scalarList)run.failures.push("filtered sparse layout/scope");
 await page.screenshot({path:out+`/qa/B-filtered-${width}.png`});
 await page.click('button[data-filter-dimension="trial"][data-filter-value="nct04501666"]');await ready();
 await page.click("#kz-filter-panel > summary");await ready();
 const restored=await inspect("restored-dense");
 if(!restored.scalarList||JSON.stringify(restored.query)!==JSON.stringify(dense.query))run.failures.push("restore dense scope");
 }
 if(run.failures.length)throw Error(run.failures.join(";"));
 run.state="SCOPED_REAL_B_SCALAR_RECORDS_PASSED_OWNER_PIXELS_PENDING";
}catch(error){run.state="FAILED_NOT_ACCEPTED";run.error=String(error);throw error;}
finally{await fs.writeFile(out+"/qa/actual.json",JSON.stringify(run,null,2));}
console.log({state:run.state,states:run.states.length,failures:run.failures});
