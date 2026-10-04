"""Long trial names must not consume the numerical plotting region."""

import subprocess
from pathlib import Path


def test_heatmap_geometry_preserves_plot_area_and_exact_fact_mapping() -> None:
    source = (
        Path(__file__).resolve().parents[2] / "src/ci_workflow/renderers/portal/assets/charts.js"
    )
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const sandbox={window:{},document:{readyState:'loading',addEventListener(){}}};
const text=fs.readFileSync(process.argv[1],'utf8').replace(
 'presentationPlan: presentationPlan,',
 'presentationPlan: presentationPlan, testHeatmap: buildHeatmapOption,'+
 ' testFit: fitHeatmapLabels, testHeading: chartHeadingParts,');
vm.runInNewContext(text,sandbox);
const api=sandbox.window.__CHART_SYNC__;
const long='Pilot Study to Assess Safety, Preliminary Efficacy and Pharmacokinetics '.repeat(4);
const rows=[1,6,0].map((n,i)=>({row_id:'f'+i,event:'drug · '+long,trial_id:'nct02588833',
 product_zh:'drug',arm:'Cohort '+i,disclosure_state:n===0?'reported_zero':'reported_value',
 value_matrix:n,numeric_value:n,value:n,renderable:true,unit:'人',_chart_type:'heatmap'}));
const option=api.testHeatmap({rows,identity_series:true});
assert.equal(option.yAxis.data[0],'drug · NCT02588833');
assert.equal(new Set(option.series[0].data.map(x=>x._row_id)).size,3);
assert.equal(option.series[0].data[2].value[2],0);
for(const width of [628,704,864,1184]){
 let fitted;
 api.testFit({setOption(value){fitted=value;}},{clientWidth:width,
   getAttribute(){return 'heatmap';}});
 assert.equal(fitted.grid.containLabel,false);
 assert.ok(width-fitted.grid.left-fitted.grid.right>=width*.5);
 assert.ok(fitted.yAxis.axisLabel.width>100);
 assert.equal(fitted.yAxis.axisLabel.hideOverlap,false);
 assert.equal(fitted.yAxis.axisLabel.rotate,0);
}
const complete='安全性 · 严重不良事件 · 受累人数（例） · 自首次给药至末次给药后30天 · 多登记臂';
const heading=api.testHeading(complete,true);
assert.equal(heading.title,'安全性 · 严重不良事件 · 受累人数（例）');
assert.equal(heading.context,'自首次给药至末次给药后30天 · 多登记臂');
assert.equal(heading.title+' · '+heading.context,complete);
assert.equal(api.testHeading('Unstructured · source wording',false).title,
 'Unstructured · source wording');
"""
    result = subprocess.run(
        ["node", "-e", probe, str(source)], capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
