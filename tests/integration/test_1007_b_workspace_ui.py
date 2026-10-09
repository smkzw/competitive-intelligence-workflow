"""Execute the production matrix renderer; not a substitute for Ego pixels."""

import subprocess
from pathlib import Path


def test_production_matrix_keeps_shared_cells_clear_states_and_all_facets() -> None:
    root = Path(__file__).resolve().parents[2]
    script = root / "src/ci_workflow/renderers/portal/assets/report-b.js"
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const common=fs.readFileSync(process.argv[2],'utf8');
const start=source.indexOf('  function renderComparisonWorkspace(');
const end=source.indexOf('\n  function ',start+5);
assert.ok(start>=0&&end>start);
class Node {
 constructor(){this.children=[];this.dataset={};this.listeners={};this.attributes={};this.hidden=false;}
 appendChild(n){this.children.push(n);return n;}
 replaceChildren(){this.children=[];}
 setAttribute(k,v){this.attributes[k]=v;}
 addEventListener(k,fn){this.listeners[k]=fn;}
 querySelector(k){return lookup[k];}
 get options(){return this.children;}
}
const lookup={};
['[data-comparison-column]','[data-comparison-prev]','[data-comparison-next]',
 '[data-comparison-status]','table','thead','tbody'].forEach(k=>lookup[k]=new Node());
const host=new Node();
const rows={a:{trial_id:'trial-a',value:0,unit:'%',product_zh:'<script>bad</script>',arm:'治疗组'},
 b:{trial_id:'trial-b',value:50,unit:'%',arm:'治疗组'},
 c:{trial_id:'trial-c',value:null,disclosure_state:'user_cleared',arm:'治疗组'}};
Object.keys(rows).forEach(id=>rows[id].row_id=id);
const workspace={study_ids:['trial-no-results','trial-a','trial-b','trial-c'],
 study_labels:{'trial-a':'PRIME｜NCT04202679','trial-b':'ARCADIA｜NCT04501666'},
 membership:{row_ids:['a','b','c']},columns:Array.from({length:9},(_,i)=>({
  id:'column-'+i,question_id:'efficacy::easi75',question_known:true,question_label:'EASI75',title:'临床条件'+i,
  cells:{'trial-a':['a'],'trial-b':['b'],'trial-c':['c']}}))};
workspace.columns.push({id:'unknown-column',question_id:'aa-unknown',question_known:false,
 question_label:'问题待核',title:'问题待核',cells:{'trial-c':['c']}});
let state={},url='https://example.test/overview.html?view=comparison',currentGroups=[];
const sandbox={comparisonQuestion:'',comparisonPage:1,resultQuery:'',rowById:rows,searchById:{},
 fullChartGroups:workspace.columns.map(c=>({scientific_group_id:c.id,rows:Object.values(rows)})),
 URL,URLSearchParams,JSON,Object,String,Math,
 window:{__B_COMPARISON_WORKSPACE__:workspace,location:{get search(){return new URL(url).search;},
 get href(){return url;}},history:{replaceState(_,__,next){url=next;}},
 __CHART_SYNC__:{unplottedValueText(){return '用户清除，待重新核实';},
 replaceGroups(g){currentGroups=g;}}},
 document:{body:{dataset:{}},querySelectorAll(){return [];},getElementById(){return host;},
 createElement(){return new Node();}},
 matches(id,current){return !current.trial||rows[id].trial_id===current.trial;},
 selectedState(){return state;}};
const orderStart=common.indexOf('  function createComparisonQuestionOrder(');
const orderEnd=common.indexOf('\n  window.__COMPARISON_QUERY__',orderStart);
if(orderStart>=0){
 vm.runInNewContext(common.slice(orderStart,orderEnd),sandbox);
 sandbox.window.__COMPARISON_QUERY__=sandbox.createComparisonQuestionOrder();
}
vm.runInNewContext(source.slice(start,end),sandbox);
sandbox.renderComparisonWorkspace({});
assert.equal(lookup['[data-comparison-column]'].value,'efficacy::easi75');
assert.equal(lookup['[data-comparison-column]'].options.length,2);
assert.equal(host.hidden,false);assert.equal(lookup.tbody.children.length,4);
assert.equal(sandbox.document.body.dataset.comparisonView,'comparison');
assert.equal(lookup.thead.children[0].children.length,5); // four columns plus study
function text(node){return [node.textContent||'',...node.children.map(text)].join('|');}
function firstFact(n){if(n.attributes['data-evidence-open'])return n;
 for(const child of n.children){const found=firstFact(child);if(found)return found;}}
assert.match(text(lookup.tbody),/0 %/);assert.match(text(lookup.tbody),/用户清除，待重新核实/);
assert.match(text(lookup.tbody),/PRIME｜NCT04202679/);
assert.doesNotMatch(text(lookup.tbody),/None|null/);
assert.ok(text(lookup.tbody).includes('<script>bad</script>')); // literal safe text only
assert.ok(firstFact(lookup.tbody.children[0].children[1]).attributes['data-evidence-open']==='a');
assert.equal(host.dataset.queryScope,'filtered-workspace');
assert.equal(JSON.parse(host.dataset.questionRowIds).length,3);
const seen=new Set(JSON.parse(host.dataset.columnIds));
lookup['[data-comparison-next]'].listeners.click();
JSON.parse(host.dataset.columnIds).forEach(id=>seen.add(id));
lookup['[data-comparison-next]'].listeners.click();
JSON.parse(host.dataset.columnIds).forEach(id=>seen.add(id));
assert.equal(seen.size,9);assert.equal(lookup['[data-comparison-next]'].disabled,true);
assert.equal(new URL(url).searchParams.get('cmp_page'),'3');
state={trial:'trial-b'};sandbox.renderComparisonWorkspace(state);
assert.equal(lookup.tbody.children.length,1);assert.match(text(lookup.tbody),/ARCADIA｜NCT04501666/);
assert.equal(currentGroups.length,1);assert.equal(currentGroups[0].rows[0].row_id,'b');
state={trial:'no-match'};sandbox.renderComparisonWorkspace(state);
assert.equal(lookup.tbody.children.length,0);assert.equal(JSON.parse(host.dataset.queryRowIds).length,0);
state={};sandbox.renderComparisonWorkspace(state);assert.equal(lookup.tbody.children.length,4);
// Matrix question columns may contain multiple incompatible scientific frames.
// They must reach their own linked charts, never turn into one invented frame.
workspace.columns.forEach(c=>{
 c.scientific_facet_ids=[c.id+'-left',c.id+'-right'];
 c.facet_label_by_row={a:'FAS，48周',b:'PPS，24周',c:'用户清除，待重新核实'};
});
sandbox.fullChartGroups=workspace.columns.flatMap(c=>c.scientific_facet_ids.map((id,i)=>({
 scientific_group_id:id,rows:[rows[i===0?'a':'b']]})));
sandbox.renderComparisonWorkspace(state);
assert.equal(currentGroups.length,2);
assert.match(lookup['[data-comparison-status]'].textContent,/2个科学条件分面/);
assert.doesNotMatch(lookup['[data-comparison-status]'].textContent,/本问题条件分面/);
assert.notEqual(currentGroups[0].scientific_group_id,currentGroups[1].scientific_group_id);
assert.match(text(lookup.tbody),/FAS，48周/);
assert.match(text(lookup.tbody),/PPS，24周/);
state={trial:'trial-b'};sandbox.renderComparisonWorkspace(state);
assert.equal(currentGroups.length,1);assert.equal(currentGroups[0].rows[0].row_id,'b');
assert.match(lookup['[data-comparison-status]'].textContent,/1个科学条件分面/);
lookup['[data-comparison-column]'].value='aa-unknown';
lookup['[data-comparison-column]'].listeners.change();
assert.equal(new URL(url).searchParams.get('cmp'),'aa-unknown'); // keep unresolved access
"""
    result = subprocess.run(["node", "-e", probe, str(script), str(script.parent / "portal.js")],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
