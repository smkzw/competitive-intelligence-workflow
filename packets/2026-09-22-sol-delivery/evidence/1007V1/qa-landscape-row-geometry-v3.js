// Bounded recovery of v2's ambiguous focus selector; no render or current replay.
const fs=await import("node:fs/promises"),crypto=await import("node:crypto");
const root=globalThis.CI_WORKFLOW_ROOT;
if(!root)throw new Error("Explicit English project required");
const recipePath=root+"/packets/2026-09-22-sol-delivery/evidence/1007V1/qa-landscape-row-geometry-v2.js";
const base=await fs.readFile(recipePath,"utf8");
if(base.split('await page.focus(".kz-a-landscape-target-band summary");').length!==2)
 throw new Error("Original selector recipe changed");
const code=base.replace('1007-landscape-row-geometry-v2"','1007-landscape-row-geometry-v3"')
 .replace('await page.focus(".kz-a-landscape-target-band summary");',
          'await page.focus("details.kz-a-landscape-target-band:first-of-type > summary");');
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
await new AsyncFunction(code)();
const out=root+"/.artifacts/1007-landscape-row-geometry-v3";
await fs.writeFile(out+"/recipe-binding.json",JSON.stringify({
 baseRecipeSha256:crypto.createHash("sha256").update(base).digest("hex"),
 executedCodeSha256:crypto.createHash("sha256").update(code).digest("hex"),
 recovery:"v2 actual first-width geometry and PNG retained; native focus matched two elements, no save/render repeated",
},null,2));
