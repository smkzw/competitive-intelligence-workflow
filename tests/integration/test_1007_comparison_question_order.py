"""Shared default task navigation; no scientific ranking or browser acceptance."""
import subprocess
from pathlib import Path

from tests.integration.test_1007_real_source_question_projection import CANDIDATE, _read


def test_shared_question_order_prefers_known_multistudy_and_preserves_all_ids() -> None:
    path = Path(__file__).resolve().parents[2] / "src/ci_workflow/renderers/portal/assets/portal.js"
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function createComparisonQuestionOrder(');
const end=source.indexOf('\n  window.__COMPARISON_QUERY__',start);
assert.ok(start>=0&&end>start,'missing single shared question ordering owner');
const sandbox={window:{},Object,Array,Set,String};
vm.runInNewContext(source.slice(start,end),sandbox);
const order=sandbox.createComparisonQuestionOrder();
const columns=[
 {question_id:'aa-unknown',question_known:false,cells:{s1:['a'],s2:['b'],s3:['c']}},
 {question_id:'a-known-single',question_known:true,cells:{s1:['a']}},
 {question_id:'z-known-cross-study',question_known:true,cells:{s1:['a'],s2:['b']}},
 {question_id:'b-known-empty',question_known:true,cells:{s1:[],s2:[]}},
 {question_id:'a-unknown-identity',question_known:true,
  cells:{'study-identity-unresolved':['c'],s1:['a']}},
 {question_id:'zz-legacy-no-known-claim',cells:{s1:['a'],s2:['b']}},
 {question_id:'mixed-known-state',question_known:true,cells:{s1:['a'],s2:['b']}},
 {question_id:'mixed-known-state',question_known:false,cells:{s1:['c']}},
];
const bytes=JSON.stringify(columns),expected=[
 'z-known-cross-study','a-known-single','a-unknown-identity','b-known-empty',
 'aa-unknown','mixed-known-state','zz-legacy-no-known-claim'];
assert.equal(JSON.stringify(order.questionIds(columns)),JSON.stringify(expected));
assert.equal(JSON.stringify(order.questionIds(columns.slice().reverse())),JSON.stringify(expected));
assert.equal(JSON.stringify(columns),bytes); // do not rewrite science, row sets or cells
assert.equal(new Set(order.questionIds(columns)).size,7); // no top-N truncation
assert.equal(order.questionIds([]).length,0);
"""
    result = subprocess.run(["node", "-e", probe, str(path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_real_ordinary_portals_default_to_known_multistudy_without_changing_payloads() -> None:
    _read()  # Verify the original source bindings; do not rewrite old portals.
    path = Path(__file__).resolve().parents[2] / "src/ci_workflow/renderers/portal/assets/portal.js"
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8'),root=process.argv[2];
const start=source.indexOf('  function createComparisonQuestionOrder(');
const end=source.indexOf('\n  window.__COMPARISON_QUERY__',start);
assert.ok(start>=0&&end>start);
const sandbox={};vm.runInNewContext(source.slice(start,end),sandbox);
const order=sandbox.createComparisonQuestionOrder();
function assignment(text,name){
 const begin=text.indexOf('window.'+name+' = ');assert.ok(begin>=0);
 const s={window:{}};vm.runInNewContext(text.slice(begin,text.indexOf(';\n',begin)+1),s);
 return s.window[name];
}
const a=assignment(fs.readFileSync(root+'/A/clinical-portfolio.html','utf8'),
 '__A_COMPARISON_WORKSPACE__');
const overview=fs.readFileSync(root+'/B/overview.html','utf8');
const paths=Array.from(overview.matchAll(/<script src="(data\/shared-payloads\/[^"]+)"/g),
 m=>m[1]);
const text=paths.map(p=>fs.readFileSync(root+'/B/'+p,'utf8')).find(t=>
 t.startsWith('window.__B_COMPARISON_WORKSPACE__ = '));assert.ok(text);
const b=assignment(text,'__B_COMPARISON_WORKSPACE__');
for(const workspace of [a,b]){
 const before=JSON.stringify(workspace),keys=order.questionIds(workspace.columns);
 assert.equal(keys.length,new Set(workspace.columns.map(c=>c.question_id)).size);
 const chosen=workspace.columns.filter(c=>c.question_id===keys[0]);
 assert.ok(chosen.length&&chosen.every(c=>c.question_known===true));
 const studies=new Set(chosen.flatMap(c=>Object.keys(c.cells).filter(s=>
  s!=='study-identity-unresolved'&&c.cells[s].length)));
 assert.ok(studies.size>=2,'ordinary default must contain actual multiple studies');
 assert.ok(keys.includes('efficacy::q-pruritus-nrs-ge4-improvement'));
 assert.ok(workspace.columns.some(c=>c.question_known===false));
 assert.equal(JSON.stringify(workspace),before);
}
"""
    result = subprocess.run(
        ["node", "-e", probe, str(path), str(CANDIDATE)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
