// Existing Ego Space12/p1; fixed native A candidate, never clinical acceptance.
const fs = await import("node:fs/promises");
const crypto = await import("node:crypto");
const root = "/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow";
const out = root + "/.artifacts/r24-144-b-desktop-density-20261003";
const page = (await taskSpace(12)).page("p1");
const base = new URL("file://" + out + "/a-final/safety.html").href;
const records = [];
await fs.mkdir(out + "/screenshots/a-final", { recursive: true });
await page.goto(base);
const selection = await page.evaluate(() => {
  const data = window.REPORT_A.safety;
  const known = data.filter(r => r.numeric_projection?.renderable && r.group_assignment_state !== "unknown");
  const groups = new Map();
  for (const r of known) {
    const key = r.product_id + "|" + r.term_key;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(r);
  }
  const target = [...groups.values()].filter(rows => rows.length <= 2)
    .sort((a, b) => a[0].row_id.localeCompare(b[0].row_id))[0];
  if (!target) throw new Error("No actual sparse group; do not manufacture one");
  const row = target[0];
  const product = window.REPORT_A.products.find(p => p.id === row.product_id);
  return { product: product.name, event: row.term_key, fact: row.row_id,
    count: target.length, source_unverified: !row.source_field_path };
});

async function ready() {
  await page.waitForSelector(".kz-a-safety-observation[data-row-id]", { state: "visible" });
}

async function capture(width, state) {
  const path = out + `/screenshots/a-final/a-safety-${width}-${state}.png`;
  await page.screenshot({ path, scale: "css" });
  const metrics = await page.evaluate(() => {
    const visible = [...document.querySelectorAll(".kz-a-safety-observation[data-row-id]")]
      .filter(n => n.getClientRects().length && !n.closest("[hidden]"));
    const selectedTable = [...document.querySelectorAll(".kz-a-safety-table tbody tr")]
      .filter(n => n.dataset.filterMatch !== "false");
    const groups = [...document.querySelectorAll(".kz-a-safety-observation-group")]
      .filter(n => !n.hidden);
    return { viewport: [innerWidth, innerHeight], url: location.href,
      all_source_ids: window.REPORT_A.safety.map(r => r.row_id),
      query_table_ids: selectedTable.map(n => n.dataset.rowId),
      visible_plot_ids: visible.map(n => n.dataset.rowId),
      groups: groups.map(n => ({ span: n.dataset.gridSpan,
        width: n.getBoundingClientRect().width, height: n.getBoundingClientRect().height })),
      page_overflow: document.documentElement.scrollWidth > innerWidth,
      drawer_open: document.getElementById("data-basis-panel")?.hidden === false,
      minimum_fact_px: Math.min(...visible.flatMap(n => [...n.querySelectorAll("span,strong,small")]
        .map(e => parseFloat(getComputedStyle(e).fontSize)))) };
  });
  records.push({ width, state, path: path.slice(root.length + 1),
    sha256: crypto.createHash("sha256").update(await fs.readFile(path)).digest("hex"), metrics });
}

for (const width of [1440, 1600, 1920, 2560]) {
  await page.cdp("Emulation.setDeviceMetricsOverride", {
    width, height: 900, deviceScaleFactor: 1, mobile: false,
  });
  const query = new URLSearchParams({ product: selection.product, event: selection.event });
  await page.goto(base + "?" + query);
  await ready();
  await capture(width, "sparse");
  await page.goto(base);
  await ready();
  await capture(width, "dense");
  await page.click('[data-filter-dimension="product"] summary');
  await page.click(`[data-filter-dimension="product"] button[data-filter-value="${selection.product}"]`);
  await page.click('[data-filter-dimension="event"] summary');
  await page.click(`[data-filter-dimension="event"] button[data-filter-value="${selection.event}"]`);
  await page.waitForFunction(fact =>
    [...document.querySelectorAll(".kz-a-safety-observation[data-row-id]")]
      .some(n => n.dataset.rowId === fact && n.getClientRects().length), selection.fact);
  await capture(width, "filtered-sparse");
  await page.click(".kz-a-safety-table summary");
  const source = `[data-evidence-row-id="${selection.fact}"]`;
  await page.click(source);
  await page.waitForFunction(() => document.getElementById("data-basis-panel")?.hidden === false);
  await capture(width, "evidence-sidebar");
  await page.keyboard.press("Escape");
  records.at(-1).after_escape = await page.evaluate(() => ({
    closed: document.getElementById("data-basis-panel")?.hidden === true,
    active_tag: document.activeElement?.tagName,
    active_fact: document.activeElement?.getAttribute("data-evidence-row-id"),
    main_inert: document.querySelector("main")?.inert,
  }));
  if (!records.at(-1).after_escape.closed || records.at(-1).after_escape.active_fact !== selection.fact) {
    throw new Error("Actual A source focus failed; preserve captures and failure");
  }
}
await fs.writeFile(out + "/browser-evidence-a-final.json", JSON.stringify({
  state: "actual_Ego_representative_A_only_owner_pixels_pending", space: 12, page: "p1",
  selection, records, limitations: ["Historical source; no clinical/current acceptance",
    "No all56page/cross-browser/full-motion acceptance; unbound sources remain unverified"],
}, null, 2) + "\n");
console.log(JSON.stringify({ records: records.length, selection, pixel_review: "pending" }));
