// One public detail URL; preserve a page the user has already verified.
const control=e=>/EGO_.*(?:CONTROL|OWNERSHIP|INACTIVE|UNASSIGNED|NOT_FOUND)|user control/i.test(String(e?.message||''));
try {
  const page=(await taskSpace(config.space)).page('p1');
  if(await page.url()!==config.url)await page.goto(config.url,{waitUntil:'domcontentloaded'});
  const captured=await readCertificate(page,config.category,config.query);
  console.log('CIW_CHINA_PAGE:'+JSON.stringify(captured));
  console.log('CIW_CHINA_END:'+JSON.stringify({status:'ok'}));
}catch(e){
  const network=String(e?.message||'').match(/(?:ERR_CONNECTION_CLOSED|ERR_CONNECTION_RESET|ERR_INTERNET_DISCONNECTED|ERR_NAME_NOT_RESOLVED|ERR_TIMED_OUT)/)?.[0];
  const code=String(e?.message||'').includes('certificate_user_verification_required')?
    'certificate_user_verification_required':network||'unexpected';
  console.log('CIW_CHINA_END:'+JSON.stringify({status:control(e)?'user_control':
    code==='certificate_user_verification_required'?'verification_required':network?'network_error':'failed',error_type:e?.name||'Error',error_code:code,
    certificate_state:e?.certificate_state}));
}
