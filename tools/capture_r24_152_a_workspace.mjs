// Native ordinary A candidate: configuration, query conservation and evidence.
const fs = await import("node:fs/promises");
const crypto = await import("node:crypto");
const root = "/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow";
const out = root + "/.artifacts/r24-152-a-compact-workspace-20261003";
const page = (await taskSpace(12)).page("p1");
const base = new URL("file://" + out + "/site/safety.html").href;
await fs.mkdir(out + "/screenshots", { recursive: false });
const records = [];

async function capture(width, state) {
  const metrics = await page.evaluate(() => {
    const workspace = document.querySelector(".kz-a-workspace-bar");
    const cards = [...document.querySelectorAll(".kz-a-safety-observation")]
      .filter(n => n.getClientRects().length && !n.closest("[hidden]"));
    const query = [...document.querySelectorAll(".kz-a-safety-table tbody tr")]
      .filter(n => n.dataset.filterMatch !== "false");
    const summary = document.querySelector("[data-safety-query-disclosure]");
    return {
      workspace_open: workspace.open,
      workspace_height: workspace.getBoundingClientRect().height,
      workspace_summary_reachable: !!workspace.querySelector("summary").getClientRects().length,
      table_ids: query.map(n => n.dataset.rowId),
      query_count: +summary.dataset.queryCount,
      source_count: window.REPORT_A.safety.length,
      first_fact_top: cards[0]?.getBoundingClientRect().top,
      minimum_fact_px: Math.min(...cards.flatMap(n => [...n.querySelectorAll("span,strong,small")]
        .map(e => parseFloat(getComputedStyle(e).fontSize)))),
      overflow: document.documentElement.scrollWidth > innerWidth,
      drawer_open: document.getElementById("data-basis-panel").hidden === false,
    };
  });
  if (metrics.source_count !== 514 || metrics.table_ids.length !== metrics.query_count ||
      metrics.overflow || metrics.minimum_fact_px < 16 || !metrics.workspace_summary_reachable) {
    throw new Error("Actual query/font/viewport/control conservation failed");
  }
  if (state !== "configuration-open" && metrics.workspace_open) {
    throw new Error("Configuration was forced open again");
  }
  const path = out + `/screenshots/a-safety-${width}-${state}.png`;
  await page.screenshot({ path, scale: "css" });
  records.push({ width, state, metrics, path: path.slice(root.length + 1),
    sha256: crypto.createHash("sha256").update(await fs.readFile(path)).digest("hex") });
}

for (const width of [1440, 1600, 1920, 2560]) {
  await page.cdp("Emulation.setDeviceMetricsOverride", {
    width, height: 900, deviceScaleFactor: 1, mobile: false,
  });
  await page.goto(base);
  await page.waitForSelector(".kz-a-safety-observation", { state: "visible" });
  await capture(width, "dense");
  await page.click(".kz-a-workspace-bar > summary");
  await page.waitForSelector("[data-a-save-view]", { state: "visible" });
  const configuration = await page.evaluate(() => ({
    save: !!document.querySelector("[data-a-save-view]").getClientRects().length,
    clear: !!document.querySelector("[data-a-clear-view]").getClientRects().length,
    portable: !!document.querySelector(".kz-a-workspace-bar .kz-personal-view").getClientRects().length,
  }));
  if (!Object.values(configuration).every(Boolean)) throw new Error("Configuration lost a control");
  await capture(width, "configuration-open");
  records.at(-1).configuration = configuration;
  await page.click(".kz-a-workspace-bar > summary");
  await page.goto(base + "?product=iptacopan&event=death");
  await page.waitForSelector(".kz-a-safety-observation", { state: "visible" });
  await capture(width, "sparse");
  if (records.at(-1).metrics.query_count !== 2) throw new Error("Sparse named query changed");
  await page.click(".kz-a-safety-table summary");
  const fact = await page.evaluate(() =>
    [...document.querySelectorAll(".kz-a-safety-table tr[data-row-id]")]
      .find(n => n.dataset.filterMatch !== "false").dataset.rowId);
  await page.click(`[data-evidence-row-id="${fact}"]`);
  await page.waitForFunction(() => document.getElementById("data-basis-panel").hidden === false);
  await capture(width, "evidence-sidebar");
  await page.keyboard.press("Escape");
  const focus = await page.evaluate(() => ({
    closed: document.getElementById("data-basis-panel").hidden,
    fact: document.activeElement?.getAttribute("data-evidence-row-id"),
    tag: document.activeElement?.tagName, inert: document.getElementById("main").inert,
  }));
  records.at(-1).after_escape = focus;
  if (!focus.closed || focus.fact !== fact || focus.tag !== "BUTTON" || focus.inert) {
    throw new Error("Evidence failed actual source-trigger restoration");
  }
}
await fs.writeFile(out + "/browser-evidence.json", JSON.stringify({
  state: "actual_Ego_bounded_A_workspace_owner_pixels_pending", space: 12, page: "p1", records,
  limits: ["Historical unaccepted source", "Not allpages/filtered-control/crossbrowser/motion/science/RC"],
}, null, 2) + "\n", { flag: "wx" });
console.log(JSON.stringify({ records: records.length, source_facts_preserved: 514 }));
