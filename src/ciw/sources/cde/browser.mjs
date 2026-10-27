/* config is JSON supplied by the trusted adapter, never evaluated source-page text. */
const URL = "https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml";
function isControlError(error) {
  return /EGO_.*(?:CONTROL|OWNERSHIP|INACTIVE|UNASSIGNED|NOT_FOUND)|user control/i.test(String(error?.message || ""));
}
async function navigate(page) {
  try { await page.goto(URL,{waitUntil:"domcontentloaded"}); }
  catch (error) {
    if (isControlError(error) || error?.name !== "PageNavigationTimeoutError") throw error;
    const ready = await page.evaluate(() => location.href.startsWith("https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml") &&
      !!document.querySelector("table.searchTable") && !!document.querySelector("#searchfrm input[name=keywords]"));
    if (!ready) throw error;
  }
}
async function submit(page, action, number) {
  const before = await page.evaluate(() => performance.timeOrigin);
  try { await action(); }
  catch (error) { if (isControlError(error) || error?.name !== "PageNavigationTimeoutError") throw error; }
  await page.waitForFunction(({before, number, query}) => {
    const actual = document.querySelector("#searchfrm input[name=keywords]")?.value;
    const text = document.querySelector(".pagination")?.parentElement.innerText || "";
    const match = text.match(/当前第\s*(\d+)\s*页\s*[，,]\s*共\s*(\d+)\s*页\s*[，,]\s*共\s*(\d+)\s*条记录/);
    const empty = match && number === 1 && match.slice(1).every(value => Number(value) === 0);
    return performance.timeOrigin !== before && actual === query && match && (Number(match[1]) === number || empty);
  }, {before, number, query:config.query}, {timeout:30000});
}
async function collect(page) {
  return await page.evaluate(() => {
    const table = document.querySelector("table.searchTable");
    if (!table) throw Error("registry_table_missing");
    let rows = [...table.rows].slice(1);
    const footer = document.querySelector(".pagination")?.parentElement.innerText || "";
    if (/共\s*0\s*条记录/.test(footer) && rows.length === 1 && rows[0].cells.length === 1 &&
        rows[0].cells[0].colSpan === 6 && rows[0].cells[0].innerText.trim() === "暂无数据...") rows = [];
    return {url:location.href,query:document.querySelector("#searchfrm input[name=keywords]")?.value,
      headers:[...table.rows[0].cells].map(cell => cell.innerText),
      rows:rows.map(row => ({cells:[...row.cells].map(cell => cell.innerText),
        detail_id:row.querySelector("a[id]")?.id})),
      pagination_text:footer};
  });
}
try {
  const task = await taskSpace(config.space);
  const page = task.page("p1");
  await navigate(page);
  await page.fill("#searchfrm input[name=keywords]",config.query);
  await submit(page, () => page.click("loc=role:button[name='查询']",{label:"search public trial registry"}),1);
  let expected = 1, totals;
  for (;;) {
    const capture = await collect(page);
    const match = capture.pagination_text.match(/当前第\s*(\d+)\s*页\s*[，,]\s*共\s*(\d+)\s*页\s*[，,]\s*共\s*(\d+)\s*条记录/);
    const empty = match && expected === 1 && match.slice(1).every(value => Number(value) === 0);
    if (!match || (Number(match[1]) !== expected && !empty)) throw Error("registry_pagination_invalid");
    const totalPages = Number(match[2]), totalRecords = Number(match[3]);
    const currentTotals = JSON.stringify([totalPages,totalRecords]);
    if (config.expected_totals && JSON.stringify(config.expected_totals) !== currentTotals) throw Error("registry_pagination_changed");
    if (totals && totals !== currentTotals) throw Error("registry_pagination_changed");
    totals = currentTotals;
    const skip = new Set(config.skip_pages || []);
    if (!skip.has(expected)) console.log("CIW_CHINA_PAGE:"+JSON.stringify(capture));
    let next = expected + 1;
    while (next <= totalPages && skip.has(next)) next++;
    if (next > totalPages) break;
    if (next === expected + 1) {
      await submit(page, () => page.click('.pagination a[aria-label="Next"]',{label:"next registry results page"}),next);
    } else {
      await page.fill('.pageInfo input[type="text"]',String(next));
      await submit(page, () => page.press('.pageInfo input[type="text"]',"Enter"),next);
    }
    expected = next;
  }
  console.log("CIW_CHINA_END:"+JSON.stringify({status:"ok",observed_at:new Date().toISOString()}));
} catch (error) {
  console.log("CIW_CHINA_END:"+JSON.stringify({status:isControlError(error)?"user_control":"failed",error_type:error?.name || "Error"}));
}
