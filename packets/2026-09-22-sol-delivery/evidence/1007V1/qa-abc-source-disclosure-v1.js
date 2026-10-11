// Native disclosure only. No model/source/edit/config/share acceptance inference.
const fs=await import("node:fs/promises"),path=await import("node:path");
const relative=".artifacts/1007-abc-source-disclosure-v1";
const candidate=path.join(workflowRoot,relative);
const actual=JSON.parse(await fs.readFile(path.join(candidate,"actual.json"),"utf8"));
if(Object.keys(actual.reports).sort().join("")!=="ABC"||actual.current_writes!==0)
 throw Error("Normal readonly ABC render must complete before QA");
const page=(await taskSpace(2)).page("p1");
const out=path.join(candidate,"source-qa");await fs.mkdir(out);
const result={state:"RUNNING_NOT_ACCEPTED",states:[],failures:[],currentWrites:0};
async function observe(report,phase){
 const value=await page.evaluate(()=>{
  const section=document.querySelector('#external-sources');
  const details=section.querySelector('[data-source-disclosure]');
  const summary=details.querySelector('summary');
  const list=details.querySelector('ul');
  const children=list?[...list.children]:[];
  return {width:innerWidth,open:details.open,label:summary.textContent.trim(),
   sourceItems:children.length,
   sourcesVisible:children.some(n=>n.checkVisibility()),
   links:[...details.querySelectorAll('a')].map(a=>({href:a.getAttribute('href'),text:a.textContent})),
   nativeFocus:document.activeElement===summary,
   sectionHeight:section.getBoundingClientRect().height,
   overflow:document.documentElement.scrollWidth>innerWidth+1,
   dateLabel:details.textContent.includes('登记版本公开日：')};
 });
 result.states.push({report,phase,...value});
 if(value.overflow||!value.label.includes('来源资料（'+value.sourceItems+'）'))
  result.failures.push(report+value.width+phase+':geometry or count');
 await page.screenshot({path:path.join(out,report+'-'+phase+'-'+value.width+'.png')});
 return value;
}
try{
 for(const report of ['A','B','C'])for(const width of [1440,1600,1920,2560]){
  await page.cdp('Emulation.setDeviceMetricsOverride',{width,
   height:width===2560?1440:width===1920?1080:900,deviceScaleFactor:1,mobile:false});
  const entry=report==='A'?'clinical-portfolio.html':'overview.html';
  await page.goto('file://'+path.join(candidate,report,entry)+
   (report==='C'?'':'?view=comparison&cmp=efficacy%3A%3Aq-pruritus-nrs-ge4-improvement'));
  await page.waitForFunction(()=>document.querySelector('[data-source-disclosure]'));
  await page.evaluate(()=>document.querySelector('#external-sources').scrollIntoView({block:'end'}));
  const before=await observe(report,'collapsed');
  if(before.open||before.sourcesVisible||before.sectionHeight>90||!before.sourceItems)
   result.failures.push(report+width+':source wall or missing original references');
  await page.focus('[data-source-disclosure] > summary');
  await page.keyboard.press('Space');
  const expanded=await observe(report,'expanded');
  if(!expanded.open||!expanded.sourcesVisible||!expanded.nativeFocus||
    JSON.stringify(expanded.links)!==JSON.stringify(before.links))
   result.failures.push(report+width+':native opening lost references');
  if(report==='A'&&(!expanded.dateLabel||expanded.sourceItems!==20))
   result.failures.push(report+width+':registry version date identity lost');
  await page.keyboard.press('Space');
  const after=await page.evaluate(()=>({open:document.querySelector('[data-source-disclosure]').open,
   focus:document.activeElement===document.querySelector('[data-source-disclosure] > summary')}));
  expanded.collapse=after;
  if(after.open||!after.focus)result.failures.push(report+width+':native collapse/focus failed');
 }
 result.state=result.failures.length?'FAILED_NOT_ACCEPTED':'BOUNDED_ABC_SOURCE_READING_PASS';
}catch(error){result.state='FAILED_NOT_ACCEPTED';result.error=String(error);throw error;}
finally{await fs.writeFile(path.join(out,'actual.json'),JSON.stringify(result,null,2));}
console.log({state:result.state,states:result.states.length,failures:result.failures});
if(result.failures.length)throw Error(result.failures.join('; '));
