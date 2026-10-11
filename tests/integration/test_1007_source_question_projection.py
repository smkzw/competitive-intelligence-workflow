"""Source-scoped descriptive questions cannot change scientific/numeric identity.

Synthetic contract counterexamples, not medical acceptance of a clinical family.
Real source adoption is independently reviewed and recorded separately.
"""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

from ci_workflow.application.source_research_service import ResearchFact, ResearchResultContext
from ci_workflow.domain.source_clause_context import SourceClauseContext, SourceClauseReference
from ci_workflow.renderers.portal import report_a, report_b
from ci_workflow.reports.b.publication_components import publication_value_components
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
@pytest.mark.parametrize("source_format", ["json", "xml"])
def test_ordinary_portal_consumes_separate_question_metadata(kind, source_format, tmp_path):
    root = Path(__file__).resolve().parents[2]
    raw = json.loads((root / "fixtures/synthetic/a-complete/inputs/report-data.json").read_text())
    _records, _groups, projections = _xml_inputs() if source_format == "xml" else _inputs()
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


def _xml_inputs():
    records, _, projections = _inputs()
    projected = []
    for index, (_row, source) in enumerate(records):
        parent = f"/article/body[1]/sec[1]/table-wrap[1]/table[1]/tbody[1]/tr[{index + 1}]"
        cell, label = parent + "/td[2]", parent + "/td[1]"
        reference = SourceClauseReference(
            reference_id=f"xml-row-{index}", source_id=f"paper-{index}",
            label_zh="行标签与时间点", original_text=f"Response at week {16 + index}",
            locator={"document_role": "primary_results_publication", "field_path": label,
                     "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC00000000/"},
        )
        context = SourceClauseContext(label_zh="论文表格原文", scope_note_zh="原始行列定位",
            scientific_scope={"source_version_id": f"source-v{index}",
                "source_measure_path": cell, "row_label_path": label},
            continuations=(reference,))
        source.update(source_id=f"paper-{index}", source_measure_path=cell,
                      source_clause_context=context.model_dump(mode="json"))
        row = report_b._project_record(source, domain="efficacy", names={}, trial_names={},
                                       fallback=f"row-{index}")
        projected.append(({**row, "_domain": "efficacy"}, source))
        projections[index].update(source_measure_path=cell,
                                 basis_reference_ids=[reference.reference_id])
    return projected, report_b._groups_for_page("efficacy", projected), projections


def test_exact_publication_sibling_label_can_share_question_without_granting_coaxis():
    records, groups, projections = _xml_inputs()
    before = deepcopy((records, groups))
    original = _workspace(records, groups, [])
    result = _workspace(records, groups, projections)
    assert len(result["columns"]) == 1
    assert result["columns"][0]["question_known"]
    assert result["columns"][0]["cells"] == {"trial-0": ["row-0"], "trial-1": ["row-1"]}
    for axis in ("membership", "facets", "numeric_eligibility"):
        assert result[axis] == original[axis]
    assert (records, groups) == before


@pytest.mark.parametrize("fault", ["different_row", "different_table", "foreign_source",
                                  "parent_traversal", "no_label_scope", "other_reference"])
def test_publication_question_rejects_unbound_label_but_keeps_every_observation(fault):
    records, _, projections = _xml_inputs()
    row = records[1][0]
    context = row["source_clause_context"]
    label = context["scientific_scope"]["row_label_path"]
    reference = context["continuations"][0]
    if fault == "different_row":
        label = label.replace("tr[2]", "tr[3]")
    elif fault == "different_table":
        label = label.replace("table[1]", "table[2]")
    elif fault == "parent_traversal":
        label = label.replace("/td[1]", "/../tr[2]/td[1]")
    elif fault == "foreign_source":
        reference["source_id"] = "another-paper"
    elif fault == "no_label_scope":
        context["scientific_scope"].pop("row_label_path")
    else:
        reference["locator"]["field_path"] = label.replace("td[1]", "td[3]")
    if fault in {"different_row", "different_table", "parent_traversal"}:
        context["scientific_scope"]["row_label_path"] = label
        reference["locator"]["field_path"] = label
    groups = report_b._groups_for_page("efficacy", records)
    result = _workspace(records, groups, projections)
    assert len(result["columns"]) == 2
    assert set(result["membership"]["row_ids"]) == {"row-0", "row-1"}
    assert any(not column["question_known"] for column in result["columns"])


def _component_inputs(fault=None):
    original, _, projections = _xml_inputs()
    records = []
    for index, (_row, source) in enumerate(original):
        source.pop("source_param_type")
        text = ("14 (18.4)", "45 (60.0)")[index]
        context = ResearchResultContext(result_key=f"result-{index}", category="outcome",
            trial_id=source["trial_id"], group_id=f"group-{index}", group_title="Source arm",
            arm="Source arm", term=source["source_measure_definition"],
            endpoint=source["source_measure_definition"], timepoint=source["timepoint"],
            value_role="reported_measure", source_unit="n (%)", domain="efficacy",
            metric="unresolved", source_measure_path=source["source_measure_path"],
            raw_value_type="composite_count_and_percent", analysis_population="As reported")
        fact = ResearchFact(fact_id=source["row_id"], row_ref=source["row_id"],
            entity_id=source["trial_id"], entity_type="clinical_trial", canonical_name="Study",
            field_id="efficacy.source_cell", raw_value=text, normalized_value=None,
            disclosure_state="reported_value", source_id=source["source_id"],
            locator={"document_role": "primary_results_publication",
                "field_path": source["source_measure_path"],
                "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC00000000/"},
            original_text=text, result_context=context,
            source_clause_context=source["source_clause_context"])
        source.update(value=(18.4, 60.0)[index], unit="%", group_id=context.group_id,
            statistic_form="proportion", numerator=None, denominator=None,
            source_value_role=context.value_role, source_metric=context.metric,
            source_fact_version_id=f"fact-v{index}", source_fact=fact.model_dump(mode="json"),
            source_result_context=context.model_dump(mode="json"),
            source_component_projection=publication_value_components(fact)["projection"],
            reported_count=(14, 45)[index], source_locator=fact.locator.model_dump(mode="json"))
        if index == 1 and fault:
            if fault == "missing_fact":
                source.pop("source_fact")
            elif fault == "value":
                source["value"] = 61
            elif fault == "count":
                source["reported_count"] = 46
            elif fault == "span":
                source["source_component_projection"]["components"][1]["token_span"] = [0, 2]
            elif fault == "context":
                source["source_result_context"]["timepoint"] = "Week 52"
            elif fault == "locator":
                source["source_locator"]["field_path"] = "/article/other-cell"
            elif fault == "source":
                source["source_id"] = "foreign-paper"
            elif fault == "group":
                source["group_id"] = "foreign-arm"
            elif fault == "unit":
                source["unit"] = "participants"
            elif fault == "denominator":
                source["denominator"] = 75
            elif fault == "fact_version":
                source["source_fact_version_id"] = ""
            elif fault == "stale_fact_scope":
                source["source_fact"]["source_clause_context"]["scientific_scope"][
                    "source_version_id"] = "stale-version"
            elif fault == "false_zero":
                source["source_fact"]["disclosure_state"] = "reported_zero"
                source["disclosure_state"] = "reported_zero"
            elif fault == "nonclinical":
                source["source_metric"] = "anti_drug_antibody"
            elif fault == "unknown_product":
                source["product_id"] = None
                source["group_assignment_state"] = "unknown"
            elif fault == "clear":
                source["value"] = None
                source["disclosure_state"] = "user_cleared"
        row = report_b._project_record(source, domain="efficacy", names={}, trial_names={},
                                       fallback=source["row_id"])
        records.append(({**row, "_domain": "efficacy"}, source))
    return records, report_b._groups_for_page("efficacy", records), projections


def test_printed_publication_percent_forms_descriptive_plot_without_invented_param_type():
    records, groups, projections = _component_inputs()
    before = deepcopy((records, groups))
    original = _workspace(records, groups, ())
    digests = [semantic_row_digest(row) for row, _ in records]
    result = _workspace(records, groups, projections)
    assert len(result["descriptive_groups"]) == 1
    plotted = result["descriptive_groups"][0]["rows"]
    assert {row["value"] for row in plotted} == {18.4, 60.0}
    assert {row["reported_count"] for row in plotted} == {14, 45}
    assert all("source_param_type" not in row for row in plotted)
    assert all(row["denominator"] is None and row["numerator"] is None for row in plotted)
    assert all(row["source_fact"]["normalized_value"] is None for row in plotted)
    assert all(row["source_fact"]["result_context"]["source_param_type"] is None
               for row in plotted)
    for axis in ("membership", "facets", "numeric_eligibility"):
        assert result[axis] == original[axis]
    assert [semantic_row_digest(row) for row, _ in records] == digests
    assert (records, groups) == before


@pytest.mark.parametrize("fault", ["missing_fact", "value", "count", "span", "context",
    "locator", "source", "group", "unit", "denominator", "fact_version",
    "stale_fact_scope", "false_zero", "nonclinical", "unknown_product", "clear"])
def test_unproven_component_does_not_plot_or_drop_original_observations(fault):
    records, groups, projections = _component_inputs(fault)
    result = _workspace(records, groups, projections)
    assert result["descriptive_groups"] == ()
    assert set(result["membership"]["row_ids"]) == {"row-0", "row-1"}
    assert sum(len(column["row_ids"]) for column in result["columns"]) == 2


def test_ordinary_b_portal_carries_printed_components_to_shared_graph_and_table_payload(tmp_path):
    raw = json.loads((Path(__file__).resolve().parents[2] /
        "fixtures/synthetic/a-complete/inputs/report-data.json").read_text())
    records, _, questions = _component_inputs()
    # Explicit fixture relationships, not a claimed medical product assignment.
    products = [{**product, "id": f"drug-{i}"}
                for i, product in enumerate(raw["products"][:2])]
    trials = [{**trial, "id": f"trial-{i}", "product_id": f"drug-{i}"}
              for i, trial in enumerate(raw["trials"][:2])]
    metadata = {key: value for key, value in raw.items()
                if key in {"schema_version", "report_version", "indication",
                           "data_cutoff", "sources"}}
    data = report_b.ReportBPortalData.model_validate({**metadata,
        "products": products, "trials": trials,
        "efficacy_views": {"facts": [source for _, source in records],
                           "clinical_questions": questions}})
    original = data.model_dump_json()
    report_b.render_report_b_site(data, tmp_path / "B")
    html = (tmp_path / "B/overview.html").read_text()
    prefix = "window.__B_COMPARISON_WORKSPACE__ = "
    paths = re.findall(r'<script src="([^"]+)">', html)
    encoded = next((tmp_path / "B" / path).read_text()
        for path in paths if path.startswith("data/")
        and (tmp_path / "B" / path).read_text().startswith(prefix))
    workspace = json.loads(encoded.removeprefix(prefix).strip().removesuffix(";"))
    assert workspace["columns"][0]["row_ids"]
    groups = workspace["descriptive_groups"]
    assert len(groups) == 1
    assert all(row["_chart_type"] == "bar" for row in groups[0]["rows"])
    assert {row["row_id"] for row in groups[0]["rows"]} == {"row-0", "row-1"}
    assert set(workspace["columns"][0]["row_ids"]) == {
        row["row_id"] for row in groups[0]["rows"]}
    assert {row["value"] for row in groups[0]["rows"]} == {18.4, 60.0}
    assert "b-comparison" in html
    assert data.model_dump_json() == original


def test_source_conflict_projection_is_idempotent_without_restoring_scientific_renderability():
    records, _, _ = _component_inputs()
    once = report_b._records_with_semantics(records, page_id="efficacy")
    twice = report_b._records_with_semantics(once, page_id="efficacy")
    assert once == twice
    assert all(row["renderable"] is False for row, _ in twice)
    assert all(row["source_metric"] == "unresolved" for row, _ in twice)
    assert len({semantic_row_digest(row) for row, _ in twice}) == 2
