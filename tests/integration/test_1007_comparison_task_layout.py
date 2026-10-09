"""Run shared production task layout/disclosure code; pixels require Ego QA."""

import subprocess
from pathlib import Path


def test_comparison_fact_has_value_hierarchy_and_reachable_original_context() -> None:
    script = (Path(__file__).resolve().parents[2]
              / "src/ci_workflow/renderers/portal/assets/portal.js")
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function createComparisonQuestionOrder(');
const end=source.indexOf('\n  window.__COMPARISON_QUERY__',start);
class Node{constructor(){this.children=[];this.attrs={};}
 appendChild(x){this.children.push(x);return x;}setAttribute(k,v){this.attrs[k]=v;}}
const doc={createElement(){return new Node();}},sandbox={};
vm.runInNewContext(source.slice(start,end),sandbox);
const query=sandbox.createComparisonQuestionOrder(),button=new Node(),cell=new Node();
const row={row_id:'a',product_zh:'<script>literal</script>',arm:'治疗组',value:0,
 time:'Week24',difference_note:'分母不同，不共轴'};
const frozen=JSON.stringify(row);
query.factCell(doc,cell,button,row,'0 %','FAS，24周');
assert.equal(cell.children[0],button);assert.equal(button.className,'kz-comparison-fact');
assert.equal(button.children[0].children[1].textContent,'0 %');
assert.equal(button.children[0].children[0].textContent,'<script>literal</script>｜治疗组');
assert.equal(button.children[1].textContent,'Week24');
const details=cell.children[1];assert.equal(details.children[0].textContent,'条件与限制');
assert.equal(details.children[1].textContent,'分母不同，不共轴');
assert.equal(details.children[2].textContent,'FAS，24周');
assert.equal(JSON.stringify(row),frozen);
const clear=new Node(),clearCell=new Node();
query.factCell(doc,clearCell,clear,{product_zh:'drug',arm:'drug',value:null},
 '用户清除，待重新核实','');
assert.equal(clear.children[0].children[0].textContent,'drug');
assert.equal(clear.children[0].children[1].textContent,'用户清除，待重新核实');
assert.equal(clearCell.children.length,1); // no empty disclosure or fake missing fields
"""
    result = subprocess.run(["node", "-e", probe, str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_matching_studies_are_visible_first_without_dropping_or_ranking_studies() -> None:
    script = (Path(__file__).resolve().parents[2]
              / "src/ci_workflow/renderers/portal/assets/portal.js")
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function createComparisonQuestionOrder(');
const end=source.indexOf('\n  window.__COMPARISON_QUERY__',start);
const sandbox={};vm.runInNewContext(source.slice(start,end),sandbox);
const query=sandbox.createComparisonQuestionOrder(),studies=['empty','zero','clear','unknown'];
const columns=[{cells:{zero:['a'],clear:['b'],unknown:['c']}}],allowed={a:true,b:true};
const before=JSON.stringify({studies,columns,allowed});
assert.equal(JSON.stringify(query.studyIds(studies,columns,allowed)),
 JSON.stringify(['zero','clear','empty','unknown'])); // no ranking of 0 versus cleared
assert.equal(JSON.stringify(query.studyIds(studies,columns,{c:true})),
 JSON.stringify(['unknown','empty','zero','clear']));
assert.equal(JSON.stringify(query.studyIds(studies,columns,{})),JSON.stringify(studies));
assert.equal(JSON.stringify(query.studyIds(studies,[],allowed)),JSON.stringify(studies));
assert.equal(JSON.stringify({studies,columns,allowed}),before);
"""
    result = subprocess.run(["node", "-e", probe, str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_comparison_preserves_facts_and_user_disclosures_across_filter_renders() -> None:
    script = (Path(__file__).resolve().parents[2]
              / "src/ci_workflow/renderers/portal/assets/portal.js")
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function createComparisonQuestionOrder(');
const end=source.indexOf('\n  window.__COMPARISON_QUERY__',start);
const sandbox={};vm.runInNewContext(source.slice(start,end),sandbox);
const query=sandbox.createComparisonQuestionOrder();
const header={hidden:false},filters={open:true,dataset:{}},notes={open:false,dataset:{}};
const doc={body:{dataset:{}},querySelectorAll(selector){
 return selector==='[data-comparison-summary-head]'?[header]:[filters,notes];
}};
query.applyLayout(doc,true);
assert.equal(doc.body.dataset.comparisonView,'comparison');
assert.equal(header.hidden,true);assert.equal(filters.open,false);assert.equal(notes.open,false);
filters.open=true; // native keyboard/pointer opening is a user's choice
query.applyLayout(doc,true);assert.equal(filters.open,true); // filter rerender must not close it
query.applyLayout(doc,false);
assert.equal(header.hidden,false);assert.equal(filters.open,true);assert.equal(notes.open,false);
filters.open=false;query.applyLayout(doc,true);query.applyLayout(doc,false);
assert.equal(filters.open,false); // restore actual pre-entry summary state, not hardcoded open
"""
    result = subprocess.run(["node", "-e", probe, str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_primary_comparison_matrix_is_not_folded_but_auxiliary_tables_still_are() -> None:
    script = (Path(__file__).resolve().parents[2]
              / "src/ci_workflow/renderers/portal/assets/portal.js")
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function collapseCompleteTables(');
const end=source.indexOf('\n  window.__COLLAPSE_COMPLETE_TABLES__',start);
class Node {
 constructor(primary=false,folded=false){this.attrs={};this.children=[];this.primary=primary;
  this.folded=folded;this.parentNode={insertBefore:(node)=>{this.wrapper=node;}};}
 getAttribute(key){return this.attrs[key];}
 hasAttribute(key){return key==='data-primary-comparison-table'&&this.primary;}
 setAttribute(key,value){this.attrs[key]=value;}
 closest(){return this.folded?{}:null;}
 appendChild(node){this.children.push(node);}
}
const primary=new Node(true),auxiliary=new Node(),alreadyFolded=new Node(false,true);
const doc={querySelectorAll(){return [primary,auxiliary,alreadyFolded];},
 createElement(){return new Node();}};
const sandbox={document:doc};vm.runInNewContext(source.slice(start,end),sandbox);
sandbox.collapseCompleteTables(doc);
assert.equal(primary.wrapper,undefined,'primary comparison must be visible without extra click');
assert.equal(primary.attrs['data-kz-complete-table'],undefined);
assert.equal(auxiliary.wrapper.children[0].textContent,'展开完整数据表');
assert.equal(auxiliary.wrapper.children[1],auxiliary);
assert.equal(alreadyFolded.wrapper,undefined);
sandbox.collapseCompleteTables(doc);assert.equal(auxiliary.wrapper.children.length,2);
"""
    result = subprocess.run(["node", "-e", probe, str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
