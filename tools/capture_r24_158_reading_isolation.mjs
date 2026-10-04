// One bounded shared-modal root family on actual ordinary A/C candidates.
const fs = await import("node:fs/promises");
const crypto = await import("node:crypto");
const root = "/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow";
const out = root + "/.artifacts/r24-158-reading-isolation-20261003";
const page = (await taskSpace(12)).page("p1");
await fs.mkdir(out + "/screenshots-v2", { recursive: false });
await page.cdp("Emulation.setDeviceMetricsOverride", {
  width: 1600, height: 900, deviceScaleFactor: 1, mobile: false,
});
const records = [];
async function observe(kind, state) {
  const metrics = await page.evaluate(() => {
    const modal = [...document.querySelectorAll('[role="dialog"]')].find(n => !n.hidden);
    return {
      modal: modal?.id || null, modal_filter: modal ? getComputedStyle(modal).filter : null,
      main_filter: getComputedStyle(document.getElementById("main")).filter,
      main_inert: document.getElementById("main").inert,
      isolated: [...document.querySelectorAll(".kz-reading-background-isolated")]
        .map(n => n.id || n.tagName),
      original: modal?.textContent,
      focus: { tag: document.activeElement?.tagName,
        fact: document.activeElement?.getAttribute("data-evidence-open")
          || document.activeElement?.getAttribute("data-evidence-row-id") },
      scene: window.__KZ_SITE_SCENE__?.snapshot(),
      overflow: document.documentElement.scrollWidth > innerWidth,
    };
  });
  if (state !== "closed") {
    if (!metrics.main_inert || !metrics.main_filter.includes("blur(5px)")
        || metrics.modal_filter !== "none" || !metrics.scene?.reasons.includes("modal"))
      throw new Error("Actual modal isolation/film pause failed");
  } else if (metrics.main_inert || metrics.isolated.length || metrics.scene?.reasons.includes("modal")) {
    throw new Error("Actual modal close did not release reading/film state");
  }
  if (metrics.overflow) throw new Error("Modal introduced desktop overflow");
  const path = out + `/screenshots-v2/${kind}-${state}.png`;
  await page.screenshot({ path, scale: "css" });
  records.push({ kind, state, metrics, path: path.slice(root.length + 1),
    sha256: crypto.createHash("sha256").update(await fs.readFile(path)).digest("hex") });
}
for (const kind of ["a", "c"]) {
  const url = new URL("file://" + out + (kind === "a"
    ? "/a/safety.html?product=iptacopan&event=death"
    : "/c/endpoint-timepoint-matrix.html?criteria_q="
      + encodeURIComponent("Thrombotic and Haemolytic Events will in"))).href;
  await page.goto(url);
  let fact;
  if (kind === "a") {
    await page.waitForSelector(".kz-a-safety-observation", { state: "visible" });
    await page.click(".kz-a-safety-table summary");
    fact = await page.evaluate(() => [...document.querySelectorAll(".kz-a-safety-table tr[data-row-id]")]
      .find(n => n.dataset.filterMatch !== "false").dataset.rowId);
    await page.click(`[data-evidence-row-id="${fact}"]`);
  } else {
    await page.waitForFunction(() => window.__C_VISIBLE_CHART_ROW_IDS__?.length === 1);
    fact = await page.evaluate(() => window.__C_VISIBLE_CHART_ROW_IDS__[0]);
    await page.evaluate(id => document.querySelector(
      `[data-criterion-row-id="${id}"] button[data-evidence-open="${id}"]`
    ).scrollIntoView({ block: "center" }), fact);
    await page.click(`[data-criterion-row-id="${fact}"] button[data-evidence-open="${fact}"]`);
  }
  await page.waitForFunction(() => window.__KZ_SITE_SCENE__?.snapshot().reasons.includes("modal"));
  await observe(kind, "source");
  // Lifecycle events test disposal/reacquisition, not a claim of real bfcache navigation.
  await page.evaluate(() => window.dispatchEvent(new Event("pagehide")));
  const released = await page.evaluate(() => ({
    isolated: document.querySelectorAll(".kz-reading-background-isolated").length,
    inert: document.getElementById("main").inert,
  }));
  if (released.isolated || released.inert) throw new Error("Pagehide leaked reading lease");
  await page.evaluate(() => window.dispatchEvent(new Event("pageshow")));
  await page.waitForFunction(() => window.__KZ_SITE_SCENE__?.snapshot().reasons.includes("modal"));
  await observe(kind, "restored-open");
  records.at(-1).lifecycle_release = released;
  await page.keyboard.press("Escape");
  await page.waitForFunction(() => !window.__KZ_SITE_SCENE__?.snapshot().reasons.includes("modal"));
  await observe(kind, "closed");
  if (records.at(-1).metrics.focus.fact !== fact || records.at(-1).metrics.focus.tag !== "BUTTON")
    throw new Error("Same-fact keyboard return failed");
}
await fs.writeFile(out + "/browser-evidence.json", JSON.stringify({
  status: "actual_Ego_shared_reading_isolation_owner_pixels_pending", space: 12, page: "p1",
  width: 1600, records,
  limitations: ["A historical source, C unreviewed candidate", "Representative source paths only",
    "Lifecycle events simulated, not real bfcache navigation", "Not allpage/motion/independent aesthetics/RC"],
}, null, 2) + "\n", { flag: "wx" });
console.log(JSON.stringify({ records: records.length, same_fact_return: true, accepted: false }));
