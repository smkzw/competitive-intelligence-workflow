// Genuine moved current32 shares in a authorized dedicated Ego profile created for current28.
// No imports, logins, cookie/cache/storage clears, source/current writes or old receipts.
const fs=await import("node:fs/promises"),crypto=await import("node:crypto");
const root=globalThis.CI_WORKFLOW_ROOT;
if(!root)throw new Error("Explicit English root required");
const out=root+"/.artifacts/1007-current32-shares-v1";
const receipt=out+"/offline-actual-v1.json";
try{await fs.access(receipt);throw new Error("Existing result; inspect partial state, no overwrite/replay");}
catch(error){if(error.code!=="ENOENT")throw error;}
const bytes=await fs.readFile(out+"/verified.json"),verified=JSON.parse(bytes);
if(verified.current_revision!==32||verified.exports.length!==2||
 verified.saved_config!=="ACTUAL_DOWNLOADED_CONFIGS_BOUND")throw new Error("Same-current four exports required");
const page=(await taskSpace(11)).page("p1");
const run={revision:32,profile_id:"Profile 3",space:11,pages:[],failures:[],
 fresh_browser:false,profile_created_for_this_candidate:false,profile_reused_from_current28:true,storage_cleared:false,
 no_import_or_login:true,source_current_writes:0,scientific_acceptance:"NOT_RUN",
 export_proof_sha256:crypto.createHash("sha256").update(bytes).digest("hex")};
async function persist(){await fs.writeFile(receipt,JSON.stringify(run,null,2));}
async function probe(){return await page.evaluate(async()=>{try{
 const r=await fetch("https://clinicaltrials.gov/api/v2/version",{mode:"no-cors",cache:"no-store"});
 return{response:true,type:r.type,status:r.status,navigator_online:navigator.onLine};
}catch(error){return{response:false,error:String(error),navigator_online:navigator.onLine};}});}
async function source(kind,trigger){
 await page.click(trigger);const drawer=kind==="A"?"#data-basis-panel":"#kz-evidence-drawer";
 await page.waitForFunction(s=>!document.querySelector(s).hidden,drawer);
 const text=await page.evaluate(s=>document.querySelector(s).textContent,drawer);
 await page.keyboard.press("Escape");
 return{text,focus:await page.evaluate(s=>document.activeElement.matches(s),trigger)};
}
async function selectFactQuestion(kind,row){
 const question=await page.evaluate(({kind,row})=>{
  const w=window[kind==="A"?"__A_COMPARISON_WORKSPACE__":"__B_COMPARISON_WORKSPACE__"];
  const rows=kind==="A"?window.__A_COMPARISON_ROWS__:window.__FILTER_ROWS__;
  const id=kind==="A"?Object.keys(rows).find(id=>rows[id].a_row_id===row||rows[id].row_id===row):
   rows.find(x=>x.id===row)?.id;
  return w.columns.find(c=>Object.values(c.cells).flat().includes(id))?.question_id;
 },{kind,row});
 if(!question)throw new Error("No saved fact in actual production workspace");
 await page.selectOption(kind==="A"?"[data-a-comparison-question]":"[data-comparison-column]",question);
}
try{
 await page.cdp("Emulation.setDeviceMetricsOverride",{width:1920,height:1080,deviceScaleFactor:1,mobile:false});
 await page.cdp("Network.enable",{});
 await page.goto("file://"+out+"/"+verified.exports[0].moved_root+"/打开报告.html",{timeout:120000});
 run.online_control=await probe();await persist();
 if(!run.online_control.response)throw new Error("Actual file-origin online control failed");
 await page.cdp("Network.emulateNetworkConditions",{offline:true,latency:0,downloadThroughput:0,uploadThroughput:0});
 run.offline_control=await probe();await persist();
 if(run.offline_control.response)throw new Error("Public traffic not actually blocked");
 for(const archive of verified.exports){
  const tag=archive.reports.join(""),moved=out+"/"+archive.moved_root;
  const manifestBytes=await fs.readFile(moved+"/share-manifest.json");
  if(crypto.createHash("sha256").update(manifestBytes).digest("hex")!==archive.manifest_sha256)
   throw new Error("Moved manifest changed");
  const manifest=JSON.parse(manifestBytes);
  for(const kind of archive.reports){
   const selected=manifest.reports[kind];
   await page.goto("file://"+moved+"/打开报告.html",{timeout:120000});
   const href=await page.evaluate(k=>[...document.querySelectorAll("a")].find(
    a=>a.getAttribute("href")?.startsWith(k+"/"))?.getAttribute("href"),kind);
   if(href!==selected.entry_href)throw new Error("Launcher is not the saved committed view");
   await page.click(`a[href="${href}"]`);
   await page.waitForSelector(kind==="C"?".kz-c-criteria-table":"#full-study-comparison table",{state:"visible"});
   await page.waitForFunction(()=>document.fonts.status==="loaded");
   await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
   const actual=await page.evaluate(()=>({revision:document.body.dataset.currentRevision,
    query:Object.fromEntries([...new URLSearchParams(location.search).keys()].map(
     k=>[k,new URLSearchParams(location.search).getAll(k)])),
    width:document.documentElement.scrollWidth,
    editor_link:!!document.querySelector('a[href^="http://127.0.0.1"]')}));
   for(const key of Object.keys(selected.view_config.query))
    if(JSON.stringify(actual.query[key])!==JSON.stringify(selected.view_config.query[key]))
     run.failures.push(`${tag}/${kind}: saved query ${key}`);
   const traffic=await probe();
   if(actual.revision!==String(selected.report_revision)||actual.width>1921||actual.editor_link||traffic.response)
    run.failures.push(`${tag}/${kind}: revision/offline/privacy`);
   let reading=null;
   if(kind==="B"){
    await page.waitForSelector(".kz-b-study-panel",{state:"visible"});
    reading=await page.evaluate(()=>({
     panels:document.querySelectorAll(".kz-b-study-panel").length,
     cards:document.querySelectorAll("[data-comparison-compact]").length,
     scalar_records:document.querySelectorAll(".kz-b-measurement-panel--scalar-list [data-comparison-compact]").length,
     values:[...document.querySelectorAll(".kz-chart-single-fact__value")].map(e=>e.textContent)}));
    reading.visibleStudyRows=await page.evaluate(()=>[...document.querySelectorAll("#full-study-comparison tbody tr")].filter(e=>getComputedStyle(e).display!=="none").length);
    if(reading.panels!==3||reading.cards!==32||reading.scalar_records!==24||reading.visibleStudyRows!==3)run.failures.push(`${tag}/B: saved new display scope`);
    await page.evaluate(()=>document.querySelector("#kz-chart-module").scrollIntoView({block:"start"}));
    await page.screenshot({path:out+`/offline-${tag}-B-default-panels-r32.png`});
   }
   const oldRow="eff-030c369a7ea60f719d66";
   if(kind!=="C")await selectFactQuestion(kind,oldRow);
   const trigger=kind==="C"?'.kz-c-criteria-table [data-evidence-open="c-nct04183335-sample-size"]':
    kind==="A"?`#full-study-comparison [data-evidence-row-id="${oldRow}"]`:
     `#full-study-comparison [data-row-id="${oldRow}"]`;
   if(kind==="C")await page.fill("#kz-c-criteria-search","样本量");
   const original=await source(kind,trigger);
   if(!original.focus||!original.text.includes("用户清除")||
    !original.text.includes(kind==="C"?"151":"-48.32")||original.text.includes("user_cleared"))
    run.failures.push(`${tag}/${kind}: clear/original/focus`);
   let edited=null;
   if(kind!=="C"){
    const row="eff-b0b587971df19e9d9cde";
    await selectFactQuestion(kind,row);
    const target=kind==="A"?`#full-study-comparison [data-evidence-row-id="${row}"]`:
     `#full-study-comparison [data-row-id="${row}"]`;
    const value=await page.evaluate(s=>document.querySelector(s).textContent,target);
    edited=await source(kind,target);edited.current=value;
    if(!value.includes("-67.5")||!edited.text.includes("用户修订")||
     !edited.text.includes("-67.5")||!edited.focus)run.failures.push(`${tag}/${kind}: saved edit/focus`);
   }
   const screenshot=`offline-${tag}-${kind}-r32.png`;
   await page.screenshot({path:out+"/"+screenshot});
   run.pages.push({tag,kind,actual,traffic,reading,original,edited,screenshot});await persist();
  }
 }
 if(run.pages.length!==4||run.failures.length)throw new Error(run.failures.join(";")||"Incomplete changed B and joint four-entry run");
 run.state="FOUR_MOVED_OFFLINE_CURRENT32_ENTRIES_DEDICATED_PROFILE_AND_SOURCE_DISCLOSURES_PASSED";
}catch(error){run.state="FAILED_NOT_ACCEPTED";run.error=String(error);throw error;}
finally{
 await page.cdp("Network.emulateNetworkConditions",{offline:false,latency:0,downloadThroughput:-1,uploadThroughput:-1});
 run.network_restored=true;await persist();
}
console.log({state:run.state,pages:run.pages.length,failures:run.failures});
