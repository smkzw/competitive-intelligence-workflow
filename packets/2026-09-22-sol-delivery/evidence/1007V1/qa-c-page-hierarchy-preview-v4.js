// Fresh ordinary C render; reuse checks, never reuse prior candidate PASS.
const fs=await import("node:fs/promises");
const root=globalThis.CI_WORKFLOW_ROOT;
if(!root)throw new Error("Explicit English root required");
const previous=await fs.readFile(root+"/packets/2026-09-22-sol-delivery/evidence/1007V1/qa-c-statistics-reading-preview-v3.js","utf8");
const recipe=previous.replaceAll("1007-c-statistics-reading-preview-v3","1007-c-page-hierarchy-preview-v4");
await import("data:text/javascript;base64,"+Buffer.from(recipe).toString("base64"));
const candidate=root+"/.artifacts/1007-c-page-hierarchy-preview-v4";
const out=root+"/.artifacts/1007-c-page-hierarchy-preview-v4-fresh-qa-v1";
const page=(await taskSpace(2)).page("p1"),hierarchy=[];
for(const width of [1440,1600,1920,2560]){
 await page.cdp("Emulation.setDeviceMetricsOverride",{width,height:1000,deviceScaleFactor:1,mobile:false});
 for(const relative of ["evidence-limitations.html","visit-duration-followup.html"]){
  await page.goto("file://"+candidate+"/C/"+relative);
  await page.waitForFunction(()=>document.readyState==="complete"&&document.fonts.status==="loaded");
  const measured=await page.evaluate(()=>{
   const title=document.querySelector("[data-c-task-title]"),limit=document.querySelector("section.kz-c-limitations");
   const t=title.getBoundingClientRect(),l=limit.getBoundingClientRect();
   return {width:innerWidth,documentWidth:document.documentElement.scrollWidth,title:title.innerText,
    titleTop:t.top,limitTop:l.top,titleVisible:t.top>=0&&t.bottom<=innerHeight,
    headings:[...document.querySelectorAll("main h2")].map(e=>e.innerText),
    limitText:limit.innerText,fontSize:parseFloat(getComputedStyle(title).fontSize)};
  });
  const failures=[];
  if(measured.width!==width||measured.documentWidth>width+1)failures.push("Viewport/overflow");
  if(!measured.titleVisible||measured.titleTop>=measured.limitTop)failures.push("Page context does not lead");
  if(measured.headings.includes(measured.title))failures.push("Repeated task heading");
  if(relative.startsWith("evidence")&&!measured.limitText.includes("不据此宣称全球或中国竞品检索已闭合"))failures.push("Evidence limits missing");
  if(relative.startsWith("visit")&&!measured.limitText.includes("给药疗程、结局观察窗与完整访视表不能互相替代"))failures.push("Visit limits missing");
  await page.screenshot({path:out+`/C-hierarchy-${relative.replace(".html","")}-${width}.png`});
  hierarchy.push({relative,...measured,failures});
 }
}
const proof=JSON.parse(await fs.readFile(out+"/actual.json"));
proof.hierarchy=hierarchy;
proof.recipeReuse="Fresh v4 hierarchy render and rerun of scoped reading/filter/source checks; previous PASS not inherited.";
proof.state=[...proof.results,...proof.geometry,...hierarchy].some(r=>r.failures.length)
 ?"SCOPED_BEHAVIOR_FAILED":"SCOPED_BEHAVIOR_PASS_VISUAL_REVIEW_PENDING";
await fs.writeFile(out+"/actual.json",JSON.stringify(proof,null,2));
console.log(JSON.stringify({state:proof.state,hierarchy:hierarchy.map(({width,relative,titleTop,limitTop,failures})=>({width,relative,titleTop,limitTop,failures}))}));
