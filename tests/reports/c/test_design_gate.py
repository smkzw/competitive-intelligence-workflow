"""Task 7.1 C 类设计事实合同与登记优先门槛 RED 测试。

合同断言（先失败后通过）：
- 观察模型覆盖试验身份/阶段/角色、人群、完整入排、分组/随机/盲法、干预/对照/
  背景/救援、剂量/疗程/随访、终点定义、时间点、样本量、关键运营与统计扩展字段；
- 四类关键阻断族独立判定：人群、分组、终点、时间点；任一缺失即阻断且不生成草稿；
- 官方登记字段已覆盖关键设计时，Protocol/SAP 缺失不阻断，并保留“仅有注册登记信息”；
- 分析人群、比较逻辑、模型/检验、效应量、多重性等统计细节缺失保持非阻断与真实披露状态；
- 门槛失败返回稳定失败码、试验/组别/字段定位，以及自然中文补件说明（不含内部状态名）；
- 完整保留 EvidenceLocator 语义；禁止用 publication 替代登记平台设计事实。
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType
from typing import Any

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

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "schemas" / "reports" / "c-design-observation.schema.json"

_CJK = re.compile(r"[\u3400-\u9fff]")
_INTERNAL_LEAKS = (
    "DesignGateDecision",
    "BLOCKED",
    "PASSED",
    "EXTENSION_MISSING",
    "GateUnitOutcome",
    "missing_required_evidence",
    "clinical_trial_registry",
    "protocol_sap",
    "primary_trial_report",
    "not_publicly_disclosed",
    "reported_value",
    "c_missing_",
    "field_family",
    "source_role",
)

_REGISTRY_LOCATOR = EvidenceLocator(
    document_role="clinical-trial-registry",
    field_path="Arms and Interventions / Outcome Measures",
    heading="Study Design",
    url="https://clinicaltrials.gov/study/NCT00000001",
)

_PROTOCOL_LOCATOR = EvidenceLocator(
    document_role="protocol-sap",
    field_path="Section 8.1 Endpoints",
    page=42,
    paragraph="Primary endpoint definition",
)


def _contracts() -> ModuleType:
    """延迟导入计划中的 C 类合同；实现前每个用例精确失败而非收集期中断。"""
    try:
        from ci_workflow.reports.c import contracts as module
    except ModuleNotFoundError as exc:
        pytest.fail(f"C 类设计合同尚未实现：{exc}", pytrace=False)
    return module


def _observation(contracts: ModuleType, **overrides: object) -> Any:
    """构造一条已接受的登记来源设计观察；测试用最小完整夹具。"""
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "row_id": "design-row-population",
        "source_row_id": "registry-row-population",
        "observation_id": "design-observation-population",
        "product_id": "product-a",
        "trial_id": "trial-1",
        "cohort_id": "cohort-1",
        "group_id": "group-1",
        "field_family": contracts.DesignFieldFamily.POPULATION,
        "field": "target_population",
        "source_field_name": "Eligibility Criteria / Population",
        "source_field_definition": "Adults with confirmed PNH and LDH ≥1.5×ULN",
        "source_text": "确诊 PNH，LDH≥1.5×ULN 的成人受试者",
        "scale": None,
        "scale_version": None,
        "operator": None,
        "threshold_value": None,
        "threshold_unit": None,
        "assessment_timepoint": "筛选期",
        "stage": "III",
        "development_role": "关键注册试验",
        "randomization": None,
        "blinding": None,
        "source_version_id": "registry-version-1",
        "source_locator": _REGISTRY_LOCATOR,
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
    return contracts.DesignObservation.model_validate(payload)


def _core_design_observations(
    contracts: ModuleType,
    *,
    trial_id: str = "trial-1",
    group_id: str = "group-1",
    source_role: SourceRole = SourceRole.CLINICAL_TRIAL_REGISTRY,
    locator: EvidenceLocator = _REGISTRY_LOCATOR,
    include_protocol: bool = False,
    include_statistical: bool = False,
    omit_families: Iterable[Any] = (),
) -> tuple[Any, ...]:
    """返回一项核心试验的关键设计观察集合；可按族省略以制造精确反例。"""
    omitted = frozenset(omit_families)
    family = contracts.DesignFieldFamily
    base = {
        "trial_id": trial_id,
        "cohort_id": f"cohort-{trial_id}",
        "group_id": group_id,
        "source_role": source_role,
        "source_locator": locator,
        "source_version_id": (
            "protocol-version-1"
            if source_role is SourceRole.PROTOCOL_SAP
            else "registry-version-1"
        ),
    }
    rows: list[Any] = []

    catalog: tuple[tuple[Any, str, str, dict[str, object]], ...] = (
        (
            family.TRIAL_IDENTITY,
            "trial_identity_stage_role",
            "试验身份、阶段与开发角色",
            {"stage": "III", "development_role": "关键注册试验"},
        ),
        (
            family.POPULATION,
            "target_population",
            "目标人群与关键入排",
            {"assessment_timepoint": "筛选期"},
        ),
        (
            family.GROUPING,
            "arm_randomization_blinding",
            "分组、随机化与盲法",
            {"randomization": "1:1 随机", "blinding": "双盲"},
        ),
        (
            family.INTERVENTION,
            "intervention_control_rescue",
            "干预、对照、背景与救援",
            {},
        ),
        (
            family.DOSE_SCHEDULE,
            "dose_schedule_followup",
            "剂量、疗程与随访",
            {},
        ),
        (
            family.ENDPOINT,
            "primary_endpoint_definition",
            "主要终点定义",
            {},
        ),
        (
            family.TIMEPOINT,
            "primary_endpoint_timepoint",
            "主要终点评估时间点",
            {"assessment_timepoint": "第26周"},
        ),
        (
            family.SAMPLE_SIZE,
            "planned_or_actual_sample_size",
            "计划或实际样本量",
            {},
        ),
    )

    for field_family, field, label, extras in catalog:
        if field_family in omitted:
            continue
        rows.append(
            _observation(
                contracts,
                row_id=f"design-row-{field}",
                source_row_id=f"source-row-{field}",
                observation_id=f"design-observation-{field}",
                field_family=field_family,
                field=field,
                source_field_name=label,
                source_field_definition=f"{label}原文定义",
                source_text=f"{label}登记原文",
                **base,
                **extras,
            )
        )

    if include_protocol and family.ENDPOINT not in omitted:
        rows.append(
            _observation(
                contracts,
                row_id="design-row-protocol-endpoint",
                source_row_id="protocol-row-endpoint",
                observation_id="design-observation-protocol-endpoint",
                field_family=family.ENDPOINT,
                field="primary_endpoint_definition",
                source_field_name="方案主要终点",
                source_field_definition="Protocol primary endpoint",
                source_text="方案主要终点原文",
                source_role=SourceRole.PROTOCOL_SAP,
                source_locator=_PROTOCOL_LOCATOR,
                source_version_id="protocol-version-1",
                trial_id=trial_id,
                cohort_id=f"cohort-{trial_id}",
                group_id=group_id,
            )
        )

    if include_statistical:
        statistical_fields = (
            ("analysis_population", "分析人群"),
            ("comparison_logic", "主要比较逻辑"),
            ("statistical_model", "统计模型与检验"),
            ("effect_size", "效应量"),
            ("multiplicity", "多重性控制"),
        )
        for field, label in statistical_fields:
            rows.append(
                _observation(
                    contracts,
                    row_id=f"design-row-{field}",
                    source_row_id=f"source-row-{field}",
                    observation_id=f"design-observation-{field}",
                    field_family=family.STATISTICAL,
                    field=field,
                    source_field_name=label,
                    source_field_definition=f"{label}定义",
                    source_text=f"{label}原文",
                    disclosure_state=FactDisclosureState.REPORTED_VALUE,
                    **base,
                )
            )

    return tuple(rows)


def _assert_chinese_assistance(text: str, *, forbidden_tokens: Iterable[str] = ()) -> None:
    assert text.strip(), "用户补件说明不能为空"
    assert _CJK.search(text), f"用户补件说明必须含中文：{text!r}"
    for token in (*_INTERNAL_LEAKS, *forbidden_tokens):
        assert token not in text, f"用户说明不得泄露内部标识 {token!r}: {text!r}"


def _failure_map(result: Any) -> dict[str, Any]:
    return {failure.failure_code: failure for failure in result.failures}


# ── 枚举与观察合同 ──────────────────────────────────────────────────────────


def test_design_field_families_cover_critical_and_statistical_layers() -> None:
    contracts = _contracts()
    assert {member.value for member in contracts.DesignFieldFamily} >= {
        "trial_identity",
        "population",
        "grouping",
        "intervention",
        "dose_schedule",
        "endpoint",
        "timepoint",
        "sample_size",
        "operational",
        "statistical",
    }


def test_design_observation_preserves_full_source_locator_semantics() -> None:
    contracts = _contracts()
    observation = _observation(
        contracts,
        source_locator=EvidenceLocator(
            document_role="clinical-trial-registry",
            field_path="Outcome Measures[0].timeFrame",
            heading="Primary Outcome",
            table="Outcome Measures",
            row="Primary: LDH normalization",
            column="Time Frame",
            url="https://clinicaltrials.gov/study/NCT00000001#outcomes",
        ),
    )

    validated = contracts.validate_design_observation(observation)
    locator = validated.source_locator
    assert locator.document_role == "clinical-trial-registry"
    assert locator.field_path == "Outcome Measures[0].timeFrame"
    assert locator.heading == "Primary Outcome"
    assert locator.table == "Outcome Measures"
    assert locator.row == "Primary: LDH normalization"
    assert locator.column == "Time Frame"
    assert locator.url.endswith("#outcomes")
    assert validated.source_role is SourceRole.CLINICAL_TRIAL_REGISTRY


def test_design_observation_schema_rejects_unknown_fields_and_blank_identity() -> None:
    contracts = _contracts()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    good = _observation(contracts).model_dump(mode="json")
    assert validator.is_valid(good)

    bad = dict(good)
    bad["unexpected_internal_flag"] = True
    assert not validator.is_valid(bad)

    with pytest.raises(ValidationError, match="试验|产品|不能为空|blank|空"):
        _observation(contracts, trial_id="   ")


def test_design_observation_schema_and_runtime_both_reject_orphan_scale_version() -> None:
    contracts = _contracts()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    payload = _observation(contracts).model_dump(mode="json")
    payload["scale"] = None
    payload["scale_version"] = "v9-orphan"

    assert not validator.is_valid(payload)
    with pytest.raises(ValidationError, match="量表版本不能脱离量表名称单独存在"):
        contracts.DesignObservation.model_validate(payload)


# ── 四类关键阻断族独立测试 ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("omitted_family_name", "failure_code", "field_token", "label_token"),
    [
        ("POPULATION", "c_missing_population", "target_population", "人群"),
        ("GROUPING", "c_missing_grouping", "arm_randomization_blinding", "分组"),
        ("ENDPOINT", "c_missing_endpoint", "primary_endpoint_definition", "终点"),
        ("TIMEPOINT", "c_missing_timepoint", "primary_endpoint_timepoint", "时间点"),
    ],
    ids=["population", "grouping", "endpoint", "timepoint"],
)
def test_each_critical_design_family_blocks_independently(
    omitted_family_name: str,
    failure_code: str,
    field_token: str,
    label_token: str,
) -> None:
    contracts = _contracts()
    omitted_family = getattr(contracts.DesignFieldFamily, omitted_family_name)
    observations = _core_design_observations(
        contracts,
        omit_families=(omitted_family,),
    )
    result = contracts.evaluate_design_gate(
        observations,
        core_trial_ids=("trial-1",),
    )

    assert isinstance(result, contracts.DesignGateResult)
    assert result.decision is contracts.DesignGateDecision.BLOCKED
    assert result.allows_draft is False

    failures = _failure_map(result)
    assert failure_code in failures
    failure = failures[failure_code]
    assert failure.trial_id == "trial-1"
    assert failure.group_id == "group-1"
    assert failure.field_id == field_token
    assert failure.field_family is omitted_family
    _assert_chinese_assistance(
        failure.user_note_zh,
        forbidden_tokens=(failure_code, omitted_family.value),
    )
    assert label_token in failure.user_note_zh
    assert "trial-1" in failure.user_note_zh or "该项试验" in failure.user_note_zh

    sibling_codes = {
        "c_missing_population",
        "c_missing_grouping",
        "c_missing_endpoint",
        "c_missing_timepoint",
    } - {failure_code}
    assert sibling_codes.isdisjoint(failures)


# ── 登记优先：Protocol/SAP 缺失不阻断 ───────────────────────────────────────


def test_registry_sufficient_design_passes_without_protocol_or_sap() -> None:
    contracts = _contracts()
    observations = _core_design_observations(
        contracts,
        source_role=SourceRole.CLINICAL_TRIAL_REGISTRY,
        locator=_REGISTRY_LOCATOR,
        include_protocol=False,
        include_statistical=False,
    )
    assert all(
        item.source_role is SourceRole.CLINICAL_TRIAL_REGISTRY for item in observations
    )
    assert all(item.source_role is not SourceRole.PROTOCOL_SAP for item in observations)

    result = contracts.evaluate_design_gate(observations, core_trial_ids=("trial-1",))

    assert result.decision is contracts.DesignGateDecision.PASSED
    assert result.allows_draft is False
    assert result.failures == ()
    assert result.evidence_scope is contracts.DesignEvidenceScope.REGISTRY_ONLY
    assert result.evidence_scope_note_zh == "仅有注册登记信息"
    _assert_chinese_assistance(result.evidence_scope_note_zh)


# ── 统计细节缺失：非阻断且保留披露状态 ─────────────────────────────────────


def test_missing_statistical_details_are_nonblocking_with_preserved_disclosure() -> None:
    contracts = _contracts()
    observations = _core_design_observations(contracts, include_statistical=False)
    result = contracts.evaluate_design_gate(observations, core_trial_ids=("trial-1",))

    assert result.decision is contracts.DesignGateDecision.PASSED
    assert result.failures == ()
    assert result.nonblocking_gaps
    statistical_gaps = [
        gap
        for gap in result.nonblocking_gaps
        if gap.field_family is contracts.DesignFieldFamily.STATISTICAL
    ]
    assert statistical_gaps
    for gap in statistical_gaps:
        assert gap.blocking is False
        assert gap.trial_id == "trial-1"
        assert gap.disclosure_state in {
            FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
            FactDisclosureState.NOT_REPORTED,
        }
        _assert_chinese_assistance(gap.user_note_zh)
        assert "不影响" in gap.user_note_zh or "不阻断" in gap.user_note_zh


def test_reported_statistical_details_remain_extractable_without_raising_gate() -> None:
    contracts = _contracts()
    observations = _core_design_observations(contracts, include_statistical=True)
    result = contracts.evaluate_design_gate(observations, core_trial_ids=("trial-1",))

    assert result.decision is contracts.DesignGateDecision.PASSED
    reported = [
        item
        for item in observations
        if item.field_family is contracts.DesignFieldFamily.STATISTICAL
    ]
    assert reported
    assert all(
        item.disclosure_state is FactDisclosureState.REPORTED_VALUE for item in reported
    )
    assert result.nonblocking_gaps == () or all(
        gap.disclosure_state is not FactDisclosureState.REPORTED_VALUE
        for gap in result.nonblocking_gaps
    )


# ── 失败码定位与中文补件 ────────────────────────────────────────────────────


def test_blocking_failure_exposes_stable_codes_and_trial_group_field_location() -> None:
    contracts = _contracts()
    observations = _core_design_observations(
        contracts,
        omit_families=(
            contracts.DesignFieldFamily.POPULATION,
            contracts.DesignFieldFamily.TIMEPOINT,
        ),
    )
    result = contracts.evaluate_design_gate(observations, core_trial_ids=("trial-1",))

    assert result.decision is contracts.DesignGateDecision.BLOCKED
    codes = {failure.failure_code for failure in result.failures}
    assert codes == {"c_missing_population", "c_missing_timepoint"}
    for failure in result.failures:
        assert failure.trial_id == "trial-1"
        assert failure.group_id == "group-1"
        assert failure.field_id
        assert isinstance(failure, contracts.DesignGateFailure)
        _assert_chinese_assistance(
            failure.user_note_zh,
            forbidden_tokens=(failure.failure_code, failure.field_id),
        )
        assert any(token in failure.user_note_zh for token in ("缺少", "缺失", "未提供"))
        assert any(token in failure.user_note_zh for token in ("请提供", "请补充", "请上传"))


# ── 禁止 publication 替代登记设计事实 ───────────────────────────────────────


def test_publication_only_design_facts_cannot_satisfy_registry_first_gate() -> None:
    contracts = _contracts()
    publication_locator = EvidenceLocator(
        document_role="primary-trial-report",
        field_path="Methods / Study design",
        page=5,
        paragraph="Patients were randomized 1:1",
    )
    observations = _core_design_observations(
        contracts,
        source_role=SourceRole.PRIMARY_TRIAL_REPORT,
        locator=publication_locator,
    )
    result = contracts.evaluate_design_gate(observations, core_trial_ids=("trial-1",))

    assert result.decision is contracts.DesignGateDecision.BLOCKED
    assert result.allows_draft is False
    codes = {failure.failure_code for failure in result.failures}
    assert "c_publication_cannot_replace_registry_design" in codes
    failure = _failure_map(result)["c_publication_cannot_replace_registry_design"]
    assert failure.trial_id == "trial-1"
    _assert_chinese_assistance(
        failure.user_note_zh,
        forbidden_tokens=("primary_trial_report", "publication"),
    )
    assert any(token in failure.user_note_zh for token in ("登记", "注册"))
    assert any(token in failure.user_note_zh for token in ("论文", "文献", "发表"))


def test_mixed_registry_and_publication_keeps_registry_as_design_authority() -> None:
    contracts = _contracts()
    registry_rows = list(_core_design_observations(contracts))
    publication_only_population = _observation(
        contracts,
        row_id="design-row-publication-population",
        source_row_id="publication-row-population",
        observation_id="design-observation-publication-population",
        field_family=contracts.DesignFieldFamily.POPULATION,
        field="target_population",
        source_role=SourceRole.PRIMARY_TRIAL_REPORT,
        source_locator=EvidenceLocator(
            document_role="primary-trial-report",
            page=4,
            paragraph="Inclusion criteria summary",
        ),
        source_version_id="publication-version-1",
        source_text="论文人群摘要，不得替代登记入排原文",
    )
    result = contracts.evaluate_design_gate(
        (*registry_rows, publication_only_population),
        core_trial_ids=("trial-1",),
    )

    assert result.decision is contracts.DesignGateDecision.PASSED
    assert result.evidence_scope in {
        contracts.DesignEvidenceScope.REGISTRY_ONLY,
        contracts.DesignEvidenceScope.REGISTRY_WITH_PUBLICATION_CROSSCHECK,
    }
    assert "c_publication_cannot_replace_registry_design" not in _failure_map(result)


# ── 审计回归：披露状态保真、局部 publication 误导、跨试验隔离 ───────────────


def test_statistical_not_reported_gap_preserves_true_disclosure_state() -> None:
    """已接受但原文未报告的统计细节须保留 NOT_REPORTED，不得改写成未公开。"""
    contracts = _contracts()
    observations = list(_core_design_observations(contracts, include_statistical=False))
    observations.append(
        _observation(
            contracts,
            row_id="design-row-stat-not-reported",
            source_row_id="source-row-stat-not-reported",
            observation_id="design-observation-stat-not-reported",
            field_family=contracts.DesignFieldFamily.STATISTICAL,
            field="analysis_population",
            source_field_name="分析人群",
            source_field_definition="分析人群定义",
            source_text="原文未报告分析人群",
            disclosure_state=FactDisclosureState.NOT_REPORTED,
        )
    )
    result = contracts.evaluate_design_gate(observations, core_trial_ids=("trial-1",))

    assert result.decision is contracts.DesignGateDecision.PASSED
    assert result.allows_draft is False
    gaps = {
        gap.field_id: gap
        for gap in result.nonblocking_gaps
        if gap.field_family is contracts.DesignFieldFamily.STATISTICAL
    }
    assert "analysis_population" in gaps
    gap = gaps["analysis_population"]
    assert gap.blocking is False
    assert gap.disclosure_state is FactDisclosureState.NOT_REPORTED
    _assert_chinese_assistance(
        gap.user_note_zh,
        forbidden_tokens=("not_reported", "not_publicly_disclosed"),
    )
    assert "未报告" in gap.user_note_zh


def test_statistical_not_applicable_is_not_mislabeled_as_undisclosed() -> None:
    """不适用的统计细节应准确标注不适用，不得伪造成尚未公开。"""
    contracts = _contracts()
    observations = list(_core_design_observations(contracts, include_statistical=False))
    observations.append(
        _observation(
            contracts,
            row_id="design-row-stat-na",
            source_row_id="source-row-stat-na",
            observation_id="design-observation-stat-na",
            field_family=contracts.DesignFieldFamily.STATISTICAL,
            field="multiplicity",
            source_field_name="多重性控制",
            source_field_definition="多重性控制定义",
            source_text="单终点设计不适用多重性控制",
            disclosure_state=FactDisclosureState.NOT_APPLICABLE,
            applicability_predicate_id="pred-single-endpoint-no-multiplicity",
        )
    )
    result = contracts.evaluate_design_gate(observations, core_trial_ids=("trial-1",))

    assert result.decision is contracts.DesignGateDecision.PASSED
    multiplicity_gaps = [
        gap
        for gap in result.nonblocking_gaps
        if gap.field_id == "multiplicity"
    ]
    assert len(multiplicity_gaps) == 1
    gap = multiplicity_gaps[0]
    assert gap.blocking is False
    assert gap.disclosure_state is FactDisclosureState.NOT_APPLICABLE
    _assert_chinese_assistance(gap.user_note_zh)
    assert "不适用" in gap.user_note_zh
    assert "尚未公开" not in gap.user_note_zh


def test_statistical_reported_zero_counts_as_disclosed_without_undisclosed_gap() -> None:
    """已报告为零的统计细节属于已公开提取，不得再标注为未公开缺口。"""
    contracts = _contracts()
    observations = list(_core_design_observations(contracts, include_statistical=False))
    observations.append(
        _observation(
            contracts,
            row_id="design-row-stat-zero",
            source_row_id="source-row-stat-zero",
            observation_id="design-observation-stat-zero",
            field_family=contracts.DesignFieldFamily.STATISTICAL,
            field="effect_size",
            source_field_name="效应量",
            source_field_definition="效应量定义",
            source_text="效应量为 0",
            disclosure_state=FactDisclosureState.REPORTED_ZERO,
            reported_zero_text="效应量为 0",
        )
    )
    result = contracts.evaluate_design_gate(observations, core_trial_ids=("trial-1",))

    assert result.decision is contracts.DesignGateDecision.PASSED
    assert all(gap.field_id != "effect_size" for gap in result.nonblocking_gaps)


def test_partial_publication_substitution_keeps_field_localization_and_accurate_zh() -> None:
    """局部论文替代不得吞掉字段定位，也不得误称试验“仅有论文”。"""
    contracts = _contracts()
    registry_rows = list(
        _core_design_observations(
            contracts,
            omit_families=(contracts.DesignFieldFamily.TIMEPOINT,),
        )
    )
    publication_timepoint = _observation(
        contracts,
        row_id="design-row-publication-timepoint",
        source_row_id="publication-row-timepoint",
        observation_id="design-observation-publication-timepoint",
        field_family=contracts.DesignFieldFamily.TIMEPOINT,
        field="primary_endpoint_timepoint",
        source_role=SourceRole.PRIMARY_TRIAL_REPORT,
        source_locator=EvidenceLocator(
            document_role="primary-trial-report",
            page=6,
            paragraph="Assessed at week 26",
        ),
        source_version_id="publication-version-1",
        source_text="论文时间点摘要，不得替代登记时间点",
        assessment_timepoint="第26周",
    )
    result = contracts.evaluate_design_gate(
        (*registry_rows, publication_timepoint),
        core_trial_ids=("trial-1",),
    )

    assert result.decision is contracts.DesignGateDecision.BLOCKED
    assert result.allows_draft is False
    failures = _failure_map(result)
    assert "c_publication_cannot_replace_registry_design" in failures
    assert "c_missing_timepoint" in failures
    timepoint_failure = failures["c_missing_timepoint"]
    assert timepoint_failure.field_id == "primary_endpoint_timepoint"
    assert timepoint_failure.group_id == "group-1"
    _assert_chinese_assistance(
        timepoint_failure.user_note_zh,
        forbidden_tokens=("c_missing_timepoint", "primary_trial_report"),
    )
    assert "时间点" in timepoint_failure.user_note_zh
    publication_note = failures["c_publication_cannot_replace_registry_design"].user_note_zh
    _assert_chinese_assistance(publication_note)
    assert "仅有论文" not in publication_note
    assert "仅有文献" not in publication_note


def test_complete_core_trial_cannot_mask_incomplete_sibling_core_trial() -> None:
    """完整核心试验不得掩盖另一项缺失关键设计的核心试验。"""
    contracts = _contracts()
    trial_1 = _core_design_observations(contracts, trial_id="trial-1")
    trial_2 = _core_design_observations(
        contracts,
        trial_id="trial-2",
        group_id="group-2",
        omit_families=(contracts.DesignFieldFamily.ENDPOINT,),
    )
    result = contracts.evaluate_design_gate(
        (*trial_1, *trial_2),
        core_trial_ids=("trial-1", "trial-2"),
    )

    assert result.decision is contracts.DesignGateDecision.BLOCKED
    assert result.allows_draft is False
    failures = _failure_map(result)
    assert "c_missing_endpoint" in failures
    failure = failures["c_missing_endpoint"]
    assert failure.trial_id == "trial-2"
    assert failure.group_id == "group-2"
    assert all(item.trial_id != "trial-1" for item in result.failures)
    _assert_chinese_assistance(
        failure.user_note_zh,
        forbidden_tokens=("c_missing_endpoint",),
    )


def test_supporting_study_cannot_satisfy_missing_core_design_families() -> None:
    """支持性试验的完整设计事实不得填补核心试验缺失的关键族。"""
    contracts = _contracts()
    supporting = _core_design_observations(contracts, trial_id="support-1")
    core = _core_design_observations(
        contracts,
        trial_id="trial-1",
        omit_families=(contracts.DesignFieldFamily.POPULATION,),
    )
    result = contracts.evaluate_design_gate(
        (*supporting, *core),
        core_trial_ids=("trial-1",),
    )

    assert result.decision is contracts.DesignGateDecision.BLOCKED
    failure = _failure_map(result)["c_missing_population"]
    assert failure.trial_id == "trial-1"
    assert failure.field_id == "target_population"
    _assert_chinese_assistance(failure.user_note_zh)
    assert "人群" in failure.user_note_zh


def test_candidate_or_undisclosed_critical_facts_cannot_pass_design_gate() -> None:
    """候选态/未公开关键事实不得被当成已覆盖而假通过。"""
    contracts = _contracts()
    base = [
        item
        for item in _core_design_observations(contracts)
        if item.field_family is not contracts.DesignFieldFamily.GROUPING
    ]
    candidate_grouping = _observation(
        contracts,
        row_id="design-row-grouping-candidate",
        source_row_id="source-row-grouping-candidate",
        observation_id="design-observation-grouping-candidate",
        field_family=contracts.DesignFieldFamily.GROUPING,
        field="arm_randomization_blinding",
        review_state=FactReviewState.CANDIDATE,
        randomization="1:1 随机",
        blinding="双盲",
    )
    undisclosed_grouping = _observation(
        contracts,
        row_id="design-row-grouping-undisclosed",
        source_row_id="source-row-grouping-undisclosed",
        observation_id="design-observation-grouping-undisclosed",
        field_family=contracts.DesignFieldFamily.GROUPING,
        field="arm_randomization_blinding",
        disclosure_state=FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        randomization="1:1 随机",
        blinding="双盲",
    )

    candidate_result = contracts.evaluate_design_gate(
        (*base, candidate_grouping),
        core_trial_ids=("trial-1",),
    )
    undisclosed_result = contracts.evaluate_design_gate(
        (*base, undisclosed_grouping),
        core_trial_ids=("trial-1",),
    )

    assert candidate_result.decision is contracts.DesignGateDecision.BLOCKED
    assert undisclosed_result.decision is contracts.DesignGateDecision.BLOCKED
    assert "c_missing_grouping" in _failure_map(candidate_result)
    assert "c_missing_grouping" in _failure_map(undisclosed_result)



def test_protocol_sap_alone_cannot_satisfy_critical_registry_design_families() -> None:
    """四类关键设计必须以官方登记覆盖；仅有 Protocol/SAP 不得通过。"""
    contracts = _contracts()
    observations = _core_design_observations(
        contracts,
        source_role=SourceRole.PROTOCOL_SAP,
        locator=_PROTOCOL_LOCATOR,
        include_protocol=False,
        include_statistical=False,
    )
    assert observations
    assert all(item.source_role is SourceRole.PROTOCOL_SAP for item in observations)

    result = contracts.evaluate_design_gate(observations, core_trial_ids=("trial-1",))

    assert result.decision is contracts.DesignGateDecision.BLOCKED
    assert result.allows_draft is False
    assert result.protocol_sap_available is True
    failures = _failure_map(result)
    for code in (
        "c_missing_population",
        "c_missing_grouping",
        "c_missing_endpoint",
        "c_missing_timepoint",
    ):
        assert code in failures
        failure = failures[code]
        assert failure.trial_id == "trial-1"
        assert failure.group_id == "group-1"
        _assert_chinese_assistance(
            failure.user_note_zh,
            forbidden_tokens=(code, "protocol_sap", "PROTOCOL_SAP"),
        )
        assert "登记" in failure.user_note_zh or "注册" in failure.user_note_zh
    assert result.evidence_scope_note_zh != "仅有注册登记信息"
    _assert_chinese_assistance(result.evidence_scope_note_zh or "")


def test_evidence_scope_note_does_not_claim_registry_when_none_exists() -> None:
    """无登记设计事实时不得宣称“仅有注册登记信息”。"""
    contracts = _contracts()
    publication_only = _core_design_observations(
        contracts,
        source_role=SourceRole.PRIMARY_TRIAL_REPORT,
        locator=EvidenceLocator(
            document_role="primary-trial-report",
            page=3,
            paragraph="Study design summary",
        ),
    )
    result = contracts.evaluate_design_gate(
        publication_only,
        core_trial_ids=("trial-1",),
    )

    assert result.decision is contracts.DesignGateDecision.BLOCKED
    assert result.evidence_scope is not contracts.DesignEvidenceScope.REGISTRY_ONLY
    assert result.evidence_scope_note_zh != "仅有注册登记信息"
    assert "注册登记" not in (result.evidence_scope_note_zh or "")
    _assert_chinese_assistance(result.evidence_scope_note_zh or "")
    assert "登记" in (result.evidence_scope_note_zh or "") or "注册" in (
        result.evidence_scope_note_zh or ""
    )


def test_duplicate_core_trial_ids_are_rejected() -> None:
    """重复核心试验标识必须失败关闭，避免缺口与失败码被调用方复制。"""
    contracts = _contracts()
    observations = _core_design_observations(contracts)
    with pytest.raises(ValueError, match="重复|不能重复"):
        contracts.evaluate_design_gate(
            observations,
            core_trial_ids=("trial-1", "trial-1"),
        )
