// Full task graph/table/source on a completed candidate; no current writes.
const fs = await import("node:fs/promises");
const crypto = await import("node:crypto");
const path = await import("node:path");
const recipes = path.join(workflowRoot, "packets/2026-09-22-sol-delivery/evidence/1007V1");
const raw = await fs.readFile(path.join(recipes, "qa-b-question-reading-preview-v1.js"));
if (crypto.createHash("sha256").update(raw).digest("hex") !==
    "0b070cb4a7313f9c6098fbc3204e7da9e1f8fb1089625256b16942ee677b501d")
  throw Error("Frozen prior task recipe changed");
const actual = JSON.parse(await fs.readFile(path.join(workflowRoot,
  ".artifacts/1007-b-primary-matrix-preview-v1/actual.json"), "utf8"));
if (actual.pages !== 104 || actual.current_writes !== 0 || actual.source_writes !== 0)
  throw Error("Complete ordinary readonly render before browser verification");
const matrix = `
    const primary = document.querySelector(".kz-b-comparison-details");
    const table = primary.querySelector("[data-primary-comparison-table]");
    const primaryIds = Array.from(table.querySelectorAll("button[data-row-id]"))
      .map(node => node.getAttribute("data-row-id"));
    const studyLabels = Array.from(table.querySelectorAll("tbody th[scope='row']"))
      .map(node => node.textContent);
`;
let source = raw.toString().replaceAll(".artifacts/1007-b-question-reading-preview-v1",
  ".artifacts/1007-b-primary-matrix-preview-v1")
  .replaceAll('el.getAttribute("data-group-index")',
    'el.closest(".kz-chart-module__group").getAttribute("data-group-index")')
  .replaceAll("el.dataset.groupIndex",
    'el.closest(".kz-chart-module__group").getAttribute("data-group-index")')
  .replace('return {width: innerWidth, height: innerHeight, mode:',
    matrix + 'return {primaryOpen: primary.open, primaryVisible: table.checkVisibility(),' +
    ' primaryIds, studyLabels, width: innerWidth, height: innerHeight, mode:')
  .replace('if (observed.overflow) run.failures.push(label + ":page overflow");',
    'if (observed.overflow) run.failures.push(label + ":page overflow");' +
    'if (observed.mode === "comparison" && label !== "source" &&' +
    ' (!observed.primaryOpen || !observed.primaryVisible ||' +
    ' observed.primaryIds.slice().sort().join("|") !== observed.displayedIds.slice().sort().join("|")))' +
    ' run.failures.push(label + ":primary table hidden or identity mismatch");' +
    'if (observed.studyLabels.some(label => /nct[0-9]{8}/.test(label)))' +
    ' run.failures.push(label + ":registry display casing");')
  .replace('await page.click(".kz-b-comparison-details > summary");\n    await record("complete-table");\n' +
    '    await page.click(".kz-b-comparison-details > summary");',
    'await page.evaluate(() => document.querySelector(".kz-b-comparison-details > summary")' +
    '.scrollIntoView({block: "center"}));' +
    'await page.click(".kz-b-comparison-details > summary");' +
    'if (await page.evaluate(() => document.querySelector(".kz-b-comparison-details").open))' +
    ' throw Error("Primary table did not collapse");' +
    'await page.click(".kz-b-comparison-details > summary");await record("complete-table");')
  .replaceAll('await page.click("#kz-filter-panel > summary");',
    'await page.evaluate(() => document.querySelector("#kz-filter-panel > summary")' +
    '.scrollIntoView({block: "center"}));await page.click("#kz-filter-panel > summary");');
await new (Object.getPrototypeOf(async function(){}).constructor)(
  "taskSpace", "workflowRoot", source)(taskSpace, workflowRoot);
