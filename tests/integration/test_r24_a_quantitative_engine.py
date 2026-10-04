"""Production option and packaging checks, not browser/visual acceptance."""

import subprocess
from pathlib import Path

from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site

ROOT = Path(__file__).resolve().parents[2]


def test_a_entry_uses_the_shared_engine_before_its_business_renderer(tmp_path: Path) -> None:
    data = ReportAPortalData.model_validate_json(
        (ROOT / "fixtures/synthetic/a-complete/inputs/report-data.json").read_bytes()
    )
    render_report_a_site(data, tmp_path)
    for page in tmp_path.rglob("*.html"):
        text = page.read_text()
        assert text.index('/charts.js"') < text.index('/report-a.js"')
    assert (tmp_path / "assets/charts.js").read_bytes() == (
        ROOT / "src/ci_workflow/renderers/portal/assets/charts.js"
    ).read_bytes()


def test_shared_bar_options_keep_signed_values_exact_ids_and_real_numeric_domain() -> None:
    probe = r"""
const fs=require('node:fs'), vm=require('node:vm'), assert=require('node:assert/strict');
const sandbox={window:{},document:{readyState:'loading',addEventListener(){}}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
const api=sandbox.window.__CHART_SYNC__;
function group(values,kind='adjusted_estimate',unit='分') {
 return {chart_type:'bar',unit,rows:values.map((value,i)=>({row_id:'fact'+i,
 _chart_type:'bar',category:'同组标签',value,numeric_value:value,unit,renderable:true,
 numeric_projection:{kind,plot_value:value,plot_unit:unit}}))};
}
const signed=api.buildBarOption(group([-4,0,2]));
assert.deepEqual(Array.from(signed.series[0].data,d=>d.value),[-4,0,2]);
assert.deepEqual(Array.from(signed.series[0].data,d=>d._row_id),['fact0','fact1','fact2']);
assert.equal(signed.yAxis.min({min:-4,max:2}),-4);
assert.ok(signed.yAxis.max({min:-4,max:2})>=2);
assert.ok(api.buildBarOption(group([0.2,0.4],'adjusted_estimate','%')).yAxis.max({max:0.4})<1);
assert.equal(api.buildBarOption(group([48,50],'participant_proportion','%')).yAxis.max({max:50}),100);
const missing=group([3,0]);missing.rows[1].renderable=false;
assert.deepEqual(Array.from(api.buildBarOption(missing).series[0].data,d=>d._row_id),['fact0']);
assert.equal(api.presentationPlan(group([1])).kind,'single_fact');
const long=group([-4,0,2]);long.orientation='horizontal';
long.rows.forEach(r=>{r.category='完整剂量与组别名称'.repeat(6)});
const horizontal=api.buildBarOption(long);
assert.equal(horizontal.xAxis.type,'value');assert.equal(horizontal.yAxis.type,'category');
assert.equal(horizontal.yAxis.axisLabel.rotate,0);
assert.equal(horizontal.xAxis.min({min:-4,max:2}),-4);
assert.ok(api.presentationPlan(long).target_height>api.presentationPlan(group([-4,0,2])).target_height);
assert.ok(api.presentationPlan(long).target_height<=420);
"""
    result = subprocess.run(
        ["node", "-e", probe, str(ROOT / "src/ci_workflow/renderers/portal/assets/charts.js")],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_a_renderer_uses_fact_event_identity_and_disposes_paged_charts() -> None:
    source = (ROOT / "src/ci_workflow/renderers/portal/assets/report-a.js").read_text()
    body = source.split("function renderEfficacy(host)", 1)[1].split("function color", 1)[0]
    assert "bar.style.width" not in body
    assert "presentationPlan" in body
    assert "ResizeObserver" in source and "disposeEfficacyCharts" in source
    assert "event.data._row_id" in source
    assert "host._observationSignature === signature" in source
    assert "showPage(currentPage)" in source
