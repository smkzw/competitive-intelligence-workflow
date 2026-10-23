const URL = "https://www.cde.org.cn/main/xxgk/listpage/9f9c74c73e0f8f56a8bfbc646055026d";
function control(error) {
  return /EGO_.*(?:CONTROL|OWNERSHIP|INACTIVE|UNASSIGNED|NOT_FOUND)|user control/i.test(String(error?.message || ""));
}
async function watch(page) {
  await page.evaluate(() => {
    window.__ciwCdeObserver?.disconnect();
    window.__ciwCdeChanged = false;
    window.__ciwCdeObserver = new MutationObserver(() => { window.__ciwCdeChanged = true; });
    window.__ciwCdeObserver.observe(document.querySelector("#acceptVarietyInfoTbody"),
      {childList:true,subtree:true,characterData:true});
  });
}
async function settled(page) {
  await page.waitForFunction(() => window.__ciwCdeChanged && !document.body.innerText.includes("拼命加载中"),
    undefined,{timeout:30000});
  await page.evaluate(() => { window.__ciwCdeObserver?.disconnect(); });
}
async function collect(page) {
  return await page.evaluate(() => {
    const visible = element => element.getBoundingClientRect().height > 0;
    const tbody = document.querySelector("#acceptVarietyInfoTbody");
    if (!tbody || !visible(tbody)) throw Error("acceptance_table_missing");
    const table = tbody.closest("table");
    const pager = [...document.querySelectorAll(".layui-laypage")].filter(visible)[0];
    const rawRows = [...tbody.rows];
    const empty = !pager && rawRows.length === 1 && rawRows[0].cells.length === 1 &&
      rawRows[0].cells[0].colSpan === 8 && rawRows[0].innerText.trim() === "暂无内容";
    if (!pager && !empty) throw Error("pagination_missing");
    const text = empty ? rawRows[0].innerText.trim() : pager.innerText;
    const total = empty ? 0 : Number(text.match(/共\s*(\d+)\s*条/)[1]);
    return {url:location.href,section:"acceptance",filters:{year:document.querySelector("#year").value,
      drug_name:document.querySelector("#drugname").value,applicant:document.querySelector("#company").value,
      acceptance_number:document.querySelector("#acceptid").value,drug_type:document.querySelector("#drugtype").value,
      application_type:document.querySelector("#applytype").value},
      headers:[...table.tHead.rows[0].cells].map(cell=>cell.innerText),
      rows:empty ? [] : rawRows.map(row=>[...row.cells].map(cell=>cell.innerText)),
      pagination:{current:empty?0:Number(pager.querySelector(".layui-laypage-curr em:last-child").innerText),
        page_size:empty?null:Number(pager.querySelector("select").value),total_records:total,text}};
  });
}
async function pagerId(page) {
  return await page.evaluate(() => [...document.querySelectorAll(".layui-laypage")]
    .find(element=>element.getBoundingClientRect().height>0)?.id);
}
let phase = "start";
try {
  const page = (await taskSpace(config.space)).page("p1");
  phase = "navigate";
  try { await page.goto(URL,{waitUntil:"domcontentloaded"}); }
  catch(error) { if (control(error) || error?.name !== "PageNavigationTimeoutError") throw error; }
  await page.waitForSelector("#drugname",{state:"visible",timeout:30000});
  await page.waitForFunction(()=>!!document.querySelector("#acceptVarietyInfoTbody") &&
    !document.body.innerText.includes("拼命加载中"),undefined,{timeout:30000});
  phase = "filters";
  for (const field of ["year","drugtype","applytype"]) {
    const selected = await page.evaluate(id=>document.getElementById(id).value,field);
    if (selected !== "") {
      await page.click(`#${field} + .layui-form-select input`,{label:"include all source categories"});
      await page.click('.layui-form-selected dd[lay-value=""]',{label:"select all source categories"});
    }
  }
  for (const [id,field] of [["drugname","drug_name"],["company","applicant"],["acceptid","acceptance_number"]]) {
    await page.fill("#"+id,config.filters[field]);
  }
  phase = "query";
  await watch(page);
  await page.click("loc=role:button[name='查询']",{label:"search public CDE records"});
  await settled(page);
  let id = await pagerId(page);
  if (id) {
    phase = "page_size";
    await watch(page);
    await page.selectOption("#"+id+" select","50");
    await settled(page);
  }
  let expected = 1, totals;
  phase = "pages";
  for (;;) {
    const capture = await collect(page), meta = capture.pagination;
    if (meta.total_records && meta.current !== expected) throw Error("page_number_mismatch");
    const identity = JSON.stringify([meta.total_records,meta.page_size,capture.filters]);
    if (totals && totals !== identity) throw Error("page_scope_changed");
    totals = identity;
    console.log("CIW_CHINA_PAGE:"+JSON.stringify(capture));
    if (!meta.total_records || expected >= Math.ceil(meta.total_records/meta.page_size)) break;
    id = await pagerId(page);
    await watch(page);
    await page.click("#"+id+" .layui-laypage-next",{label:"next public acceptance page"});
    await settled(page);
    expected++;
  }
  console.log("CIW_CHINA_END:"+JSON.stringify({status:"ok",observed_at:new Date().toISOString()}));
} catch(error) {
  console.log("CIW_CHINA_END:"+JSON.stringify({status:control(error)?"user_control":"failed",phase,error_type:error?.name || "Error"}));
}
