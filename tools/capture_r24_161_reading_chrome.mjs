// Same ordinary entry inputs, fresh generated sites; existing Ego12/p1 only.
const fs = await import("node:fs/promises");
const crypto = await import("node:crypto");
const root = "/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow";
const out = root + "/.artifacts/r24-161-c-reading-chrome-20261003";
const page = (await taskSpace(12)).page("p1");
const factB = "safe-2bcd8ce52a408a96952a";
const queryC = "Thrombotic and Haemolytic Events will in";
const records = [];
await fs.mkdir(out + "/screenshots", { recursive: false });
async function capture(kind, width, state) {
  const metrics = await page.evaluate(kind => {
    const groups = [...document.querySelectorAll(".kz-chart-module__group")];
    const facts = [...document.querySelectorAll("[data-criterion-row-id]")];
    const ids = kind === "b" ? (window.__CHART_GROUPS__ || []).flatMap(g =>
      g.rows.map(r => String(r.row_id))) : window.__C_VISIBLE_CHART_ROW_IDS__;
    const table = kind === "b" ? groups.flatMap(g => [...g.querySelectorAll("tr[data-row-id]")]
      .map(r => r.dataset.rowId)) : [...document.querySelectorAll(".kz-chart-table__row")]
      .filter(r => r.style.display !== "none").map(r => r.dataset.rowId);
    const personal = document.querySelector(".kz-personal-view");
    const first = kind === "b" ? groups[0] : facts[0];
    const reading = kind === "b" ? groups.flatMap(g => [...g.querySelectorAll("p,button,summary,strong,span")])
      : facts;
    const main = document.getElementById("main");
    return {
      ids, table, first_fact_y: first?.getBoundingClientRect().top,
      main_width: main.getBoundingClientRect().width, viewport: [innerWidth, innerHeight],
      reading_floor: Math.min(...reading.filter(n => n.getClientRects().length)
        .map(n => parseFloat(getComputedStyle(n).fontSize))),
      overflow: document.documentElement.scrollWidth > innerWidth,
      personal_disclosure: personal?.closest("details")?.className,
      personal_visible: !!personal?.getClientRects().length,
      query_count: ids?.length, selection: document.querySelector("[data-filter-summary]")?.textContent,
      method_parent: document.querySelector(".kz-c-criteria-method")?.parentElement.className,
      source_open: window.__EVIDENCE_DRAWER__.isOpen(),
      main_inert: main.inert, main_filter: getComputedStyle(main).filter,
      source_filter: getComputedStyle(document.getElementById("kz-evidence-drawer")).filter,
      source_text: window.__EVIDENCE_DRAWER__.isOpen()
        ? document.getElementById("kz-evidence-drawer").textContent : null,
      scene: window.__KZ_SITE_SCENE__?.snapshot(),
    };
  }, kind);
  const sorted = ids => JSON.stringify([...ids].sort());
  if (sorted(metrics.ids) !== sorted(metrics.table) || metrics.overflow
      || metrics.reading_floor < 16 || metrics.main_width < width * .9
      || metrics.personal_disclosure !== `kz-${kind}-personal`) {
    throw new Error("Actual query, reading, width or configuration contract failed");
  }
  if (state === "source" && (!metrics.main_inert || metrics.source_filter !== "none"
      || !metrics.main_filter.includes("blur(5px)") || !metrics.scene.reasons.includes("modal")))
    throw new Error("Shared source isolation contract failed on integrated ordinary candidate");
  const path = out + `/screenshots/${kind}-${width}-${state}.png`;
  await page.screenshot({ path, scale: "css" });
  records.push({ kind, width, state, metrics, path: path.slice(root.length + 1),
    sha256: crypto.createHash("sha256").update(await fs.readFile(path)).digest("hex") });
}
for (const kind of ["b", "c"]) {
  const base = new URL("file://" + out + (kind === "b"
    ? "/b/safety.html" : "/c-final/endpoint-timepoint-matrix.html")).href;
  const sparse = kind === "b" ? "?trial=nct04702568&clinical_concept=any_sae"
    : "?criteria_q=" + encodeURIComponent(queryC);
  async function ready() {
    if (kind === "b") await page.waitForFunction(() =>
      document.querySelector("[data-b-result-range]")?.textContent.includes("匹配")
        && document.querySelectorAll(".kz-chart-module__group").length > 0);
    else await page.waitForFunction(() => window.__C_VISIBLE_CHART_ROW_IDS__?.length > 0);
  }
  for (const width of [1440, 1600, 1920, 2560]) {
    await page.cdp("Emulation.setDeviceMetricsOverride", {
      width, height: 900, deviceScaleFactor: 1, mobile: false,
    });
    await page.goto(base + sparse);
    await ready();
    await capture(kind, width, "sparse");
    await page.goto(base);
    await ready();
    await capture(kind, width, "dense");
    if (width === 1600) {
      await page.click("#kz-filter-panel > summary");
      await page.click(`details.kz-${kind}-personal > summary`);
      await capture(kind, width, "personal-open");
      if (!records.at(-1).metrics.personal_visible)
        throw new Error("Personal configuration became unreachable");
      await page.click("#kz-filter-panel > summary");
    }
    if (kind === "b") {
      await page.fill('input[placeholder="产品、试验、指标或事实编号"]', factB);
      await page.waitForFunction(() => document.querySelector("[data-b-result-range]")
        ?.textContent.includes("匹配 1 条事实"));
    } else {
      await page.fill("#kz-c-criteria-search", queryC);
      await page.waitForFunction(() => window.__C_VISIBLE_CHART_ROW_IDS__?.length === 1);
    }
    await capture(kind, width, "filtered-sparse");
    const fact = kind === "b" ? factB : records.at(-1).metrics.ids[0];
    const selector = kind === "b" ? `button[data-chart-evidence-open="${fact}"]`
      : `[data-criterion-row-id="${fact}"] button[data-evidence-open="${fact}"]`;
    await page.evaluate(s => document.querySelector(s).scrollIntoView({ block: "center" }), selector);
    await page.click(selector);
    await page.waitForFunction(() => window.__EVIDENCE_DRAWER__.isOpen());
    await capture(kind, width, "source");
    await page.keyboard.press("Escape");
    const focus = await page.evaluate(() => ({
      closed: !window.__EVIDENCE_DRAWER__.isOpen(), inert: document.getElementById("main").inert,
      fact: document.activeElement?.getAttribute("data-chart-evidence-open")
        || document.activeElement?.getAttribute("data-evidence-open"),
      tag: document.activeElement?.tagName,
    }));
    records.at(-1).after_escape = focus;
    if (!focus.closed || focus.inert || focus.fact !== fact || focus.tag !== "BUTTON")
      throw new Error("Source did not return to same actual fact trigger");
  }
}
await fs.writeFile(out + "/browser-evidence.json", JSON.stringify({
  state: "actual_Ego_component_checks_owner_pixels_pending", records,
  limitations: ["Historical B and unreviewed C inputs, not current scientific acceptance",
    "Representative safety/endpoint components only, not all physical pages/cross-browser",
    "Personal configuration visibility is not export/import/save/offline acceptance",
    "Still pixels are not full movie/independent aesthetic/24portals/threehosts/RC proof"],
}, null, 2) + "\n", { flag: "wx" });
console.log(JSON.stringify({ records: records.length, accepted: false }));
