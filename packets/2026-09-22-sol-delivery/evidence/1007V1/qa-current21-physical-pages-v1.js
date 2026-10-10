// One frozen candidate, all real HTML pages/four desktop widths. Structural
// traversal only; screenshots and scientific/subjective acceptance are separate.
// Ego184/p2, no profiles/storage reads, saves, source adoption or rebuilds.
const fs=await import("node:fs/promises"),crypto=await import("node:crypto");
const root=globalThis.CI_WORKFLOW_ROOT;
if(!root)throw new Error("Explicit English project required");
const generation="67b793ef865d035092fb27dfeaec8ce87cfaa0e97edb3631724eb07d55518310";
const project=root+"/.artifacts/1007-abc-current-integration-v1/working/project";
const out=root+"/.artifacts/1007-current21-physical-pages-v1";
await fs.mkdir(out); // Existing attempt must never be overwritten/replayed.
const currentBytes=await fs.readFile(project+"/reports/generations/"+generation+".json");
const current=JSON.parse(currentBytes);
if(crypto.createHash("sha256").update(currentBytes).digest("hex")!==generation||current.revision!==21)
 throw new Error("Frozen current generation mismatch");
const expected={A:49,B:104,C:16},queue=[];
for(const report of current.reports){
 const pages=Object.keys(report.file_hashes).filter(p=>p.endsWith(".html"));
 if(pages.length!==expected[report.report])throw new Error("Real manifest page set changed");
 for(const path of pages){
  if(path.includes("..")||path.startsWith("/"))throw new Error("Unsafe manifest path");
  const bytes=await fs.readFile(project+"/"+report.site_relative_path+"/"+path);
  if(crypto.createHash("sha256").update(bytes).digest("hex")!==report.file_hashes[path])
   throw new Error("Actual page bytes differ from current");
  queue.push({report:report.report,revision:report.revision,path,sha256:report.file_hashes[path]});
 }
}
const widths=[1440,1600,1920,2560],page=(await taskSpace(184)).page("p2");
const run={state:"IN_PROGRESS_NOT_ACCEPTED",generation,pages:expected,total:queue.length*4,
 actual:[],failures:[],browser:"Ego Lite184",fresh_profile:false,source_writes:0,
 saves:0,renders:0,visual_acceptance:"NOT_RUN",scientific_acceptance:"NOT_RUN"};
const recipe=globalThis.CI_WORKFLOW_RECIPE_PATH;
if(recipe)run.recipe_sha256=crypto.createHash("sha256").update(await fs.readFile(recipe)).digest("hex");
try{
 await page.goto("http://127.0.0.1:65033/",{timeout:120000});
 for(const width of widths){
  await page.cdp("Emulation.setDeviceMetricsOverride",{width,height:900,deviceScaleFactor:1,mobile:false});
  for(const item of queue){
   const url="http://127.0.0.1:65033/reports/"+generation+"/"+item.report+"/"+
    item.path.split("/").map(encodeURIComponent).join("/");
   await page.goto(url,{timeout:120000});
   await page.waitForFunction(()=>document.readyState==="complete"&&document.fonts.status==="loaded");
   await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve(true)))));
   const actual=await page.evaluate(()=>({
    title:document.title,revision:document.body.dataset.currentRevision,
    width:innerWidth,document_width:document.documentElement.scrollWidth,
    body_font:Number.parseFloat(getComputedStyle(document.body).fontSize),
    main_present:!!document.querySelector("main"),
    visible_canvas:[...document.querySelectorAll("canvas")].map(c=>({
     width:c.getBoundingClientRect().width,height:c.getBoundingClientRect().height,
     pixels_width:c.width,pixels_height:c.height})).filter(c=>c.width>0&&c.height>0),
    engineering_state_text:document.body.innerText.includes("user_cleared"),
   }));
   const record={...item,width,actual};
   if(actual.revision!==String(item.revision)||actual.width!==width||
      actual.document_width>width+1||actual.body_font<16||!actual.main_present||
      actual.engineering_state_text||actual.visible_canvas.some(c=>!c.pixels_width||!c.pixels_height)){
    run.failures.push({report:item.report,path:item.path,width,actual});
   }
   if(["overview.html","efficacy.html","baseline-demographics.html",
       "sample-analysis-statistics.html"].includes(item.path)){
    record.screenshot=`${item.report}-${width}-${item.path.replace(".html","")}.png`;
    await page.screenshot({path:out+"/"+record.screenshot});
   }
   run.actual.push(record);
   await fs.writeFile(out+"/actual.json",JSON.stringify(run,null,2));
  }
  console.log(JSON.stringify({width,actual:run.actual.length,failures:run.failures.length}));
 }
 run.state=run.failures.length?"STRUCTURAL_FAILURES_NOT_ACCEPTED":"ALL169_PHYSICAL_PAGES_FOUR_WIDTHS_STRUCTURAL_PASSED_NOT_VISUAL_ACCEPTANCE";
 if(run.failures.length)throw new Error("Structural failures retained; do not relabel PASS");
}catch(error){run.error=String(error);run.state="FAILED_OR_INCOMPLETE_NOT_ACCEPTED";throw error;}
finally{
 run.not_run=run.total-run.actual.length;
 await fs.writeFile(out+"/actual.json",JSON.stringify(run,null,2));
}
console.log(JSON.stringify({state:run.state,actual:run.actual.length,not_run:run.not_run}));
