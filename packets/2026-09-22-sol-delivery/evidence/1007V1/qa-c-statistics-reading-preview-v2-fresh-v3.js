// Correct only the instrument's guessed route; frozen production bytes unchanged.
const fs=await import("node:fs/promises"),crypto=await import("node:crypto");
const root=globalThis.CI_WORKFLOW_ROOT;
if(!root)throw new Error("Explicit English root required");
const relative="packets/2026-09-22-sol-delivery/evidence/1007V1/qa-c-statistics-reading-preview-v2-fresh-v2.js";
const bytes=await fs.readFile(root+"/"+relative),code=bytes.toString();
const digest=crypto.createHash("sha256").update(bytes).digest("hex");
const manifest=JSON.parse(await fs.readFile(root+"/.artifacts/1007-c-statistics-reading-preview-v2/actual.json"));
if(!manifest.render_hashes["endpoint-timepoint-matrix.html"])throw new Error("Actual endpoint route missing");
const corrected=code.replace("-fresh-qa-v2","-fresh-qa-v3")
 .replace('includes("endpoint-definitions.html")','includes("endpoint-timepoint-matrix.html")');
if(corrected===code||corrected.includes('includes("endpoint-definitions.html")'))throw new Error("Instrument correction did not apply");
await import("data:text/javascript;base64,"+Buffer.from(corrected).toString("base64"));
const page=(await taskSpace(2)).page("p1");
await page.goto("file://"+root+"/.artifacts/1007-c-statistics-reading-preview-v2/C/sample-analysis-statistics.html");
await page.focus("details.kz-c-statistics-scope > summary");await page.keyboard.press("Enter");
await page.click('details.kz-c-statistics-scope a[href="endpoint-timepoint-matrix.html"]');
await page.waitForFunction(()=>location.pathname.endsWith("endpoint-timepoint-matrix.html"));
const reached=await page.evaluate(()=>({title:document.querySelector("h1").innerText,
 path:location.pathname.split("/").pop(),width:innerWidth,documentWidth:document.documentElement.scrollWidth}));
if(reached.path!=="endpoint-timepoint-matrix.html"||reached.documentWidth>reached.width+1)throw new Error("Actual endpoint navigation failed");
await fs.writeFile(root+"/.artifacts/1007-c-statistics-reading-preview-v2-fresh-qa-v3/instrument-correction.json",JSON.stringify({
 originalRecipeSha256:digest,correction:"Production context and live DOM use endpoint-timepoint-matrix.html; v2 incorrectly guessed endpoint-definitions.html. Original four FAIL remain unchanged.",
 reached,sourceWrites:0,saves:0,currentChanges:0},null,2));
console.log(JSON.stringify({actualEndpointNavigation:"SCOPED_PASS",reached}));
