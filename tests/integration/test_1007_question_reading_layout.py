"""Question-led B comparison reading. Presentation only, not clinical acceptance."""

import re
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("case", (
    "cross_study_positive",
    "longitudinal",
    "trajectory_before_scalars",
    "filtered_sparse",
    "filtered_sparse_zero",
    "filtered_sparse_clear",
    "filtered_sparse_longtitle",
    "filtered_dense_scalars",
    "heading_source_targets",
    "shared_long_source_titles",
    "shared_repeated_studies",
    "shared_grid_span_4",
    "shared_grid_span_6",
    "shared_grid_span_8",
    "shared_grid_span_12",
    "mixed_question_facet",
    "mixed_question_zero",
    "mixed_question_clear",
    "descriptive_question",
    "descriptive_filter",
    "descriptive_clear",
))
def test_question_reading_leads_with_scoped_plots_without_merging_frames(case: str) -> None:
    root = Path(__file__).resolve().parents[2]
    script = root / "src/ci_workflow/renderers/portal/assets/report-b.js"
    common = root / "src/ci_workflow/renderers/portal/assets/portal.js"
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const common=fs.readFileSync(process.argv[2],'utf8');
const which=process.argv[3];
function slice(text,name,until){
 const start=text.indexOf('  function '+name+'(');
 const end=text.indexOf(until,start+5);
 assert.ok(start>=0&&end>start,name);
 return text.slice(start,end);
}
class Node {
 constructor(tag='div'){this.tagName=String(tag).toUpperCase();this.children=[];this.dataset={};
  this.attributes={};this.className='';this.textContent='';this.parentElement=null;
  this.listeners={};this.hidden=false;this.open=false;this.disabled=false;this.value='';this.id='';}
 appendChild(child){if(child.parentElement)child.parentElement.removeChild(child);
  this.children.push(child);child.parentElement=this;return child;}
 get firstChild(){return this.children[0]||null;}
 insertBefore(child,reference){if(child.parentElement)child.parentElement.removeChild(child);
  const at=reference?this.children.indexOf(reference):-1;
  if(at<0)this.children.push(child);else this.children.splice(at,0,child);
  child.parentElement=this;return child;}
 removeChild(child){const at=this.children.indexOf(child);
  if(at>=0)this.children.splice(at,1);child.parentElement=null;return child;}
 replaceChildren(){this.children.forEach(child=>child.parentElement=null);this.children=[];}
 setAttribute(key,value){this.attributes[key]=String(value);if(key==='id')this.id=String(value);}
 getAttribute(key){return Object.prototype.hasOwnProperty.call(this.attributes,key)
  ?this.attributes[key]:null;}
 addEventListener(type,fn){(this.listeners[type]=this.listeners[type]||[]).push(fn);}
 get options(){return this.children;}
 matches(selector){
  if(selector[0]==='.')return this.className.split(' ').includes(selector.slice(1));
  if(selector[0]==='['){const attr=selector.slice(1,-1).split('=')[0];
   return Object.prototype.hasOwnProperty.call(this.attributes,attr);}
  return this.tagName===selector.toUpperCase();
 }
 querySelectorAll(selector){const found=[];
  const visit=node=>node.children.forEach(child=>{if(child.matches(selector))found.push(child);
   visit(child);});
  visit(this);return found;}
 querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
}
function text(node){return [node.textContent||'',...node.children.map(text)].join('');}
function walk(node,visit){visit(node);node.children.forEach(child=>walk(child,visit));}
const QUESTION='瘙痒NRS改善≥4分';
const LONG='Percentage of Participants Achieving >=4-Point Improvement '+
 'From Baseline in WI-NRS at Week 24';
const rows={};
function row(id,study,extra){
 const value={row_id:id,trial_id:study,source_version_id:'source-v1',
  source_measure_path:'outcome[15]',
  product_zh:study==='NCT04501666'?'奈莫利珠单抗':'度普利尤单抗',arm:'真实治疗组',unit:'%',
  unit_label_zh:'受试者百分比',time:'Week 4',value:12,display_label_zh:LONG,
  _chart_identity_label:(study==='NCT04501666'?'奈莫利珠单抗｜OLYMPIA':'度普利尤单抗｜PRIME2')};
 Object.assign(value,extra||{});rows[id]=value;return value;
}
function wrapperFor(group,index,span=12){
 const wrapper=new Node();wrapper.className='kz-chart-module__group';
 wrapper.setAttribute('data-group-index',index);
 // These attributes already belong to the shared renderer's PresentationPlan.
 wrapper.setAttribute('data-grid-span',span);
 wrapper.setAttribute('data-observation-count',group.rows.length);
 const title=new Node('h3');title.className='kz-chart-group__title';
 title.textContent=group.title_zh;
 const context=new Node('p');context.className='kz-chart-group__context';
 context.textContent='完整源研究、分析集与观察时间';
 const unit=new Node('p');unit.className='kz-chart-group__unit';unit.textContent='原始单位：%';
 const single=group.rows.length===1;
 const chart=new Node();chart.className='kz-chart-group__chart'+
  (single?' kz-chart-group__chart--single-fact':'');
 if(single){
  const number=new Node('strong');number.className='kz-chart-single-fact__value';
  number.textContent=group.rows[0].value+' %';chart.appendChild(number);
  const context=new Node('span');context.className='kz-chart-single-fact__context';
  context.textContent='正式药名';chart.appendChild(context);
 }
 group.rows.forEach(item=>{
  const button=new Node('button');button.className='kz-chart-single-fact__source';
  button.setAttribute('data-row-id',item.row_id);
  button.setAttribute('data-chart-evidence-open',item.row_id);
  chart.appendChild(button);
 });
 const details=new Node('details');details.className='kz-complete-table';
 const summary=new Node('summary');summary.textContent='完整表';details.appendChild(summary);
 const table=new Node('table');table.setAttribute('data-group-index',index);
 details.appendChild(table);
 wrapper.appendChild(title);wrapper.appendChild(context);wrapper.appendChild(unit);
 wrapper.appendChild(chart);wrapper.appendChild(details);
 wrapper.__title=title;wrapper.__details=details;wrapper.__buttons=chart.querySelectorAll('button');
 wrapper.__context=context;wrapper.__unit=unit;wrapper.__chart=chart;wrapper.__table=table;
 return wrapper;
}
const module=new Node();module.id='kz-chart-module';
const heading=new Node('h1');heading.id='full-study-comparison-heading';
heading.textContent='全研究横比';
const host=new Node('section');host.id='full-study-comparison';
const status=new Node('p');status.setAttribute('data-comparison-status','');
const unmatched=new Node('span');unmatched.setAttribute('data-comparison-unmatched-count','0');
const table=new Node('table');table.setAttribute('data-primary-comparison-table','');
const thead=new Node('thead');const tbody=new Node('tbody');
table.appendChild(thead);table.appendChild(tbody);
const select=new Node('select');select.setAttribute('data-comparison-column','');
const prev=new Node('button');prev.setAttribute('data-comparison-prev','');
const next=new Node('button');next.setAttribute('data-comparison-next','');
host.appendChild(heading);host.appendChild(select);host.appendChild(prev);host.appendChild(next);
host.appendChild(status);host.appendChild(unmatched);host.appendChild(table);
const overviewHead=new Node();overviewHead.className='kz-b-section-heading';
overviewHead.textContent='关键结果';
const overview=new Node('details');overview.setAttribute('data-summary-observations','');
overview.open=true;
overview.appendChild(overviewHead);overview.appendChild(module);
const roots=[host,overview];
function byId(id){let found=null;roots.forEach(root=>walk(root,node=>{
 if(node.id===id)found=node;}));return found;}
const calls=[];
let url='https://example.test/overview.html?view=comparison';
const sandbox={comparisonQuestion:'',comparisonPage:1,resultQuery:'',rowById:rows,searchById:{},
 fullChartGroups:[],URL,URLSearchParams,JSON,Object,String,Number,Math,
 window:{location:{get search(){return new URL(url).search;},get href(){return url;}},
  history:{replaceState(_,__,next){url=String(next);}},__CHART_GROUPS__:[],
  __COMPARISON_QUERY__:null,__B_COMPARISON_WORKSPACE__:null,
  __CHART_SYNC__:{replaceGroups(groups){sandbox.window.__CHART_GROUPS__=groups;
   module.children.slice().forEach(child=>module.removeChild(child));
   groups.forEach((group,index)=>module.appendChild(wrapperFor(group,index)));}}},
 document:{body:{dataset:{}},querySelector(selector){return overview.matches(selector)?overview:
  overviewHead.matches(selector)?overviewHead:null;},
  querySelectorAll(){return [];},getElementById:byId,createElement(tag){return new Node(tag);}},
 matches(id,state){return !state.trial||rows[id].trial_id===state.trial;},
 selectedState(){return sandbox.state||{};},state:{}};
vm.runInNewContext(slice(common,'createComparisonQuestionOrder',
 '\n  window.__COMPARISON_QUERY__'),sandbox);
sandbox.window.__COMPARISON_QUERY__=sandbox.createComparisonQuestionOrder();
vm.runInNewContext(slice(source,'organizeComparisonCharts','\n  function ')+'\n'+
 slice(source,'renderComparisonWorkspace','\n  function '),sandbox);
function ids(node){const found=[];walk(node,item=>{
 const id=item.getAttribute&&item.getAttribute('data-row-id');
 if(id)found.push(id);});return found.sort();}
if(which==='trajectory_before_scalars'){
 const timeline={comparison_purpose:'within_source_measure_time_axis',
  scientific_group_kind:'within_source_longitudinal',rows:[
   row('week1','NCT04202679',{time:'Week 1',value:1.3}),
   row('week24','NCT04202679',{time:'Week 24',value:57.7})]};
 const counts={comparison_purpose:'clinical_question_descriptive',rows:[
  row('count1','NCT04501666',{unit:'Participants',value:78}),
  row('count2','NCT04501679',{unit:'Participants',value:75})]};
 const groups=[counts,timeline],before=JSON.stringify(groups);
 groups.forEach((g,i)=>module.appendChild(wrapperFor(g,i)));
 sandbox.organizeComparisonCharts(groups,{study_labels:{},columns:[{question_known:true,
  question_label:QUESTION,row_ids:Object.keys(rows)}]});
 assert.equal(module.querySelector('.kz-b-study-panel').dataset.studyId,'NCT04202679',
  'B wrapper must not undo the common timecourse-first reading order');
 assert.deepEqual(ids(module),Object.keys(rows).sort(),'every source target retained');
 assert.equal(JSON.stringify(groups),before,'reading order does not change scientific frames');
}else if(which.startsWith('filtered_')){
 const groups=[];
 for(let i=1;i<=6;i++)groups.push({scientific_group_id:'facet-pruritus',cross_trial:false,rows:[
  row('a-'+i,'NCT04202679',{time:'Week '+i,value:20+i})]});
 groups.push({scientific_group_id:'facet-pruritus',cross_trial:false,rows:[
  row('b-1','NCT04501666',{time:'Week 16',value:45})]});
 groups.push({scientific_group_id:'facet-pruritus',cross_trial:false,rows:[
  row('b-2','NCT04501666',{time:'Week 24',value:51})]});
 if(which==='filtered_sparse_zero')rows['b-1'].value=0;
 if(which==='filtered_sparse_clear')Object.assign(rows['b-2'],
  {value:null,disclosure_state:'user_cleared',renderable:false,original_value:51});
 if(which==='filtered_dense_scalars')for(let i=3;i<=6;i++)groups.push({
  scientific_group_id:'facet-pruritus',cross_trial:false,rows:[
   row('b-'+i,'NCT04501666',{time:'Week '+i,value:20+i})]});
 const selectedIds=groups.filter(g=>g.rows[0].trial_id==='NCT04501666')
  .map(g=>g.rows[0].row_id).sort();
 const before=JSON.stringify(groups);
 sandbox.fullChartGroups=groups;
 sandbox.window.__B_COMPARISON_WORKSPACE__={study_ids:['NCT04202679','NCT04501666'],
  study_labels:{NCT04202679:'PRIME2｜NCT04202679',NCT04501666:'OLYMPIA｜NCT04501666'},
  membership:{row_ids:Object.keys(rows)},columns:[{id:'facet-pruritus',question_id:'pruritus-nrs',
   question_known:true,question_label:QUESTION,title:QUESTION,cells:{
    NCT04202679:groups.filter(g=>g.rows[0].trial_id==='NCT04202679').map(g=>g.rows[0].row_id),
    NCT04501666:selectedIds}}]};
 if(which==='filtered_sparse_longtitle')
  sandbox.window.__B_COMPARISON_WORKSPACE__.study_labels.NCT04501666=LONG.repeat(4);
 sandbox.state={trial:'NCT04501666'};
 sandbox.renderComparisonWorkspace(sandbox.state);
 assert.equal(JSON.stringify(groups),before,'filtering must not rewrite scientific frames');
 assert.equal(heading.textContent,QUESTION,'the chosen question leads, not the generic page title');
 assert.equal(module.parentElement,host,
  'plots belong to the comparison reading, not the overview dump');
 assert.ok(host.children.indexOf(module)<host.children.indexOf(status));
 assert.equal(overview.hidden,true,'unrelated overview dump stays out of the comparison reading');
 assert.equal(status.textContent,selectedIds.length+'组结果');
 assert.doesNotMatch(status.textContent,/项相关研究|个研究分面|本问题条件分面/);
 assert.deepEqual(ids(module),selectedIds);
 const records=module.querySelector('.kz-b-study-records');
 assert.ok(records&&records.tagName==='DETAILS');
 assert.equal(records.open,selectedIds.length<=4,
  'few source observations stay immediately readable; dense auxiliary records stay closed');
 assert.equal(records.querySelectorAll('.kz-chart-module__group').length,selectedIds.length);
 const originalTitle=records.querySelector('.kz-b-study-original-title');
 assert.ok(originalTitle&&originalTitle.parentElement.className==='kz-complete-table',
  'opening sparse values must not also dump the original English study title');
 assert.equal(originalTitle.textContent,
  sandbox.window.__B_COMPARISON_WORKSPACE__.study_labels.NCT04501666);
 assert.equal(sandbox.window.__CHART_GROUPS__.length,selectedIds.length,
  'status follows the recomputed groups');
 assert.ok(sandbox.window.__CHART_GROUPS__.every(group=>group.rows.every(item=>item.trial_id==='NCT04501666')));
}else if(which.startsWith('descriptive_')){
 const a=row('known-a','NCT04202679',{unit:'Participants',value:75});
 const b=row('known-b','NCT04501666',{unit:'Participants',value:78});
 if(which==='descriptive_clear')Object.assign(b,
  {value:null,disclosure_state:'user_cleared',renderable:false,original_value:78});
 const other=row('other-question','NCT90000001',{value:15});
 const groups=[a,b,other].map((r,i)=>({scientific_group_id:'facet-'+i,cross_trial:false,rows:[r]}));
 const descriptive={scientific_group_id:'descriptive-view',cross_trial:false,identity_series:true,
  comparison_purpose:'clinical_question_descriptive',question_id:'known-question',
  title_zh:QUESTION+' · 人数',metric_label_zh:'人数',rows:[a,b]};
 const workspace={study_ids:['NCT04202679','NCT04501666','NCT90000001'],study_labels:{},
  membership:{row_ids:Object.keys(rows)},descriptive_groups:[descriptive],columns:[{
   id:'known-column',question_id:'known-question',question_known:true,
   question_label:QUESTION,title:QUESTION,scientific_facet_ids:['facet-0','facet-1'],
   row_ids:['known-a','known-b'],cells:{NCT04202679:['known-a'],NCT04501666:['known-b']}},
  {id:'other-column',question_id:'other-question',question_known:true,
   question_label:'另一结局',title:'另一结局',scientific_facet_ids:['facet-2'],
   row_ids:['other-question'],cells:{NCT90000001:['other-question']}}]};
 const frozen=JSON.stringify({groups,workspace});
 sandbox.fullChartGroups=groups;sandbox.window.__B_COMPARISON_WORKSPACE__=workspace;
 if(which==='descriptive_filter')sandbox.state={trial:'NCT04501666'};
 sandbox.renderComparisonWorkspace(sandbox.state);
 assert.equal(JSON.stringify({groups,workspace}),frozen);
 assert.deepEqual(ids(table),ids(module),'same filtered question drives table and graph');
 const actual=sandbox.window.__CHART_GROUPS__;
 assert.equal(actual.length,1,'a shared descriptive metric is not two isolated scalar cards');
 if(which==='descriptive_filter'){
  assert.equal(actual[0].rows.length,1);
 }else{
  assert.equal(actual[0].comparison_purpose,'clinical_question_descriptive');
  const panel=module.querySelector('.kz-b-shared-plot');
  assert.ok(panel,'descriptive multi-study plot is primary; no harmonized permission invented');
  assert.equal(panel.dataset.sharedPlot,'source-posted');
  assert.equal(panel.children[0].textContent,QUESTION+' · 人数');
  assert.equal(actual[0].cross_trial,false,'no harmonization invented');
 }
 if(which==='descriptive_clear')assert.equal(actual[0].rows[1].value,null);
 sandbox.state={};
 select.value='other-question';select.listeners.change[0]();
 assert.deepEqual(ids(table),['other-question']);assert.deepEqual(ids(module),['other-question']);
}else if(which.startsWith('mixed_question_')){
 const a=row('known-a','NCT04202679',{value:which==='mixed_question_zero'?0:56});
 const b=row('known-b','NCT04501666',{value:48});
 if(which==='mixed_question_clear')Object.assign(b,
  {value:null,disclosure_state:'user_cleared',renderable:false,original_value:48});
 const other=row('other-question','NCT90000001',{value:15});
 // One retained scientific frame may have distinct descriptive question
 // bindings. Choosing one question must not copy its sibling into the plot.
 const groups=[{scientific_group_id:'shared-facet',cross_trial:false,rows:[a,b,other]}];
 const frozen=JSON.stringify(groups);
 sandbox.fullChartGroups=groups;
 sandbox.window.__B_COMPARISON_WORKSPACE__={study_ids:Object.keys(rows).map(id=>rows[id].trial_id),
  study_labels:{},membership:{row_ids:Object.keys(rows)},columns:[{
   id:'known-column',question_id:'known-question',question_known:true,
   question_label:QUESTION,title:QUESTION,scientific_facet_ids:['shared-facet'],
   row_ids:['known-a','known-b'],cells:{NCT04202679:['known-a'],NCT04501666:['known-b']}},
  {id:'unresolved-column',question_id:'unresolved-question',question_known:false,
   question_label:'另一测量',title:'另一测量',scientific_facet_ids:['shared-facet'],
   row_ids:['other-question'],cells:{NCT90000001:['other-question']}}]};
 sandbox.renderComparisonWorkspace({});
 assert.equal(JSON.stringify(groups),frozen,
  'query projection must leave scientific frames unchanged');
 assert.deepEqual(ids(table),['known-a','known-b']);
 assert.deepEqual(ids(module),ids(table),
  'plot and primary matrix must have the same current query');
 assert.equal(JSON.stringify(sandbox.window.__CHART_GROUPS__.flatMap(g=>g.rows.map(r=>r.row_id)).sort()),
  JSON.stringify(['known-a','known-b']));
 // A zero or cleared member remains in the selected query; no row is borrowed
 // from the next question just because it shares a facet identifier.
 assert.equal(rows['known-a'].value,which==='mixed_question_zero'?0:56);
 if(which==='mixed_question_clear')assert.equal(rows['known-b'].disclosure_state,'user_cleared');
 select.value='unresolved-question';select.listeners.change[0]();
 assert.deepEqual(ids(table),['other-question']);
 assert.deepEqual(ids(module),['other-question']);
}else if(which==='cross_study_positive'||which.startsWith('shared_')){
 const first={scientific_group_id:'frame-shared',numeric_frame:{id:'frame-shared'},cross_trial:true,
  identity_series:true,title_complete:true,title_zh:LONG,rows:[
   row('shared-a','NCT04202679',{time:'Week 24',value:56}),
   row('shared-b','NCT04501666',{time:'Week 24',value:48})]};
 const second={scientific_group_id:'frame-other',numeric_frame:{id:'frame-other'},cross_trial:true,
  identity_series:true,title_complete:true,title_zh:'另一科学分面的原始定义，不得并入上一比较框',rows:[
   row('other-a','NCT04202679',{product_zh:'度普利尤单抗',
    _chart_identity_label:'度普利尤单抗｜PRIME2',time:'Week 16'}),
   row('other-c','NCT99999999',{product_zh:'另一产品',trial_id:'NCT99999999',
    _chart_identity_label:'另一产品｜OTHER',time:'Week 16'})]};
 if(which==='shared_repeated_studies'){
  const studies=['NCT04202679','NCT04501666','NCT90000001','NCT90000002'];
  first.rows=studies.flatMap((study,index)=>[0,1,2].map(arm=>row('study-'+index+'-arm-'+arm,
   study,{trial_id:arm===1?study.toLowerCase():study,value:56,arm:'原始组别'+arm,
    trial_zh:LONG+'｜登记研究'+index,
    _chart_identity_label:'完整源身份｜'+study+'｜原始组别'+arm})));
 }
 const groups=[first,second];
 if(which==='shared_long_source_titles')groups.forEach(group=>group.rows.forEach(item=>{
  item.trial_zh=LONG.repeat(4);item._chart_identity_label=LONG.repeat(4);
 }));
 const frozen=JSON.stringify(groups);
 const span=which.startsWith('shared_grid_span_')?Number(which.split('_').pop()):6;
 const cards=groups.map((group,index)=>wrapperFor(group,index,span));
 const sourceButtons=cards.flatMap(card=>card.__buttons);
 sourceButtons.forEach(button=>button.addEventListener('click',function(){
  calls.push(button.getAttribute('data-row-id'));
 }));
 const listeners=sourceButtons.map(button=>button.listeners.click[0]);
 cards.forEach(card=>module.appendChild(card));
 sandbox.organizeComparisonCharts(groups,{study_labels:{},columns:[{question_known:true,
  question_label:QUESTION,row_ids:first.rows.map(item=>item.row_id)},{question_known:true,
  question_label:'皮损IGA达到0/1',row_ids:['other-a','other-c']}]});
 assert.equal(JSON.stringify(groups),frozen,'layout must not merge or rewrite numeric frames');
 assert.equal(module.querySelectorAll('.kz-chart-module__group').length,2);
 const shared=module.querySelectorAll('.kz-b-shared-plot');
 assert.equal(shared.length,2,'each already-qualified frame stays its own primary plot');
 const byQuestion={};
 shared.forEach(panel=>{byQuestion[panel.children[0].textContent]=panel;});
 const primary=byQuestion[QUESTION];
 assert.equal(primary.dataset.sharedPlot,'cross-study');
 assert.equal(primary.dataset.gridSpan,String(span),
  'the existing PresentationPlan span belongs to the outer plot card');
 assert.notEqual(primary.dataset.studyId,'NCT04202679');
 assert.doesNotMatch(primary.children[0].textContent,/原比较框|NCT04202679|待核/);
 const identities=primary.querySelector('.kz-b-shared-plot__identities');
 assert.ok(identities&&identities.parentElement===primary);
 assert.match(identities.textContent,/度普利尤单抗｜NCT04202679/);
 assert.match(identities.textContent,/奈莫利珠单抗｜NCT04501666/);
 assert.doesNotMatch(identities.textContent,/真实治疗组|原始组别/,
  'arm identities belong to the legend and full disclosure, not a repeated study heading');
 assert.doesNotMatch(identities.textContent,/Percentage of Participants/);
 if(which==='shared_long_source_titles')assert.ok(text(cards[0].__details).includes(LONG));
 assert.equal(byQuestion['皮损IGA达到0/1'].dataset.sharedPlot,'cross-study');
 assert.match(byQuestion['皮损IGA达到0/1'].querySelector('.kz-b-shared-plot__identities').textContent,/另一产品｜NCT99999999/);
 assert.doesNotMatch(byQuestion['皮损IGA达到0/1'].querySelector('.kz-b-shared-plot__identities').textContent,/奈莫利珠单抗/);
 assert.equal(cards[0].__title.parentElement.className,'kz-complete-table');
 cards.forEach(card=>{
  assert.equal(card.getAttribute('data-grid-span'),String(span),'do not rewrite the shared plan');
  assert.equal(card.__context.parentElement,card.__details);
  assert.equal(card.__unit.parentElement,card.__details);
  assert.ok(module.querySelectorAll('.kz-chart-group__chart').includes(card.__chart));
  assert.equal(card.__details.querySelector('table'),card.__table,
   'reuse the complete source table');
 });
 assert.deepEqual(ids(module),groups.flatMap(group=>group.rows.map(item=>item.row_id)).sort(),
  'every original fact target remains reachable, even when values and arms repeat');
 sourceButtons.forEach((button,index)=>{
  assert.ok(module.querySelectorAll('button').includes(button));
  assert.equal(button.listeners.click[0],listeners[index]);
  button.listeners.click[0]();
 });
 assert.deepEqual(calls,sourceButtons.map(button=>button.getAttribute('data-row-id')));
 if(which==='shared_repeated_studies'){
  assert.equal(first.rows.length,12);
  const studies=['NCT04202679','NCT04501666','NCT90000001','NCT90000002'];
  assert.equal(identities.textContent.split('；').length,studies.length,
   'twelve facts across four studies need four heading identities');
  studies.forEach(study=>assert.equal(identities.textContent.split(study).length-1,1));
  first.rows.forEach(item=>{
   const disclosure=text(cards[0].__details);
   assert.ok(disclosure.includes(item._chart_identity_label),'retain the complete source identity');
   assert.ok(disclosure.includes(item.trial_zh),'retain the original registry title');
   assert.ok(disclosure.includes(item.arm),'retain every original arm identity');
  });
 }
 assert.ok(!module.querySelector('.kz-b-study-records'));
 assert.doesNotMatch(text(module),/不代表|不等于|证据是否充分|边界|限制/);
}else{
 const group={scientific_group_id:'frame-line',numeric_frame:{id:'frame-line'},cross_trial:false,
  identity_series:true,comparison_purpose:'within_source_measure_time_axis',
  scientific_group_kind:'within_source_longitudinal',title_complete:true,_chart_type:'line',
  title_zh:LONG,rows:[2,12,24].map(week=>row('line-'+week,'NCT04202679',
   {time:'Week '+week,value:week}))};
 const groups=[group];const before=JSON.stringify(groups);
 const card=wrapperFor(group,0);module.appendChild(card);
 const button=card.__buttons[0];
 button.addEventListener('click',function(){calls.push(button.getAttribute('data-row-id'));});
 const listener=button.listeners.click[0];
 sandbox.organizeComparisonCharts(groups,{study_labels:{NCT04202679:'PRIME2｜NCT04202679'},
  columns:[{question_known:true,question_label:QUESTION,row_ids:group.rows.map(item=>item.row_id)}]});
 assert.equal(JSON.stringify(groups),before);
 assert.equal(module.querySelectorAll('.kz-chart-group__chart').length,1,
  'the source-qualified line stays one plot');
 assert.equal(module.querySelectorAll('.kz-chart-module__group').length,1);
 const panel=module.querySelector('.kz-b-study-panel');
 assert.equal(panel.children[0].textContent,'PRIME2｜NCT04202679');
 assert.equal(panel.dataset.studyId,'NCT04202679');
 assert.notEqual(panel.dataset.sharedPlot,'cross-study');
 assert.doesNotMatch(panel.children[0].textContent,/原比较框/);
 const measure=module.querySelector('.kz-b-measurement-panel');
 assert.equal(measure.children[0].textContent,QUESTION);
 assert.equal(card.__title.parentElement,card.__details,
  'duplicate long definition moves into the complete table');
 assert.ok(text(card.__details).includes(LONG));
 assert.equal(card.__details.querySelector('table').getAttribute('data-group-index'),'0');
 assert.deepEqual(ids(module),['line-12','line-2','line-24'].sort());
 assert.ok(module.querySelectorAll('button').includes(button));
 assert.equal(button.listeners.click[0],listener,'moving the card keeps the source listener');
 button.listeners.click[0]();
 assert.deepEqual(calls,['line-2']);
 assert.ok(!module.querySelector('.kz-b-study-records'),
  'a multi-observation line is not a closed scalar dump');
 assert.doesNotMatch(text(panel),/不代表|不等于|证据是否充分/);
 if(which==='heading_source_targets'){
  assert.equal(card.__title.parentElement.className,'kz-complete-table');
  assert.ok(card.__details.querySelector('.kz-chart-group__title')===card.__title);
 }
}
"""
    result = subprocess.run(
        ["node", "-e", probe, str(script), str(common), case],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("span", (4, 6, 8, 12))
def test_shared_plot_geometry_places_existing_plan_on_the_outer_card(span: int) -> None:
    root = Path(__file__).resolve().parents[2]
    css = (root / "src/ci_workflow/renderers/portal/assets/report-b.css").read_text(
        encoding="utf-8",
    )
    selector = f'.kz-b-shared-plot[data-grid-span="{span}"]' if span < 12 else ".kz-b-study-panel"
    selectors = {
        selector: f"grid-column:span{span};" if span < 12 else "grid-column:1/-1;",
        ".kz-b-shared-plot .kz-b-measurement-observations > .kz-chart-module__group":
            "grid-column:1/-1;",
        ".kz-b-shared-plot:has(.kz-complete-table[open])": "grid-column:1/-1;",
    }
    for selector, required in selectors.items():
        match = re.search(re.escape(selector) + r"\s*\{([^}]+)\}", css)
        assert match is not None, selector
        block = re.sub(r"\s+", "", match.group(1))
        assert required in block
        assert not any(token in block for token in (
            "font-size", "height:", "overflow:hidden", "ellipsis", "line-clamp", "!important",
        )), "layout must not shrink, clip or override chart content"
