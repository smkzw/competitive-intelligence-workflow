"""A mixed disclosure panel must not allocate axes for its one drawable fact.

Production planner/mount seam, explicit synthetic observations. Missing, unknown
product relationships and user-cleared rows remain in the query/table universe;
they do not become zero values or choose the single-fact evidence target.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "src/ci_workflow/renderers/portal/assets/charts.js"


@pytest.mark.parametrize("kind", ["bar", "line", "heatmap"])
@pytest.mark.parametrize("unknown_first", [False, True])
@pytest.mark.parametrize("value", [0, 7])
def test_one_drawable_fact_keeps_other_disclosures_without_empty_axes(
    kind: str, unknown_first: bool, value: int,
) -> None:
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const type=process.argv[2],unknownFirst=process.argv[3]==='True',value=Number(process.argv[4]);
let axes=0;
function node(){return {style:{},children:[],attributes:{},listeners:{},
 classList:{add(){},remove(){}},appendChild(n){this.children.push(n);n.parentElement=this},
 setAttribute(k,v){this.attributes[k]=String(v)},getAttribute(k){return this.attributes[k]},
 addEventListener(k,v){this.listeners[k]=v},querySelector(){return null}};}
const sandbox={window:{echarts:{init(){axes++;throw Error('single drawable fact created axes')}}},
 document:{readyState:'loading',addEventListener(){},createElement:node}};
const text=fs.readFileSync(process.argv[1],'utf8').replace(
 'presentationPlan: presentationPlan,',
 'presentationPlan: presentationPlan, testMount: initGroupChart,');
vm.runInNewContext(text,sandbox);
const api=sandbox.window.__CHART_SYNC__;
const known={row_id:'known-zero-or-value',value,numeric_value:value,unit:'人',
 renderable:true,_chart_type:type,disclosure_state:value===0?'reported_zero':'reported_value',
 product_zh:'产品',trial_id:'NCT12345678',category:'组1',display_label_zh:'受累人数'};
const unknown={...known,row_id:'unknown-related-fact',renderable:false,numeric_value:null,
 value:null,raw_numeric_value:9,disclosure_state:'reported_value',
 reason:'组别与产品关系待核；原始数值保留，但不进行产品间共轴比较'};
const rows=unknownFirst?[unknown,known]:[known,unknown];
const group={chart_type:type,rows,title_zh:'受累人数'};
const plan=api.presentationPlan(group);
assert.equal(plan.kind,'single_fact','one drawable fact should not allocate a matrix');
assert.equal(plan.target_height,0);
assert.equal(plan.observation_count,2);
assert.deepEqual(Array.from(plan.observation_ids),rows.map(r=>r.row_id));
assert.deepEqual(Array.from(plan.plotted_ids),[known.row_id]);
assert.equal(plan.unplotted[0].row_id,unknown.row_id);
assert.match(plan.unplotted[0].reason,/组别与产品关系待核/);
const target=node(); api.testMount(target,0,group);
assert.equal(axes,0);
assert.equal(target.style.height,'auto');
assert.equal(target.children[0].textContent,String(value)+' 人');
const button=target.children.find(n=>n.attributes['data-chart-evidence-open']);
assert.equal(button.attributes['data-chart-evidence-open'],known.row_id);
assert.deepEqual(Array.from(api.getChartRowIds()),rows.map(r=>r.row_id));
assert.deepEqual(Array.from(api.getSeriesValues(0)),[value]);
"""
    result = subprocess.run(
        ["node", "-e", probe, str(SOURCE), kind, str(unknown_first), str(value)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
