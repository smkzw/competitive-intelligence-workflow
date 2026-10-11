// Official rendered article DOM via the existing Ego page; never session data.
const fs = await import('node:fs/promises');
const crypto = await import('node:crypto');
const root = globalThis.CI_WORKFLOW_ROOT;
if (root !== '/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow')
  throw Error('Explicit English root required');
const page = (await taskSpace(2)).page('p1');
if (await page.url() !== 'https://pmc.ncbi.nlm.nih.gov/articles/PMC11840645/')
  throw Error('Expected ordinary official source page');
const capture = await page.evaluate(() => {
  const original = document.querySelector('article');
  if (!original) throw Error('Actual official article absent');
  const article = original.cloneNode(true);
  article.querySelectorAll('script,style,iframe').forEach(node=>node.remove());
  article.querySelectorAll('*').forEach(node=>{
    for (const name of node.getAttributeNames()) {
      if (name.startsWith('on') || ['nonce','integrity'].includes(name))
        node.removeAttribute(name);
    }
  });
  return {url:location.href, acquired_at:new Date().toISOString(),
    article_html:article.outerHTML, article_text:original.innerText,
    tables:original.querySelectorAll('table').length};
});
const bytes = Buffer.from(capture.article_html, 'utf8');
const visible = await page.evaluate(() => ({url:location.href,
  title:document.title, tables:document.querySelectorAll('table').length,
  body_chars:document.body.innerText.length,
  matching_study:document.body.innerText.includes('OLYMPIA 1'),
  matching_pmid:document.body.innerText.includes('39602139'),
  headings:[...document.querySelectorAll('h2,h3')].map(node=>node.textContent.trim())}));
const html = bytes.toString('utf8');
if (!html.includes('39602139') ||
    !html.includes('OLYMPIA 1') || !html.includes('<table') || visible.tables < 2)
  throw Error('Response did not contain the expected actual primary tables');
const out = root + '/.artifacts/1007-nemolizumab-primary-browser-capture-v1';
await fs.mkdir(out); // Never overwrite prior access receipts or original objects.
await fs.writeFile(out + '/article-dom.html', bytes, {flag:'wx'});
await fs.writeFile(out + '/article-text.txt', capture.article_text, {flag:'wx'});
delete capture.article_html;
delete capture.article_text;
const receipt = {...capture, visible,
  state:'OFFICIAL_RENDERED_ARTICLE_CAPTURED_NOT_SCIENTIFIC_ADOPTION',
  pmid:'39602139', pmcid:'PMC11840645', doi:'10.1001/jamadermatol.2024.4796',
  sha256:crypto.createHash('sha256').update(bytes).digest('hex'), byte_size:bytes.length,
  source:'ordinary public rendered article DOM in existing Ego Lite space2/p1',
  representation:'article-only DOM, scripts/styles/iframes and event/nonce attributes removed',
  native_http_response_bytes:false, http_status_or_headers:'NOT_CAPTURED',
  prior_instruments:[
    'Same-origin credentials-omit fetch did not return expected primary tables; status not retained',
    'CDP Page.getResourceContent returned Resource was not cached; not a source absence finding'],
  cookies_or_tokens_captured:false,
  acquisition_proves_historical_cutoff:false,
  scientific_fact_or_current_writes:0};
await fs.writeFile(out + '/receipt.json', JSON.stringify(receipt,null,1), {flag:'wx'});
console.log({state:receipt.state, bytes:bytes.length, sha256:receipt.sha256,
  actual_tables:visible.tables});
