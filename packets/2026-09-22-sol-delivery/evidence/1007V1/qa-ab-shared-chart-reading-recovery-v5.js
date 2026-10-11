// Same candidate/source bytes. Recover only strict floating-rect instrument error.
const fs=await import("node:fs/promises"),path=await import("node:path");
const crypto=await import("node:crypto");
const recipe=await fs.readFile(path.join(workflowRoot,
 "packets/2026-09-22-sol-delivery/evidence/1007V1/qa-ab-shared-chart-reading-v5.js"));
if(crypto.createHash("sha256").update(recipe).digest("hex")!==
 "dbdc8cb3f81d575215bf9d790bed40a7b2bd17c06101217258eed7246f5e5623")
 throw Error("Frozen v5 recipe changed");
// Resolve its frozen v4 instrument and option-order extension without replaying
// the already-terminal home/filter/source/focus task suites.
let resolver=recipe.toString().replace(
 'await new(Object.getPrototypeOf(async function(){}).constructor)(\n'+
 ' "taskSpace","workflowRoot",source)(taskSpace,workflowRoot);',
 'return source;');
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
let source=await new AsyncFunction("workflowRoot",resolver)(workflowRoot);
const start=source.indexOf('const page=(await taskSpace(2)).page("p1");');
if(start<0)throw Error("Bounded recovery section missing");
source=source.slice(start).replace('candidateRelative,"shared-reading-qa"',
 'candidateRelative,"shared-reading-qa-v2"')
 .replace('h.width!==32||h.height!==32',
 'Math.abs(h.width-32)>0.01||Math.abs(h.height-32)>0.01');
await new AsyncFunction("taskSpace","workflowRoot","candidateRelative","fs","path",source)(
 taskSpace,workflowRoot,".artifacts/1007-ab-shared-chart-reading-v5",fs,path);
