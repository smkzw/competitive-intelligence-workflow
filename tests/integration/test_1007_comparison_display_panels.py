"""Display-only production DOM organization; not clinical or pixel acceptance."""

import re
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("case", (
    "dense", "sparse", "unresolved", "multi_observation", "cross_study", "typed_units",
))
def test_comparison_panels_preserve_scientific_frames_and_source_targets(case: str) -> None:
    script = (Path(__file__).resolve().parents[2]
              / "src/ci_workflow/renderers/portal/assets/report-b.js")
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8'),which=process.argv[2];
const start=source.indexOf('  function organizeComparisonCharts(');
const end=source.indexOf('\n  function ',start+5);
assert.ok(start>=0 && end>start,'production comparison panels are missing');
class Node {
 constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.dataset={};
  this.attributes={};this.className='';this.textContent='';this.parentElement=null;}
 appendChild(child){if(child.parentElement)child.parentElement.removeChild(child);
  this.children.push(child);child.parentElement=this;return child;}
 get firstChild(){return this.children[0]||null;}
 insertBefore(child,reference){if(child.parentElement)child.parentElement.removeChild(child);
  this.children.splice(this.children.indexOf(reference),0,child);child.parentElement=this;}
 removeChild(child){this.children.splice(this.children.indexOf(child),1);child.parentElement=null;}
 setAttribute(k,v){this.attributes[k]=String(v);}
 getAttribute(k){return this.attributes[k];}
 querySelectorAll(selector){const found=[];const match=n=>selector[0]==='.' ?
  n.className.split(' ').includes(selector.slice(1)) : n.tagName===selector.toUpperCase();
  const visit=n=>n.children.forEach(c=>{if(match(c))found.push(c);visit(c);});
  visit(this);return found;}
 querySelector(s){return this.querySelectorAll(s)[0]||null;}
}
const module=new Node(), originals=[], groups=[];
function add(id,study,measure,week,value,unit='percentage of participants',count=1){
 const rows=Array.from({length:count},(_,i)=>({row_id:id+(i?'-extra':''),trial_id:study,
  source_version_id:'source-v1',source_measure_path:measure,actual_timepoint:week,
  actual_timepoint_unit:'week',time:'Week '+week,value:value+i,unit,
  unit_label_zh:unit==='percentage of participants'?'受试者百分比':unit,
  product_zh:'正式药名',arm:'真实治疗组',display_label_zh:'瘙痒改善',
  source_param_type:'NUMBER',statistic_form:'not_reported'}));
 const group={scientific_group_id:'frame-'+id,rows,title_zh:'完整原始口径 '+id,
  numeric_frame:{id:'independent-'+id}};groups.push(group);
 const wrapper=new Node();wrapper.className='kz-chart-module__group';
 wrapper.setAttribute('data-group-index',groups.length-1);
 const title=new Node('h3');title.className='kz-chart-group__title';
 title.textContent=group.title_zh;
 const chart=new Node();chart.className='kz-chart-group__chart'+
  (count===1?' kz-chart-group__chart--single-fact':'');
 const number=new Node('strong');number.className='kz-chart-single-fact__value';
 number.textContent=value+' '+unit;chart.appendChild(number);
 const context=new Node('span');context.className='kz-chart-single-fact__context';
 context.textContent='正式药名 · '+study+' · 真实治疗组';chart.appendChild(context);
 const button=new Node('button');button.className='kz-chart-single-fact__source';
 button.setAttribute('data-row-id',id);button.setAttribute('data-chart-evidence-open',id);
 chart.appendChild(button);
 const details=new Node('details');details.className='kz-complete-table';
 details.appendChild(new Node('summary'));const table=new Node('table');
 table.setAttribute('data-group-index',groups.length-1);details.appendChild(table);
 wrapper.appendChild(title);wrapper.appendChild(chart);wrapper.appendChild(details);module.appendChild(wrapper);
 originals.push({wrapper,button,title,context,number,table,details});
}
if(which==='dense'){
 for(let i=1;i<=24;i++)add('weekly-'+i,'NCT04202679','outcome[15]',i,30+i);
 add('landmark','NCT04202679','outcome[16]',24,60);
 add('km','NCT04202679','outcome[17]',24,82.3,'%');
 add('nem-1','NCT04501666','outcome[3]',16,56,'participants');
 add('nem-2','NCT04501679','outcome[3]',16,45,'participants');
}else if(which==='typed_units'){
 add('count','NCT04202679','outcome[15]',4,78,'Participants');
 groups[0].rows[0].unit_label_zh='例';
 add('probability','NCT04202679','outcome[16]',4,0.67,'probability of participants');
 add('unknown','NCT04202679','outcome[17]',4,12,'未核原始单位全文');
}else if(which==='unresolved'){
 add('missing-path','NCT04202679','',4,12);
 add('unknown-study','','outcome[15]',4,12);
 add('known','NCT04202679','outcome[15]',4,12);
}else if(which==='multi_observation'||which==='cross_study'){
 add('shared-valid-frame','NCT04202679','outcome[15]',4,12,'%',2);
 if(which==='cross_study')groups[0].rows[1].trial_id='NCT04501666';
 add('single','NCT04202679','outcome[15]',8,15);
}else{
 add('week-20','NCT04202679','outcome[15]',20,50);
 add('week-2','NCT04202679','outcome[15]',2,25);
}
const before=JSON.stringify(groups);
const sandbox={document:{getElementById(id){return id==='kz-chart-module'?module:null;},
 createElement(tag){return new Node(tag);}},window:{__COMPARISON_QUERY__:{
 observationIds(ids,rows){return ids.slice().sort(
  (a,b)=>rows[a].actual_timepoint-rows[b].actual_timepoint);},
 valueText(row,missing){return row.value==null?missing:
  String(row.value)+(row.unit_label_zh||row.unit?' '+(row.unit_label_zh||row.unit):'');}}},
 Object,Array,String,Number,JSON,Math};
vm.runInNewContext(source.slice(start,end),sandbox);
sandbox.organizeComparisonCharts(groups,{study_labels:{NCT04202679:'PRIME2｜NCT04202679'}});
assert.equal(JSON.stringify(groups),before,'layout must not merge or rewrite numeric frames');
assert.equal(module.querySelectorAll('.kz-chart-module__group').length,groups.length);
originals.forEach((old,i)=>{
 assert.ok(module.querySelectorAll('button').includes(old.button),'same evidence target retained');
 assert.equal(old.button.getAttribute('data-row-id'),groups[i].rows[0].row_id);
 assert.equal(old.table.getAttribute('data-group-index'),String(i));
 assert.ok(module.querySelectorAll('table').includes(old.table));
 assert.ok(module.querySelectorAll('h3').includes(old.title),'full heading remains reachable');
 assert.ok(module.querySelectorAll('span').includes(old.context));
 assert.ok(module.querySelectorAll('strong').includes(old.number));
 if(groups[i].rows.length===1){
  const row=groups[i].rows[0];
  assert.equal(old.number.textContent,sandbox.window.__COMPARISON_QUERY__.valueText(row,''),
   'reuse the existing explicit unit label; no source-unit inference or value conversion');
 }
});
const panels=module.querySelectorAll('.kz-b-study-panel');
const measures=module.querySelectorAll('.kz-b-measurement-panel');
measures.forEach(m=>{
 assert.doesNotMatch(m.children[0].textContent,/not_reported/);
 const cards=m.querySelectorAll('.kz-chart-module__group');
 assert.equal(m.dataset.observationCount,String(cards.length),
  'actual wrapper scope, not guessed width');
 const compact=cards.length<=4&&cards.every(n=>n.dataset.comparisonCompact);
 assert.equal(m.className.split(' ').includes('kz-b-measurement-panel--compact'),compact,
  'few scalar measures may sit beside one another; multi-observation plots keep full geometry');
});
if(which==='dense'){
 assert.equal(panels.length,3);assert.equal(measures.length,5);
 const weekly=measures.find(n=>n.dataset.measurePath==='outcome[15]');
 assert.equal(weekly.querySelectorAll('.kz-chart-module__group').length,24);
 assert.deepEqual(weekly.querySelectorAll('.kz-b-observation-time').map(n=>n.textContent),
  Array.from({length:24},(_,i)=>'Week '+(i+1)));
 assert.match(panels[0].children[0].textContent,/PRIME2/);
 assert.ok(originals.every(o=>o.title.parentElement===o.details),
  'repeated complete headings are in reachable native disclosure, not dominant card headings');
}else if(which==='typed_units'){
 assert.equal(panels.length,1);assert.equal(measures.length,3);
 assert.deepEqual(originals.map(o=>o.number.textContent),
  ['78 例','0.67 probability of participants','12 未核原始单位全文']);
 assert.ok(groups.every(g=>g.rows[0].unit!=='%'),'probability was not turned into percent');
}else if(which==='sparse'){
 assert.equal(panels.length,1);assert.equal(measures.length,1);
 assert.deepEqual(module.querySelectorAll('.kz-b-observation-time').map(n=>n.textContent),
  ['Week 2','Week 20']);
}else if(which==='unresolved'){
 assert.equal(panels.length,3,'unknown identity/path must not be guessed into known panel');
}else{
 assert.equal(originals[0].title.parentElement,originals[0].wrapper,
  'a valid multi-observation plot remains intact, not turned into isolated facts');
 if(which==='cross_study'){
  assert.equal(panels.length,2);assert.match(panels[0].children[0].textContent,/原比较框/);
  assert.doesNotMatch(panels[0].children[0].textContent,/待核/);
 }
}
// Repeated rebuilding is handled by the chart controller, not accumulated sections.
const ids=module.querySelectorAll('button').map(n=>n.getAttribute('data-row-id')).sort();
sandbox.organizeComparisonCharts(groups,{study_labels:{}});
assert.equal(module.querySelectorAll('.kz-b-study-panel').length,panels.length);
assert.deepEqual(module.querySelectorAll('button').map(n=>n.getAttribute('data-row-id')).sort(),ids);
"""
    result = subprocess.run(["node", "-e", probe, str(script), case],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_sparse_measurements_have_real_horizontal_allocation_without_font_shrink() -> None:
    css = (Path(__file__).resolve().parents[2]
           / "src/ci_workflow/renderers/portal/assets/report-b.css").read_text()
    css = re.sub(r"\s+", "", css)
    assert ".kz-b-study-panel{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));" in css
    assert "--b-observation-span:6;grid-column:span6;" in css
    assert ".kz-b-measurement-panel:has(.kz-complete-table[open]){grid-column:1/-1;}" in css
    assert "font-size:16px" in css


def test_nested_scalar_grid_has_one_span_owner_for_one_few_and_dense_observations() -> None:
    css = (Path(__file__).resolve().parents[2]
           / "src/ci_workflow/renderers/portal/assets/report-b.css").read_text()
    rules = dict(re.findall(r"([^{}]+)\{([^{}]*)\}", css))
    rules = {selector.strip(): re.sub(r"\s+", "", body)
             for selector, body in rules.items()}
    # Real current29 four-width FAIL exposed competing equal-specificity rules.
    # One consumed variable avoids two selectors assigning contradictory spans.
    assert "--b-observation-span:3;" in rules[".kz-b-measurement-panel"]
    assert "--b-observation-span:6;" in rules[".kz-b-measurement-panel--compact"]
    one = '.kz-b-measurement-panel--compact[data-observation-count="1"]'
    assert "--b-observation-span:12;" in rules[one]
    cards = ".kz-b-measurement-observations > [data-comparison-compact]"
    assert "grid-column:spanvar(--b-observation-span);" in rules[cards]
    assert ".kz-b-measurement-panel--compact .kz-chart-module__group" not in rules
