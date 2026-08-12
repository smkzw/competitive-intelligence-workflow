"""Task 3.1 项目合同覆盖服务：逐字段只收紧偏序、不可变结果键与反向依赖重算。

项目覆盖只允许增加单元、提高阈值、扩大适用对象或收窄可接受集合；
任何删除、降低、放宽或其他无法证明为收紧的操作失败关闭。

- 偏序按逐字段比较，不以单元数量或一个总分代替：
  `new_applicable_set ⊇ old_applicable_set`、`new_source_roles ⊆ old_source_roles`、
  `new_maturity_floor ≥ old_maturity_floor`、`new_conflict_acceptance ⊆ old_conflict_acceptance`；
  非阻断缺失可改为阻断，阻断不得放松为非阻断。
- 规则结果不可变键由报告类型、证据快照 ID、基础规则版本、项目合同版本和
  适用对象集合摘要共同确定；父结果永不就地覆盖。
- 受影响报告由变更单元到报告类型的反向依赖计算；
  调用方声明集合与计算集合不完全一致则拒绝。
- 父合同不存在、已被错误替换或证据快照不一致时不得生成子结果。
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from ci_workflow.domain.enums import ReportKind
from ci_workflow.gates.evaluator import evaluate_report
from ci_workflow.gates.models import (
    ApplicableUniverseSnapshot,
    ConflictStrategy,
    GateBlockingLevel,
    GateEvaluationError,
    GateEvidenceBinding,
    GateOverride,
    GateSpec,
    GateUnitSpec,
    MissingStrategy,
    ReportGateResult,
    compute_gate_result_key,
    disclosure_maturity_rank,
)

# 可证明的适用性拓宽：旧谓词 → 新谓词，且新适用集合 ⊇ 旧适用集合。
# always_applicable 对对象类型全集适用，故任何谓词 → always_applicable 都是拓宽；
# 申报成熟度集合 ⊆ 临床成熟度集合，故 maturity_ge_submission → maturity_ge_clinical 是拓宽。
# 其余谓词变化无法在规格层证明为扩大，按失败关闭拒绝。
_APPLICABILITY_WIDENINGS: frozenset[tuple[str, str]] = frozenset(
    {
        ("maturity_ge_submission", "maturity_ge_clinical"),
    }
)


def _applicability_is_widening(old_predicate: str, new_predicate: str) -> bool:
    if old_predicate == new_predicate:
        return True
    if new_predicate == "always_applicable":
        return True
    return (old_predicate, new_predicate) in _APPLICABILITY_WIDENINGS


def compare_unit_strictness(
    parent: GateUnitSpec, child: GateUnitSpec
) -> tuple[str, ...]:
    """逐字段比较单单元只收紧偏序；返回全部违反描述，空元组 = 单调。

    只收紧规则（固定偏序算法）：
    - 阈值只能提高；阻断（false→true）允许、反向拒绝；
    - 允许来源角色集合只能收窄，最低披露成熟度只能提高；
    - 可接受事实状态、允许事实域与允许观察类型只能收窄；
    - 可接受冲突处置只能收窄；
    - 非阻断缺失可改为阻断，阻断不得放松；
    - 必需上下文字段只能增加；
    - 适用对象类型、父子对象范围不得以无法证明为扩大的方式变化；
    - 适用性谓词只能保持不变或可证明地拓宽。
    """
    violations: list[str] = []
    if child.report_kind is not parent.report_kind:
        violations.append(f"{parent.unit_id} 报告类型发生变化")
    if child.threshold < parent.threshold:
        violations.append(
            f"{parent.unit_id} 阈值降低：{parent.threshold} -> {child.threshold}"
        )
    if (
        parent.blocking_level is GateBlockingLevel.CRITICAL
        and child.blocking_level is not GateBlockingLevel.CRITICAL
    ):
        violations.append(f"{parent.unit_id} 阻断级别放松：关键改为扩展")
    extra_roles = set(child.allowed_source_roles) - set(parent.allowed_source_roles)
    if extra_roles:
        names = "、".join(sorted(role.value for role in extra_roles))
        violations.append(f"{parent.unit_id} 允许来源角色放宽：新增 {names}")
    if (
        disclosure_maturity_rank(child.minimum_disclosure_maturity)
        < disclosure_maturity_rank(parent.minimum_disclosure_maturity)
    ):
        violations.append(f"{parent.unit_id} 最低披露成熟度降低")
    extra_states = set(child.accepted_fact_states) - set(parent.accepted_fact_states)
    if extra_states:
        names = "、".join(sorted(state.value for state in extra_states))
        violations.append(f"{parent.unit_id} 可接受事实状态放宽：新增 {names}")
    extra_domains = set(child.allowed_fact_domains) - set(parent.allowed_fact_domains)
    if extra_domains:
        names = "、".join(sorted(domain.value for domain in extra_domains))
        violations.append(f"{parent.unit_id} 允许事实域放宽：新增 {names}")
    extra_kinds = set(child.allowed_observation_kinds) - set(
        parent.allowed_observation_kinds
    )
    if extra_kinds:
        names = "、".join(sorted(kind.value for kind in extra_kinds))
        violations.append(f"{parent.unit_id} 允许观察类型放宽：新增 {names}")
    if (
        parent.conflict_strategy is ConflictStrategy.RESOLVED_ONLY
        and child.conflict_strategy is not ConflictStrategy.RESOLVED_ONLY
    ):
        violations.append(f"{parent.unit_id} 可接受冲突处置放宽：允许保留开放冲突")
    if (
        parent.missing_strategy is MissingStrategy.BLOCK
        and child.missing_strategy is not MissingStrategy.BLOCK
    ):
        violations.append(f"{parent.unit_id} 缺失策略放松：阻断改为保留披露状态")
    removed_fields = set(parent.required_context_fields) - set(
        child.required_context_fields
    )
    if removed_fields:
        names = "、".join(sorted(field.value for field in removed_fields))
        violations.append(f"{parent.unit_id} 必需上下文字段减少：{names}")
    if child.object_type is not parent.object_type:
        violations.append(f"{parent.unit_id} 适用对象类型变化（无法证明为扩大）")
    if child.scope_parent is not parent.scope_parent:
        violations.append(f"{parent.unit_id} 父子对象范围变化（无法证明为扩大）")
    if not _applicability_is_widening(
        parent.applicability_predicate_id, child.applicability_predicate_id
    ):
        violations.append(f"{parent.unit_id} 适用性范围缩小")
    return tuple(violations)


def validate_spec_override(parent: GateSpec, child: GateSpec) -> tuple[str, ...]:
    """校验整份规格覆盖：单元只能增加，既有单元逐字段只收紧。"""
    violations: list[str] = []
    if child.report_kind is not parent.report_kind:
        violations.append("覆盖不得改变报告类型")
    parent_units = {unit.unit_id: unit for unit in parent.units}
    child_units = {unit.unit_id: unit for unit in child.units}
    for unit_id, parent_unit in parent_units.items():
        child_unit = child_units.get(unit_id)
        if child_unit is None:
            violations.append(f"删除证据门槛单元：{unit_id}")
            continue
        violations.extend(compare_unit_strictness(parent_unit, child_unit))
    return tuple(violations)


def compute_changed_unit_ids(parent: GateSpec, child: GateSpec) -> tuple[str, ...]:
    """变更单元 = 新增单元 ∪ 任一字段变化的既有单元 ∪ 被删除单元。"""
    parent_units = {unit.unit_id: unit for unit in parent.units}
    child_units = {unit.unit_id: unit for unit in child.units}
    changed: list[str] = []
    for unit_id in sorted(set(parent_units) | set(child_units)):
        if (
            unit_id not in parent_units
            or unit_id not in child_units
            or parent_units[unit_id] != child_units[unit_id]
        ):
            changed.append(unit_id)
    return tuple(changed)


def compute_affected_report_kinds(
    changed_unit_ids: Sequence[str],
    specs_by_report_kind: Mapping[ReportKind, GateSpec],
) -> tuple[ReportKind, ...]:
    """由变更单元到报告类型的反向依赖计算受影响报告集合。

    反向索引为 unit_id -> report_kind；同一单元标识不得映射到多个报告类型，
    未知变更单元必须失败关闭（调用方不得伪造依赖）。
    """
    reverse_index: dict[str, ReportKind] = {}
    for kind, spec in specs_by_report_kind.items():
        for unit in spec.units:
            existing = reverse_index.get(unit.unit_id)
            if existing is not None and existing is not kind:
                raise GateEvaluationError(
                    f"单元标识冲突，反向依赖不唯一：{unit.unit_id}"
                )
            reverse_index[unit.unit_id] = kind
    affected: set[ReportKind] = set()
    for unit_id in changed_unit_ids:
        unit_kind = reverse_index.get(unit_id)
        if unit_kind is None:
            raise GateEvaluationError(f"变更单元不属于任何已知规格：{unit_id}")
        affected.add(unit_kind)
    return tuple(sorted(affected, key=lambda kind: kind.value))


def validate_override_declaration(
    override: GateOverride,
    *,
    specs_by_report_kind: Mapping[ReportKind, tuple[GateSpec, GateSpec]],
) -> tuple[str, ...]:
    """调用方声明必须与计算集合完全一致，否则失败关闭。

    每个报告类型对应 (父规格, 子规格)；受影响报告由变更单元到报告类型的
    反向依赖计算，依赖单元与受影响报告集合均不允许调用方伪造。
    """
    violations: list[str] = []
    changed: list[str] = []
    affected_kinds: set[ReportKind] = set()
    for kind, (parent, child) in specs_by_report_kind.items():
        if parent.report_kind is not kind or child.report_kind is not kind:
            violations.append(f"规格报告类型与映射键不一致：{kind.value}")
            continue
        if parent.version != override.base_spec_version:
            violations.append(
                f"{kind.value} 父规格版本与基础规则版本不一致："
                f"{parent.version} != {override.base_spec_version}"
            )
        if child.version != override.base_spec_version:
            violations.append(
                f"{kind.value} 子规格必须保持基础规则版本，覆盖只改变项目合同版本"
            )
        kind_changed = compute_changed_unit_ids(parent, child)
        violations.extend(validate_spec_override(parent, child))
        changed.extend(kind_changed)
        if kind_changed:
            affected_kinds.add(kind)
    if set(override.changed_unit_ids) != set(changed):
        violations.append("调用方声明依赖单元与计算变更单元不一致")
    computed_affected = tuple(sorted(affected_kinds, key=lambda kind: kind.value))
    if set(override.affected_report_kinds) != set(computed_affected):
        violations.append("调用方声明受影响报告集合与反向依赖计算不一致")
    return tuple(violations)


def recompute_report_result(
    parent_result: ReportGateResult | None,
    *,
    override: GateOverride,
    specs_by_report_kind: Mapping[ReportKind, tuple[GateSpec, GateSpec]],
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
) -> ReportGateResult:
    """父结果不可变：校验父合同存在、未被错误替换、证据快照一致后生成子结果。

    - 父合同不存在（parent_result 为 None）不得生成子结果。
    - 父结果被错误替换（合同版本、规则版本、结果键或规则指纹不一致）不得生成子结果。
    - 证据快照不一致（快照 ID 或适用对象集合摘要不同）不得生成子结果。
    - 父结果必须绑定产生它的规则内容指纹；同版本但内容不同的父规格失败关闭。
    - 覆盖必须通过只收紧偏序与声明一致性校验。
    - 子结果绑定子规格指纹，只追加新项目合同版本；父结果对象不被就地修改。
    """
    if parent_result is None:
        raise GateEvaluationError("父合同结果不存在，不得生成子结果")
    if parent_result.contract_version != override.parent_contract_version:
        raise GateEvaluationError(
            "父结果合同版本与覆盖父版本不一致（父合同已被错误替换）"
        )
    if parent_result.spec_version != override.base_spec_version:
        raise GateEvaluationError(
            "父结果规则版本与覆盖基础版本不一致（父合同已被错误替换）"
        )
    expected_parent_key = compute_gate_result_key(
        parent_result.report_kind,
        parent_result.evidence_snapshot_id,
        parent_result.spec_version,
        parent_result.contract_version,
        parent_result.universe_summary,
        spec_fingerprint=parent_result.spec_fingerprint,
    )
    if parent_result.result_key != expected_parent_key:
        raise GateEvaluationError("父结果键不一致，父结果不可信")
    if snapshot.evidence_snapshot_id != parent_result.evidence_snapshot_id:
        raise GateEvaluationError(
            "证据快照不一致：子结果必须基于与父结果相同的证据快照"
        )
    if snapshot.universe_summary != parent_result.universe_summary:
        raise GateEvaluationError(
            "适用对象集合摘要不一致：子结果必须基于相同的已闭合宇宙"
        )
    pair = specs_by_report_kind.get(parent_result.report_kind)
    if pair is None:
        raise GateEvaluationError(
            f"缺少 {parent_result.report_kind.value} 报告的父子规格"
        )
    parent_spec, child_spec = pair
    if child_spec.report_kind is not parent_result.report_kind:
        raise GateEvaluationError("子规格报告类型与父结果不一致")
    # 父结果必须由传入父规格的规则内容产生；同版本但内容不同的父规格
    # （相同 spec_id/version、不同单元或阈值）不得重算该结果（P0-5）。
    if parent_spec.spec_fingerprint != parent_result.spec_fingerprint:
        raise GateEvaluationError(
            "父规格规则指纹与父结果不一致（父合同已被错误替换），不得生成子结果"
        )
    violations = validate_spec_override(parent_spec, child_spec)
    if violations:
        raise GateEvaluationError(
            "覆盖未通过只收紧偏序校验：" + "；".join(violations)
        )
    declaration_violations = validate_override_declaration(
        override, specs_by_report_kind=specs_by_report_kind
    )
    if declaration_violations:
        raise GateEvaluationError(
            "覆盖声明与计算不一致：" + "；".join(declaration_violations)
        )
    return evaluate_report(
        child_spec,
        snapshot,
        bindings,
        contract_version=override.child_contract_version,
    )
