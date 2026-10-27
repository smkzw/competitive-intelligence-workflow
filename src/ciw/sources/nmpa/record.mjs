const FIELDS = {
  '境外生产药品': {certificate: '注册证号', product: '产品名称（中文）'},
  '境内生产药品': {certificate: '批准文号', product: '产品名称'},
};
async function readCertificate(page, category, number) {
  const fields=FIELDS[category];
  if(!fields)throw Error('certificate_category_unsupported');
  const wanted=(category+'——“'+number+'”基本信息').replace(/\s+/g,'');
  // The page loads before its record table is populated: wait for this exact
  // heading, this certificate column, and a non-empty required product value.
  await page.waitForFunction(({wanted, label, product}) => {
    const body = (document.body?.innerText || '').replace(/\s+/g, '');
    if(body.includes('请完成安全验证')&&body.includes('向右滑动'))throw Error('certificate_user_verification_required');
    if (!body.includes(wanted)) return false;
    const rows = [...document.querySelectorAll('table tr')]
      .filter(row => row.cells.length === 2 && row.cells[0].innerText.trim() === label);
    const named = [...document.querySelectorAll('table tr')]
      .filter(row => row.cells.length === 2 && row.cells[0].innerText.trim() === product &&
        row.cells[1].innerText.trim());
    return rows.length >= 1 && named.length === 1;
  }, {wanted, label: fields.certificate, product: fields.product}, {timeout: 45000});
  const captured = await page.evaluate(({category, number, wanted, label, product}) => {
    const visible = el => el.checkVisibility
      ? el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true})
      : !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
    // The observed official page exposes this heading as one visible text line;
    // take it from the category label, ignoring any breadcrumb prefix.
    const heading = (document.body?.innerText || '').split('\n')
      .map(line => line.replace(/\s+/g, ' ').trim())
      .map(line => line.slice(Math.max(0, line.indexOf(category))))
      .filter(line => line.replace(/\s+/g, '') === wanted);
    if (heading.length !== 1) throw Error('certificate_heading_not_unique');
    // Visible record rows, in document order, exactly as the observed official
    // page exposes them: every table row with the record's two-cell shape.
    const rows = [...document.querySelectorAll('table tr')]
      .filter(row => visible(row) && row.cells.length === 2)
      .map(row => [row.cells[0].innerText.trim(), row.cells[1].innerText]);
    if (rows.filter(([key]) => key === label).length !== 1)
      throw Error('certificate_column_not_unique');
    const named = rows.filter(([key, value]) => key === product && value.trim());
    if (named.length !== 1) throw Error('certificate_product_not_unique');
    return {url: location.href, category, registration_number: number, heading: heading[0], rows,
      observed_at: new Date().toISOString()};
  }, {category: category, number: number, wanted,
      label: fields.certificate, product: fields.product});
  return captured;
}
