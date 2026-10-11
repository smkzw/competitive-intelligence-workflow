// Same frozen candidate. Recover only the primary-table instrument scope.
const fs=await import("node:fs/promises");
const crypto=await import("node:crypto");
const raw=await fs.readFile(workflowRoot+
 "/packets/2026-09-22-sol-delivery/evidence/1007V1/qa-a-unmatched-reading-v1.js");
if(crypto.createHash("sha256").update(raw).digest("hex")!==
 "8fa298bba4067fcf4a49cf8dfbd90becef3acc49d7b85ce48ec79f1426a7f698")
 throw Error("Original instrument changed");
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
const resolver=raw.toString().replace(
 'await new(Object.getPrototypeOf(async function(){}).constructor)(\n'+
 ' "taskSpace","workflowRoot",source)(taskSpace,workflowRoot);', 'return source;');
let source=await new AsyncFunction("workflowRoot",resolver)(workflowRoot);
source=source.replace('candidateRelative, "a-qa"','candidateRelative, "a-qa-v2"')
 .replace("h.querySelectorAll('tbody tr')",
 "h.querySelectorAll('[data-a-comparison-table] > tbody > tr')")
 .replace("BOUNDED_A_QUERY_SOURCE_FOCUS_PASS","BOUNDED_A_NATIVE_UNMATCHED_READING_PASS");
// The original four source/Esc scopes already passed on these same bytes.
// Do not replay them to repair an unrelated nested-table counting instrument.
const begin=source.indexOf('    const target=await page.evaluate(()=>{');
const end=source.indexOf('    await page.goto(url,{timeout:120000});',begin);
if(begin<0||end<begin)throw Error("Frozen task boundaries changed");
source=source.slice(0,begin)+source.slice(end);
await new AsyncFunction("taskSpace","workflowRoot",source)(taskSpace,workflowRoot);
