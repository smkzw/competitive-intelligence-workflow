from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from ci_workflow.capabilities.lineage_registry import ScientificLineageRegistry
from ci_workflow.domain.claims import (
    ClaimFactLink,
    ClaimKind,
    ClaimVersion,
    DeterministicCalculationRecord,
)
from ci_workflow.domain.enums import FactReviewState
from ci_workflow.domain.facts import (
    AtomicFactVersion,
    FactConflictMember,
    FactConflictSet,
)
from ci_workflow.domain.ids import stable_id


def _display_value(value: Any) -> str:
    if isinstance(value, str):
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("冲突事实值不能为空")
        return normalized
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _scope(fact: AtomicFactVersion) -> tuple[str | None, ...]:
    return (
        fact.entity_id,
        fact.field_id,
        fact.context,
        fact.arm_id,
        fact.cohort_id,
        fact.population,
        fact.timepoint,
        fact.time_window,
        fact.normalized_unit or fact.unit,
    )


def build_fact_conflict_set(
    facts: tuple[AtomicFactVersion, ...], *, created_at: datetime
) -> FactConflictSet:
    if len(facts) < 2:
        raise ValueError("冲突集合至少需要两个事实版本")
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("冲突集合创建时间必须包含明确时区")
    expected_scope = _scope(facts[0])
    if any(_scope(fact) != expected_scope for fact in facts[1:]):
        raise ValueError("只有同一字段和比较范围内的事实才能形成冲突集合")
    by_version = {fact.fact_version_id: fact for fact in facts}
    if len(by_version) != len(facts):
        raise ValueError("冲突集合事实版本不得重复")
    sorted_facts = tuple(by_version[key] for key in sorted(by_version))
    members = tuple(
        FactConflictMember(
            fact_version_id=fact.fact_version_id,
            observed_value=_display_value(
                fact.normalized_value
                if fact.normalized_value is not None
                else fact.raw_value
            ),
            source_fragment_ids=fact.source_fragment_ids,
            source_role=fact.source_role,
        )
        for fact in sorted_facts
    )
    observed_values = tuple(sorted({member.observed_value for member in members}))
    if len(observed_values) < 2:
        raise ValueError("相同事实值不形成冲突集合")
    member_ids = tuple(member.fact_version_id for member in members)
    scope_parts = tuple(part or "not-applicable" for part in expected_scope)
    return FactConflictSet(
        conflict_set_id=stable_id(
            "fact-conflict-set", *scope_parts, *member_ids, *observed_values
        ),
        entity_id=facts[0].entity_id,
        field_id=facts[0].field_id,
        context=facts[0].context,
        arm_id=facts[0].arm_id,
        cohort_id=facts[0].cohort_id,
        population=facts[0].population,
        timepoint=facts[0].timepoint,
        time_window=facts[0].time_window,
        members=members,
        member_fact_version_ids=member_ids,
        observed_values=observed_values,
        resolution_state="open",
        selected_fact_version_id=None,
        resolution_note=None,
        created_at=created_at,
    )


def _accepted_fact_links(
    facts: tuple[AtomicFactVersion, ...],
) -> tuple[tuple[AtomicFactVersion, ...], tuple[ClaimFactLink, ...]]:
    if not facts:
        raise ValueError("声明至少需要一个支持事实")
    by_version = {fact.fact_version_id: fact for fact in facts}
    if len(by_version) != len(facts):
        raise ValueError("声明支持事实不得重复")
    ordered = tuple(by_version[key] for key in sorted(by_version))
    if any(fact.review_state is not FactReviewState.ACCEPTED for fact in ordered):
        raise ValueError("只有已接受事实可进入声明")
    links = tuple(
        ClaimFactLink(
            fact_version_id=fact.fact_version_id,
            support_role="supports",
            fact_review_state="accepted",
        )
        for fact in ordered
    )
    return ordered, links


def _claim_version(
    *,
    claim_identity: str,
    claim_text: str,
    claim_kind: ClaimKind,
    facts: tuple[AtomicFactVersion, ...],
    lineage_registry: ScientificLineageRegistry,
    created_at: datetime,
    calculation: DeterministicCalculationRecord | None = None,
    synthesis_method_zh: str | None = None,
) -> ClaimVersion:
    lineage_registry.assert_registered_facts(facts)
    ordered_facts, links = _accepted_fact_links(facts)
    claim_id = stable_id("claim", claim_identity)
    extra_payload = json.dumps(
        {
            "calculation": (
                None if calculation is None else calculation.model_dump(mode="json")
            ),
            "synthesis_method_zh": synthesis_method_zh,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    supporting_ids = tuple(fact.fact_version_id for fact in ordered_facts)
    return ClaimVersion.model_validate(
        {
            "claim_id": claim_id,
            "claim_version_id": stable_id(
                "claim-version",
                claim_id,
                claim_kind,
                claim_text,
                *supporting_ids,
                extra_payload,
            ),
            "claim_text": claim_text,
            "claim_kind": claim_kind,
            "fact_links": links,
            "supporting_fact_version_ids": supporting_ids,
            "calculation": calculation,
            "synthesis_method_zh": synthesis_method_zh,
            "ai_disclosure_label_zh": (
                "AI 综合判断" if claim_kind == "synthesis" else None
            ),
            "review_state": FactReviewState.CANDIDATE,
            "created_at": created_at,
        },
        context={"lineage_registry": lineage_registry},
    )


def create_direct_evidence_claim(
    *,
    claim_identity: str,
    claim_text: str,
    supporting_facts: tuple[AtomicFactVersion, ...],
    lineage_registry: ScientificLineageRegistry,
    created_at: datetime,
) -> ClaimVersion:
    return _claim_version(
        claim_identity=claim_identity,
        claim_text=claim_text,
        claim_kind="direct_evidence",
        facts=supporting_facts,
        lineage_registry=lineage_registry,
        created_at=created_at,
    )


def _numeric_fact_value(fact: AtomicFactVersion) -> float:
    value = fact.normalized_value if fact.normalized_value is not None else fact.raw_value
    if isinstance(value, bool) or value is None:
        raise ValueError("确定性差值计算需要数值事实")
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ValueError("确定性差值计算需要数值事实") from error


def create_deterministic_difference_claim(
    *,
    claim_identity: str,
    claim_text: str,
    treatment_fact: AtomicFactVersion,
    control_fact: AtomicFactVersion,
    lineage_registry: ScientificLineageRegistry,
    created_at: datetime,
) -> ClaimVersion:
    if treatment_fact.entity_id != control_fact.entity_id:
        raise ValueError("组间差值只能使用同一试验实体的事实")
    if (
        treatment_fact.arm_id is None
        or control_fact.arm_id is None
        or treatment_fact.arm_id == control_fact.arm_id
    ):
        raise ValueError("组间差值必须使用同一试验内两个不同组别的事实")
    comparable_fields = (
        "field_id",
        "context",
        "population",
        "timepoint",
        "time_window",
        "cohort_id",
    )
    if any(
        getattr(treatment_fact, field) != getattr(control_fact, field)
        for field in comparable_fields
    ):
        raise ValueError("组间差值只能使用同一指标、人群和时间范围的事实")
    treatment_unit = treatment_fact.normalized_unit or treatment_fact.unit
    control_unit = control_fact.normalized_unit or control_fact.unit
    if treatment_unit is None or treatment_unit != control_unit:
        raise ValueError("组间差值的事实单位必须一致且明确")
    treatment_value = _numeric_fact_value(treatment_fact)
    control_value = _numeric_fact_value(control_fact)
    calculation = DeterministicCalculationRecord(
        operation="treatment_minus_control",
        formula_zh="试验组数值减去对照组数值",
        input_fact_version_ids=(
            treatment_fact.fact_version_id,
            control_fact.fact_version_id,
        ),
        input_values=(treatment_value, control_value),
        result=round(treatment_value - control_value, 12),
        unit=treatment_unit,
    )
    normalized_claim_text = " ".join(claim_text.split())
    result_text = format(calculation.result, "g")
    numeric_unit_pattern = re.compile(
        rf"(?<![0-9.])[+-]?(?:\d+(?:\.\d+)?|\.\d+)\s*{re.escape(treatment_unit)}"
    )
    stated_values = tuple(
        float(match.group(0).removesuffix(treatment_unit).strip())
        for match in numeric_unit_pattern.finditer(normalized_claim_text)
    )
    allowed_values = {treatment_value, control_value, calculation.result}
    negative_magnitude_words = ("下降", "减少", "降低")
    positive_magnitude_words = ("上升", "增加", "升高")
    all_calculation_values = (treatment_value, control_value, calculation.result)
    magnitude_mode = (
        all(value <= 0 for value in all_calculation_values)
        and any(word in normalized_claim_text for word in negative_magnitude_words)
    ) or (
        all(value >= 0 for value in all_calculation_values)
        and any(word in normalized_claim_text for word in positive_magnitude_words)
    )
    visible_result = abs(calculation.result) if magnitude_mode else calculation.result
    allowed_visible_values = (
        allowed_values | {abs(value) for value in allowed_values}
        if magnitude_mode
        else allowed_values
    )
    if (
        visible_result not in stated_values
        or any(value not in allowed_visible_values for value in stated_values)
        or (not magnitude_mode and result_text not in normalized_claim_text)
    ):
        raise ValueError("确定性计算声明文字与复算结果不一致")
    return _claim_version(
        claim_identity=claim_identity,
        claim_text=claim_text,
        claim_kind="deterministic_calculation",
        facts=(treatment_fact, control_fact),
        lineage_registry=lineage_registry,
        created_at=created_at,
        calculation=calculation,
    )


def create_synthesis_claim(
    *,
    claim_identity: str,
    claim_text: str,
    supporting_facts: tuple[AtomicFactVersion, ...],
    lineage_registry: ScientificLineageRegistry,
    synthesis_method_zh: str,
    created_at: datetime,
) -> ClaimVersion:
    if not " ".join(claim_text.split()).startswith("AI 综合判断："):
        raise ValueError("AI 综合判断必须在文字中明确标识")
    return _claim_version(
        claim_identity=claim_identity,
        claim_text=claim_text,
        claim_kind="synthesis",
        facts=supporting_facts,
        lineage_registry=lineage_registry,
        created_at=created_at,
        synthesis_method_zh=synthesis_method_zh,
    )
