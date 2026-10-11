// One normal candidate, one authorized Ego space; no saved/current writes.
const fs = await import("node:fs/promises");
const path = await import("node:path");
const root = workflowRoot;
if (path.basename(root) !== "competitive-intelligence-workflow")
  throw Error("Explicit English project root is required");
const out = path.join(root, ".artifacts/1007-b-question-reading-preview-v1");
const page = (await taskSpace(2)).page("p1");
const home = "file://" + path.join(out, "B/overview.html");
const comparison = home + "?view=comparison&cmp=" +
  encodeURIComponent("efficacy::q-pruritus-nrs-ge4-improvement");
const run = {state: "RUNNING_NOT_ACCEPTED", states: [], failures: []};
await fs.mkdir(path.join(out, "qa"));

async function record(label) {
  const observed = await page.evaluate(() => {
    const host = document.querySelector("#full-study-comparison");
    const plots = (document.body.dataset.comparisonView === "comparison"
      ? Array.from(document.querySelectorAll("#kz-chart-module [data-chart-type]")) : [])
      .map(el => {
        const chart = echarts.getInstanceByDom(el);
        const group = window.__CHART_GROUPS__[Number(el.getAttribute("data-group-index"))];
        const rect = el.getBoundingClientRect();
        return {kind: el.dataset.chartType, rowIds: group.rows.map(r => r.row_id),
          studies: Array.from(new Set(group.rows.map(r => r.trial_id))),
          crossTrial: group.cross_trial, instantiated: !!chart,
          tableIds: Array.from(el.closest(".kz-chart-module__group")
            .querySelectorAll("table tr[data-row-id]")).map(tr => tr.dataset.rowId),
          top: rect.top, width: rect.width, height: rect.height};
      });
    return {width: innerWidth, height: innerHeight, mode: document.body.dataset.comparisonView,
      overflow: document.documentElement.scrollWidth > innerWidth + 1,
      queryIds: JSON.parse(host.dataset.questionRowIds || "[]"),
      displayedIds: JSON.parse(host.dataset.displayedRowIds || "[]"),
      findings: document.querySelectorAll(".kz-b-finding").length,
      findingsVisible: !!document.querySelector(".kz-b-findings:not([hidden])"), plots};
  });
  run.states.push({label, ...observed});
  if (observed.overflow) run.failures.push(label + ":page overflow");
  if (observed.mode === "comparison" && observed.queryIds.slice().sort().join("|") !==
    observed.displayedIds.slice().sort().join("|")) run.failures.push(label + ":query/table mismatch");
  await page.screenshot({path: path.join(out, "qa", "B-" + label + "-" + observed.width + ".png")});
  await fs.writeFile(path.join(out, "qa/actual.json"), JSON.stringify(run, null, 2));
  return observed;
}

try {
  for (const width of [1440, 1600, 1920, 2560]) {
    await page.cdp("Emulation.setDeviceMetricsOverride", {width, height: width === 2560 ? 1440 :
      width === 1920 ? 1080 : 900, deviceScaleFactor: 1, mobile: false});
    await page.goto(home, {timeout: 120000});
    await page.waitForFunction(() => document.fonts.status === "loaded" && window.__CHART_SYNC__,
      undefined, {timeout: 120000});
    const summary = await record("home");
    if (!summary.findings || !summary.findingsVisible) run.failures.push("real home findings missing");
    const rawHeadings = await page.evaluate(() => Array.from(document.querySelectorAll(
      ".kz-b-findings summary")).map(n => n.textContent).filter(t => /Percentage of Participants/.test(t)));
    if (rawHeadings.length) run.failures.push("raw English home heading");
    await page.goto(comparison, {timeout: 120000});
    await page.waitForFunction(() => document.querySelector('#kz-chart-module [data-chart-type="line"]'),
      undefined, {timeout: 120000});
    const dense = await record("dense");
    if (dense.findingsVisible) run.failures.push("home findings leaked into comparison task");
    const line = dense.plots.find(p => p.kind === "line" && p.rowIds.length === 24);
    if (!line || !line.instantiated || line.rowIds.slice().sort().join("|") !==
      line.tableIds.slice().sort().join("|")) run.failures.push("24 source visits/graph/table mismatch");
    await page.click(".kz-b-comparison-details > summary");
    await record("complete-table");
    await page.click(".kz-b-comparison-details > summary");
    const target = await page.evaluate(() => {
      const el = Array.from(document.querySelectorAll('#kz-chart-module [data-chart-type="line"]'))
        .find(el => window.__CHART_GROUPS__[Number(el.dataset.groupIndex)].rows.length === 24);
      el.scrollIntoView({block: "center"});
      const chart = echarts.getInstanceByDom(el), data = chart.getOption().series[0].data;
      const last = data[data.length - 1], pixel = chart.convertToPixel({seriesIndex: 0}, last.value);
      const rect = el.getBoundingClientRect();
      return {x: rect.left + pixel[0], y: rect.top + pixel[1], row: last._row_id};
    });
    await page.mouse.click(target.x, target.y, {label: "打开末次观察原文"});
    await page.waitForFunction(() => !document.querySelector("#kz-evidence-drawer").hidden,
      undefined, {timeout: 15000});
    const evidence = await page.evaluate(() => document.querySelector("#kz-evidence-drawer").innerText);
    if (!evidence.includes("57.7") || !evidence.includes("原文定位")) run.failures.push("wrong point source");
    await record("source");
    await page.keyboard.press("Escape");
    await page.click("#kz-filter-panel > summary");
    await page.click('button[data-filter-dimension="trial"][data-filter-value="nct04501666"]');
    await page.waitForFunction(() => JSON.parse(document.querySelector("#full-study-comparison")
      .dataset.questionRowIds || "[]").length === 2, undefined, {timeout: 15000});
    await page.click("#kz-filter-panel > summary");
    await record("filtered-sparse");
    // Existing actual baseline frame: multiple source-bound studies, no new
    // clinical efficacy equivalence and no inferred product/arm relationship.
    await page.goto(home + "?view=comparison&cmp=" +
      encodeURIComponent("baseline::baseline:agecontinuous"), {timeout: 120000});
    await page.waitForFunction(() => window.__CHART_GROUPS__ && window.__CHART_GROUPS__.some(g =>
      g.cross_trial && new Set(g.rows.map(r => r.trial_id)).size > 1), undefined, {timeout: 120000});
    const shared = await record("shared-baseline");
    const positive = shared.plots.filter(p => p.crossTrial && p.studies.length > 1);
    if (!positive.length || positive.some(p => !p.instantiated ||
      p.rowIds.slice().sort().join("|") !== p.tableIds.slice().sort().join("|")))
      run.failures.push("existing multi-study baseline frame/graph/table mismatch");
  }
  run.sharedPositive = "EXISTING_DESCRIPTIVE_BASELINE_FRAME_NOT_NEW_EFFICACY_OR_DRUG_IDENTITY_ACCEPTANCE";
  if (run.failures.length) throw Error(run.failures.join("; "));
  run.state = "BOUNDED_TASK_RUNTIME_PASSED_OWNER_PIXEL_REVIEW_PENDING";
} catch (error) {
  run.state = "FAILED_NOT_ACCEPTED"; run.error = String(error); throw error;
} finally {
  await fs.writeFile(path.join(out, "qa/actual.json"), JSON.stringify(run, null, 2));
}
console.log({state: run.state, states: run.states.length, failures: run.failures});
