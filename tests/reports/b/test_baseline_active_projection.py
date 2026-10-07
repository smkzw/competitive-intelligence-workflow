"""Study-scoped scalar edits keep baseline evidence and source identity intact."""

from copy import deepcopy

import pytest

from ci_workflow.renderers.portal.active_fact_projection import (
    ActiveFact,
    ActiveFactBinding,
    ActiveFactRevision,
    validate_active_fact_binding,
)
from ci_workflow.renderers.portal.report_a import SourceRow, StudyRow
from ci_workflow.renderers.portal.report_b import (
    ReportBPortalData,
    _project_active_facts_b,
    active_fact_binding_for_b,
    validate_active_fact_revision_b,
)
from tests.reports.b.test_source_baseline_view import _view


def _data():
    return ReportBPortalData(schema_version="1.0", report_version="source-baseline-test",
        indication="合成基线测试", data_cutoff="2026-10-07T00:00:00Z",
        related_studies=(StudyRow(id="nct12345678", display_id="NCT12345678",
            product_id=None, name="Source study", phase="未列示", region="登记",
            status="未列示", role="未绑定产品"),), baseline_views=_view(),
        sources=(SourceRow(source="https://clinicaltrials.gov/study/NCT12345678",
            scope="合成来源", maturity="候选", limitation="非真实验收"),))


def _revision(data, row, *, number=52.5, cleared=False, edited=True):
    binding = active_fact_binding_for_b(data, "baseline", row["row_id"])
    identity = {field: getattr(binding, field) for field in (
        "product_id", "drug_name", "trial_id", "registry_id", "group_id", "arm",
        "cohort_id", "period", "endpoint_definition", "event_definition",
        "statistical_form", "measure_object", "unit", "normalized_unit")}
    fact = ActiveFact(fact_id=row["row_id"], fact_version_id="baseline-revision-v1",
        field_id="baseline-value", raw_value=None if cleared else str(number),
        normalized_value=None if cleared else number,
        disclosure_state="user_cleared" if cleared else "reported_value",
        primary_fragment_id="original-fragment", source_version_id=binding.source_version_id,
        source_locator=binding.source_pointer, source_quote=row["source_text"],
        consumer_bindings=(binding,), review_state="user_modified" if edited else "candidate",
        user_edit={"request_id": "baseline-edit", "revision": 1, "basis": "合成测试",
            "saved_by": "test", "saved_at": "2026-10-07T00:00:00Z", "operation": "save"},
        **identity)
    return ActiveFactRevision(revision=1, request_id="baseline-edit",
        fact_revision_digest="b" * 64, facts=(fact,)), binding


@pytest.mark.parametrize("stat", ["MEAN", "STANDARD_DEVIATION"])
def test_study_only_scalar_edit_projects_without_guessing_product(stat) -> None:
    data = _data()
    row = next(r for r in data.baseline_views["facts"] if r["statistic_form"] == stat)
    before = deepcopy(data.model_dump(mode="json"))
    revision, binding = _revision(data, row)
    assert binding.product_id is None and binding.drug_name is None
    validate_active_fact_revision_b(data, revision)
    projected, consumers = _project_active_facts_b(data, revision)
    changed = next(r for r in projected.baseline_views["facts"] if r["row_id"] == row["row_id"])
    assert changed["value"] == 52.5 and changed["raw_value"] == "52.5"
    assert changed["source_text"] == row["source_text"]
    assert projected.user_edits[row["row_id"]].original_value == f"{row['value']:g} {row['unit']}"
    assert consumers[0].collection == "baseline"
    assert consumers[0].page_relative_path == "baseline-overview.html"
    assert data.model_dump(mode="json") == before


def test_baseline_clear_is_current_user_state_not_source_nonpublication() -> None:
    data = _data()
    row = next(r for r in data.baseline_views["facts"] if r["statistic_form"] == "MEAN")
    revision, _ = _revision(data, row, cleared=True)
    projected, _ = _project_active_facts_b(data, revision)
    current = next(r for r in projected.baseline_views["facts"] if r["row_id"] == row["row_id"])
    assert current["value"] is None and current["raw_value"] is None
    assert current["disclosure_state"] == "user_cleared"
    assert current["source_text"] == row["source_text"]
    assert projected.user_edits[row["row_id"]].current_value == "用户清除，待重新核实"


def test_baseline_source_projection_is_not_falsely_marked_user_modified() -> None:
    data = _data()
    row = next(r for r in data.baseline_views["facts"] if r["statistic_form"] == "MEAN")
    revision, _ = _revision(data, row, edited=False)
    projected, consumers = _project_active_facts_b(data, revision)
    assert not projected.user_edits and len(consumers) == 1
    assert projected.baseline_views == data.baseline_views


@pytest.mark.parametrize("number", [-1, float("inf"), float("nan")])
def test_invalid_spread_rejects_before_projection(number) -> None:
    data = _data()
    row = next(r for r in data.baseline_views["facts"]
               if r["statistic_form"] == "STANDARD_DEVIATION")
    revision, _ = _revision(data, row, number=number)
    with pytest.raises(ValueError):
        _project_active_facts_b(data, revision)


def test_unknown_product_permission_does_not_extend_to_b_effects() -> None:
    data = _data()
    row = next(r for r in data.baseline_views["facts"] if r["statistic_form"] == "MEAN")
    _, binding = _revision(data, row)
    with pytest.raises(ValueError):
        ActiveFactBinding.model_validate({**binding.model_dump(), "collection": "efficacy"})


def test_explicit_unknown_keys_and_precise_locator_are_still_required() -> None:
    data = _data()
    row = next(r for r in data.baseline_views["facts"] if r["statistic_form"] == "MEAN")
    revision, binding = _revision(data, row)
    payload = revision.facts[0].model_dump()
    payload.pop("product_id")
    with pytest.raises(ValueError, match="空值身份"):
        validate_active_fact_binding(ActiveFact.model_validate(payload), binding, binding)
    with pytest.raises(ValueError, match="source_pointer"):
        validate_active_fact_binding(revision.facts[0].model_copy(update={
            "source_locator": "$.wrong"}), binding, binding)
