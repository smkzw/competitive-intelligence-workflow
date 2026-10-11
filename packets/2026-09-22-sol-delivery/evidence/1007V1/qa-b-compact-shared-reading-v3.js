// Same completed v2 candidate. Preserve the premature file-not-found attempt.
const fs = await import("node:fs/promises");
const crypto = await import("node:crypto");
const path = await import("node:path");
const recipes = path.join(workflowRoot, "packets/2026-09-22-sol-delivery/evidence/1007V1");
async function read(name, digest) {
  const raw = await fs.readFile(path.join(recipes, name));
  if (crypto.createHash("sha256").update(raw).digest("hex") !== digest)
    throw Error("Terminal recipe changed: " + name);
  return raw.toString();
}
const original = await read("qa-b-question-reading-preview-v1.js",
  "0b070cb4a7313f9c6098fbc3204e7da9e1f8fb1089625256b16942ee677b501d");
const identity = await read("qa-b-compact-shared-reading-v1.js",
  "1fccc85ba662cf91ba525823c8db79d29f53b89eb2262ed3f2754ce975395d6a");
const geometry = await read("qa-b-compact-shared-reading-v2.js",
  "5ab3c8123b7f4e43f6f382d8eacd334220496fe0aa5757b7e319ccee9de27169");
function literal(source, name) {
  const start = source.indexOf("const " + name + " = `") + ("const " + name + " = `").length;
  const end = source.indexOf("`;", start);
  if (start < name.length + 12 || end < start) throw Error("Missing frozen probe");
  return source.slice(start, end);
}
const extra = literal(identity, "extra").replace(
  'return {rowCount: rows.length, studyCount, visibleIds, names, legend, glyphs, failures,',
  literal(geometry, "checks") + 'return {rowCount: rows.length, studyCount, visibleIds,' +
    ' names, legend, glyphs, failures, geometry,');
const actual = JSON.parse(await fs.readFile(path.join(workflowRoot,
  ".artifacts/1007-b-compact-shared-reading-v2/actual.json"), "utf8"));
if (actual.pages !== 104 || actual.current_writes !== 0 || actual.source_writes !== 0)
  throw Error("Read-only render must complete before browser verification");
const source = original.replaceAll(".artifacts/1007-b-question-reading-preview-v1",
  ".artifacts/1007-b-compact-shared-reading-v2")
  .replaceAll('el.getAttribute("data-group-index")',
    'el.closest(".kz-chart-module__group").getAttribute("data-group-index")')
  .replaceAll('el.dataset.groupIndex',
    'el.closest(".kz-chart-module__group").getAttribute("data-group-index")')
  .replaceAll('"qa"', '"qa-v5"').replaceAll('"qa/actual.json"', '"qa-v5/actual.json"')
  .replaceAll('await page.click("#kz-filter-panel > summary");',
    'await page.evaluate(() => document.querySelector("#kz-filter-panel > summary")' +
    '.scrollIntoView({block: "center"})); await page.click("#kz-filter-panel > summary");')
  .replace('const shared = await record("shared-baseline");',
    'const shared = await record("shared-baseline");' + extra);
await new (Object.getPrototypeOf(async function(){}).constructor)(
  "taskSpace", "workflowRoot", source)(taskSpace, workflowRoot);
