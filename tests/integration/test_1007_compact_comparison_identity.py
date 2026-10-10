"""A/B full-study matrix compact identity family: presentation only.

The production renderers run over a mock DOM; pixels still require Ego QA.
Each repeated, exactly equal product/regimen identity must fold into one
visible group header while every fact ID, value, visit, unit, disclosure and
source trigger survives, and any differing identity keeps its own label.
"""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "src/ci_workflow/renderers/portal/assets"


def _run_node(probe: str, *paths: str) -> None:
    result = subprocess.run(
        ["node", "-e", probe, *paths], capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


IDENTITY_ONE = "帕博利珠单抗｜200mg Q3W"
IDENTITY_TWO = "帕博利珠单抗｜100mg Q3W"


def test_a_comparison_compacts_repeated_identity_without_losing_facts() -> None:
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const common=fs.readFileSync(process.argv[2],'utf8');
const start=source.indexOf('  function renderAComparison(');
const end=source.indexOf('\n  window.__A_COMPARISON_EVIDENCE__',start);
assert.ok(start>=0&&end>start);
class Node {
 constructor(){this.children=[];this.dataset={};this.attrs={};this.listeners={};}
 appendChild(n){this.children.push(n);return n;}
 insertBefore(n,ref){const index=this.children.indexOf(ref);
  this.children.splice(index<0?this.children.length:index,0,n);return n;}
 replaceChildren(){this.children=[];}
 setAttribute(k,v){this.attrs[k]=v;}
 addEventListener(k,f){this.listeners[k]=f;}
 querySelector(k){return lookup[k];}
 get options(){return this.children;}
}
const lookup={};
['[data-a-comparison-question]','[data-a-comparison-prev]','[data-a-comparison-next]',
 '[data-a-comparison-status]','[data-a-comparison-table]','thead','tbody']
 .forEach(k=>lookup[k]=new Node());
const host=new Node(),summary=new Node();
const identityOne='帕博利珠单抗｜200mg Q3W',identityTwo='帕博利珠单抗｜100mg Q3W';
const rows={
 p1:{row_id:'p1',a_row_id:'source-p1',trial_id:'trial-a',product_id:'drug-a',
  product_zh:'帕博利珠单抗',arm_detail:'200mg Q3W',value:12.5,unit:'%',time:'Week 24',
  _domain:'efficacy'},
 p2:{row_id:'p2',a_row_id:'source-p2',trial_id:'trial-a',product_id:'drug-a',
  product_zh:'帕博利珠单抗',arm_detail:'200mg Q3W',value:18,unit:'%',time:'Week 48',
  _domain:'efficacy'},
 p3:{row_id:'p3',a_row_id:'source-p3',trial_id:'trial-a',product_id:'drug-a',
  product_zh:'帕博利珠单抗',arm_detail:'200mg Q3W',value:20.1,unit:'%',time:'Week 96',
  difference_note:'分析人群不同，不共轴',_domain:'efficacy'},
 q1:{row_id:'q1',a_row_id:'source-q1',trial_id:'trial-a',product_id:'drug-a',
  product_zh:'帕博利珠单抗',arm_detail:'100mg Q3W',value:9.9,unit:'%',time:'Week 100',
  _domain:'efficacy'},
 q2:{row_id:'q2',a_row_id:'source-q2',trial_id:'trial-a',product_id:'drug-a',
  product_zh:'帕博利珠单抗',arm_detail:'100mg Q3W',value:11.1,unit:'%',time:'Week 104',
  _domain:'efficacy'},
 s1:{row_id:'s1',a_row_id:'source-s1',trial_id:'trial-a',product_id:'drug-a',
  product_zh:'纳武利尤单抗',value:7.7,unit:'%',time:'Week 12',_domain:'efficacy'}};
const columns=[{id:'col-1',question_id:'easi',question_known:true,question_label:'EASI',
 title:'EASI 75 应答率',cells:{'trial-a':['p1','p2','p3','q1','q2','s1']}}];
const workspace={membership:{row_ids:Object.keys(rows)},study_ids:['trial-a'],
 study_labels:{'trial-a':'PRIME｜NCT04202679'},columns};
let url='https://example.test/clinical-portfolio.html?view=comparison';
const sandbox={aComparisonPage:1,selected:{},
 trials:[{id:'trial-a',phase:'III',region:'CN'}],
 Object,JSON,String,Number,Math,URLSearchParams,
 productById(id){return {name:id,target:'target'};},
 dimensionMatches(_,actual,wanted){return actual===wanted;},
 window:{__A_COMPARISON_WORKSPACE__:workspace,__A_COMPARISON_ROWS__:rows,
  __A_COMPARISON_GROUPS__:[],
  location:{get search(){return new URL(url).search;},pathname:'/clinical-portfolio.html'},
  history:{replaceState(_,__,next){url=new URL(next,url).href;}},
  __CHART_SYNC__:{unplottedValueText(){return '用户清除，待重新核实';},
   replaceGroups(){}}},
 document:{body:{dataset:{}},querySelectorAll(){return [];},getElementById(){return host;},
  querySelector(){return summary;},
  createElement(){return new Node();}}};
const orderStart=common.indexOf('  function createComparisonQuestionOrder(');
const orderEnd=common.indexOf('\n  window.__COMPARISON_QUERY__',orderStart);
vm.runInNewContext(common.slice(orderStart,orderEnd),sandbox);
sandbox.window.__COMPARISON_QUERY__=sandbox.createComparisonQuestionOrder();
vm.runInNewContext(source.slice(start,end),sandbox);
sandbox.renderAComparison();
function text(n){return [n.textContent||'',...n.children.map(text)].join('|');}
function walk(n,visit){visit(n);for(const child of n.children)walk(child,visit);}
function facts(n,out){walk(n,node=>{
 if(node.attrs&&node.attrs['data-evidence-row-id'])out.push(node);});return out;}
function headers(node){return node.children.filter(
 n=>String(n.className||'').includes('kz-comparison-identity-header'));}
function compact(node){return String(node.className||'')
 .includes('kz-comparison-observation--compact');}
const cell=lookup.tbody.children[0].children[1],list=cell.children[0];
const headerNodes=headers(list);
assert.equal(headerNodes.length,2,'exactly one visible identity header per repeated run');
assert.equal(headerNodes[0].textContent,identityOne,'header carries the exact repeated identity');
assert.equal(headerNodes[1].textContent,identityTwo,'a different arm keeps its own header');
assert.equal(list.children[1],headerNodes[0],'header leads its own run');
assert.equal(list.children[5],headerNodes[1],'second run header leads its own facts');
assert.deepEqual([2,3,4,6,7].map(i=>compact(list.children[i])),
 [true,true,true,true,true],'repeated identity facts fold under their header');
assert.equal(compact(list.children[0]),false,'a sole fact never folds its identity');
assert.equal(compact(list.children[1]),false,'the header is not a compacted observation');
const buttons=facts(list,[]);
assert.equal(buttons.length,6,'every fact is still rendered exactly once');
assert.deepEqual(buttons.map(b=>b.attrs['data-evidence-row-id']),
 ['source-s1','source-p1','source-p2','source-p3','source-q1','source-q2'],
 'compaction preserves the shared visit presentation order and adds nothing');
buttons.forEach(b=>{assert.equal(b.attrs['data-evidence-collection'],'efficacy');
 assert.ok('data-open-evidence' in b.attrs,'source trigger survives compaction');});
const allText=text(list);
['12.5 %','18 %','20.1 %','9.9 %','11.1 %','7.7 %','Week 100','Week 104',
 '分析人群不同，不共轴',identityOne,identityTwo,'纳武利尤单抗']
 .forEach(s=>assert.ok(allText.includes(s),s));
assert.ok(text(list.children[2]).includes(identityOne),
 'the folded copy stays complete inside its own fact');
assert.ok(text(list.children[6]).includes(identityTwo),
 'the folded copy stays complete inside its own fact');
assert.equal(JSON.parse(host.dataset.displayedRowIds).length,6,'scope keeps every fact');
sandbox.renderAComparison();
const again=headers(lookup.tbody.children[0].children[1].children[0]);
assert.equal(again.length,2,'re-render rebuilds cells without accumulation');
"""
    _run_node(probe, str(ASSETS / "report-a.js"), str(ASSETS / "portal.js"))


def test_b_comparison_compacts_repeated_identity_without_losing_facts() -> None:
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const common=fs.readFileSync(process.argv[2],'utf8');
const start=source.indexOf('  function renderComparisonWorkspace(');
const end=source.indexOf('\n  function ',start+5);
assert.ok(start>=0&&end>start);
class Node {
 constructor(){this.children=[];this.dataset={};this.attrs={};this.listeners={};}
 appendChild(n){this.children.push(n);return n;}
 insertBefore(n,ref){const index=this.children.indexOf(ref);
  this.children.splice(index<0?this.children.length:index,0,n);return n;}
 replaceChildren(){this.children=[];}
 setAttribute(k,v){this.attrs[k]=v;}
 addEventListener(k,f){this.listeners[k]=f;}
 querySelector(k){return lookup[k];}
 get options(){return this.children;}
}
const lookup={};
['[data-comparison-column]','[data-comparison-prev]','[data-comparison-next]',
 '[data-comparison-status]','table','thead','tbody'].forEach(k=>lookup[k]=new Node());
const host=new Node();
const identityOne='帕博利珠单抗｜200mg Q3W',identityTwo='帕博利珠单抗｜100mg Q3W';
const rows={
 p1:{row_id:'p1',trial_id:'trial-a',product_zh:'帕博利珠单抗',arm:'200mg Q3W',
  value:12.5,unit:'%',time:'Week 24'},
 p2:{row_id:'p2',trial_id:'trial-a',product_zh:'帕博利珠单抗',arm:'200mg Q3W',
  value:18,unit:'%',time:'Week 48'},
 p3:{row_id:'p3',trial_id:'trial-a',product_zh:'帕博利珠单抗',arm:'200mg Q3W',
  value:20.1,unit:'%',time:'Week 96',difference_note:'分析人群不同，不共轴'},
 q1:{row_id:'q1',trial_id:'trial-a',product_zh:'帕博利珠单抗',arm:'100mg Q3W',
  value:9.9,unit:'%',time:'Week 100'},
 q2:{row_id:'q2',trial_id:'trial-a',product_zh:'帕博利珠单抗',arm:'100mg Q3W',
  value:11.1,unit:'%',time:'Week 104'},
 s1:{row_id:'s1',trial_id:'trial-a',product_zh:'纳武利尤单抗',
  value:7.7,unit:'%',time:'Week 12'}};
const workspace={study_ids:['trial-a'],study_labels:{'trial-a':'PRIME｜NCT04202679'},
 membership:{row_ids:Object.keys(rows)},
 columns:[{id:'column-1',question_id:'efficacy::easi75',question_known:true,
  question_label:'EASI75',title:'临床条件1',cells:{'trial-a':['p1','p2','p3','q1','q2','s1']}}]};
let state={},url='https://example.test/overview.html?view=comparison';
const sandbox={comparisonQuestion:'',comparisonPage:1,resultQuery:'',rowById:rows,searchById:{},
 fullChartGroups:[],
 URL,URLSearchParams,JSON,Object,String,Math,
 window:{__B_COMPARISON_WORKSPACE__:workspace,
  location:{get search(){return new URL(url).search;},get href(){return url;}},
  history:{replaceState(_,__,next){url=next;}},
  __CHART_SYNC__:{unplottedValueText(){return '用户清除，待重新核实';},replaceGroups(){}}},
 document:{body:{dataset:{}},querySelectorAll(){return [];},getElementById(){return host;},
  createElement(){return new Node();}},
 matches(){return true;},
 selectedState(){return state;}};
const orderStart=common.indexOf('  function createComparisonQuestionOrder(');
const orderEnd=common.indexOf('\n  window.__COMPARISON_QUERY__',orderStart);
vm.runInNewContext(common.slice(orderStart,orderEnd),sandbox);
sandbox.window.__COMPARISON_QUERY__=sandbox.createComparisonQuestionOrder();
vm.runInNewContext(source.slice(start,end),sandbox);
sandbox.renderComparisonWorkspace({});
function text(n){return [n.textContent||'',...n.children.map(text)].join('|');}
function walk(n,visit){visit(n);for(const child of n.children)walk(child,visit);}
function facts(n,out){walk(n,node=>{
 if(node.attrs&&node.attrs['data-evidence-open'])out.push(node);});return out;}
function headers(node){return node.children.filter(
 n=>String(n.className||'').includes('kz-comparison-identity-header'));}
function compact(node){return String(node.className||'')
 .includes('kz-comparison-observation--compact');}
const cell=lookup.tbody.children[0].children[1],list=cell.children[0];
const headerNodes=headers(list);
assert.equal(headerNodes.length,2,'exactly one visible identity header per repeated run');
assert.equal(headerNodes[0].textContent,identityOne,'header carries the exact repeated identity');
assert.equal(headerNodes[1].textContent,identityTwo,'a different arm keeps its own header');
assert.equal(list.children[1],headerNodes[0],'header leads its own run');
assert.equal(list.children[5],headerNodes[1],'second run header leads its own facts');
assert.deepEqual([2,3,4,6,7].map(i=>compact(list.children[i])),
 [true,true,true,true,true],'repeated identity facts fold under their header');
assert.equal(compact(list.children[0]),false,'a sole fact never folds its identity');
assert.equal(compact(list.children[1]),false,'the header is not a compacted observation');
const buttons=facts(list,[]);
assert.equal(buttons.length,6,'every fact is still rendered exactly once');
assert.deepEqual(buttons.map(b=>b.attrs['data-evidence-open']),
 ['s1','p1','p2','p3','q1','q2'],
 'compaction preserves the shared visit presentation order and adds nothing');
buttons.forEach(b=>{assert.equal(b.attrs['data-row-id'],b.attrs['data-evidence-open'],
 'source trigger survives compaction');});
const allText=text(list);
['12.5 %','18 %','20.1 %','9.9 %','11.1 %','7.7 %','Week 100','Week 104',
 '分析人群不同，不共轴',identityOne,identityTwo,'纳武利尤单抗']
 .forEach(s=>assert.ok(allText.includes(s),s));
assert.ok(text(list.children[2]).includes(identityOne),
 'the folded copy stays complete inside its own fact');
assert.ok(text(list.children[6]).includes(identityTwo),
 'the folded copy stays complete inside its own fact');
assert.equal(JSON.parse(host.dataset.displayedRowIds).length,6,'scope keeps every fact');
sandbox.renderComparisonWorkspace(state);
const again=headers(lookup.tbody.children[0].children[1].children[0]);
assert.equal(again.length,2,'re-render rebuilds cells without accumulation');
"""
    _run_node(probe, str(ASSETS / "report-b.js"), str(ASSETS / "portal.js"))


def test_shared_css_keeps_folded_identity_readable_and_never_shrinks_type() -> None:
    css = (ASSETS / "kangzhe-site.css").read_text(encoding="utf-8")
    marker = css.index(".kz-comparison-observation--compact .kz-comparison-fact__identity")
    block = css[marker : css.index("}", marker)]
    assert "clip" in block, "folded label uses the visually-hidden clip pattern"
    assert "display" not in block and "visibility" not in block, (
        "the folded copy must stay in the accessibility tree and page search"
    )
    assert "font-size" not in block and "!important" not in block
    header = css.index(".kz-comparison-identity-header")
    header_block = css[header : css.index("}", header)]
    assert "grid-column: 1 / -1" in header_block, "one header spans its whole run"
    assert "display: none" not in header_block and "font-size" not in header_block
    time_marker = css.index(".kz-comparison-observation--compact .kz-comparison-fact__time")
    time_block = css[time_marker : css.index("}", time_marker)]
    assert "grid-row: 1" in time_block, "value and visit share one compact line"


def test_shared_factory_unknown_identity_breaks_a_repeated_run() -> None:
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function createComparisonQuestionOrder(');
const end=source.indexOf('\n  window.__COMPARISON_QUERY__',start);
class Node {
 constructor(){this.children=[];this.className='';}
 appendChild(n){this.children.push(n);return n;}
 insertBefore(n,ref){this.children.splice(this.children.indexOf(ref),0,n);}
}
const sandbox={};vm.runInNewContext(source.slice(start,end),sandbox);
const factory=sandbox.createComparisonQuestionOrder();
const doc={createElement(){return new Node();}},cell=new Node();
const rows=[{product_zh:'度普利尤单抗',arm:'300mg Q2W'},
 {product_zh:'度普利尤单抗',arm:'300mg Q2W'},{},{},
 {product_zh:'度普利尤单抗',arm:'300mg Q2W'}];
rows.forEach((row,index)=>factory.factCell(doc,cell,new Node(),row,String(index),'条件'));
const list=cell.children[0];
assert.equal(list.children.filter(n=>n.className==='kz-comparison-identity-header').length,1);
const observations=list.children.filter(n=>n.className.includes('kz-comparison-observation'));
assert.equal(observations.length,5);
assert.deepEqual(observations.map(n=>n.className.includes('--compact')),
 [true,true,false,false,false]);
assert.equal(observations[2].children[0].children[0].children[0].textContent,'产品关联待核');
"""
    _run_node(probe, str(ASSETS / "portal.js"))
