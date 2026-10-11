// Same frozen v3 bytes; scroll the real toolbar into view before pointer input.
// v2/v3 failed attempts stay untouched. No forced clicks or DOM-state edits.
const fs = await import("node:fs/promises");
const crypto = await import("node:crypto");
const path = await import("node:path");
const base = path.join(workflowRoot,
  "packets/2026-09-22-sol-delivery/evidence/1007V1/qa-b-question-reading-preview-v1.js");
const raw = await fs.readFile(base);
if (crypto.createHash("sha256").update(raw).digest("hex") !==
  "0b070cb4a7313f9c6098fbc3204e7da9e1f8fb1089625256b16942ee677b501d")
  throw Error("Original failed recipe changed");
const source = raw.toString().replaceAll(".artifacts/1007-b-question-reading-preview-v1",
  ".artifacts/1007-b-question-reading-preview-v3")
  .replaceAll('el.getAttribute("data-group-index")',
    'el.closest(".kz-chart-module__group").getAttribute("data-group-index")')
  .replaceAll('el.dataset.groupIndex',
    'el.closest(".kz-chart-module__group").getAttribute("data-group-index")')
  .replaceAll('"qa"', '"qa-v4"').replaceAll('"qa/actual.json"', '"qa-v4/actual.json"')
  .replaceAll('await page.click("#kz-filter-panel > summary");',
    'await page.evaluate(() => document.querySelector("#kz-filter-panel > summary")' +
    '.scrollIntoView({block: "center"})); await page.click("#kz-filter-panel > summary");');
await new (Object.getPrototypeOf(async function(){}).constructor)(
  "taskSpace", "workflowRoot", source)(taskSpace, workflowRoot);
