// Run with ego-browser nodejs < tools/capture_r24_144_density.mjs.
// Existing authorized Space12/p1 only; runtime evidence, not science acceptance.
const fs = await import("node:fs/promises");
const crypto = await import("node:crypto");
const root = "/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow";
const out = root + "/.artifacts/r24-144-b-desktop-density-20261003";
const task = await taskSpace(12);
const page = task.page("p1");
const base = new URL("file://" + out + "/b-final/safety.html").href;
const fact = "safe-2bcd8ce52a408a96952a";
const sparseQuery = "?trial=nct04702568&clinical_concept=any_sae";
const widths = [1440, 1600, 1920, 2560];
const records = [];
await fs.mkdir(out + "/screenshots/final", { recursive: true });

async function ready() {
  await page.waitForFunction(() =>
    document.querySelector("[data-b-result-range]")?.textContent.includes("匹配") &&
    document.querySelectorAll(".kz-chart-module__group").length > 0,
  undefined, { timeout: 15000 });
}

async function capture(width, state) {
  const path = out + `/screenshots/final/b-safety-${width}-${state}.png`;
  await page.screenshot({ path, scale: "css" });
  const metrics = await page.evaluate(() => {
    const visible = [...document.querySelectorAll(".kz-chart-module__group")]
      .filter(node => node.offsetParent !== null);
    return {
      viewport: [innerWidth, innerHeight],
      url: location.href,
      range: document.querySelector("[data-b-result-range]")?.textContent,
      mounted_ids: (window.__CHART_GROUPS__ || []).flatMap(group =>
        group.rows.map(row => row.row_id)),
      plans: (window.__CHART_GROUPS__ || []).map(group =>
        window.__CHART_SYNC__.presentationPlan(group)),
      table_ids: visible.flatMap(node => [...node.querySelectorAll("tr[data-row-id]")]
        .map(row => row.dataset.rowId)),
      source_data_count: window.__EVIDENCE_VIEWS__?.length,
      geometry: visible.map(node => ({
        span: node.dataset.gridSpan,
        width: node.getBoundingClientRect().width,
        height: node.getBoundingClientRect().height,
        plot_height: node.querySelector(".kz-chart-group__chart")?.getBoundingClientRect().height,
        kind: node.querySelector(".kz-chart-group__chart")?.dataset.chartType,
      })),
      page_overflow: document.documentElement.scrollWidth > innerWidth,
      minimum_reading_px: Math.min(...visible.flatMap(node =>
        [...node.querySelectorAll("p,button,summary,strong,span")]
          .filter(element => element.getClientRects().length)
          .map(element => parseFloat(getComputedStyle(element).fontSize)))),
      drawer_open: document.getElementById("kz-evidence-drawer")?.hidden === false,
    };
  });
  records.push({ width, state, path: path.slice(root.length + 1),
    sha256: crypto.createHash("sha256").update(await fs.readFile(path)).digest("hex"), metrics });
}

for (const width of widths) {
  await page.cdp("Emulation.setDeviceMetricsOverride", {
    width, height: 900, deviceScaleFactor: 1, mobile: false,
  });
  await page.goto(base + sparseQuery);
  await ready();
  await capture(width, "sparse");
  await page.goto(base);
  await ready();
  await capture(width, "dense");
  await page.fill('input[placeholder="产品、试验、指标或事实编号"]', fact);
  await page.waitForFunction(() =>
    document.querySelector("[data-b-result-range]")?.textContent.includes("匹配 1 条事实"),
  undefined, { timeout: 10000 });
  await capture(width, "filtered-sparse");
  const selector = `button[data-chart-evidence-open="${fact}"]`;
  await page.click(selector);
  await page.waitForFunction(() =>
    document.getElementById("kz-evidence-drawer")?.hidden === false,
  undefined, { timeout: 10000 });
  await capture(width, "evidence-sidebar");
  await page.keyboard.press("Escape");
  const focus = await page.evaluate(() => ({
    drawer_closed: document.getElementById("kz-evidence-drawer")?.hidden === true,
    active_tag: document.activeElement?.tagName,
    active_fact: document.activeElement?.getAttribute("data-chart-evidence-open"),
    main_inert: document.querySelector("main")?.inert,
  }));
  records[records.length - 1].after_escape = focus;
  if (!focus.drawer_closed || focus.active_fact !== fact || focus.main_inert) {
    throw new Error("Actual source drawer/focus behavior failed: " + JSON.stringify(focus));
  }
}
await fs.writeFile(out + "/browser-evidence-final.json", JSON.stringify({
  status: "actual_ego_component_checks_not_scientific_or_allpage_acceptance",
  space: task.spaceId, page: page.label, records,
  limitations: ["Fixed historical R62 source; not current independent medical acceptance",
    "B representative safety component only; no all205page or cross-browser acceptance",
    "Still screenshots do not prove full-cycle motion"],
}, null, 2) + "\n");
console.log(JSON.stringify({ records: records.length, widths, fact, output: out,
  state: "actual captures completed; owner must view pixels before visual conclusions" }));
