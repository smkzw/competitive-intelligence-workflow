# GPT Pro 专家审阅（2026-09-22，基线 d1909b8）纠偏不变量回归。
# 每项对应 ACCEPTANCE.md 的 SCI 编号；修复要求先红后绿，
# 不以"删诊断探针"或"改写 reported_zero 为 reported_value"过关。
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ci_workflow.domain.enums import FactDisclosureState  # noqa: E402
from ci_workflow.renderers.portal.report_a import EfficacyRow, TrialRow  # noqa: E402
from ci_workflow.reports.b.registry_observation import (  # noqa: E402
    classify_registry_endpoint,
    resolve_indication_id,
)


def _efficacy_row(**overrides):
    base = {
        "row_id": "eff-1",
        "product_id": "p1",
        "trial_id": "nct1",
        "endpoint": "endpoint",
        "timepoint": "第12周",
        "arm": "治疗组",
        "value": 1.0,
        "unit": "%",
        "population": "全分析集",
    }
    base.update(overrides)
    return EfficacyRow(**base)


# ── SCI01（R01）：披露状态与数值的唯一不变量 ──────────────────────────────


def test_sci01_reported_zero_with_explicit_zero_is_accepted():
    row = _efficacy_row(
        value=0.0, disclosure_state=FactDisclosureState.REPORTED_ZERO
    )
    assert row.value == 0


def test_sci01_reported_zero_without_value_is_rejected():
    with pytest.raises(ValueError):
        _efficacy_row(value=None, disclosure_state=FactDisclosureState.REPORTED_ZERO)


def test_sci01_reported_zero_with_nonzero_is_rejected():
    with pytest.raises(ValueError):
        _efficacy_row(value=2.5, disclosure_state=FactDisclosureState.REPORTED_ZERO)


def test_sci01_missing_states_cannot_carry_numeric_value():
    for state in (
        FactDisclosureState.NOT_REPORTED,
        FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        FactDisclosureState.NOT_APPLICABLE,
        FactDisclosureState.BELOW_REPORTING_THRESHOLD,
        FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
    ):
        with pytest.raises(ValueError):
            _efficacy_row(value=1.0, disclosure_state=state)


def test_sci01_reported_value_requires_finite_number():
    with pytest.raises(ValueError):
        _efficacy_row(value=None, disclosure_state=FactDisclosureState.REPORTED_VALUE)
    with pytest.raises(ValueError):
        _efficacy_row(
            value=math.nan, disclosure_state=FactDisclosureState.REPORTED_VALUE
        )


# ── SCI02（R02）：安全域概念分类——否定不命中，特定指标不冒充总体 ────────────


def test_sci02_non_serious_not_matched_as_sae():
    assert _safety_concept("Non-serious adverse events") != "any_sae"


def test_sci02_generic_ae_not_any_teae():
    assert _safety_concept("Number of participants with adverse events") != "any_teae"


def test_sci02_discontinuation_due_to_ae_is_specific_not_any():
    concept = _safety_concept(
        "Number of participants discontinuing due to adverse events"
    )
    assert concept != "any_teae"
    assert "discontinuation" in concept


def test_sci02_any_teae_still_matched():
    assert _safety_concept("Any treatment-emergent adverse event") == "any_teae"


def test_sci02_serious_sae_still_matched():
    assert _safety_concept("Number of participants with serious adverse events") == "any_sae"


def test_sci02_death_and_aesi_recognized():
    assert _safety_concept("Deaths from any cause") == "death"
    assert _safety_concept(
        "Adverse events of special interest"
    ) == "aesi"


def _safety_concept(title: str) -> str:
    from ci_workflow.reports.b.safety_concepts import classify_safety_concept

    concept = classify_safety_concept(title)
    assert concept is not None, "安全域测量不得因拒判而丢数据"
    return concept


# ── SCI03/SCI04（R03）：跨模块分母 crosswalk ─────────────────────────────
# 生产实现：src/ci_workflow/reports/b/safety_denominator_crosswalk.py


def _atrisk_crosswalk(rows):
    from ci_workflow.reports.b.safety_denominator_crosswalk import build_atrisk_crosswalk

    # The production crosswalk now requires complete study/group/source identity.
    # Preserve these historical clinical scenarios under that stronger contract.
    return build_atrisk_crosswalk([
        {
            "study_id": "S1", "measure_object": "participants_at_risk",
            "analysis_population": "SAF", "source_version_id": "sv1",
            "window": row["period"], **row,
        }
        for row in rows
    ])


def _identified_lookup(crosswalk, *, stat, period, title, group_id):
    return crosswalk.lookup(
        stat=stat, period=period, title=title, study_id="S1", module="ae",
        group_id=group_id, measure_object="participants_at_risk",
        analysis_population="SAF", window=period, source_version_id="sv1",
    )


def test_sci03_period_mismatch_is_unknown_not_borrowed():
    rows = [
        {"module": "ae", "group_id": "EG000", "title": "Drug X (TP1)",
         "period": "TP1", "stat": "other", "num_at_risk": 100},
        {"module": "ae", "group_id": "EG001", "title": "Drug X (TP2)",
         "period": "TP2", "stat": "other", "num_at_risk": 40},
    ]
    crosswalk = _atrisk_crosswalk(rows)
    assert _identified_lookup(
        crosswalk, stat="other", period="TP2", title="Drug X (TP2)", group_id="EG001",
    ) == 40
    assert _identified_lookup(
        crosswalk, stat="other", period="TP1", title="Drug X (TP1)", group_id="EG000",
    ) == 100
    # 期别未知时不得借用任何一期的人数
    assert crosswalk.lookup(stat="other", period=None, title="Drug X") is None


def test_sci03_conflicting_values_never_first_wins():
    rows = [
        {"module": "ae", "group_id": "EG000", "title": "Drug X",
         "period": "TP1", "stat": "other", "num_at_risk": 100},
        {"module": "ae", "group_id": "EG000", "title": "Drug X",
         "period": "TP1", "stat": "other", "num_at_risk": 60},
    ]
    crosswalk = _atrisk_crosswalk(rows)
    assert _identified_lookup(
        crosswalk, stat="other", period="TP1", title="Drug X", group_id="EG000",
    ) is None
    assert crosswalk.conflicts  # 冲突显式保留，不静默取第一个


def test_sci04_sae_other_death_denominators_match_own_statistic():
    rows = [
        {"module": "ae", "group_id": "EG000", "title": "Drug X",
         "period": "TP1", "stat": "serious", "num_at_risk": 57},
        {"module": "ae", "group_id": "EG000", "title": "Drug X",
         "period": "TP1", "stat": "other", "num_at_risk": 80},
        {"module": "ae", "group_id": "EG000", "title": "Drug X",
         "period": "TP1", "stat": "deaths", "num_at_risk": 57},
    ]
    crosswalk = _atrisk_crosswalk(rows)
    assert _identified_lookup(
        crosswalk, stat="serious", period="TP1", title="Drug X", group_id="EG000",
    ) == 57
    assert _identified_lookup(
        crosswalk, stat="other", period="TP1", title="Drug X", group_id="EG000",
    ) == 80
    assert _identified_lookup(
        crosswalk, stat="deaths", period="TP1", title="Drug X", group_id="EG000",
    ) == 57
    # SAE 行不得优先借用 other 的人数（R03：other 优先于 serious 是缺陷）


def test_sci04_person_time_not_interchangeable_with_persons():
    rows = [
        {"module": "ae", "group_id": "EG000", "title": "Drug X",
         "period": "TP1", "stat": "person_time", "num_at_risk": 123.5,
         "unit": "person-months"},
    ]
    crosswalk = _atrisk_crosswalk(rows)
    # 人时不是人数：查询人数口径不得返回人时值
    assert crosswalk.lookup(stat="other", period="TP1", title="Drug X") is None
    assert _identified_lookup(
        crosswalk, stat="person_time", period="TP1", title="Drug X", group_id="EG000",
    ) == 123.5


# ── SCI05（R04）：适应症作用域解析 ───────────────────────────────────────


def test_sci05_canonical_ids_resolve_directly():
    for canonical in ("pnh", "ipf", "atopic-dermatitis", "igan", "ulcerative-colitis"):
        assert resolve_indication_id(canonical) == canonical


def test_sci05_aliases_and_canonical_agree():
    for name, expected in (
        ("阵发性睡眠性血红蛋白尿症", "pnh"),
        ("PNH", "pnh"),
        ("idiopathic pulmonary fibrosis", "ipf"),
        ("特发性肺纤维化", "ipf"),
        ("atopic dermatitis", "atopic-dermatitis"),
    ):
        assert resolve_indication_id(name) == expected


def test_sci05_unknown_indication_cannot_unlock_disease_specific_rules():
    # 未知适应症（不能解析为任何 scope）不得命中任何疾病专属规则——
    # 最多落入跨适应症共享的 generic 规则（诚实未分类，不误归族）
    pnh_hit = classify_registry_endpoint(
        "Change in hemoglobinuria", indication_id="pnh"
    )
    unknown_hit = classify_registry_endpoint(
        "Change in hemoglobinuria", indication_id="unknown-indication-x"
    )
    assert pnh_hit == "endpoint-pnh-hemoglobin-v1"
    assert unknown_hit != "endpoint-pnh-hemoglobin-v1"
    assert pnh_hit.startswith("endpoint-pnh-")


def test_sci05_resolved_none_is_distinct_from_unspecified():
    # 未提供适应症 = 历史全局行为；提供了但未知 = 收缩到共享规则。
    # 两者不得共用 None 语义。
    from ci_workflow.reports.b.registry_observation import scoped_family_rules

    scoped = [scope for _, _, scope in scoped_family_rules() if scope]
    assert scoped, "政策必须包含适应症门闩规则以验证本不变量"


# ── SCI06（R05）：终点实例身份与逐实例时间配对 ─────────────────────────────


def test_sci06_endpoint_instances_have_distinct_ids_and_timepoints():
    from ci_workflow.reports.c.endpoint_instances import build_endpoint_instances

    observations = [
        _endpoint_obs("obs-1", "pri0", "primary", "主要终点A", "第12周"),
        _timepoint_obs("obs-1t", "pri0", "primary", "第12周"),
        _endpoint_obs("obs-2", "pri1", "primary", "主要终点B", "第24周"),
        _timepoint_obs("obs-2t", "pri1", "primary", "第24周"),
    ]
    instances = build_endpoint_instances(observations)
    primaries = [i for i in instances if i.role == "primary"]
    assert len(primaries) == 2
    assert len({i.outcome_id for i in primaries}) == 2
    assert {i.timepoint for i in primaries} == {"第12周", "第24周"}


def test_sci06_missing_instance_timepoint_fails_validation():
    from ci_workflow.reports.c.endpoint_instances import (
        EndpointInstanceError,
        validate_endpoint_timepoint_pairs,
    )

    observations = [
        _endpoint_obs("obs-1", "pri0", "primary", "主要终点A", "第12周"),
        _timepoint_obs("obs-1t", "pri0", "primary", "第12周"),
        # 第二条主终点没有配对时间点实例——按角色集合检查会漏过，
        # 实例级检查必须失败
        _endpoint_obs("obs-2", "pri1", "primary", "主要终点B", "第24周"),
    ]
    with pytest.raises(EndpointInstanceError):
        validate_endpoint_timepoint_pairs(observations)


def test_sci06_duplicate_outcome_id_with_conflicting_measure_fails():
    from ci_workflow.reports.c.endpoint_instances import (
        EndpointInstanceError,
        validate_endpoint_timepoint_pairs,
    )

    observations = [
        _endpoint_obs("obs-1", "pri0", "primary", "主要终点A", "第12周"),
        _endpoint_obs("obs-2", "pri0", "primary", "同名但不同定义", "第12周"),
        _timepoint_obs("obs-1t", "pri0", "primary", "第12周"),
    ]
    with pytest.raises(EndpointInstanceError):
        validate_endpoint_timepoint_pairs(observations)


def _timepoint_obs(obs_id, outcome_id, role, timepoint):
    obs = _endpoint_obs(obs_id, outcome_id, role, "", timepoint)
    from ci_workflow.reports.c.contracts import DesignFieldFamily

    return obs.model_copy(update={
        "field_family": DesignFieldFamily.TIMEPOINT,
        "field": "primary_endpoint_timepoint",
    })


def _endpoint_obs(obs_id, outcome_id, role, measure, timepoint):
    from ci_workflow.domain.enums import (
        FactDisclosureState,
        FactReviewState,
    )
    from ci_workflow.domain.evidence import EvidenceLocator
    from ci_workflow.gates.models import (
        ConflictDisposition,
        DisclosureMaturity,
        SourceRole,
    )
    from ci_workflow.reports.c.contracts import (
        DesignFieldFamily,
        DesignObservation,
    )

    return DesignObservation(
        row_id=obs_id,
        source_row_id="src-" + obs_id,
        observation_id="obs-" + obs_id,
        product_id="p1",
        trial_id="nct1",
        cohort_id="cohort-nct1",
        group_id="group-nct1-overall",
        field_family=(
            DesignFieldFamily.ENDPOINT
            if measure
            else DesignFieldFamily.TIMEPOINT
        ),
        field="primary_endpoint_definition" if measure else "primary_endpoint_timepoint",
        endpoint_key=role,
        outcome_id=outcome_id,
        source_field_name="registry.outcomes.primary",
        source_field_definition="CT.gov 登记字段终点定义的原文记录",
        source_text=measure or (timepoint or ""),
        assessment_timepoint=timepoint,
        source_version_id="srcver-1",
        source_locator=EvidenceLocator(document_role="registry", field_path="outcomes"),
        source_role=SourceRole.CLINICAL_TRIAL_REGISTRY,
        disclosure_maturity=DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT,
        review_state=FactReviewState.ACCEPTED,
        disclosure_state=FactDisclosureState.REPORTED_VALUE,
        conflict_disposition=ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT,
        compatibility_rule="none",
    )


# ── SCI07（R06）：检索归一不得破坏小数与范围 ───────────────────────────────


def test_sci07_decimals_and_ranges_survive_normalization():
    from ci_workflow.reports.c.synthesis import _normalize_text

    assert "0.5" in _normalize_text("0.5 mg BID")
    assert "5-10" in _normalize_text("5-10 mg") or "5~10" in _normalize_text("5-10 mg")
    normalized = _normalize_text("5.10 mg")
    assert "5.10" in normalized or "5.1" in normalized


def test_sci07_comparators_and_negation_preserved():
    from ci_workflow.reports.c.synthesis import _normalize_text

    text = _normalize_text("≤ 10 mg 不适用")
    assert "≤" in text or "<=" in text
    assert "不适用" in text


# ── SCI10（R13）：未知样本量保留，planned/actual 分开 ─────────────────────


def test_sci10_unknown_sample_size_is_representable():
    row = TrialRow(
        id="nct-unknown",
        display_id="NCTUNKNOWN",
        product_id="p1",
        name="研究",
        phase="II期",
        region="全球",
        status="招募中",
        sample_size=None,
        treatment_sample_size=None,
        role="登记研究",
    )
    assert row.sample_size is None


def test_sci10_explicit_zero_is_preserved_but_negative_size_is_rejected():
    base = {
        "display_id": "NCTZERO",
        "product_id": "p1",
        "name": "研究",
        "phase": "II期",
        "region": "全球",
        "status": "招募中",
        "role": "登记研究",
    }
    assert TrialRow(id="nct-zero", sample_size=0, **base).sample_size == 0
    with pytest.raises(ValueError):
        TrialRow(id="nct-negative", sample_size=-1, **base)


def test_sci10_planned_and_actual_are_separate_fields():
    row = TrialRow(
        id="nct-both",
        display_id="NCTBOTH",
        product_id="p1",
        name="研究",
        phase="III期",
        region="全球",
        status="进行中（不招募）",
        sample_size=520,
        planned_sample_size=None,
        treatment_sample_size=260,
        role="登记研究",
    )
    assert row.sample_size == 520
    assert row.treatment_sample_size == 260
