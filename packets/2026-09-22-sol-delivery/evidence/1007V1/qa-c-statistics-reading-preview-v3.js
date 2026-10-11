// Ordinary C9/current21, four widths and reading states; no saves/current writes.
const fs=await import("node:fs/promises"),crypto=await import("node:crypto");
const root=globalThis.CI_WORKFLOW_ROOT;
if(!root)throw new Error("Explicit English root required");
const candidate=root+"/.artifacts/1007-c-statistics-reading-preview-v3";
const out=root+"/.artifacts/1007-c-statistics-reading-preview-v3-fresh-qa-v1";
const bytes=await fs.readFile(candidate+"/actual.json");
const digest=crypto.createHash("sha256").update(bytes).digest("hex");
const original=await fs.readFile(root+"/packets/2026-09-22-sol-delivery/evidence/1007V1/qa-c-statistics-reading-preview-v2-fresh-v2.js","utf8");
const recipe=original.replaceAll("1007-c-statistics-reading-preview-v2","1007-c-statistics-reading-preview-v3")
 .replace("-fresh-qa-v2","-fresh-qa-v1")
 .replace("dfe782d0306ff08e7d338fc45ec0cc6074c20c699b33a2854b65dadd1eaba088",digest)
 .replace('includes("endpoint-definitions.html")','includes("endpoint-timepoint-matrix.html")');
await import("data:text/javascript;base64,"+Buffer.from(recipe).toString("base64"));
const page=(await taskSpace(2)).page("p1"),geometry=[];
for(const width of [1440,1600,1920,2560]){
 await page.cdp("Emulation.setDeviceMetricsOverride",{width,height:1000,deviceScaleFactor:1,mobile:false});
 await page.goto("file://"+candidate+"/C/evidence-limitations.html");
 await page.waitForFunction(()=>document.readyState==="complete"&&document.fonts.status==="loaded");
 const measured=await page.evaluate(()=>({width:innerWidth,documentWidth:document.documentElement.scrollWidth,
  fields:[...document.querySelectorAll(".kz-c-evidence-summary > div")].map(e=>{
   const dd=e.querySelector("dd"),dt=e.querySelector("dt"),r=dd.getBoundingClientRect(),s=getComputedStyle(dd);
   return {label:dt.innerText,text:dd.innerText,width:r.width,height:r.height,lineHeight:parseFloat(s.lineHeight),fontSize:parseFloat(s.fontSize)};
  })}));
 const failures=[];
 if(measured.documentWidth>width+1||measured.fields.length!==3)failures.push("Summary reachability/overflow");
 for(const f of measured.fields){
  if(f.width<160||f.height>f.lineHeight*3+1||f.fontSize<16)failures.push("Narrow or overwrapped "+f.label);
 }
 if(measured.fields[0]?.text!=="2026-10-07")failures.push("Exact source cutoff");
 await page.screenshot({path:out+`/C-limitations-${width}.png`});
 geometry.push({...measured,failures});
}
const proof=JSON.parse(await fs.readFile(out+"/actual.json"));
proof.geometry=geometry;
proof.state=geometry.some(r=>r.failures.length)||proof.results.some(r=>r.failures.length)
 ?"SCOPED_BEHAVIOR_FAILED":"SCOPED_BEHAVIOR_PASS_VISUAL_REVIEW_PENDING";
proof.recipeReuse="Ordinary v3 candidate; original v2 route typo corrected, all reading states rerun. No previous candidate PASS inherited.";
await fs.writeFile(out+"/actual.json",JSON.stringify(proof,null,2));
console.log(JSON.stringify({state:proof.state,geometry:geometry.map(r=>({width:r.width,fields:r.fields,failures:r.failures}))}));
