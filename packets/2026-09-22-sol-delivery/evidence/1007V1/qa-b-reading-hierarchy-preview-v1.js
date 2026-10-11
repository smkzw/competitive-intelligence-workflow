// Normal production preview, existing authorized Ego space; no factual writes.
const fs = await import("node:fs/promises"), crypto = await import("node:crypto");
const root = globalThis.CI_WORKFLOW_ROOT;
if (root !== "/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow")
  throw Error("Explicit English project required");
const out = root + "/.artifacts/1007-b-reading-hierarchy-preview-v1";
const bytes = await fs.readFile(out + "/actual.json"), proof = JSON.parse(bytes);
if (proof.facts !== 1505 || proof.current_writes !== 0) throw Error("Wrong candidate");
await fs.mkdir(out + "/qa");
const page = (await taskSpace(2)).page("p1");
const base = "file://" + out + "/B/overview.html";
const suffix = "?view=comparison&cmp=" + encodeURIComponent("efficacy::q-pruritus-nrs-ge4-improvement");
const run = {state: "RUNNING_NOT_ACCEPTED", states: [], failures: [], owner_pixels: "PENDING",
  render_proof_sha256: crypto.createHash("sha256").update(bytes).digest("hex"),
  limits: "One normal B page family, four desktop widths; not whole product/current/science/share/RC"};
async function ready(compare) {
  await page.waitForFunction(want => document.fonts.status === "loaded" &&
    (!want || document.querySelector("#full-study-comparison tbody tr")), compare, {timeout: 120000});
  await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
}
async function inspect(label) {
  const state = await page.evaluate(() => {
    const host = document.querySelector("#full-study-comparison"), summary = document.querySelector("[data-summary-observations]");
    const visible = n => n.checkVisibility() && !n.closest("details:not([open]) :not(summary)");
    const heads = [...document.querySelectorAll("main h1,main h2,main h3,main h4")].filter(visible);
    return {width: innerWidth, mode: document.body.dataset.comparisonView,
      overflow: document.documentElement.scrollWidth > innerWidth + 1,
      activeNav: [...document.querySelectorAll('.site-header__nav a[aria-current="page"]')].map(n => n.textContent),
      summaryExpanded: summary.open, headings: heads.map(n => n.textContent),
      rawEnglishHeadings: heads.filter(n => /(?:[A-Za-z]+\s+){10}/.test(n.textContent)).map(n => n.textContent),
      query: host.dataset.questionRowIds ? JSON.parse(host.dataset.questionRowIds).sort() : [],
      displayed: host.dataset.displayedRowIds ? JSON.parse(host.dataset.displayedRowIds).sort() : [],
      chartIds: [...new Set(window.__CHART_GROUPS__.flatMap(g => g.rows.map(r => r.row_id)))].sort(),
      records: [...document.querySelectorAll(".kz-b-study-records")].map(n => ({open: n.open,
        count: n.querySelectorAll(".kz-chart-module__group").length, summary: n.querySelector("summary").textContent})),
      visibleStudies: [...host.querySelectorAll("tbody tr")].filter(n => getComputedStyle(n).display !== "none").length,
      times: [...host.querySelectorAll(".kz-comparison-fact__time")].map(n => n.textContent),
      studyNames: [...host.querySelectorAll("tbody th")].map(n => n.textContent),
      measurementNames: [...document.querySelectorAll(".kz-b-measurement-panel > h4")].map(n => n.textContent),
      clearOrZero: [...host.querySelectorAll(".kz-comparison-fact__value")].map(n => n.textContent),
    };
  });
  if (state.overflow || state.rawEnglishHeadings.length) run.failures.push(label + " overflow/raw title");
  if (label === "home" && (state.summaryExpanded || JSON.stringify(state.activeNav) !== '["首页"]'))
    run.failures.push("home is not a summary");
  if (label !== "home") {
    if (JSON.stringify(state.activeNav) !== '["全研究横比"]') run.failures.push("comparison navigation");
    if (JSON.stringify(state.query) !== JSON.stringify(state.displayed) ||
        JSON.stringify(state.query) !== JSON.stringify(state.chartIds)) run.failures.push("fact coverage");
    if (state.times.some(t => /\b(?:week|baseline)\b/i.test(t))) run.failures.push("untranslated visit");
    if (label === "comparison" && (state.query.length !== 32 || state.visibleStudies !== 3 ||
        state.records.some(r => r.open))) run.failures.push("comparison defaults/coverage");
    if (label === "filtered" && (state.query.length !== 2 || state.visibleStudies !== 1))
      run.failures.push("filtered membership");
  }
  run.states.push({label, ...state});
  await fs.writeFile(out + "/qa/actual.json", JSON.stringify(run, null, 2));
  await page.screenshot({path: out + `/qa/B-${label}-${state.width}.png`});
  return state;
}
try {
  for (const width of [1440, 1600, 1920, 2560]) {
    await page.cdp("Emulation.setDeviceMetricsOverride", {width, height: 1000, deviceScaleFactor: 1, mobile: false});
    await page.goto(base, {timeout: 120000}); await ready(false); await inspect("home");
    await page.click('.site-header__nav a[href="overview.html?view=comparison"]');
    await ready(true); const matched = await inspect("comparison");
    await page.click('.kz-b-study-records > summary >> nth=0');
    await inspect("expanded-source-records");
    const scope = await page.evaluate(() => ({
      observations: document.querySelector('.kz-b-study-records').querySelectorAll('[data-comparison-compact]').length,
      englishTitleRetained: document.querySelector('.kz-b-study-original-title').textContent,
      sourceButtons: document.querySelectorAll('.kz-b-study-records [data-chart-evidence-open]').length,
    }));
    if (scope.observations !== 28 || !scope.englishTitleRetained) run.failures.push("full originals inaccessible");
    run.states.push({label: "originals", width, ...scope});
    await page.click("#kz-filter-panel > summary");
    await page.click('button[data-filter-dimension="trial"][data-filter-value="nct04501666"]');
    await ready(true); await inspect("filtered");
    await page.click('button[data-filter-dimension="trial"][data-filter-value="nct04501666"]');
    await page.click("#kz-filter-panel > summary"); await ready(true);
    const trigger = `#full-study-comparison [data-evidence-open="${matched.query[0]}"]`;
    await page.click(trigger); await page.waitForFunction(() => !document.querySelector("#kz-evidence-drawer").hidden);
    const source = await page.evaluate(() => document.querySelector("#kz-evidence-drawer").innerText);
    await page.screenshot({path: out + `/qa/B-source-${width}.png`});
    await page.keyboard.press("Escape");
    if (!source.includes("原文定位") || !(await page.evaluate(s => document.activeElement.matches(s), trigger)))
      run.failures.push("source focus");
    run.states.push({label: "source-Esc", width, sourceLocator: source.includes("原文定位"), actualFocus: true});
  }
  if (run.failures.length) throw Error(run.failures.join("; "));
  run.state = "B_READING_TASK_RUNTIME_PASSED_OWNER_AND_INDEPENDENT_VISUAL_PENDING";
} catch (error) {
  run.state = "FAILED_NOT_ACCEPTED"; run.error = String(error); throw error;
} finally {
  await fs.writeFile(out + "/qa/actual.json", JSON.stringify(run, null, 2));
}
console.log({state: run.state, states: run.states.length, failures: run.failures});
