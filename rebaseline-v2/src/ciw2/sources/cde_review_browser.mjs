const URL='https://www.cde.org.cn/main/xxgk/listpage/9f9c74c73e0f8f56a8bfbc646055026d';
function control(e){return /EGO_.*(?:CONTROL|OWNERSHIP|INACTIVE|UNASSIGNED|NOT_FOUND)|user control/i.test(String(e?.message||''));}
async function watch(p){await p.evaluate(()=>{
  window.__ciwReviewObserver?.disconnect();window.__ciwReviewChanged=false;
  window.__ciwReviewObserver=new MutationObserver(()=>{window.__ciwReviewChanged=true;});
  window.__ciwReviewObserver.observe(document.getElementById('newReportTbody'),{childList:true,subtree:true});
});}
async function settled(p){
  await p.waitForFunction(()=>window.__ciwReviewChanged&&!document.body.innerText.includes('拼命加载中'),undefined,{timeout:30000});
  await p.evaluate(()=>window.__ciwReviewObserver.disconnect());
}
async function pagerId(p){return await p.evaluate(()=>[...document.querySelectorAll('.layui-laypage')].find(e=>e.getBoundingClientRect().height>0)?.id);}
async function collect(p){return await p.evaluate(()=>{
  const tbody=document.getElementById('newReportTbody'),table=tbody.closest('table');
  const pager=[...document.querySelectorAll('.layui-laypage')].find(e=>e.getBoundingClientRect().height>0);
  const legend=[...document.querySelectorAll('p')].find(e=>e.getBoundingClientRect().height>0&&e.innerText.includes('本专业'));
  if(!pager||!legend||!tbody.getBoundingClientRect().height)throw Error('Review source not ready');
  return {url:location.href,section:'new_review_task',filters:{sequence:document.getElementById('splxtype').value,
    task_type:document.getElementById('applytypecdeNewReport').value,ui_acceptance_number:document.getElementById('acceptid2').value},
    headers:[...table.rows[0].cells].map(c=>c.innerText),
    rows:[...tbody.rows].map(r=>[...r.cells].map(c=>({text:c.innerText,images:[...c.querySelectorAll('img')].map(i=>i.getAttribute('src'))}))),
    legend:[...legend.querySelectorAll('span')].map(s=>({text:s.innerText,images:[...s.querySelectorAll('img')].map(i=>i.getAttribute('src'))})),
    pagination:{current:Number(pager.querySelector('.layui-laypage-curr em:last-child').innerText),page_size:Number(pager.querySelector('select').value),text:pager.innerText},
    observed_at:new Date().toISOString()};
});}
try{
  const p=(await taskSpace(config.space)).page('p1');
  try{await p.goto(URL,{waitUntil:'domcontentloaded'});}
  catch(e){if(control(e)||e?.name!=='PageNavigationTimeoutError')throw e;}
  await p.click('text=审评任务公示',{label:'进入公开审评任务序列'});
  await p.waitForFunction(()=>!!document.getElementById('newReportTbody')&&!document.body.innerText.includes('拼命加载中'),undefined,{timeout:30000});
  // Newly loaded official page defaults are checked, never assumed or silently
  // treated as other sequences. Unsupported scope is not an empty result.
  const scope=await p.evaluate(()=>[document.getElementById('splxtype').value,document.getElementById('applytypecdeNewReport').value]);
  if(scope[0]!=='化药'||scope[1]!=='IND')throw Error('Unsupported review sequence');
  await p.fill('#acceptid2','');await watch(p);
  await p.click('loc=role:button[name=查询]',{label:'读取完整化药IND审评序列'});await settled(p);
  let id=await pagerId(p);if(!id)throw Error('Review paginator missing');
  await watch(p);await p.selectOption('#'+id+' select','50');await settled(p);
  let total;
  for(let page=1;;page++){
    const c=await collect(p),n=Number(c.pagination.text.match(/共\s*(\d+)\s*条/)[1]);
    if(c.pagination.current!==page||c.pagination.page_size!==50||c.filters.sequence!=='化药'||c.filters.task_type!=='IND'||c.filters.ui_acceptance_number!=='')throw Error('Review scope drift');
    if(total!==undefined&&n!==total)throw Error('Review total drift');total=n;
    if(c.rows.length!==Math.min(50,n-(page-1)*50))throw Error('Review page gap');
    console.log('CIW_CHINA_PAGE:'+JSON.stringify(c));
    if(page*50>=n)break;
    id=await pagerId(p);await watch(p);
    await p.click('#'+id+' .layui-laypage-next',{label:'获取公开审评序列下一页'});await settled(p);
  }
  console.log('CIW_CHINA_END:'+JSON.stringify({status:'ok',observed_at:new Date().toISOString()}));
}catch(e){console.log('CIW_CHINA_END:'+JSON.stringify({status:control(e)?'user_control':'failed',error_type:e?.name||'Error'}));}
