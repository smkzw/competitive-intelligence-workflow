/* Algorithm excerpts from src/ci_workflow/renderers/portal/assets/report-a.js.
   No DOM, browser, or generated site is exercised by this script. */
'use strict';
const out=[];
function record(id,input,actual,expected){out.push({id,input,actual,expected,pass:JSON.stringify(actual)===JSON.stringify(expected)});}
function projectRate(eventRecord){
  // numericValue in the caller is a boolean test; all fixtures here are finite numbers.
  var eventRate = eventRecord && typeof eventRecord.value==='number' && isFinite(eventRecord.value) ? eventRecord.value : null;
  if(eventRate!=null && String(eventRecord.unit||'').indexOf('例')!==-1){
    var den=parseFloat(eventRecord.denominator);
    if(isFinite(den)&&den>0){eventRate=Math.round(eventRate/den*1000)/10;}
  }
  if(eventRate!=null && String(eventRecord.unit||'')==='人' && eventRecord.numerator!=null && eventRecord.denominator!=null && Number(eventRecord.denominator)>0){
    eventRate=Math.round(Number(eventRecord.numerator)/Number(eventRecord.denominator)*1000)/10;
  }
  return eventRate;
}
record('M01',{value:7,unit:'人'},projectRate({value:7,unit:'人'}),null);
record('M02',{value:7,unit:'人',numerator:7,denominator:7},projectRate({value:7,unit:'人',numerator:7,denominator:7}),100);
record('M03',{value:20,unit:'例',denominator:10,measureObject:'events'},projectRate({value:20,unit:'例',denominator:10}),null);
record('M04',{value:7,unit:'%'},projectRate({value:7,unit:'%'}),7);
const treatment=12,control=null,useDifference=true;
record('M05',{treatment,control,useDifference},(useDifference&&control!=null)?treatment-control:treatment,null);
const derivedRate=100,allEventRates=[];
const yMax=Math.max(10,Math.ceil(Math.max.apply(null,[0].concat(allEventRates))/10)*10);
const yPosition=14+72*(yMax-derivedRate)/(yMax-0);
record('M06',{derivedRate,allEventRates},yPosition>=0&&yPosition<=100,true);
const stages=['II期及更早','III期','申报或上市','历史观察'];
function stageForProduct(product){
  if(/终止|暂停|撤回|停止|清算/.test(product.status)) return '历史观察';
  if(/申报|上市|获批|NDA/.test(product.phase+product.status)) return '申报或上市';
  if(/IV期/.test(product.phase)) return 'IV期';
  if(/III期/.test(product.phase)) return 'III期';
  if(/II期/.test(product.phase)) return 'II期及更早';
  if(/I期/.test(product.phase)) return 'I期及更早';
  return '阶段未标注';
}
['I期','II期','III期','IV期','未标注'].forEach((phase,i)=>record('L0'+(i+1),{phase,status:'招募中',stage:stageForProduct({phase,status:'招募中'})},stages.includes(stageForProduct({phase,status:'招募中'})),true));
console.log(JSON.stringify(out,null,2));
