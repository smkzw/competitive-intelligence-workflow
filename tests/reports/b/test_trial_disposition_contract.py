"""Task 6.7 B 类 trial_disposition_observation 强类型合同 RED 测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
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

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "schemas" / "trial-disposition-observation.schema.json"

_LOCATOR = EvidenceLocator(
    document_role="primary-trial-report",
    field_path="Table 14.1.1 participant disposition",
    table="受试者处置表",
    row="Treatment group",
    column="n (%)",
    page=19,
)


def _observation(**overrides: object) -> TrialDispositionObservation:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "row_id": "disposition-row-received-treatment",
        "source_row_id": "source-row-received-treatment",
        "observation_id": "disposition-observation-received-treatment",
        "product_id": "product-a",
        "trial_id": "trial-1",
        "period_id": "treatment-period-1",
        "cohort_id": "cohort-1",
        "scope_level": DispositionScopeLevel.GROUP,
        "group_id": "group-treatment",
        "analysis_population": "随机化人群",
        "field_family": DispositionFieldFamily.PARTICIPANT_FLOW,
        "field": DispositionField.RECEIVED_TREATMENT,
        "source_field_name": "Received treatment",
        "source_field_definition": "接受至少一次研究治疗的受试者",
        "measure_object": DispositionMeasureObject.SUBJECT,
        "statistic_form": DispositionStatisticForm.COUNT,
        "value": 100,
        "raw_value": "100",
        "unit": "例",
        "numerator": 100,
        "denominator": 118,
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
        "disclosure_state": FactDisclosureState.REPORTED_VALUE,
        "conflict_disposition": ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT,
        "reported_zero_text": None,
        "route_receipt_id": None,
        "applicability_predicate_id": None,
        "compatibility_rule": "trial-disposition-v1",
        "difference_labels_zh": (),
    }
    payload.update(overrides)
    return TrialDispositionObservation.model_validate(payload)


def test_disposition_enums_cover_field_families_levels_measurements_and_denominators() -> None:
    assert {member.value for member in DispositionFieldFamily} == {
        "participant_flow",
        "reason",
        "adherence",
        "rescue_treatment",
        "prohibited_medication",
        "protocol_deviation",
    }
    assert {
        "screened",
        "screen_failure",
        "randomized",
        "received_treatment",
        "completed_treatment",
        "completed_study",
        "treatment_discontinued",
        "study_withdrawal",
        "lost_to_follow_up",
        "screen_failure_reason",
        "treatment_discontinuation_reason",
        "study_withdrawal_reason",
        "adherence",
        "rescue_treatment",
        "prohibited_medication",
        "protocol_deviation",
        "major_protocol_deviation",
        "protocol_deviation_leading_to_exclusion",
        "source_other",
    } <= {member.value for member in DispositionField}
    assert {member.value for member in DispositionScopeLevel} == {
        "overall",
        "cohort",
        "group",
    }
    assert {member.value for member in DispositionMeasureObject} == {"subject", "event"}
    assert {
        "count",
        "event_count",
        "proportion",
        "adherence_summary",
        "other",
    } <= {member.value for member in DispositionStatisticForm}
    assert {
        "screened",
        "randomized",
        "treated",
        "safety",
        "analysis",
        "period_start",
        "other",
    } <= {member.value for member in DispositionDenominatorRole}


def test_participant_flow_keeps_treatment_and_study_completion_and_exit_distinct() -> None:
    completed_treatment = _observation(
        field=DispositionField.COMPLETED_TREATMENT,
        value=94,
        numerator=94,
        raw_value="94",
    )
    completed_study = _observation(
        field=DispositionField.COMPLETED_STUDY,
        value=90,
        numerator=90,
        raw_value="90",
    )
    stopped_treatment = _observation(
        field=DispositionField.TREATMENT_DISCONTINUED,
        value=6,
        numerator=6,
        raw_value="6",
    )
    withdrew_study = _observation(
        field=DispositionField.STUDY_WITHDRAWAL,
        value=8,
        numerator=8,
        raw_value="8",
    )

    assert completed_treatment.measure_object is DispositionMeasureObject.SUBJECT
    assert completed_study.measure_object is DispositionMeasureObject.SUBJECT
    assert completed_treatment.field is not completed_study.field
    assert stopped_treatment.field is not withdrew_study.field
    assert completed_treatment.identity_key != completed_study.identity_key
    assert stopped_treatment.identity_key != withdrew_study.identity_key

    with pytest.raises(ValidationError, match="受试者|事件数"):
        _observation(
            field=DispositionField.COMPLETED_STUDY,
            measure_object=DispositionMeasureObject.EVENT,
            statistic_form=DispositionStatisticForm.EVENT_COUNT,
        )


def test_subject_and_event_protocol_deviation_counts_never_collapse() -> None:
    subject_count = _observation(
        field_family=DispositionFieldFamily.PROTOCOL_DEVIATION,
        field=DispositionField.PROTOCOL_DEVIATION,
        value=6,
        raw_value="6例",
        numerator=6,
        measure_object=DispositionMeasureObject.SUBJECT,
        statistic_form=DispositionStatisticForm.COUNT,
        protocol_deviation_level="major",
    )
    event_count = _observation(
        field_family=DispositionFieldFamily.PROTOCOL_DEVIATION,
        field=DispositionField.PROTOCOL_DEVIATION,
        value=8,
        raw_value="8 events",
        numerator=8,
        measure_object=DispositionMeasureObject.EVENT,
        statistic_form=DispositionStatisticForm.EVENT_COUNT,
        protocol_deviation_level="major",
    )
    major = _observation(
        field_family=DispositionFieldFamily.PROTOCOL_DEVIATION,
        field=DispositionField.MAJOR_PROTOCOL_DEVIATION,
        value=6,
        raw_value="6例",
        numerator=6,
        protocol_deviation_level="major",
    )
    leading_to_exclusion = _observation(
        field_family=DispositionFieldFamily.PROTOCOL_DEVIATION,
        field=DispositionField.PROTOCOL_DEVIATION_LEADING_TO_EXCLUSION,
        value=2,
        raw_value="2例",
        numerator=2,
        protocol_deviation_level="leading_to_exclusion",
    )

    assert subject_count.value == 6
    assert event_count.value == 8
    assert subject_count.measure_object is DispositionMeasureObject.SUBJECT
    assert event_count.measure_object is DispositionMeasureObject.EVENT
    assert subject_count.statistic_form is DispositionStatisticForm.COUNT
    assert event_count.statistic_form is DispositionStatisticForm.EVENT_COUNT
    assert subject_count.identity_key != event_count.identity_key
    assert major.field is not leading_to_exclusion.field
    assert major.protocol_deviation_level != leading_to_exclusion.protocol_deviation_level

    with pytest.raises(ValidationError, match="事件|整数"):
        _observation(
            field_family=DispositionFieldFamily.PROTOCOL_DEVIATION,
            field=DispositionField.PROTOCOL_DEVIATION,
            value=8.5,
            raw_value="8.5 events",
            numerator=None,
            measure_object=DispositionMeasureObject.EVENT,
            statistic_form=DispositionStatisticForm.EVENT_COUNT,
            protocol_deviation_level="major",
        )


def test_screen_failure_stays_in_screening_scope_and_group_semantics_are_closed() -> None:
    screened = _observation(
        field=DispositionField.SCREENED,
        scope_level=DispositionScopeLevel.OVERALL,
        cohort_id=None,
        group_id=None,
        analysis_population="筛选总体",
        value=240,
        raw_value="240",
        numerator=None,
        denominator=None,
        denominator_role=DispositionDenominatorRole.SCREENED,
    )
    screen_failure = _observation(
        field=DispositionField.SCREEN_FAILURE,
        scope_level=DispositionScopeLevel.OVERALL,
        cohort_id=None,
        group_id=None,
        analysis_population="筛选总体",
        value=42,
        raw_value="42",
        numerator=42,
        denominator=240,
        denominator_role=DispositionDenominatorRole.SCREENED,
    )

    assert screened.group_id is None
    assert screen_failure.group_id is None
    assert screen_failure.denominator_role is DispositionDenominatorRole.SCREENED

    with pytest.raises(ValidationError, match="筛败|筛选|组别"):
        _observation(
            field=DispositionField.SCREEN_FAILURE,
            scope_level=DispositionScopeLevel.GROUP,
            group_id="group-treatment",
            analysis_population="随机化人群",
            denominator_role=DispositionDenominatorRole.RANDOMIZED,
        )
    with pytest.raises(ValidationError, match="组别|总体"):
        _observation(
            field=DispositionField.COMPLETED_STUDY,
            scope_level=DispositionScopeLevel.OVERALL,
            cohort_id=None,
            group_id="group-treatment",
        )
    with pytest.raises(ValidationError, match="组别"):
        _observation(
            scope_level=DispositionScopeLevel.GROUP,
            group_id=None,
        )


def test_reason_observation_preserves_original_canonical_and_three_state_semantics() -> None:
    reason = _observation(
        field_family=DispositionFieldFamily.REASON,
        field=DispositionField.TREATMENT_DISCONTINUATION_REASON,
        source_field_name="Reason for treatment discontinuation",
        source_field_definition="受试者停止治疗的主要原因分类",
        value=3,
        raw_value="3",
        numerator=3,
        reason_original_text="Adverse event",
        canonical_reason="不良事件",
        reason_is_mutually_exclusive=True,
        reason_is_exhaustive=False,
    )
    source_did_not_state = _observation(
        field_family=DispositionFieldFamily.REASON,
        field=DispositionField.STUDY_WITHDRAWAL_REASON,
        source_field_name="Reason for withdrawal",
        source_field_definition="退出研究的来源原因分类",
        value=2,
        raw_value="2",
        numerator=2,
        reason_original_text="Other",
        canonical_reason="其他",
        reason_is_mutually_exclusive=None,
        reason_is_exhaustive=None,
    )

    assert reason.reason_original_text == "Adverse event"
    assert reason.canonical_reason == "不良事件"
    assert reason.reason_is_mutually_exclusive is True
    assert reason.reason_is_exhaustive is False
    assert source_did_not_state.reason_is_mutually_exclusive is None
    assert source_did_not_state.reason_is_exhaustive is None
    assert source_did_not_state.reason_original_text == "Other"

    with pytest.raises(ValidationError, match="原因原文|规范原因"):
        _observation(
            field_family=DispositionFieldFamily.REASON,
            field=DispositionField.TREATMENT_DISCONTINUATION_REASON,
            reason_original_text=None,
        )
    with pytest.raises(ValidationError, match="原因原文|规范原因"):
        _observation(
            field_family=DispositionFieldFamily.REASON,
            field=DispositionField.TREATMENT_DISCONTINUATION_REASON,
            canonical_reason=None,
        )


def test_adherence_requires_definition_and_threshold_and_keeps_implementation_fields() -> None:
    adherence = _observation(
        field_family=DispositionFieldFamily.ADHERENCE,
        field=DispositionField.ADHERENCE,
        source_field_name="Treatment compliance",
        source_field_definition="按计划给药完成比例",
        statistic_form=DispositionStatisticForm.ADHERENCE_SUMMARY,
        value=80.0,
        raw_value="80%",
        unit="%",
        numerator=94,
        denominator=118,
        denominator_role=DispositionDenominatorRole.TREATED,
        adherence_definition="完成至少80%的计划给药",
        adherence_threshold=">=80%",
    )
    rescue = _observation(
        field_family=DispositionFieldFamily.RESCUE_TREATMENT,
        field=DispositionField.RESCUE_TREATMENT,
        source_field_name="Rescue medication",
        source_field_definition="使用补救治疗的受试者",
        denominator_role=DispositionDenominatorRole.TREATED,
    )
    prohibited = _observation(
        field_family=DispositionFieldFamily.PROHIBITED_MEDICATION,
        field=DispositionField.PROHIBITED_MEDICATION,
        source_field_name="Prohibited medication",
        source_field_definition="使用方案禁止药物的受试者",
        denominator_role=DispositionDenominatorRole.SAFETY,
    )

    assert adherence.statistic_form is DispositionStatisticForm.ADHERENCE_SUMMARY
    assert adherence.adherence_definition == "完成至少80%的计划给药"
    assert adherence.adherence_threshold == ">=80%"
    assert rescue.field_family is DispositionFieldFamily.RESCUE_TREATMENT
    assert prohibited.field_family is DispositionFieldFamily.PROHIBITED_MEDICATION

    with pytest.raises(ValidationError, match="依从性|定义|阈值"):
        _observation(
            field_family=DispositionFieldFamily.ADHERENCE,
            field=DispositionField.ADHERENCE,
            adherence_definition=None,
        )
    with pytest.raises(ValidationError, match="依从性|定义|阈值"):
        _observation(
            field_family=DispositionFieldFamily.ADHERENCE,
            field=DispositionField.ADHERENCE,
            adherence_threshold=None,
        )


def test_counts_and_proportions_reject_impossible_values_without_bool_coercion() -> None:
    with pytest.raises(ValidationError, match="不得为负数|非负"):
        _observation(value=-1, raw_value="-1", numerator=-1)
    with pytest.raises(ValidationError, match="比例|范围"):
        _observation(
            field_family=DispositionFieldFamily.RESCUE_TREATMENT,
            field=DispositionField.RESCUE_TREATMENT,
            statistic_form=DispositionStatisticForm.PROPORTION,
            value=101.0,
            raw_value="101%",
            unit="%",
            numerator=101,
            denominator=100,
        )
    with pytest.raises(ValidationError, match="分母|正"):
        _observation(numerator=1, denominator=0)
    with pytest.raises(ValidationError, match="分子|分母"):
        _observation(numerator=119, denominator=118)
    with pytest.raises(ValidationError, match="布尔|整数"):
        _observation(value=True, raw_value="true", numerator=True)


def test_event_count_can_exceed_a_participant_denominator_without_becoming_a_rate() -> None:
    events = _observation(
        field_family=DispositionFieldFamily.PROTOCOL_DEVIATION,
        field=DispositionField.PROTOCOL_DEVIATION,
        measure_object=DispositionMeasureObject.EVENT,
        statistic_form=DispositionStatisticForm.EVENT_COUNT,
        value=5,
        raw_value="5次",
        numerator=5,
        denominator=2,
        denominator_role=DispositionDenominatorRole.TREATED,
        protocol_deviation_level="all",
    )

    assert events.value == 5
    assert events.denominator == 2
    assert events.recomputed_proportion is None


def test_canonical_field_and_field_family_mismatch_fails_closed() -> None:
    with pytest.raises(ValidationError, match="字段族|不匹配"):
        _observation(
            field_family=DispositionFieldFamily.REASON,
            field=DispositionField.RECEIVED_TREATMENT,
        )


def test_proportion_recomputes_only_from_explicit_numerator_and_denominator() -> None:
    exact = _observation(
        field_family=DispositionFieldFamily.RESCUE_TREATMENT,
        field=DispositionField.RESCUE_TREATMENT,
        statistic_form=DispositionStatisticForm.PROPORTION,
        value=60.0,
        raw_value="60%",
        unit="%",
        numerator=6,
        denominator=10,
        denominator_role=DispositionDenominatorRole.TREATED,
    )
    source_mismatch = _observation(
        field_family=DispositionFieldFamily.RESCUE_TREATMENT,
        field=DispositionField.RESCUE_TREATMENT,
        statistic_form=DispositionStatisticForm.PROPORTION,
        value=50.0,
        raw_value="50%",
        unit="%",
        numerator=6,
        denominator=10,
        denominator_role=DispositionDenominatorRole.TREATED,
    )
    reported_without_denominator = _observation(
        field_family=DispositionFieldFamily.RESCUE_TREATMENT,
        field=DispositionField.RESCUE_TREATMENT,
        statistic_form=DispositionStatisticForm.PROPORTION,
        value=60.0,
        raw_value="60%",
        unit="%",
        numerator=None,
        denominator=None,
    )
    count_without_denominator = _observation(
        value=6,
        raw_value="6例",
        unit="例",
        numerator=None,
        denominator=None,
    )

    assert exact.recomputed_proportion == pytest.approx(60.0)
    assert source_mismatch.value == 50.0
    assert source_mismatch.recomputed_proportion == pytest.approx(60.0)
    assert any(
        "来源比例" in label and "复算" in label
        for label in source_mismatch.difference_labels_zh
    )
    assert reported_without_denominator.recomputed_proportion is None
    assert count_without_denominator.recomputed_proportion is None


def test_reported_zero_is_explicit_and_missing_is_never_synthesized_as_zero() -> None:
    zero = _observation(
        value=0,
        raw_value="0例",
        numerator=0,
        denominator=118,
        disclosure_state=FactDisclosureState.REPORTED_ZERO,
        reported_zero_text="0例",
    )

    assert zero.value == 0
    assert zero.disclosure_state is FactDisclosureState.REPORTED_ZERO
    assert zero.reported_zero_text == "0例"

    with pytest.raises(ValidationError, match="零|reported_zero"):
        _observation(
            value=0,
            raw_value="0例",
            numerator=0,
            disclosure_state=FactDisclosureState.REPORTED_VALUE,
            reported_zero_text=None,
        )
    with pytest.raises(ValidationError, match="零值原文|零值证据"):
        _observation(
            value=0,
            raw_value="0例",
            numerator=0,
            denominator=118,
            disclosure_state=FactDisclosureState.REPORTED_ZERO,
            reported_zero_text="来源原文未包含明确数值",
        )


def test_stable_identity_uses_scientific_dimensions_not_observed_value_or_source_metadata() -> None:
    baseline = _observation()
    changed_value = _observation(value=92, numerator=92, raw_value="92")
    changed_source = _observation(
        source_row_id="source-row-received-treatment-v2",
        source_version_id="source-version-2",
        source_locator=EvidenceLocator(
            document_role="clinical-trial-registry",
            field_path="Results.participantFlow",
            table="受试者处置表",
            row="Treatment group",
            column="n",
            page=20,
        ),
        review_state=FactReviewState.CANDIDATE,
        difference_labels_zh=("来源版本不同",),
    )
    changed_window = _observation(time_window="整个研究期")
    changed_denominator = _observation(denominator_role=DispositionDenominatorRole.TREATED)
    changed_unit = _observation(unit="人")
    assert baseline.row_id == baseline.identity_key
    assert baseline.identity_key == changed_value.identity_key
    assert baseline.identity_key == changed_source.identity_key
    assert baseline.identity_key != changed_window.identity_key
    assert baseline.identity_key != changed_denominator.identity_key
    assert baseline.identity_key != changed_unit.identity_key
    assert baseline.row_id != changed_window.row_id


def test_public_validation_rejects_model_copy_tampering_and_recomputes_identity() -> None:
    original = _observation()
    forged_scope = original.model_copy(update={"group_id": "group-control"})
    validated_scope = validate_trial_disposition_observation(forged_scope)
    assert validated_scope.group_id == "group-control"
    assert validated_scope.row_id != original.row_id

    forged_disclosure = original.model_copy(
        update={
            "disclosure_state": FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
            "value": 100,
            "numerator": 100,
            "denominator": 118,
        }
    )
    with pytest.raises((ValidationError, ValueError), match="重新校验|未公开|披露"):
        validate_trial_disposition_observation(forged_disclosure)

    unknown = original.model_copy(update={"unknown_field": "forged"})
    with pytest.raises((ValidationError, ValueError), match="重新校验|extra|未知"):
        validate_trial_disposition_observation(unknown)


def test_trial_disposition_json_schema_matches_model_and_fails_closed() -> None:
    assert SCHEMA_PATH.exists(), "Task 6.7 必须提供 trial-disposition-observation.schema.json"
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    payload = _observation().model_dump(mode="json")
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    assert not errors, [error.message for error in errors]

    unknown = dict(payload)
    unknown["unknown_field"] = "must fail closed"
    assert list(validator.iter_errors(unknown)), "JSON Schema 必须拒绝未知字段"

    invalid_field = dict(payload)
    invalid_field["field"] = "invented_disposition_field"
    assert list(validator.iter_errors(invalid_field)), "JSON Schema 必须拒绝自由文本字段名"

    mismatched_family = dict(payload)
    mismatched_family["field_family"] = "reason"
    assert list(validator.iter_errors(mismatched_family)), "JSON Schema 必须拒绝字段族错配"

    for raw_zero in (0, "0", "0例"):
        unpublished = dict(payload)
        unpublished.update(
            disclosure_state="not_publicly_disclosed",
            value=None,
            numerator=None,
            denominator=None,
            raw_value=raw_zero,
        )
        assert list(validator.iter_errors(unpublished)), "未公开状态不得在原始值中伪装零"
