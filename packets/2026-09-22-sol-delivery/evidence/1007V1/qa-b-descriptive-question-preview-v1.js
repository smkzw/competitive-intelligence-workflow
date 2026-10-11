// Actual source-posted clinical question, not a synthetic demo or numeric licence.
const fs = await import("node:fs/promises");
const crypto = await import("node:crypto");
const path = await import("node:path");
const previous = path.join(workflowRoot,
  "packets/2026-09-22-sol-delivery/evidence/1007V1/qa-b-query-scope-preview-v1.js");
const raw = await fs.readFile(previous);
if (crypto.createHash("sha256").update(raw).digest("hex") !==
    "32269dff9e33088e16937cd518b8af4b0ee208a44a83b7c02c832e809313ca49")
  throw Error("Frozen prior question-query recipe changed");
const extra = `
    const posted = window.__CHART_GROUPS__.filter(g =>
      g.comparison_purpose === "clinical_question_descriptive").map(g => ({
        ids: g.rows.map(r => r.row_id), values: g.rows.map(r => r.value),
        studies: [...new Set(g.rows.map(r => r.trial_id))],
        crossTrial: g.cross_trial, unit: g.metric_label_zh}));
`;
const checks = `
    const counts = dense.posted.find(g => g.ids.length === 4 && g.studies.length === 2);
    if (!counts || counts.crossTrial || counts.values.slice().sort((a,b)=>a-b).join("|") !==
        "75|78|103|111") run.failures.push("source-posted two-study count plot missing");
    const clinicalRows = dense.plots.flatMap(p => p.rowIds).slice().sort();
    if (clinicalRows.join("|") !== dense.primaryIds.slice().sort().join("|"))
      run.failures.push("clinical graph/query/table mismatch");
`;
let source = raw.toString().replaceAll(".artifacts/1007-b-query-scope-preview-v1",
  ".artifacts/1007-b-descriptive-question-preview-v1")
  .replace("const extra = `", "const extra = `" + extra)
  .replace('" primaryIds, chartIds, studyLabels, width:"',
    '" primaryIds, chartIds, studyLabels, posted, width:"')
  .replace('await new (Object.getPrototypeOf(async function(){}).constructor)(',
    'source = source.replace(\'const line = dense.plots.find\', ' +
    JSON.stringify(checks + 'const line = dense.plots.find') + ');\n' +
    'await new (Object.getPrototypeOf(async function(){}).constructor)(');
await new (Object.getPrototypeOf(async function(){}).constructor)(
  "taskSpace", "workflowRoot", source)(taskSpace, workflowRoot);
