"""Published values stay in actual shared/B table paths even when charts cannot plot."""
import json
import subprocess
from pathlib import Path

import pytest

ASSETS = Path(__file__).resolve().parents[2] / 'src/ci_workflow/renderers/portal/assets'
PROBE = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const mode=process.argv[1],row=JSON.parse(process.argv[2]),want=process.argv[3];
const before=JSON.stringify(row);
function node(){return {children:[],style:{},classList:{add(){},remove(){}},
 setAttribute(){},addEventListener(){},querySelector(){return null},
 appendChild(n){this.children.push(n)}}}
// B's linked page payload is mandatory in production, including for helper probes.
const env={window:{__CHART_GROUPS__:[],__B_PAGE_ID__:'baseline-overview',
 __FILTER_ROWS__:[],__B_COMPARISON_WORKSPACE__:{columns:[],study_ids:[],membership:{row_ids:[]}},
 __EVIDENCE_VIEWS__:[]},
 document:{readyState:'loading',addEventListener(){},querySelectorAll(){return[]},
 createElement:node,getElementById(){return null},querySelector(){return null}}};
let shared=fs.readFileSync(process.argv[4],'utf8').replace(
 'presentationPlan: presentationPlan,',
 'presentationPlan: presentationPlan, testTable:renderTable,');
vm.runInNewContext(shared,env);
let got;
if(mode==='shared'){
 const table=env.window.__CHART_SYNC__.testTable(node(),0,{rows:[row]});
 const tr=table.children[1].children[0];
 got=tr.children[2].textContent;
 assert.ok(tr.children[4].textContent.length,'disclosure/reason still visible');
}else{
 const b=fs.readFileSync(process.argv[5],'utf8').replace(
  '  function rowValueText(', '  window.__R223_VALUE__=rowValueText;\n  function rowValueText(')
 .replace('  function columnValue(',
  '  window.__R223_COLUMN__=columnValue;\n  function columnValue(');
 vm.runInNewContext(b,env);
 // Exercise actual typed-column rendering, not just a stand-alone number helper.
 got=env.window.__R223_COLUMN__(row,'numeric_value');
 assert.equal(env.window.__R223_VALUE__(row),got);
}
assert.equal(got,want,mode+' discarded or leaked the current value: '+got);
assert.equal(JSON.stringify(row),before,'display must not modify source/current');
'''

CASES = [
    ({'numeric_value':55.5}, '55.5'),
    ({'numeric_value':0,'disclosure_state':'reported_zero'}, '0'),
    ({'value':'51/60','numeric_value':None}, '51/60'),
    ({'display_value':'82.3%（调整估计）','numeric_value':82.3}, '82.3%（调整估计）'),
    ({'effect':1.37}, '1.37'),
    ({'value_matrix':[42.8]}, '42.8'),
    ({'raw_numeric_value':12,'group_assignment_state':'unknown'}, '12（组别产品归属待核）'),
    ({'disclosure_state':'user_cleared','numeric_value':None,'raw_numeric_value':55.5,
      'status':'旧来源仍记录55.5'}, '用户清除，待重新核实'),
    ({'disclosure_state':'not_applicable'}, '不适用'),
    ({'disclosure_state':'unresolved_due_to_route','status':'暂无公开记录'}, '路径未解析'),
    ({'disclosure_state':'conflicting','status':'暂无公开记录'}, '来源冲突'),
    ({'disclosure_state':'below_reporting_threshold','raw_numeric_value':0}, '低于报告阈值'),
]


@pytest.mark.parametrize('mode',['shared','b'])
@pytest.mark.parametrize(('fields','expected'),CASES)
def test_unplotted_current_table_retains_source_value_and_state(
    mode: str, fields: dict[str, object], expected: str,
) -> None:
    row = {'row_id':'fact-current','renderable':False,'disclosure_state':'reported_value',
           'difference_note':'口径尚不足以同轴', **fields}
    result = subprocess.run(['node','-e',PROBE,mode,json.dumps(row,ensure_ascii=False),
        expected,str(ASSETS/'charts.js'),str(ASSETS/'report-b.js')],
        capture_output=True,text=True,check=False)
    assert result.returncode==0,result.stderr


@pytest.mark.parametrize('key', [
    '__FILTER_ROWS__', '__CHART_GROUPS__', '__B_COMPARISON_WORKSPACE__',
    '__EVIDENCE_VIEWS__',
])
def test_b_still_rejects_missing_required_page_payload(key: str) -> None:
    probe = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const window={__FILTER_ROWS__:[],__CHART_GROUPS__:[],
 __B_COMPARISON_WORKSPACE__:{columns:[],study_ids:[],membership:{row_ids:[]}},
 __EVIDENCE_VIEWS__:[]};
delete window[process.argv[1]];
assert.throws(()=>vm.runInNewContext(fs.readFileSync(process.argv[2],'utf8'),{window}),
 /B page payload script missing before report-b.js/);
'''
    result = subprocess.run(
        ['node', '-e', probe, key, str(ASSETS / 'report-b.js')],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
