// Actual committed B31 via the existing editor; no clinical save or source writes.
const fs=await import("node:fs/promises"),crypto=await import("node:crypto");
const root=globalThis.CI_WORKFLOW_ROOT,port=Number(globalThis.CI_WORKFLOW_EDITOR_PORT);
if(!root||!Number.isSafeInteger(port))throw new Error("Explicit English root/owned editor required");
const bytes=await fs.readFile(root+"/.artifacts/1007-b-disclosure-current31-v1/verified.json");
const current=JSON.parse(bytes),out=root+"/.artifacts/1007-b-current31-native-qa-v1";
if(current.revision!==31||current.reports.B!==31||current.facts_unchanged!==1505)
 throw new Error("B31 committed proof required");
await fs.mkdir(out);
const page=(await taskSpace(2)).page("p1");
const question="efficacy::q-pruritus-nrs-ge4-improvement";
const base=`http://127.0.0.1:${port}/reports/${current.generation}/B/overview.html`;
const run={state:"RUNNING_NOT_ACCEPTED",generation:current.generation,revision:31,
 rebuild_proof_sha256:crypto.createHash("sha256").update(bytes).digest("hex"),
 states:[],failures:[],source_current_writes:0,owner_pixels:"PENDING",
 limits:"B31 current native reading/filter/config; not all pages/hosts/clinical/RC"};
async function ready(){await page.waitForFunction(()=>document.fonts.status==="loaded"&&
 document.querySelector("#full-study-comparison table tbody tr"),undefined,{timeout:120000});
 await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));}
async function inspect(label){const m=await page.evaluate(()=>{
 const h=document.querySelector("#full-study-comparison"),r=document.querySelector(".kz-b-filters");
 const edit=JSON.parse(document.querySelector("#ci-current-edit").textContent);
 return {width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth+1,
  generation:edit.generation,revision:document.body.dataset.currentRevision,
  question:JSON.parse(h.dataset.questionRowIds).sort(),
  displayed:JSON.parse(h.dataset.displayedRowIds).sort(),
  chartIds:[...new Set(window.__CHART_GROUPS__.flatMap(g=>g.rows.map(r=>r.row_id)))].sort(),
  visible:[...h.querySelectorAll("tbody tr")].filter(n=>getComputedStyle(n).display!=="none").length,
  rows:h.querySelectorAll("tbody tr").length,
  filter:{height:r.getBoundingClientRect().height,scrollTop:r.scrollTop,font:getComputedStyle(r).fontSize},
  unmatched:Number(h.querySelector("[data-comparison-unmatched-count]").textContent)};});
 if(m.overflow||m.generation!==run.generation||m.revision!=="31")run.failures.push(label+" current identity/overflow");
 if(JSON.stringify(m.question)!==JSON.stringify(m.displayed)||
 JSON.stringify(m.question)!==JSON.stringify(m.chartIds))run.failures.push(label+" query mismatch");
 if(label==="filtered"?(m.question.length!==2||m.visible!==1):
 (m.question.length!==32||m.visible!==3||m.rows!==46||m.unmatched!==43))run.failures.push(label+" membership");
 run.states.push({label,...m});await fs.writeFile(out+"/actual.json",JSON.stringify(run,null,2));return m;}
try{
 for(const width of [1440,1600,1920,2560]){
  await page.cdp("Emulation.setDeviceMetricsOverride",{width,height:1000,deviceScaleFactor:1,mobile:false});
  await page.goto(base+"?view=comparison&cmp="+encodeURIComponent(question),{timeout:120000});await ready();
  await inspect("matched");await page.screenshot({path:out+`/B-matched-${width}.png`});
  await page.click("#kz-filter-panel > summary");await ready();
  await page.focus('.kz-b-filters[role="region"]');await page.keyboard.press("PageDown");
  await page.waitForFunction(()=>document.querySelector(".kz-b-filters").scrollTop>0,undefined,{timeout:5000});
  const opened=await inspect("expanded-filter");
  if(opened.filter.height>421||opened.filter.font!=="16px")run.failures.push("filter geometry");
  await page.click('button[data-filter-dimension="trial"][data-filter-value="nct04501666"]');await ready();
  await inspect("filtered");await page.screenshot({path:out+`/B-filtered-${width}.png`});
  await page.click('button[data-filter-dimension="trial"][data-filter-value="nct04501666"]');await ready();
  await page.click("#kz-filter-panel > summary");await ready();
  const restored=await inspect("restored"),id=restored.question[0];
  const trigger=`#full-study-comparison [data-evidence-open="${id}"]`;
  await page.click(trigger);await page.waitForFunction(()=>!document.querySelector("#kz-evidence-drawer").hidden);
  const text=await page.evaluate(()=>document.querySelector("#kz-evidence-drawer").innerText);
  await page.screenshot({path:out+`/B-source-${width}.png`});await page.keyboard.press("Escape");
  if(!text.includes("原文定位")||!(await page.evaluate(s=>document.activeElement.matches(s),trigger)))
   run.failures.push("source/Esc focus");
 }
 async function controls(){await page.waitForSelector(".kz-personal-view",{state:"attached",timeout:120000});
  const shells=await page.evaluate(()=>{const a=[];for(let n=document.querySelector(".kz-personal-view");n;n=n.parentElement)
   if(n.tagName==="DETAILS")a.unshift({className:n.className,open:n.open});return a;});
  for(const s of shells.filter(s=>!s.open))await page.click(`details[class="${s.className}"] > summary`);
  await page.waitForSelector(".kz-personal-view",{state:"visible"});}
 await page.goto(base+"?view=comparison&cmp="+encodeURIComponent(question),{timeout:120000});await ready();await controls();
 const download=page.waitForEvent("download",{timeout:30000});
 await page.click(".kz-personal-view button >> nth=0");
 const file=out+"/personal-view-B.json";await(await download).saveAs(file);
 const config=JSON.parse(await fs.readFile(file));
 if(config.selections[0].revision!==31||config.selections[0].report!=="B")throw new Error("Wrong B config identity");
 await page.goto(base+"?view=comparison&cmp="+encodeURIComponent("efficacy::q-wi-nrs-percent-change"),{timeout:120000});await controls();
 const chooser=page.waitForFileChooser({timeout:30000});
 await page.click(".kz-personal-view button >> nth=1");await(await chooser).setFiles(file);
 await page.waitForURL(u=>u.searchParams.get("cmp")===question,{timeout:120000});await ready();
 run.personal_config={file:"personal-view-B.json",config,restored:true};
 if(run.failures.length)throw new Error(run.failures.join(";"));
 run.state="ACTUAL_CURRENT31_B_READING_AND_NATIVE_CONFIG_PASSED_OWNER_PIXELS_PENDING";
}catch(error){run.state="FAILED_NOT_ACCEPTED";run.error=String(error);throw error;}
finally{await fs.writeFile(out+"/actual.json",JSON.stringify(run,null,2));}
console.log({state:run.state,states:run.states.length,failures:run.failures});
