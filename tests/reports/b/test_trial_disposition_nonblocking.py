"""Task 6.7 处置数值缺失的非阻断披露 RED 测试。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.gates.models import (
    ConflictDisposition,
    DisclosureMaturity,
    SourceRole,
)
from ci_workflow.reports.b.disposition import (
    DispositionDenominatorRole,
    DispositionField,
    DispositionFieldFamily,
    DispositionMeasureObject,
    DispositionScopeLevel,
    DispositionStatisticForm,
    TrialDispositionObservation,
    validate_trial_disposition_observation,
)

_LOCATOR = EvidenceLocator(
    document_role="primary-trial-report",
    field_path="Table 14.1.1 participant disposition",
    table="受试者处置表",
    row="Treatment group",
    column="n (%)",
    page=19,
)

_NON_CONCRETE_STATES = (
    FactDisclosureState.NOT_REPORTED,
    FactDisclosureState.BELOW_REPORTING_THRESHOLD,
    FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
    FactDisclosureState.NOT_APPLICABLE,
    FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
)


def _observation(**overrides: object) -> TrialDispositionObservation:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "row_id": "disposition-row-missing",
        "source_row_id": "source-row-missing",
        "observation_id": "disposition-observation-missing",
        "product_id": "product-a",
        "trial_id": "trial-1",
        "period_id": "treatment-period-1",
        "cohort_id": "cohort-1",
        "scope_level": DispositionScopeLevel.GROUP,
        "group_id": "group-treatment",
        "analysis_population": "随机化人群",
        "field_family": DispositionFieldFamily.PARTICIPANT_FLOW,
        "field": DispositionField.COMPLETED_TREATMENT,
        "source_field_name": "Completed treatment",
        "source_field_definition": "完成预定治疗的受试者",
        "measure_object": DispositionMeasureObject.SUBJECT,
        "statistic_form": DispositionStatisticForm.COUNT,
        "value": None,
        "raw_value": "来源未报告",
        "unit": None,
        "numerator": None,
        "denominator": None,
        "denominator_role": DispositionDenominatorRole.RANDOMIZED,
        "time_window": "治疗期（第1天至第12周）",
        "reason_original_text": None,
        "canonical_reason": None,
        "reason_is_mutually_exclusive": None,
        "reason_is_exhaustive": None,
        "adherence_definition": None,
        "adherence_threshold": None,
        "protocol_deviation_level": None,
        "source_version_id": "source-version-1",
        "source_locator": _LOCATOR,
        "source_role": SourceRole.PRIMARY_TRIAL_REPORT,
        "disclosure_maturity": DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT,
        "review_state": FactReviewState.ACCEPTED,
        "disclosure_state": FactDisclosureState.NOT_REPORTED,
        "conflict_disposition": ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT,
        "reported_zero_text": None,
        "route_receipt_id": None,
        "applicability_predicate_id": None,
        "compatibility_rule": "trial-disposition-v1",
        "difference_labels_zh": (),
    }
    payload.update(overrides)
    return TrialDispositionObservation.model_validate(payload)


def _state_overrides(state: FactDisclosureState) -> dict[str, Any]:
    if state is FactDisclosureState.BELOW_REPORTING_THRESHOLD:
        return {"raw_value": "<5%"}
    if state is FactDisclosureState.NOT_PUBLICLY_DISCLOSED:
        return {"raw_value": "来源未公开"}
    if state is FactDisclosureState.NOT_APPLICABLE:
        return {
            "raw_value": "不适用",
            "applicability_predicate_id": "disposition-not-applicable-v1",
        }
    if state is FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE:
        return {
            "raw_value": "当前技术路径未解决",
            "route_receipt_id": "receipt-disposition-1",
        }
    return {"raw_value": "来源未报告"}


@pytest.mark.parametrize("state", _NON_CONCRETE_STATES)
def test_missing_disposition_numbers_are_structured_nonblocking_and_not_zero(
    state: FactDisclosureState,
) -> None:
    observation = _observation(disclosure_state=state, **_state_overrides(state))

    assert isinstance(observation.disclosure_state, FactDisclosureState)
    assert observation.disclosure_state is state
    assert observation.value is None
    assert observation.numerator is None
    assert observation.denominator is None
    assert observation.recomputed_proportion is None
    assert observation.value != 0


@pytest.mark.parametrize("state", _NON_CONCRETE_STATES)
def test_non_concrete_disclosure_states_reject_numeric_payloads_instead_of_coercing_them(
    state: FactDisclosureState,
) -> None:
    overrides = _state_overrides(state)
    overrides.update(
        {
            "value": 0,
            "raw_value": "0例",
            "unit": "例",
            "numerator": 0,
            "denominator": 118,
        }
    )
    with pytest.raises(ValidationError, match="未报告|未公开|阈值|不适用|路线|数值|分母|披露"):
        _observation(disclosure_state=state, **overrides)


@pytest.mark.parametrize("raw_value", ("n=0", "0/118", "0 (0%)", "低于5%", "未达到5%"))
def test_not_publicly_disclosed_rejects_embedded_numeric_raw_text(raw_value: str) -> None:
    with pytest.raises(ValidationError, match="未公开|数值型原始表达"):
        _observation(
            disclosure_state=FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
            raw_value=raw_value,
        )


@pytest.mark.parametrize(
    ("unit", "value"),
    (("percent", 101.0), ("percentage", 101.0), ("ratio", 1.5)),
)
def test_adherence_summary_obeys_explicit_proportion_unit_range(
    unit: str,
    value: float,
) -> None:
    with pytest.raises(ValidationError, match="依从性比例|范围"):
        _observation(
            field_family=DispositionFieldFamily.ADHERENCE,
            field=DispositionField.ADHERENCE,
            source_field_name="Treatment compliance",
            source_field_definition="治疗依从性",
            statistic_form=DispositionStatisticForm.ADHERENCE_SUMMARY,
            value=value,
            raw_value=f"{value}{unit}",
            unit=unit,
            numerator=1,
            denominator=2,
            adherence_definition="达到方案规定的用药依从性",
            adherence_threshold="按来源定义",
            disclosure_state=FactDisclosureState.REPORTED_VALUE,
        )


def test_model_copy_cannot_turn_not_publicly_disclosed_into_a_numeric_zero() -> None:
    missing = _observation(
        disclosure_state=FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        raw_value="来源未公开",
    )
    forged = missing.model_copy(
        update={
            "value": 0,
            "raw_value": "0例",
            "numerator": 0,
            "denominator": 118,
        }
    )

    with pytest.raises((ValidationError, ValueError), match="重新校验|未公开|数值|披露"):
        validate_trial_disposition_observation(forged)


def test_nonblocking_reason_adherence_and_pd_do_not_require_undisclosed_metadata() -> None:
    reason = _observation(
        field_family=DispositionFieldFamily.REASON,
        field=DispositionField.STUDY_WITHDRAWAL_REASON,
        source_field_name="Reason for withdrawal",
        source_field_definition="退出研究的来源原因分类",
        disclosure_state=FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        raw_value="来源未公开",
    )
    adherence = _observation(
        field_family=DispositionFieldFamily.ADHERENCE,
        field=DispositionField.ADHERENCE,
        source_field_name="Treatment compliance",
        source_field_definition="治疗依从性",
        disclosure_state=FactDisclosureState.NOT_REPORTED,
        raw_value="来源未报告",
    )
    protocol_deviation = _observation(
        field_family=DispositionFieldFamily.PROTOCOL_DEVIATION,
        field=DispositionField.PROTOCOL_DEVIATION,
        source_field_name="Protocol deviation",
        source_field_definition="方案偏离",
        disclosure_state=FactDisclosureState.NOT_REPORTED,
        raw_value="来源未报告",
    )

    assert reason.reason_original_text is None
    assert reason.canonical_reason is None
    assert adherence.adherence_definition is None
    assert adherence.adherence_threshold is None
    assert protocol_deviation.protocol_deviation_level is None


def test_route_unresolved_and_not_applicable_keep_distinct_reasons_from_not_public() -> None:
    unresolved = _observation(
        disclosure_state=FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
        raw_value="当前技术路径未解决",
        route_receipt_id="receipt-disposition-1",
    )
    not_applicable = _observation(
        disclosure_state=FactDisclosureState.NOT_APPLICABLE,
        raw_value="不适用",
        applicability_predicate_id="disposition-not-applicable-v1",
    )
    not_public = _observation(
        disclosure_state=FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        raw_value="来源未公开",
    )

    assert unresolved.disclosure_state is FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE
    assert unresolved.route_receipt_id == "receipt-disposition-1"
    assert not_applicable.disclosure_state is FactDisclosureState.NOT_APPLICABLE
    assert not_applicable.applicability_predicate_id == "disposition-not-applicable-v1"
    assert not_public.disclosure_state is FactDisclosureState.NOT_PUBLICLY_DISCLOSED
    assert not_public.route_receipt_id is None
    assert not_public.applicability_predicate_id is None


def test_conflicting_disposition_uses_shared_fact_state_and_stays_non_numeric_when_unresolved(
) -> None:
    conflicting = _observation(
        disclosure_state=FactDisclosureState.CONFLICTING,
        raw_value="两个来源对完成治疗人数的口径冲突",
        conflict_disposition=ConflictDisposition.OPEN_CONFLICT_PRESERVED,
    )

    assert conflicting.disclosure_state is FactDisclosureState.CONFLICTING
    assert conflicting.conflict_disposition is ConflictDisposition.OPEN_CONFLICT_PRESERVED
    assert conflicting.value is None
    assert conflicting.numerator is None
    assert conflicting.denominator is None

    with pytest.raises(ValidationError, match="冲突|处置"):
        _observation(
            disclosure_state=FactDisclosureState.CONFLICTING,
            raw_value="来源冲突",
            conflict_disposition=ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT,
        )


def test_reported_zero_is_concrete_only_when_source_zero_evidence_is_present() -> None:
    zero = _observation(
        disclosure_state=FactDisclosureState.REPORTED_ZERO,
        value=0,
        raw_value="0例",
        unit="例",
        numerator=0,
        denominator=118,
        reported_zero_text="0例",
    )

    assert zero.disclosure_state is FactDisclosureState.REPORTED_ZERO
    assert zero.value == 0
    assert zero.reported_zero_text == "0例"

    with pytest.raises(ValidationError, match="零|reported_zero|来源"):
        _observation(
            disclosure_state=FactDisclosureState.REPORTED_ZERO,
            value=0,
            raw_value=None,
            unit="例",
            numerator=0,
            denominator=118,
            reported_zero_text=None,
        )
