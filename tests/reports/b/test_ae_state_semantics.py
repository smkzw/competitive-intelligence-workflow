"""Task 6.3 B 类安全性事实披露、谱系与术语语义合同。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ci_workflow.domain.enums import FactDisclosureState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.reports.b.safety import (
    SafetyArmRole,
    SafetyFactRow,
    SafetyFamily,
    SafetyTechnicalStatus,
    SafetyTermMapping,
    SafetyTermMappingConfidence,
    SafetyViewError,
    disclosure_state_label_zh,
    validate_safety_fact_row,
)

_LOCATOR = EvidenceLocator(
    document_role="trial-results",
    table="Table 14.3.1",
    row="headache",
    column="treatment",
)


def _fact(
    row_id: str = "row-headache-treatment",
    *,
    state: FactDisclosureState = FactDisclosureState.REPORTED_VALUE,
    value: float | None = 12.0,
    raw_value: str | None = "12%",
    source_term: str = "Headache",
    term_mapping: SafetyTermMapping | dict[str, object] | None = None,
    **updates: object,
) -> SafetyFactRow:
    payload: dict[str, object] = {
        "row_id": row_id,
        "source_row_id": f"source-{row_id}",
        "observation_id": f"observation-{row_id}",
        "product_id": "product-a",
        "trial_id": "NCT00000001",
        "family": SafetyFamily.COMMON_AE,
        "term_id": "headache",
        "source_term": source_term,
        "event_definition_zh": "治疗期间出现的不良事件",
        "time_window_zh": "治疗期间",
        "analysis_population_zh": "安全性分析集",
        "arm_role": SafetyArmRole.TREATMENT,
        "arm_id": "arm-treatment",
        "arm_label": "治疗组",
        "value": value,
        "raw_value": raw_value,
        "unit": "%",
        "denominator": 100,
        "disclosure_state": state,
        "source_version_id": "source-version-1",
        "source_locator": _LOCATOR,
    }
    if term_mapping is not None:
        payload["term_mapping"] = term_mapping
    payload.update(updates)
    return SafetyFactRow.model_validate(payload)


def test_all_disclosure_states_have_distinct_labels_and_keep_non_values_non_numeric() -> None:
    states = (
        FactDisclosureState.REPORTED_VALUE,
        FactDisclosureState.REPORTED_ZERO,
        FactDisclosureState.NOT_REPORTED,
        FactDisclosureState.BELOW_REPORTING_THRESHOLD,
        FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        FactDisclosureState.NOT_APPLICABLE,
        FactDisclosureState.CONFLICTING,
        FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
    )
    labels = {
        disclosure_state_label_zh(state)
        for state in states
    }
    assert len(labels) == len(states)

    assert _fact().has_numeric_value
    assert _fact(
        state=FactDisclosureState.REPORTED_ZERO,
        value=0,
        raw_value="0%",
    ).has_numeric_value
    assert not _fact(
        state=FactDisclosureState.NOT_REPORTED,
        value=None,
        raw_value="结果未报告",
    ).has_numeric_value
    assert _fact(
        state=FactDisclosureState.BELOW_REPORTING_THRESHOLD,
        value=None,
        raw_value="<5%",
    ).display_value_zh == "<5%"
    assert not _fact(
        state=FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        value=None,
        raw_value="来源尚未公开",
    ).is_colorable
    assert not _fact(
        state=FactDisclosureState.NOT_APPLICABLE,
        value=None,
        raw_value="该事件不适用",
        applicability_predicate_id="aesi-not-applicable-v1",
    ).is_colorable
    assert not _fact(
        state=FactDisclosureState.CONFLICTING,
        value=None,
        raw_value="来源值存在差异",
    ).is_colorable
    technical = _fact(
        state=FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
        value=None,
        raw_value="当前路径未能核实",
        technical_status=SafetyTechnicalStatus.ACCESS_BLOCKED,
        technical_diagnostic="官方页面访问受限",
        unresolved_route_receipt_id="receipt-1",
    )
    assert technical.is_technical_anomaly
    assert not technical.is_colorable


def test_reported_value_and_reported_zero_require_consistent_numeric_values() -> None:
    with pytest.raises(ValidationError, match="reported_value|确定零值"):
        _fact(value=None, raw_value="结果未报告")

    with pytest.raises(ValidationError, match="reported_zero.*零值|零值"):
        _fact(state=FactDisclosureState.REPORTED_ZERO, value=2, raw_value="2%")

    with pytest.raises(ValidationError, match="reported_zero|零值"):
        _fact(state=FactDisclosureState.REPORTED_ZERO, value=0, raw_value="未报告")

    with pytest.raises(ValidationError, match="reported_zero|零值"):
        _fact(state=FactDisclosureState.REPORTED_ZERO, value=0, raw_value=None)

    with pytest.raises(ValidationError, match="确定零值"):
        _fact(state=FactDisclosureState.REPORTED_VALUE, value=0, raw_value="0%")

    with pytest.raises(ValidationError, match="非数值披露状态"):
        _fact(state=FactDisclosureState.NOT_REPORTED, value=1.0, raw_value="1%")

    with pytest.raises(ValidationError, match="数值型原始表达"):
        _fact(state=FactDisclosureState.NOT_PUBLICLY_DISCLOSED, value=None, raw_value="12%")


def test_threshold_is_source_text_not_a_hidden_numeric_value() -> None:
    threshold = _fact(
        state=FactDisclosureState.BELOW_REPORTING_THRESHOLD,
        value=None,
        raw_value="<5%",
    )
    assert threshold.raw_value == "<5%"
    assert threshold.numeric_value is None
    assert threshold.display_value_zh == "<5%"

    with pytest.raises(ValidationError, match="阈值原文"):
        _fact(
            state=FactDisclosureState.BELOW_REPORTING_THRESHOLD,
            value=None,
            raw_value="未报告",
        )


def test_technical_route_failure_is_separate_from_scientific_non_reporting() -> None:
    with pytest.raises(ValidationError, match="路由回执"):
        _fact(
            state=FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
            value=None,
            raw_value="访问失败",
            technical_status=SafetyTechnicalStatus.ACCESS_BLOCKED,
        )

    with pytest.raises(ValidationError, match="独立技术诊断"):
        _fact(
            state=FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
            value=None,
            raw_value="访问失败",
            unresolved_route_receipt_id="receipt-1",
        )

    with pytest.raises(ValidationError, match="技术异常必须使用"):
        _fact(
            state=FactDisclosureState.NOT_REPORTED,
            value=None,
            raw_value="公开材料未列示",
            technical_status=SafetyTechnicalStatus.ACCESS_BLOCKED,
            technical_diagnostic="访问受限",
        )

    not_reported = _fact(
        state=FactDisclosureState.NOT_REPORTED,
        value=None,
        raw_value="公开材料未列示",
    )
    unresolved = _fact(
        state=FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
        value=None,
        raw_value="访问失败",
        technical_status=SafetyTechnicalStatus.ACCESS_BLOCKED,
        unresolved_route_receipt_id="receipt-1",
    )
    assert not_reported.disclosure_state is FactDisclosureState.NOT_REPORTED
    assert unresolved.disclosure_state is FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE
    assert unresolved.technical_status is SafetyTechnicalStatus.ACCESS_BLOCKED


def test_source_version_row_and_precise_locator_form_immutable_lineage() -> None:
    fact = _fact()
    assert fact.source_version_id == "source-version-1"
    assert fact.source_row_id == "source-row-headache-treatment"
    assert fact.source_locator == _LOCATOR
    assert fact.provenance.source_version_id == fact.source_version_id
    assert fact.provenance.source_row_id == fact.source_row_id
    assert fact.provenance.source_locator == _LOCATOR

    nested = _fact(
        source_lineage={
            "source_version_id": "source-version-2",
            "source_row_id": "source-nested",
            "source_locator": _LOCATOR,
        },
        source_version_id="source-version-2",
        source_row_id="source-nested",
    )
    assert nested.provenance.source_row_id == "source-nested"

    forged = fact.model_copy(update={"source_version_id": "forged-version"})
    with pytest.raises(SafetyViewError, match="重新校验|来源谱系"):
        validate_safety_fact_row(forged)


def test_reliable_term_mapping_is_additive_and_uncertain_mapping_stays_separate() -> None:
    reliable = _fact(
        term_mapping={
            "source_term": "Headache",
            "preferred_term": "Headache",
            "source_language": "en",
            "meddra_version": "27.1",
            "mapping_method": "MedDRA 字典精确匹配",
            "confidence": "high",
        }
    )
    assert reliable.source_term == "Headache"
    assert reliable.standard_term == "Headache"
    assert reliable.mapping_is_reliable
    assert reliable.comparison_term == "Headache"
    assert "Headache" in reliable.display_term
    assert reliable.term_mapping is not None
    assert reliable.term_mapping.source_term == reliable.source_term

    uncertain = _fact(
        row_id="row-headache-uncertain",
        term_mapping={
            "source_term": "头痛/头晕",
            "preferred_term": "Headache",
            "source_language": "zh",
            "meddra_version": "27.1",
            "mapping_method": "人工候选匹配",
            "confidence": SafetyTermMappingConfidence.UNCERTAIN,
        },
        source_term="头痛/头晕",
        term_id="头痛/头晕",
    )
    assert uncertain.standard_term == "Headache"
    assert not uncertain.mapping_is_reliable
    assert uncertain.comparison_term == "头痛/头晕"
    assert "头痛/头晕" in uncertain.display_term
    assert "待核实" in uncertain.display_term

    with pytest.raises(ValidationError, match="映射|规范术语"):
        _fact(source_term="Headache", standard_term="Headache")

    with pytest.raises(ValidationError, match="映射来源术语"):
        _fact(
            term_mapping={
                "source_term": "Dizziness",
                "preferred_term": "Dizziness",
                "meddra_version": "27.1",
                "mapping_method": "字典精确匹配",
                "confidence": "high",
            }
        )


def test_model_copy_tampering_is_rejected_after_revalidation() -> None:
    fact = _fact()
    forged = fact.model_copy(
        update={"value": None, "disclosure_state": FactDisclosureState.REPORTED_VALUE}
    )
    with pytest.raises(SafetyViewError, match="重新校验"):
        validate_safety_fact_row(forged)


def test_aliases_do_not_change_the_original_safety_semantics() -> None:
    fact = SafetyFactRow.model_validate(
        {
            "id": "row-alias",
            "source_row": "source-alias",
            "project_id": "product-a",
            "study_id": "NCT00000001",
            "safety_family": "common_teae",
            "original_term": "Headache",
            "event_definition": "治疗期间出现的不良事件",
            "time_window": "治疗期间",
            "population": "安全性分析集",
            "group_role": "active",
            "group_id": "arm-treatment",
            "group_label": "治疗组",
            "observed_value": 12.0,
            "source_value": "12%",
            "measurement_unit": "%",
            "denominator": 100,
            "source_version": "source-version-1",
            "locator": _LOCATOR,
        }
    )
    assert fact.family is SafetyFamily.COMMON_AE
    assert fact.arm_role is SafetyArmRole.TREATMENT
    assert fact.value == 12.0
    assert fact.source_term == "Headache"
