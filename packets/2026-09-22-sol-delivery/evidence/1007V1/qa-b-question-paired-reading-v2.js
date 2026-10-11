// Same candidate: paired reading plus actual new descriptive glyph/source action.
const fs = await import("node:fs/promises");
const path = await import("node:path");
const raw = await fs.readFile(path.join(workflowRoot,
  "packets/2026-09-22-sol-delivery/evidence/1007V1/qa-b-question-paired-reading-v1.js"), "utf8");
await new (Object.getPrototypeOf(async function(){}).constructor)(
  "taskSpace", "workflowRoot", "candidateRelative", raw)(taskSpace, workflowRoot, candidateRelative);
const page = (await taskSpace(2)).page("p1");
const out = path.join(workflowRoot, candidateRelative);
const result = {states: [], failures: []};
try {
  for (const width of [1440, 1600, 1920, 2560]) {
    await page.cdp("Emulation.setDeviceMetricsOverride", {width, height: width === 2560 ?
      1440 : width === 1920 ? 1080 : 900, deviceScaleFactor: 1, mobile: false});
    await page.goto("file://" + path.join(out, "B/overview.html") +
      "?view=comparison&cmp=efficacy%3A%3Aq-pruritus-nrs-ge4-improvement");
    await page.waitForFunction(() => window.__CHART_GROUPS__ && window.__CHART_GROUPS__.some(g =>
      g.comparison_purpose === "clinical_question_descriptive" && g.rows.length === 4));
    const target = await page.evaluate(() => {
      const groupIndex = window.__CHART_GROUPS__.findIndex(g =>
        g.comparison_purpose === "clinical_question_descriptive" && g.rows.length === 4);
      const el = document.querySelector("#kz-chart-" + groupIndex);
      el.scrollIntoView({block: "center"});
      const chart = echarts.getInstanceByDom(el), option = chart.getOption();
      let found;
      option.series.forEach((series, seriesIndex) => series.data.forEach((point, dataIndex) => {
        if (point._row_id === "eff-7a82bfadf17f4066f213") found = {seriesIndex, dataIndex, point};
      }));
      if (!found || found.point.value !== 75) throw Error("wrong source-posted point");
      const pixel = chart.convertToPixel({seriesIndex:found.seriesIndex},
        [found.dataIndex, found.point.value / 2]), rect = el.getBoundingClientRect();
      return {x:rect.left+pixel[0], y:rect.top+pixel[1], id:found.point._row_id};
    });
    await page.mouse.click(target.x, target.y, {label:"查看真实人数来源"});
    await page.waitForFunction(() => !document.querySelector("#kz-evidence-drawer").hidden);
    const observed = await page.evaluate(() => ({
      text: document.querySelector("#kz-evidence-drawer").innerText,
      id: document.querySelector("#kz-evidence-drawer").dataset.rowId}));
    if (!observed.text.includes("75") || !observed.text.includes("原文定位"))
      result.failures.push(width+":wrong source evidence");
    await page.screenshot({path:path.join(out,"paired-qa","count-source-"+width+".png")});
    await page.keyboard.press("Escape");
    const focus = await page.evaluate(() => ({hidden:document.querySelector("#kz-evidence-drawer").hidden,
      id:document.activeElement.getAttribute("data-chart-evidence-open")}));
    if (!focus.hidden || focus.id !== target.id) result.failures.push(width+":glyph focus return");
    result.states.push({width, clickedFact:target.id, evidence:observed, focus});
  }
  result.state=result.failures.length?"FAILED_NOT_ACCEPTED":"BOUNDED_GLYPH_SOURCE_FOCUS_PASS";
} finally {
  await fs.writeFile(path.join(out,"paired-qa/source-interaction.json"),JSON.stringify(result,null,2));
}
console.log({state:result.state,states:result.states.length,failures:result.failures});
if(result.failures.length)throw Error(result.failures.join("; "));
