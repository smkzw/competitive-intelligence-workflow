// Actual ordinary C9/current21 preview; dedicated space2; no source/current writes.
const fs=await import("node:fs/promises"),crypto=await import("node:crypto");
const root=globalThis.CI_WORKFLOW_ROOT;
if(!root)throw new Error("Explicit English root required");
const candidate=root+"/.artifacts/1007-c-statistics-reading-preview-v2";
const out=root+"/.artifacts/1007-c-statistics-reading-preview-v2-fresh-qa-v2";
const bytes=await fs.readFile(candidate+"/actual.json");
const digest=crypto.createHash("sha256").update(bytes).digest("hex");
if(digest!=="dfe782d0306ff08e7d338fc45ec0cc6074c20c699b33a2854b65dadd1eaba088")throw new Error("Candidate changed");
const manifest=JSON.parse(bytes),results=[],page=(await taskSpace(2)).page("p1");
await fs.mkdir(out);
async function settle(){
 await page.waitForFunction(()=>document.readyState==="complete"&&document.fonts.status==="loaded");
 await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
}
async function open(relative){
 const html=await fs.readFile(candidate+"/C/"+relative);
 if(crypto.createHash("sha256").update(html).digest("hex")!==manifest.render_hashes[relative])throw new Error("Render changed");
 await page.goto("file://"+candidate+"/C/"+relative);await settle();
}
async function activate(selector){await page.focus(selector);await page.keyboard.press("Enter");await settle();}
async function inspect(){return await page.evaluate(()=>{
 const s=document.querySelector('section[aria-label="统计字段覆盖与复核边界"]');
 const d=s.querySelector("details.kz-c-statistics-scope");
 return {width:innerWidth,documentWidth:document.documentElement.scrollWidth,
  warning:[...s.children].filter(e=>e.tagName==="P").map(e=>e.innerText),open:d.open,
  summaryDisplay:getComputedStyle(d.querySelector("summary")).display,completeText:d.textContent,
  links:[...d.querySelectorAll("a")].map(e=>e.getAttribute("href")),
  declaredIds:window.__C_DESIGN_WORKSPACE__.membership.row_ids.slice().sort(),
  visibleIds:window.__C_VISIBLE_CHART_ROW_IDS__.slice().sort(),
  dataTop:document.querySelector("#kz-c-chart-visuals").getBoundingClientRect().top};
});}
const summary="details.kz-c-statistics-scope > summary";
const hit='.kz-c-criteria-source[data-row-id="c-nct04183335-sample-size"]';
for(const width of [1440,1600,1920,2560]){
 await page.cdp("Emulation.setDeviceMetricsOverride",{width,height:1000,deviceScaleFactor:1,mobile:false});
 await open("sample-analysis-statistics.html");const dense=await inspect();
 await page.screenshot({path:out+`/C-firstfold-${width}.png`});
 await activate(summary);const expanded=await inspect();
 await page.screenshot({path:out+`/C-complete-scope-${width}.png`});
 await activate(summary);
 await page.fill("#kz-c-criteria-search","NCT04183335");
 await page.waitForFunction(()=>window.__C_VISIBLE_CHART_ROW_IDS__.length===1);
 const sparse=await inspect();await page.screenshot({path:out+`/C-filtered-cleared-${width}.png`});
 await activate(hit);await page.waitForFunction(()=>window.__EVIDENCE_DRAWER__.isOpen());
 const evidence=await page.evaluate(()=>({id:window.__EVIDENCE_DRAWER__.getOpenRowId(),
  text:document.querySelector("#kz-evidence-view").innerText,
  original:window.__EVIDENCE_VIEWS__.find(v=>v.row.row_id==="c-nct04183335-sample-size").original_text}));
 await page.screenshot({path:out+`/C-cleared-source-${width}.png`});
 await page.keyboard.press("Escape");
 const esc=await page.evaluate(()=>!window.__EVIDENCE_DRAWER__.isOpen()&&
  document.activeElement===document.querySelector('.kz-c-criteria-source[data-row-id="c-nct04183335-sample-size"]'));
 await page.fill("#kz-c-criteria-search","");
 await page.waitForFunction(()=>window.__C_VISIBLE_CHART_ROW_IDS__.length===4);
 const restored=await inspect(),failures=[];
 if(dense.documentWidth>width+1||dense.summaryDisplay!=="list-item")failures.push("Viewport/native arrow");
 if(dense.visibleIds.length!==4||JSON.stringify(dense.visibleIds)!==JSON.stringify(dense.declaredIds))failures.push("Complete query");
 if(!dense.warning.join(" ").includes("未纳入 Protocol/SAP 正文")||!dense.warning.join(" ").includes("不等于完整统计分析复核"))failures.push("Visible source/review limits");
 if(!expanded.open||!expanded.links.includes("endpoint-definitions.html")||!expanded.completeText.includes("逐研究缺口"))failures.push("Complete scope reachable");
 if(sparse.visibleIds[0]!=="c-nct04183335-sample-size")failures.push("Exact sparse query");
 if(evidence.id!==sparse.visibleIds[0]||!evidence.text.includes("用户清除")||!evidence.text.includes(evidence.original)||!esc)failures.push("Current clear/original/source/Esc");
 if(JSON.stringify(restored.visibleIds)!==JSON.stringify(dense.visibleIds))failures.push("Full query restore");
 results.push({width,dense,expanded,sparse,evidence,esc,restored,failures});
 await fs.writeFile(out+"/progress.json",JSON.stringify({state:"PARTIAL_NOT_FINAL",results},null,2));
}
await open("evidence-limitations.html");
const limitations=await page.evaluate(()=>({folds:document.querySelectorAll("details.kz-c-statistics-scope").length,text:document.querySelector("main").innerText}));
await page.screenshot({path:out+"/C-limitations-2560.png"});
const proof={state:results.some(r=>r.failures.length)?"SCOPED_BEHAVIOR_FAILED":"SCOPED_BEHAVIOR_PASS_VISUAL_REVIEW_PENDING",
 candidateManifestSha256:digest,profileId:"Profile 2",spaceId:2,results,limitations,
 source_generation:manifest.source_generation,sourceWrites:0,saves:0,currentChanges:0,
 previousAttempt:"v1 patch transport did not return; wrapper stopped before browser dispatch, possible late new-file effect retained. No v1 PASS claimed. This separate v2 has its own output.",
 limits:"C statistics/current clear/source/four desktop states only; not full science/share/hosts/RC."};
await fs.writeFile(out+"/actual.json",JSON.stringify(proof,null,2));
console.log(JSON.stringify({state:proof.state,widths:results.length,failures:results.flatMap(r=>r.failures)}));
