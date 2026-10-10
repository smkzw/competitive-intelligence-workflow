// Actual ordinary-render candidate, existing184/p2. No current save/profile access.
const fs=await import("node:fs/promises"),crypto=await import("node:crypto");
const root=globalThis.CI_WORKFLOW_ROOT;
if(!root)throw new Error("Explicit English project required");
const out=root+"/.artifacts/1007-landscape-row-geometry-v2";
await fs.mkdir(out);
const candidate=root+"/.artifacts/1007-landscape-desktop-candidate-v2";
const manifest=JSON.parse(await fs.readFile(candidate+"/actual.json","utf8"));
const bytes=await fs.readFile(candidate+"/site/overview.html");
if(crypto.createHash("sha256").update(bytes).digest("hex")!==manifest.render_hashes["overview.html"])
 throw new Error("Frozen actual page changed");
const page=(await taskSpace(184)).page("p2");
const results=[];
for(const width of [1440,1600,1920,2560]){
 await page.cdp("Emulation.setDeviceMetricsOverride",{width,height:900,deviceScaleFactor:1,mobile:false});
 await page.goto("file://"+candidate+"/site/overview.html");
 await page.waitForFunction(()=>document.readyState==="complete"&&document.fonts.status==="loaded");
 await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>r(true)))));
 const actual=await page.evaluate(()=>({
  width:innerWidth,documentWidth:document.documentElement.scrollWidth,
  productIds:[...document.querySelectorAll(".kz-a-landscape-product")].map(e=>e.dataset.productId),
  bands:[...document.querySelectorAll(".kz-a-landscape-target-band")].map(b=>({
   target:b.querySelector("summary").innerText,open:b.open,
   x:b.getBoundingClientRect().x,y:b.getBoundingClientRect().y,
   width:b.getBoundingClientRect().width,height:b.getBoundingClientRect().height,
   cells:[...b.querySelector(".kz-a-landscape-band__cells").children].map(e=>({
    x:e.getBoundingClientRect().x,y:e.getBoundingClientRect().y,
    height:e.getBoundingClientRect().height,text:e.textContent})),
  })),
 }));
 if(actual.documentWidth>width+1||new Set(actual.productIds).size!==38||actual.bands.length!==2)
  throw new Error("Actual whole landscape or viewport incomplete");
 for(const band of actual.bands){
  if(band.cells.length!==7||Math.max(...band.cells.map(c=>c.y))-Math.min(...band.cells.map(c=>c.y))>1)
   throw new Error("Stage cells not one aligned row");
  if(!band.cells[4].text.trim()||band.height>110)throw new Error("Actual III-phase geometry wrong");
 }
 if(Math.abs(actual.bands[0].x-actual.bands[1].x)>1||
    actual.bands[1].y<actual.bands[0].y+actual.bands[0].height)throw new Error("Next target not next row");
 await page.screenshot({path:out+`/overview-${width}.png`});
 await page.focus(".kz-a-landscape-target-band summary");
 await page.keyboard.press("Enter");
 const closed=await page.evaluate(()=>{
  const b=document.querySelector(".kz-a-landscape-target-band");
  return {open:b.open,visibleCellHeight:b.querySelector(".kz-a-landscape-band__cells").getBoundingClientRect().height,
          focus:document.activeElement===b.querySelector("summary")};
 });
 if(closed.open||closed.visibleCellHeight!==0||!closed.focus)throw new Error("Native collapse/focus failed");
 await page.keyboard.press("Enter");
 const reopened=await page.evaluate(()=>document.querySelector(".kz-a-landscape-target-band").open);
 if(!reopened)throw new Error("Native re-open failed");
 results.push({width,actual,keyboard:{closed,reopened},screenshot:`overview-${width}.png`});
}
const proof={state:"FOUR_DESKTOP_WIDTHS_LANDSCAPE_ROWS_AND_NATIVE_KEYBOARD_PASSED_NOT_CURRENT_ACCEPTANCE",
 candidateManifestSha256:crypto.createHash("sha256").update(await fs.readFile(candidate+"/actual.json")).digest("hex"),
 pageSha256:manifest.render_hashes["overview.html"],authorCssSha256:manifest.author_css_sha256,
 results,sourceWrites:0,saves:0,currentChanges:0,freshProfile:false,
 limits:"V1 lacked pinned identity and is nonrepresentative, retained. V2 recipe target_labels precheck was vacuous; actual source-backed two target rows validated here. No user-value/science/full-state/cross-browser acceptance."};
await fs.writeFile(out+"/actual.json",JSON.stringify(proof,null,2));
console.log(JSON.stringify({state:proof.state,actualWidths:results.length}));
