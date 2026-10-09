"""Verified registry denominator scope stays source-qualified in shared A/B views.

The scope label is derived only from the locked fact ``result_context``
denominator candidates plus the exact source paths: a visit label, a class title
or a guessed ITT meaning never creates an N. Missing, duplicated or conflicting
candidates stay 分母范围待核. The compact disclosure lives inside the paired
fact/disclosure details; a user-cleared current value is never restored from the
source in the fact header.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.b_efficacy_source_views import (
    denominator_scope_disclosure,
    project_b_efficacy_source_views,
)
from ci_workflow.application.portal_consumer_registry import register_a_source_consumers
from ci_workflow.application.source_research_service import ResearchResultContext
from ci_workflow.renderers.portal import report_a, report_b
from ci_workflow.renderers.portal.report_b import ReportBPortalData
from tests.integration.test_1007_b_efficacy_source_views import _fixed_fixture
from tests.integration.test_w04_source_consumer_registry import AT, _candidate

REPO = Path(__file__).resolve().parents[2]
PORTAL_JS = REPO / "src/ci_workflow/renderers/portal/assets/portal.js"

SCOPE_MEASURE = "测量级分析人数"
SCOPE_CLASS = "该访视或类别分析人数"
SCOPE_CATEGORY = "该子类别分析人数"
SCOPE_UNRESOLVED = "分母范围待核"
SCOPE_LABELS = frozenset({SCOPE_MEASURE, SCOPE_CLASS, SCOPE_CATEGORY, SCOPE_UNRESOLVED})
METADATA_KEYS = (
    "source_denominator_scope_zh",
    "source_denominator_value",
    "source_denominator_path",
)

MEASURE = "resultsSection.outcomeMeasuresModule.outcomeMeasures[13]"
ROW_VALUE_PATH = (
    "$.resultsSection.outcomeMeasuresModule.outcomeMeasures[13]"
    ".classes[16].categories[0].measurements[0].value"
)


def _candidate_dict(
    *, group_id: str = "OG1", value: int = 77,
    value_path: str = f"{MEASURE}.classes[16].denoms[0].counts[0].value",
) -> dict[str, Any]:
    return {
        "group_id": group_id, "raw_value": str(value), "raw_value_type": "str",
        "parsed_value": value, "unit": "Participants", "value_path": value_path,
    }


def _observation(
    candidates: tuple[dict[str, Any], ...], *,
    group_id: str = "OG1",
    measure: str | None = MEASURE,
    class_title: str | None = "Week 8",
    category_title: str | None = "Any",
) -> ResearchResultContext:
    return ResearchResultContext.model_validate({
        "result_key": "clinicaltrials-result_scope-unit",
        "category": "outcome", "trial_id": "NCT04202679",
        "group_id": group_id, "group_title": "Dupilumab 300 mg Q2W",
        "arm": "Dupilumab 300 mg Q2W", "term": "WI-NRS percent change",
        "endpoint": "WI-NRS percent change", "timepoint": "Week 8",
        "value_role": "reported_measure", "source_unit": "percentage of participants",
        "domain": "efficacy", "metric": "reported_percentage",
        "source_measure_path": measure,
        "denominator_candidates": candidates,
        "class_title": class_title, "category_title": category_title,
    })


def test_scope_labels_follow_exact_candidate_paths_and_never_guess_a_visit_or_itt() -> None:
    measure = _observation((_candidate_dict(
        value=78,
        value_path=f"{MEASURE}.denoms[0].counts[0].value",
    ),))
    assert denominator_scope_disclosure(measure, ROW_VALUE_PATH) == (
        SCOPE_MEASURE, 78, f"$.{MEASURE}.denoms[0].counts[0].value",
    )

    class_scoped = _observation((_candidate_dict(),))
    assert denominator_scope_disclosure(class_scoped, ROW_VALUE_PATH) == (
        SCOPE_CLASS, 77,
        f"$.{MEASURE}.classes[16].denoms[0].counts[0].value",
    )

    category_path = f"{MEASURE}.classes[16].categories[0]"
    category_scoped = _observation((_candidate_dict(
        value=8, value_path=f"{category_path}.denoms[0].counts[0].value",
    ),))
    assert denominator_scope_disclosure(
        category_scoped, f"$.{category_path}.measurements[0].value",
    ) == (SCOPE_CATEGORY, 8, f"$.{category_path}.denoms[0].counts[0].value")

    # A visit/class/category title is presentation context, never a scope proof.
    for label, _n, _path in (
        denominator_scope_disclosure(measure, ROW_VALUE_PATH),
        denominator_scope_disclosure(class_scoped, ROW_VALUE_PATH),
    ):
        assert label in SCOPE_LABELS and "ITT" not in label


def test_missing_duplicate_conflicting_or_foreign_candidates_never_invent_n() -> None:
    # No verified candidate: the visit label alone cannot supply an N.
    assert denominator_scope_disclosure(_observation(()), ROW_VALUE_PATH) == (
        SCOPE_UNRESOLVED, None, None,
    )
    # Conflicting values for the fact's own group.
    assert denominator_scope_disclosure(_observation((
        _candidate_dict(value=77),
        _candidate_dict(value=76),
    )), ROW_VALUE_PATH) == (SCOPE_UNRESOLVED, None, None)
    # Duplicate evidence with different paths is an ambiguous scope, not a new N.
    assert denominator_scope_disclosure(_observation((
        _candidate_dict(value=77),
        _candidate_dict(value=77, value_path=f"{MEASURE}.denoms[0].counts[1].value"),
    )), ROW_VALUE_PATH) == (SCOPE_UNRESOLVED, None, None)
    # Another group's N must never be borrowed.
    assert denominator_scope_disclosure(
        _observation((_candidate_dict(group_id="OG2"),)), ROW_VALUE_PATH,
    ) == (SCOPE_UNRESOLVED, None, None)
    # A candidate that does not cover this fact's exact value path stays unresolved.
    assert denominator_scope_disclosure(_observation((_candidate_dict(
        value_path=(
            "resultsSection.outcomeMeasuresModule.outcomeMeasures[11]"
            ".classes[0].denoms[0].counts[0].value"
        ),
    ),)), ROW_VALUE_PATH) == (SCOPE_UNRESOLVED, None, None)
    # Missing measure/row paths cannot prove any scope.
    assert denominator_scope_disclosure(_observation((_candidate_dict(),), measure=None),
                                        ROW_VALUE_PATH) == (SCOPE_UNRESOLVED, None, None)
    assert denominator_scope_disclosure(_observation((_candidate_dict(),)), None) == (
        SCOPE_UNRESOLVED, None, None,
    )


def test_deterministic_view_retains_source_n_scope_and_path_without_new_science(
    tmp_path: Path,
) -> None:
    root, snapshot, a_report, version_id = _candidate(tmp_path)
    row_id = next(row.row_id for row in a_report.efficacy if row.source_version_id)
    selected = {f"efficacy:{row_id}": version_id}
    register_a_source_consumers(root, snapshot, a_report, selected, registered_at=AT)

    view = project_b_efficacy_source_views(root, snapshot, a_report, selected)[0]
    row = next(item for item in a_report.efficacy if item.row_id == row_id)

    assert view["source_denominator_scope_zh"] == SCOPE_MEASURE
    assert view["source_denominator_value"] == view["denominator"] == row.denominator == 35
    assert view["source_denominator_path"] == (
        "$.resultsSection.outcomeMeasuresModule.outcomeMeasures[0]"
        ".denoms[0].counts[0].value"
    )
    # The verified source values and their existing locator are unchanged.
    assert (view["value"], view["numerator"], view["denominator"]) == (30.0, 30, 35)
    assert view["source_text"] == "30"
    assert view["source_locator"]["field_path"] == row.source_field_path


def test_shared_a_b_rows_disclose_scope_only_on_verified_source_views(
    tmp_path: Path,
) -> None:
    root, snapshot, a_report, version_id = _candidate(tmp_path)
    row_id = next(row.row_id for row in a_report.efficacy if row.source_version_id)
    selected = {f"efficacy:{row_id}": version_id}
    register_a_source_consumers(root, snapshot, a_report, selected, registered_at=AT)
    views = project_b_efficacy_source_views(root, snapshot, a_report, selected)

    b_report = ReportBPortalData.model_validate({
        **a_report.model_dump(mode="json"),
        "efficacy_views": {"coverage_mode": "partial", "facts": views},
    })
    records = report_b._efficacy_records(
        b_report,
        {product.id: product.name for product in b_report.products},
        {trial.id: trial.display_id for trial in b_report.trials},
    )
    shared = next(row for row, _source in records if row["row_id"] == view_row_id(views))
    assert shared["source_denominator_scope_zh"] == SCOPE_MEASURE
    assert shared["source_denominator_value"] == 35
    assert shared["source_denominator_path"].endswith(
        ".outcomeMeasures[0].denoms[0].counts[0].value"
    )
    # Legacy pool rows stay byte-identical in key set: no new scientific hash input.
    legacy = next(row for row, _source in records if row["row_id"] != view_row_id(views))
    assert not any(key in legacy for key in METADATA_KEYS)

    a_data = report_a.ReportAPortalData.model_validate({
        **a_report.model_dump(mode="json"),
        "efficacy_views": {
            "coverage_mode": "partial",
            "facts": [
                {**view, "source_fact_version_id": version_id} for view in views
            ],
        },
    })
    _workspace, _groups, a_rows = report_a._a_comparison_workspace(a_data)
    assert a_rows[view_row_id(views)]["source_denominator_scope_zh"] == SCOPE_MEASURE
    assert a_rows[view_row_id(views)]["source_denominator_value"] == 35


def view_row_id(views: tuple[dict[str, Any], ...]) -> str:
    return str(views[0]["row_id"])


def test_scope_disclosure_does_not_change_existing_consumer_or_semantic_identity(
    tmp_path: Path,
) -> None:
    root, snapshot, a_report, version_id = _candidate(tmp_path)
    row_id = next(row.row_id for row in a_report.efficacy if row.source_version_id)
    selected = {f"efficacy:{row_id}": version_id}
    register_a_source_consumers(root, snapshot, a_report, selected, registered_at=AT)
    view = project_b_efficacy_source_views(root, snapshot, a_report, selected)[0]
    plain = {key: value for key, value in view.items() if key not in METADATA_KEYS}

    def report(value: dict[str, Any]) -> ReportBPortalData:
        return ReportBPortalData.model_validate({
            **a_report.model_dump(mode="json"),
            "efficacy_views": {"coverage_mode": "partial", "facts": [value]},
        })

    old = report(plain)
    disclosed = report(view)
    assert report_b.active_fact_binding_for_b(old, "efficacy", row_id) == (
        report_b.active_fact_binding_for_b(disclosed, "efficacy", row_id)
    )
    from ci_workflow.reports.b.semantic_grouping import semantic_row_digest, semantic_source_digest

    def projected(data: ReportBPortalData) -> dict[str, Any]:
        return next(row for row, _ in report_b._efficacy_records(
            data, {p.id: p.name for p in data.products},
            {t.id: t.display_id for t in data.trials},
        ) if row["row_id"] == row_id)

    assert semantic_row_digest(projected(old)) == semantic_row_digest(projected(disclosed))
    changed = report({**view, "value": 31.0})
    with pytest.raises(report_b.ReportBPortalError, match="来源view身份不一致"):
        report_b.active_fact_binding_for_b(changed, "efficacy", row_id)
    assert semantic_source_digest({**view, "value": 31.0}) != semantic_source_digest(view)
    assert semantic_row_digest({**projected(disclosed), "value": 31.0}) != (
        semantic_row_digest(projected(old))
    )


def test_fact_cell_discloses_source_only_scope_in_paired_context() -> None:
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function createComparisonQuestionOrder(');
const end=source.indexOf('\n  window.__COMPARISON_QUERY__',start);
class Node{constructor(){this.children=[];this.attrs={};}
 appendChild(x){this.children.push(x);return x;}setAttribute(k,v){this.attrs[k]=v;}}
const doc={createElement(){return new Node();}},sandbox={};
vm.runInNewContext(source.slice(start,end),sandbox);
const query=sandbox.createComparisonQuestionOrder();
const disclosure='来源分母：该访视或类别分析人数 N=77（来源原值，非当前值）';
const cell=new Node(),button=new Node();
const row={row_id:'v1',product_zh:'drug',arm:'drug',value:61.5,
 difference_note:'分母口径不同',source_denominator_scope_zh:'该访视或类别分析人数',
 source_denominator_value:77,source_denominator_path:'$.resultsSection.x.y'};
const frozen=JSON.stringify(row);
query.factCell(doc,cell,button,row,'61.5 %','');
assert.equal(button.children[0].children[1].textContent,'61.5 %'); // face unchanged
const observation=cell.children[0].children[0];
assert.equal(observation.children[0],button); // source trigger stays reachable
const details=observation.children[1];
assert.equal(details.children[0].textContent,'条件与限制');
assert.equal(details.children[1].textContent,'分母口径不同');
assert.equal(details.children[2].textContent,disclosure);
assert.equal(details.children[2].className,'kz-comparison-context__denominator');
assert.equal(JSON.stringify(row),frozen); // presentation never rewrites the row
// A user-cleared current value keeps its cleared face; the retained N is source-only.
const clear=new Node(),clearCell=new Node();
query.factCell(doc,clearCell,clear,{row_id:'v2',product_zh:'drug',arm:'drug',value:null,
 source_denominator_scope_zh:'该访视或类别分析人数',source_denominator_value:77},
 '用户清除，待重新核实','');
assert.equal(clear.children[0].children[1].textContent,'用户清除，待重新核实');
const clearDetails=clearCell.children[0].children[0].children[1];
assert.equal(clearDetails.children.length,2);
assert.equal(clearDetails.children[1].textContent,disclosure);
// Unresolved scope is disclosed without inventing an N.
const unknown=new Node(),unknownCell=new Node();
query.factCell(doc,unknownCell,unknown,{row_id:'v3',product_zh:'drug',value:61.5,
 source_denominator_scope_zh:'分母范围待核'},'61.5 %','');
assert.equal(unknownCell.children[0].children[0].children[1].children[1].textContent,
 '来源分母：分母范围待核');
// No verified metadata and no notes: no empty disclosure is created.
const plain=new Node(),plainCell=new Node();
query.factCell(doc,plainCell,plain,{row_id:'v4',product_zh:'drug',value:61.5},'61.5 %','');
assert.equal(plainCell.children[0].children[0].children.length,1);
"""
    result = subprocess.run(["node", "-e", probe, str(PORTAL_JS)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_real_frozen_views_expose_locked_scope_and_stay_read_only() -> None:
    project, snapshot, a_report, selected = _fixed_fixture()
    database = project / "state/project.sqlite"
    snapshot_path = project / snapshot.relative_path
    database_before = sha256(database.read_bytes()).hexdigest()
    snapshot_before = sha256(snapshot_path.read_bytes()).hexdigest()

    views = project_b_efficacy_source_views(project, snapshot, a_report, selected)

    labels: Counter[str] = Counter()
    expected_labels: Counter[str] = Counter()
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        for view in views:
            version_id = selected[f"efficacy:{view['row_id']}"]
            context_json, locator_json = connection.execute(
                "SELECT v.scientific_context_json,f.locator FROM fact_versions v "
                "JOIN evidence_fragments f ON f.fragment_id=v.primary_fragment_id "
                "WHERE v.fact_version_id=?",
                (version_id,),
            ).fetchone()
            context = json.loads(context_json)["result_context"]
            candidates = [
                candidate for candidate in context.get("denominator_candidates", ())
                if candidate["group_id"] == context["group_id"]
            ]
            row_path = json.loads(locator_json)["field_path"]
            if len(candidates) != 1:
                expected = (SCOPE_UNRESOLVED, None, None)
            else:
                path = candidates[0]["value_path"]
                scope = path.rsplit(".denoms[", 1)[0]
                measure = context["source_measure_path"]
                suffix = path[len(measure) + 1:] if path.startswith(measure + ".") else None
                if not row_path.startswith("$." + scope + "."):
                    expected = (SCOPE_UNRESOLVED, None, None)
                elif suffix and suffix.split(".", 1)[0].startswith("classes["):
                    nested = suffix.split(".", 2)
                    if len(nested) > 1 and nested[1].startswith("categories["):
                        expected = (SCOPE_CATEGORY, candidates[0]["parsed_value"], "$." + path)
                    else:
                        expected = (SCOPE_CLASS, candidates[0]["parsed_value"], "$." + path)
                elif suffix and suffix.split(".", 1)[0].startswith("categories["):
                    expected = (SCOPE_CATEGORY, candidates[0]["parsed_value"], "$." + path)
                elif suffix and suffix.startswith("denoms["):
                    expected = (SCOPE_MEASURE, candidates[0]["parsed_value"], "$." + path)
                else:
                    expected = (SCOPE_UNRESOLVED, None, None)
            assert (
                view["source_denominator_scope_zh"],
                view["source_denominator_value"],
                view["source_denominator_path"],
            ) == expected, view["row_id"]
            assert view["source_denominator_scope_zh"] in SCOPE_LABELS
            labels[view["source_denominator_scope_zh"]] += 1
            expected_labels[expected[0]] += 1

    assert labels == expected_labels
    assert labels[SCOPE_UNRESOLVED] == 0
    assert labels[SCOPE_MEASURE] == len(views)
    assert sha256(database.read_bytes()).hexdigest() == database_before
    assert sha256(snapshot_path.read_bytes()).hexdigest() == snapshot_before


def test_current_frozen_snapshot_discloses_each_verified_class_n_source_only() -> None:
    snapshot_path = (
        REPO / ".artifacts/1007-abc-current-integration-v1/working/project/snapshots"
        "/evidence/evidence-snapshot_fca99fb6250a1d7452356764.json"
    )
    if not snapshot_path.is_file():
        pytest.skip("current frozen joint A/B evidence snapshot is not in this checkout")
    before = sha256(snapshot_path.read_bytes()).hexdigest()
    closure = json.loads(snapshot_path.read_bytes())["closure"]["facts"]

    class_ns: list[int] = []
    class_candidates = 0
    unresolved = 0
    for item in closure:
        context = ResearchResultContext.model_validate(item["fact"]["result_context"])
        own = [
            candidate for candidate in context.denominator_candidates
            if candidate.group_id == context.group_id
        ]
        label, value, path = denominator_scope_disclosure(
            context, item["fact"]["locator"]["field_path"],
        )
        assert label in SCOPE_LABELS and "ITT" not in label
        if len(own) == 1 and ".classes[" in own[0].value_path:
            class_candidates += 1
            assert label == SCOPE_CLASS
            assert value == own[0].parsed_value
            assert path == "$." + own[0].value_path
            class_ns.append(value)
        elif label == SCOPE_UNRESOLVED:
            unresolved += 1
            assert value is None and path is None

    assert class_candidates == 33
    assert class_ns and len(set(class_ns)) > 1 and min(class_ns) >= 75
    assert unresolved == 0
    assert sha256(snapshot_path.read_bytes()).hexdigest() == before
