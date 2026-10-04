"""The clinical trial identifier remains searchable after result pagination."""

import subprocess
from pathlib import Path


def test_production_b_search_indexes_registry_id_not_only_trial_title() -> None:
    source = (
        Path(__file__).resolve().parents[2] / "src/ci_workflow/renderers/portal/assets/report-b.js"
    )
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const sandbox={window:{__B_PAGE_ID__:'safety',__CHART_GROUPS__:[{rows:[{
 row_id:'source-fact-1',trial_id:'nct02588833',trial_zh:'Pilot Study',product_zh:'pegcetacoplan',
 original_endpoint:'Number of Subjects With TEAEs',display_label_zh:'严重不良事件',
 arm:'Cohort 1',value:1,numeric_value:1,renderable:true}]}]},
 document:{readyState:'loading',addEventListener(){}}};
const text=fs.readFileSync(process.argv[1],'utf8').replace('normalizeBChartGroups();',
 'normalizeBChartGroups(); window.__TEST_SEARCH__=searchById;');
vm.runInNewContext(text,sandbox);
const index=sandbox.window.__TEST_SEARCH__['source-fact-1'];
for(const token of ['NCT02588833','Pilot Study','source-fact-1','pegcetacoplan','严重不良事件'])
 assert.ok(index.includes(token.toLowerCase()),'Missing searchable token: '+token);
"""
    result = subprocess.run(
        ["node", "-e", probe, str(source)], capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
