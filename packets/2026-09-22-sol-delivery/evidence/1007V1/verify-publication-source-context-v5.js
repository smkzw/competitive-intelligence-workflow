// Native Ego checks on ordinary A/B renders; terminal records are never replayed.
const fs = await import('node:fs/promises');
const crypto = await import('node:crypto');
const root = globalThis.CI_WORKFLOW_ROOT;
if (root !== '/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow')
  throw Error('Explicit English root required');
const width = Number(globalThis.CI_WORKFLOW_WIDTH);
if (![1440,1600,1920,2560].includes(width)) throw Error('Desktop contract width required');
const output = root + '/.artifacts/1007-publication-source-context-v5';
const destination = output + `/browser-${width}.json`;
try { await fs.access(destination); throw Error('Terminal receipt already exists'); }
catch (e) { if (e.code !== 'ENOENT') throw e; }
const input = await fs.readFile(output + '/actual.json');
const receipt = {width,height:1080,space:2,
  candidate_receipt_sha256:crypto.createHash('sha256').update(input).digest('hex'),
  states:[],failures:[],dense_matrix:'NOT_RUN: source slice has four observations',
  current_edit_share:'NOT_RUN'};
const page = (await taskSpace(2)).page('p1');
try {
  await page.cdp('Emulation.setDeviceMetricsOverride',
    {width,height:1080,deviceScaleFactor:1,mobile:false});
  for (const kind of ['A','B']) {
    const entry = kind === 'A' ? 'clinical-portfolio.html' : 'overview.html';
    const url = `http://127.0.0.1:65046/${kind}/${entry}?view=comparison`;
    await page.goto(url);
    await page.waitForSelector('button[aria-label="查看数值 18.4 的数据依据"]');
    const first = await page.evaluate(() => {
      const host = document.querySelector('#full-study-comparison');
      const r = host.getBoundingClientRect();
      return {text:host.innerText,width:r.width,left:r.left,right:r.right,
        documentWidth:document.documentElement.scrollWidth,
        glyphs:[...host.querySelectorAll('button[aria-label^="查看数值"]')]
          .map(x=>x.getAttribute('aria-label'))};
    });
    for (const value of ['18.4','60','22','37.2'])
      if (!first.text.includes(value)) throw Error(kind + ': missing visible result ' + value);
    if (first.documentWidth > width + 1) throw Error(kind + ': document overflow');
    const firstShot = `${kind}-${width}-comparison.png`;
    await page.screenshot({path:output+'/'+firstShot});
    const evidence = [];
    for (const [value,printed] of [['18.4','14 (18.4)'],['60','45 (60.0)'],
                                 ['22','18 (22.0)'],['37.2','29 (37.2)']]) {
      const trigger = `button[aria-label="查看数值 ${value} 的数据依据"]`;
      await page.click(trigger);
      const drawer = kind === 'A' ? '#data-basis-panel' : '#kz-evidence-drawer';
      await page.waitForFunction(selector=>!document.querySelector(selector).hidden,drawer);
      const text = await page.evaluate(selector=>document.querySelector(selector).innerText,drawer);
      if (!text.includes(printed) || text.includes('逐事实来源待核'))
        throw Error(kind + ': exact printed source absent ' + printed);
      if (value === '18.4') await page.screenshot({path:output+`/${kind}-${width}-source.png`});
      await page.keyboard.press('Escape');
      const focus = await page.evaluate(selector=>document.activeElement===document.querySelector(selector),trigger);
      if (!focus) throw Error(kind + ': Esc lost actual glyph focus');
      evidence.push({value,printed,focus,text});
    }
    receipt.states.push({kind,url,first,firstShot,evidence});
    if (kind === 'B') {
      await page.click('#kz-filter-panel > summary');
      await page.click('button[data-filter-dimension="trial"][data-filter-value="prime"]');
      await page.waitForFunction(()=>document.querySelectorAll(
        '#full-study-comparison button[aria-label^="查看数值"]').length===2);
      const filtered = await page.evaluate(()=>({
        table:document.querySelector('#full-study-comparison').innerText,
        glyphs:[...document.querySelectorAll('#full-study-comparison button[aria-label^="查看数值"]')]
          .map(x=>x.getAttribute('aria-label'))}));
      if (filtered.glyphs.some(x=>x.includes('22 ')||x.includes('37.2 ')))
        throw Error('Filtered graph kept another study');
      await page.screenshot({path:output+`/B-${width}-filtered.png`});
      receipt.states.push({kind,state:'filtered',filtered});
    }
  }
  receipt.state = 'ACTUAL_SOURCE_GLYPH_TABLE_ESC_DESKTOP_SCOPE_PASSED';
} catch (error) {
  receipt.state='FAILED_NOT_ACCEPTED'; receipt.failures.push(String(error)); throw error;
} finally {
  await fs.writeFile(destination,JSON.stringify(receipt,null,2),{flag:'wx'});
}
console.log({width,state:receipt.state,states:receipt.states.length});
