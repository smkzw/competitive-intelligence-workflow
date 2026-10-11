"""Primary graph-and-table reading, not a clinical or browser acceptance claim."""

import json
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("case", ["registry_id", "named_registry"])
def test_shared_study_label_formats_registry_id_without_mutating_identity(case):
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8'),which=process.argv[2];
const start=source.indexOf('  function createComparisonQuestionOrder(');
const end=source.indexOf('\n  window.__COMPARISON_QUERY__',start),sandbox={};
vm.runInNewContext(source.slice(start,end),sandbox);
const q=sandbox.createComparisonQuestionOrder();
const row={trial_id:'nct04501666',label:which==='registry_id'?
 'A Study to Assess the Efficacy and Safety of Nemolizumab in Participants With Prurigo Nodularis':
 'PRIME｜nct04501666'};
const before=JSON.stringify(row);
assert.equal(q.studyText(row.trial_id,row.label),
 which==='registry_id'?'NCT04501666':'PRIME｜NCT04501666');
assert.equal(JSON.stringify(row),before);
assert.equal(q.studyText('local-study-1','local-study-1'),'local-study-1');
assert.equal(q.studyText('local-study-2','Nemolizumab'),'Nemolizumab');
"""
    result = subprocess.run(
        ["node", "-e", probe, str(ROOT / "src/ci_workflow/renderers/portal/assets/portal.js"),
         case], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


def test_ordinary_b_render_has_immediate_primary_table_and_folded_auxiliary_tables(tmp_path):
    from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site

    raw = json.loads((ROOT / "fixtures/synthetic/a-complete/inputs/report-data.json").read_text())
    render_report_b_site(ReportBPortalData.model_validate(raw), tmp_path / "B")

    class DetailsInventory(HTMLParser):
        def __init__(self):
            super().__init__()
            self.primary = []
            self.auxiliary = []

        def handle_starttag(self, tag, attrs):
            if tag != "details":
                return
            attrs = dict(attrs)
            classes = attrs.get("class", "").split()
            if "kz-b-comparison-details" in classes:
                self.primary.append("open" in attrs)
            elif "kz-complete-table" in classes:
                self.auxiliary.append("open" in attrs)

    inventory = DetailsInventory()
    inventory.feed((tmp_path / "B/overview.html").read_text())
    assert inventory.primary == [True], "The primary comparison matrix needs no extra click"
    assert not any(inventory.auxiliary), "Source/detail tables remain optional disclosures"
