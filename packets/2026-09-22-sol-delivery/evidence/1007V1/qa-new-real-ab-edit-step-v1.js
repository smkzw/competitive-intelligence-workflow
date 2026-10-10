// Read actual generated reports after a committed step, before the next UI write.
const fs=await import("node:fs/promises");
const root=globalThis.CI_WORKFLOW_ROOT,step=Number(globalThis.CI_WORKFLOW_EDIT_STEP);
if(!root||![1,3,4].includes(step))throw new Error("Explicit step1/3/4 required");
const output=root+"/.artifacts/1007-current14-real-ab-edit-v1";
const verified=JSON.parse(await fs.readFile(output+`/step-${step}-verified.json`,"utf8"));
const recoverB=globalThis.CI_WORKFLOW_EDIT_QA_RECOVER_B===true;
const destination=output+`/step-${step}-reports-actual${recoverB?"-b-id-recovery-v1":""}.json`;
try{await fs.access(destination);throw new Error("Existing actual result; do not replay");}
catch(e){if(e.code!=="ENOENT")throw e;}
const page=(await taskSpace(184)).page("p2");
const row="eff-b0b587971df19e9d9cde",run={revision:14+step,generation:verified.generation,
  step,space:184,states:[],failures:[],scientific_acceptance:"NOT_INHERITED"};
try{
 if(recoverB){
  const prior=JSON.parse(await fs.readFile(output+`/step-${step}-reports-actual.json`,"utf8"));
  if(prior.generation!==run.generation||prior.states.length!==1||prior.states[0].kind!=="A"||prior.failures.length)
   throw new Error("Exact same-generation completed A required");
  run.completed_prior_states=prior.states;
  run.recovery="B production filter identity is id, not row_id. Original A result and failed B lookup retained; no repeat of save or A QA.";
 }
 await page.goto("http://127.0.0.1:65033/?fact="+verified.target_current.fact_id,{timeout:120000});
 for(const kind of recoverB?["B"]:["A","B"]){
  const entry=kind==="A"?"clinical-portfolio.html":"overview.html";
  const base=`http://127.0.0.1:65033/reports/${run.generation}/${kind}/${entry}`;
  await page.goto(base+"?view=comparison",{timeout:120000});
  await page.waitForSelector("#full-study-comparison select",{state:"visible"});
  const selected=await page.evaluate(({kind,row})=>{
   const w=window[kind==="A"?"__A_COMPARISON_WORKSPACE__":"__B_COMPARISON_WORKSPACE__"];
   const rows=kind==="A"?window.__A_COMPARISON_ROWS__:window.__FILTER_ROWS__;
   const id=kind==="A"?Object.keys(rows).find(id=>rows[id].a_row_id===row||rows[id].row_id===row):
    rows.find(item=>item.id===row)?.id;
   const col=w.columns.find(c=>Object.values(c.cells).flat().includes(id));
   if(!col)throw new Error("No production query matches actual bound row");
   return{question:col.question_id,page:1+Math.floor(w.columns.filter(
    c=>c.question_id===col.question_id).indexOf(col)/4)};
  },{kind,row});
  await page.selectOption(kind==="A"?"[data-a-comparison-question]":"[data-comparison-column]",selected.question);
  for(let n=1;n<selected.page;n++)await page.click(kind==="A"?"[data-a-comparison-next]":"[data-comparison-next]");
  const trigger=kind==="A"?`#full-study-comparison [data-evidence-row-id="${row}"]`:
    `#full-study-comparison [data-row-id="${row}"]`;
  const current=await page.evaluate(selector=>document.querySelector(selector).textContent,trigger);
  const expected=step===1?"-67.4":step===3?"用户清除":"-67.5";
  if(!current.includes(expected))run.failures.push(kind+": current value missing");
  await page.click(trigger);
  const drawer=kind==="A"?"#data-basis-panel":"#kz-evidence-drawer";
  await page.waitForFunction(selector=>!document.querySelector(selector).hidden,drawer);
  const basis=await page.evaluate(selector=>document.querySelector(selector).textContent,drawer);
  if(!basis.includes("-67.5")||!basis.includes(step===3?"用户清除":"用户修订"))
   run.failures.push(kind+": source/user status missing");
  const screenshot=`step-${step}-${kind}-source.png`;
  await page.screenshot({path:output+"/"+screenshot});
  await page.keyboard.press("Escape");
  const focus=await page.evaluate(selector=>document.activeElement===document.querySelector(selector),trigger);
  if(!focus)run.failures.push(kind+": Esc did not return to actual trigger");
  run.states.push({kind,selected,current,basis,focus,screenshot});
  await fs.writeFile(destination,JSON.stringify(run,null,2));
 }
 if(run.failures.length)throw new Error(run.failures.join(";"));
 run.state="ACTUAL_NORMAL_AB_REPORT_VALUES_SOURCE_AND_ESC_PASSED";
}catch(error){run.state="FAILED_NOT_ACCEPTED";run.error=String(error);throw error;}
finally{await fs.writeFile(destination,JSON.stringify(run,null,2));}
console.log(JSON.stringify({step,states:run.states.length,failures:run.failures}));
