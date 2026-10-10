// Six moved single/joint entries, saved current views and true blocked traffic.
// Ego184 only; no profiles, cookies, storage clearing or source/current writes.
const fs=await import("node:fs/promises"),root=globalThis.CI_WORKFLOW_ROOT;
const revision=Number(globalThis.CI_WORKFLOW_QA_REVISION||19);
if(!root||!Number.isSafeInteger(revision)||revision<19)throw new Error("Explicit current required");
const out=root+`/.artifacts/1007-scoped-current${revision}-shares-v2`;
const receipt=out+"/offline-actual-v1.json";
try{await fs.access(receipt);throw new Error("Existing offline result: never overwrite/replay");}
catch(error){if(error.code!=="ENOENT")throw error;}
const verified=JSON.parse(await fs.readFile(out+"/verified.json","utf8"));
if(verified.current_revision!==revision||verified.saved_config!=="ACTUAL_DOWNLOADED_CONFIGS_BOUND")
 throw new Error("Same-version exported personal views required");
const page=(await taskSpace(184)).page("p2");
const run={revision,space:184,pages:[],failures:[],fresh_browser:false,
 storage_cleared:false,source_current_writes:0,scientific_acceptance:"NOT_RUN"};
async function probe(){return await page.evaluate(async()=>{try{
 const response=await fetch("https://clinicaltrials.gov/api/v2/version",{mode:"no-cors",cache:"no-store"});
 return{response:true,type:response.type,status:response.status,navigator_online:navigator.onLine};
}catch(error){return{response:false,error:String(error),navigator_online:navigator.onLine};}});}
async function openSource(kind,trigger){
 await page.click(trigger);const drawer=kind==="A"?"#data-basis-panel":"#kz-evidence-drawer";
 await page.waitForFunction(selector=>!document.querySelector(selector).hidden,drawer);
 const text=await page.evaluate(selector=>document.querySelector(selector).textContent,drawer);
 await page.keyboard.press("Escape");
 const focus=await page.evaluate(selector=>document.activeElement.matches(selector),trigger);
 return{text,focus};
}
try{
 await page.cdp("Emulation.setDeviceMetricsOverride",{width:1920,height:1080,deviceScaleFactor:1,mobile:false});
 await page.cdp("Network.enable",{});
 await page.goto("file://"+out+"/"+verified.exports[0].moved_root+"/打开报告.html",{timeout:120000});
 run.online_control=await probe();
 if(!run.online_control.response)throw new Error("File-origin online control failed; do not fake offline proof");
 await page.cdp("Network.emulateNetworkConditions",{offline:true,latency:0,downloadThroughput:0,uploadThroughput:0});
 run.offline_control=await probe();
 if(run.offline_control.response)throw new Error("Public traffic was not actually blocked");
 for(const archive of verified.exports){
  const tag=archive.reports.join("");const moved=out+"/"+archive.moved_root;
  const manifest=JSON.parse(await fs.readFile(moved+"/share-manifest.json","utf8"));
  for(const kind of archive.reports){
   const selected=manifest.reports[kind];
   await page.goto("file://"+moved+"/打开报告.html",{timeout:120000});
   const href=await page.evaluate(kind=>[...document.querySelectorAll("a")].find(
    a=>a.getAttribute("href")?.startsWith(kind+"/"))?.getAttribute("href"),kind);
   if(href!==selected.entry_href)throw new Error("Launcher differs from committed saved view");
   await page.click(`a[href="${href}"]`);
   await page.waitForSelector(kind==="C"?".kz-c-criteria-table":"#full-study-comparison table",{state:"visible"});
   const actual=await page.evaluate(()=>({revision:document.body.dataset.currentRevision,
    query:Object.fromEntries([...new URLSearchParams(location.search).keys()].map(
     key=>[key,new URLSearchParams(location.search).getAll(key)])),
    width:document.documentElement.scrollWidth,
    editable_service_link:!!document.querySelector('a[href^="http://127.0.0.1"]')}));
   const expectedQuery=selected.view_config.query;
   for(const key of Object.keys(expectedQuery))if(JSON.stringify(actual.query[key])!==JSON.stringify(expectedQuery[key]))
    run.failures.push(`${tag}/${kind}: saved query ${key}`);
   const traffic=await probe();
   if(actual.revision!==String(selected.report_revision)||actual.width>1920||actual.editable_service_link||traffic.response)
    run.failures.push(`${tag}/${kind}: current/offline/privacy`);
   const oldRow="eff-030c369a7ea60f719d66";
   const oldTrigger=kind==="C"?'.kz-c-criteria-table [data-evidence-open="c-nct04183335-sample-size"]':
    kind==="A"?`#full-study-comparison [data-evidence-row-id="${oldRow}"]`:
     `#full-study-comparison [data-row-id="${oldRow}"]`;
   if(kind==="C")await page.fill("#kz-c-criteria-search","样本量");
   const original=await openSource(kind,oldTrigger);
   if(!original.focus||!original.text.includes("用户清除")||!original.text.includes(kind==="C"?"151":"-48.32")||
      original.text.includes("user_cleared"))run.failures.push(`${tag}/${kind}: clear/original/focus`);
   let edited=null;
   if(kind!=="C"){
    const row="eff-b0b587971df19e9d9cde";
    const question=await page.evaluate(({kind,row})=>{
     const w=window[kind==="A"?"__A_COMPARISON_WORKSPACE__":"__B_COMPARISON_WORKSPACE__"];
     const rows=kind==="A"?window.__A_COMPARISON_ROWS__:window.__FILTER_ROWS__;
     const id=kind==="A"?Object.keys(rows).find(id=>rows[id].a_row_id===row||rows[id].row_id===row):rows.find(x=>x.id===row)?.id;
     return w.columns.find(c=>Object.values(c.cells).flat().includes(id))?.question_id;
    },{kind,row});
    if(!question)throw new Error("No real saved fact in production workspace");
    await page.selectOption(kind==="A"?"[data-a-comparison-question]":"[data-comparison-column]",question);
    const trigger=kind==="A"?`#full-study-comparison [data-evidence-row-id="${row}"]`:
      `#full-study-comparison [data-row-id="${row}"]`;
    const value=await page.evaluate(selector=>document.querySelector(selector).textContent,trigger);
    edited=await openSource(kind,trigger);edited.current=value;
    if(!value.includes("-67.5")||!edited.text.includes("用户修订")||!edited.text.includes("-67.5")||!edited.focus)
     run.failures.push(`${tag}/${kind}: restored user edit not saved/current`);
   }
   const screenshot=`offline-${tag}-${kind}-r${revision}.png`;
   await page.screenshot({path:out+"/"+screenshot});
   run.pages.push({tag,kind,actual,traffic,original,edited,screenshot});
   await fs.writeFile(receipt,JSON.stringify(run,null,2));
  }
 }
 if(run.failures.length)throw new Error(run.failures.join(";"));
 run.state="SIX_MOVED_OFFLINE_SAVED_CURRENT_ENTRIES_AND_SOURCE_EDIT_DISCLOSURES_PASSED";
}catch(error){run.state="FAILED_NOT_ACCEPTED";run.error=String(error);throw error;}
finally{
 await page.cdp("Network.emulateNetworkConditions",{offline:false,latency:0,downloadThroughput:-1,uploadThroughput:-1});
 run.network_restored=true;await fs.writeFile(receipt,JSON.stringify(run,null,2));
}
console.log(JSON.stringify({state:run.state,pages:run.pages.length,failures:run.failures}));
