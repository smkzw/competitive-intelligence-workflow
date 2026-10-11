// Three genuine current downloads/imports; not storage injection or old C9 receipts.
const fs=await import("node:fs/promises"),root=globalThis.CI_WORKFLOW_ROOT;
const port=Number(globalThis.CI_WORKFLOW_EDITOR_PORT);
if(!root||!Number.isSafeInteger(port)||port<1024)throw new Error("Explicit root/owned port required");
const verified=JSON.parse(await fs.readFile(root+"/.artifacts/1007-comparison-reading-current28-v1/verified.json"));
if(verified.revision!==28)throw new Error("Verified current28 required");
const revisions=Object.fromEntries(verified.current.reports.map(r=>[r.report,r.revision]));
const out=root+"/.artifacts/1007-current28-config-v1";await fs.mkdir(out);
const page=(await taskSpace(2)).page("p1");
const run={state:"RUNNING_NOT_ACCEPTED",revision:28,generation:verified.generation,
 space:2,configs:[],fresh_browser:false,source_current_writes:0};
async function controls(){
 await page.waitForSelector(".kz-personal-view",{state:"attached",timeout:120000});
 const shells=await page.evaluate(()=>{const result=[];
  for(let e=document.querySelector(".kz-personal-view");e;e=e.parentElement){
   if(e.tagName==="DETAILS")result.unshift({className:e.className,open:e.open});
  }return result;
 });
 for(const shell of shells.filter(e=>!e.open))await page.click(`details[class="${shell.className}"] > summary`);
 await page.waitForSelector(".kz-personal-view",{state:"visible"});
}
try{
 for(const kind of ["A","B","C"]){
  const entry=kind==="A"?"clinical-portfolio.html":"overview.html";
  const base=`http://127.0.0.1:${port}/reports/${run.generation}/${kind}/${entry}`;
  const chosen=kind==="C"?"?view=comparison":"?view=comparison&cmp=efficacy%3A%3Aq-wi-nrs-percent-change";
  await page.goto(base+chosen,{timeout:120000});await controls();
  await fs.writeFile(out+`/snapshot-${kind}.txt`,await page.snapshot());
  const download=page.waitForEvent("download",{timeout:30000});
  await page.click(".kz-personal-view button >> nth=0");
  const file=out+`/personal-view-${kind}.json`;await(await download).saveAs(file);
  const config=JSON.parse(await fs.readFile(file));
  if(config.selections[0].report!==kind||config.selections[0].revision!==revisions[kind]||
   config.selections[0].query.view?.[0]!=="comparison")throw new Error("Wrong current view download");
  const other=kind==="C"?"?view=summary":"?view=comparison&cmp=efficacy%3A%3Aq-pruritus-nrs-ge4-improvement";
  await page.goto(base+other,{timeout:120000});await controls();
  const chooser=page.waitForFileChooser({timeout:30000});
  await page.click(".kz-personal-view button >> nth=1");await(await chooser).setFiles(file);
  await page.waitForURL(url=>url.searchParams.get("view")==="comparison"&&
   (kind==="C"||url.searchParams.get("cmp")==="efficacy::q-wi-nrs-percent-change"),{timeout:120000});
  await page.waitForSelector(".kz-personal-view",{state:"attached",timeout:120000});
  const actual=await page.evaluate(()=>({revision:document.body.dataset.currentRevision,
   generation:JSON.parse(document.querySelector("#ci-current-edit").textContent).generation,
   query:location.search}));
  if(actual.revision!==String(revisions[kind])||actual.generation!==run.generation)
   throw new Error("Import reopened another generation");
  run.configs.push({kind,file:`personal-view-${kind}.json`,config,actual});
  await fs.writeFile(out+"/actual.json",JSON.stringify(run,null,2));
 }
 run.state="ACTUAL_ABC_PERSONAL_VIEW_DOWNLOAD_AND_DISTINCT_IMPORT_PASSED";
}catch(error){run.state="FAILED_NOT_ACCEPTED";run.error=String(error);throw error;}
finally{await fs.writeFile(out+"/actual.json",JSON.stringify(run,null,2));}
console.log({state:run.state,configs:run.configs.length});
