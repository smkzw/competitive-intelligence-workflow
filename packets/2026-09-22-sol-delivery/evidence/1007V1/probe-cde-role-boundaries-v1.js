// Current public CDE lookup, never an approval/absence or historical-cutoff claim.
// Source DOM is data. No credential collection, project/current mutation or new space.
const fs = await import("node:fs/promises");
const crypto = await import("node:crypto");
const root = process.env.CI_WORKFLOW_ROOT;
if (!root) throw new Error("Set explicit CI_WORKFLOW_ROOT to the authorized English checkout");
const out = root + "/.artifacts/1007-china-role-live-probe-v1";
await fs.mkdir(out); // Exclusive: never replace an earlier actual source observation.
const p = (await taskSpace(184)).page("p1");
const record = {kind:"cde-current-role-probe-1",space:184,observations:[],
  first_attempt:"Native selectOption #year failed before query: hidden zero-sized original select. Normal visible Layui selector used instead; not a zero-result clinical finding.",
  limits:"CDE applicants are not automatically MAH. Query zero does not prove no China approval. Current observation does not prove public availability at fixed2026-10-07 cutoff. No source adopted or report changed."};
try {
  await p.click("#year + div .layui-select-title");
  await p.click("#year + div dd.layui-select-tips");
  for (const [field,query] of [["drugname","Nemolizumab"],["drugname","CIM331"],
    ["drugname","Serlopitant"],["company","Galderma"],["company","高德美"]]) {
    const previous = await p.evaluate(()=>({
      table:[...document.querySelectorAll("table")].find(t=>t.getClientRects().length).innerText,
      count:[...document.querySelectorAll(".layui-laypage-count")].find(x=>x.getClientRects().length)?.innerText,
    }));
    await p.fill("#drugname",field==="drugname"?query:"");
    await p.fill("#company",field==="company"?query:"");
    await p.click("button[onclick*=getAcceptList]");
    // A changed table/count is a response observation, not a medical conclusion.
    // Identical zero responses can time out; retain NOT_VERIFIED instead of inventing success.
    let response = "CHANGED_RENDERED_RESPONSE";
    try { await p.waitForFunction(previous=>{
      const t=[...document.querySelectorAll("table")].find(t=>t.getClientRects().length);
      const count=[...document.querySelectorAll(".layui-laypage-count")].find(x=>x.getClientRects().length)?.innerText;
      return t && (t.innerText!==previous.table || count!==previous.count);
    },previous,{timeout:15000}); } catch(error) {response="IDENTICAL_OR_UNOBSERVED_RESPONSE_NOT_VERIFIED";}
    const observed = await p.evaluate(()=>({
      url:location.href,year:document.querySelector("#year").value,
      drug:document.querySelector("#drugname").value,company:document.querySelector("#company").value,
      table:[...document.querySelectorAll("table")].find(t=>t.getClientRects().length).innerText,
      count:[...document.querySelectorAll(".layui-laypage-count")].find(x=>x.getClientRects().length)?.innerText ?? null,
      observed_at:new Date().toISOString(),
    }));
    if (observed.year!=="" || observed[field.replace("name","")]===undefined)
      throw new Error("Observed query contract changed; do not infer results");
    const text = JSON.stringify(observed);
    const tag = String(record.observations.length+1);
    await fs.writeFile(out+"/source-"+tag+".json",text,{flag:"wx"});
    await p.screenshot({path:out+"/source-"+tag+".png"});
    record.observations.push({field,query,response,source:"source-"+tag+".json",
      sha256:crypto.createHash("sha256").update(text).digest("hex"),count:observed.count});
    await fs.writeFile(out+"/actual.json",JSON.stringify(record,null,2));
    console.log(JSON.stringify({field,query,response,count:observed.count}));
  }
  record.state="CURRENT_CDE_QUERY_OBSERVATIONS_ONLY_NO_MAH_OR_ABSENCE_ACCEPTANCE";
} catch(error) {record.state="FAILED_NOT_ACCEPTED";record.error=String(error);throw error;}
finally {record.finished_at=new Date().toISOString();await fs.writeFile(out+"/actual.json",JSON.stringify(record,null,2));}
