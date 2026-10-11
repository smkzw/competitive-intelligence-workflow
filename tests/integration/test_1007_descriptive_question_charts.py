"""Production descriptive graphs keep questions, metrics and source atoms distinct."""

from copy import deepcopy

import pytest

from ci_workflow.domain.source_clause_context import SourceClauseContext, SourceClauseReference
from ci_workflow.renderers.portal import report_b
from ci_workflow.reports.b.semantic_grouping import semantic_row_digest


def inputs():
    records, projections = [], []
    for study in range(2):
        for visit in (4, 16):
            version, path = f"source-{study}", f"results.measure[{visit}]"
            reference = SourceClauseReference(
                reference_id=f"ref-{study}-{visit}", source_id=version,
                label_zh="瘙痒改善定义", original_text="Number achieving >=4-point improvement",
                locator={"document_role": "clinical_trial_registry",
                         "field_path": f"$.{path}.description"},
            )
            context = SourceClauseContext(label_zh="登记结局定义", scope_note_zh="原登记测量",
                scientific_scope={"source_version_id": version, "source_measure_path": path},
                continuations=(reference,))
            source = {"row_id": f"row-{study}-{visit}", "product_id": f"drug-{study}",
                "trial_id": f"nct{study + 1:08d}", "group_id": "OG001",
                "endpoint": reference.original_text, "value": study * 10 + visit,
                "unit": "Participants",
                "timepoint": f"Week {visit}", "source_domain": "efficacy",
                "source_version_id": version, "source_measure_path": path,
                "source_clause_context": context.model_dump(mode="json"),
                "source_measure_definition": reference.original_text,
                "source_param_type": "COUNT_OF_PARTICIPANTS",
                "source_value_role": "participant_count",
                "source_analysis_population": "As reported", "clinical_concept": "not_reported"}
            row = report_b._project_record(source, domain="efficacy", names={}, trial_names={},
                                          fallback=source["row_id"])
            records.append(({**row, "_domain": "efficacy"}, source))
            projections.append({"source_version_id": version, "source_measure_path": path,
                "question_id": "itch-response", "question_label_zh": "瘙痒评分改善≥4分",
                "basis_reference_ids": [reference.reference_id],
                "comparison_purpose": "clinical_question_descriptive"})
    return records, projections


def workspace(records, projections):
    groups = report_b._groups_for_page("efficacy", records)
    return report_b._comparison_workspace(records, groups, (), question_projections=projections)


def test_posted_values_share_descriptive_plot_not_scientific_eligibility():
    records, projections = inputs()
    before = deepcopy(records)
    original = workspace(records, [])
    actual = workspace(records, projections)
    plots = actual["descriptive_groups"]
    assert len(plots) == 1 and len(plots[0]["rows"]) == 4
    plot = plots[0]
    assert plot["comparison_purpose"] == "clinical_question_descriptive"
    assert plot["cross_trial"] is False  # no accepted harmonized frame is manufactured
    assert plot["identity_series"] is True
    assert plot["question_id"] == "efficacy::itch-response"
    assert {r["trial_id"] for r in plot["rows"]} == {"nct00000001", "nct00000002"}
    assert len({r["_chart_comparison_context_key"] for r in plot["rows"]}) == 4
    assert {r["row_id"] for r in plot["rows"]} == set(actual["membership"]["row_ids"])
    for key in ("membership", "facets", "numeric_eligibility"):
        assert actual[key] == original[key]
    assert records == before
    assert [semantic_row_digest(r) for r, _ in records] == [
        semantic_row_digest(r) for r, _ in before]


@pytest.mark.parametrize("fault", ("question", "version", "binding", "metric", "param", "scope"))
def test_different_question_or_unbound_or_different_metric_never_borrows_rows(fault):
    records, projections = inputs()
    for index in (2, 3):
        if fault == "question":
            projections[index]["question_id"] = "other-question"
        elif fault == "version":
            projections[index]["source_version_id"] = "wrong-version"
        elif fault == "binding":
            projections[index]["basis_reference_ids"] = ["absent"]
        elif fault == "metric":
            records[index][0]["numeric_projection"] = {
                **records[index][0]["numeric_projection"],
                "kind": "participant_proportion", "plot_unit": "%"}
            records[index][0]["unit"] = "%"
        elif fault == "param":
            records[index][0]["source_param_type"] = "MEAN"
        else:
            scope = records[index][0]["source_clause_context"]["scientific_scope"]
            scope["source_measure_path"] = "wrong"
    actual = workspace(records, projections)
    for plot in actual["descriptive_groups"]:
        ids = {r["row_id"] for r in plot["rows"]}
        assert not ({"row-0-4", "row-1-4"} <= ids)
    assert len(actual["membership"]["row_ids"]) == 4


def test_zero_and_current_clear_retained_without_restoring_source_value():
    records, projections = inputs()
    records[0][0].update(value=0, numeric_value=0)
    records[1][0].update(value=None, numeric_value=None, renderable=False,
                        disclosure_state="user_cleared")
    actual = workspace(records, projections)
    rows = {r["row_id"]: r for p in actual["descriptive_groups"] for r in p["rows"]}
    assert rows["row-0-4"]["value"] == 0
    assert rows["row-0-16"]["value"] is None
    assert rows["row-0-16"]["renderable"] is False
    assert "row-0-16" in actual["numeric_eligibility"]["undrawable_reasons"]


@pytest.mark.parametrize("prefix", ("", "Baseline, "))
def test_descriptive_visits_use_real_order_not_lexical_week_16_before_4(prefix):
    records, projections = inputs()
    for row, _ in records:
        visit = 4 if row["row_id"].endswith("-4") else 16
        row.update(time=f"{prefix}Week {visit}", actual_timepoint=f"{prefix}Week {visit}")
    before = deepcopy(records)
    forward = workspace(records, projections)["descriptive_groups"][0]
    reversed_group = workspace(list(reversed(records)), projections)["descriptive_groups"][0]
    expected = ["row-0-4", "row-0-16", "row-1-4", "row-1-16"]
    assert [r["row_id"] for r in forward["rows"]] == expected
    assert [r["row_id"] for r in reversed_group["rows"]] == expected
    assert forward["cross_trial"] is False
    assert records == before


def test_presentation_visit_order_does_not_convert_units_or_qualify_ranges():
    times = ("Baseline, Week 16", "Week 4 to Week 16", "Month 2", "Baseline, Week 4",
             "Not reported")
    records = [({"row_id": str(i), "product_id": "drug", "trial_id": "study",
                 "group_id": "group", "time": time, "actual_timepoint": time}, None)
               for i, time in enumerate(times)]
    before = deepcopy(records)
    ordered = report_b._sorted_bucket(records, chronological=True)
    assert [row["time"] for row, _ in ordered] == [
        "Month 2", "Baseline, Week 4", "Baseline, Week 16", "Not reported",
        "Week 4 to Week 16"]
    assert report_b._exact_visit_coordinate(records[0][0]) is None
    assert report_b._exact_visit_coordinate(records[1][0]) is None
    assert records == before
