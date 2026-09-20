from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ci_workflow.reports.b.contracts import (
    EndpointCompatibilityError,
    EndpointObservation,
    load_endpoint_compatibility_policy,
    load_timepoint_compatibility_policy,
    match_endpoint_compatibility,
)

ROOT = Path(__file__).resolve().parents[3]
ENDPOINT_POLICY_PATH = ROOT / "policies" / "endpoints" / "compatibility-v1.yaml"
TIMEPOINT_POLICY_PATH = ROOT / "policies" / "timepoints" / "compatibility-v1.yaml"


def _observation(**overrides: object) -> EndpointObservation:
    fields: dict[str, object] = {
        "observation_id": "observation-01",
        "trial_id": "NCT00000001",
        "endpoint_id": "easi75",
        "endpoint_definition": "EASI-75 应答者比例",
        "endpoint_role": "primary",
        "unit": "%",
        "direction": "higher_is_better",
        "analysis_form": "response_rate",
        "timepoint": 12,
        "time_unit": "week",
    }
    fields.update(overrides)
    return EndpointObservation.model_validate(fields)


def test_compatible_observation_preserves_raw_values_and_rule_lineage() -> None:
    raw_definition = " EASI-75   应答者比例 "
    raw_unit = " % "
    result = match_endpoint_compatibility(
        _observation(endpoint_definition=raw_definition, unit=raw_unit),
        endpoint_policy=load_endpoint_compatibility_policy(ENDPOINT_POLICY_PATH),
        timepoint_policy=load_timepoint_compatibility_policy(TIMEPOINT_POLICY_PATH),
    )

    assert result.compatible is True
    assert result.compatibility_key == (
        "endpoint-easi75-response-v1",
        "timepoint-week-12-v1",
    )
    assert result.endpoint_rule_id == "endpoint-easi75-response-v1"
    assert result.timepoint_rule_id == "timepoint-week-12-v1"
    assert result.difference_labels_zh == ()
    assert result.original_endpoint == "easi75"
    assert result.original_definition == raw_definition
    assert result.original_unit == raw_unit
    assert result.actual_timepoint == 12
    assert result.original_endpoint_role == "primary"
    assert result.analysis_form == "response_rate"


def test_direction_unit_and_analysis_mismatch_is_split_without_rewriting_originals() -> None:
    result = match_endpoint_compatibility(
        _observation(
            direction="lower_is_better",
            unit="分数",
            analysis_form="absolute_value",
        ),
        endpoint_policy=load_endpoint_compatibility_policy(ENDPOINT_POLICY_PATH),
        timepoint_policy=load_timepoint_compatibility_policy(TIMEPOINT_POLICY_PATH),
    )

    assert result.compatible is False
    assert result.compatibility_key is None
    assert result.endpoint_rule_id is None
    assert result.timepoint_rule_id == "timepoint-week-12-v1"
    assert "方向不兼容" in result.difference_labels_zh
    assert "单位不可直接换算" in result.difference_labels_zh
    assert "分析形式不兼容" in result.difference_labels_zh
    assert result.original_unit == "分数"
    assert result.actual_timepoint == 12


def test_timepoint_outside_window_is_split_and_loaders_fail_closed(tmp_path: Path) -> None:
    # v1.2 起登记窗补齐 mid 段（14.5–21.9），周 20 已合法入窗；
    # 外窗用例改用延伸窗上界之外的周 320。
    result = match_endpoint_compatibility(
        _observation(timepoint=320),
        endpoint_policy=load_endpoint_compatibility_policy(ENDPOINT_POLICY_PATH),
        timepoint_policy=load_timepoint_compatibility_policy(TIMEPOINT_POLICY_PATH),
    )

    assert result.compatible is False
    assert result.endpoint_rule_id == "endpoint-easi75-response-v1"
    assert result.timepoint_rule_id is None
    assert "实际时间点未命中同单位兼容窗" in result.difference_labels_zh
    assert result.actual_timepoint == 320

    payload = yaml.safe_load(ENDPOINT_POLICY_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    rules = payload["rules"]
    assert isinstance(rules, list)
    rules[0]["unknown_field"] = True
    unknown_path = tmp_path / "unknown.yaml"
    unknown_path.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")
    with pytest.raises(EndpointCompatibilityError):
        load_endpoint_compatibility_policy(unknown_path)

    duplicate_payload = yaml.safe_load(ENDPOINT_POLICY_PATH.read_text(encoding="utf-8"))
    assert isinstance(duplicate_payload, dict)
    duplicate_rules = duplicate_payload["rules"]
    assert isinstance(duplicate_rules, list)
    duplicate_rule = dict(duplicate_rules[0])
    duplicate_rule["rule_id"] = "endpoint-easi75-response-duplicate"
    duplicate_rules.append(duplicate_rule)
    duplicate_path = tmp_path / "duplicate.yaml"
    duplicate_path.write_text(
        yaml.safe_dump(duplicate_payload, allow_unicode=True), encoding="utf-8"
    )
    with pytest.raises(EndpointCompatibilityError):
        load_endpoint_compatibility_policy(duplicate_path)

    non_chinese_payload = yaml.safe_load(ENDPOINT_POLICY_PATH.read_text(encoding="utf-8"))
    assert isinstance(non_chinese_payload, dict)
    non_chinese_rules = non_chinese_payload["rules"]
    assert isinstance(non_chinese_rules, list)
    non_chinese_rules[0]["difference_label_zh"] = "mismatch"
    non_chinese_path = tmp_path / "non-chinese-label.yaml"
    non_chinese_path.write_text(
        yaml.safe_dump(non_chinese_payload, allow_unicode=True), encoding="utf-8"
    )
    with pytest.raises(EndpointCompatibilityError):
        load_endpoint_compatibility_policy(non_chinese_path)


def test_match_revalidates_model_copy_and_does_not_trust_frozen_observation() -> None:
    forged = _observation().model_copy(update={"unit": "分数"})

    result = match_endpoint_compatibility(forged)

    assert result.compatible is False
    assert result.original_unit == "分数"
    assert "单位不可直接换算" in result.difference_labels_zh

    injected = _observation().model_copy(update={"unknown_field": "forged"})
    with pytest.raises(EndpointCompatibilityError, match="重新校验"):
        match_endpoint_compatibility(injected)


def test_construct_only_claim_cannot_force_unknown_endpoint_into_family() -> None:
    result = match_endpoint_compatibility(
        _observation(endpoint_id="pasi75", clinical_construct="easi75_response")
    )

    assert result.compatible is False
    assert result.endpoint_rule_id is None
    assert "未命中终点兼容规则" in result.difference_labels_zh


def test_compatible_nearby_timepoint_retains_difference_label() -> None:
    result = match_endpoint_compatibility(_observation(timepoint=10))

    assert result.compatible is True
    assert result.timepoint_rule_id == "timepoint-week-12-v1"
    assert result.actual_timepoint == 10
    assert any(
        "第 10 周" in label and "第 12 周附近" in label for label in result.difference_labels_zh
    )


def test_loaders_reject_ambiguous_endpoint_rules_and_overlapping_windows(
    tmp_path: Path,
) -> None:
    endpoint_payload = yaml.safe_load(ENDPOINT_POLICY_PATH.read_text(encoding="utf-8"))
    assert isinstance(endpoint_payload, dict)
    endpoint_rules = endpoint_payload["rules"]
    assert isinstance(endpoint_rules, list)
    ambiguous = dict(endpoint_rules[0])
    ambiguous["rule_id"] = "endpoint-easi75-response-ambiguous"
    ambiguous["label_zh"] = "EASI-75 应答重复规则"
    endpoint_rules.append(ambiguous)
    endpoint_path = tmp_path / "ambiguous-endpoint.yaml"
    endpoint_path.write_text(yaml.safe_dump(endpoint_payload, allow_unicode=True), encoding="utf-8")

    with pytest.raises(EndpointCompatibilityError, match="重叠|歧义"):
        load_endpoint_compatibility_policy(endpoint_path)

    timepoint_payload = yaml.safe_load(TIMEPOINT_POLICY_PATH.read_text(encoding="utf-8"))
    assert isinstance(timepoint_payload, dict)
    timepoint_rules = timepoint_payload["rules"]
    assert isinstance(timepoint_rules, list)
    overlapping = dict(timepoint_rules[1])
    overlapping.update(
        {
            "rule_id": "timepoint-week-13-overlap",
            "minimum": 12,
            "maximum": 16,
            "canonical_value": 13,
            "label_zh": "第 13 周附近",
        }
    )
    timepoint_rules.append(overlapping)
    timepoint_path = tmp_path / "overlapping-timepoint.yaml"
    timepoint_path.write_text(
        yaml.safe_dump(timepoint_payload, allow_unicode=True), encoding="utf-8"
    )

    with pytest.raises(EndpointCompatibilityError, match="重叠|歧义"):
        load_timepoint_compatibility_policy(timepoint_path)
