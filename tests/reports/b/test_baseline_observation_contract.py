"""Task 6.5 B 类 baseline_observation 强类型合同测试。"""

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
from ci_workflow.reports.b.baseline import (
    BaselineCompatibilityKey,
    BaselineDataType,
    BaselineObservation,
    BaselineStatisticForm,
    BaselineVariableDomain,
    validate_baseline_observation,
)

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "schemas" / "baseline-observation.schema.json"

_LOCATOR = EvidenceLocator(
    document_role="primary-trial-report",
    field_path="Table 1.baseline",
    table="Table 1",
    row="Treatment group",
    column="Mean (SD)",
    page=12,
)


def _observation(**overrides: object) -> BaselineObservation:
    payload: dict[str, object] = {
        "row_id": "baseline-row-age-g1",
        "source_row_id": "source-row-age-g1",
        "observation_id": "baseline-observation-age-g1",
        "product_id": "product-a",
        "trial_id": "trial-1",
        "cohort_id": "cohort-1",
        "group_id": "group-1",
        "analysis_population": "全分析集",
        "variable_domain": BaselineVariableDomain.DEMOGRAPHICS,
        "source_name": "Age",
        "source_definition": "Age at baseline",
        "standardized_concept": "age",
        "scale": None,
        "scale_version": None,
        "direction": None,
        "theoretical_range": None,
        "data_type": BaselineDataType.CONTINUOUS,
        "statistic_form": BaselineStatisticForm.MEAN,
        "value": 54.3,
        "raw_value": "54.3 (12.1)",
        "unit": "岁",
        "dispersion": 12.1,
        "range_lower": None,
        "range_upper": None,
        "category_level": None,
        "bin_label": None,
        "bin_lower": None,
        "bin_upper": None,
        "numerator": None,
        "denominator": 100,
        "denominator_role": "随机化人群",
        "baseline_definition": "首次给药前最近一次评估",
        "baseline_timepoint": "基线",
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
        "compatibility_rule": "baseline-age-v1",
        "difference_labels_zh": (),
    }
    payload.update(overrides)
    return BaselineObservation.model_validate(payload)


def test_baseline_enums_are_closed_and_cover_required_domains_and_statistics() -> None:
    assert {member.value for member in BaselineVariableDomain} == {
        "demographics",
        "disease_context",
        "baseline_severity",
    }
    assert {member.value for member in BaselineDataType} == {
        "continuous",
        "categorical",
        "count",
    }
    assert {
        "sample_size",
        "mean",
        "standard_deviation",
        "median",
        "quartiles",
        "range",
        "count",
        "proportion",
        "other",
    } <= {member.value for member in BaselineStatisticForm}


def test_baseline_observation_preserves_complete_scope_science_and_lineage_fields() -> None:
    observation = _observation()

    assert observation.product_id == "product-a"
    assert observation.trial_id == "trial-1"
    assert observation.cohort_id == "cohort-1"
    assert observation.group_id == "group-1"
    assert observation.analysis_population == "全分析集"
    assert observation.variable_domain is BaselineVariableDomain.DEMOGRAPHICS
    assert observation.source_name == "Age"
    assert observation.source_definition == "Age at baseline"
    assert observation.standardized_concept == "age"
    assert observation.scale is None
    assert observation.scale_version is None
    assert observation.direction is None
    assert observation.theoretical_range is None
    assert observation.data_type is BaselineDataType.CONTINUOUS
    assert observation.statistic_form is BaselineStatisticForm.MEAN
    assert observation.value == 54.3
    assert observation.unit == "岁"
    assert observation.dispersion == 12.1
    assert observation.denominator == 100
    assert observation.denominator_role == "随机化人群"
    assert observation.baseline_definition == "首次给药前最近一次评估"
    assert observation.baseline_timepoint == "基线"
    assert observation.source_version_id == "source-version-1"
    assert observation.source_locator == _LOCATOR
    assert observation.disclosure_state is FactDisclosureState.REPORTED_VALUE
    assert observation.compatibility_rule == "baseline-age-v1"
    assert observation.difference_labels_zh == ()


def test_continuous_statistic_forms_are_not_interchangeable_or_synthetic() -> None:
    mean = _observation(statistic_form=BaselineStatisticForm.MEAN, value=54.3, dispersion=12.1)
    median = _observation(
        row_id="baseline-row-age-median-g1",
        source_row_id="source-row-age-median-g1",
        observation_id="baseline-observation-age-median-g1",
        statistic_form=BaselineStatisticForm.MEDIAN,
        value=52.0,
        dispersion=None,
    )
    quartiles = _observation(
        row_id="baseline-row-age-quartiles-g1",
        source_row_id="source-row-age-quartiles-g1",
        observation_id="baseline-observation-age-quartiles-g1",
        statistic_form=BaselineStatisticForm.QUARTILES,
        value=None,
        dispersion=None,
        range_lower=42.0,
        range_upper=63.0,
    )

    assert mean.statistic_form is not median.statistic_form
    assert mean.dispersion == 12.1
    assert median.dispersion is None
    assert quartiles.range_lower == 42.0
    assert quartiles.range_upper == 63.0

    with pytest.raises(ValidationError, match="统计形式|离散|区间"):
        _observation(
            statistic_form=BaselineStatisticForm.MEAN,
            value=54.3,
            dispersion=12.1,
            range_lower=42.0,
            range_upper=63.0,
        )


def test_categorical_observation_requires_positive_denominator_and_keeps_source_level() -> None:
    female = _observation(
        row_id="baseline-row-sex-female-g1",
        source_row_id="source-row-sex-female-g1",
        observation_id="baseline-observation-sex-female-g1",
        variable_domain=BaselineVariableDomain.DEMOGRAPHICS,
        source_name="Sex",
        source_definition="Sex at baseline",
        standardized_concept="sex",
        data_type=BaselineDataType.CATEGORICAL,
        statistic_form=BaselineStatisticForm.PROPORTION,
        value=45.0,
        raw_value="45/100 (45%)",
        unit="%",
        dispersion=None,
        category_level="Female",
        denominator=100,
        numerator=45,
    )

    assert female.category_level == "Female"
    assert female.numerator == 45
    assert female.denominator == 100
    assert female.value == 45.0

    with pytest.raises(ValidationError, match="分母"):
        _observation(
            data_type=BaselineDataType.CATEGORICAL,
            statistic_form=BaselineStatisticForm.PROPORTION,
            value=45.0,
            numerator=45,
            denominator=None,
            category_level="Female",
        )
    with pytest.raises(ValidationError, match="分子|分母"):
        _observation(
            data_type=BaselineDataType.CATEGORICAL,
            statistic_form=BaselineStatisticForm.PROPORTION,
            value=45.0,
            numerator=101,
            denominator=100,
            category_level="Female",
        )


def test_missing_states_cannot_carry_numeric_or_denominator_but_reported_zero_is_explicit() -> None:
    with pytest.raises(ValidationError, match="未报告|未公开|数值|分母"):
        _observation(
            disclosure_state=FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
            value=54.3,
            raw_value=None,
            denominator=100,
        )

    zero = _observation(
        row_id="baseline-row-sex-none-g1",
        source_row_id="source-row-sex-none-g1",
        observation_id="baseline-observation-sex-none-g1",
        data_type=BaselineDataType.CATEGORICAL,
        statistic_form=BaselineStatisticForm.PROPORTION,
        source_name="Sex",
        source_definition="Sex at baseline",
        standardized_concept="sex",
        value=0,
        raw_value="0/100 (0%)",
        unit="%",
        dispersion=None,
        category_level="Unknown",
        numerator=0,
        denominator=100,
        disclosure_state=FactDisclosureState.REPORTED_ZERO,
        reported_zero_text="0/100 (0%)",
    )
    assert zero.value == 0
    assert zero.disclosure_state is FactDisclosureState.REPORTED_ZERO

    with pytest.raises(ValidationError, match="零值|reported_zero"):
        _observation(
            disclosure_state=FactDisclosureState.REPORTED_ZERO,
            value=2,
            raw_value="2%",
            reported_zero_text=None,
        )


def test_counts_and_proportions_reject_impossible_values() -> None:
    with pytest.raises(ValidationError, match="不得为负数"):
        _observation(
            standardized_concept="baseline_sample_size",
            data_type=BaselineDataType.COUNT,
            statistic_form=BaselineStatisticForm.SAMPLE_SIZE,
            value=-1,
            raw_value="-1",
            unit="人",
            dispersion=None,
        )
    with pytest.raises(ValidationError, match="比例"):
        _observation(
            standardized_concept="sex",
            data_type=BaselineDataType.CATEGORICAL,
            statistic_form=BaselineStatisticForm.PROPORTION,
            value=101,
            raw_value="101%",
            unit="%",
            dispersion=None,
            category_level="Female",
        )


def test_not_applicable_and_route_unresolved_retain_distinct_non_numeric_state() -> None:
    not_applicable = _observation(
        value=None,
        raw_value="该变量不适用",
        denominator=None,
        dispersion=None,
        disclosure_state=FactDisclosureState.NOT_APPLICABLE,
        applicability_predicate_id="baseline-scale-not-applicable-v1",
    )
    unresolved = _observation(
        value=None,
        raw_value="当前技术路径未能核实",
        denominator=None,
        dispersion=None,
        disclosure_state=FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
        route_receipt_id="receipt-baseline-1",
    )

    assert not_applicable.disclosure_state is FactDisclosureState.NOT_APPLICABLE
    assert unresolved.disclosure_state is FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE
    assert not_applicable.value is None
    assert unresolved.value is None


def test_compatibility_key_uses_scientific_semantics_not_display_or_review_metadata() -> None:
    baseline = _observation()
    same_science = _observation(
        row_id="baseline-row-age-g2",
        source_row_id="source-row-age-g2",
        observation_id="baseline-observation-age-g2",
        group_id="group-2",
        source_name="年龄",
        source_definition="入组时年龄",
        source_version_id="source-version-2",
        source_locator=EvidenceLocator(
            document_role="primary-trial-report",
            table="Table 1",
            row="Control group",
            column="Mean (SD)",
            page=12,
        ),
        difference_labels_zh=("来源原名不同",),
        review_state=FactReviewState.CANDIDATE,
    )
    changed_statistic = _observation(
        row_id="baseline-row-age-median-g1",
        source_row_id="source-row-age-median-g1",
        observation_id="baseline-observation-age-median-g1",
        statistic_form=BaselineStatisticForm.MEDIAN,
        value=52.0,
        dispersion=None,
    )
    changed_direction = _observation(direction="higher_is_more_severe")
    changed_definition = _observation(baseline_definition="筛选期首次评估")

    assert isinstance(baseline.compatibility_key, BaselineCompatibilityKey)
    assert baseline.compatibility_key == same_science.compatibility_key
    assert baseline.compatibility_key != changed_statistic.compatibility_key
    assert baseline.compatibility_key != changed_direction.compatibility_key
    assert baseline.compatibility_key != changed_definition.compatibility_key


def test_stable_identity_separates_scope_and_scientific_row_dimensions() -> None:
    group_two = _observation(
        row_id="baseline-row-age-g2",
        source_row_id="source-row-age-g2",
        observation_id="baseline-observation-age-g2",
        group_id="group-2",
    )
    median = _observation(
        row_id="baseline-row-age-median-g1",
        source_row_id="source-row-age-median-g1",
        observation_id="baseline-observation-age-median-g1",
        statistic_form=BaselineStatisticForm.MEDIAN,
        value=52.0,
        dispersion=None,
    )
    changed_value = _observation(value=61.0, dispersion=13.0)

    baseline_identity = _observation().identity_key
    assert baseline_identity != group_two.identity_key
    assert baseline_identity != median.identity_key
    assert baseline_identity == changed_value.identity_key
    assert _observation().row_id != group_two.row_id
    assert _observation().row_id != median.row_id


def test_public_validation_rejects_model_copy_tampering_and_unknown_fields() -> None:
    forged = _observation().model_copy(update={"group_id": "group-2"})
    validated = validate_baseline_observation(forged)
    assert validated.group_id == "group-2"
    assert validated.row_id != _observation().row_id

    unknown = _observation().model_copy(update={"unknown_field": "forged"})
    with pytest.raises((ValidationError, ValueError), match="重新校验|extra|未知"):
        validate_baseline_observation(unknown)


def test_baseline_json_schema_matches_model_and_rejects_unknown_fields() -> None:
    assert SCHEMA_PATH.exists(), "Task 6.5 必须提供 baseline-observation.schema.json"
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    payload = _observation().model_dump(mode="json")
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    assert not errors, [error.message for error in errors]

    forged = dict(payload)
    forged["unknown_field"] = "must fail closed"
    assert list(validator.iter_errors(forged)), "JSON Schema 必须拒绝未知字段"
