const URL='https://www.cde.org.cn/main/xxgk/listpage/9f9c74c73e0f8f56a8bfbc646055026d';
const {createHash}=await import('node:crypto');
function control(e){return /EGO_.*(?:CONTROL|OWNERSHIP|INACTIVE|UNASSIGNED|NOT_FOUND)|user control/i.test(String(e?.message||''));}
function anchor(c){return createHash('sha256').update(JSON.stringify([c.section,Object.keys(c.filters).sort().map(k=>[k,c.filters[k]]),c.headers,c.rows,[],c.pagination.page_size,Number(c.pagination.text.match(/共\s*(\d+)\s*条/)[1])])).digest('hex');}
async function watch(p){await p.evaluate(()=>{window.__ciwPriorityObserver?.disconnect();window.__ciwPriorityChanged=false;
 window.__ciwPriorityObserver=new MutationObserver(()=>{window.__ciwPriorityChanged=true;});
 window.__ciwPriorityObserver.observe(document.getElementById('includePriorityTbody'),{childList:true,subtree:true});});}
async function settled(p){await p.waitForFunction(()=>window.__ciwPriorityChanged&&!document.body.innerText.includes('拼命加载中'),undefined,{timeout:30000});await p.evaluate(()=>window.__ciwPriorityObserver.disconnect());}
async function pagerId(p){return await p.evaluate(()=>[...document.querySelectorAll('.layui-laypage')].find(n=>n.getBoundingClientRect().height>0)?.id);}
async function collect(p){return await p.evaluate(()=>{
 const body=document.getElementById('includePriorityTbody'),table=body.closest('table');
 const active=[...document.querySelectorAll('li.layui-this')].some(n=>n.getBoundingClientRect().height>0&&n.innerText.trim()==='纳入优先审评品种名单');
 const pager=[...document.querySelectorAll('.layui-laypage')].find(n=>n.getBoundingClientRect().height>0);
 if(!active||!pager||!body.getBoundingClientRect().height)throw Error('Priority included source not ready');
 return {url:location.href,section:'priority_included',filters:{acceptance_number:document.getElementById('acceptidInclude').value,
  drug_name:document.getElementById('drugnameInclude').value,applicant:document.getElementById('companyInclude').value},
  headers:[...table.rows[0].cells].map(n=>n.innerText),rows:[...body.rows].map(r=>[...r.cells].map(n=>n.innerText)),
  pagination:{current:Number(pager.querySelector('.layui-laypage-curr em:last-child').innerText),page_size:Number(pager.querySelector('select').value),text:pager.innerText},observed_at:new Date().toISOString()};});}
let reusedPages=[],newPages=[],resumeUsed=false,resumeRejected=null;
try{
 const p=(await taskSpace(config.space)).page('p1');
 try{await p.goto(URL,{waitUntil:'domcontentloaded'});}catch(e){if(control(e)||e.name!=='PageNavigationTimeoutError')throw e;}
 await p.click('text=优先审评公示',{label:'进入公开优先审评目录'});
 await p.waitForFunction(()=>document.getElementById('includePriorityTbody')?.getBoundingClientRect().height>0&&!document.body.innerText.includes('拼命加载中'),undefined,{timeout:30000});
 const active=await p.evaluate(()=>[...document.querySelectorAll('li.layui-this')].some(n=>n.getBoundingClientRect().height>0&&n.innerText.trim()==='纳入优先审评品种名单'));
 if(!active){await p.click('text=纳入优先审评品种名单',{label:'选择实际纳入优先审评名单'});await p.waitForFunction(()=>document.getElementById('includePriorityTbody')?.getBoundingClientRect().height>0&&!document.body.innerText.includes('拼命加载中'),undefined,{timeout:30000});}
 for(const id of ['acceptidInclude','drugnameInclude','companyInclude'])await p.fill('#'+id,'');
 await watch(p);await p.click('loc=role:button[name=查询]',{label:'读取完整优先审评目录'});await settled(p);
 let id=await pagerId(p);if(!id)throw Error('Priority pager missing');
 const size=await p.evaluate(id=>document.querySelector('#'+id+' select').value,id);
 if(size!=='50'){await watch(p);await p.selectOption('#'+id+' select','50');await settled(p);}
 let total;
 for(let page=1;;){
  const c=await collect(p),n=Number(c.pagination.text.match(/共\s*(\d+)\s*条/)[1]);
  if(c.pagination.current!==page||c.pagination.page_size!==50||Object.values(c.filters).some(Boolean))throw Error('Priority scope drift');
  if(total!==undefined&&n!==total)throw Error('Priority total drift');total=n;
  if(c.rows.length!==Math.min(50,n-(page-1)*50))throw Error('Priority page gap');
  if(page===1&&config.resume){resumeUsed=n===config.resume.total_records&&c.pagination.page_size===config.resume.page_size&&anchor(c)===config.resume.first_page_sha256;
   if(resumeUsed)reusedPages=config.resume.pages_read.filter(n=>n!==1);else resumeRejected='fresh_scope_or_anchor_changed';}
  console.log('CIW_CHINA_PAGE:'+JSON.stringify(c));newPages.push(page);
  let next=page+1;while(resumeUsed&&reusedPages.includes(next))next++;
  if(next>Math.ceil(n/50))break;
  id=await pagerId(p);await watch(p);
  if(next===page+1)await p.click('#'+id+' .layui-laypage-next',{label:'读取优先审评目录下一页'});
  else{await p.fill('#'+id+' .layui-laypage-skip input',String(next));await p.click('#'+id+' .layui-laypage-btn',{label:'补取缺失优先审评页'});}
  await settled(p);page=next;
 }
 console.log('CIW_CHINA_END:'+JSON.stringify({status:'ok',resume_used:resumeUsed,reused_pages:reusedPages,new_pages_checked:newPages,resume_rejected_reason:resumeRejected}));
}catch(e){console.log('CIW_CHINA_END:'+JSON.stringify({status:control(e)?'user_control':'failed',error_type:e?.name||'Error',resume_used:resumeUsed,reused_pages:reusedPages,new_pages_checked:newPages,resume_rejected_reason:resumeRejected}));}
