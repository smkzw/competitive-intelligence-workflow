// Explicit production controls after two selector-family instrument failures.
// V1 completed A is retained within this exact frozen generation; no old-version PASS.
const fs = await import('node:fs/promises'), crypto = await import('node:crypto');
const root = globalThis.CI_WORKFLOW_ROOT;
if (!root) throw Error('Explicit English root required');
const out = root + '/.artifacts/1007-current33-shares-v1';
const bytes = await fs.readFile(out + '/verified.json'), verified = JSON.parse(bytes);
const digest = data => crypto.createHash('sha256').update(data).digest('hex');
if (verified.current_revision !== 33 || verified.exports.length !== 4)
  throw Error('Same-current four archives required');
const priorBytes = await fs.readFile(out + '/offline-actual-v1.json');
const prior = JSON.parse(priorBytes);
if (prior.revision !== 33 || prior.failures.length || prior.pages.length !== 1 ||
    prior.pages[0].tag !== 'A' || prior.pages[0].kind !== 'A' ||
    prior.export_proof_sha256 !== digest(bytes) || !prior.network_restored)
  throw Error('Only completed same-candidate A can resume');
const receipt = out + '/offline-actual-v3.json';
try {await fs.access(receipt); throw Error('Existing result; no overwrite or blind replay');}
catch (error) {if (error.code !== 'ENOENT') throw error;}
const page = (await taskSpace(11)).page('p1');
const run = {state:'RUNNING_NOT_ACCEPTED', revision:33, pages:prior.pages, failures:[],
  profile_id:'Profile 3', space:11, fresh_browser:false, profile_reused_from_current28:true,
  profile_created_for_this_candidate:false, storage_cleared:false, no_import_or_login:true,
  source_current_writes:0, scientific_acceptance:'NOT_RUN', export_proof_sha256:digest(bytes),
  recovery:{prior_sha256:digest(priorBytes),completed_same_candidate_entries:1,newly_executed_entries:0}};
async function persist() {await fs.writeFile(receipt, JSON.stringify(run, null, 2));}
async function probe() {
  return await page.evaluate(async () => {
    try {const r = await fetch('https://clinicaltrials.gov/api/v2/version',
      {mode:'no-cors',cache:'no-store'});
      return {response:true,type:r.type,status:r.status,navigator_online:navigator.onLine};
    } catch (error) {return {response:false,error:String(error),navigator_online:navigator.onLine};}
  });
}
async function source(kind, trigger) {
  await page.click(trigger);
  const drawer = kind === 'A' ? '#data-basis-panel' : '#kz-evidence-drawer';
  await page.waitForFunction(s => !document.querySelector(s).hidden, drawer);
  const text = await page.evaluate(s => document.querySelector(s).textContent, drawer);
  await page.keyboard.press('Escape');
  return {text,focus:await page.evaluate(s => document.activeElement.matches(s), trigger)};
}
async function selectQuestion(kind, row) {
  const question = await page.evaluate(({kind,row}) => {
    const w = window[kind === 'A' ? '__A_COMPARISON_WORKSPACE__' : '__B_COMPARISON_WORKSPACE__'];
    const rows = kind === 'A' ? window.__A_COMPARISON_ROWS__ : window.__FILTER_ROWS__;
    const id = kind === 'A' ? Object.keys(rows).find(id => rows[id].a_row_id === row ||
      rows[id].row_id === row) : rows.find(x => x.id === row)?.id;
    return w.columns.find(c => Object.values(c.cells).flat().includes(id))?.question_id;
  }, {kind,row});
  if (!question) throw Error('No fact in actual comparison workspace');
  await page.selectOption(kind === 'A' ? '[data-a-comparison-question]' :
    '[data-comparison-column]', question);
}
function trigger(kind, row) {
  return kind === 'A' ? `#full-study-comparison button[data-evidence-row-id="${row}"]` :
    `#full-study-comparison [data-primary-comparison-table] button[data-row-id="${row}"]`;
}
try {
  await page.cdp('Emulation.setDeviceMetricsOverride',
    {width:1920,height:1080,deviceScaleFactor:1,mobile:false});
  await page.cdp('Network.enable', {});
  await page.goto('file://' + out + '/' + verified.exports[0].moved_root + '/打开报告.html',
    {timeout:120000});
  run.online_control = await probe(); await persist();
  if (!run.online_control.response) throw Error('Actual file-origin online control failed');
  await page.cdp('Network.emulateNetworkConditions',
    {offline:true,latency:0,downloadThroughput:0,uploadThroughput:0});
  run.offline_control = await probe(); await persist();
  if (run.offline_control.response) throw Error('Traffic not actually blocked');
  for (const archive of verified.exports) {
    const tag = archive.reports.join(''), moved = out + '/' + archive.moved_root;
    const manifestBytes = await fs.readFile(moved + '/share-manifest.json');
    if (digest(manifestBytes) !== archive.manifest_sha256) throw Error('Moved manifest changed');
    const manifest = JSON.parse(manifestBytes);
    for (const kind of archive.reports) {
      if (run.pages.some(p => p.tag === tag && p.kind === kind)) continue;
      const selected = manifest.reports[kind];
      await page.goto('file://' + moved + '/打开报告.html', {timeout:120000});
      const href = await page.evaluate(k => [...document.querySelectorAll('a')].find(
        a => a.getAttribute('href')?.startsWith(k + '/'))?.getAttribute('href'), kind);
      if (href !== selected.entry_href) throw Error('Launcher must use committed saved view');
      await page.click(`a[href="${href}"]`);
      const table = kind === 'C' ? '.kz-c-criteria-table' : kind === 'B' ?
        '#full-study-comparison [data-primary-comparison-table]' : '#full-study-comparison table';
      await page.waitForSelector(table, {state:'visible',timeout:120000});
      await page.waitForFunction(() => document.fonts.status === 'loaded');
      const actual = await page.evaluate(() => ({revision:document.body.dataset.currentRevision,
        query:Object.fromEntries([...new URLSearchParams(location.search).keys()].map(
          k => [k,new URLSearchParams(location.search).getAll(k)])),
        width:document.documentElement.scrollWidth,
        editor_link:!!document.querySelector('a[href^="http://127.0.0.1"]')}));
      for (const key of Object.keys(selected.view_config.query))
        if (JSON.stringify(actual.query[key]) !== JSON.stringify(selected.view_config.query[key]))
          run.failures.push(tag + '/' + kind + ':saved query ' + key);
      const traffic = await probe();
      if (actual.revision !== '33' || actual.width > 1921 || actual.editor_link || traffic.response)
        run.failures.push(tag + '/' + kind + ':revision/offline/privacy');
      let reading = null;
      if (kind === 'B') {
        await page.waitForSelector('#kz-chart-0 svg', {state:'visible',timeout:120000});
        reading = await page.evaluate(() => {
          const groups = window.__CHART_GROUPS__, host = document.querySelector('#full-study-comparison');
          const ids = JSON.parse(host.dataset.displayedRowIds || '[]');
          const graphIds = groups.flatMap(g => g.rows.map(r => r.row_id));
          const tableIds = [...host.querySelectorAll('[data-primary-comparison-table] button[data-row-id]')]
            .map(b => b.dataset.rowId);
          const line = groups.findIndex((g,i) => g.rows.length === 24 &&
            document.querySelector('#kz-chart-' + i).dataset.chartType === 'line');
          const chart = line < 0 ? null : echarts.getInstanceByDom(document.querySelector('#kz-chart-' + line));
          const points = chart ? chart.getOption().series.flatMap(s => s.data)
            .filter(p => p.value != null).map(p => ({value:Array.isArray(p.value) ? p.value[1] : p.value,
              id:p._row_id,annotated:!!p.label && p.label.show === true})) : [];
          return {ids,graphIds,tableIds,line,points};
        });
        const canonical = ids => ids.slice().sort().join('|');
        if (reading.ids.length !== 32 || canonical(reading.ids) !== canonical(reading.graphIds) ||
            canonical(reading.ids) !== canonical(reading.tableIds) || reading.points.length !== 24 ||
            !reading.points.some(p => p.value === 57.7 && p.annotated))
          run.failures.push(tag + '/B:saved annotated line/same-query primary table');
        await page.evaluate(() => document.querySelector('#kz-chart-module').scrollIntoView({block:'start'}));
        await page.screenshot({path:out + '/offline-' + tag + '-B-default-panels-r33.png'});
      }
      const clearedRow = 'eff-030c369a7ea60f719d66';
      if (kind !== 'C') await selectQuestion(kind, clearedRow);
      else await page.fill('#kz-c-criteria-search', '样本量');
      const clearedTrigger = kind === 'C' ?
        '.kz-c-criteria-table button[data-evidence-open="c-nct04183335-sample-size"]' : trigger(kind, clearedRow);
      const original = await source(kind, clearedTrigger);
      if (!original.focus || !original.text.includes('用户清除') ||
          !original.text.includes(kind === 'C' ? '151' : '-48.32') || original.text.includes('user_cleared'))
        run.failures.push(tag + '/' + kind + ':clear/original/focus');
      let edited = null;
      if (kind !== 'C') {
        const row = 'eff-b0b587971df19e9d9cde';
        await selectQuestion(kind, row);
        const target = trigger(kind, row);
        const value = await page.evaluate(s => document.querySelector(s).textContent, target);
        edited = await source(kind, target); edited.current = value;
        if (!value.includes('-67.5') || !edited.text.includes('用户修订') ||
            !edited.text.includes('-67.5') || !edited.focus)
          run.failures.push(tag + '/' + kind + ':saved edit/focus');
      }
      const screenshot = 'offline-' + tag + '-' + kind + '-r33.png';
      await page.screenshot({path:out + '/' + screenshot});
      run.pages.push({tag,kind,actual,traffic,reading,original,edited,screenshot});
      run.recovery.newly_executed_entries++; await persist();
    }
  }
  if (run.pages.length !== 6 || run.failures.length) throw Error(run.failures.join(';') || 'Incomplete six entries');
  run.state = 'SIX_MOVED_OFFLINE_CURRENT33_ENTRIES_DEDICATED_PROFILE_AND_SOURCE_DISCLOSURES_PASSED';
} catch (error) {run.state = 'FAILED_NOT_ACCEPTED'; run.error = String(error); throw error;}
finally {
  await page.cdp('Network.emulateNetworkConditions',
    {offline:false,latency:0,downloadThroughput:-1,uploadThroughput:-1});
  run.network_restored = true; await persist();
}
console.log({state:run.state,pages:run.pages.length,failures:run.failures});
