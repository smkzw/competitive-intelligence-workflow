"""Use actual visible chart categories, not hidden registry titles, for geometry."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ci_workflow.renderers.portal.report_b import _group_title

ROOT = Path(__file__).resolve().parents[2]
CHARTS = ROOT / "src/ci_workflow/renderers/portal/assets/charts.js"
REAL = ROOT / ".artifacts/1007-baseline-planner-source-v1.json"


def _probe(groups: list[dict]) -> None:
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const sandbox={window:{},document:{readyState:'loading',addEventListener(){}}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
const api=sandbox.window.__CHART_SYNC__;
const groups=JSON.parse(process.argv[2]);
for(const group of groups){
 const input=JSON.stringify(group),plan=api.presentationPlan(group);
 const option=api.buildBarOption(group);
 assert.equal(plan.grid_span,6,'four visible study categories do not need a whole desktop row');
 assert.ok(plan.target_height<=284,'small grouped comparison must fit a compact height');
 assert.equal(plan.observation_count,12);assert.equal(plan.entity_count,4);
 const expectedSeries=new Set(group.rows.map(r=>r.arm_role==='unknown'
  ?r._chart_series_key+'\u0001'+r._chart_series_label:r._chart_series_key)).size;
 assert.equal(plan.series_count,expectedSeries);assert.equal(plan.glyph_count,12);
 assert.equal(option.xAxis.data.length,4);
 for(const series of option.series)for(const point of series.data){
  if(point._row_id && point.value!==null){
   const row=group.rows.find(r=>r.row_id===point._row_id);
   assert.equal(series.name,row._chart_series_label,
    'one study group must not inherit another drug label');
  }
 }
 assert.equal(plan.observation_ids.length,12);assert.equal(plan.plotted_ids.length,12);
 assert.equal(JSON.stringify(group),input,'layout must not change clinical facts or grouping');
 const sparse={...group,rows:group.rows.slice(0,2)};
 assert.ok(api.presentationPlan(sparse).grid_span<=6);
 assert.ok(api.presentationPlan(sparse).target_height<220);
 const unknown={...group,rows:group.rows.map(r=>({...r,_chart_comparison_context_key:''}))};
 const separate=api.presentationPlan(unknown);
 assert.equal(separate.entity_count,12,'unknown relationships cannot collapse to four categories');
 assert.equal(separate.grid_span,12);assert.equal(separate.observation_ids.length,12);
 assert.equal(api.buildBarOption(unknown).xAxis.data.length,12);
 const long={...group,rows:group.rows.map(r=>({...r,
  _chart_identity_key:r._chart_identity_key.replace('nct','study'),
  _chart_identity_label:'actual visible long clinical category '.repeat(5)}))};
 assert.equal(api.presentationPlan(long).grid_span,12,'actual long axis labels need room');
}
"""
    result = subprocess.run(
        ["node", "-e", script, str(CHARTS), json.dumps(groups)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_shared_plan_measures_resolved_visible_categories_with_source_ids_intact() -> None:
    group = {"chart_type": "bar", "cross_trial": True, "title_zh": "年龄 · 均值"}
    group["rows"] = [
        {
            "row_id": f"source-{study}-{arm}", "value": 40 + study + arm,
            "numeric_value": 40 + study + arm, "renderable": True,
            "_chart_type": "bar", "_chart_identity_key": f"::nct0000000{study}",
            "_chart_identity_label": "完整登记试验长名" * 25,
            "_chart_series_key": f"BG{arm}", "_chart_series_label": f"来源组 {arm}",
            "_chart_comparison_context_key": "baseline-mean-exact-context",
            "_chart_comparison_context_label": "基线",
            "display_label_zh": "年龄 · 均值", "trial_zh": "完整登记长标题" * 25,
            "unit": "years",
        }
        for study in range(4) for arm in range(3)
    ]
    _probe([group])


@pytest.mark.skipif(not REAL.is_file(), reason="bound normal preview chart payload absent")
def test_all_four_real_baseline_groups_use_same_planner_without_source_changes() -> None:
    groups = json.loads(REAL.read_bytes())
    assert len(groups) == 4 and sum(len(g["rows"]) for g in groups) == 48
    _probe(groups)


@pytest.mark.parametrize("separator", ["｜", " · "])
def test_explicit_dispersion_suffix_is_not_repeated_in_baseline_heading(separator: str) -> None:
    row = {
        "clinical_concept_label_zh": f"年龄（连续变量）{separator}标准差",
        "statistical_form_family_label_zh": "标准差",
    }
    assert _group_title(row, domain="baseline").count("标准差") == 1
    assert row["clinical_concept_label_zh"].endswith("标准差")


def test_statistic_is_preserved_when_it_is_not_an_exact_existing_suffix() -> None:
    row = {
        "clinical_concept_label_zh": "不同标准差定义的人群年龄",
        "statistical_form_family_label_zh": "标准差",
    }
    assert _group_title(row, domain="baseline").endswith(" · 标准差")
