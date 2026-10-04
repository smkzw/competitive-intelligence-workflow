// Exact native A successor; no C assets, old sites, profiles or current touched.
const fs = await import("node:fs/promises");
const crypto = await import("node:crypto");
const root = "/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow";
const out = root + "/.artifacts/r24-148-a-query-disclosure-20261003";
const page = (await taskSpace(12)).page("p1");
const base = new URL("file://" + out + "/site-v2/safety.html").href;
await fs.mkdir(out + "/screenshots-v2", { recursive: false });
const records = [];
for (const width of [1440, 1600, 1920, 2560]) {
  await page.cdp("Emulation.setDeviceMetricsOverride", {
    width, height: 900, deviceScaleFactor: 1, mobile: false,
  });
  for (const state of ["dense", "sparse"]) {
    await page.goto(base + (state === "sparse" ? "?product=iptacopan&event=death" : ""));
    await page.waitForSelector("[data-safety-query-disclosure]", { state: "visible" });
    const metrics = await page.evaluate(() => {
      const node = document.querySelector("[data-safety-query-disclosure]");
      const query = [...document.querySelectorAll(".kz-a-safety-table tbody tr")]
        .filter(r => r.dataset.filterMatch !== "false");
      return { summary: node.textContent, total: +node.dataset.queryCount,
        drawable: +node.dataset.drawableCount, unassigned: +node.dataset.unassignedCount,
        table_ids: query.map(r => r.dataset.rowId),
        source_count: window.REPORT_A.safety.length,
        overflow: document.documentElement.scrollWidth > innerWidth };
    });
    if (metrics.total !== metrics.table_ids.length || metrics.overflow || metrics.source_count !== 514) {
      throw new Error("Query/table/original fact conservation failed");
    }
    if (state === "sparse" && (metrics.total !== 2 || metrics.unassigned !== 0 || metrics.drawable !== 2)) {
      throw new Error("Sparse disclosure still uses total-page scope");
    }
    const path = out + `/screenshots-v2/a-safety-${width}-${state}.png`;
    await page.screenshot({ path, scale: "css" });
    records.push({ width, state, path: path.slice(root.length + 1), metrics,
      sha256: crypto.createHash("sha256").update(await fs.readFile(path)).digest("hex") });
  }
}
await fs.writeFile(out + "/browser-evidence-v2.json", JSON.stringify({
  state: "actual_Ego_bounded_query_family_pixels_pending", space: 12, page: "p1", records,
  limits: ["Historical unaccepted source", "No allpage/medical/current/crossbrowser/RC acceptance"],
}, null, 2) + "\n", { flag: "wx" });
console.log(JSON.stringify({ records: records.length, preserved_source_facts: 514 }));
