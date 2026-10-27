// Trusted config supplies a project-bound registry ID, never source-page instructions.
const LIST='https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml';
const control=e=>/EGO_.*(?:CONTROL|OWNERSHIP|INACTIVE|UNASSIGNED|NOT_FOUND)|user control/i.test(String(e?.message||''));
let detail;
try{
  const t=await taskSpace(config.space),p=t.page('p1');
  try{await p.goto(LIST,{waitUntil:'domcontentloaded'});}
  catch(e){if(control(e)||e?.name!=='PageNavigationTimeoutError')throw e;}
  await p.waitForSelector('#searchfrm input[name=keywords]',{state:'visible',timeout:30000});
  await p.fill('#searchfrm input[name=keywords]',config.query);
  const before=await p.evaluate(()=>performance.timeOrigin);
  try{await p.click('loc=role:button[name=查询]',{label:'检索明确登记试验编号'});}
  catch(e){if(control(e)||e?.name!=='PageNavigationTimeoutError')throw e;}
  await p.waitForFunction(({before,ctr})=>performance.timeOrigin!==before&&
    document.querySelector('#searchfrm input[name=keywords]')?.value===ctr&&!!document.querySelector('table.searchTable'),
    {before,ctr:config.query},{timeout:30000});
  const ids=await p.evaluate(ctr=>[...document.querySelectorAll('table.searchTable tr')]
    .filter(r=>r.cells[1]?.innerText.trim()===ctr).map(r=>r.cells[1].querySelector('a')?.id),config.query);
  if(ids.length!==1||ids[0]!==config.detail_id)throw Error('Trial detail list binding changed');
  const popup=p.waitForEvent('popup',{timeout:30000});
  await p.click('table.searchTable tr td:nth-child(2) a:text-is("'+config.query+'")',{label:'打开对应试验中文原文'});
  detail=await popup;
  await detail.waitForFunction(ctr=>document.title===ctr+'详细信息'&&!!document.querySelector('#collapseOne'),config.query,{timeout:30000});
  await detail.waitForFunction(()=>{const e=document.querySelector('#collapseTwo');
    return e&&!e.classList.contains('collapsing');},undefined,{timeout:30000});
  const expanded=await detail.evaluate(()=>document.querySelector('#collapseTwo')?.classList.contains('in'));
  if(!expanded)await detail.click('loc=href:/clinicaltrials.searchlistdetail.dhtml#collapseTwo',{label:'展开完整试验方案资料'});
  await detail.waitForFunction(()=>{const e=document.querySelector('#collapseTwo');
    return e?.classList.contains('in')&&!!e.querySelector('table.searchDetailTable tr');},undefined,{timeout:30000});
  const captured=await detail.evaluate(detailId=>{
    const basic=[],wanted=new Set(['登记号','试验状态','首次公示信息日期','申请人名称']);
    for(const row of document.querySelectorAll('#collapseOne tr')){
      const cells=[...row.cells].map(c=>c.innerText);
      for(let i=0;i+1<cells.length;i+=2)if(wanted.has(cells[i].trim()))basic.push(cells.slice(i,i+2));
    }
    const keys=new Set(['登记号','试验分类','年龄','试验药','主要终点指标及评价时间','目标入组人数','第一例受试者签署知情同意书日期']);
    const tables=[...document.querySelectorAll('#collapseTwo table.searchDetailTable')]
      .filter(t=>t.parentElement.closest('table')===null).map(t=>{
        const rows=[...t.rows].filter(r=>r.closest('table')===t),nested=[];
        rows.forEach((r,i)=>[...r.cells].forEach((c,j)=>{
          const child=[...c.children].find(e=>e.tagName==='TABLE');
          if(child)nested.push({row:i,column:j,rows:[...child.rows].map(r=>[...r.cells].map(c=>c.innerText))});
        }));
        return {rows:rows.map(r=>[...r.cells].map(c=>c.innerText)),nested};
      }).filter(t=>t.rows.some(r=>keys.has(r[0]?.trim())));
    return {url:location.href,title:document.title,section:'trial_detail',
      registry_id:basic.find(r=>r[0].trim()==='登记号')?.[1],detail_id:detailId,
      basic,tables,observed_at:new Date().toISOString()};
  },ids[0]);
  console.log('CIW_CHINA_PAGE:'+JSON.stringify(captured));
  await detail.close();detail=undefined;
  console.log('CIW_CHINA_END:'+JSON.stringify({status:'ok'}));
}catch(e){
  if(!control(e)&&detail?.openedBy==='agent')try{await detail.close();}catch{}
  console.log('CIW_CHINA_END:'+JSON.stringify({status:control(e)?'user_control':'failed',error_type:e?.name||'Error'}));
}
