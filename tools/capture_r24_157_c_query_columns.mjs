// Actual existing Ego page; no accepted/current switch or fabricated visual PASS.
const fs = await import("node:fs/promises");
const crypto = await import("node:crypto");
const root = "/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow";
const out = root + "/.artifacts/r24-157-c-query-columns-20261003";
const page = (await taskSpace(12)).page("p1");
const base = new URL("file://" + out + "/site/endpoint-timepoint-matrix.html").href;
const query = "Thrombotic and Haemolytic Events will in";
await fs.mkdir(out + "/screenshots", { recursive: false });
const records = [];
async function capture(width, state) {
  const metrics = await page.evaluate(() => {
    const facts = [...document.querySelectorAll("[data-criterion-row-id]")];
    return {
      query: window.__C_VISIBLE_CHART_ROW_IDS__,
      matched: facts.filter(n => n.dataset.criterionContextOnly !== "true")
        .map(n => n.dataset.criterionRowId),
      context: facts.filter(n => n.dataset.criterionContextOnly === "true")
        .map(n => n.dataset.criterionRowId),
      table: [...document.querySelectorAll(".kz-chart-table__row[data-row-id]")]
        .filter(n => n.style.display !== "none").map(n => n.dataset.rowId),
      columns: [...document.querySelectorAll("th[data-criteria-study]")]
        .map(n => n.dataset.criteriaStudy),
      notice: document.querySelector("[data-criteria-unmatched-selected]")?.textContent || "",
      choices: [...document.querySelectorAll(".kz-c-criteria-choices input")]
        .map(n => ({ study: n.value, checked: n.checked })),
      overflow: document.documentElement.scrollWidth > innerWidth,
      font: Math.min(...facts.map(n => parseFloat(getComputedStyle(n).fontSize))),
      drawer: window.__EVIDENCE_DRAWER__.getOpenRowId(),
    };
  });
  const sorted = ids => JSON.stringify([...ids].sort());
  if (sorted(metrics.query) !== sorted(metrics.matched)
      || sorted(metrics.query) !== sorted(metrics.table) || metrics.overflow
      || metrics.font < 16 || !metrics.choices.every(n => n.checked)) {
    throw new Error("Current C query/font/selection conservation failed");
  }
  if (state !== "restored" && (metrics.query.length !== 1 || metrics.context.length !== 2
      || metrics.columns.join() !== "NCT03829449"
      || !metrics.notice.includes("NCT02264639"))) throw new Error("Sparse columns failed");
  if (state === "restored" && (metrics.query.length !== 51 || metrics.columns.length !== 2
      || metrics.notice)) throw new Error("Clear search did not restore full selected scope");
  const path = out + `/screenshots/c-${width}-${state}.png`;
  await page.screenshot({ path, scale: "css" });
  records.push({ width, state, metrics, path: path.slice(root.length + 1),
    sha256: crypto.createHash("sha256").update(await fs.readFile(path)).digest("hex") });
}
for (const width of [1440, 1600, 1920, 2560]) {
  await page.cdp("Emulation.setDeviceMetricsOverride", {
    width, height: 900, deviceScaleFactor: 1, mobile: false,
  });
  await page.goto(base);
  await page.waitForFunction(() => window.__C_VISIBLE_CHART_ROW_IDS__?.length === 51);
  await page.fill("#kz-c-criteria-search", query);
  await page.waitForFunction(() => document.querySelectorAll("th[data-criteria-study]").length === 1);
  await page.evaluate(() => document.querySelector(".kz-c-criteria-table-wrap")
    .scrollIntoView({ block: "start" }));
  await capture(width, "filtered-sparse");
  if (width === 1600) {
    const fact = records.at(-1).metrics.query[0];
    await page.click(`[data-criterion-row-id="${fact}"] button[data-evidence-open="${fact}"]`);
    await page.waitForFunction(() => window.__EVIDENCE_DRAWER__.isOpen());
    await capture(width, "source");
    await page.keyboard.press("Escape");
    const focus = await page.evaluate(() => ({
      closed: !window.__EVIDENCE_DRAWER__.isOpen(),
      fact: document.activeElement?.getAttribute("data-evidence-open"),
      tag: document.activeElement?.tagName, inert: document.getElementById("main").inert,
    }));
    records.at(-1).after_escape = focus;
    if (!focus.closed || focus.fact !== fact || focus.tag !== "BUTTON" || focus.inert)
      throw new Error("Same-fact source return failed after column collapse");
  }
  await page.fill("#kz-c-criteria-search", "");
  await page.waitForFunction(() => document.querySelectorAll("th[data-criteria-study]").length === 2);
  await page.evaluate(() => window.scrollTo(0, 0));
  await capture(width, "restored");
}
await fs.writeFile(out + "/browser-evidence.json", JSON.stringify({
  state: "actual_Ego_bounded_query_columns_owner_pixels_pending", space: 12, page: "p1", records,
  limitations: ["Unreviewed C candidate, not current", "Representative endpoint page only",
    "Not complete four-state/allpage/crossbrowser/science/motion/RC acceptance"],
}, null, 2) + "\n", { flag: "wx" });
console.log(JSON.stringify({ records: records.length, preserved: 51, sparse: 1,
  context_not_counted: 2, accepted: false }));
