"""Task 4.5 规范证据视图模型与数据完整性单元测试。

合同要点：
- 每条证据视图绑定稳定 ``row_id``（ReportRow 本体嵌入）、单一锁定快照、
  来源版本与精确 locator；临床事实由模型本身携带，禁止从展示层拼出。
- 观察字段（量表/时间点/值/阈值/单位/分子/分母与基线/完成情况扩展字段）
  只允许"确定值 XOR 互斥状态"：不适用、尚未公开、来源未列示、技术暂不可用，
  状态必须互斥且提供中文标签，不得空白或把缺失当作 0。
- 简短原文与原因原文仅在输入已有且允许时携带，与规范化说明/规范原因
  分离存储，原文不得被规范化文本覆盖。
- 冲突与历史版本各自绑定来源版本与精确 locator；固定对照集合必须同快照、
  同页面、行唯一，观察类型必须匹配冻结目录页面的证据抽屉配置。
"""

from __future__ import annotations

from typing import Any

import pytest

from ci_workflow.domain.enums import ReportKind
from ci_workflow.reports.common.evidence_view import (
    EVIDENCE_FIELD_STATE_LABELS_ZH,
    MUTUAL_EXCLUSION_MARKS_ZH,
    EvidenceFieldState,
    EvidenceObservationKind,
    EvidenceViewBoundaryError,
    OriginalTextStatus,
    validate_evidence_view_payload,
    validate_evidence_view_set_payload,
)
from ci_workflow.reports.common.view_state import derive_row_id

SNAPSHOT = "report-snapshot-45"
PAGE_A = "efficacy-safety-overview"
PAGE_B_BASELINE = "baseline-demographics"
PAGE_B_DISPOSITION = "disposition-overview"

_LOCATOR: dict[str, Any] = {
    "document_role": "primary_registry",
    "field_path": "Results.participantFlow",
    "table": "基线特征表",
}


def row(
    *,
    label: str = "第3组治疗组主要终点",
    state: str = "reported_value",
    page: str = PAGE_A,
    snapshot: str = SNAPSHOT,
    **identity: str,
) -> dict[str, Any]:
    return {
        "row_id": derive_row_id(**identity),
        "display_label_zh": label,
        "page_responsibility_id": page,
        "report_snapshot_id": snapshot,
        "disclosure_state": state,
        **identity,
    }


def field(*, value: str | None = None, state: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if value is not None:
        payload["value"] = value
    if state is not None:
        payload["state"] = state
    return payload


def evidence(
    *,
    kind: str = "general",
    report_kind: str = "A",
    page: str = PAGE_A,
    row_payload: dict[str, Any] | None = None,
    disclosure: str = "reported_value",
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "report_kind": report_kind,
        "observation_kind": kind,
        "row": row_payload
        or row(
            page=page,
            state=disclosure,
            product_id="product-01",
            trial_id="trial-01",
            group_id="group-treat",
            endpoint_id="endpoint-hba1c",
        ),
        "product_zh": "产品甲",
        "trial_zh": "试验一",
        "group_zh": field(value="治疗组"),
        "element_zh": "主要终点 HbA1c 变化值",
        "scale": field(value="原始"),
        "timepoint": field(value="第12周"),
        "value": field(value="5.2"),
        "threshold": field(state="not_applicable"),
        "unit": field(value="mg/dL"),
        "numerator": field(state="not_applicable"),
        "denominator": field(value="120"),
        "source_version_id": "source-version-01",
        "source_version_label_zh": "ClinicalTrials.gov 登记版本（2026年5月1日）",
        "locator": _LOCATOR,
        "explanation": field(value="直接取自来源报告值，未做换算"),
    }
    payload.update(overrides)
    return payload


def baseline_extension() -> dict[str, Any]:
    """baseline/disposition 扩展字段族：全字段确定性表达。"""
    return {
        "canonical_variable_family": field(value="人口学特征"),
        "source_field_name": field(value="Age"),
        "source_field_definition": field(value="入选时年龄（岁）"),
        "statistical_form_or_measurement_object": field(value="均值"),
        "scale_version_direction": field(state="not_applicable"),
        "denominator_role": field(value="随机化人群"),
        "time_window_or_baseline_definition": field(value="基线＝第1天给药前"),
        "reason_original_text": "Age at enrollment",
        "canonical_reason": field(value="按登记原字段直接规范为年龄变量"),
        "mutual_exclusion_exhaustiveness": field(value="互斥且穷尽"),
        "compatibility_rule": field(value="同定义可直接合并"),
        "difference_label": field(state="not_applicable"),
    }


# ─── 通用证据视图：稳定绑定与完整通用字段 ───────────────────────────────────


def test_general_evidence_view_binds_row_snapshot_source_version_and_locator() -> None:
    view = validate_evidence_view_payload(evidence())
    assert view.row.row_id.startswith("report-row_")
    assert view.row.report_snapshot_id == SNAPSHOT
    assert view.source_version_id == "source-version-01"
    assert view.locator.document_role == "primary_registry"
    assert view.locator.table == "基线特征表"


def test_reported_value_requires_concrete_value() -> None:
    with pytest.raises(EvidenceViewBoundaryError, match="已报告"):
        validate_evidence_view_payload(evidence(value=field(state="not_yet_disclosed")))
    with pytest.raises(EvidenceViewBoundaryError, match="已报告"):
        validate_evidence_view_payload(evidence(value=field(state="not_applicable")))


def test_reported_zero_requires_numeric_zero_and_zero_is_not_missing() -> None:
    zero = validate_evidence_view_payload(
        evidence(disclosure="reported_zero", value=field(value="0"))
    )
    assert zero.value.value == "0"
    with pytest.raises(EvidenceViewBoundaryError, match="已报告零值"):
        validate_evidence_view_payload(
            evidence(disclosure="reported_zero", value=field(value="0.5"))
        )
    with pytest.raises(EvidenceViewBoundaryError, match="已报告零值"):
        validate_evidence_view_payload(
            evidence(disclosure="reported_zero", value=field(state="not_applicable"))
        )


def test_not_disclosed_state_rejects_concrete_value() -> None:
    with pytest.raises(EvidenceViewBoundaryError, match="未公开"):
        validate_evidence_view_payload(
            evidence(disclosure="not_publicly_disclosed", value=field(value="5.2"))
        )
    view = validate_evidence_view_payload(
        evidence(
            disclosure="not_publicly_disclosed",
            value=field(state="not_yet_disclosed"),
        )
    )
    assert view.value.state is EvidenceFieldState.NOT_YET_DISCLOSED
    # 未公开行的分母可以已报告，与既有行合同一致。
    assert view.denominator.value == "120"


def test_missing_value_must_be_typed_state_not_blank_or_zero() -> None:
    with pytest.raises(EvidenceViewBoundaryError, match="恰好"):
        validate_evidence_view_payload(evidence(value=field()))
    with pytest.raises(EvidenceViewBoundaryError, match="恰好"):
        validate_evidence_view_payload(evidence(value=field(value="5.2", state="not_applicable")))


def test_four_states_are_mutually_exclusive_with_chinese_labels() -> None:
    labels = EVIDENCE_FIELD_STATE_LABELS_ZH
    assert set(labels) == {
        EvidenceFieldState.NOT_APPLICABLE,
        EvidenceFieldState.NOT_YET_DISCLOSED,
        EvidenceFieldState.SOURCE_NOT_LISTED,
        EvidenceFieldState.TECHNICALLY_UNAVAILABLE,
    }
    assert set(labels.values()) == {"不适用", "尚未公开", "来源未列示", "技术暂不可用"}
    for label in labels.values():
        assert any("\u4e00" <= ch <= "\u9fff" for ch in label)


def test_observation_field_is_immutable() -> None:
    view = validate_evidence_view_payload(evidence())
    with pytest.raises(ValueError, match="frozen"):
        view.value = view.denominator


# ─── 规范化说明与简短原文：原文不被覆盖 ─────────────────────────────────────


def test_original_text_only_when_input_has_it_and_allowed() -> None:
    ok = validate_evidence_view_payload(
        evidence(
            original_text="Mean change from baseline: 5.2",
            original_text_status=OriginalTextStatus.PROVIDED.value,
        )
    )
    assert ok.original_text == "Mean change from baseline: 5.2"
    with pytest.raises(EvidenceViewBoundaryError, match="原文"):
        validate_evidence_view_payload(
            evidence(
                original_text=None,
                original_text_status=OriginalTextStatus.PROVIDED.value,
            )
        )
    with pytest.raises(EvidenceViewBoundaryError, match="原文"):
        validate_evidence_view_payload(
            evidence(
                original_text="不允许携带的原文",
                original_text_status=OriginalTextStatus.NOT_PERMITTED.value,
            )
        )
    with pytest.raises(EvidenceViewBoundaryError, match="原文"):
        validate_evidence_view_payload(
            evidence(
                original_text="未提供状态却给了原文",
                original_text_status=OriginalTextStatus.NOT_PROVIDED.value,
            )
        )


def test_original_text_preserved_verbatim_and_not_overwritten_by_explanation() -> None:
    raw = "Mean change from baseline:  5.2  (SD 1.1)"
    view = validate_evidence_view_payload(
        evidence(
            original_text=raw,
            original_text_status=OriginalTextStatus.PROVIDED.value,
            explanation=field(value="直接取自来源报告值，未做换算"),
        )
    )
    assert view.original_text == raw  # 原文逐字保留，不做空白折叠
    assert view.explanation.value == "直接取自来源报告值，未做换算"
    assert view.explanation.value != raw


def test_explanation_must_be_native_chinese() -> None:
    with pytest.raises(EvidenceViewBoundaryError, match="中文"):
        validate_evidence_view_payload(evidence(explanation=field(value="raw value")))


# ─── 临床事实身份必须由模型携带，不得留给展示层 ─────────────────────────────


def test_view_requires_product_trial_group_element_facts() -> None:
    with pytest.raises(EvidenceViewBoundaryError, match="中文"):
        validate_evidence_view_payload(evidence(product_zh="product-01"))
    with pytest.raises(EvidenceViewBoundaryError, match="中文"):
        validate_evidence_view_payload(evidence(trial_zh="trial-01"))
    with pytest.raises(EvidenceViewBoundaryError, match="中文"):
        validate_evidence_view_payload(evidence(element_zh="endpoint-hba1c"))
    with pytest.raises(EvidenceViewBoundaryError, match="中文"):
        validate_evidence_view_payload(evidence(group_zh=field(value="group-treat")))


def test_group_may_be_typed_not_applicable() -> None:
    view = validate_evidence_view_payload(evidence(group_zh=field(state="not_applicable")))
    assert view.group_zh.state is EvidenceFieldState.NOT_APPLICABLE


# ─── baseline/disposition 扩展字段族：与通用字段互斥的观察类型 ───────────────


def test_general_view_rejects_baseline_extension_fields() -> None:
    with pytest.raises(EvidenceViewBoundaryError, match="扩展"):
        validate_evidence_view_payload(
            evidence(kind="general", canonical_reason=field(value="规范原因"))
        )


def test_baseline_observation_requires_full_extension_family() -> None:
    for missing in (
        "canonical_variable_family",
        "source_field_name",
        "source_field_definition",
        "statistical_form_or_measurement_object",
        "scale_version_direction",
        "denominator_role",
        "time_window_or_baseline_definition",
        "canonical_reason",
        "mutual_exclusion_exhaustiveness",
        "compatibility_rule",
        "difference_label",
    ):
        extension = baseline_extension()
        extension.pop(missing)
        payload = evidence(
            kind="baseline_observation",
            report_kind="B",
            page=PAGE_B_BASELINE,
            disclosure="reported_value",
            value=field(value="54.3"),
            unit=field(value="岁"),
            **extension,
        )
        with pytest.raises(EvidenceViewBoundaryError, match="扩展"):
            validate_evidence_view_payload(payload)


def test_baseline_observation_accepts_full_extension_family() -> None:
    view = validate_evidence_view_payload(
        evidence(
            kind="baseline_observation",
            report_kind="B",
            page=PAGE_B_BASELINE,
            disclosure="reported_value",
            value=field(value="54.3"),
            unit=field(value="岁"),
            **baseline_extension(),
        )
    )
    assert view.source_field_name is not None
    assert view.source_field_name.value == "Age"
    assert view.source_field_definition is not None
    assert view.source_field_definition.value == "入选时年龄（岁）"
    assert view.source_field_name.value != view.source_field_definition.value
    assert view.observation_kind is EvidenceObservationKind.BASELINE_OBSERVATION
    assert view.canonical_variable_family is not None
    assert view.canonical_reason is not None
    assert view.reason_original_text == "Age at enrollment"
    assert view.reason_original_text != view.canonical_reason.value  # 原文不被规范原因覆盖


def test_extension_requires_separate_source_field_name_and_definition() -> None:
    """§15.5：来源原名与定义必须分列携带；通用观察不得携带扩展字段。"""
    no_name = baseline_extension()
    no_name.pop("source_field_name")
    with pytest.raises(EvidenceViewBoundaryError, match="扩展"):
        validate_evidence_view_payload(
            evidence(
                kind="baseline_observation",
                report_kind="B",
                page=PAGE_B_BASELINE,
                disclosure="reported_value",
                value=field(value="54.3"),
                unit=field(value="岁"),
                **no_name,
            )
        )
    no_definition = baseline_extension()
    no_definition.pop("source_field_definition")
    with pytest.raises(EvidenceViewBoundaryError, match="扩展"):
        validate_evidence_view_payload(
            evidence(
                kind="baseline_observation",
                report_kind="B",
                page=PAGE_B_BASELINE,
                disclosure="reported_value",
                value=field(value="54.3"),
                unit=field(value="岁"),
                **no_definition,
            )
        )
    with pytest.raises(EvidenceViewBoundaryError, match="扩展"):
        validate_evidence_view_payload(
            evidence(kind="general", source_field_name=field(value="Age"))
        )
    unlisted = baseline_extension()
    unlisted["source_field_name"] = field(state="source_not_listed")
    unlisted_name = validate_evidence_view_payload(
        evidence(
            kind="trial_disposition_observation",
            report_kind="B",
            page=PAGE_B_DISPOSITION,
            disclosure="reported_value",
            element_zh="完成研究",
            value=field(value="102"),
            **unlisted,
        )
    )
    assert unlisted_name.source_field_name is not None
    assert unlisted_name.source_field_name.state is EvidenceFieldState.SOURCE_NOT_LISTED


def test_disposition_observation_carries_conflicts_and_history() -> None:
    view = validate_evidence_view_payload(
        evidence(
            kind="trial_disposition_observation",
            report_kind="B",
            page=PAGE_B_DISPOSITION,
            disclosure="reported_value",
            element_zh="完成研究",
            value=field(value="102"),
            numerator=field(value="102"),
            denominator=field(value="120"),
            **baseline_extension(),
            conflicts=[
                {
                    "conflicting_source_version_id": "source-version-02",
                    "conflicting_value_zh": "105/120",
                    "conflict_note_zh": "登记结果页与主要报告完成人数不一致",
                    "locator": _LOCATOR,
                }
            ],
            historical_versions=[
                {
                    "source_version_id": "source-version-00",
                    "previous_value": field(value="99"),
                    "supersession_note_zh": "2026年3月登记版本已被5月版本取代，仅留历史",
                    "locator": _LOCATOR,
                }
            ],
        )
    )
    assert view.conflicts[0].conflicting_source_version_id == "source-version-02"
    assert view.historical_versions[0].previous_value.value == "99"
    assert view.historical_versions[0].locator.table == "基线特征表"


def test_historical_version_preserves_typed_previous_state() -> None:
    view = validate_evidence_view_payload(
        evidence(
            kind="baseline_observation",
            report_kind="B",
            page=PAGE_B_BASELINE,
            value=field(value="54.3"),
            unit=field(value="岁"),
            **baseline_extension(),
            historical_versions=[
                {
                    "source_version_id": "source-version-00",
                    "previous_value": field(state="not_yet_disclosed"),
                    "supersession_note_zh": "旧版本未披露该字段，仅留历史",
                    "locator": _LOCATOR,
                }
            ],
        )
    )
    assert view.historical_versions[0].previous_value.state is (
        EvidenceFieldState.NOT_YET_DISCLOSED
    )


def test_mutual_exclusion_mark_accepts_only_known_chinese_marks() -> None:
    payload = evidence(
        kind="baseline_observation",
        report_kind="B",
        page=PAGE_B_BASELINE,
        value=field(value="54.3"),
        unit=field(value="岁"),
        **baseline_extension(),
    )
    payload["mutual_exclusion_exhaustiveness"] = field(value="互斥但未穷尽")
    view = validate_evidence_view_payload(payload)
    assert view.mutual_exclusion_exhaustiveness is not None
    assert view.mutual_exclusion_exhaustiveness.value == "互斥但未穷尽"
    assert set(MUTUAL_EXCLUSION_MARKS_ZH) == {"互斥且穷尽", "互斥但未穷尽", "非互斥"}
    payload["mutual_exclusion_exhaustiveness"] = field(value="大致互斥")
    with pytest.raises(EvidenceViewBoundaryError, match="互斥穷尽"):
        validate_evidence_view_payload(payload)


def test_conflict_requires_source_version_and_precise_locator() -> None:
    payload = evidence(conflicts=[{"conflicting_value_zh": "105/120"}])
    with pytest.raises(EvidenceViewBoundaryError):
        validate_evidence_view_payload(payload)


# ─── 页面目录权威：观察类型必须匹配冻结目录的抽屉配置 ───────────────────────


def test_observation_kind_must_match_frozen_page_drawer_profile() -> None:
    # B 疗效页声明 common-clinical：baseline 观察被拒绝。
    with pytest.raises(EvidenceViewBoundaryError, match="抽屉"):
        validate_evidence_view_payload(
            evidence(
                kind="baseline_observation",
                report_kind="B",
                page="efficacy",
                value=field(value="54.3"),
                unit=field(value="岁"),
                **baseline_extension(),
            )
        )


def test_standalone_validator_requires_frozen_catalog_page() -> None:
    with pytest.raises(EvidenceViewBoundaryError, match="冻结目录"):
        validate_evidence_view_payload(evidence(page="not-a-page"))


# ─── 固定对照集合：同快照、同页面、行唯一 ───────────────────────────────────


def _set_payload(*views: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_kind": views[0]["report_kind"],
        "report_snapshot_id": SNAPSHOT,
        "page_responsibility_id": views[0]["row"]["page_responsibility_id"],
        "views": list(views),
    }


def test_evidence_set_binds_pins_to_one_snapshot_and_page() -> None:
    first = evidence()
    second = evidence(
        row_payload=row(
            page=PAGE_A,
            product_id="product-01",
            trial_id="trial-01",
            group_id="group-ctrl",
            endpoint_id="endpoint-hba1c",
        ),
        group_zh=field(value="对照组"),
    )
    view_set = validate_evidence_view_set_payload(_set_payload(first, second))
    assert [v.row.row_id for v in view_set.views] == [
        first["row"]["row_id"],
        second["row"]["row_id"],
    ]
    assert view_set.report_snapshot_id == SNAPSHOT


def test_evidence_set_rejects_duplicate_row_ids() -> None:
    with pytest.raises(EvidenceViewBoundaryError, match="重复"):
        validate_evidence_view_set_payload(_set_payload(evidence(), evidence()))


def test_evidence_set_rejects_cross_snapshot_or_cross_page_pins() -> None:
    other_snapshot = evidence(
        row_payload=row(
            page=PAGE_A,
            snapshot="report-snapshot-other",
            product_id="product-01",
            trial_id="trial-01",
            group_id="group-ctrl",
            endpoint_id="endpoint-hba1c",
        ),
        group_zh=field(value="对照组"),
    )
    with pytest.raises(EvidenceViewBoundaryError, match="快照"):
        validate_evidence_view_set_payload(_set_payload(evidence(), other_snapshot))
    other_page = evidence(
        row_payload=row(
            page="landscape",
            product_id="product-01",
            trial_id="trial-01",
            group_id="group-ctrl",
            endpoint_id="endpoint-hba1c",
        ),
        group_zh=field(value="对照组"),
    )
    with pytest.raises(EvidenceViewBoundaryError, match="页面"):
        validate_evidence_view_set_payload(_set_payload(evidence(), other_page))


def test_empty_evidence_set_is_allowed() -> None:
    view_set = validate_evidence_view_set_payload(
        {
            "report_kind": ReportKind.A.value,
            "report_snapshot_id": SNAPSHOT,
            "page_responsibility_id": PAGE_A,
            "views": [],
        }
    )
    assert view_set.views == ()
