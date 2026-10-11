// Same bounded task checks, plus actual ECharts category order, new candidate.
const fs=await import("node:fs/promises"),path=await import("node:path");
const crypto=await import("node:crypto");
const raw=await fs.readFile(path.join(workflowRoot,
 "packets/2026-09-22-sol-delivery/evidence/1007V1/qa-ab-shared-chart-reading-v4.js"));
if(crypto.createHash("sha256").update(raw).digest("hex")!==
 "bff040d8cb69a8589ef66161208f63044a59446bba77c92b708246a1f00d3fd1")
 throw Error("Original v4 instrument changed");
let source=raw.toString().replaceAll(".artifacts/1007-ab-shared-question-preview-v4",
 ".artifacts/1007-ab-shared-chart-reading-v5");
source=source.replace("groups:groups.map(g=>({rows:g.rows.map(r=>({id:r.row_id,study:r.trial_id,",
 "groups:groups.map(g=>{const index=window.__CHART_GROUPS__.indexOf(g);"+
 "const chart=echarts.getInstanceByDom(document.querySelector('#kz-chart-'+index));"+
 "const order=chart.getOption().series.flatMap(s=>s.data).filter(p=>p._row_id).map(p=>p._row_id);"+
 "return {plottedOrder:order,rows:g.rows.map(r=>({id:r.row_id,study:r.trial_id,");
source=source.replace("value:r.value})),crossTrial:g.cross_trial})),",
 "value:r.value})),crossTrial:g.cross_trial};}),");
source=source.replace("for(const group of measured.groups){",
 "for(const group of measured.groups){"+
 "if(group.plottedOrder.join('|')!==group.rows.map(r=>r.id).join('|'))"+
 "result.failures.push(report+width+':actual graph order differs from posted visit order');");
await new(Object.getPrototypeOf(async function(){}).constructor)(
 "taskSpace","workflowRoot",source)(taskSpace,workflowRoot);
