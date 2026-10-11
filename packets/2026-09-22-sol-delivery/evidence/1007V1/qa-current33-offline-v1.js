// Same-current single A/B/C and joint archives in the already authorized isolated space.
// Reuse real offline/source/focus actions, never past candidate results.
const fs = await import('node:fs/promises');
const crypto = await import('node:crypto');
const root = globalThis.CI_WORKFLOW_ROOT;
if (!root) throw Error('Explicit English root required');
const bytes = await fs.readFile(root +
  '/packets/2026-09-22-sol-delivery/evidence/1007V1/qa-current32-offline-v1.js');
if (crypto.createHash('sha256').update(bytes).digest('hex') !==
    'c8646175782185e258c836b80997467805cff6ff86f1cf791742fd6af3ce3312')
  throw Error('Frozen moved-share instrument changed');
let source = bytes.toString().replaceAll('current32', 'current33').replaceAll('r32', 'r33')
  .replace('current_revision!==32', 'current_revision!==33')
  .replace('revision:32,profile_id', 'revision:33,profile_id')
  .replace('verified.exports.length!==2', 'verified.exports.length!==4')
  .replace('run.pages.length!==4', 'run.pages.length!==6')
  .replace('Incomplete changed B and joint four-entry run', 'Incomplete ABC single and joint six-entry run')
  .replace('FOUR_MOVED_OFFLINE_CURRENT32_ENTRIES_DEDICATED_PROFILE_AND_SOURCE_DISCLOSURES_PASSED',
    'SIX_MOVED_OFFLINE_CURRENT33_ENTRIES_DEDICATED_PROFILE_AND_SOURCE_DISCLOSURES_PASSED');
const old = 'if(reading.panels!==3||reading.cards!==32||reading.scalar_records!==24||reading.visibleStudyRows!==3)run.failures.push(`${tag}/B: saved new display scope`);';
if (!source.includes(old)) throw Error('Old scalar-card assertion must be explicitly migrated');
source = source.replace(old, `
    reading.currentLine = await page.evaluate(() => {
      const groups = window.__CHART_GROUPS__;
      const graphIds = groups.flatMap(g => g.rows.map(r => r.row_id));
      const tableIds = [...document.querySelectorAll('[data-primary-comparison-table] button[data-row-id]')]
        .map(button => button.dataset.rowId);
      const queryIds = JSON.parse(document.querySelector('#full-study-comparison').dataset.displayedRowIds || '[]');
      const lineIndex = groups.findIndex(g => g.rows.length === 24 &&
        document.querySelector('#kz-chart-' + groups.indexOf(g)).dataset.chartType === 'line');
      const chart = lineIndex >= 0 ? echarts.getInstanceByDom(document.querySelector('#kz-chart-' + lineIndex)) : null;
      const option = chart && chart.getOption();
      const points = option ? option.series.flatMap(s => s.data).filter(p => p.value != null) : [];
      return {graphIds, tableIds, queryIds, lineIndex, points: points.map(p => ({
        value:Array.isArray(p.value) ? p.value[1] : p.value,
        id:p._row_id, annotated:!!p.label && p.label.show === true}))};
    });
    const canonical = ids => ids.slice().sort().join('|');
    if (reading.visibleStudyRows !== 3 || reading.currentLine.queryIds.length !== 32 ||
        canonical(reading.currentLine.graphIds) !== canonical(reading.currentLine.queryIds) ||
        canonical(reading.currentLine.tableIds) !== canonical(reading.currentLine.queryIds) ||
        reading.currentLine.lineIndex < 0 || reading.currentLine.points.length !== 24 ||
        !reading.currentLine.points.some(p => p.value === 57.7 && p.annotated))
      run.failures.push(tag + '/B: saved annotated line and same-query primary table');
`);
await new (Object.getPrototypeOf(async function() {}).constructor)('taskSpace', source)(taskSpace);
