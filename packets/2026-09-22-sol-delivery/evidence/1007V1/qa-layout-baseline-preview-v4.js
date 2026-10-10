// Existing Ego184/p2 only. Normal A/B current-value preview; no source/save/profile writes.
const fs = await import("node:fs/promises"), crypto = await import("node:crypto");
const root = globalThis.CI_WORKFLOW_ROOT;
if (!root) throw new Error("Explicit English project required");
const out = root + "/.artifacts/1007-layout-baseline-preview-qa-v4";
const candidate = root + "/.artifacts/1007-baseline-landscape-preview-v3";
const manifestBytes = await fs.readFile(candidate + "/actual.json");
const manifest = JSON.parse(manifestBytes);
await fs.mkdir(out); // Exclusive attempt; never overwrite earlier failures.
const page = (await taskSpace(184)).page("p2");
const results = [];
const settle = async () => {
  await page.waitForFunction(() => document.readyState === "complete" && document.fonts.status === "loaded");
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
};
const open = async (report, relative) => {
  const bytes = await fs.readFile(candidate + "/" + report + "/" + relative);
  if (crypto.createHash("sha256").update(bytes).digest("hex") !== manifest.reports[report].render_hashes[relative])
    throw new Error("Frozen ordinary-render page changed");
  await page.goto("file://" + candidate + "/" + report + "/" + relative);
  await settle();
};
for (const width of [1440,1600,1920,2560]) {
  await page.cdp("Emulation.setDeviceMetricsOverride", {width,height:900,deviceScaleFactor:1,mobile:false});
  await open("A", "overview.html");
  const landscape = await page.evaluate(() => ({
    width:innerWidth, documentWidth:document.documentElement.scrollWidth,
    productIds:[...document.querySelectorAll(".kz-a-landscape-product")].map(e=>e.dataset.productId),
    bands:[...document.querySelectorAll(".kz-a-landscape-target-band")].map(b=>({
      target:b.dataset.landscapeTarget, open:b.open, x:b.getBoundingClientRect().x,
      y:b.getBoundingClientRect().y,height:b.getBoundingClientRect().height,
      cells:[...b.querySelector(".kz-a-landscape-band__cells").children].map(e=>({
        x:e.getBoundingClientRect().x,y:e.getBoundingClientRect().y,text:e.textContent})),
    })),
  }));
  if (landscape.documentWidth > width+1 || new Set(landscape.productIds).size !== 38 || landscape.bands.length !== 2)
    throw new Error("Whole landscape or viewport incomplete");
  for (const band of landscape.bands) {
    if (band.cells.length!==7 || Math.max(...band.cells.map(c=>c.y))-Math.min(...band.cells.map(c=>c.y))>1 ||
        !band.cells[4].text.trim() || band.height>110) throw new Error("Stage row geometry wrong");
  }
  await page.screenshot({path:out+`/A-overview-${width}.png`});
  const summary = "details.kz-a-landscape-target-band:first-of-type > summary";
  await page.focus(summary);
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => !document.querySelector(".kz-a-landscape-target-band").open);
  await settle();
  // Exercise the asynchronous resize renderer: it must preserve native closed state and focus.
  await page.cdp("Emulation.setDeviceMetricsOverride", {width:width-8,height:900,deviceScaleFactor:1,mobile:false});
  await settle();
  const closed = await page.evaluate(() => {
    const band=document.querySelector(".kz-a-landscape-target-band"), cells=band.querySelector(".kz-a-landscape-band__cells");
    return {open:band.open,visible:cells.checkVisibility(),height:cells.getBoundingClientRect().height,
      focus:document.activeElement===band.querySelector("summary")};
  });
  if (closed.open || closed.visible || closed.height !== 0 || !closed.focus)
    throw new Error("Native collapse/resize focus lost");
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => document.querySelector(".kz-a-landscape-target-band").open);
  await page.cdp("Emulation.setDeviceMetricsOverride", {width,height:900,deviceScaleFactor:1,mobile:false});
  await settle();
  await open("B", "baseline-demographics.html");
  const baseline = await page.evaluate(() => ({
    width:innerWidth,documentWidth:document.documentElement.scrollWidth,
    ids:[...new Set([...document.querySelectorAll(".kz-chart-table tbody tr")].map(e=>e.dataset.rowId))].sort(),
    evidenceIds:window.__EVIDENCE_DRAWER__.listRowIds().sort(),
    headings:[...document.querySelectorAll("h2,h3")].map(e=>e.textContent.trim()),
    falseEmpty:document.body.innerText.includes("暂无公开基线"),
  }));
  if (baseline.documentWidth>width+1 || baseline.ids.length!==48 || baseline.falseEmpty ||
      baseline.ids.some(id=>!baseline.evidenceIds.includes(id))) throw new Error("Actual demographics missing or false-empty");
  await page.screenshot({path:out+`/B-demographics-${width}.png`});
  const trigger = "button.kz-chart-evidence-hit >> nth=0";
  await page.focus(trigger);
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => window.__EVIDENCE_DRAWER__.isOpen());
  const evidence = await page.evaluate(() => ({
    rowId:window.__EVIDENCE_DRAWER__.getOpenRowId(),
    text:document.querySelector("#kz-evidence-view").innerText,
    externalLinks:[...document.querySelectorAll("#kz-evidence-view a")].map(e=>e.href),
  }));
  if (!baseline.ids.includes(evidence.rowId) || !evidence.text.includes("原来源原文"))
    throw new Error("Baseline glyph opened wrong or incomplete evidence");
  await page.screenshot({path:out+`/B-demographics-source-${width}.png`});
  await page.keyboard.press("Escape");
  const focusReturned = await page.evaluate(() => !window.__EVIDENCE_DRAWER__.isOpen() &&
    document.activeElement===document.querySelector("button.kz-chart-evidence-hit"));
  if (!focusReturned) throw new Error("Baseline source Esc failed real trigger focus");
  results.push({width,landscape,nativeCollapseResize:closed,baseline,evidence,focusReturned});
  await fs.writeFile(out+"/progress.json",JSON.stringify({state:"PARTIAL_NOT_FINAL",results},null,2));
}
await open("B", "baseline-overview.html");
const overviewIds = await page.evaluate(() => window.__EVIDENCE_DRAWER__.listRowIds().sort());
if (overviewIds.length !== 183) throw new Error("Baseline overview failed full 183-row reachability");
const proof={state:"FOUR_WIDTHS_A_STAGE_GEOMETRY_NATIVE_RESIZE_AND_B_DEMOGRAPHIC_SOURCE_PASSED_SCOPED",
  candidateManifestSha256:crypto.createHash("sha256").update(manifestBytes).digest("hex"),
  generation:manifest.source_generation,results,baselineOverviewCount:overviewIds.length,
  sourceWrites:0,saves:0,currentChanges:0,freshProfile:false,
  limits:"A49/B104 ordinary preview, unchanged1144 user facts. Representative geometry/baseline/source only; no new-source acceptance, all-state subjective visual, cross-browser, C, hosts or release."};
await fs.writeFile(out+"/actual.json",JSON.stringify(proof,null,2));
console.log(JSON.stringify({state:proof.state,widths:results.length,demographicRows:48,overviewRows:overviewIds.length}));
