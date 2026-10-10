// Actual normal UI only, Ego184. No API forgery/cookie/token access or blind retry.
const fs = await import("node:fs/promises");
const root = globalThis.CI_WORKFLOW_ROOT;
const step = Number(globalThis.CI_WORKFLOW_EDIT_STEP);
if (!root || ![1,2,3,4].includes(step)) throw new Error("Explicit root and step1–4 required");
const output = root + "/.artifacts/1007-current14-real-ab-edit-v1";
const pre = JSON.parse(await fs.readFile(output + "/prewrite.json", "utf8"));
const fact = pre.selected_fact.fact_id;
const pending = output + `/step-${step}-pending.json`;
const returned = output + `/step-${step}-ui-return.json`;
try {await fs.access(pending); throw new Error("Existing step: inspect actual current, never replay");}
catch (error) {if (error.code !== "ENOENT") throw error;}
if (step > 1) {
  const prior = JSON.parse(await fs.readFile(output + `/step-${step-1}-ui-return.json`, "utf8"));
  if (prior.revision !== 13 + step || prior.error) throw new Error("Previous actual step required");
}
const page = (await taskSpace(184)).page("p3");
await page.goto(`http://127.0.0.1:65033/?fact=${fact}`, {timeout:120000});
await page.waitForSelector("#input-value", {state:"visible"});
const before = await page.evaluate(fact => {
  const envelope = JSON.parse(document.querySelector("#facts").textContent);
  return {revision:envelope.revision,fact:envelope.facts[fact],
    value:document.querySelector("#input-value").value,status:document.querySelector("#status").textContent};
}, fact);
if (before.revision !== 13 + step || before.fact.fact_id !== fact)
  throw new Error("Actual editor precondition mismatch, no click");
const expectedBefore = ["-67.5","-67.4","-67.5",""][step-1];
if (before.value !== expectedBefore) throw new Error("Unexpected selected current value, no click");
const action = ["set","undo","clear","undo"][step-1];
await fs.writeFile(pending, JSON.stringify({step,action,fact,before,
  limits:"Temporary user-layer operation chain, not modified source or medical acceptance"},null,2),{flag:"wx"});
try {
  if (step === 1) {
    await page.fill("#input-value", "-67.4");
    await page.fill("#input-normalized", "-67.4");
  }
  await page.fill("#basis", `1007V1真实新增A+B依赖操作验证第${step}步：${action}；临时用户层验证，原登记估计-67.5不改，最终撤销恢复；非医学新结论。`);
  await page.click(action === "set" ? "#save" : action === "clear" ? "#clear" : "#undo");
  await page.waitForFunction(() => {
    const text = document.querySelector("#result").textContent.trim();
    return text !== "" || document.querySelector("#status").textContent.includes("操作未完成");
  },undefined,{timeout:600000});
  const actual = await page.evaluate(()=>({
    result:JSON.parse(document.querySelector("#result").textContent || "null"),
    status:document.querySelector("#status").textContent,
    value:document.querySelector("#input-value").value,
    normalized:document.querySelector("#input-normalized").value,
    links:[...document.querySelectorAll("#report-links a")].map(a=>({text:a.textContent,url:a.href}))
  }));
  actual.step=step;actual.action=action;actual.revision=14+step;
  actual.error=actual.result?.error || actual.result?.refresh_required ||
    (actual.status.includes("操作未完成") ? actual.status : null);
  await fs.writeFile(returned,JSON.stringify(actual,null,2),{flag:"wx"});
  const expectedAfter = ["-67.4","-67.5","","-67.5"][step-1];
  if (actual.error || !actual.status.includes(`revision ${14+step}`) || actual.value !== expectedAfter)
    throw new Error("Actual result mismatch: inspect persisted result/current, do not repeat");
  await page.screenshot({path:output+`/step-${step}-editor.png`});
  console.log(JSON.stringify({step,action,status:actual.status,value:actual.value,result:actual.result}));
} catch(error) {
  await fs.writeFile(output+`/step-${step}-failure.json`,JSON.stringify({error:String(error),
    rule:"Reopen actual current/receipt before any further click; never blind retry"},null,2),{flag:"wx"});
  throw error;
}
