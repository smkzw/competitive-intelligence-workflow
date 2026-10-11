// Existing Ego2/p1, ordinary current32 A/B; original instruments stay immutable.
const fs=await import("node:fs/promises"),path=await import("node:path");
const crypto=await import("node:crypto");
const candidateRelative=".artifacts/1007-ab-shared-question-preview-v4";
const recipes=path.join(workflowRoot,"packets/2026-09-22-sol-delivery/evidence/1007V1");
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
async function frozen(name,digest){
 const raw=await fs.readFile(path.join(recipes,name));
 if(crypto.createHash("sha256").update(raw).digest("hex")!==digest)
  throw Error("Original recipe changed: "+name);
 return raw.toString();
}
const rawB=await frozen("qa-b-primary-matrix-preview-v1.js",
 "ee37c4f5709bfa27e5c5aea1484fb6c5275545d8d90b760aa831649cd3f9275e");
await new AsyncFunction("taskSpace","workflowRoot",rawB.replaceAll(
 ".artifacts/1007-b-primary-matrix-preview-v1",candidateRelative)
 .replace("actual.pages !== 104","actual.reports.B.pages !== 104"))(taskSpace,workflowRoot);
const paired=await fs.readFile(path.join(recipes,"qa-b-question-paired-reading-v2.js"),"utf8");
await new AsyncFunction("taskSpace","workflowRoot","candidateRelative",paired)(
 taskSpace,workflowRoot,candidateRelative);
let rawA=await frozen("qa-a-shared-question-current-v1.js",
 "d2aae27911cf63c368ba896d87ff7abc54221cc799e4b4ff4c402f2c1457f1ac");
rawA=rawA.replaceAll(".artifacts/1007-ab-shared-question-preview-v3",candidateRelative)
 .replace('candidateRelative, "a-qa-v2"','candidateRelative, "a-qa"')
 .replace("window.__QA_A_SOURCE_TRIGGER__=document.elementFromPoint(x,y);",
 "const original=window.__A_COMPARISON_EVIDENCE__;"+
 "window.__A_COMPARISON_EVIDENCE__=function(id,trigger){"+
 "window.__QA_A_SOURCE_TRIGGER__=trigger;return original(id,trigger);};");
await new AsyncFunction("taskSpace","workflowRoot",rawA)(taskSpace,workflowRoot);

const page=(await taskSpace(2)).page("p1");
const result={state:"RUNNING_NOT_ACCEPTED",states:[],failures:[],currentWrites:0};
const out=path.join(workflowRoot,candidateRelative,"shared-reading-qa");
await fs.mkdir(out);
try{
 for(const report of ["A","B"])for(const width of [1440,1600,1920,2560]){
  await page.cdp("Emulation.setDeviceMetricsOverride",{width,height:width===2560?1440:
   width===1920?1080:900,deviceScaleFactor:1,mobile:false});
  await page.goto("file://"+path.join(workflowRoot,candidateRelative,report,
   report==="A"?"clinical-portfolio.html":"overview.html")+
   "?view=comparison&cmp=efficacy%3A%3Aq-pruritus-nrs-ge4-improvement");
  await page.waitForFunction(()=>window.__CHART_GROUPS__&&
   window.__CHART_GROUPS__.some(g=>g.comparison_purpose==="clinical_question_descriptive"));
  const measured=await page.evaluate(()=>{
   const groups=window.__CHART_GROUPS__.filter(g=>
    g.comparison_purpose==="clinical_question_descriptive");
   return {width:innerWidth,
    units:[...document.querySelectorAll(".kz-chart-group__unit")].map(n=>n.textContent),
    groups:groups.map(g=>({rows:g.rows.map(r=>({id:r.row_id,study:r.trial_id,
     product:r.product_id,time:r.actual_timepoint,value:r.value})),crossTrial:g.cross_trial})),
    hits:[...document.querySelectorAll(".kz-chart-evidence-hit")].map(n=>{
     const s=getComputedStyle(n),box=n.getBoundingClientRect();
     return {position:s.position,background:s.backgroundColor,width:box.width,height:box.height,
      id:n.getAttribute("data-chart-evidence-open")};})};
  });
  result.states.push({report,...measured});
  if(measured.units.some(t=>t.includes("percentage of participants")))
   result.failures.push(report+width+":duplicate raw unit");
  if(!measured.hits.length||measured.hits.some(h=>h.position!=="absolute"||
   h.background!=="rgba(0, 0, 0, 0)"||h.width!==32||h.height!==32))
   result.failures.push(report+width+":source targets rendered as empty default buttons");
  for(const group of measured.groups){
   if(group.crossTrial)result.failures.push(report+width+":manufactured scientific frame");
   const byIdentity=new Map();
   for(const row of group.rows){
    const id=row.product+"|"+row.study;
    if(!byIdentity.has(id))byIdentity.set(id,[]);
    byIdentity.get(id).push(row.time);
   }
   for(const times of byIdentity.values())if(times.length===2&&
    times.join("|")!=="Baseline, Week 4|Baseline, Week 16")
    result.failures.push(report+width+":wrong posted visit order:"+times.join("|"));
  }
  await page.screenshot({path:path.join(out,report+"-dense-"+width+".png")});
 }
 result.state=result.failures.length?"FAILED_NOT_ACCEPTED":"BOUNDED_SHARED_CHART_READING_PASS";
}finally{await fs.writeFile(path.join(out,"actual.json"),JSON.stringify(result,null,2));}
console.log({state:result.state,states:result.states.length,failures:result.failures});
if(result.failures.length)throw Error(result.failures.join("; "));
