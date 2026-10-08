"""Source-scoped descriptive questions cannot change scientific/numeric identity.

Synthetic contract counterexamples, not medical acceptance of a clinical family.
Real source adoption is independently reviewed and recorded separately.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from ci_workflow.domain.source_clause_context import SourceClauseContext, SourceClauseReference
from ci_workflow.renderers.portal import report_a, report_b
from ci_workflow.reports.b.semantic_grouping import semantic_row_digest
from ci_workflow.reports.common.view_state import SourceQuestionProjection


def _inputs():
    records, projections = [], []
    for index in range(2):
        version, path = f"source-v{index}", f"results.measure[{index}]"
        reference = SourceClauseReference(
            reference_id=f"ref-{index}", source_id=f"source-{index}",
            label_zh="原结局定义", original_text=f"Original definition {index}",
            locator={"document_role": "clinical_trial_registry",
                     "field_path": f"$.{path}.description",
                     "url": "https://clinicaltrials.gov/study/NCT00000001"},
        )
        context = SourceClauseContext(label_zh="登记结局语境", scope_note_zh="仅描述性同题",
            scientific_scope={"source_version_id": version, "source_measure_path": path},
            continuations=(reference,))
        source = {"row_id": f"row-{index}", "product_id": f"drug-{index}",
            "trial_id": f"trial-{index}", "endpoint": f"Source-defined question {index}",
            "value": 30 + index, "unit": "%" if index == 0 else "participants",
            "timepoint": "Week 16" if index == 0 else "Week 24",
            "source_domain": "efficacy", "source_version_id": version,
            "source_measure_path": path, "source_clause_context": context.model_dump(mode="json"),
            "source_measure_definition": reference.original_text,
            "source_param_type": "NUMBER", "source_analysis_population": "As reported",
            "clinical_concept": "not_reported",
        }
        row = report_b._project_record(source, domain="efficacy", names={}, trial_names={},
                                       fallback=f"row-{index}")
        records.append(({**row, "_domain": "efficacy"}, source))
        projections.append({"source_version_id": version, "source_measure_path": path,
            "question_id": "source-question", "question_label_zh": "来源支持的共同临床问题",
            "basis_reference_ids": [reference.reference_id],
            "comparison_purpose": "clinical_question_descriptive"})
    groups = report_b._groups_for_page("efficacy", records)
    return records, groups, projections


def _workspace(records, groups, projections):
    return report_b._comparison_workspace(records, groups, ("trial-0", "trial-1"),
                                         question_projections=projections)


def test_source_question_shares_column_not_scientific_frame_or_digest():
    records, groups, projections = _inputs()
    before_records, before_groups = deepcopy(records), deepcopy(groups)
    digests = [semantic_row_digest(row) for row, _ in records]
    original = report_b._comparison_workspace(records, groups, ("trial-0", "trial-1"))
    result = _workspace(records, groups, projections)
    assert len(original["columns"]) == 2
    assert len(result["columns"]) == 1
    column = result["columns"][0]
    assert column["question_known"] is True
    assert column["comparison_purpose"] == "clinical_question_descriptive"
    assert column["cells"] == {"trial-0": ["row-0"], "trial-1": ["row-1"]}
    assert len(column["scientific_facets"]) == 2
    for key in ("membership", "facets", "numeric_eligibility"):
        assert result[key] == original[key]
    assert records == before_records and groups == before_groups
    assert [semantic_row_digest(row) for row, _ in records] == digests


@pytest.mark.parametrize(
    "fault", ["version", "path", "reference", "scope", "domain", "page_domain"],
)
def test_unproven_source_binding_does_not_merge_or_drop_rows(fault):
    records, groups, projections = _inputs()
    if fault == "version":
        projections[1]["source_version_id"] = "another-version"
    elif fault == "path":
        projections[1]["source_measure_path"] = "another.measure[0]"
    elif fault == "reference":
        projections[1]["basis_reference_ids"] = ["missing-ref"]
    elif fault == "scope":
        records[1][0]["source_clause_context"]["scientific_scope"]["source_version_id"] = "wrong"
    elif fault == "domain":
        records[1][0]["source_domain"] = "immunogenicity"
    else:
        records[1][0]["_domain"] = "supporting"
    # The scientific projector returns copies, not aliases of the source rows.
    # Recreate the production groups after changing a projected scientific axis.
    page = "overview" if fault == "page_domain" else "efficacy"
    groups = report_b._groups_for_page(page, records)
    result = _workspace(records, groups, projections)
    assert len(result["columns"]) == 2
    assert set(result["membership"]["row_ids"]) == {"row-0", "row-1"}
    assert any(not column["question_known"] for column in result["columns"])


def test_distinct_questions_do_not_merge_by_topic_or_equal_numeric_value():
    records, groups, projections = _inputs()
    projections[1]["question_id"] = "composite-or-other-question"
    records[1][0]["value"] = records[0][0]["value"]
    result = _workspace(records, groups, projections)
    assert len(result["columns"]) == 2


@pytest.mark.parametrize(
    "fault", ["duplicate", "label_conflict", "numeric_permission", "copied_model"],
)
def test_projection_contract_rejects_ambiguous_or_numeric_authority(fault):
    records, groups, projections = _inputs()
    if fault == "duplicate":
        projections.append(deepcopy(projections[0]))
    elif fault == "label_conflict":
        projections[1]["question_label_zh"] = "不同临床问题"
    elif fault == "numeric_permission":
        projections[0]["numeric_permission"] = True
    else:
        projections[0] = SourceQuestionProjection.model_validate(projections[0]).model_copy(
            update={"comparison_purpose": "semantic_numeric_frame"},
        )
    with pytest.raises(report_b.ReportBPortalError, match="临床问题"):
        _workspace(records, groups, projections)


def test_two_question_bindings_inside_one_science_facet_remain_distinct():
    records, _groups, projections = _inputs()
    projections[1]["question_id"] = "other-question"
    groups = ({"scientific_group_id": "same-science-facet", "title_zh": "原科学条件",
               "rows": [row for row, _ in records]},)
    result = _workspace(records, groups, projections)
    assert len(result["columns"]) == 2
    assert len({column["id"] for column in result["columns"]}) == 2
    assert {item["facet_id"] for item in result["facets"]["assignments"]} == {"same-science-facet"}
    assert set(result["membership"]["row_ids"]) == {"row-0", "row-1"}


def test_source_condition_notes_reach_existing_cell_labels_without_changing_facets():
    records, groups, projections = _inputs()
    projections[0]["condition_notes_zh"] = ["Kaplan–Meier 概率，非原报告百分比"]
    projections[1]["condition_notes_zh"] = [
        "参与者人数，未换算率", "缺失处理原文截断，完整规则待核",
    ]
    original = report_b._comparison_workspace(records, groups, ("trial-0", "trial-1"))
    result = _workspace(records, groups, projections)
    column = result["columns"][0]
    assert "Kaplan–Meier 概率" in column["facet_label_by_row"]["row-0"]
    assert "未换算率" in column["facet_label_by_row"]["row-1"]
    assert "原文截断" in column["facet_label_by_row"]["row-1"]
    for key in ("membership", "facets", "numeric_eligibility"):
        assert result[key] == original[key]
    assert tuple(f for c in original["columns"] for f in c["scientific_facets"]) == (
        column["scientific_facets"])


@pytest.mark.parametrize("kind", ["A", "B"])
def test_ordinary_portal_consumes_separate_question_metadata(kind, tmp_path):
    root = Path(__file__).resolve().parents[2]
    raw = json.loads((root / "fixtures/synthetic/a-complete/inputs/report-data.json").read_text())
    _records, _groups, projections = _inputs()
    facts = []
    for index, native in enumerate((raw["efficacy"][0], raw["efficacy"][2])):
        facts.append({**native, **{key: value for key, value in _records[index][1].items()
            if key not in {"row_id", "product_id", "trial_id", "value", "unit", "timepoint"}}})
    raw["efficacy_views"] = {"coverage_mode": "partial", "facts": facts,
                             "clinical_questions": projections}
    if kind == "A":
        data = report_a.ReportAPortalData.model_validate(raw)
        before = data.model_dump_json()
        report_a.render_report_a_site(data, tmp_path / "A")
        html = (tmp_path / "A/clinical-portfolio.html").read_text()
        prefix = "window.__A_COMPARISON_WORKSPACE__ = "
        encoded = html.split(prefix, 1)[1].split(";\n", 1)[0]
        workspace = json.loads(encoded)
    else:
        data = report_b.ReportBPortalData.model_validate(raw)
        before = data.model_dump_json()
        report_b.render_report_b_site(data, tmp_path / "B")
        prefix = "window.__B_COMPARISON_WORKSPACE__ = "
        workspaces = [json.loads(path.read_text().removeprefix(prefix).strip().removesuffix(";"))
            for path in (tmp_path / "B/data").rglob("*.js")
            if path.read_text().startswith(prefix)]
        # Dossiers legitimately have one study; do not let hash-file iteration
        # choose one of them instead of the full production study workspace.
        workspace = max(workspaces, key=lambda w: len(w["membership"]["row_ids"]))
    column = next(c for c in workspace["columns"]
                  if c["question_id"] == "efficacy::source-question")
    assert set(column["cells"]) == {raw["efficacy"][0]["trial_id"], raw["efficacy"][2]["trial_id"]}
    assert len(column["row_ids"]) == 2
    assert len(column["scientific_facets"]) == 2
    assert {b["source_version_id"] for b in column["question_source_bindings"]} == {
        "source-v0", "source-v1"}
    assert data.model_dump_json() == before
