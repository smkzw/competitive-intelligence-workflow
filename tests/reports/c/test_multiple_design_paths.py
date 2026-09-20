"""Task 7.4 C 类多路径综合：至少两条证据路径、前提、权衡与观察绑定 RED。

合同断言（先失败后通过；本文件不提供实现 stub）：
- 综合入口位于 ``reports.c.synthesis.synthesize_design_paths``；
- 输入为适应症身份 + 已校验 ``DesignObservation``；成功结果至少含两条不同设计签名的
  候选路径，且每条绑定真实观察/试验身份、适用前提与主要权衡；
- 结果分层：事实模式 / 重要差异 / 异常点（来源事实层）与候选路径（综合层）分离；
- 共同签名的多试验形成模式；仅单试验且偏离共同模式的事实可标为异常点，不得隐含优劣；
- 路径身份与内容在输入重排下保持稳定；展示顺序可确定，但不得含排名/得分/最佳语义；
- 面向用户字段使用自然中文临床试验表达，不得泄漏内部状态码或工程标签。
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from types import ModuleType
from typing import Any

import pytest

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.gates.models import ConflictDisposition, DisclosureMaturity, SourceRole
from ci_workflow.reports.c.contracts import DesignFieldFamily, DesignObservation

_INDICATION_ID = "indication-pnh"

_TRIAL_ALPHA = "trial-alpha"
_TRIAL_GAMMA = "trial-gamma"
_TRIAL_BETA = "trial-beta"
_TRIAL_DELTA = "trial-delta"
_TRIAL_EPSILON = "trial-epsilon"

_PRODUCT_C5_LONG = "product-c5-long-acting"
_PRODUCT_C5_LONG_B = "product-c5-long-acting-b"
_PRODUCT_ORAL = "product-oral-factor-b"
_PRODUCT_ORAL_B = "product-oral-factor-b-b"
_PRODUCT_EARLY = "product-early-exploratory"

_CJK = re.compile(r"[\u3400-\u9fff]")
_INTERNAL_LEAKS = (
    "DesignSynthesisError",
    "DesignFieldFamily",
    "NOT_PUBLICLY_DISCLOSED",
    "not_publicly_disclosed",
    "REPORTED_VALUE",
    "reported_value",
    "OPEN_CONFLICT_PRESERVED",
    "clinical_trial_registry",
    "field_family",
    "source_role",
    "c_missing_",
    "synthesize_design_paths",
    "candidate_paths",
    "observation_id",
    "path_id",
    "BLOCKED",
    "PASSED",
)

_RANKING_TOKENS = (
    "最佳",
    "首选",
    "第一名",
    "唯一推荐",
    "最优",
    "推荐方案",
    "winner",
    "best",
    "preferred",
    "rank",
    "score",
)

_FORBIDDEN_RESULT_KEYS = {
    "rank",
    "ranking",
    "score",
    "scores",
    "winner",
    "best",
    "preferred",
    "recommendation_rank",
    "unique_recommendation",
    "recommended_path_id",
}


def _synthesis() -> ModuleType:
    """延迟导入计划中的 C 类多路径综合；实现前每个用例精确失败。"""

    import importlib

    try:
        return importlib.import_module("ci_workflow.reports.c.synthesis")
    except ModuleNotFoundError as exc:
        pytest.fail(f"C 类多路径综合尚未实现：{exc}", pytrace=False)


def _locator(*, trial_id: str, field_path: str, row: str) -> EvidenceLocator:
    nct = {
        _TRIAL_ALPHA: "NCT02912468",
        _TRIAL_GAMMA: "NCT00000003",
        _TRIAL_BETA: "NCT00000002",
        _TRIAL_DELTA: "NCT00000004",
        _TRIAL_EPSILON: "NCT00000005",
    }[trial_id]
    return EvidenceLocator(
        document_role="clinical-trial-registry",
        field_path=field_path,
        heading="Study Design",
        table="Design Facts",
        row=row,
        column="Value",
        url=f"https://clinicaltrials.gov/study/{nct}#design",
        paragraph="Design",
    )


def _observation(**overrides: object) -> DesignObservation:
    """构造一条已接受的登记来源设计观察。"""

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "row_id": "design-row-default",
        "source_row_id": "registry-row-default",
        "observation_id": "obs-default",
        "product_id": _PRODUCT_C5_LONG,
        "trial_id": _TRIAL_ALPHA,
        "cohort_id": "cohort-alpha",
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
        "source_version_id": "registry-version-alpha-1",
        "source_locator": _locator(
            trial_id=_TRIAL_ALPHA,
            field_path="protocolSection.eligibilityModule",
            row="Population",
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


def _trial_core(
    *,
    trial_id: str,
    product_id: str,
    cohort_id: str,
    population_text: str,
    grouping_text: str,
    randomization: str,
    blinding: str,
    intervention_text: str,
    control_text: str,
    dose_text: str,
    endpoint_name: str,
    endpoint_definition: str,
    endpoint_text: str,
    timepoint: str,
    timepoint_text: str,
    visit_text: str,
    stage: str = "III",
    development_role: str = "关键注册试验",
    extra: Sequence[DesignObservation] = (),
) -> tuple[DesignObservation, ...]:
    """为一条试验生成支撑设计签名的核心观察集合。"""

    version = f"registry-version-{trial_id}-1"
    base_kwargs: dict[str, object] = {
        "product_id": product_id,
        "trial_id": trial_id,
        "cohort_id": cohort_id,
        "source_version_id": version,
    }
    rows = (
        _observation(
            **base_kwargs,
            row_id=f"design-row-{trial_id}-population",
            source_row_id=f"registry-row-{trial_id}-population",
            observation_id=f"obs-{trial_id}-population",
            group_id="group-all-enrolled",
            field_family=DesignFieldFamily.POPULATION,
            field="target_population",
            source_field_name="目标人群",
            source_field_definition="Target population",
            source_text=population_text,
            assessment_timepoint="筛选期",
            stage=stage,
            development_role=development_role,
            source_locator=_locator(
                trial_id=trial_id,
                field_path="protocolSection.eligibilityModule",
                row=f"{trial_id} population",
            ),
        ),
        _observation(
            **base_kwargs,
            row_id=f"design-row-{trial_id}-grouping",
            source_row_id=f"registry-row-{trial_id}-grouping",
            observation_id=f"obs-{trial_id}-grouping",
            group_id="group-all-enrolled",
            field_family=DesignFieldFamily.GROUPING,
            field="arm_randomization_blinding",
            source_field_name="分组/随机/盲法",
            source_field_definition="Randomization and blinding",
            source_text=grouping_text,
            randomization=randomization,
            blinding=blinding,
            stage=stage,
            development_role=development_role,
            source_locator=_locator(
                trial_id=trial_id,
                field_path="protocolSection.designModule",
                row=f"{trial_id} grouping",
            ),
        ),
        _observation(
            **base_kwargs,
            row_id=f"design-row-{trial_id}-intervention",
            source_row_id=f"registry-row-{trial_id}-intervention",
            observation_id=f"obs-{trial_id}-intervention",
            group_id="group-experimental",
            field_family=DesignFieldFamily.INTERVENTION,
            field="experimental_arm",
            source_field_name="试验组干预",
            source_field_definition="Experimental intervention",
            source_text=intervention_text,
            stage=stage,
            development_role=development_role,
            source_locator=_locator(
                trial_id=trial_id,
                field_path="protocolSection.armsInterventionsModule",
                row=f"{trial_id} intervention",
            ),
        ),
        _observation(
            **base_kwargs,
            row_id=f"design-row-{trial_id}-control",
            source_row_id=f"registry-row-{trial_id}-control",
            observation_id=f"obs-{trial_id}-control",
            group_id="group-control",
            field_family=DesignFieldFamily.INTERVENTION,
            field="control_arm",
            source_field_name="对照组干预",
            source_field_definition="Control intervention",
            source_text=control_text,
            stage=stage,
            development_role=development_role,
            source_locator=_locator(
                trial_id=trial_id,
                field_path="protocolSection.armsInterventionsModule",
                row=f"{trial_id} control",
            ),
        ),
        _observation(
            **base_kwargs,
            row_id=f"design-row-{trial_id}-dose",
            source_row_id=f"registry-row-{trial_id}-dose",
            observation_id=f"obs-{trial_id}-dose",
            group_id="group-experimental",
            field_family=DesignFieldFamily.DOSE_SCHEDULE,
            field="dosing_regimen",
            source_field_name="给药方案",
            source_field_definition="Dosing regimen",
            source_text=dose_text,
            stage=stage,
            development_role=development_role,
            source_locator=_locator(
                trial_id=trial_id,
                field_path="protocolSection.armsInterventionsModule.dosing",
                row=f"{trial_id} dose",
            ),
        ),
        _observation(
            **base_kwargs,
            row_id=f"design-row-{trial_id}-endpoint",
            source_row_id=f"registry-row-{trial_id}-endpoint",
            observation_id=f"obs-{trial_id}-endpoint",
            group_id="group-all-enrolled",
            field_family=DesignFieldFamily.ENDPOINT,
            field="primary_endpoint_definition",
            source_field_name=endpoint_name,
            source_field_definition=endpoint_definition,
            source_text=endpoint_text,
            stage=stage,
            development_role=development_role,
            source_locator=_locator(
                trial_id=trial_id,
                field_path="protocolSection.outcomesModule.primaryOutcomes[0].measure",
                row=f"{trial_id} endpoint",
            ),
        ),
        _observation(
            **base_kwargs,
            row_id=f"design-row-{trial_id}-timepoint",
            source_row_id=f"registry-row-{trial_id}-timepoint",
            observation_id=f"obs-{trial_id}-timepoint",
            group_id="group-all-enrolled",
            field_family=DesignFieldFamily.TIMEPOINT,
            field="primary_endpoint_timepoint",
            source_field_name="主要终点时间点",
            source_field_definition="Primary endpoint assessment timepoint",
            source_text=timepoint_text,
            assessment_timepoint=timepoint,
            stage=stage,
            development_role=development_role,
            source_locator=_locator(
                trial_id=trial_id,
                field_path="protocolSection.outcomesModule.primaryOutcomes[0].timeFrame",
                row=f"{trial_id} timepoint",
            ),
        ),
        _observation(
            **base_kwargs,
            row_id=f"design-row-{trial_id}-visit",
            source_row_id=f"registry-row-{trial_id}-visit",
            observation_id=f"obs-{trial_id}-visit",
            group_id="group-all-enrolled",
            field_family=DesignFieldFamily.OPERATIONAL,
            field="visit_schedule",
            source_field_name="访视安排",
            source_field_definition="Visit schedule",
            source_text=visit_text,
            assessment_timepoint=timepoint,
            stage=stage,
            development_role=development_role,
            source_locator=_locator(
                trial_id=trial_id,
                field_path="protocolSection.scheduleModule",
                row=f"{trial_id} visit",
            ),
        ),
    )
    return rows + tuple(extra)


def _multi_path_corpus() -> tuple[DesignObservation, ...]:
    """确定性多试验语料：两条可证据支撑的设计签名 + 共同模式 + 单试验异常点。

    路径 A（静脉长效 C5 + 活性对照 + 第26周 LDH）：trial-alpha、trial-gamma
    路径 B（口服旁路抑制 + 安慰剂对照 + 第12周血红蛋白）：trial-beta、trial-delta
    异常点：trial-epsilon 单臂开放、第4周探索性终点，仅单试验出现。
    """

    path_a_alpha = _trial_core(
        trial_id=_TRIAL_ALPHA,
        product_id=_PRODUCT_C5_LONG,
        cohort_id="cohort-alpha",
        population_text="确诊 PNH 的成人受试者，允许补体抑制剂经治或初治。",
        grouping_text="1:1 随机、双盲、平行对照。",
        randomization="1:1 随机",
        blinding="双盲",
        intervention_text="长效补体 C5 抑制剂按体重静脉给药。",
        control_text="短效补体 C5 抑制剂按标签静脉给药。",
        dose_text="负荷后每 8 周静脉给药一次。",
        endpoint_name="LDH 正常化",
        endpoint_definition="Proportion of subjects with LDH ≤1×ULN at Week 26",
        endpoint_text="第 26 周 LDH 正常化（≤1×ULN）的受试者比例。",
        timepoint="第26周",
        timepoint_text="主要终点评估时间点：第 26 周。",
        visit_text="筛选、随机、第 2/4/8/16/26 周访视，治疗结束后随访至第 52 周。",
    )
    path_a_gamma = _trial_core(
        trial_id=_TRIAL_GAMMA,
        product_id=_PRODUCT_C5_LONG_B,
        cohort_id="cohort-gamma",
        population_text="确诊 PNH 的成人受试者，允许补体抑制剂经治或初治。",
        grouping_text="1:1 随机、双盲、平行对照。",
        randomization="1:1 随机",
        blinding="双盲",
        intervention_text="长效补体 C5 抑制剂按体重静脉给药。",
        control_text="短效补体 C5 抑制剂按标签静脉给药。",
        dose_text="负荷后每 8 周静脉给药一次。",
        endpoint_name="LDH 正常化",
        endpoint_definition="Proportion of subjects with LDH ≤1×ULN at Week 26",
        endpoint_text="第 26 周 LDH 正常化（≤1×ULN）的受试者比例。",
        timepoint="第26周",
        timepoint_text="主要终点评估时间点：第 26 周。",
        visit_text="筛选、随机、第 2/4/8/16/26 周访视，治疗结束后随访至第 52 周。",
    )
    path_b_beta = _trial_core(
        trial_id=_TRIAL_BETA,
        product_id=_PRODUCT_ORAL,
        cohort_id="cohort-beta",
        population_text="确诊 PNH 的成人受试者，主要纳入补体抑制剂初治人群。",
        grouping_text="2:1 随机、双盲、安慰剂平行对照。",
        randomization="2:1 随机",
        blinding="双盲",
        intervention_text="口服补体旁路因子 B 小分子抑制剂。",
        control_text="匹配安慰剂口服。",
        dose_text="每日两次口服，连续给药。",
        endpoint_name="血红蛋白升高",
        endpoint_definition=(
            "Proportion of subjects with hemoglobin increase ≥2 g/dL from baseline "
            "at Week 12"
        ),
        endpoint_text="第 12 周血红蛋白较基线升高 ≥2 g/dL 的受试者比例。",
        timepoint="第12周",
        timepoint_text="主要终点评估时间点：第 12 周。",
        visit_text="筛选、随机、第 2/4/8/12 周访视，此后按方案随访。",
    )
    path_b_delta = _trial_core(
        trial_id=_TRIAL_DELTA,
        product_id=_PRODUCT_ORAL_B,
        cohort_id="cohort-delta",
        population_text="确诊 PNH 的成人受试者，主要纳入补体抑制剂初治人群。",
        grouping_text="2:1 随机、双盲、安慰剂平行对照。",
        randomization="2:1 随机",
        blinding="双盲",
        intervention_text="口服补体旁路因子 B 小分子抑制剂。",
        control_text="匹配安慰剂口服。",
        dose_text="每日两次口服，连续给药。",
        endpoint_name="血红蛋白升高",
        endpoint_definition=(
            "Proportion of subjects with hemoglobin increase ≥2 g/dL from baseline "
            "at Week 12"
        ),
        endpoint_text="第 12 周血红蛋白较基线升高 ≥2 g/dL 的受试者比例。",
        timepoint="第12周",
        timepoint_text="主要终点评估时间点：第 12 周。",
        visit_text="筛选、随机、第 2/4/8/12 周访视，此后按方案随访。",
    )
    outlier = _trial_core(
        trial_id=_TRIAL_EPSILON,
        product_id=_PRODUCT_EARLY,
        cohort_id="cohort-epsilon",
        population_text="确诊 PNH 的成人受试者，单臂探索性入组。",
        grouping_text="单臂、开放标签、无随机对照。",
        randomization="无随机",
        blinding="开放标签",
        intervention_text="早期探索性补体通路干预静脉给药。",
        control_text="无对照臂；本试验为单臂设计。",
        dose_text="每周静脉给药一次，共 4 周。",
        endpoint_name="探索性生物标志物变化",
        endpoint_definition="Exploratory change in biomarker panel at Week 4",
        endpoint_text="第 4 周探索性生物标志物组合相对基线的变化。",
        timepoint="第4周",
        timepoint_text="主要探索性评估时间点：第 4 周。",
        visit_text="筛选后仅安排第 1/2/4 周访视。",
        stage="I/II",
        development_role="早期探索试验",
    )
    return path_a_alpha + path_a_gamma + path_b_beta + path_b_delta + outlier


_CORPUS = _multi_path_corpus()
_CORPUS_BY_ID = {item.observation_id: item for item in _CORPUS}
_ALL_OBSERVATION_IDS = frozenset(_CORPUS_BY_ID)
_ALL_TRIAL_IDS = frozenset(item.trial_id for item in _CORPUS)

_PATH_A_TRIALS = frozenset({_TRIAL_ALPHA, _TRIAL_GAMMA})
_PATH_B_TRIALS = frozenset({_TRIAL_BETA, _TRIAL_DELTA})
_OUTLIER_TRIALS = frozenset({_TRIAL_EPSILON})


def _synthesize(module: ModuleType, observations: Sequence[DesignObservation]) -> Any:
    synthesize = getattr(module, "synthesize_design_paths", None)
    assert callable(synthesize), "需要 synthesize_design_paths 综合入口"
    return synthesize(_INDICATION_ID, observations)


def _as_sequence(value: Any, *, field_name: str) -> tuple[Any, ...]:
    assert value is not None, f"缺少字段 {field_name}"
    if isinstance(value, (str, bytes)):
        pytest.fail(f"{field_name} 必须是序列而非纯文本")
    assert isinstance(value, Sequence), f"{field_name} 必须是序列"
    return tuple(value)


def _paths(result: Any) -> tuple[Any, ...]:
    for name in ("candidate_paths", "paths", "design_paths"):
        value = getattr(result, name, None)
        if value is not None:
            return _as_sequence(value, field_name=name)
    pytest.fail("综合结果缺少候选路径集合（candidate_paths）")


def _patterns(result: Any) -> tuple[Any, ...]:
    for name in ("patterns", "fact_patterns", "sourced_patterns"):
        value = getattr(result, name, None)
        if value is not None:
            return _as_sequence(value, field_name=name)
    pytest.fail("综合结果缺少事实模式集合（patterns）")


def _differences(result: Any) -> tuple[Any, ...]:
    for name in ("differences", "design_differences", "sourced_differences"):
        value = getattr(result, name, None)
        if value is not None:
            return _as_sequence(value, field_name=name)
    pytest.fail("综合结果缺少重要差异集合（differences）")


def _outliers(result: Any) -> tuple[Any, ...]:
    for name in ("outliers", "design_outliers", "sourced_outliers"):
        value = getattr(result, name, None)
        if value is not None:
            return _as_sequence(value, field_name=name)
    pytest.fail("综合结果缺少异常点集合（outliers）")


def _item_text(item: Any, *names: str) -> str:
    for name in names:
        value = getattr(item, name, None)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            parts = [part.strip() for part in value if isinstance(part, str) and part.strip()]
            if parts:
                return "\n".join(parts)
    pytest.fail(f"条目缺少用户可见中文文本字段：{names}")


def _id_set(item: Any, *names: str) -> set[str]:
    for name in names:
        value = getattr(item, name, None)
        if value is None:
            continue
        if isinstance(value, str) and value.strip():
            return {value.strip()}
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            ids = {str(part).strip() for part in value if str(part).strip()}
            if ids:
                return ids
    pytest.fail(f"条目缺少身份绑定字段：{names}")


def _path_id(path: Any) -> str:
    for name in ("path_id", "design_path_id", "path_identity", "identity"):
        value = getattr(path, name, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    pytest.fail("候选路径缺少稳定 path_id / path_identity")


def _path_signature(path: Any) -> str:
    for name in ("design_signature", "signature", "signature_id", "design_signature_id"):
        value = getattr(path, name, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return _item_text(path, "summary_zh", "path_summary_zh", "statement_zh", "summary")


def _assert_natural_zh(text: str) -> None:
    assert _CJK.search(text), f"用户可见文本应含中文：{text!r}"
    for token in _INTERNAL_LEAKS:
        assert token not in text, f"用户可见文本泄漏内部标记 {token!r}: {text!r}"
    for token in _RANKING_TOKENS:
        assert token.lower() not in text.lower(), f"用户可见文本含排名/最佳语义 {token!r}: {text!r}"


def _assert_bound_to_corpus(item: Any) -> None:
    observation_ids = _id_set(
        item,
        "observation_ids",
        "supporting_observation_ids",
        "evidence_observation_ids",
        "sourced_observation_ids",
    )
    trial_ids = _id_set(
        item,
        "trial_ids",
        "supporting_trial_ids",
        "evidence_trial_ids",
        "sourced_trial_ids",
    )
    assert observation_ids <= _ALL_OBSERVATION_IDS, (
        f"出现未输入的观察身份：{sorted(observation_ids - _ALL_OBSERVATION_IDS)}"
    )
    assert trial_ids <= _ALL_TRIAL_IDS, (
        f"出现未输入的试验身份：{sorted(trial_ids - _ALL_TRIAL_IDS)}"
    )
    assert observation_ids, "必须绑定至少一条观察身份"
    assert trial_ids, "必须绑定至少一个试验身份"
    for observation_id in observation_ids:
        assert _CORPUS_BY_ID[observation_id].trial_id in trial_ids


def _dump_keys(result: Any) -> set[str]:
    if hasattr(result, "model_dump"):
        dumped = result.model_dump()
        assert isinstance(dumped, dict)
        return {str(key).casefold() for key in dumped}
    return {name.casefold() for name in dir(result) if not name.startswith("_")}


def _collect_user_texts(items: Iterable[Any]) -> list[str]:
    texts: list[str] = []
    for item in items:
        for name in (
            "statement_zh",
            "summary_zh",
            "path_summary_zh",
            "assumption_zh",
            "assumptions_zh",
            "tradeoff_zh",
            "tradeoffs_zh",
            "label_zh",
            "note_zh",
        ):
            value = getattr(item, name, None)
            if isinstance(value, str) and value.strip():
                texts.append(value)
            elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                texts.extend(
                    part for part in value if isinstance(part, str) and part.strip()
                )
    return texts


def test_synthesis_module_exposes_design_path_entry() -> None:
    module = _synthesis()
    assert callable(
        getattr(module, "synthesize_design_paths", None)
    ), "需要 synthesize_design_paths 综合入口"
    assert issubclass(
        getattr(module, "DesignSynthesisError", type(None)), Exception
    ), "需要 DesignSynthesisError 失败类型"


def test_successful_synthesis_yields_at_least_two_evidence_backed_paths() -> None:
    module = _synthesis()
    result = _synthesize(module, _CORPUS)
    paths = _paths(result)

    indication = getattr(result, "indication_id", None)
    if indication is not None:
        assert indication == _INDICATION_ID

    assert len(paths) >= 2, "成功综合必须至少提供两条候选路径"

    path_ids = {_path_id(path) for path in paths}
    signatures = {_path_signature(path) for path in paths}
    assert len(path_ids) == len(paths), "路径身份必须唯一"
    assert len(signatures) >= 2, "候选路径必须对应至少两个不同设计签名"

    for path in paths:
        _assert_bound_to_corpus(path)
        summary = _item_text(path, "summary_zh", "path_summary_zh", "statement_zh", "summary")
        assumptions = _item_text(
            path,
            "assumptions_zh",
            "assumption_zh",
            "applicable_assumptions_zh",
            "preconditions_zh",
        )
        tradeoffs = _item_text(
            path,
            "tradeoffs_zh",
            "tradeoff_zh",
            "major_tradeoffs_zh",
            "trade_off_zh",
        )
        _assert_natural_zh(summary)
        _assert_natural_zh(assumptions)
        _assert_natural_zh(tradeoffs)


def test_paths_assumptions_and_tradeoffs_reflect_disclosed_differences() -> None:
    """路径前提/权衡必须能落到语料中已公开差异，而不是模型空想。"""

    module = _synthesis()
    result = _synthesize(module, _CORPUS)
    paths = _paths(result)
    differences = _differences(result)

    assert differences, "多签名语料应产生至少一条重要差异"

    for item in differences:
        _assert_bound_to_corpus(item)
        _assert_natural_zh(_item_text(item, "statement_zh", "summary_zh", "label_zh"))

    joined_path_text = "\n".join(_collect_user_texts(paths)).lower()
    anchors = ("静脉", "口服", "安慰剂", "活性", "26", "12", "ldh", "血红蛋白")
    assert sum(1 for token in anchors if token in joined_path_text) >= 3, (
        "路径前提/权衡应反映语料中的公开差异（途径/对照/终点时间窗等）"
    )


def test_common_signature_forms_pattern_and_single_trial_divergence_is_outlier() -> None:
    module = _synthesis()
    result = _synthesize(module, _CORPUS)
    patterns = _patterns(result)
    outliers = _outliers(result)
    paths = _paths(result)

    assert patterns, "共同签名的多试验应形成事实模式"
    assert outliers, "仅单试验偏离共同模式的事实应形成异常点"

    pattern_trial_sets = [
        _id_set(item, "trial_ids", "supporting_trial_ids", "sourced_trial_ids")
        for item in patterns
    ]
    assert any(len(trials) >= 2 for trials in pattern_trial_sets), (
        "至少一条模式应绑定多个试验"
    )
    assert any(
        trials & _PATH_A_TRIALS == _PATH_A_TRIALS
        or trials & _PATH_B_TRIALS == _PATH_B_TRIALS
        for trials in pattern_trial_sets
    ), "模式应覆盖同签名的成对试验"

    outlier_trial_sets = [
        _id_set(item, "trial_ids", "supporting_trial_ids", "sourced_trial_ids")
        for item in outliers
    ]
    assert any(
        trials == _OUTLIER_TRIALS or bool(trials & _OUTLIER_TRIALS)
        for trials in outlier_trial_sets
    ), "异常点应绑定仅单试验出现的偏离设计（trial-epsilon）"

    for item in (*patterns, *outliers):
        _assert_bound_to_corpus(item)
        _assert_natural_zh(_item_text(item, "statement_zh", "summary_zh", "label_zh"))

    for text in _collect_user_texts(outliers):
        _assert_natural_zh(text)

    assert len(paths) >= 2


def test_fact_layer_is_separated_from_path_synthesis_layer() -> None:
    module = _synthesis()
    result = _synthesize(module, _CORPUS)
    patterns = _patterns(result)
    differences = _differences(result)
    outliers = _outliers(result)
    paths = _paths(result)

    assert patterns is not paths
    assert differences is not paths
    assert outliers is not paths
    assert len(patterns) + len(differences) + len(outliers) >= 3
    assert len(paths) >= 2


def test_input_reordering_preserves_path_identity_and_bindings() -> None:
    module = _synthesis()
    baseline = _synthesize(module, _CORPUS)
    reordered = _synthesize(module, tuple(reversed(_CORPUS)))

    def _path_snapshot(path: Any) -> tuple[object, ...]:
        return (
            _path_id(path),
            _path_signature(path),
            frozenset(
                _id_set(
                    path,
                    "observation_ids",
                    "supporting_observation_ids",
                    "evidence_observation_ids",
                )
            ),
            frozenset(
                _id_set(
                    path,
                    "trial_ids",
                    "supporting_trial_ids",
                    "evidence_trial_ids",
                )
            ),
            _item_text(path, "summary_zh", "path_summary_zh", "statement_zh", "summary"),
            _item_text(
                path,
                "assumptions_zh",
                "assumption_zh",
                "applicable_assumptions_zh",
                "preconditions_zh",
            ),
            _item_text(
                path,
                "tradeoffs_zh",
                "tradeoff_zh",
                "major_tradeoffs_zh",
                "trade_off_zh",
            ),
        )

    assert sorted(_path_snapshot(path) for path in _paths(reordered)) == sorted(
        _path_snapshot(path) for path in _paths(baseline)
    )
    assert sorted(_collect_user_texts(_patterns(reordered))) == sorted(
        _collect_user_texts(_patterns(baseline))
    )


def test_result_has_no_ranking_or_unique_recommendation_semantics() -> None:
    module = _synthesis()
    result = _synthesize(module, _CORPUS)
    keys = _dump_keys(result)
    forbidden = {key.casefold() for key in _FORBIDDEN_RESULT_KEYS}
    assert keys.isdisjoint(forbidden), (
        f"结果不得暴露排名/唯一推荐字段：{sorted(keys & forbidden)}"
    )

    for path in _paths(result):
        path_keys = _dump_keys(path)
        assert path_keys.isdisjoint(forbidden)
        for text in _collect_user_texts((path,)):
            _assert_natural_zh(text)


def test_more_supporting_trials_do_not_create_hidden_ranking() -> None:
    """隐性排名攻击：扩大某一签名的试验数不得改写为优先/更优路径。"""

    module = _synthesis()
    baseline = _synthesize(module, _CORPUS)

    boosted_rows: list[DesignObservation] = []
    for item in _CORPUS:
        if item.trial_id != _TRIAL_GAMMA:
            continue
        payload = item.model_dump()
        payload["trial_id"] = "trial-zeta"
        payload["product_id"] = "product-c5-long-acting-z"
        payload["cohort_id"] = "cohort-zeta"
        for key in ("observation_id", "row_id", "source_row_id"):
            payload[key] = str(payload[key]).replace("gamma", "zeta").replace(
                _TRIAL_GAMMA, "trial-zeta"
            )
        payload["source_version_id"] = "registry-version-zeta-1"
        boosted_rows.append(DesignObservation.model_validate(payload))

    boosted = _synthesize(module, tuple(_CORPUS) + tuple(boosted_rows))
    baseline_paths = _paths(baseline)
    boosted_paths = _paths(boosted)
    assert len(boosted_paths) >= 2

    baseline_by_signature = {_path_signature(path): path for path in baseline_paths}
    boosted_by_signature = {_path_signature(path): path for path in boosted_paths}
    assert set(baseline_by_signature) == set(boosted_by_signature), (
        "仅增加同签名试验不得改变候选路径签名集合"
    )

    larger = max(
        boosted_paths,
        key=lambda path: len(_id_set(path, "trial_ids", "supporting_trial_ids")),
    )
    smaller = min(
        boosted_paths,
        key=lambda path: len(_id_set(path, "trial_ids", "supporting_trial_ids")),
    )
    assert len(_id_set(larger, "trial_ids", "supporting_trial_ids")) > len(
        _id_set(smaller, "trial_ids", "supporting_trial_ids")
    )

    # 展示顺序可确定，但试验数更多的路径不得因数量变化独占新的首位。
    if _path_id(boosted_paths[0]) == _path_id(larger):
        assert _path_id(baseline_paths[0]) == _path_id(
            baseline_by_signature[_path_signature(larger)]
        ), "首位变化若仅因试验数增多，构成隐性排名"

    preference_tokens = (
        "优先",
        "更优",
        "首选",
        "推荐采用",
        "建议采用",
        "优于",
        "劣于",
        "排名",
        "第一路径",
        "第二路径",
    )
    for text in _collect_user_texts(boosted_paths):
        lowered = text.lower()
        for token in preference_tokens:
            assert token.lower() not in lowered, (
                f"试验数不均衡不得写入隐性偏好语义 {token!r}: {text!r}"
            )

    for path in boosted_paths:
        path_keys = _dump_keys(path)
        assert path_keys.isdisjoint({key.casefold() for key in _FORBIDDEN_RESULT_KEYS})
        assert "priority" not in path_keys
        assert "order_index" not in path_keys
        assert "weight" not in path_keys


def test_synthesis_binds_only_existing_observation_and_trial_identities() -> None:
    """共享合同回归：综合层不得发明观察/试验身份。"""

    module = _synthesis()
    result = _synthesize(module, _CORPUS)
    layers = (
        *_patterns(result),
        *_differences(result),
        *_outliers(result),
        *_paths(result),
    )
    for item in layers:
        observation_ids = _id_set(
            item,
            "observation_ids",
            "supporting_observation_ids",
            "evidence_observation_ids",
        )
        trial_ids = _id_set(
            item,
            "trial_ids",
            "supporting_trial_ids",
            "evidence_trial_ids",
            "sourced_trial_ids",
        )
        assert observation_ids, "综合条目必须绑定观察身份"
        assert trial_ids, "综合条目必须绑定试验身份"
        assert observation_ids <= _ALL_OBSERVATION_IDS, (
            f"出现未输入的观察身份：{sorted(observation_ids - _ALL_OBSERVATION_IDS)}"
        )
        assert trial_ids <= _ALL_TRIAL_IDS, (
            f"出现未输入的试验身份：{sorted(trial_ids - _ALL_TRIAL_IDS)}"
        )
        for observation_id in observation_ids:
            assert _CORPUS_BY_ID[observation_id].trial_id in trial_ids
