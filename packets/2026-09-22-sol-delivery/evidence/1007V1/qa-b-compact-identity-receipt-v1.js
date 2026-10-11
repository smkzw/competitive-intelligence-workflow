// Persist measured identity/geometry: the task recorder copied each state
// before the extra assertions attached their details. No task replay or edits.
const fs = await import("node:fs/promises");
const path = await import("node:path");
const crypto = await import("node:crypto");
const recipes = path.join(workflowRoot, "packets/2026-09-22-sol-delivery/evidence/1007V1");
async function read(name, digest) {
  const raw = await fs.readFile(path.join(recipes, name));
  if (crypto.createHash("sha256").update(raw).digest("hex") !== digest)
    throw Error("Frozen probe changed");
  return raw.toString();
}
function literal(source, name) {
  const token = "const " + name + " = `";
  const start = source.indexOf(token) + token.length, end = source.indexOf("`;", start);
  if (start < token.length || end < start) throw Error("Missing probe");
  return source.slice(start, end);
}
const first = await read("qa-b-compact-shared-reading-v1.js",
  "1fccc85ba662cf91ba525823c8db79d29f53b89eb2262ed3f2754ce975395d6a");
const second = await read("qa-b-compact-shared-reading-v2.js",
  "5ab3c8123b7f4e43f6f382d8eacd334220496fe0aa5757b7e319ccee9de27169");
const probe = literal(first, "extra").replace(
  'return {rowCount: rows.length, studyCount, visibleIds, names, legend, glyphs, failures,',
  literal(second, "checks") + 'return {rowCount: rows.length, studyCount, visibleIds,' +
    ' names, legend, glyphs, failures, geometry,');
const out = path.join(workflowRoot, ".artifacts/1007-b-compact-shared-reading-v2");
const actual = JSON.parse(await fs.readFile(path.join(out, "actual.json"), "utf8"));
if (actual.pages !== 104 || actual.source_writes !== 0 || actual.current_writes !== 0)
  throw Error("Candidate must have completed normally");
const page = (await taskSpace(2)).page("p1"), run = {states: [], failures: []};
for (const width of [1440, 1600, 1920, 2560]) {
  await page.cdp("Emulation.setDeviceMetricsOverride", {width,
    height: width === 2560 ? 1440 : width === 1920 ? 1080 : 900,
    deviceScaleFactor: 1, mobile: false});
  await page.goto("file://" + path.join(out, "B/overview.html") +
    "?view=comparison&cmp=" + encodeURIComponent("baseline::baseline:agecontinuous"));
  await page.waitForFunction(() => document.querySelector('.kz-b-shared-plot [data-chart-type]') &&
    echarts.getInstanceByDom(document.querySelector('.kz-b-shared-plot [data-chart-type]')));
  const shared = {};
  await new (Object.getPrototypeOf(async function(){}).constructor)(
    "page", "run", "shared", probe)(page, run, shared);
  run.states.push({width, identities: shared.identities});
}
if (run.failures.length) throw Error(run.failures.join("; "));
run.state = "FOUR_WIDTH_IDENTITY_GEOMETRY_PASSED_NOT_PRODUCT_ACCEPTANCE";
await fs.writeFile(path.join(out, "qa-v5/identity-geometry-actual.json"),
  JSON.stringify(run, null, 2), {flag: "wx"});
console.log({state: run.state, widths: run.states.length, failures: run.failures});
