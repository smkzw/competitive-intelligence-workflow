// Bounded sparse task on a completed ordinary candidate; never replay saves.
const fs = await import("node:fs/promises");
const path = await import("node:path");
const out = path.join(workflowRoot, ".artifacts/1007-b-sparse-visible-preview-v1");
const actual = JSON.parse(await fs.readFile(path.join(out, "actual.json"), "utf8"));
if (actual.pages !== 104 || actual.source_writes !== 0 || actual.current_writes !== 0)
  throw Error("Ordinary read-only render must complete first");
const page = (await taskSpace(2)).page("p1"), run = {states: [], failures: []};
await fs.mkdir(path.join(out, "qa"));
try {
  for (const width of [1440, 1600, 1920, 2560]) {
    await page.cdp("Emulation.setDeviceMetricsOverride", {width,
      height: width === 2560 ? 1440 : width === 1920 ? 1080 : 900,
      deviceScaleFactor: 1, mobile: false});
    await page.goto("file://" + path.join(out, "B/overview.html") +
      "?view=comparison&cmp=" + encodeURIComponent("efficacy::q-pruritus-nrs-ge4-improvement"));
    await page.waitForFunction(() => document.querySelector('#kz-chart-module [data-chart-type="line"]'));
    await page.evaluate(() => document.querySelector("#kz-filter-panel > summary")
      .scrollIntoView({block: "center"}));
    await page.click("#kz-filter-panel > summary");
    await page.click('button[data-filter-dimension="trial"][data-filter-value="nct04501666"]');
    await page.waitForFunction(() => JSON.parse(document.querySelector("#full-study-comparison")
      .dataset.questionRowIds).length === 2);
    await page.evaluate(() => document.querySelector("#kz-filter-panel > summary")
      .scrollIntoView({block: "center"}));
    await page.click("#kz-filter-panel > summary");
    const observed = await page.evaluate(() => {
      const host = document.querySelector("#full-study-comparison");
      const values = Array.from(document.querySelectorAll('.kz-chart-single-fact__value'))
        .map(el => ({text: el.textContent, visible: !!el.getClientRects().length}));
      const rows = window.__CHART_GROUPS__.flatMap(group => group.rows);
      const visibleSources = Array.from(document.querySelectorAll(
        '#kz-chart-module button[data-chart-evidence-open]')).filter(el => el.getClientRects().length)
        .map(el => el.getAttribute('data-chart-evidence-open'));
      return {width: innerWidth, values, visibleSources,
        rows: rows.map(row => ({id: row.row_id, value: row.value, unit: row.unit,
          renderable: row.renderable, study: row.trial_id})),
        queryIds: JSON.parse(host.dataset.questionRowIds),
        displayedIds: JSON.parse(host.dataset.displayedRowIds),
        overflow: document.documentElement.scrollWidth > innerWidth + 1,
        openRecords: document.querySelectorAll('.kz-b-study-records[open]').length};
    });
    run.states.push(observed);
    if (observed.overflow || !observed.openRecords || observed.values.filter(v => v.visible).length !== 2)
      run.failures.push(width + ': sparse results not immediately readable');
    if (observed.queryIds.slice().sort().join('|') !== observed.displayedIds.slice().sort().join('|'))
      run.failures.push(width + ': query scope changed');
    if (!observed.rows.some(row => row.value === 111 && row.unit === 'Participants') ||
        !observed.rows.some(row => row.value === 16 && row.renderable === false))
      run.failures.push(width + ': raw count or unresolved statistic changed');
    await page.screenshot({path: path.join(out, 'qa/B-sparse-' + width + '.png')});
  }
  if (run.failures.length) throw Error(run.failures.join('; '));
  run.state = 'SPARSE_VISIBILITY_RUNTIME_PASSED_OWNER_PIXELS_PENDING';
} catch (error) {
  run.state = 'FAILED_NOT_ACCEPTED'; run.error = String(error); throw error;
} finally {
  await fs.writeFile(path.join(out, 'qa/actual.json'), JSON.stringify(run, null, 2), {flag: 'wx'});
}
console.log({state: run.state, widths: run.states.length, failures: run.failures});
