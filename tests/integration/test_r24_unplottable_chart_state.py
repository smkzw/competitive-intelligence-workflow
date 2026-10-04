"""All production chart kinds obey the same no-empty-axis state boundary."""

import subprocess
from pathlib import Path


def test_production_mount_never_initializes_axes_for_all_unplottable_rows() -> None:
    source = (
        Path(__file__).resolve().parents[2] / "src/ci_workflow/renderers/portal/assets/charts.js"
    )
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function node(){return {style:{},children:[],classList:{add(){},remove(){}},
 setAttribute(){},querySelector(){return null},appendChild(n){this.children.push(n)}}}
let initializations=0;
const sandbox={window:{echarts:{init(){
 initializations++;throw Error('Empty numeric axes initialized')}}},
 document:{readyState:'loading',addEventListener(){},
 createElement:node,getElementById(){return null}}};
// Test entry instrumentation only: execute the unchanged production closure.
const text=fs.readFileSync(process.argv[1],'utf8').replace(
 'presentationPlan: presentationPlan,',
 'presentationPlan: presentationPlan, testMountGroup: initGroupChart,');
vm.runInNewContext(text,sandbox);
function content(n){return (n.textContent||'')+n.children.map(content).join(' ')}
for(const type of ['bar','line','heatmap','forest','bubble']) {
 for(const state of ['user_cleared','reported_value','not_publicly_disclosed']) {
  const target=node();
  sandbox.window.__CHART_SYNC__.testMountGroup(target,0,{rows:[{row_id:'fact1',
   _chart_type:type,renderable:false,value:null,numeric_value:null,disclosure_state:state}]});
  assert.equal(initializations,0,type+':'+state);
  assert.equal(target.style.height,'auto');
  assert.ok(content(target).includes('完整记录仍列于下方表格'));
  if(state==='user_cleared')assert.ok(content(target).includes('用户清除，待重新核实'));
  if(state==='reported_value')assert.ok(content(target).includes('有公开记录'));
 }
}
"""
    result = subprocess.run(
        ["node", "-e", probe, str(source)], capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
