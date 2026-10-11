// Read the frozen candidate's actual chart; no navigation or scientific writes.
const fs = await import("node:fs/promises");
const path = await import("node:path");
const page = (await taskSpace(2)).page("p1");
const actual = await page.evaluate(() => {
  if (!location.pathname.includes("1007-b-question-reading-preview-v3/B/overview.html") ||
      new URLSearchParams(location.search).get("cmp") !== "baseline::baseline:agecontinuous")
    throw Error("Expected frozen v3 actual baseline page");
  const el = document.querySelector("#kz-chart-module [data-chart-type]");
  const index = Number(el.closest(".kz-chart-module__group").dataset.groupIndex);
  const rows = window.__CHART_GROUPS__[index].rows;
  const option = echarts.getInstanceByDom(el).getOption();
  const glyphs = option.series.flatMap(series => series.data.flatMap((datum, position) =>
    datum._row_id ? [{row: datum._row_id, value: datum.value,
      category: option.xAxis[0].data[position], series: series.name}] : []));
  const errors = [];
  rows.forEach(row => {
    const points = glyphs.filter(point => point.row === row.row_id);
    if (points.length !== 1 || points[0].value !== row.value ||
        points[0].category !== row.trial_id.toUpperCase()) errors.push(row.row_id);
  });
  return {state: errors.length ? "FAILED" : "FACT_VALUE_STUDY_MAPPING_PASSED_LEGEND_REVISE",
    query: location.search, rows: rows.length, glyphs,
    seriesNames: option.series.map(series => series.name), errors};
});
await fs.writeFile(path.join(workflowRoot,
  ".artifacts/1007-b-question-reading-preview-v3/series-inspection-v1.json"),
  JSON.stringify(actual, null, 2), {flag: "wx"});
console.log({state: actual.state, rows: actual.rows, errors: actual.errors});
if (actual.errors.length) throw Error("Actual glyph fact/study mapping failed");
