// Ordinary ABC candidate; reuse exact prior task actions, never old results.
const fs = await import('node:fs/promises');
const path = await import('node:path');
const crypto = await import('node:crypto');
const raw = await fs.readFile(path.join(workflowRoot,
  'packets/2026-09-22-sol-delivery/evidence/1007V1/qa-abc-task-geometry-v2.js'));
if (crypto.createHash('sha256').update(raw).digest('hex') !==
    '51fe8f0d33474a00647fc9607422705546a69364f95a68df1c569793018f6d0c')
  throw Error('Frozen prior instrument changed');
const relative = '.artifacts/1007-abc-axis-reading-v1';
const root = path.join(workflowRoot, relative);
const source = raw.toString().replaceAll('.artifacts/1007-abc-task-geometry-v2', relative);
await new(Object.getPrototypeOf(async function(){}).constructor)(
  'taskSpace', 'workflowRoot', source)(taskSpace, workflowRoot);

const page = (await taskSpace(2)).page('p1');
const run = {state:'RUNNING_NOT_ACCEPTED',states:[],failures:[],currentWrites:0};
async function record(report, label) {
  const actual = await page.evaluate(() => ({
    width:innerWidth,
    axes:window.__CHART_GROUPS__.flatMap((group,index) => {
      const instance = echarts.getInstanceByDom(document.querySelector('#kz-chart-'+index));
      if (!instance) return [];
      const option = instance.getOption();
      return ['xAxis','yAxis'].flatMap(dimension => (option[dimension] || [])
        .filter(axis => (axis.type === 'value' || axis.type === 'log') && axis.show !== false)
        .map(axis => ({group:index,dimension,type:axis.type,rotate:axis.axisLabel.rotate,
          width:axis.axisLabel.width,overflow:axis.axisLabel.overflow,
          fontSize:axis.axisLabel.fontSize})));
    }),
    overflow:document.documentElement.scrollWidth > innerWidth+1,
  }));
  run.states.push({report,label,...actual});
  if (!actual.axes.length || actual.overflow || actual.axes.some(axis =>
      axis.rotate !== 0 || axis.width != null || axis.overflow || axis.fontSize < 16))
    run.failures.push(report+':'+label+':'+actual.width+':numeric-ticks');
}
try {
  for (const report of ['A','B']) {
    const entry = report === 'A' ? 'clinical-portfolio.html' : 'overview.html';
    const url = 'file://'+path.join(root,report,entry)+
      '?view=comparison&cmp=efficacy%3A%3Aq-pruritus-nrs-ge4-improvement';
    for (const width of [1440,1600,1920,2560]) {
      await page.cdp('Emulation.setDeviceMetricsOverride',{width,
        height:width===2560?1440:width===1920?1080:900,deviceScaleFactor:1,mobile:false});
      await page.goto(url,{timeout:120000});
      await page.waitForFunction(() => window.__CHART_GROUPS__ &&
        document.querySelector('#kz-chart-0 svg'));
      await record(report,'dense');
      if (report === 'A') {
        for (const selector of ['details[data-comparison-disclosure]',
          'details[data-filter-dimension=product]']) {
          await page.evaluate(selector => document.querySelector(selector+' > summary')
            .scrollIntoView({block:'center'}),selector);
          if (!await page.evaluate(selector => document.querySelector(selector).open,selector))
            await page.click(selector+' > summary');
        }
        await page.click('[data-filter-dimension=product] button[data-filter-value=Nemolizumab]');
        await page.waitForFunction(() => JSON.parse(document.querySelector('#full-study-comparison')
          .dataset.displayedRowIds||'[]').length === 4);
        await page.click('details[data-comparison-disclosure] > summary');
      } else {
        await page.evaluate(() => document.querySelector('#kz-filter-panel > summary')
          .scrollIntoView({block:'center'}));
        await page.click('#kz-filter-panel > summary');
        await page.click('button[data-filter-dimension="trial"][data-filter-value="nct04501666"]');
        await page.waitForFunction(() => JSON.parse(document.querySelector('#full-study-comparison')
          .dataset.displayedRowIds||'[]').length === 2);
        await page.click('#kz-filter-panel > summary');
      }
      await record(report,'filtered');
    }
  }
  run.state = run.failures.length ? 'FAILED_NOT_ACCEPTED' : 'BOUNDED_NUMERIC_TICKS_PASS';
} catch(error) {
  run.state='FAILED_NOT_ACCEPTED'; run.error=String(error); throw error;
} finally {
  await fs.writeFile(path.join(root,'axis-options.json'),JSON.stringify(run,null,2),{flag:'wx'});
}
console.log({state:run.state,states:run.states.length,failures:run.failures});
if (run.failures.length) throw Error(run.failures.join('; '));
