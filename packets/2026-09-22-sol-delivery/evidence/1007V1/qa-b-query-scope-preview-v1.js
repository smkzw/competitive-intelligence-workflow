// Reuse completed task recipe; verify all rendered observations match the
// selected primary-table query, including question switches and filtering.
const fs = await import("node:fs/promises");
const crypto = await import("node:crypto");
const path = await import("node:path");
const previous = path.join(workflowRoot,
  "packets/2026-09-22-sol-delivery/evidence/1007V1/qa-b-primary-matrix-preview-v1.js");
const raw = await fs.readFile(previous);
if (crypto.createHash("sha256").update(raw).digest("hex") !==
    "ee37c4f5709bfa27e5c5aea1484fb6c5275545d8d90b760aa831649cd3f9275e")
  throw Error("Frozen primary-matrix recipe changed");
const extra = `
    const chartIds = window.__CHART_GROUPS__.flatMap(group => group.rows.map(row => row.row_id));
`;
let source = raw.toString().replaceAll(".artifacts/1007-b-primary-matrix-preview-v1",
  ".artifacts/1007-b-query-scope-preview-v1")
  .replace("const matrix = `", "const matrix = `" + extra)
  .replace(" primaryIds, studyLabels, width:", " primaryIds, chartIds, studyLabels, width:")
  .replace(' run.failures.push(label + ":registry display casing");',
    ' run.failures.push(label + ":registry display casing");' +
    'if (observed.mode === "comparison" && observed.chartIds.slice().sort().join("|") !==' +
    ' observed.primaryIds.slice().sort().join("|"))' +
    ' run.failures.push(label + ":chart/primary-query identity mismatch");');
await new (Object.getPrototypeOf(async function(){}).constructor)(
  "taskSpace", "workflowRoot", source)(taskSpace, workflowRoot);
