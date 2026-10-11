// Continue only verified original step1; never replay a pending transaction.
const fs=await import("node:fs/promises"),root=globalThis.CI_WORKFLOW_ROOT;
const step=Number(globalThis.CI_WORKFLOW_EDIT_STEP),port=Number(globalThis.CI_WORKFLOW_EDITOR_PORT);
if(!root||![2,3,4].includes(step)||!Number.isSafeInteger(port)||port<1024||port>65535)
 throw new Error("Explicit English root, remaining step and actual editor port required");
const out=root+"/.artifacts/1007-current23-tesae-ui-v1";
const pre=JSON.parse(await fs.readFile(out+"/prewrite.json"));
const fact=pre.selected_fact.fact_id,expectedRevision=22+step;
const prior=JSON.parse(await fs.readFile(out+`/step-${step-1}-verified.json`));
if(prior.revision!==expectedRevision)throw new Error("Prior readonly proof required");
const page=(await taskSpace(2)).page("p1");
await page.goto(`http://127.0.0.1:${port}/?fact=${fact}`,{timeout:120000});
await page.waitForSelector("#input-value",{state:"visible"});
const before=await page.evaluate(fact=>{const e=JSON.parse(document.querySelector("#facts").textContent);
 return{revision:e.revision,fact:e.facts[fact],value:document.querySelector("#input-value").value};},fact);
if(before.revision!==expectedRevision||before.value!==["3","2",""][step-2])
 throw new Error("Actual current precondition changed; no click");
const action=["undo","clear","undo"][step-2];
await fs.writeFile(out+`/step-${step}-pending.json`,JSON.stringify({before,action,step,port},null,2),{flag:"wx"});
try{
 await page.fill("#basis",`1007V1新TESAE真实A+B绑定验收${step}：${action}；临时用户层，登记原值2不改，最终撤销恢复；非医学结论。`);
 const started=Date.now();
 await page.click(action==="clear"?"#clear":"#undo");
 const busy=await page.evaluate(()=>({status:document.querySelector("#status").textContent,
  disabled:["save","clear","undo"].map(id=>document.getElementById(id).disabled)}));
 await page.waitForFunction(()=>document.querySelector("#result").textContent.trim()!==""||
  document.querySelector("#status").textContent.includes("操作未完成"),undefined,{timeout:600000});
 const returned=await page.evaluate(()=>({result:JSON.parse(document.querySelector("#result").textContent||"null"),
  status:document.querySelector("#status").textContent,value:document.querySelector("#input-value").value,
  disabled:["save","clear","undo"].map(id=>document.getElementById(id).disabled),
  links:[...document.querySelectorAll("#report-links a")].map(a=>({text:a.textContent,url:a.href}))}));
 returned.elapsed_ms=Date.now()-started;returned.observed_busy=busy;
 await fs.writeFile(out+`/step-${step}-ui-return.json`,JSON.stringify(returned,null,2),{flag:"wx"});
 if(returned.result?.revision!==expectedRevision+1||returned.value!==["2","","2"][step-2])
  throw new Error("Read saved current and return; never repeat action");
 if(returned.disabled.some(Boolean))throw new Error("Committed editor remains locked");
 await page.screenshot({path:out+`/step-${step}-editor.png`});
 console.log({step,action,revision:returned.result.revision,value:returned.value,elapsed_ms:returned.elapsed_ms});
}catch(error){await fs.writeFile(out+`/step-${step}-failure.json`,JSON.stringify({error:String(error),
 rule:"Inspect durable current/return before recovery; no blind replay"},null,2),{flag:"wx"});throw error;}
