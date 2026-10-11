// New A rendering: actual resolved chart type, bound public sources and focus.
const fs = await import("node:fs/promises");
const crypto = await import("node:crypto");
const path = await import("node:path");
const raw = await fs.readFile(path.join(workflowRoot,
  "packets/2026-09-22-sol-delivery/evidence/1007V1/qa-a-shared-question-recovery-v2.js"));
if(crypto.createHash("sha256").update(raw).digest("hex") !==
   "3c1e1c695073c05620532cb12a05e239c143d6cf995064dd0ff8887b50acf429")
  throw Error("Failed A instrument evidence changed");
const oldField="groups: groups.map(g=>({purpose:g.comparison_purpose, kind:g.chart_type,";
const actualField="groups: groups.map((g,index)=>({purpose:g.comparison_purpose, "+
  'kind:document.querySelector("#kz-chart-"+index).dataset.chartType,';
let source=raw.toString().replaceAll(".artifacts/1007-ab-shared-question-preview-v2",
  ".artifacts/1007-ab-shared-question-preview-v3")
  .replace('candidateRelative, "a-qa-v3"','candidateRelative, "a-qa"')
  .replace("await new(Object.getPrototypeOf(async function(){}).constructor)(",
    "source=source.replace("+JSON.stringify(oldField)+","+JSON.stringify(actualField)+");\n"+
    "await new(Object.getPrototypeOf(async function(){}).constructor)(");
await new(Object.getPrototypeOf(async function(){}).constructor)(
  "taskSpace","workflowRoot",source)(taskSpace,workflowRoot);
