// Discover public detail links by ordinary catalogue controls; never private APIs.
let result, detail, stage='home', number;
try {
  const t=await taskSpace(config.space), p=t.page('p1');
  await p.goto('https://datasearch.nmpa.gov.cn/datasearch/home-index.html', {waitUntil:'domcontentloaded'});
  await p.waitForSelector('input[data-step="4"]',{state:'visible',timeout:45000});
  await p.click(`a[title="${config.category}"] >> nth=0`,{label:'选择公开药品生产目录'});
  await p.fill('input[data-step="4"]',config.query);
  stage='query_popup';
  const opened=p.waitForEvent('popup',{timeout:30000});
  await p.click('button[data-step="5"]',{label:'查询明确药品许可名称'});
  result=await opened;
  stage='catalogue';
  await result.waitForFunction(()=>/共\s*\d+\s*条/.test(document.querySelector('.el-pagination__total')?.innerText||''),undefined,{timeout:45000});
  await result.waitForFunction(()=>![...document.querySelectorAll('.el-loading-mask')].some(e=>e.checkVisibility()),undefined,{timeout:45000});
  let count=0;
  while(true){
    const state=await result.evaluate(()=>({
      rows:[...document.querySelectorAll('table.el-table__body tr')].filter(e=>e.checkVisibility())
        .map(r=>({number:r.cells[1]?.innerText.trim(),name:r.cells[2]?.innerText.trim()})),
      total:document.querySelector('.el-pagination__total')?.innerText,
      next:[...document.querySelectorAll('.btn-next')].findIndex(e=>e.checkVisibility()&&!e.disabled)
    }));
    for(let i=0;i<state.rows.length;i++){
      const row=state.rows[i];
      number=row.number;stage='detail_popup';
      if(!/^国药准字[A-Z]{1,3}[0-9]{8}$/.test(row.number))throw Error('certificate_number_invalid');
      const popup=result.waitForEvent('popup',{timeout:30000});
      await result.click(`table.el-table__body tr:nth-child(${i+1}) button`,{label:'打开所选药品许可详情'});
      detail=await popup;
      stage='detail_content';
      const captured=await readCertificate(detail,config.category,row.number);
      console.log('CIW_CHINA_PAGE:'+JSON.stringify({...captured,query:config.query,total:state.total}));
      count++; await detail.close();detail=undefined;
    }
    if(state.next<0)break;
    stage='next_catalogue_page';number=undefined;
    const previous=state.rows.map(r=>r.number).join('|');
    await result.click(`.btn-next >> nth=${state.next}`,{label:'读取下一页公开许可'});
    await result.waitForFunction(old=>[...document.querySelectorAll('table.el-table__body tr')]
      .filter(e=>e.checkVisibility()).map(r=>r.cells[1]?.innerText.trim()).join('|')!==old,previous,{timeout:30000});
    await result.waitForFunction(()=>![...document.querySelectorAll('.el-loading-mask')].some(e=>e.checkVisibility()),undefined,{timeout:30000});
  }
  await result.close();result=undefined;
  console.log('CIW_CHINA_END:'+JSON.stringify({status:'ok',records:count}));
}catch(e){
  const control=/EGO_.*(?:CONTROL|OWNERSHIP|INACTIVE|UNASSIGNED|NOT_FOUND)|user control/i.test(String(e?.message||''));
  const verification=String(e?.message||'').includes('certificate_user_verification_required');
  const network=String(e?.message||'').match(/ERR_CONNECTION_CLOSED|ERR_CONNECTION_RESET|ERR_INTERNET_DISCONNECTED|ERR_NAME_NOT_RESOLVED|ERR_TIMED_OUT/)?.[0];
  if(!control&&!verification)for(const p of [detail,result])if(p?.openedBy==='agent')try{await p.close();}catch{}
  console.log('CIW_CHINA_END:'+JSON.stringify({status:control?'user_control':verification?'verification_required':network?'network_error':'failed',error_type:e?.name||'Error',error_code:network,
    stage,registration_number:number,certificate_state:e?.certificate_state,
    reason:String(e?.message||'').slice(0,360)}));
}
