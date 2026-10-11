"""The actual plotted trajectory/labels, not hidden source prose, own desktop geometry."""

import re
import subprocess
from pathlib import Path

import pytest

ASSETS = Path(__file__).resolve().parents[2] / "src/ci_workflow/renderers/portal/assets"


@pytest.mark.parametrize("case", ["trajectory", "short", "scalar", "parallel"])
def test_shared_plan_follows_actual_series_and_visible_labels(case):
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const sandbox={window:{},document:{readyState:'loading',addEventListener(){}}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
const api=sandbox.window.__CHART_SYNC__,which=process.argv[2];
const title='Full original scientific measurement title and statistical context '.repeat(5);
const rows=Array.from({length:24},(_,index)=>({row_id:'actual-'+index,
 value:index===0?0:index+1,numeric_value:index===0?0:index+1,
 renderable:true,disclosure_state:'reported_value',_chart_type:'line',
 actual_timepoint:index+1,actual_timepoint_unit:'week',unit:'%',
 product_id:'drug',trial_id:'study',group_id:'arm',product_zh:'药物',trial_zh:'研究',
 display_label_zh:title,_chart_identity_key:'drug::study',
 _chart_identity_label:'药物｜研究',_chart_series_key:'treatment',
 _chart_series_label:'治疗组',arm_role:'treatment'}));
let group={title_zh:title,reading_title_zh:'瘙痒应答',identity_series:true,rows};
if(which==='scalar')group={...group,rows:[{...rows[0],_chart_type:'bar'}]};
if(which==='short')group={...group,rows:rows.slice(0,2)};
if(which==='parallel')group={...group,rows:rows.concat(rows.map(row=>({...row,
 row_id:row.row_id+'-parallel'})))};
const before=JSON.stringify(group),plan=api.presentationPlan(group);
assert.equal(JSON.stringify(group),before,'no source identity, value or clinical frame mutation');
assert.equal(plan.observation_count,group.rows.length);
assert.equal(JSON.stringify(plan.observation_ids),JSON.stringify(group.rows.map(row=>row.row_id)));
if(which==='scalar'){
 assert.equal(plan.kind,'single_fact');assert.equal(plan.target_height,0);
 assert.equal(plan.grid_span,4,'hidden original title is not a visible scalar label budget');
}else{
 const option=api.buildLineOption(group),points=option.series.flatMap(s=>s.data)
  .filter(p=>p._row_id);
 assert.equal(plan.series_count,option.series.length,'parallel observations are actual series');
 assert.equal(plan.entity_count,1,'24 visits of one identity are not24 different entities');
 if(which==='short'){
  assert.ok(plan.target_height<220,'two observations retain a small comparison');
 }else if(which==='trajectory'){
  assert.ok(plan.target_height<=320,'simple trajectories do not require a380px plot');
  assert.ok(plan.grid_span<=8,'one24-visit series is not24 separate studies');
 }else{
  assert.equal(plan.grid_span,12,'25 collision-preserved series are a complex comparison');
  assert.ok(plan.target_height>=380,'do not compact away collision-preserved series');
 }
 assert.equal(points.length,group.rows.length,'all real points retained');
 assert.equal(plan.glyph_count,group.rows.length);
 assert.equal(points.find(p=>p._row_id==='actual-0').value[1],0,'real zero retained');
}
"""
    result = subprocess.run(["node", "-e", probe, str(ASSETS / "charts.js"), case],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_query_surfaces_existing_eligible_timecourse_before_scalar_comparisons():
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function createComparisonQuestionOrder(');
const end=source.indexOf('\n  window.__COMPARISON_QUERY__',start);
const sandbox={Object,Array,Set,String};vm.runInNewContext(source.slice(start,end),sandbox);
const api=sandbox.createComparisonQuestionOrder();
const timeline={kind:'line',rows:[{row_id:'week1'},{row_id:'week24'}]};
const counts={kind:'bar',rows:[{row_id:'study1'},{row_id:'study2'}]};
const workspace={longitudinal_groups:[timeline],descriptive_groups:[counts]};
const before=JSON.stringify(workspace),visible={week1:true,week24:true,study1:true,study2:true};
const result=api.plotGroups(workspace,[],[],visible,visible);
assert.equal(result[0].kind,'line','eligible timecourse is the initial visual question answer');
assert.equal(result[1].kind,'bar','other complete observations remain next to it');
assert.equal(result.flatMap(g=>g.rows).length,4);assert.equal(JSON.stringify(workspace),before);
const sparse=api.plotGroups(workspace,[],[],{study1:true,study2:true},visible);
assert.equal(sparse.length,1);
assert.equal(sparse[0].kind,'bar','filtered trajectory not fabricated');
"""
    result = subprocess.run(["node", "-e", probe, str(ASSETS / "portal.js")],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_a_comparison_grid_does_not_distribute_flex_page_height_to_content_rows():
    css = (ASSETS / "report-a.css").read_text()
    rule = re.search(r'\[data-comparison-view="comparison"\] \.kz-a-main\s*\{([^}]+)', css)
    assert rule and "align-content: start" in rule[1]


def test_b_single_plot_does_not_apply_its_footprint_twice_inside_measurement():
    css = (ASSETS / "report-b.css").read_text()
    rule = re.search(
        r'\.kz-b-measurement-observations > \.kz-chart-module__group:only-child\s*\{([^}]+)',
        css,
    )
    assert rule and "grid-column: 1 / -1" in rule[1]
