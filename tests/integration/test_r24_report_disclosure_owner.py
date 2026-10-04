"""Unplotted is not undisclosed; B must retain the shared current-state label.

These execute real production closures with a minimal DOM, not browser/visual
acceptance. All source/current states and row-level reasons remain unchanged.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ci_workflow.domain.enums import FactDisclosureState

ASSETS = Path(__file__).resolve().parents[2] / 'src/ci_workflow/renderers/portal/assets'
STATES = (
    'reported_value', 'reported_zero', 'user_cleared', 'not_applicable',
    'not_publicly_disclosed', 'not_reported', 'below_reporting_threshold',
    'unresolved_due_to_route', 'conflicting',
)

PROBE = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const mode=process.argv[1], state=process.argv[2];
function node(){return {style:{},children:[],classList:{add(){},remove(){}},
 setAttribute(){},querySelector(){return null},appendChild(n){this.children.push(n)}}}
function content(n){return (n.textContent||'')+n.children.map(content).join(' ')}
const wanted={reported_value:'有公开记录',reported_zero:'有公开记录',
 user_cleared:'用户清除，待重新核实',not_applicable:'不适用',
 not_publicly_disclosed:'该指标结果尚未公开',not_reported:'未报告',
 below_reporting_threshold:'低于报告阈值',unresolved_due_to_route:'路径未解析',
 conflicting:'来源冲突',conflicting_sources:'来源冲突',unknown:'待核实'}[state];
const shared=fs.readFileSync(process.argv[3],'utf8').replace(
 'presentationPlan: presentationPlan,',
 'presentationPlan: presentationPlan, testMountGroup: initGroupChart,');
const bSource=fs.readFileSync(process.argv[4],'utf8').replace(
 '  function applyState(',
 '  window.__R218_APPLY__=applyState;\n  function applyState(');
const pages=mode==='b' ? ['baseline-overview','baseline-demographics',
 'disposition-overview','participant-flow','product-trial-profiles'] : ['safety'];
for(const page of pages){
 const target=node(),row={row_id:'fact1',_chart_type:'bar',renderable:false,
  value:null,numeric_value:null,disclosure_state:state,
  difference_note:'该观察缺少适用的数值口径'};
 const group={rows:[row]};
 if(mode==='shared') group.empty_message='当前未形成可绘制的试验内比较';
 const table={style:{},getAttribute(){return 'fact1'}};
 const sandbox={window:{__B_PAGE_ID__:page,__CHART_GROUPS__:[group],
  echarts:{init(){throw Error('Unplottable must not create axes')}}},
  document:{readyState:'loading',addEventListener(){},createElement:node,
   getElementById(){return null},querySelector(){return null},
   querySelectorAll(selector){
    if(selector==='.kz-chart-undisclosed__title')return [target.children[0].children[0]];
    if(selector==='.kz-chart-table__row[data-row-id]')return [table];
    return [];}}};
 vm.runInNewContext(shared,sandbox);
 sandbox.window.__CHART_SYNC__.testMountGroup(target,0,group);
 if(mode==='b'){
  // Layout synchronization is a separate tested contract; this probe exercises
  // the actual B filter lifecycle and any report-level label mutation.
  sandbox.window.__CHART_SYNC__.syncWithFilter=()=>{};
  vm.runInNewContext(bSource,sandbox);
  sandbox.window.__R218_APPLY__({});
  sandbox.window.__R218_APPLY__({});
 }
 const title=target.children[0].children[0].textContent;
 assert.ok(title.includes(wanted),page+':'+state+' lost current disclosure: '+title);
 if(state!=='not_publicly_disclosed'){
  assert.ok(!title.includes('未公开')&&!title.includes('暂无公开'),title);
 }
 assert.ok(content(target).includes(row.difference_note),'row reason stays accessible');
 assert.ok(content(target).includes('完整记录仍列于下方表格'),'full table stays available');
 if(mode==='shared')assert.ok(content(target).includes(group.empty_message),
  'the comparison explanation must remain alongside, not override, factual disclosure');
 assert.equal(row.disclosure_state,state,'display code must not rewrite science');
}
'''


@pytest.mark.parametrize('state', (*STATES, 'conflicting_sources', 'unknown'))
@pytest.mark.parametrize('mode', ['shared', 'b'])
def test_current_state_survives_unplotted_hint_and_b_filter_lifecycle(
    mode: str, state: str,
) -> None:
    result = subprocess.run(
        ['node', '-e', PROBE, mode, state, str(ASSETS / 'charts.js'),
         str(ASSETS / 'report-b.js')], capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_family_covers_every_current_fact_disclosure_state() -> None:
    assert set(STATES) == {state.value for state in FactDisclosureState}
