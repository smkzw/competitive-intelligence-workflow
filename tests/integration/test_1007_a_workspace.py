"""A uses the existing scientific frames, never a label-only comparison table."""

import json
from pathlib import Path

import pytest

from ci_workflow.renderers.portal import report_a


def _payload():
    root = Path(__file__).resolve().parents[2]
    raw = json.loads((root / "fixtures/synthetic/a-complete/inputs/report-data.json").read_text())
    raw["efficacy_views"] = {"facts": [{
        **row, "original_endpoint": row["endpoint"],
        "original_definition": "EASI75 exact definition",
        "actual_timepoint": 16, "actual_timepoint_unit": "week", "analysis_form": "response_rate",
        "analysis_population": "FAS", "direction": "higher_is_better",
        "estimand": "treatment_policy",
        "denominator_role": "full_analysis_set", "instrument_or_scale": "EASI v1.0",
    } for row in raw["efficacy"]]}
    return raw


def test_ordinary_a_has_all_study_rows_shared_columns_and_fact_mapping(tmp_path):
    raw = _payload()
    data = report_a.ReportAPortalData.model_validate(raw)
    before = data.model_dump_json()
    workspace, groups, rows = report_a._a_comparison_workspace(data)
    assert set(workspace["study_ids"]) == set(data.trial_ids)
    first_ids = {r["row_id"] for r in raw["efficacy"][:4]}
    assert any(first_ids <= set(column["row_ids"]) for column in workspace["columns"])
    assert set(rows) == {r.row_id for r in (*data.efficacy, *data.safety)}
    assert all(rows[row_id]["a_row_id"] == row_id for row_id in rows)
    assert any(group["cross_trial"] for group in groups)
    report_a.render_report_a_site(data, tmp_path / "A")
    html = (tmp_path / "A/clinical-portfolio.html").read_text()
    assert 'id="full-study-comparison"' in html and "__A_COMPARISON_WORKSPACE__" in html
    assert "__A_COMPARISON_ROWS__" in html and "kz-chart-module" in html
    assert "clinical-portfolio.html?view=comparison" in (tmp_path / "A/overview.html").read_text()
    assert data.model_dump_json() == before


@pytest.mark.parametrize("field,value", [
    ("instrument_or_scale", "another scale"), ("direction", "lower_is_better"),
    ("analysis_population", "PPS"), ("original_definition", "未知(待核)"),
    ("source_domain", "immunogenicity"),
])
def test_a_differences_remain_visible_without_wrong_common_frame(field, value):
    raw = _payload()
    raw["efficacy_views"]["facts"][2][field] = value
    data = report_a.ReportAPortalData.model_validate(raw)
    workspace, groups, rows = report_a._a_comparison_workspace(data)
    assert "eff-competitor-t" in rows
    pair = {"eff-fixture-t", "eff-competitor-t"}
    assert not any(pair <= {r["row_id"] for r in group["rows"]} for group in groups)
    if field in {"instrument_or_scale", "direction", "analysis_population"}:
        # One known question, different retained scientific facets; a shared
        # descriptive matrix column must not be mistaken for a joint axis.
        column = next(c for c in workspace["columns"] if pair <= set(c["row_ids"]))
        assert len(column["scientific_facet_ids"]) > 1
        assert column["comparison_purpose"] == "clinical_question_descriptive"
        assert not any(pair <= set(f["row_ids"]) for f in column["scientific_facets"])
    else:
        assert not any(pair <= set(c["row_ids"]) for c in workspace["columns"])


def test_legacy_a_keeps_unknown_semantics_instead_of_guessing_equivalence():
    raw = _payload()
    raw.pop("efficacy_views")
    workspace, _groups, rows = report_a._a_comparison_workspace(
        report_a.ReportAPortalData.model_validate(raw),
    )
    assert len(rows) == len(raw["efficacy"]) + len(raw["safety"])
    assert not any({"eff-fixture-t", "eff-competitor-t"} <= set(column["row_ids"])
                   for column in workspace["columns"])


@pytest.mark.parametrize("field,value", [
    ("source_domain", "immunogenicity"), ("source_metric", "cmax"),
    ("source_domain", None),
])
def test_native_b_adapter_keeps_explicit_scientific_typing(field, value):
    from ci_workflow.renderers.portal import report_b

    raw = _payload()
    raw["efficacy_views"]["facts"][0][field] = value
    data = report_b.ReportBPortalData.model_validate(raw)
    records = report_b._efficacy_records(data, {p.id: p.name for p in data.products},
                                        {t.id: t.display_id for t in data.trials})
    first = next(row for row, _view in records if row["row_id"] == raw["efficacy"][0]["row_id"])
    assert field in first and first[field] == value
    tagged = tuple(({**row, "_domain": "efficacy"}, view) for row, view in records)
    groups = report_b._groups_for_page("efficacy", tagged)
    workspace = report_b._comparison_workspace(tagged, groups, data.trial_ids)
    assert first["row_id"] not in workspace["numeric_eligibility"]["drawable_row_ids"]
