"""Production A matrix/query/chart projection; Node is not physical browser QA."""

import subprocess
from pathlib import Path


def test_a_matrix_filter_paging_linked_groups_and_fact_buttons():
    root = Path(__file__).resolve().parents[2]
    script = root / "src/ci_workflow/renderers/portal/assets/report-a.js"
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const common=fs.readFileSync(process.argv[2],'utf8');
const start=source.indexOf('  function renderAComparison(');
const end=source.indexOf('\n  window.__A_COMPARISON_EVIDENCE__',start);
assert.ok(start>=0&&end>start);
class Node {
 constructor(){this.children=[];this.dataset={};this.attrs={};this.listeners={};}
 appendChild(n){this.children.push(n);return n;} replaceChildren(){this.children=[];}
 setAttribute(k,v){this.attrs[k]=v;} addEventListener(k,f){this.listeners[k]=f;}
 querySelector(k){return lookup[k];} get options(){return this.children;}
}
const lookup={};
['[data-a-comparison-question]','[data-a-comparison-prev]','[data-a-comparison-next]',
 '[data-a-comparison-status]','[data-a-comparison-table]','thead','tbody']
 .forEach(k=>lookup[k]=new Node());
const host=new Node(),summary=new Node();
const rows={a:{a_row_id:'source-a',trial_id:'trial-a',product_id:'drug-a',
 product_zh:'<img onerror=bad()>',value:0,unit:'%',_domain:'efficacy'},
 b:{a_row_id:'source-b',trial_id:'trial-b',product_id:'drug-b',value:50,unit:'%',_domain:'efficacy'},
 c:{a_row_id:'source-c',trial_id:'trial-c',product_id:'drug-c',value:null,_domain:'safety'},
 last:{a_row_id:'source-last',trial_id:'trial-c',product_id:'drug-c',value:2,_domain:'safety'}};
Object.keys(rows).forEach(id=>rows[id].row_id=id);
const columns=Array.from({length:9},(_,i)=>({id:'col-'+i,question_id:'easi',question_known:true,
 question_label:'EASI',title:'条件'+i,
 cells:i===0?{'trial-a':['a'],'trial-b':['b']}:i===1?{'trial-c':['c']}:i===8?{'trial-c':['last']}:{}}));
columns.push({id:'unknown-col',question_id:'aa-unknown',question_known:false,
 question_label:'问题待核',title:'问题待核',cells:{'trial-c':['c']}});
const workspace={membership:{row_ids:Object.keys(rows)},
 study_ids:['trial-empty','trial-a','trial-b','trial-c'],
 study_labels:{'trial-a':'PRIME｜NCT04202679'},columns};
let url='https://example.test/clinical-portfolio.html?view=comparison&cmp_page=1.5',currentGroups=[];
const groups=columns.map(c=>({scientific_group_id:c.id,
 rows:Object.values(c.cells).flat().map(id=>rows[id])}));
const sandbox={aComparisonPage:1,selected:{},
 trials:Object.values(rows).map(r=>({id:r.trial_id,phase:'III',region:'CN'})),
 Object,JSON,String,Number,Math,URLSearchParams,
 productById(id){return {name:id,target:'target'};},
 dimensionMatches(_,actual,wanted){return actual===wanted;},
 window:{__A_COMPARISON_WORKSPACE__:workspace,__A_COMPARISON_ROWS__:rows,__A_COMPARISON_GROUPS__:groups,
 location:{get search(){return new URL(url).search;},pathname:'/clinical-portfolio.html'},
 history:{replaceState(_,__,next){url=new URL(next,url).href;}},
 __CHART_SYNC__:{unplottedValueText(){return '用户清除，待重新核实';},
 replaceGroups(g){currentGroups=g;}}},
 document:{body:{dataset:{}},querySelectorAll(){return [];},getElementById(){return host;},
 querySelector(){return summary;},
 createElement(){return new Node();}}};
const orderStart=common.indexOf('  function createComparisonQuestionOrder(');
const orderEnd=common.indexOf('\n  window.__COMPARISON_QUERY__',orderStart);
if(orderStart>=0){
 vm.runInNewContext(common.slice(orderStart,orderEnd),sandbox);
 sandbox.window.__COMPARISON_QUERY__=sandbox.createComparisonQuestionOrder();
}
vm.runInNewContext(source.slice(start,end),sandbox);
sandbox.renderAComparison();
assert.equal(lookup['[data-a-comparison-question]'].value,'easi');
assert.equal(lookup['[data-a-comparison-question]'].options.length,2);
assert.equal(new URL(url).searchParams.get('cmp_page'),'1');
assert.equal(host.hidden,false);assert.equal(summary.hidden,true);assert.equal(lookup.tbody.children.length,4);
assert.equal(sandbox.document.body.dataset.comparisonView,'comparison');
function text(n){return [n.textContent||'',...n.children.map(text)].join('|');}
assert.match(text(lookup.tbody),/0 %/);assert.match(text(lookup.tbody),/用户清除/);
assert.match(text(lookup.tbody),/PRIME｜NCT04202679/);
assert.ok(text(lookup.tbody).includes('<img onerror=bad()>')); // literal text, no HTML parsing
assert.equal(lookup.tbody.children[0].children[1].children[0]
 .attrs['data-efficacy-row-id'],'source-a');
assert.equal(lookup.tbody.children[0].children[1].children[0]
 .attrs['data-evidence-row-id'],'source-a');
assert.equal(lookup.tbody.children[0].children[1].children[0]
 .attrs['data-evidence-collection'],'efficacy');
const seen=new Set(JSON.parse(host.dataset.columnIds));
lookup['[data-a-comparison-next]'].listeners.click();
JSON.parse(host.dataset.columnIds).forEach(id=>seen.add(id));
lookup['[data-a-comparison-next]'].listeners.click();
JSON.parse(host.dataset.columnIds).forEach(id=>seen.add(id));
assert.equal(seen.size,9);assert.match(text(lookup.tbody),/2/);
assert.equal(new URL(url).searchParams.get('cmp_page'),'3');
lookup['[data-a-comparison-prev]'].listeners.click();lookup['[data-a-comparison-prev]'].listeners.click();
sandbox.selected={product:['drug-b']};sandbox.renderAComparison();
assert.equal(lookup.tbody.children.length,1);
assert.equal(currentGroups.flatMap(g=>g.rows.map(r=>r.a_row_id)).join(','),'source-b');
sandbox.selected={product:['no-match']};sandbox.renderAComparison();
assert.equal(lookup.tbody.children.length,0);assert.equal(currentGroups.length,0);
sandbox.selected={};sandbox.renderAComparison();assert.equal(lookup.tbody.children.length,4);
assert.ok(JSON.parse(host.dataset.queryRowIds).includes('last'));
columns[0].scientific_facet_ids=['frame-a','frame-b'];
columns[0].facet_label_by_row={a:'FAS，48周',b:'PPS，24周'};
sandbox.window.__A_COMPARISON_GROUPS__=[
 {scientific_group_id:'frame-a',rows:[rows.a]},
 {scientific_group_id:'frame-b',rows:[rows.b]}];
sandbox.renderAComparison();
assert.equal(currentGroups.length,2);
assert.match(text(lookup.tbody),/FAS，48周/);assert.match(text(lookup.tbody),/PPS，24周/);
sandbox.selected={product:['drug-b']};sandbox.renderAComparison();
assert.equal(currentGroups.length,1);assert.equal(currentGroups[0].scientific_group_id,'frame-b');
lookup['[data-a-comparison-question]'].value='aa-unknown';
sandbox.selected={};
lookup['[data-a-comparison-question]'].listeners.change();
assert.equal(new URL(url).searchParams.get('cmp'),'aa-unknown'); // unresolved still reachable
const clearedButton=lookup.tbody.children[0].children[1].children[0];
assert.equal(clearedButton.attrs['data-evidence-row-id'],'source-c');
assert.equal(clearedButton.attrs['data-evidence-collection'],'safety');
const callbackStart=source.indexOf('  window.__A_COMPARISON_EVIDENCE__ = ');
const callbackEnd=source.indexOf('\n  function applyFilters(',callbackStart);
let opened;
sandbox.openEvidencePanel=t=>{opened=t;};
vm.runInNewContext(source.slice(callbackStart,callbackEnd),sandbox);
const glyph=new Node();sandbox.window.__A_COMPARISON_EVIDENCE__('a',glyph);
assert.equal(opened,glyph);assert.equal(glyph.attrs['data-evidence-row-id'],'source-a');
assert.equal(glyph.attrs['data-evidence-collection'],'efficacy');
sandbox.window.__A_COMPARISON_EVIDENCE__('c',glyph);
assert.equal(glyph.attrs['data-evidence-row-id'],'source-c');
assert.equal(glyph.attrs['data-evidence-collection'],'safety');
const prior=JSON.stringify(glyph.attrs);sandbox.window.__A_COMPARISON_EVIDENCE__('missing',glyph);
assert.equal(JSON.stringify(glyph.attrs),prior); // unknown row does not open a default source
"""
    result = subprocess.run(["node", "-e", probe, str(script), str(script.parent / "portal.js")],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
