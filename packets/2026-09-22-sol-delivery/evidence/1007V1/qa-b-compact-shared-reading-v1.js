// Reuse the terminal task path; new candidate and evidence, no history rewrite.
const fs = await import("node:fs/promises");
const crypto = await import("node:crypto");
const path = await import("node:path");
const base = path.join(workflowRoot,
  "packets/2026-09-22-sol-delivery/evidence/1007V1/qa-b-question-reading-preview-v4.js");
const raw = await fs.readFile(base);
if (crypto.createHash("sha256").update(raw).digest("hex") !==
    "d99b2e3958b06e8e4ea64dee8ec0d923585a869a6c6aad0d8533b878e798474e")
  throw Error("Previous task QA recipe changed");
const extra = `
    const identities = await page.evaluate(() => {
      return Array.from(document.querySelectorAll(".kz-b-shared-plot")).map(panel => {
        const el = panel.querySelector("[data-chart-type]");
        const index = Number(el.closest(".kz-chart-module__group").dataset.groupIndex);
        const rows = window.__CHART_GROUPS__[index].rows;
        const chart = echarts.getInstanceByDom(el), option = chart.getOption();
        const glyphs = option.series.flatMap(series => series.data.flatMap((point, position) =>
          point._row_id ? [{id: point._row_id, value: point.value,
            study: option.xAxis[0].data[position], series: series.name}] : []));
        const failures = [];
        rows.forEach(row => {
          const points = glyphs.filter(point => point.id === row.row_id);
          if (points.length !== 1 || points[0].value !== row.value ||
              points[0].study !== row.trial_id.toUpperCase()) failures.push(row.row_id);
        });
        const names = option.series.map(series => series.name);
        const legend = Array.from(panel.querySelectorAll(".kz-chart-legend__item"))
          .map(item => item.textContent);
        if (new Set(names).size !== names.length) failures.push("ambiguous series names");
        if (JSON.stringify(names) !== JSON.stringify(legend)) failures.push("legend drift");
        const header = panel.querySelector(".kz-b-shared-plot__identities");
        const visibleIds = (header?.textContent || "").match(/NCT[0-9]+/g) || [];
        const studyCount = new Set(rows.map(row => row.trial_id)).size;
        if (visibleIds.length !== studyCount || new Set(visibleIds).size !== studyCount)
          failures.push("repeated or missing study header");
        return {rowCount: rows.length, studyCount, visibleIds, names, legend, glyphs, failures,
          panelWidth: panel.getBoundingClientRect().width,
          plotWidth: el.getBoundingClientRect().width};
      });
    });
    shared.identities = identities;
    identities.forEach(item => run.failures.push(...item.failures));
`;
let source = raw.toString().replaceAll(".artifacts/1007-b-question-reading-preview-v3",
  ".artifacts/1007-b-compact-shared-reading-v1");
// Insert assertions into the original locked recipe, without changing its checks.
source = source.replace('await new (Object.getPrototypeOf(async function(){}).constructor)(',
  'const instrumented = source.replace(\'const shared = await record("shared-baseline");\', ' +
  '\'const shared = await record("shared-baseline");\' + extra);\n' +
  'await new (Object.getPrototypeOf(async function(){}).constructor)(')
  .replace('"taskSpace", "workflowRoot", source)(taskSpace, workflowRoot);',
    '"taskSpace", "workflowRoot", instrumented)(taskSpace, workflowRoot);');
await new (Object.getPrototypeOf(async function(){}).constructor)(
  "taskSpace", "workflowRoot", "extra", source)(taskSpace, workflowRoot, extra);
