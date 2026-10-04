"""Task 7.4 C 类综合：禁止唯一推荐、凑数路径与无依据产品建议 RED。

合同断言（先失败后通过；本文件不提供实现 stub）：
- 仅有适应症、空观察、关键事实未披露/未解决、或证据只支撑一条独立设计签名时，
  必须失败关闭，不得输出唯一路径、草稿路径或“最佳/唯一推荐”；
- 失败说明使用自然中文，不泄漏内部状态码；
- 本任务无产品背景合同，不得输出针对用户自有产品的确定性建议；
- 无原始数值/单位/公式/可逆原始行时，不得生成归一化分数或雷达数据；
- 与 ``test_multiple_design_paths.py`` 共用同一综合入口合同。
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from types import ModuleType
from typing import Any

import pytest

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.gates.models import ConflictDisposition, DisclosureMaturity, SourceRole
from ci_workflow.reports.c.contracts import DesignFieldFamily, DesignObservation

_INDICATION_ID = "indication-pnh"
_TRIAL_SOLO = "trial-solo"
_PRODUCT_SOLO = "product-solo-c5"

_CJK = re.compile(r"[\u3400-\u9fff]")
_INTERNAL_LEAKS = (
    "DesignSynthesisError",
    "DesignFieldFamily",
    "NOT_PUBLICLY_DISCLOSED",
    "not_publicly_disclosed",
    "UNRESOLVED_DUE_TO_ROUTE",
    "unresolved_due_to_route",
    "OPEN_CONFLICT_PRESERVED",
    "clinical_trial_registry",
    "field_family",
    "source_role",
    "c_missing_",
    "candidate_paths",
    "synthesize_design_paths",
    "BLOCKED",
    "PASSED",
)

_UNIQUE_RECOMMENDATION_TOKENS = (
    "唯一推荐",
    "最佳方案",
    "首选方案",
    "最优路径",
    "第一名",
    "唯一方案",
    "推荐第一",
    "best path",
    "unique recommendation",
)

_PRODUCT_SPECIFIC_TOKENS = (
    "我们的产品",
    "自有产品",
    "贵司产品",
    "本品应",
    "建议本品",
    "针对用户产品",
    "product-specific recommendation",
    "own product",
)

_NORMALIZED_KEYS = {
    "radar",
    "radar_scores",
    "radar_dimensions",
    "normalized_scores",
    "normalized_values",
    "normalization",
    "score_vector",
}


def _synthesis() -> ModuleType:
    import importlib

    try:
        return importlib.import_module("ci_workflow.reports.c.synthesis")
    except ModuleNotFoundError as exc:
        pytest.fail(f"C 类多路径综合尚未实现：{exc}", pytrace=False)


def _error_type(module: ModuleType) -> type[BaseException]:
    error_type = getattr(module, "DesignSynthesisError", None)
    assert isinstance(error_type, type) and issubclass(error_type, Exception), (
        "需要 DesignSynthesisError"
    )
    return error_type


def _locator(*, field_path: str, row: str) -> EvidenceLocator:
    return EvidenceLocator(
        document_role="clinical-trial-registry",
        field_path=field_path,
        heading="Study Design",
        table="Design Facts",
        row=row,
        column="Value",
        url="https://clinicaltrials.gov/study/NCT00000099#design",
        paragraph="Design",
    )


def _observation(**overrides: object) -> DesignObservation:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "row_id": "design-row-solo",
        "source_row_id": "registry-row-solo",
        "observation_id": "obs-solo-default",
        "product_id": _PRODUCT_SOLO,
        "trial_id": _TRIAL_SOLO,
        "cohort_id": "cohort-solo",
        "group_id": "group-all-enrolled",
        "field_family": DesignFieldFamily.POPULATION,
        "field": "target_population",
        "source_field_name": "目标人群",
        "source_field_definition": "Adults with PNH",
        "source_text": "确诊 PNH 的成人受试者。",
        "scale": None,
        "scale_version": None,
        "operator": None,
        "threshold_value": None,
        "threshold_unit": None,
        "assessment_timepoint": None,
        "stage": "III",
        "development_role": "关键注册试验",
        "randomization": None,
        "blinding": None,
        "source_version_id": "registry-version-solo-1",
        "source_locator": _locator(
            field_path="protocolSection.eligibilityModule",
            row="solo population",
        ),
        "source_role": SourceRole.CLINICAL_TRIAL_REGISTRY,
        "disclosure_maturity": DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT,
        "review_state": FactReviewState.ACCEPTED,
        "disclosure_state": FactDisclosureState.REPORTED_VALUE,
        "conflict_disposition": ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT,
        "reported_zero_text": None,
        "route_receipt_id": None,
        "applicability_predicate_id": None,
        "compatibility_rule": "c-design-v1",
        "difference_labels_zh": (),
    }
    payload.update(overrides)
    return DesignObservation.model_validate(payload)


def _single_signature_corpus() -> tuple[DesignObservation, ...]:
    """仅一条独立设计签名：可形成事实，但不足以产生两条候选路径。"""

    return (
        _observation(
            row_id="design-row-solo-population",
            source_row_id="registry-row-solo-population",
            observation_id="obs-solo-population",
            field_family=DesignFieldFamily.POPULATION,
            field="target_population",
            source_field_name="目标人群",
            source_field_definition="Target population",
            source_text="确诊 PNH 的成人受试者。",
            assessment_timepoint="筛选期",
            source_locator=_locator(
                field_path="protocolSection.eligibilityModule",
                row="solo population",
            ),
        ),
        _observation(
            row_id="design-row-solo-grouping",
            source_row_id="registry-row-solo-grouping",
            observation_id="obs-solo-grouping",
            field_family=DesignFieldFamily.GROUPING,
            field="arm_randomization_blinding",
            source_field_name="分组/随机/盲法",
            source_field_definition="Randomization and blinding",
            source_text="1:1 随机、双盲、平行对照。",
            randomization="1:1 随机",
            blinding="双盲",
            source_locator=_locator(
                field_path="protocolSection.designModule",
                row="solo grouping",
            ),
        ),
        _observation(
            row_id="design-row-solo-intervention",
            source_row_id="registry-row-solo-intervention",
            observation_id="obs-solo-intervention",
            group_id="group-experimental",
            field_family=DesignFieldFamily.INTERVENTION,
            field="experimental_arm",
            source_field_name="试验组干预",
            source_field_definition="Experimental intervention",
            source_text="长效补体 C5 抑制剂按体重静脉给药。",
            source_locator=_locator(
                field_path="protocolSection.armsInterventionsModule",
                row="solo intervention",
            ),
        ),
        _observation(
            row_id="design-row-solo-control",
            source_row_id="registry-row-solo-control",
            observation_id="obs-solo-control",
            group_id="group-control",
            field_family=DesignFieldFamily.INTERVENTION,
            field="control_arm",
            source_field_name="对照组干预",
            source_field_definition="Control intervention",
            source_text="短效补体 C5 抑制剂按标签静脉给药。",
            source_locator=_locator(
                field_path="protocolSection.armsInterventionsModule",
                row="solo control",
            ),
        ),
        _observation(
            row_id="design-row-solo-dose",
            source_row_id="registry-row-solo-dose",
            observation_id="obs-solo-dose",
            group_id="group-experimental",
            field_family=DesignFieldFamily.DOSE_SCHEDULE,
            field="dosing_regimen",
            source_field_name="给药方案",
            source_field_definition="Dosing regimen",
            source_text="负荷后每 8 周静脉给药一次。",
            source_locator=_locator(
                field_path="protocolSection.armsInterventionsModule.dosing",
                row="solo dose",
            ),
        ),
        _observation(
            row_id="design-row-solo-endpoint",
            source_row_id="registry-row-solo-endpoint",
            observation_id="obs-solo-endpoint",
            field_family=DesignFieldFamily.ENDPOINT,
            field="primary_endpoint_definition",
            source_field_name="LDH 正常化",
            source_field_definition="Proportion of subjects with LDH ≤1×ULN at Week 26",
            source_text="第 26 周 LDH 正常化（≤1×ULN）的受试者比例。",
            source_locator=_locator(
                field_path="protocolSection.outcomesModule.primaryOutcomes[0].measure",
                row="solo endpoint",
            ),
        ),
        _observation(
            row_id="design-row-solo-timepoint",
            source_row_id="registry-row-solo-timepoint",
            observation_id="obs-solo-timepoint",
            field_family=DesignFieldFamily.TIMEPOINT,
            field="primary_endpoint_timepoint",
            source_field_name="主要终点时间点",
            source_field_definition="Primary endpoint assessment timepoint",
            source_text="主要终点评估时间点：第 26 周。",
            assessment_timepoint="第26周",
            source_locator=_locator(
                field_path="protocolSection.outcomesModule.primaryOutcomes[0].timeFrame",
                row="solo timepoint",
            ),
        ),
        _observation(
            row_id="design-row-solo-visit",
            source_row_id="registry-row-solo-visit",
            observation_id="obs-solo-visit",
            field_family=DesignFieldFamily.OPERATIONAL,
            field="visit_schedule",
            source_field_name="访视安排",
            source_field_definition="Visit schedule",
            source_text="筛选、随机、第 2/4/8/16/26 周访视。",
            assessment_timepoint="第26周",
            source_locator=_locator(
                field_path="protocolSection.scheduleModule",
                row="solo visit",
            ),
        ),
    )


def _undisclosed_critical_corpus() -> tuple[DesignObservation, ...]:
    """关键人群事实未公开披露：不得据此凑出候选路径。"""

    accepted = _single_signature_corpus()
    blocked_population = _observation(
        row_id="design-row-solo-population-undisclosed",
        source_row_id="registry-row-solo-population-undisclosed",
        observation_id="obs-solo-population-undisclosed",
        field_family=DesignFieldFamily.POPULATION,
        field="target_population",
        source_field_name="目标人群",
        source_field_definition="Target population",
        source_text="登记资料未公开目标人群的完整定义。",
        disclosure_state=FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        source_locator=_locator(
            field_path="protocolSection.eligibilityModule",
            row="solo population undisclosed",
        ),
    )
    # 用未披露人群替换已接受人群，保留其余字段以形成“关键缺口”输入。
    return (blocked_population,) + tuple(
        item for item in accepted if item.field != "target_population"
    )


def _unresolved_critical_corpus() -> tuple[DesignObservation, ...]:
    """关键终点仍为候选审查态：不得作为已接受事实进入路径综合。"""

    accepted = _single_signature_corpus()
    unresolved_endpoint = _observation(
        row_id="design-row-solo-endpoint-unresolved",
        source_row_id="registry-row-solo-endpoint-unresolved",
        observation_id="obs-solo-endpoint-unresolved",
        field_family=DesignFieldFamily.ENDPOINT,
        field="primary_endpoint_definition",
        source_field_name="LDH 正常化",
        source_field_definition="Unresolved primary endpoint candidate",
        source_text="主要终点定义仍待审查确认。",
        review_state=FactReviewState.CANDIDATE,
        disclosure_state=FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
        source_locator=_locator(
            field_path="protocolSection.outcomesModule.primaryOutcomes[0].measure",
            row="solo endpoint unresolved",
        ),
    )
    return (unresolved_endpoint,) + tuple(
        item for item in accepted if item.field != "primary_endpoint_definition"
    )


def _synthesize(module: ModuleType, observations: Sequence[DesignObservation]) -> Any:
    synthesize = getattr(module, "synthesize_design_paths", None)
    assert callable(synthesize), "需要 synthesize_design_paths 综合入口"
    return synthesize(_INDICATION_ID, observations)


def _assert_failure_note_zh(exc: BaseException) -> None:
    message = str(exc)
    assert message.strip(), "失败必须给出说明"
    assert _CJK.search(message), f"失败说明应使用自然中文：{message!r}"
    for token in _INTERNAL_LEAKS:
        assert token not in message, f"失败说明泄漏内部标记 {token!r}: {message!r}"
    for token in _UNIQUE_RECOMMENDATION_TOKENS:
        assert token.lower() not in message.lower(), (
            f"失败说明不得改写成唯一推荐语义 {token!r}: {message!r}"
        )


def _assert_no_path_payload(result: Any) -> None:
    """若错误实现返回对象而非抛错，也不得带候选路径。"""

    for name in ("candidate_paths", "paths", "design_paths"):
        value = getattr(result, name, None)
        if value is None:
            continue
        assert tuple(value) == (), f"{name} 在失败场景必须为空"


def _walk(obj: Any) -> list[Any]:
    seen: list[Any] = [obj]
    if hasattr(obj, "model_dump"):
        seen.append(obj.model_dump())
    if isinstance(obj, dict):
        seen.extend(obj.values())
        seen.extend(obj.keys())
    elif isinstance(obj, Sequence) and not isinstance(obj, (str, bytes)):
        seen.extend(obj)
    return seen


def _contains_normalized_without_raw(result: Any) -> bool:
    stack = list(_walk(result))
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            keys = {str(key).casefold() for key in current}
            if keys & _NORMALIZED_KEYS:
                has_raw = any(
                    str(key).casefold() in {
                        "raw_value",
                        "raw_values",
                        "raw_row",
                        "raw_rows",
                        "unit",
                        "formula",
                        "source_text",
                    }
                    for key in current
                )
                if not has_raw:
                    return True
            stack.extend(current.values())
        elif hasattr(current, "model_dump"):
            stack.append(current.model_dump())
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes)):
            stack.extend(current)
    return False


def test_indication_only_cannot_produce_unique_recommendation() -> None:
    module = _synthesis()
    error_type = _error_type(module)
    synthesize = module.synthesize_design_paths

    with pytest.raises(error_type) as exc_info:
        synthesize(_INDICATION_ID, ())

    _assert_failure_note_zh(exc_info.value)
    message = str(exc_info.value)
    assert any(
        token in message for token in ("不足", "缺少", "无法", "不能", "至少两条", "观察")
    ), f"应说明证据不足以综合：{message!r}"


def test_empty_observation_sequence_fails_closed_without_draft_paths() -> None:
    module = _synthesis()
    error_type = _error_type(module)

    with pytest.raises(error_type) as exc_info:
        _synthesize(module, ())

    _assert_failure_note_zh(exc_info.value)


def test_single_design_signature_cannot_be_padded_into_two_paths() -> None:
    module = _synthesis()
    error_type = _error_type(module)
    corpus = _single_signature_corpus()

    with pytest.raises(error_type) as exc_info:
        _synthesize(module, corpus)

    _assert_failure_note_zh(exc_info.value)
    message = str(exc_info.value)
    assert any(
        token in message
        for token in ("一条", "不足", "无法", "不能", "至少两条", "签名")
    ), f"应明确拒绝单路径凑数：{message!r}"


def test_undisclosed_critical_facts_block_path_synthesis() -> None:
    module = _synthesis()
    error_type = _error_type(module)

    with pytest.raises(error_type) as exc_info:
        _synthesize(module, _undisclosed_critical_corpus())

    _assert_failure_note_zh(exc_info.value)
    message = str(exc_info.value)
    assert any(
        token in message for token in ("未公开", "缺失", "不足", "无法", "不能", "关键")
    ), f"应说明关键事实未披露导致停止综合：{message!r}"


def test_unresolved_critical_facts_block_path_synthesis() -> None:
    module = _synthesis()
    error_type = _error_type(module)

    with pytest.raises(error_type) as exc_info:
        _synthesize(module, _unresolved_critical_corpus())

    _assert_failure_note_zh(exc_info.value)
    message = str(exc_info.value)
    assert any(
        token in message for token in ("未解决", "待审", "不足", "无法", "不能", "关键")
    ), f"应说明关键事实未解决导致停止综合：{message!r}"


def test_no_product_specific_recommendation_without_background_contract() -> None:
    """即使错误实现返回了结果，也不得冒充产品特异建议。"""

    module = _synthesis()
    synthesize = module.synthesize_design_paths
    error_type = _error_type(module)

    try:
        result = synthesize(_INDICATION_ID, _single_signature_corpus())
    except error_type as exc:
        _assert_failure_note_zh(exc)
        blob = str(exc)
    else:
        _assert_no_path_payload(result)
        if hasattr(result, "model_dump"):
            blob = json.dumps(result.model_dump(), ensure_ascii=False)
        else:
            blob = str(result)

    for token in _PRODUCT_SPECIFIC_TOKENS:
        assert token.lower() not in blob.lower(), (
            f"无产品背景合同时不得输出产品特异建议：{token!r} in {blob!r}"
        )


def test_no_normalized_or_radar_scores_without_raw_reversible_values() -> None:
    module = _synthesis()
    synthesize = module.synthesize_design_paths
    error_type = _error_type(module)

    try:
        result = synthesize(_INDICATION_ID, _single_signature_corpus())
    except error_type as exc:
        _assert_failure_note_zh(exc)
        return

    assert not _contains_normalized_without_raw(result), (
        "无原始数值/单位/公式/原始行时不得生成归一化或雷达分数"
    )
    if hasattr(result, "model_dump"):
        dumped = result.model_dump()
        keys = {str(key).casefold() for key in dumped}
        # 最小实现可完全省略归一化视图。
        overlapping = keys & _NORMALIZED_KEYS
        assert not overlapping or not _contains_normalized_without_raw(result)


def _clone_single_signature_trial(
    *,
    trial_id: str,
    product_id: str,
    cohort_id: str,
    mutate_experimental_arm: str | None = None,
) -> tuple[DesignObservation, ...]:
    """复制单签名语料到新试验身份；可选只改试验组干预标点/别名。"""

    rows: list[DesignObservation] = []
    for item in _single_signature_corpus():
        payload = item.model_dump()
        old_trial = str(payload["trial_id"])
        payload["trial_id"] = trial_id
        payload["product_id"] = product_id
        payload["cohort_id"] = cohort_id
        for key in ("observation_id", "row_id", "source_row_id"):
            payload[key] = str(payload[key]).replace(old_trial, trial_id)
        payload["source_version_id"] = f"registry-version-{trial_id}-1"
        if mutate_experimental_arm is not None and payload["field"] == "experimental_arm":
            payload["source_text"] = mutate_experimental_arm
        rows.append(DesignObservation.model_validate(payload))
    return tuple(rows)


def _twin_signature_corpus(*, label: str, arm_text: str) -> tuple[DesignObservation, ...]:
    """构造一对同签名试验，并统一替换试验组干预文本。"""

    return _clone_single_signature_trial(
        trial_id=f"trial-{label}-1",
        product_id=f"product-{label}-1",
        cohort_id=f"cohort-{label}-1",
        mutate_experimental_arm=arm_text,
    ) + _clone_single_signature_trial(
        trial_id=f"trial-{label}-2",
        product_id=f"product-{label}-2",
        cohort_id=f"cohort-{label}-2",
        mutate_experimental_arm=arm_text,
    )


def test_cosmetic_punctuation_only_difference_cannot_pad_second_path() -> None:
    """凑数路径攻击：仅标点差异不得拆成两条“不同”设计签名。"""

    module = _synthesis()
    error_type = _error_type(module)

    path_a = _clone_single_signature_trial(
        trial_id="trial-punct-a1",
        product_id="product-punct-a1",
        cohort_id="cohort-punct-a1",
    ) + _clone_single_signature_trial(
        trial_id="trial-punct-a2",
        product_id="product-punct-a2",
        cohort_id="cohort-punct-a2",
    )
    # 与 path_a 设计事实相同，仅把句号换成英文句点。
    original_arm = next(
        item.source_text
        for item in path_a
        if item.field == "experimental_arm" and item.trial_id == "trial-punct-a1"
    )
    punctured_arm = original_arm.replace("。", ".")
    assert punctured_arm != original_arm

    path_b = _clone_single_signature_trial(
        trial_id="trial-punct-b1",
        product_id="product-punct-b1",
        cohort_id="cohort-punct-b1",
        mutate_experimental_arm=punctured_arm,
    ) + _clone_single_signature_trial(
        trial_id="trial-punct-b2",
        product_id="product-punct-b2",
        cohort_id="cohort-punct-b2",
        mutate_experimental_arm=punctured_arm,
    )

    with pytest.raises(error_type) as exc_info:
        _synthesize(module, path_a + path_b)

    _assert_failure_note_zh(exc_info.value)
    message = str(exc_info.value)
    assert any(
        token in message for token in ("一条", "不足", "无法", "不能", "至少两条", "签名")
    ), f"标点级差异凑数应失败关闭：{message!r}"


# 根因同族：句读级标点替换只改书写，不得拆出第二条设计签名。
_PUNCTUATION_EQUIVALENCE_CASES = (
    pytest.param("试验组接受静脉给药。", "试验组接受静脉给药.", id="句末句号"),
    pytest.param("试验组先负荷给药，随后维持给药。", "试验组先负荷给药, 随后维持给药。", id="逗号"),
    pytest.param("试验组先负荷给药；随后维持给药。", "试验组先负荷给药; 随后维持给药。", id="分号"),
    pytest.param("给药方式：静脉输注。", "给药方式: 静脉输注。", id="冒号非数值位"),
    pytest.param("试验组接受静脉给药—按体重调整。", "试验组接受静脉给药 按体重调整。", id="破折号"),
    pytest.param("试验组接受静脉给药（按体重）。", "试验组接受静脉给药(按体重)。", id="括号"),
)


@pytest.mark.parametrize(("plain_arm", "variant_arm"), _PUNCTUATION_EQUIVALENCE_CASES)
def test_root_punctuation_equivalence_cannot_pad_second_path(
    plain_arm: str,
    variant_arm: str,
) -> None:
    """根因同族标点攻击：句读级标点替换后仍只有一条设计签名。"""

    assert plain_arm != variant_arm
    module = _synthesis()
    error_type = _error_type(module)

    corpus = _twin_signature_corpus(
        label="punct-plain", arm_text=plain_arm
    ) + _twin_signature_corpus(label="punct-variant", arm_text=variant_arm)

    with pytest.raises(error_type) as exc_info:
        _synthesize(module, corpus)

    _assert_failure_note_zh(exc_info.value)
    message = str(exc_info.value)
    assert any(
        token in message for token in ("一条", "不足", "无法", "不能", "至少两条", "签名")
    ), f"句读级标点差异凑数应失败关闭：{message!r}"


# 数值边界控制：小数、范围、比较符、百分号与日期分隔符差异必须保持独立签名。
_NUMERIC_BOUNDARY_CASES = (
    pytest.param(
        "试验组目标变化为 -5 单位。", "试验组目标变化为 5 单位。",
        "-5", id="负号",
    ),
    pytest.param(
        "试验组阈值为 10‰。", "试验组阈值为 10。",
        "10‰", id="千分号",
    ),
    pytest.param(
        "试验组接受 0.5 mg 静脉给药。",
        "试验组接受 0.05 mg 静脉给药。",
        "0.5",
        id="小数位",
    ),
    pytest.param(
        "试验组接受 0.5 mg 静脉给药。",
        "试验组接受 5 mg 静脉给药。",
        "0.5",
        id="小数点消失",
    ),
    pytest.param(
        "试验组接受 5-10 mg 静脉给药。",
        "试验组接受 5.10 mg 静脉给药。",
        "5-10",
        id="范围与小数",
    ),
    pytest.param(
        "试验组接受 5-10 mg 静脉给药。",
        "试验组接受 5 10 mg 静脉给药。",
        "5-10",
        id="范围与空格",
    ),
    pytest.param(
        "试验组接受 ≤2 mg 静脉给药。",
        "试验组接受 ≥2 mg 静脉给药。",
        "≤2",
        id="比较符",
    ),
    pytest.param(
        "试验组接受 10% 剂量静脉给药。",
        "试验组接受 10 剂量静脉给药。",
        "10%",
        id="百分号",
    ),
    pytest.param(
        "试验组自 2024-01-05 起接受静脉给药。",
        "试验组自 2024 01 05 起接受静脉给药。",
        "2024-01-05",
        id="日期分隔符",
    ),
)


@pytest.mark.parametrize(("left_arm", "right_arm", "fragment"), _NUMERIC_BOUNDARY_CASES)
def test_numeric_boundary_difference_keeps_two_distinct_paths(
    left_arm: str,
    right_arm: str,
    fragment: str,
) -> None:
    """数值边界控制：标点折叠不得吞掉有意义的数值差异。"""

    module = _synthesis()
    result = _synthesize(
        module,
        _twin_signature_corpus(label="num-left", arm_text=left_arm)
        + _twin_signature_corpus(label="num-right", arm_text=right_arm),
    )

    paths = tuple(getattr(result, "candidate_paths", ()))
    assert len(paths) == 2, "数值边界不同的两条签名应各自形成一条候选路径"
    signatures = {str(path.design_signature) for path in paths}
    assert len(signatures) == 2, "两条数值边界路径必须对应两个不同设计签名"

    joined_summary = "\n".join(str(path.summary_zh) for path in paths)
    assert fragment in joined_summary, (
        f"数值片段 {fragment!r} 不得在用户可见文本中被标点折叠破坏：{joined_summary!r}"
    )


def test_normalization_distinguishes_numeric_role_from_sentence_role() -> None:
    """同一标点字符的数值角色与句子角色必须被区分处理。"""

    module = _synthesis()
    normalize = getattr(module, "_normalize_text", None)
    assert callable(normalize), "需要 _normalize_text 归一入口"

    # 句子角色：句末句号与英文句点等价。
    assert normalize("给药。") == normalize("给药.")
    assert normalize("第 26 周 LDH 正常化。") == normalize("第 26 周 LDH 正常化.")

    # 数值角色：小数点、范围、比值与百分号必须保留。
    assert "0.5" in normalize("0.5 mg")
    assert "5-10" in normalize("5-10 mg")
    assert "%" in normalize("10 % 剂量")
    assert normalize("0.5 mg") != normalize("5 mg")
    assert normalize("0.5 mg") != normalize("0.05 mg")
    assert normalize("5-10 mg") != normalize("5.10 mg")
    assert normalize("5-10 mg") != normalize("5 10 mg")
    assert normalize("≤2 mg") != normalize("≥2 mg")
    assert normalize("1:1 随机") != normalize("1 1 随机")
    assert normalize("10% 剂量") != normalize("10 剂量")
    assert normalize("10%-20% 剂量") != normalize("10% 20% 剂量")


@pytest.mark.parametrize("field", ["experimental_arm", "primary_endpoint_definition"])
def test_same_field_distinct_observations_cannot_be_first_wins_path_evidence(field: str) -> None:
    module = _synthesis()
    rows = (_twin_signature_corpus(label="ambiguous", arm_text="干预甲")
            + _twin_signature_corpus(label="peer", arm_text="干预乙"))
    chosen = next(row for row in rows if row.field == field)
    other = chosen.model_copy(update={
        "observation_id": "zz-distinct-evidence", "row_id": "zz-distinct-evidence",
        "source_row_id": "zz-distinct-evidence", "source_text": "另一独立设计安排",
    })
    # A path cannot claim both inputs but derive its identity from the arbitrary
    # first ID. This narrow synthesis rejects unknown combinations, not the
    # searchable source-precedent library or either original observation.
    for corpus in ((*rows, other), (other, *reversed(rows))):
        with pytest.raises(_error_type(module), match="多个.*观察|组合关系"):
            _synthesize(module, corpus)


def test_same_field_equivalent_observation_does_not_invent_another_design() -> None:
    module = _synthesis()
    rows = _twin_signature_corpus(label="duplicate", arm_text="干预甲")
    chosen = next(row for row in rows if row.field == "experimental_arm")
    duplicate = chosen.model_copy(update={
        "observation_id": "zz-equivalent", "row_id": "zz-equivalent",
        "source_row_id": "zz-equivalent",
    })
    # The ordinary one-signature insufficiency remains, not a false ambiguity.
    with pytest.raises(_error_type(module), match="一条独立设计签名"):
        _synthesize(module, (*rows, duplicate))


def test_one_multi_trial_signature_plus_lone_divergent_trial_cannot_pad() -> None:
    """凑数路径攻击：一条多试验签名 + 单试验偏离不得凑出第二条路径。"""

    from tests.reports.c import test_multiple_design_paths as multi

    module = _synthesis()
    error_type = _error_type(module)
    path_a = tuple(
        item for item in multi._CORPUS if item.trial_id in multi._PATH_A_TRIALS
    )
    lone = tuple(item for item in multi._CORPUS if item.trial_id == multi._TRIAL_BETA)
    assert path_a and lone

    with pytest.raises(error_type) as exc_info:
        _synthesize(module, path_a + lone)

    _assert_failure_note_zh(exc_info.value)
    message = str(exc_info.value)
    assert any(
        token in message for token in ("一条", "不足", "无法", "不能", "至少两条", "签名")
    ), f"单试验不得被凑成第二路径：{message!r}"


def test_successful_multi_path_result_has_no_product_specific_speculation() -> None:
    """产品特异臆测攻击：成功多路径结果仍不得给出自有产品建议。"""

    from tests.reports.c import test_multiple_design_paths as multi

    module = _synthesis()
    result = _synthesize(module, multi._CORPUS)
    if hasattr(result, "model_dump"):
        blob = json.dumps(result.model_dump(), ensure_ascii=False)
    else:
        blob = str(result)

    for token in _PRODUCT_SPECIFIC_TOKENS:
        assert token.lower() not in blob.lower(), (
            f"成功结果仍不得输出产品特异建议：{token!r} in {blob!r}"
        )
    # 也不得把内部 product_id 写成面向用户的推荐话术锚点。
    for product_id in {
        multi._PRODUCT_C5_LONG,
        multi._PRODUCT_ORAL,
        multi._PRODUCT_EARLY,
    }:
        assert product_id not in blob, (
            f"用户可见综合结果不得直接泄漏 product_id：{product_id!r}"
        )


def test_successful_multi_path_result_omits_rawless_normalized_views() -> None:
    """无原始值归一化攻击：成功路径同样不得冒出雷达/归一化分数。"""

    from tests.reports.c import test_multiple_design_paths as multi

    module = _synthesis()
    result = _synthesize(module, multi._CORPUS)
    assert not _contains_normalized_without_raw(result), (
        "成功综合在无原始数值合同下不得生成归一化/雷达分数"
    )
    if hasattr(result, "model_dump"):
        dumped = result.model_dump()
        keys = {str(key).casefold() for key in dumped}
        overlapping = keys & _NORMALIZED_KEYS
        assert not overlapping, f"成功结果不得暴露归一化视图字段：{sorted(overlapping)}"


def test_shared_c_package_exports_remain_usable_after_synthesis() -> None:
    """共享合同回归：c 包导出仍暴露既有门槛/投影入口与综合入口。"""

    import ci_workflow.reports.c as reports_c

    required = (
        "DesignObservation",
        "evaluate_design_gate",
        "validate_design_observation",
        "project_eligibility_drilldown",
        "project_design_map",
        "project_endpoint_definition_timepoint",
        "project_trial_dossier",
        "synthesize_design_paths",
        "DesignSynthesisError",
        "CandidateDesignPath",
        "DesignPathSynthesisResult",
    )
    for name in required:
        assert hasattr(reports_c, name), f"c 包缺少共享导出 {name}"
        assert name in getattr(reports_c, "__all__", ()), (
            f"c 包 __all__ 未声明共享导出 {name}"
        )

    # 既有观察合同仍可校验；综合入口保持可调用。
    sample = _single_signature_corpus()[0]
    validated = reports_c.validate_design_observation(sample)
    assert validated.observation_id == sample.observation_id
    assert callable(reports_c.synthesize_design_paths)
    assert issubclass(reports_c.DesignSynthesisError, Exception)
