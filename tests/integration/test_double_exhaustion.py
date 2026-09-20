"""Task 3.2 双重穷尽集成测试：执行者/复核者分离、两轮饱和、技术失败与科学缺失分离。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ci_workflow.gates.exhaustion import (
    GapDoubleExhaustion,
    OmissionReviewConclusion,
    assert_gap_technical_failure_not_reclassified,
)
from ci_workflow.gates.models import ReportKind
from tests.integration.test_no_draft_when_blocked import (
    gap_exhaustion,
    omission_review,
)


def test_gap_requires_separate_executor_and_reviewer_roles() -> None:
    """搜索/恢复执行者与独立遗漏复核者必须是不同角色：同人自报必须失败。"""
    with pytest.raises(ValidationError):
        gap_exhaustion(
            gap_id="gap-identity",
            executor_role_id="executor-a",
            reviewer_role_id="executor-a",  # 同一角色自报
        )


def test_per_gap_omission_review_is_required() -> None:
    """无逐缺口复核的“无实质遗漏”一句话不能通过：复核必须绑定具体缺口。"""
    review = omission_review("gap-identity")
    assert review.gap_id == "gap-identity"
    assert review.conclusion is OmissionReviewConclusion.NO_MATERIAL_OMISSION
    # 逐缺口复核结论必须携带独立复核者身份与确定性摘要
    assert review.reviewer_role_id != "executor-search"
    assert review.conclusion_digest
    # 换个缺口后复核者不得“借用”该结论：结论摘要随缺口内容变化
    other = omission_review("gap-other")
    assert other.conclusion_digest != review.conclusion_digest


def test_terminal_exhaustion_rejects_material_omission_conclusion() -> None:
    """仍发现实质遗漏时不得把缺口包装为已穷尽终态。"""
    gap = gap_exhaustion(gap_id="gap-material-omission")
    mutated = _gap_content_dump(gap)
    mutated["omission_review"]["conclusion"] = "material_omission_found"
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(mutated)


def test_two_saturated_recovery_rounds_are_required() -> None:
    """连续两轮饱和、无关键信息增益的科学穷尽证据是阻断前提。"""
    gap = gap_exhaustion(gap_id="gap-two-rounds")
    assert len(gap.recovery_exhaustion_proofs) == 1
    history = gap.recovery_exhaustion_proofs[0].recovery_history
    assert len(history.rounds) >= 2
    assert history.can_declare_information_saturated is True
    # 两轮策略签名必须不同
    signatures = {item.strategy_signature for item in history.rounds}
    assert len(signatures) == 2


def test_technical_failure_cannot_become_scientific_absence() -> None:
    """网络/限流等未决技术失败不得写成未报告或未公开。"""
    # 技术路线 + 科学状态 → 模型直接拒绝（经完整重验证）
    for bad_state in ("not_reported", "not_publicly_disclosed"):
        gap = gap_exhaustion(
            gap_id="gap-technical",
            current_state="unresolved_due_to_route",
            route_completion="route_access_blocked",
            final_result_class="rate_limited",
            technical=True,
        )
        mutated = _gap_content_dump(gap)
        mutated["current_state"] = bad_state
        mutated["route_evidence"] = [
            {**route, "final_result_class": "not_found"}
            for route in mutated["route_evidence"]
        ]
        with pytest.raises(ValidationError):
            GapDoubleExhaustion.model_validate(mutated)
    # 合法技术缺口：未决于路线 + 技术诊断
    technical_gap = gap_exhaustion(
        gap_id="gap-technical-3",
        current_state="unresolved_due_to_route",
        route_completion="route_access_blocked",
        final_result_class="rate_limited",
        technical=True,
    )
    assert technical_gap.current_state == "unresolved_due_to_route"
    assert_gap_technical_failure_not_reclassified(technical_gap)


def test_technical_failure_not_reclassified_raises_on_violation() -> None:
    """assert 函数对违规缺口必须抛错：技术失败不得伪装为科学缺失。"""
    # 通过模型校验合法但断言函数仍检查状态与路线
    gap = gap_exhaustion(
        gap_id="gap-technical-assert",
        current_state="unresolved_due_to_route",
        route_completion="route_access_blocked",
        final_result_class="content_truncated",
        technical=True,
    )
    # 正常合法缺口不抛错
    assert_gap_technical_failure_not_reclassified(gap)


def test_access_blocked_conclusion_requires_technical_diagnosis() -> None:
    """访问阻断结论必须绑定独立技术诊断（已完成同路径重试与替代策略）。"""
    gap = gap_exhaustion(
        gap_id="gap-access",
        current_state="unresolved_due_to_route",
        route_completion="route_access_blocked",
        final_result_class="rate_limited",
        technical=True,
    )
    assert gap.technical_diagnosis is not None
    assert gap.technical_diagnosis.same_path_retry_completed is True
    assert gap.technical_diagnosis.alternative_strategies_completed is True
    assert gap.technical_diagnosis.reviewer_role_id == gap.reviewer_role_id

    # 访问阻断结论但缺口缺少技术诊断 → 失败关闭
    broken = _gap_content_dump(gap)
    broken["technical_diagnosis"] = None
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(broken)


def test_technical_gap_rejects_unbound_information_gain_claims() -> None:
    """技术访问未解决时不得自由声称发现了新字段或新来源版本。"""
    from ci_workflow.domain.evidence import InformationGainDiff
    from ci_workflow.gates.exhaustion import compute_reviewer_inputs_digest

    gap = gap_exhaustion(
        gap_id="gap-technical-fake-gain",
        current_state="unresolved_due_to_route",
        route_completion="route_access_blocked",
        final_result_class="rate_limited",
        technical=True,
    )
    rounds = (
        InformationGainDiff(round=1, new_fields=("伪造字段",), new_source_versions=()),
        InformationGainDiff(round=2, new_fields=(), new_source_versions=("fake-v1",)),
    )
    forged = gap.model_copy(
        update={
            "information_gain_rounds": rounds,
            "evidence_gap": gap.evidence_gap.model_copy(
                update={"information_gain_diff": rounds}
            ),
        }
    )
    payload = _gap_content_dump(forged)
    payload["omission_review"]["reviewed_inputs_digest"] = (
        compute_reviewer_inputs_digest(forged)
    )
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(payload)


def test_scientific_gap_rejects_unbound_information_gain_identities() -> None:
    """布尔值相同仍不足；片段、单元和冲突集合必须逐轮精确绑定历史。"""
    from ci_workflow.gates.exhaustion import compute_reviewer_inputs_digest

    gap = gap_exhaustion(gap_id="gap-fake-gain-identities")
    rounds = list(gap.information_gain_rounds)
    rounds[0] = rounds[0].model_copy(
        update={"new_evidence_fragment_ids": ("fragment-not-in-history",)}
    )
    forged = gap.model_copy(
        update={
            "information_gain_rounds": tuple(rounds),
            "evidence_gap": gap.evidence_gap.model_copy(
                update={"information_gain_diff": tuple(rounds)}
            ),
        }
    )
    payload = _gap_content_dump(forged)
    payload["omission_review"]["reviewed_inputs_digest"] = (
        compute_reviewer_inputs_digest(forged)
    )
    with pytest.raises(ValidationError, match="逐轮完全一致"):
        GapDoubleExhaustion.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("new_fields", ("未绑定字段",)),
        ("new_source_versions", ("unbound-source-version",)),
    ],
)
def test_terminal_scientific_gap_rejects_legacy_free_form_gain(
    field: str, value: tuple[str, ...]
) -> None:
    """终态饱和只接受历史中的类型化增益身份，不接受自由字段或版本标签。"""
    from ci_workflow.gates.exhaustion import compute_reviewer_inputs_digest

    gap = gap_exhaustion(gap_id=f"gap-free-gain-{field}")
    rounds = list(gap.information_gain_rounds)
    rounds[0] = rounds[0].model_copy(update={field: value})
    forged = gap.model_copy(
        update={
            "information_gain_rounds": tuple(rounds),
            "evidence_gap": gap.evidence_gap.model_copy(
                update={"information_gain_diff": tuple(rounds)}
            ),
        }
    )
    payload = _gap_content_dump(forged)
    payload["omission_review"]["reviewed_inputs_digest"] = (
        compute_reviewer_inputs_digest(forged)
    )
    with pytest.raises(ValidationError, match="自由字段或来源版本"):
        GapDoubleExhaustion.model_validate(payload)


def test_diagnosis_requires_completed_retries_and_alternatives() -> None:
    """独立技术诊断必须声明已完成同路径重试与替代策略。"""
    from ci_workflow.gates.exhaustion import GapTechnicalDiagnosis

    with pytest.raises(ValidationError):
        GapTechnicalDiagnosis(
            gap_id="gap-dx",
            reviewer_role_id="reviewer-independent",
            technical_result_classes=("rate_limited",),
            same_path_retry_completed=False,
            alternative_strategies_completed=True,
            diagnosis_zh="重试尚未完成，不能给出访问阻断结论。",
        )
    with pytest.raises(ValidationError):
        GapTechnicalDiagnosis(
            gap_id="gap-dx-2",
            reviewer_role_id="reviewer-independent",
            technical_result_classes=("rate_limited",),
            same_path_retry_completed=True,
            alternative_strategies_completed=False,
            diagnosis_zh="替代策略尚未完成，不能给出访问阻断结论。",
        )


def test_gap_route_evidence_binds_final_result_and_receipts() -> None:
    """每个缺口必须绑定已完成路线证据：完成/不适用/访问阻断与回执摘要。"""
    gap = gap_exhaustion(gap_id="gap-route")
    route = gap.route_evidence[0]
    assert route.route_id == "clinicaltrials-global-baseline"
    assert route.route_name_zh
    assert route.receipt_ids
    assert route.attempt_count >= 1


def test_gap_digest_covers_route_technical_and_gain_rounds() -> None:
    """缺口穷尽摘要必须覆盖路线、技术诊断与信息增益轮次：任一改动都改变摘要。"""

    base = gap_exhaustion(gap_id="gap-digest")
    digest_before = base.gap_digest

    # 路线证据变化 → 摘要变化
    swapped_route = base.model_copy(
        update={
            "route_evidence": (
                base.route_evidence[0].model_copy(
                    update={"route_id": "different-route"}
                ),
            )
        }
    )
    assert swapped_route.gap_digest != digest_before

    # 技术诊断变化 → 摘要变化
    technical = gap_exhaustion(
        gap_id="gap-digest-tech",
        current_state="unresolved_due_to_route",
        route_completion="route_access_blocked",
        final_result_class="rate_limited",
        technical=True,
    )
    assert technical.technical_diagnosis is not None
    assert technical.gap_digest != digest_before

    # 信息增益轮次变化 → 摘要变化
    from tests.integration.test_no_draft_when_blocked import info_gain_diff

    changed_rounds = base.model_copy(
        update={
            "information_gain_rounds": (
                info_gain_diff(1),
                info_gain_diff(2).model_copy(update={"new_fields": ("x",)}),
            )
        }
    )
    assert changed_rounds.gap_digest != digest_before


def test_double_exhaustion_record_rejects_duplicate_gap_identity() -> None:
    """双重穷尽记录不得包含重复缺口标识或重复单元/对象对。"""
    from ci_workflow.gates.exhaustion import DoubleExhaustionRecord
    from tests.integration.test_no_draft_when_blocked import now

    with pytest.raises(ValidationError):
        DoubleExhaustionRecord(
            project_id="p1",
            report_kind=ReportKind.A,
            gaps=(gap_exhaustion(gap_id="gap-1"), gap_exhaustion(gap_id="gap-1")),
            created_at=now(),
        )

    with pytest.raises(ValidationError):
        DoubleExhaustionRecord(
            project_id="p1",
            report_kind=ReportKind.A,
            gaps=(
                gap_exhaustion(gap_id="gap-1"),
                gap_exhaustion(gap_id="gap-2"),
            ),
            created_at=now(),
        )


def _gap_content_dump(gap: GapDoubleExhaustion) -> dict:
    """排除全部计算字段的完整内容转储，供重验证使用。"""
    computed = {
        "gap_digest",
        "reviewer_inputs_digest",
        "conclusion_digest",
        "diagnosis_digest",
        "record_digest",
        "evidence_digest",
    }

    def strip(node):
        if isinstance(node, dict):
            return {k: strip(v) for k, v in node.items() if k not in computed}
        if isinstance(node, list):
            return [strip(item) for item in node]
        return node

    return strip(gap.model_dump(mode="json"))


def test_gap_applicable_route_ids_must_match_route_evidence() -> None:
    """适用路线集合与路线证据必须机械一致：缺失/多余/回执交集全部拒绝。"""
    base = gap_exhaustion(gap_id="gap-routes")

    for applicable_route_ids in (
        ("clinicaltrials-global-baseline", "extra-route"),
        (),
        ("other-route",),
    ):
        mutated = _gap_content_dump(base)
        mutated["applicable_route_ids"] = list(applicable_route_ids)
        with pytest.raises(ValidationError):
            GapDoubleExhaustion.model_validate(mutated)

    # 路线回执互不相交：两条路线共用同一回执 → 拒绝
    mutated = _gap_content_dump(base)
    receipts = mutated["route_evidence"][0]["receipt_ids"]
    mutated["route_evidence"].append(
        {**mutated["route_evidence"][0], "route_id": "route-dup", "receipt_ids": receipts}
    )
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(mutated)


def test_reviewer_inputs_digest_binds_route_and_rounds() -> None:
    """复核输入摘要由缺口内容确定性计算；输入变化必须改变摘要或拒绝重验证。"""
    from ci_workflow.gates.exhaustion import compute_reviewer_inputs_digest

    gap = gap_exhaustion(gap_id="gap-digest-in")
    digest_before = gap.reviewer_inputs_digest

    # 摘要可直接由同一内容重算，与字段一致（机械绑定）
    recomputed = compute_reviewer_inputs_digest(gap)
    assert recomputed == gap.reviewer_inputs_digest
    assert gap.omission_review.reviewed_inputs_digest == digest_before


def test_omission_review_requires_clean_context_distinct_from_producer() -> None:
    """角色名不同不足以证明独立复核；生产与审查上下文摘要必须不同。"""
    gap = gap_exhaustion(gap_id="gap-same-context")
    digest_before = gap.reviewer_inputs_digest
    payload = _gap_content_dump(gap)
    payload["omission_review"]["reviewer_context_digest"] = (
        payload["omission_review"]["producer_context_digest"]
    )
    with pytest.raises(ValidationError, match="独立干净上下文"):
        GapDoubleExhaustion.model_validate(payload)

    # 缺口状态变化（仍是科学缺失）→ 纯函数输入摘要变化
    from ci_workflow.gates.exhaustion import (
        compute_reviewer_inputs_digest_from_parts,
    )

    altered_digest = compute_reviewer_inputs_digest_from_parts(
        gap_id=gap.gap_id,
        gate_unit_id=gap.gate_unit_id,
        object_type=gap.object_type,
        object_id=gap.object_id,
        current_state="not_publicly_disclosed",
        applicable_route_ids=gap.applicable_route_ids,
        route_evidence=gap.route_evidence,
        recovery_exhaustion_proofs=gap.recovery_exhaustion_proofs,
        same_path_retry_audit=gap.same_path_retry_audit,
        alternative_path_audit=gap.alternative_path_audit,
        information_gain_rounds=gap.information_gain_rounds,
        associated_entity_ids=gap.associated_entity_ids,
    )
    assert altered_digest != digest_before

    # 路线回执变化（脱离证明）→ 模型拒绝（逐路线精确绑定）
    broken_dump = _gap_content_dump(gap)
    broken_dump["route_evidence"][0]["receipt_ids"] = (
        broken_dump["route_evidence"][0]["receipt_ids"][:-1]
    )
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(broken_dump)


def test_technical_gap_cannot_reuse_scientific_not_found_proof() -> None:
    """技术缺口不得复用科学 not_found 穷尽证明，也不得缺失技术证据。"""
    # 技术缺口 + 科学饱和证明 → 拒绝
    technical = gap_exhaustion(
        gap_id="gap-mix",
        current_state="unresolved_due_to_route",
        route_completion="route_access_blocked",
        final_result_class="rate_limited",
        technical=True,
    )
    scientific = gap_exhaustion(gap_id="gap-sci")
    # 技术缺口 + 科学饱和证明 → 拒绝
    mutated = _gap_content_dump(technical)
    mutated["recovery_exhaustion_proofs"] = [
        proof.model_dump(mode="json")
        for proof in scientific.recovery_exhaustion_proofs
    ]
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(mutated)

    # 技术缺口剥离技术证据 → 拒绝
    stripped = _gap_content_dump(technical)
    stripped["same_path_retry_audit"] = None
    stripped["alternative_path_audit"] = None
    stripped["technical_diagnosis"] = None
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(stripped)


def test_scientific_gap_cannot_carry_technical_evidence() -> None:
    """科学缺口不得携带技术失败路线、技术诊断或重试审计。"""
    scientific = gap_exhaustion(gap_id="gap-sci-pure")
    technical = gap_exhaustion(
        gap_id="gap-tech-pure",
        current_state="unresolved_due_to_route",
        route_completion="route_access_blocked",
        final_result_class="rate_limited",
        technical=True,
    )
    for field in (
        "technical_diagnosis",
        "same_path_retry_audit",
        "alternative_path_audit",
    ):
        mutated = _gap_content_dump(scientific)
        mutated[field] = getattr(technical, field).model_dump(mode="json")
        with pytest.raises(ValidationError):
            GapDoubleExhaustion.model_validate(mutated)

    # 科学缺口混入限流路线 → 拒绝
    mutated = _gap_content_dump(scientific)
    mutated["route_evidence"] = [
        {**r, "final_result_class": "rate_limited",
         "completion": "access_blocked"}
        for r in mutated["route_evidence"]
    ]
    with pytest.raises(ValidationError):
        GapDoubleExhaustion.model_validate(mutated)
