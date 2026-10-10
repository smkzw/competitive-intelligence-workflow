// Three normal downloaded/imported personal views, one actual committed bundle.
const fs=await import("node:fs/promises"),root=globalThis.CI_WORKFLOW_ROOT;
if(!root)throw new Error("Explicit English root required");
const revision=Number(globalThis.CI_WORKFLOW_QA_REVISION||18);
if(!Number.isSafeInteger(revision)||revision<18)throw new Error("Explicit committed revision required");
const proof=globalThis.CI_WORKFLOW_QA_PROOF||"/.artifacts/1007-current14-real-ab-edit-v1/step-4-verified.json";
if(!/^\/\.artifacts\/[a-z0-9-/]+\.json$/.test(proof)||proof.includes(".."))throw new Error("Explicit local proof required");
const verified=JSON.parse(await fs.readFile(root+proof,"utf8"));
if(verified.revision!==revision)throw new Error("Completed current operation required");
const out=root+`/.artifacts/1007-current${revision}-config-v1`;await fs.mkdir(out);
const page=(await taskSpace(184)).page("p2");
const run={revision,generation:verified.generation,space:184,configs:[],fresh_browser:false};
async function openControls(kind){
 const ancestors=await page.evaluate(()=>{const list=[];for(let el=document.querySelector(".kz-personal-view");el;el=el.parentElement)
  if(el.tagName==="DETAILS")list.unshift({className:el.className,open:el.open});return list;});
 if(kind!=="A"&&ancestors.some(x=>/filter-panel/.test(x.className)))throw new Error("Config nested in legacy filter");
 for(const item of ancestors.filter(x=>!x.open))await page.click(`details[class="${item.className}"] > summary`);
 await page.waitForSelector(".kz-personal-view",{state:"visible"});
}
try{
 await page.goto("http://127.0.0.1:65033/",{timeout:120000});
 for(const kind of ["A","B","C"]){
  const entry=kind==="A"?"clinical-portfolio.html":"overview.html";
  const base=`http://127.0.0.1:65033/reports/${run.generation}/${kind}/${entry}`;
  const chosen=kind==="C"?"?view=comparison":"?view=comparison&cmp=efficacy%3A%3Aq-wi-nrs-percent-change";
  await page.goto(base+chosen,{timeout:120000});await openControls(kind);
  const download=page.waitForEvent("download",{timeout:30000});
  await page.click(".kz-personal-view button >> nth=0");
  const file=out+`/personal-view-${kind}.json`;await(await download).saveAs(file);
  const config=JSON.parse(await fs.readFile(file,"utf8"));
  const reportRevision=kind==="C"?9:revision;
  if(config.selections[0].report!==kind||config.selections[0].revision!==reportRevision||
    config.selections[0].query.view?.[0]!=="comparison")throw new Error("Not the saved current task view");
  await page.goto(base+(kind==="C"?"?view=summary":"?view=comparison&cmp=efficacy%3A%3Aq-pruritus-nrs-ge4-improvement"),{timeout:120000});
  await openControls(kind);const chooser=page.waitForFileChooser({timeout:30000});
  await page.click(".kz-personal-view button >> nth=1");await(await chooser).setFiles(file);
  await page.waitForURL(url=>url.searchParams.get("view")==="comparison"&&
    (kind==="C"||url.searchParams.get("cmp")==="efficacy::q-wi-nrs-percent-change"),{timeout:30000});
  const actual=await page.evaluate(()=>({report_revision:document.body.dataset.currentRevision,
    generation:JSON.parse(document.querySelector("#ci-current-edit").textContent).generation,
    query:location.search}));
  if(actual.report_revision!==String(reportRevision)||actual.generation!==run.generation)
    throw new Error("Imported view reopened another committed bundle");
  run.configs.push({kind,config,file:`personal-view-${kind}.json`,actual});
  await fs.writeFile(out+"/actual.json",JSON.stringify(run,null,2));
 }
 run.state="ACTUAL_ABC_PERSONAL_VIEW_DOWNLOAD_AND_DISTINCT_IMPORT_PASSED";
}catch(error){run.state="FAILED_NOT_ACCEPTED";run.error=String(error);throw error;}
finally{await fs.writeFile(out+"/actual.json",JSON.stringify(run,null,2));}
console.log(JSON.stringify({state:run.state,configs:run.configs.length}));
