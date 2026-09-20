"""Task 3.1 版本化 A/B/C 证据规则：闭世界对象集合、作用域证据与报告特异评估器。

评估器读取已闭合宇宙和不可变事实，从已接受事实确定性地推导成熟度和结果承载，
逐单元逐对象评估，产生版本化报告门槛结果。

- 评估输入必须绑定已闭合宇宙；未知、重复、漏评或未证明为空的对象集合失败关闭。
- 证据绑定引用的对象必须属于已闭合宇宙且处于同一条作用域路径；未知对象失败关闭。
- 组/比较/试验/终点/时间点级规则只能由同作用域事实满足；
  总体值（无组作用域）或错误作用域不得冒充分组值。
- 比较级单元按试验判定：比较设计试验对真实比较对象评估，
  单臂设计试验给出试验锚定的明确不适用，其他试验的比较不得豁免本试验。
- 终点级单元（核心疗效终点）按试验设计解析权威适用组别：
  比较试验取关联比较的全部组别（无关联时取该试验全部组别），
  单臂试验取终点显式关联组别；每个组别需要独立合格数值绑定，
  一个绑定不能覆盖两个组，同一不可变事实版本只能证明一个组别。
- 空对象类不得让关键单元消失：对声明父对象（必要时产品集合）出确定性结果；
  has_comparator 在类型化单臂空比较证明下明确不适用。
- region_visit_operational_key 仅在版本化指示规则合同声明其为关键时适用。
- 适用性谓词由评估器从已接受事实确定性推导，不接受调用方传入。
- 结果键绑定报告类型、证据快照、规则指纹、合同版本与集合摘要。
- A 的成熟度由已接受事实确定，不接受调用方手工降级。
- result_bearing 只由属于适格试验的已接受观察性疗效/安全数值事实触发。
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from ci_workflow.domain.enums import (
    FactDisclosureState,
    FactReviewState,
)
from ci_workflow.gates.models import (
    ApplicableUniverseSnapshot,
    DevelopmentMaturity,
    EmptySetReasonCode,
    FactDomain,
    GateBlockingLevel,
    GateEvaluationError,
    GateEvidenceBinding,
    GateObjectType,
    GateSpec,
    GateUnitOutcome,
    GateUnitResult,
    GateUnitSpec,
    ObservationKind,
    ReportGateResult,
    SourceRole,
    TrialDesignKind,
    _aggregate_report_gates,
    _best_disclosure_state,
    _GateEvaluationBatch,
    assert_applicable_universe_closed,
    assert_bindings_in_universe,
    derive_expected_unit_object_pairs,
    evaluate_unit_decision,
    evidence_binding_qualifies,
)

# ── 固定集合 ────────────────────────────────────────────────────────────────

_REPORTED_STATES: frozenset[FactDisclosureState] = frozenset(
    {FactDisclosureState.REPORTED_VALUE, FactDisclosureState.REPORTED_ZERO}
)

_RESULT_BEARING_SOURCE_ROLES: frozenset[SourceRole] = frozenset(
    {
        SourceRole.CLINICAL_TRIAL_REGISTRY,
        SourceRole.REGULATORY_MATERIAL,
        SourceRole.PRIMARY_TRIAL_REPORT,
        SourceRole.CONFERENCE_DISCLOSURE,
        SourceRole.COMPANY_DISCLOSURE,
        SourceRole.DESIGNATED_INDUSTRY_SOURCE,
    }
)

_CLINICAL_MATURITIES: frozenset[DevelopmentMaturity] = frozenset(
    {
        DevelopmentMaturity.CLINICAL,
        DevelopmentMaturity.SUBMISSION,
        DevelopmentMaturity.APPROVED,
        DevelopmentMaturity.PAUSED_TERMINATED_WITHDRAWN,
    }
)

_SUBMISSION_MATURITIES: frozenset[DevelopmentMaturity] = frozenset(
    {
        DevelopmentMaturity.SUBMISSION,
        DevelopmentMaturity.APPROVED,
        DevelopmentMaturity.PAUSED_TERMINATED_WITHDRAWN,
    }
)


# 对象类型 → 证据绑定必须携带的作用域属性。
# 组级规则只能由同组事实满足，比较/试验/终点/时间点级同理；
# 产品级事实允许携带试验作用域（如成熟度与结果承载判定），不做作用域相等约束。
_SCOPE_ATTR_BY_OBJECT_TYPE: dict[GateObjectType, str | None] = {
    GateObjectType.PRODUCT: None,
    GateObjectType.TRIAL: "trial_id",
    GateObjectType.COMPARISON: "comparison_id",
    GateObjectType.GROUP: "group_id",
    GateObjectType.ENDPOINT: "endpoint_id",
    GateObjectType.TIMEPOINT: "timepoint_id",
}


def _binding_scope_matches(
    unit: GateUnitSpec, object_id: str, binding: GateEvidenceBinding
) -> bool:
    """证据绑定的作用域必须与单元评估对象一致。

    总体值（无组/比较作用域）或错误作用域不得满足组级、比较级等作用域规则；
    缺少作用域属性的绑定一律不计入该对象的合格证据。
    """
    attribute = _SCOPE_ATTR_BY_OBJECT_TYPE[unit.object_type]
    if attribute is None:
        return True
    scope_value = cast("str | None", getattr(binding, attribute))
    return scope_value == object_id


# ── 成熟度推导 ──────────────────────────────────────────────────────────────


def derive_product_maturity(
    product_id: str,
    bindings: Sequence[GateEvidenceBinding],
) -> DevelopmentMaturity:
    """从已接受事实确定性地推导产品开发成熟度；不接受调用方手工降级。

    推导规则：
    - 暂停/终止/撤回：已接受监管事实且披露状态为不适用
    - 已批准：已接受监管事实且有观察性数值结果与已报告值
    - 申报：已接受监管事实
    - 临床：已接受试验事实（trial_id 非空）
    - 临床前：无以上事实
    """
    indicators: set[str] = set()
    for binding in bindings:
        if binding.object_id != product_id:
            continue
        if binding.review_state is not FactReviewState.ACCEPTED:
            continue
        if binding.trial_id is not None:
            indicators.add("clinical_trial")
        if binding.source_role is SourceRole.REGULATORY_MATERIAL:
            indicators.add("regulatory_material")
            if (
                binding.observation_kind is ObservationKind.OBSERVED_RESULT
                and binding.disclosure_state is FactDisclosureState.REPORTED_VALUE
            ):
                indicators.add("regulatory_observed_result")
            if binding.disclosure_state is FactDisclosureState.NOT_APPLICABLE:
                indicators.add("regulatory_not_applicable")
    if "regulatory_not_applicable" in indicators:
        return DevelopmentMaturity.PAUSED_TERMINATED_WITHDRAWN
    if "regulatory_observed_result" in indicators:
        return DevelopmentMaturity.APPROVED
    if "regulatory_material" in indicators:
        return DevelopmentMaturity.SUBMISSION
    if "clinical_trial" in indicators:
        return DevelopmentMaturity.CLINICAL
    return DevelopmentMaturity.PRECLINICAL


# ── 结果承载（含适格试验要求） ──────────────────────────────────────────────


def check_result_bearing(
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
) -> bool:
    """result_bearing 只由属于适格试验的已接受观察性疗效/安全数值事实触发。

    合同要求：事实必须属于目标适应症适格试验（trial_id 已设置且在宇宙中）。
    计划样本量、目标值和方案假设均不触发。
    """
    for binding in bindings:
        if binding.review_state is not FactReviewState.ACCEPTED:
            continue
        if binding.fact_domain not in (FactDomain.EFFICACY, FactDomain.SAFETY):
            continue
        if binding.observation_kind is not ObservationKind.OBSERVED_RESULT:
            continue
        if binding.numeric_value is None:
            continue
        if binding.disclosure_state not in _REPORTED_STATES:
            continue
        if binding.source_role not in _RESULT_BEARING_SOURCE_ROLES:
            continue
        # 合同要求：事实必须属于适格试验
        if binding.trial_id is None:
            continue
        if binding.trial_id not in snapshot.trial_ids:
            raise GateEvaluationError("结果承载判定引用未知试验对象")
        return True
    return False


# ── 适用性谓词 ──────────────────────────────────────────────────────────────


def _is_applicable(
    unit: GateUnitSpec,
    object_id: str,
    *,
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
) -> tuple[bool, bool]:
    """判定单元对指定对象是否适用；返回 (applicable, justified)。"""
    predicate = unit.applicability_predicate_id
    if predicate == "always_applicable":
        return (True, True)
    if predicate == "result_bearing":
        product_bindings = [b for b in bindings if b.object_id == object_id]
        return (check_result_bearing(snapshot, product_bindings), True)
    if predicate == "maturity_ge_clinical":
        maturity = derive_product_maturity(object_id, bindings)
        return (maturity in _CLINICAL_MATURITIES, True)
    if predicate == "maturity_ge_submission":
        maturity = derive_product_maturity(object_id, bindings)
        return (maturity in _SUBMISSION_MATURITIES, True)
    if predicate == "has_comparator":
        if snapshot.comparison_ids:
            return (True, True)
        comparison_proof = next(
            (
                proof
                for proof in snapshot.empty_set_proofs
                if proof.object_type is GateObjectType.COMPARISON
            ),
            None,
        )
        if (
            comparison_proof is not None
            and comparison_proof.reason_code
            is EmptySetReasonCode.STUDY_DESIGN_SINGLE_ARM
        ):
            return (False, True)
        raise GateEvaluationError(
            "比较对象为空但没有单臂研究设计证明，不能免除治疗与对照证据"
        )
    if predicate == "region_visit_operational_key":
        # 仅在版本化指示规则合同声明其为关键时适用；未声明即为明确不适用
        return (predicate in snapshot.applicable_conditional_predicates, True)
    raise GateEvaluationError(f"未知适用性谓词：{predicate}")


# ── 宇宙关系图索引 ──────────────────────────────────────────────────────────


class _UniverseIndex:
    """由已闭合关系图与设计证据构建的只读索引；评估器专用。

    只读消费快照内容，不改变宇宙；用于按试验/比较/终点解析适用对象与权威组别。
    """

    def __init__(self, snapshot: ApplicableUniverseSnapshot) -> None:
        self.trial_product: dict[str, str] = {}
        self.comparison_trial: dict[str, str] = {}
        self.group_trial: dict[str, str] = {}
        self.endpoint_trial: dict[str, str] = {}
        self.timepoint_endpoint: dict[str, str] = {}
        self.trial_comparisons: dict[str, set[str]] = {
            trial_id: set() for trial_id in snapshot.trial_ids
        }
        self.trial_groups: dict[str, set[str]] = {
            trial_id: set() for trial_id in snapshot.trial_ids
        }
        self.comparison_groups: dict[str, set[str]] = {
            comparison_id: set() for comparison_id in snapshot.comparison_ids
        }
        self.comparison_endpoints: dict[str, set[str]] = {
            comparison_id: set() for comparison_id in snapshot.comparison_ids
        }
        self.endpoint_groups: dict[str, set[str]] = {
            endpoint_id: set() for endpoint_id in snapshot.endpoint_ids
        }
        for edge in snapshot.relationship_edges:
            if edge.parent_type is GateObjectType.PRODUCT:
                self.trial_product[edge.child_id] = edge.parent_id
            elif edge.parent_type is GateObjectType.TRIAL:
                if edge.child_type is GateObjectType.COMPARISON:
                    self.comparison_trial[edge.child_id] = edge.parent_id
                    self.trial_comparisons[edge.parent_id].add(edge.child_id)
                elif edge.child_type is GateObjectType.GROUP:
                    self.group_trial[edge.child_id] = edge.parent_id
                    self.trial_groups[edge.parent_id].add(edge.child_id)
                else:
                    self.endpoint_trial[edge.child_id] = edge.parent_id
            elif edge.parent_type is GateObjectType.COMPARISON:
                if edge.child_type is GateObjectType.GROUP:
                    self.comparison_groups[edge.parent_id].add(edge.child_id)
                else:
                    self.comparison_endpoints[edge.parent_id].add(edge.child_id)
            elif edge.parent_type is GateObjectType.ENDPOINT:
                if edge.child_type is GateObjectType.GROUP:
                    self.endpoint_groups[edge.parent_id].add(edge.child_id)
                else:
                    self.timepoint_endpoint[edge.child_id] = edge.parent_id
            else:
                self.timepoint_endpoint[edge.child_id] = edge.parent_id
        self.design_by_trial = {
            record.trial_id: record for record in snapshot.trial_design_evidence
        }
        self.comparison_proof = next(
            (
                proof
                for proof in snapshot.empty_set_proofs
                if proof.object_type is GateObjectType.COMPARISON
            ),
            None,
        )


# ── 终点级单元（核心疗效终点）逐组数值 ──────────────────────────────────────


def _endpoint_associated_groups(
    snapshot: ApplicableUniverseSnapshot, endpoint_id: str
) -> tuple[str, ...]:
    """终点→组别关联边构成该终点的权威适用组别集合。"""
    return tuple(
        sorted(
            edge.child_id
            for edge in snapshot.relationship_edges
            if edge.parent_type is GateObjectType.ENDPOINT
            and edge.parent_id == endpoint_id
            and edge.child_type is GateObjectType.GROUP
        )
    )


def _endpoint_required_groups(
    endpoint_id: str,
    *,
    snapshot: ApplicableUniverseSnapshot,
    index: _UniverseIndex,
) -> frozenset[str]:
    """终点的权威适用组别：按试验设计类型解析。

    - 比较设计：与终点存在关联边的比较所关联的全部组别；无关联比较时
      采用该试验的全部组别（保守失败关闭）；
    - 单臂设计：终点显式关联的组别，不虚构对照。
    """
    trial_id = index.endpoint_trial.get(endpoint_id)
    if trial_id is None:
        return frozenset(_endpoint_associated_groups(snapshot, endpoint_id))
    design = index.design_by_trial.get(trial_id)
    if design is not None and design.design_kind is TrialDesignKind.COMPARATIVE:
        linked_comparisons = tuple(
            sorted(
                comparison_id
                for comparison_id, endpoints in index.comparison_endpoints.items()
                if endpoint_id in endpoints
            )
        )
        if linked_comparisons:
            return frozenset(
                group_id
                for comparison_id in linked_comparisons
                for group_id in index.comparison_groups.get(comparison_id, set())
            )
        return frozenset(index.trial_groups.get(trial_id, set()))
    return frozenset(_endpoint_associated_groups(snapshot, endpoint_id))


def _evaluate_endpoint_unit(
    unit: GateUnitSpec,
    endpoint_id: str,
    *,
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
    index: _UniverseIndex,
) -> GateUnitResult:
    """终点级单元：每个权威适用组别必须有一个独立合格数值绑定。

    - 一个绑定即使同时携带治疗/对照标签也只能覆盖其绑定组别；
    - 同一组别的重复绑定不能覆盖另一组别；
    - 同一不可变事实版本被多个组别引用时不得计入覆盖（一个证据只能证明一个组）；
    - 无组别作用域的总体值不能覆盖任何组别；
    - 终点无任何适用组别时失败关闭（阻断/扩展缺失），不虚构通过。
    """
    required = _endpoint_required_groups(
        endpoint_id, snapshot=snapshot, index=index
    )
    scope_bindings = tuple(
        binding
        for binding in bindings
        if binding.object_id == endpoint_id and binding.unit_id == unit.unit_id
    )
    has_open_critical_conflict = (
        unit.blocking_level is GateBlockingLevel.CRITICAL
        and any(
            binding.disclosure_state is FactDisclosureState.CONFLICTING
            for binding in scope_bindings
        )
    )
    qualifying = (
        ()
        if has_open_critical_conflict
        else tuple(
            binding
            for binding in scope_bindings
            if evidence_binding_qualifies(binding, unit, snapshot=snapshot)
        )
    )
    fact_groups: dict[str, set[str]] = {}
    for binding in qualifying:
        if binding.group_id is None or binding.group_id not in required:
            continue
        fact_groups.setdefault(binding.fact_version_id, set()).add(
            binding.group_id
        )
    # 一个不可变事实版本只能证明一个组别；跨组引用不计数。
    # 谱系只保留实际计数的不同事实版本，跨组复用不得放大计数或结果谱系。
    contributing_groups = {
        fact_version_id: next(iter(groups))
        for fact_version_id, groups in fact_groups.items()
        if len(groups) == 1 and next(iter(groups)) in required
    }
    contributing = tuple(sorted(contributing_groups))
    covered = frozenset(contributing_groups.values())
    # 事实阈值和组别覆盖是两个独立条件：保留全部合法谱系，不能用事实数量
    # 替代完整覆盖，也不能因一组具有多个合法事实而违反结果模型的计数合同。
    satisfied_count = len(contributing)
    coverage_complete = bool(required) and covered == required
    # 有效阈值取规格阈值与适用组别数的较大者：覆盖收紧不得被组别数稀释。
    threshold = max(unit.threshold, len(required))
    if coverage_complete and satisfied_count >= threshold:
        outcome = GateUnitOutcome.SATISFIED
        blocking = False
        failure_code = None
        user_note_zh = None
    elif unit.blocking_level is GateBlockingLevel.CRITICAL:
        outcome = GateUnitOutcome.BLOCKED
        blocking = True
        failure_code = unit.failure_code
        user_note_zh = (
            f"{unit.user_label_zh}缺失：{unit.missing_impact_zh}。"
            f"{unit.user_next_step_zh}"
        )
    else:
        outcome = GateUnitOutcome.EXTENSION_MISSING
        blocking = False
        failure_code = unit.failure_code
        user_note_zh = None
    return GateUnitResult(
        unit_id=unit.unit_id,
        report_kind=unit.report_kind,
        object_id=endpoint_id,
        applicable=True,
        outcome=outcome,
        blocking=blocking,
        threshold=threshold,
        satisfied_count=satisfied_count,
        coverage_complete=coverage_complete,
        fact_version_ids=contributing,
        source_locations=tuple(
            sorted(
                binding.source_location
                for binding in qualifying
                if binding.fact_version_id in contributing_groups
                and binding.source_location is not None
            )
        ),
        disclosure_state=(
            FactDisclosureState.CONFLICTING
            if has_open_critical_conflict
            else _best_disclosure_state(scope_bindings)
        ),
        failure_code=failure_code,
        user_note_zh=user_note_zh,
    )


# ── 报告级评估 ──────────────────────────────────────────────────────────────


def evaluate_report(
    spec: GateSpec,
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
    *,
    contract_version: str,
) -> ReportGateResult:
    """评估一份报告的完整门槛：闭世界校验 → 完整期望矩阵 → 逐对象评估 → 合取。

    - 评估输入必须绑定已闭合宇宙；未知、重复、漏评或未证明为空的对象集合失败关闭。
    - 证据绑定引用的对象必须属于已闭合宇宙；未知对象失败关闭。
    - 评估迭代与聚合共用 derive_expected_unit_object_pairs 的单一规范矩阵：
      对象类空 → 声明父对象（必要时产品集合）锚点；比较级单元按试验判定。
    - 终点级单元按终点→组别关联逐组要求独立数值绑定，有效阈值取规格阈值与
      适用组别数的较大者。
    - 适用性谓词由评估器从已接受事实确定性推导，不接受调用方传入。
    - 结果键绑定报告类型、证据快照、规则指纹、合同版本与集合摘要。
    - A/B/C 共享证据版本，不共享证据规则结果。
    """
    assert_applicable_universe_closed(snapshot)
    assert_bindings_in_universe(snapshot, bindings)

    index = _UniverseIndex(snapshot)
    spec_units = {unit.unit_id: unit for unit in spec.units}
    unknown_unit_ids = sorted(
        {binding.unit_id for binding in bindings}.difference(spec_units)
    )
    if unknown_unit_ids:
        raise GateEvaluationError(
            "证据绑定引用未知门槛单元：" + "、".join(unknown_unit_ids)
        )
    unit_results: list[GateUnitResult] = []

    for unit_id, object_id in derive_expected_unit_object_pairs(spec, snapshot):
        unit = spec_units[unit_id]
        if unit.object_type is GateObjectType.COMPARISON:
            if object_id in snapshot.comparison_ids:
                scoped_bindings = tuple(
                    binding
                    for binding in bindings
                    if _binding_scope_matches(unit, object_id, binding)
                )
                applicable, justified = _is_applicable(
                    unit, object_id, snapshot=snapshot, bindings=scoped_bindings
                )
                unit_results.append(
                    evaluate_unit_decision(
                        unit,
                        object_id=object_id,
                        applicable=applicable,
                        applicability_justified=justified,
                        bindings=scoped_bindings,
                        snapshot=snapshot,
                    )
                )
            else:
                # 单臂试验（或无试验时产品集合）的试验锚定明确不适用；
                # 必须有单臂研究设计证明，普通空比较证明不得豁免对照证据。
                if object_id in snapshot.trial_ids:
                    design = index.design_by_trial.get(object_id)
                    if (
                        design is None
                        or design.design_kind is not TrialDesignKind.SINGLE_ARM
                    ):
                        raise GateEvaluationError(
                            "试验缺少单臂研究设计证明，比较级单元不得判定为"
                            "不适用，必须失败关闭"
                        )
                    if not snapshot.comparison_ids:
                        proof = index.comparison_proof
                        if (
                            proof is None
                            or proof.reason_code
                            is not EmptySetReasonCode.STUDY_DESIGN_SINGLE_ARM
                        ):
                            raise GateEvaluationError(
                                "比较对象集合为空但缺少单臂研究设计证明，"
                                "必须失败关闭"
                            )
                unit_results.append(
                    evaluate_unit_decision(
                        unit,
                        object_id=object_id,
                        applicable=False,
                        applicability_justified=True,
                        bindings=(),
                        snapshot=snapshot,
                    )
                )
            continue
        scoped_bindings = tuple(
            binding
            for binding in bindings
            if _binding_scope_matches(unit, object_id, binding)
        )
        applicable, justified = _is_applicable(
            unit, object_id, snapshot=snapshot, bindings=scoped_bindings
        )
        if unit.object_type is GateObjectType.ENDPOINT and applicable:
            unit_results.append(
                _evaluate_endpoint_unit(
                    unit,
                    object_id,
                    snapshot=snapshot,
                    bindings=scoped_bindings,
                    index=index,
                )
            )
        else:
            unit_results.append(
                evaluate_unit_decision(
                    unit,
                    object_id=object_id,
                    applicable=applicable,
                    applicability_justified=justified,
                    bindings=scoped_bindings,
                    snapshot=snapshot,
                )
            )

    if not unit_results:
        raise GateEvaluationError(
            "评估未产生任何单元结果，可能所有单元均不适用；"
            "请确认适用对象集合与谓词配置"
        )

    batch = _GateEvaluationBatch.from_evaluation(
        spec=spec, snapshot=snapshot, unit_results=unit_results
    )
    return _aggregate_report_gates(
        spec=spec,
        snapshot=snapshot,
        batch=batch,
        contract_version=contract_version,
    )
