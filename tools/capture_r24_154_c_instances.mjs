// Existing Ego space only; ordinary C review candidate, not accepted/current.
const fs = await import("node:fs/promises");
const crypto = await import("node:crypto");
const root = "/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow";
const out = root + "/.artifacts/r24-154-c-density-integration-20261003";
const page = (await taskSpace(12)).page("p1");
const base = new URL("file://" + out + "/site-v2/endpoint-timepoint-matrix.html").href;
const query = "Thrombotic and Haemolytic Events will in";
await fs.mkdir(out + "/screenshots", { recursive: false });
const records = [];

async function capture(width, state) {
  const metrics = await page.evaluate(() => {
    const q = window.__C_VISIBLE_CHART_ROW_IDS__ || [];
    const nodes = [...document.querySelectorAll("[data-criterion-row-id]")];
    const matched = nodes.filter(n => n.getAttribute("data-criterion-context-only") !== "true");
    const table = [...document.querySelectorAll(".kz-chart-table__row[data-row-id]")]
      .filter(n => n.style.display !== "none");
    const blocks = [...document.querySelectorAll("[data-endpoint-instance]")];
    return {
      query_ids: q, matched_ids: matched.map(n => n.getAttribute("data-criterion-row-id")),
      table_ids: table.map(n => n.getAttribute("data-row-id")),
      context_ids: nodes.filter(n => n.getAttribute("data-criterion-context-only") === "true")
        .map(n => n.getAttribute("data-criterion-row-id")),
      blocks: blocks.length, first_fact_top: nodes[0]?.getBoundingClientRect().top,
      minimum_fact_px: Math.min(...nodes.map(n => parseFloat(getComputedStyle(n).fontSize))),
      overflow: document.documentElement.scrollWidth > innerWidth,
      search: document.querySelector("#kz-c-criteria-search").value,
      source_open: window.__EVIDENCE_DRAWER__.isOpen(),
      source_fact: window.__EVIDENCE_DRAWER__.getOpenRowId(),
      source_text: document.querySelector("#kz-evidence-view-fields")?.textContent,
    };
  });
  const sorted = a => JSON.stringify([...a].sort());
  if (sorted(metrics.query_ids) !== sorted(metrics.matched_ids) ||
      sorted(metrics.query_ids) !== sorted(metrics.table_ids) ||
      metrics.minimum_fact_px < 16 || metrics.overflow) {
    throw new Error("C actual query/table/font/viewport conservation failed");
  }
  if (state === "dense" && (metrics.query_ids.length !== 51 || metrics.blocks !== 17)) {
    throw new Error("C dense endpoint instances changed");
  }
  if (state !== "dense" && (metrics.query_ids.length !== 1 || metrics.context_ids.length !== 2)) {
    throw new Error("C sparse observation/context separation failed");
  }
  const images = [];
  for (const framing of ["first-screen", "target-card"]) {
    if (framing === "first-screen") await page.evaluate(() => window.scrollTo(0, 0));
    else if (!metrics.source_open) await page.evaluate(() =>
      document.querySelector(".kz-c-criteria-table-wrap").scrollIntoView({ block: "start" }));
    const path = out + `/screenshots/c-endpoints-${width}-${state}-${framing}.png`;
    await page.screenshot({ path, scale: "css" });
    images.push({ framing, path: path.slice(root.length + 1),
      sha256: crypto.createHash("sha256").update(await fs.readFile(path)).digest("hex") });
  }
  records.push({ width, state, metrics, images });
}

for (const width of [1440, 1600, 1920, 2560]) {
  await page.cdp("Emulation.setDeviceMetricsOverride", {
    width, height: 900, deviceScaleFactor: 1, mobile: false,
  });
  await page.goto(base);
  await page.waitForFunction(() => window.__C_VISIBLE_CHART_ROW_IDS__?.length === 51);
  await capture(width, "dense");
  await page.fill("#kz-c-criteria-search", query);
  await page.waitForFunction(() => window.__C_VISIBLE_CHART_ROW_IDS__?.length === 1);
  await capture(width, "filtered-sparse");
  await page.goto(base + "?criteria_q=" + encodeURIComponent(query));
  await page.waitForFunction(() => window.__C_VISIBLE_CHART_ROW_IDS__?.length === 1);
  await capture(width, "sparse");
  const fact = records.at(-1).metrics.query_ids[0];
  const selector = `[data-criterion-row-id="${fact}"] button[data-evidence-open="${fact}"]`;
  await page.click(selector);
  await page.waitForFunction(() => window.__EVIDENCE_DRAWER__.isOpen());
  await capture(width, "evidence-sidebar");
  if (records.at(-1).metrics.source_fact !== fact) throw new Error("Wrong original source opened");
  await page.keyboard.press("Escape");
  const focus = await page.evaluate(() => ({
    closed: !window.__EVIDENCE_DRAWER__.isOpen(),
    fact: document.activeElement?.getAttribute("data-evidence-open"),
    tag: document.activeElement?.tagName, main_inert: document.getElementById("main").inert,
  }));
  records.at(-1).after_escape = focus;
  if (!focus.closed || focus.fact !== fact || focus.tag !== "BUTTON" || focus.main_inert) {
    throw new Error("C source-trigger focus restoration failed");
  }
}
await fs.writeFile(out + "/browser-evidence.json", JSON.stringify({
  state: "actual_Ego_bounded_C_instances_owner_pixels_pending", space: 12, page: "p1", records,
  limits: ["85 unreviewed observations", "Not all 14 pages/cross-browser/motion/science/current/RC"],
}, null, 2) + "\n", { flag: "wx" });
console.log(JSON.stringify({ records: records.length, screenshots: records.length * 2,
  dense: 51, instances: 17, sparse: 1, context_not_counted: 2 }));
