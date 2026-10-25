const URL = "https://www.cde.org.cn/main/xxgk/listpage/9f9c74c73e0f8f56a8bfbc646055026d";
const {createHash} = await import('node:crypto');
function anchor(c) {
  const rows=c.rows.map(row=>row.map(cell=>typeof cell==='string'?cell:[cell.text,cell.images]));
  const legend=(c.legend||[]).map(e=>[e.text,e.images]);
  const total=c.pagination.total_records ?? Number(c.pagination.text.match(/共\s*(\d+)\s*条/)[1]);
  return createHash('sha256').update(JSON.stringify([c.section,Object.keys(c.filters).sort().map(k=>[k,c.filters[k]]),
    c.headers,rows,legend,c.pagination.page_size,total])).digest('hex');
}
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
let resumeUsed=false,reusedPages=[],newPages=[],resumeRejected=null;
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
  await page.click('button[onclick="defaultObj.methods.getAcceptList()"]',
    {label:"search public CDE records",timeout:30000});
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
    if(expected===1 && config.resume) {
      resumeUsed=meta.total_records===config.resume.total_records && meta.page_size===config.resume.page_size &&
        anchor(capture)===config.resume.first_page_sha256;
      if(resumeUsed) reusedPages=config.resume.pages_read.filter(n=>n!==1);
      else resumeRejected='fresh_scope_or_anchor_changed';
    }
    console.log("CIW_CHINA_PAGE:"+JSON.stringify(capture));
    newPages.push(meta.current);
    const last=meta.total_records?Math.ceil(meta.total_records/meta.page_size):0;
    let next=expected+1;
    while(resumeUsed && reusedPages.includes(next)) next++;
    if (!meta.total_records || next>last) break;
    id = await pagerId(page);
    await watch(page);
    if(next===expected+1) await page.click("#"+id+" .layui-laypage-next",{label:"next public acceptance page"});
    else {
      await page.fill('#'+id+' .layui-laypage-skip input',String(next));
      await page.click('#'+id+' .layui-laypage-btn',{label:'jump to missing acceptance page'});
    }
    await settled(page);
    expected=next;
  }
  console.log("CIW_CHINA_END:"+JSON.stringify({status:"ok",observed_at:new Date().toISOString(),
    resume_used:resumeUsed,reused_pages:reusedPages,new_pages_checked:newPages,resume_rejected_reason:resumeRejected}));
} catch(error) {
  console.log("CIW_CHINA_END:"+JSON.stringify({status:control(error)?"user_control":"failed",phase,error_type:error?.name || "Error",
    resume_used:resumeUsed,reused_pages:reusedPages,new_pages_checked:newPages,resume_rejected_reason:resumeRejected}));
}
