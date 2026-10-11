// Capture the real production event callback, not an elementFromPoint approximation.
const fs=await import("node:fs/promises"),path=await import("node:path");
const crypto=await import("node:crypto");
const raw=await fs.readFile(path.join(workflowRoot,
  "packets/2026-09-22-sol-delivery/evidence/1007V1/qa-a-shared-question-current-v1.js"));
if(crypto.createHash("sha256").update(raw).digest("hex")!==
  "d2aae27911cf63c368ba896d87ff7abc54221cc799e4b4ff4c402f2c1457f1ac")
  throw Error("Original focus instrument changed");
let source=raw.toString().replace('candidateRelative, "a-qa-v2"',
  'candidateRelative, "a-qa-v3"');
source=source.replace("window.__QA_A_SOURCE_TRIGGER__=document.elementFromPoint(x,y);",
  "const original=window.__A_COMPARISON_EVIDENCE__;"+
  "window.__A_COMPARISON_EVIDENCE__=function(id,trigger){"+
  "window.__QA_A_SOURCE_TRIGGER__=trigger;return original(id,trigger);};");
source=source.replace("triggerTag:trigger&&trigger.tagName,",
  "triggerTag:trigger&&trigger.tagName,triggerRects:trigger&&trigger.getClientRects().length,");
await new(Object.getPrototypeOf(async function(){}).constructor)(
  "taskSpace","workflowRoot",source)(taskSpace,workflowRoot);
