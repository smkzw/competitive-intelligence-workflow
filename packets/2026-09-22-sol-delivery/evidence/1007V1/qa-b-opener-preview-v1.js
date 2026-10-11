// Actual production source buttons and glyphs at four widths, not a hand-written demo.
const fs = await import('node:fs/promises');
const root = globalThis.CI_WORKFLOW_ROOT;
if (!root) throw Error('Explicit English root required');
const out = root + '/.artifacts/1007-b-opener-preview-v1';
const proof = JSON.parse(await fs.readFile(out + '/actual.json'));
if (proof.pages !== 104 || proof.facts !== 1505 || proof.current_writes !== 0)
  throw Error('Normal current33 preview required');
const qa = out + '/qa'; await fs.mkdir(qa);
const page = (await taskSpace(2)).page('p1');
const url = 'file://' + out + '/B/overview.html?view=comparison&cmp=efficacy%3A%3Aq-pruritus-nrs-ge4-improvement';
const run = {state:'RUNNING_NOT_ACCEPTED',states:[],failures:[],currentWrites:0,sourceWrites:0};
async function source(row, expected, original, label) {
  const question = await page.evaluate(row => window.__B_COMPARISON_WORKSPACE__.columns
    .find(c => Object.values(c.cells).flat().includes(row))?.question_id, row);
  if (!question) throw Error('Source fact absent from real workspace');
  await page.selectOption('[data-comparison-column]', question);
  const selector = '#full-study-comparison [data-primary-comparison-table] button[data-row-id="' + row + '"]';
  const before = await page.evaluate(s => {
    const e = document.querySelector(s); window.__OWNER_OPENER__ = e;
    e.scrollIntoView({block:'center',inline:'nearest'});
    return {ids:document.querySelector('#full-study-comparison').dataset.displayedRowIds,
      query:location.search};
  }, selector);
  await page.click(selector);
  await page.waitForFunction(() => !document.querySelector('#kz-evidence-drawer').hidden);
  const evidence = await page.evaluate(() => ({
    text:document.querySelector('#kz-evidence-drawer').innerText,
    openerConnected:window.__OWNER_OPENER__.isConnected,
    ids:document.querySelector('#full-study-comparison').dataset.displayedRowIds}));
  await page.screenshot({path:qa + '/' + label + '-' + run.width + '.png'});
  await page.keyboard.press('Escape');
  const focus = await page.evaluate(() => ({closed:document.querySelector('#kz-evidence-drawer').hidden,
    actualOpener:document.activeElement === window.__OWNER_OPENER__,
    connected:window.__OWNER_OPENER__.isConnected,
    row:document.activeElement.getAttribute('data-row-id')}));
  run.states.push({label,width:run.width,before,evidence,focus});
  if (!evidence.text.includes(expected) || !evidence.text.includes(original) ||
      !evidence.openerConnected || evidence.ids !== before.ids || !focus.closed ||
      !focus.actualOpener || !focus.connected || focus.row !== row)
    run.failures.push(label + ':' + run.width + ':source/current/actual-focus');
}
try {
  for (const width of [1440,1600,1920,2560]) {
    run.width = width;
    await page.cdp('Emulation.setDeviceMetricsOverride', {width,
      height:width === 2560 ? 1440 : width === 1920 ? 1080 : 900,deviceScaleFactor:1,mobile:false});
    await page.goto(url, {timeout:120000});
    await page.waitForSelector('#full-study-comparison [data-primary-comparison-table]',
      {state:'visible',timeout:120000});
    await page.waitForSelector('#kz-chart-0 svg', {state:'visible',timeout:120000});
    const target = await page.evaluate(() => {
      const chartElement = document.querySelector('#kz-chart-0');
      chartElement.scrollIntoView({block:'center'});
      const chart = echarts.getInstanceByDom(chartElement), option = chart.getOption();
      const point = option.series[0].data[23], box = chartElement.getBoundingClientRect();
      const pixel = chart.convertToPixel({seriesIndex:0},point.value);
      const original = window.__EVIDENCE_DRAWER__.openByRowId;
      window.__OWNER_OPEN_COUNT__ = 0;
      window.__EVIDENCE_DRAWER__.openByRowId = function(id,trigger) {
        window.__OWNER_GLYPH_TRIGGER__ = trigger; window.__OWNER_OPEN_COUNT__++;
        return original.apply(this,arguments);
      };
      return {x:box.left+pixel[0],y:box.top+pixel[1],id:point._row_id,value:point.value};
    });
    if (target.value[1] !== 57.7) throw Error('Real week24 value changed');
    await page.mouse.click(target.x,target.y,{label:'打开真实第24周来源'});
    await page.waitForFunction(() => !document.querySelector('#kz-evidence-drawer').hidden);
    await page.keyboard.press('Escape');
    const glyph = await page.evaluate(() => ({closed:document.querySelector('#kz-evidence-drawer').hidden,
      same:document.activeElement === window.__OWNER_GLYPH_TRIGGER__,count:window.__OWNER_OPEN_COUNT__}));
    run.states.push({label:'glyph',width,target,glyph});
    if (!glyph.closed || !glyph.same || glyph.count !== 1) run.failures.push('glyph:' + width);
    await source('eff-030c369a7ea60f719d66','用户清除','-48.32','cleared');
    await source('eff-b0b587971df19e9d9cde','用户修订','-67.5','modified');
  }
  run.state = run.failures.length ? 'FAILED_NOT_ACCEPTED' : 'FOUR_WIDTH_GLYPH_CLEAR_EDIT_ACTUAL_OPENER_PASS';
} catch (error) {run.state='FAILED_NOT_ACCEPTED';run.error=String(error);throw error;}
finally {await fs.writeFile(qa+'/actual.json',JSON.stringify(run,null,2));}
console.log({state:run.state,states:run.states.length,failures:run.failures});
if (run.failures.length) throw Error(run.failures.join(';'));
