"""Normal shared plot consumers use question labels without changing source facts."""

import subprocess
from pathlib import Path

import pytest

from tests.integration.test_1007_longitudinal_chart_option import PROBE

ASSETS = Path(__file__).resolve().parents[2] / "src/ci_workflow/renderers/portal/assets"


def test_shared_query_projects_only_display_labels_into_a_chart_rows():
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function createComparisonQuestionOrder(');
const end=source.indexOf('\n  window.__COMPARISON_QUERY__',start);
const sandbox={Object,Array,Set,String};
vm.runInNewContext(source.slice(start,end),sandbox);
const api=sandbox.createComparisonQuestionOrder();
const row={row_id:'actual',value:0.67,unit:'probability of participants'};
const group={scientific_group_id:'frame',title_zh:'Original full title',rows:[row]};
const before=JSON.stringify(group);
const display={actual:{...row,unit_label_zh:'受试者概率',time_label_zh:'第24周'}};
const selected=[{id:'frame',question_known:true,question_label:'瘙痒NRS改善至少4分',
 row_ids:['actual'],cells:{study:['actual']}}];
const result=api.plotGroups({},[group],selected,{actual:true},{actual:true},display);
assert.equal(result[0].reading_title_zh,'瘙痒NRS改善至少4分');
assert.equal(result[0].rows[0].unit_label_zh,'受试者概率');
assert.equal(result[0].rows[0].time_label_zh,'第24周');
assert.equal(result[0].rows[0].unit,row.unit);
assert.equal(result[0].rows[0].value,0.67);
assert.equal(result[0].scientific_group_id,'frame');
assert.equal(JSON.stringify(group),before,'no scientific/source group mutation');
assert.equal(api.plotGroups({},[group],selected,{},{}).length,0);
"""
    result = subprocess.run(["node", "-e", probe, str(ASSETS / "portal.js")],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("case", ["main_heading", "original_detail", "scalar_unit"])
def test_common_chart_uses_question_heading_and_keeps_full_original_in_detail(case):
    prefix = PROBE.split("// Unordered actual visits")[0]
    probe = prefix + r"""
const assert=require('node:assert/strict'),which=process.argv[2];
const ORIGINAL='Probability of Participants With an Improvement (Reduction) in WI-NRS '+
 'by >=4 From Baseline at Week 24 · 报告未注明统计口径 · 基线、第24周';
const question='最重瘙痒NRS较基线改善至少4分';
const row=baseRow({row_id:'probability',value:0.67,unit:'probability of participants',
 unit_label_zh:'受试者概率',display_label_zh:ORIGINAL});
const group={title_zh:ORIGINAL,title_complete:true,reading_title_zh:question,rows:[row]};
const before=JSON.stringify(group);
api.replaceGroups([group]);
if(which==='main_heading'){
 assert.equal(documentRef.querySelector('.kz-chart-group__title').textContent,question);
 assert.equal(documentRef.querySelector('.kz-chart-group__context'),null,
  'complete English/statistical context is not a second headline');
}else if(which==='original_detail'){
 const details=documentRef.querySelector('.kz-complete-table');
 const original=details.querySelector('.kz-chart-source-context');
 assert.ok(original,'full original title belongs to reachable native table disclosure');
 assert.equal(original.textContent,ORIGINAL);
 assert.ok(documentRef.querySelector('.kz-chart-table'),'source rows remain reachable');
}else{
 assert.equal(documentRef.querySelector('.kz-chart-single-fact__value').textContent,
  '0.67 受试者概率');
}
assert.equal(JSON.stringify(group),before,'presentation does not change original units/values');
"""
    result = subprocess.run(["node", "-e", probe, str(ASSETS / "charts.js"), case],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
