// New current23 real TESAE consumer. One UI action; never replay a pending click.
const fs=await import("node:fs/promises"),root=globalThis.CI_WORKFLOW_ROOT;
const step=Number(globalThis.CI_WORKFLOW_EDIT_STEP);
if(!root||![1,2,3,4].includes(step))throw new Error("Explicit root/step required");
const out=root+"/.artifacts/1007-current23-tesae-ui-v1";
const pre=JSON.parse(await fs.readFile(out+"/prewrite.json"));
const fact=pre.selected_fact.fact_id,expectedRevision=22+step;
if(step>1){const prior=JSON.parse(await fs.readFile(out+`/step-${step-1}-verified.json`));
 if(prior.revision!==expectedRevision)throw new Error("Prior readonly postconditions required");}
const page=(await taskSpace(2)).page("p1");
await page.goto("http://127.0.0.1:64582/?fact="+fact,{timeout:120000});
await page.waitForSelector("#input-value",{state:"visible"});
const before=await page.evaluate(fact=>{const e=JSON.parse(document.querySelector("#facts").textContent);
 return{revision:e.revision,fact:e.facts[fact],value:document.querySelector("#input-value").value};},fact);
if(before.revision!==expectedRevision||before.value!==["2","3","2",""][step-1])
 throw new Error("Current precondition changed; no click");
const action=["set","undo","clear","undo"][step-1];
await fs.writeFile(out+`/step-${step}-pending.json`,JSON.stringify({before,action,step},null,2),{flag:"wx"});
try{
 if(action==="set")await page.fill("#input-value","3");
 await page.fill("#basis",`1007V1新TESAE真实A+B绑定验收${step}：${action}；临时用户层数值，登记原值2不改，最终撤销恢复；不是医学结论。`);
 await page.click(action==="set"?"#save":action==="clear"?"#clear":"#undo");
 await page.waitForFunction(()=>document.querySelector("#result").textContent.trim()!==""||
  document.querySelector("#status").textContent.includes("操作未完成"),undefined,{timeout:600000});
 const returned=await page.evaluate(()=>({result:JSON.parse(document.querySelector("#result").textContent||"null"),
  status:document.querySelector("#status").textContent,value:document.querySelector("#input-value").value,
  links:[...document.querySelectorAll("#report-links a")].map(a=>({text:a.textContent,url:a.href}))}));
 await fs.writeFile(out+`/step-${step}-ui-return.json`,JSON.stringify(returned,null,2),{flag:"wx"});
 if(returned.result?.revision!==expectedRevision+1||returned.value!==["3","2","","2"][step-1])
  throw new Error("Inspect actual current and saved return; do not repeat this action");
 await page.screenshot({path:out+`/step-${step}-editor.png`});
 console.log({step,action,revision:returned.result.revision,value:returned.value});
}catch(error){await fs.writeFile(out+`/step-${step}-failure.json`,JSON.stringify({error:String(error),
 rule:"Read persisted current/return before recovery. Never blindly click again."},null,2),{flag:"wx"});throw error;}
