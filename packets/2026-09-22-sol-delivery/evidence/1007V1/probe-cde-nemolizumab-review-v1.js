// Exact-number CDE review lookup. No application-code/MAH/indication inference.
const fs = await import("node:fs/promises");
const crypto = await import("node:crypto");
const root = process.env.CI_WORKFLOW_ROOT;
if (!root) throw new Error("Set explicit CI_WORKFLOW_ROOT to the authorized English checkout");
const out = root + "/.artifacts/1007-cde-nemolizumab-review-v1";
await fs.mkdir(out);
const p = (await taskSpace(184)).page("p1");
const record={space:184,observations:[],limits:"Biological clinical-application sequence only. Official search highlights matching IDs, not filters the full table. Unmatched warning is not approval, withdrawal or absence proof. Indication/MAH unresolved; current access is not historical disclosure."};
try {
  await p.click("#splxtype + div .layui-select-title");
  await p.click("#splxtype + div dd[lay-value=生物]");
  for (const id of ["JXSL2600117","JXSL2500208"]) {
    const previous=await p.evaluate(()=>[...document.querySelectorAll("table")].find(t=>t.getClientRects().length).innerText);
    await p.fill("#acceptid2",id);
    await p.click("button[onclick*=getNewReportList]");
    let response="CHANGED_RENDERED_RESPONSE";
    try {await p.waitForFunction(old=>[...document.querySelectorAll("table")].find(t=>t.getClientRects().length).innerText!==old,previous,{timeout:15000});}
    catch(error) {response="IDENTICAL_OR_UNOBSERVED_RESPONSE_NOT_VERIFIED";}
    const observed=await p.evaluate(()=>({url:location.href,acceptance_number:document.querySelector("#acceptid2").value,
      sequence:document.querySelector("#splxtype").value,
      application_filter:document.querySelector("#applytypecdeNewReportSw").value,
      application_label:document.querySelector("#applytypecdeNewReportSw").selectedOptions[0].text,
      warning:document.querySelector("#hightLightWarn_xb")?.innerText ?? null,
      exact_matches:defaultObj.data.sessionTableData.filter(r=>r.acceptid===document.querySelector("#acceptid2").value).map(r=>({acceptance_number:r.acceptid,drug_name:r.drgnamecn,state:r.spzt,start_date:r.taskstrtdate})),
      table:[...document.querySelectorAll("table")].find(t=>t.getClientRects().length).innerText,
      count:[...document.querySelectorAll(".layui-laypage-count")].find(t=>t.getClientRects().length)?.innerText??null,
      observed_at:new Date().toISOString()}));
    if(observed.acceptance_number!==id||observed.sequence!=="生物")throw new Error("Actual query changed");
    const raw=JSON.stringify(observed);await fs.writeFile(out+"/"+id+".json",raw,{flag:"wx"});
    await p.screenshot({path:out+"/"+id+".png"});
    record.observations.push({id,response,source:id+".json",sha256:crypto.createHash("sha256").update(raw).digest("hex"),count:observed.count});
    await fs.writeFile(out+"/actual.json",JSON.stringify(record,null,2));
    console.log(JSON.stringify({id,response,table:observed.table,count:observed.count}));
  }
  record.state="TWO_CURRENT_REVIEW_SEQUENCE_OBSERVATIONS_ONLY_NOT_MAH_ACCEPTED";
}catch(error){record.state="FAILED_NOT_ACCEPTED";record.error=String(error);throw error;}
finally{record.finished_at=new Date().toISOString();await fs.writeFile(out+"/actual.json",JSON.stringify(record,null,2));}
