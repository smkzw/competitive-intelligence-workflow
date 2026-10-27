// Read-only visible article capture; source text is data, never executable instructions.
try {
  const t = await taskSpace(config.space), p = t.page(config.page || 'p1');
  if(await p.url()!==config.url)await p.goto(config.url, {waitUntil: 'domcontentloaded'});
  await p.waitForFunction(() => !!document.body?.innerText?.trim(), undefined, {timeout: 30000});
  const doc = await p.evaluate(() => {
    const visible = e => e && (e.checkVisibility ? e.checkVisibility() : !!e.getClientRects().length);
    const first = selectors => selectors.map(s => document.querySelector(s)).find(visible);
    const article = first(['#js_content', 'article', 'main', '[role=main]']) || document.body;
    const heading = first(['#activity-name', 'h1']);
    const publisher = first(['#js_name']);
    const date = first(['#publish_time', 'time']);
    const body=article.innerText;
    const header=[heading?.innerText?.trim(),publisher?.innerText?.trim(),date?.innerText?.trim()]
      .filter(s=>s&&!body.includes(s)).join('\n');
    const canonicalTitle = document.querySelector('meta[property="og:title"]')?.content?.trim();
    return {url: location.href, title: canonicalTitle || heading?.innerText?.trim() || document.title,
      text: header ? header+'\n'+body : body, publisher: publisher?.innerText?.trim() || '',
      published_at: date?.getAttribute('datetime') || '', date_text: date?.innerText || '',
      fetched_at: new Date().toISOString()};
  });
  console.log('CIW_CHINA_PAGE:' + JSON.stringify(doc));
  console.log('CIW_CHINA_END:' + JSON.stringify({status: 'ok'}));
} catch(e) {
  const control = /EGO_.*(?:CONTROL|OWNERSHIP|INACTIVE|UNASSIGNED|NOT_FOUND)|user control/i.test(String(e?.message||''));
  console.log('CIW_CHINA_END:' + JSON.stringify({status: control ? 'user_control' : 'failed', error_type:e?.name||'Error'}));
}
