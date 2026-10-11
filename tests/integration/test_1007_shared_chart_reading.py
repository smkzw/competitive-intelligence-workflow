"""A/B shared chart chrome, production functions; browser geometry is separate."""

import re
import subprocess
from pathlib import Path

from tests.integration.test_1007_longitudinal_chart_option import PROBE

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "src/ci_workflow/renderers/portal/assets"


def test_bar_unit_note_uses_existing_chinese_display_projection():
    prefix = PROBE.split("// Unordered actual visits")[0].replace(
        "getOption() { return this.option || {series: []}; },",
        "getModel(){return {getSeriesByIndex(){return {getData(){return "
        "{getItemGraphicEl(){return null;}};}};}};},"
        "getOption() { return this.option || {series: []}; },",
    )
    probe = prefix + r"""
const assert=require('node:assert/strict');
function note(raw,label){
 const rows=[1,2].map(id=>baseRow({row_id:'r'+id,_chart_type:'bar',
  value:id,unit:raw,unit_label_zh:label}));
 // No model geometry needed for this heading/unit consumer test.
 api.replaceGroups([{title_zh:'瘙痒改善',title_complete:true,rows}]);
 const element=documentRef.querySelector('.kz-chart-group__unit');
 return element&&element.textContent;
}
assert.equal(note('percentage of participants','受试者百分比'),null,
 'short supplied Chinese label already appears on graph; no English unit repeat');
assert.equal(note('a genuinely unresolved original long source unit',''),
 '单位：a genuinely unresolved original long source unit','unknown unit not translated by guess');
"""
    result = subprocess.run(["node", "-e", probe, str(ASSETS / "charts.js")],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_graphical_source_hit_style_belongs_to_common_assets_not_b_only():
    common = (ASSETS / "portal.css").read_text()
    report_b = (ASSETS / "report-b.css").read_text()
    hit = re.search(r"\.kz-chart-evidence-hit\s*\{([^}]+)\}", common)
    assert hit, "A/B/C shared hit target must not become empty browser-default buttons"
    assert "position: absolute" in hit[1] and "background: transparent" in hit[1]
    chart = re.search(r"\.kz-chart-group__chart\s*\{([^}]+)\}", common)
    assert chart and "position: relative" in chart[1]
    assert not re.search(r"\.kz-chart-evidence-hit\s*\{", report_b), "one style owner"


def test_posted_visit_order_reaches_actual_chart_categories():
    prefix = PROBE.split("// Unordered actual visits")[0].replace(
        "getOption() { return this.option || {series: []}; },",
        "getModel(){return {getSeriesByIndex(){return {getData(){return "
        "{getItemGraphicEl(){return null;}};}};}};},"
        "getOption() { return this.option || {series: []}; },",
    )
    probe = prefix + r"""
const assert=require('node:assert/strict');
const rows=[4,16].map(week=>baseRow({row_id:'r'+week,_chart_type:'bar',value:week,
 product_id:'drug',trial_id:'study',group_id:'OG1',
 _chart_identity_label:'产品｜研究',_chart_comparison_context_key:'r'+week,
 _chart_comparison_context_label:'基线、第'+week+'周'}));
const group={title_zh:'瘙痒改善',title_complete:true,identity_series:true,
 comparison_purpose:'clinical_question_descriptive',rows};
api.replaceGroups([group]);
const chart=liveChart();
assert.equal(JSON.stringify(chart.getOption().series.flatMap(s=>s.data).filter(p=>p._row_id)
 .map(p=>p._row_id)),JSON.stringify(['r4','r16']),
 'explicit posted visit order is not lexical label order');
"""
    result = subprocess.run(["node", "-e", probe, str(ASSETS / "charts.js")],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
