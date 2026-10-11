// Geometry checks supplement, not replace, full task or owner pixel review.
const fs = await import("node:fs/promises");
const path = await import("node:path");
const page = (await taskSpace(2)).page("p1");
const out = path.join(workflowRoot, candidateRelative);
const run = {states: [], failures: [], currentWrites: 0};
await fs.mkdir(path.join(out, "paired-qa"));
try {
  for (const width of [1440, 1600, 1920, 2560]) {
    await page.cdp("Emulation.setDeviceMetricsOverride", {width, height: width === 2560 ?
      1440 : width === 1920 ? 1080 : 900, deviceScaleFactor: 1, mobile: false});
    await page.goto("file://" + path.join(out, "B/overview.html") +
      "?view=comparison&cmp=efficacy%3A%3Aq-pruritus-nrs-ge4-improvement");
    await page.waitForFunction(() => window.__CHART_GROUPS__ && window.__CHART_GROUPS__.some(g =>
      g.comparison_purpose === "clinical_question_descriptive"));
    const measured = await page.evaluate(() => {
      const module = document.querySelector("#kz-chart-module").getBoundingClientRect();
      const table = document.querySelector(".kz-b-comparison-details").getBoundingClientRect();
      const chart = document.querySelector("#kz-chart-module [data-chart-type]").getBoundingClientRect();
      return {width: innerWidth, height: innerHeight, module: {left:module.left,right:module.right},
        table: {left:table.left,top:table.top,bottom:table.bottom}, chartTop:chart.top,
        inline: module.right <= table.left + 1 && table.top < innerHeight - 200,
        overflow: document.documentElement.scrollWidth > innerWidth + 1};
    });
    run.states.push(measured);
    if (!measured.inline || measured.overflow) run.failures.push(width + ":graph/table reading geometry");
    await page.screenshot({path: path.join(out, "paired-qa", "dense-" + width + ".png")});
  }
  run.state = run.failures.length ? "REVISE_NOT_ACCEPTED" : "BOUNDED_GEOMETRY_PASS_PIXEL_REVIEW_REQUIRED";
} finally {
  await fs.writeFile(path.join(out, "paired-qa/actual.json"), JSON.stringify(run, null, 2));
}
console.log(run);
if (run.failures.length) throw Error(run.failures.join("; "));
