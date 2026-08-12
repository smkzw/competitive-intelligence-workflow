"""Task 3.4 规范事件归约器：图事件 → 规范状态（确定性、不原地改写）。"""

from __future__ import annotations

import hashlib
import json
from typing import Any, TypeGuard

from ci_workflow.domain.ids import stable_id
from ci_workflow.graph.definitions import node_contract
from ci_workflow.graph.registry import TRANSITION_REGISTRY
from ci_workflow.graph.state import (
    EVIDENCE_LEDGER_KEY,
    FAMILY_DEFAULT_STATES,
    RUNTIME_STATE_FAMILIES,
    SIDE_EFFECT_LEDGER_KEY,
    render_write_template,
)
from ci_workflow.graph.types import validate_typed_outputs
from ci_workflow.storage.event_store import StoredWorkflowEvent

_SIDE_EFFECT_EVENT_TYPES = frozenset(
    {"artifact.publish", "artifact.move", "revision.approve", "artifact.delete"}
)

# 本图拥有的事件类型：迁移、节点完成、四类声明副作用
GRAPH_EVENT_TYPES = frozenset(
    {
        "graph.transition.accepted",
        "graph.transition.rejected",
        "graph.node.completed",
        *_SIDE_EFFECT_EVENT_TYPES,
    }
)


def _merge_evidence_references(existing: list[Any], refs: Any) -> list[Any]:
    """共享证据账本按 fragment_id 去重合并；引用而非事实。"""
    known = {
        ref["fragment_id"]
        for ref in existing
        if isinstance(ref, dict) and ref.get("fragment_id")
    }
    merged = list(existing)
    if not isinstance(refs, list):
        return merged
    for ref in refs:
        if isinstance(ref, dict) and ref.get("fragment_id") not in known:
            merged.append(ref)
            if isinstance(ref.get("fragment_id"), str):
                known.add(ref["fragment_id"])
    return merged


def _apply_node_completed(state: dict[str, Any], event: StoredWorkflowEvent) -> dict[str, Any]:
    payload = event.payload
    contract = node_contract(str(payload["node_id"]))
    outputs = payload["outputs"]
    report_kind = payload.get("report_kind")
    result = dict(state)
    for write in contract.writes:
        if write == EVIDENCE_LEDGER_KEY:
            ledger = dict(result.get(EVIDENCE_LEDGER_KEY, {}))
            existing = list(ledger.get("evidence_references", []))
            ledger["evidence_references"] = _merge_evidence_references(
                existing, outputs.get("evidence_references", [])
            )
            result[EVIDENCE_LEDGER_KEY] = ledger
            continue
        if not isinstance(report_kind, str):
            raise ValueError(f"{contract.node_id} 的报告写键缺少 report_kind")
        key = render_write_template(write, report_kind)
        current = dict(result.get(key, {}))
        if contract.scope == "artifact":
            format_name = outputs.get("format")
            if not isinstance(format_name, str):
                raise ValueError(f"{contract.node_id} 缺少 format 输出")
            slot = dict(current.get(format_name, {}))
            slot.update(outputs)
            current[format_name] = slot
        else:
            current.update(outputs)
        result[key] = current
    return result


class SideEffectTargetError(ValueError):
    """副作用目标身份派生失败：字段缺失或类型错误，失败关闭而非 KeyError。"""


class GraphEventContractError(ValueError):
    """图事件载荷违反契约：伪造、错配或类型错误；失败关闭且不改写状态。"""


def _is_nonblank_str(value: object) -> TypeGuard[str]:
    return isinstance(value, str) and bool(value.strip())


def derive_side_effect_target(event_type: str, payload: dict[str, object]) -> str:
    """按操作类型派生幂等目标身份；归约器与副作用执行器共用同一规则。

    - ``revision.approve``：必须携带非空 ``approval_id``；
    - ``artifact.publish`` / ``artifact.move``：必须携带非空 ``target_identity``；
    - ``artifact.delete``：优先非空 ``target_identity``，否则非空 ``path``；
    - 字段缺失或类型错误一律以 :class:`SideEffectTargetError` 失败关闭。
    """
    if event_type == "revision.approve":
        approval_id = payload.get("approval_id")
        if not _is_nonblank_str(approval_id):
            raise SideEffectTargetError("revision.approve 需要非空 approval_id")
        return " ".join(approval_id.split())
    if event_type in ("artifact.publish", "artifact.move"):
        target = payload.get("target_identity")
        if not _is_nonblank_str(target):
            raise SideEffectTargetError(f"{event_type} 需要非空 target_identity")
        return " ".join(target.split())
    if event_type == "artifact.delete":
        target = payload.get("target_identity")
        if _is_nonblank_str(target):
            return " ".join(target.split())
        path = payload.get("path")
        if _is_nonblank_str(path):
            return " ".join(path.split())
        raise SideEffectTargetError("artifact.delete 需要非空 target_identity 或 path")
    raise SideEffectTargetError(f"未知副作用类型: {event_type}")


def _require_nonblank(event_label: str, event_id: str, field: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GraphEventContractError(
            f"{event_label} 事件 {event_id} 的 {field} 必须是非空字符串"
        )
    return " ".join(value.split())


def _canonical_json_bytes(value: object) -> bytes:
    """与 GraphExecutor.complete_node 完全一致的规范 JSON 序列化算法。"""
    try:
        return (
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise GraphEventContractError("图事件载荷必须是有限、可序列化的 JSON") from error


def _payload_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _validate_accepted_transition(
    state: dict[str, Any],
    event: StoredWorkflowEvent,
) -> None:
    """对 ``graph.transition.accepted`` 载荷做完整契约校验；任一失败不改写状态。

    校验顺序：封闭类型 → 运行族 → 状态值成员 → 声明边 → trigger/guard_id
    精确匹配 → 归约输入中的规范当前状态 → 守卫重求值放行。伪造、错配或类型
    错误的载荷一律以 :class:`GraphEventContractError` 失败关闭，因此直接向
    共享 EventStore 追加的伪造成交事件无法成为规范状态。

    注（注册表版本）：本任务把事件 ``schema_version=1.0`` 与当前注册表冻结为
    基线；将来若注册表版本变化，必须在事件中携带迁移契约版本，并由版本化
    注册表解析器选择对应迁移表后再变更本校验，不得靠削弱重放校验来兼容。
    """
    payload = event.payload
    event_id = event.event_id
    family = _require_nonblank(
        "graph.transition.accepted", event_id, "family", payload.get("family")
    )
    object_id = _require_nonblank(
        "graph.transition.accepted", event_id, "object_id", payload.get("object_id")
    )
    to_state = _require_nonblank(
        "graph.transition.accepted", event_id, "to_state", payload.get("to_state")
    )
    trigger = _require_nonblank(
        "graph.transition.accepted", event_id, "trigger", payload.get("trigger")
    )
    guard_id = _require_nonblank(
        "graph.transition.accepted", event_id, "guard_id", payload.get("guard_id")
    )
    _require_nonblank(
        "graph.transition.accepted", event_id, "request_digest", payload.get("request_digest")
    )
    raw_from = payload.get("from_state")
    if raw_from is not None and (not isinstance(raw_from, str) or not raw_from.strip()):
        raise GraphEventContractError(
            f"graph.transition.accepted 事件 {event_id} 的 from_state 必须是字符串或 None"
        )
    from_state: str | None = None if raw_from is None else " ".join(raw_from.split())
    guard_evidence = payload.get("guard_evidence")
    if not isinstance(guard_evidence, dict):
        raise GraphEventContractError(
            f"graph.transition.accepted 事件 {event_id} 的 guard_evidence 必须是字典"
        )
    if family not in RUNTIME_STATE_FAMILIES:
        raise GraphEventContractError(f"证据状态族不接受迁移事件: {family}")
    values = TRANSITION_REGISTRY.state_values(family)
    if to_state not in values:
        raise GraphEventContractError(f"{family} 不存在状态: {to_state}")
    if from_state is not None and from_state not in values:
        raise GraphEventContractError(f"{family} 不存在状态: {from_state}")
    edge = TRANSITION_REGISTRY.declared(family, from_state, to_state)
    if edge is None:
        raise GraphEventContractError(
            f"未声明迁移: {family}:{from_state} -> {to_state}"
        )
    if trigger != edge.trigger:
        raise GraphEventContractError(f"trigger 不匹配: {trigger} != {edge.trigger}")
    if guard_id != edge.guard_id:
        raise GraphEventContractError(f"guard_id 不匹配: {guard_id} != {edge.guard_id}")
    family_state = state.get(family, {})
    current = family_state.get(object_id)
    expected: str | None = FAMILY_DEFAULT_STATES[family] if current is None else str(current)
    if expected != from_state:
        raise GraphEventContractError(
            f"当前状态不匹配: expected={expected} got={from_state}"
        )
    guard = TRANSITION_REGISTRY.evaluate_guard(
        guard_id,
        guard_evidence,
        target_family=family,
        target_object_id=object_id,
    )
    if not guard.allowed:
        raise GraphEventContractError(f"守卫重求值拒绝: {guard_id}: {guard.reason}")


def _validate_node_completed(event: StoredWorkflowEvent) -> None:
    """对 ``graph.node.completed`` 载荷做完整契约校验；任一失败不改写状态。

    校验：封闭类型 → 声明合同作用域/报告类型 → 输出键集 → 完成谓词 →
    类型词表 → 完成摘要重算 → 事件 ID 重算 → 幂等键重算，与
    ``GraphExecutor.complete_node`` 的公共执行边界一致；伪造、错配或漂移的
    载荷无法通过归约进入规范状态。

    注（节点合同版本）：本任务把事件 schema_version=1.0 与当前节点合同冻结为
    基线；将来节点合同版本变化时，必须在事件中携带节点合同版本并由版本化
    解析器选择对应合同后再变更本校验，不得靠削弱重放校验来兼容。
    """
    payload = event.payload
    event_id = event.event_id
    node_id = _require_nonblank("graph.node.completed", event_id, "node_id", payload.get("node_id"))
    input_digest = _require_nonblank(
        "graph.node.completed", event_id, "input_digest", payload.get("input_digest")
    )
    _require_nonblank(
        "graph.node.completed", event_id, "completion_digest", payload.get("completion_digest")
    )
    outputs = payload.get("outputs")
    if not isinstance(outputs, dict):
        raise GraphEventContractError(
            f"graph.node.completed 事件 {event_id} 的 outputs 必须是字典"
        )
    report_kind = payload.get("report_kind")
    declared_scope = payload.get("scope")
    try:
        contract = node_contract(node_id)
    except ValueError as error:
        raise GraphEventContractError(f"未知图节点: {node_id}") from error
    if declared_scope != contract.scope:
        raise GraphEventContractError(f"scope 不匹配: {declared_scope} != {contract.scope}")
    if contract.scope in ("report", "artifact"):
        if report_kind not in ("A", "B", "C"):
            raise GraphEventContractError(f"{node_id} 需要报告类型 A/B/C")
    elif report_kind is not None:
        raise GraphEventContractError(f"{node_id} 是 shared 节点，不接受 report_kind")
    declared_names = {field.name for field in contract.typed_outputs}
    if set(outputs) != declared_names:
        raise GraphEventContractError(
            f"{node_id} 输出与声明不符: {sorted(set(outputs) ^ declared_names)}"
        )
    try:
        if not contract.completion_predicate(outputs):
            raise GraphEventContractError(f"{node_id} 输出未满足完成谓词（不完整或为空）")
        validate_typed_outputs(contract, outputs)
    except GraphEventContractError:
        raise
    except (TypeError, ValueError) as error:
        raise GraphEventContractError(f"{node_id} 输出类型不合法") from error
    expected_digest = _payload_digest(
        {
            "node_id": node_id,
            "report_kind": report_kind,
            "input_digest": input_digest,
            "outputs": outputs,
        }
    )
    if payload.get("completion_digest") != expected_digest:
        raise GraphEventContractError(f"completion_digest 不匹配: {event_id}")
    expected_event_id = stable_id(
        "graph-node-completed",
        event.project_id,
        event.run_id,
        node_id,
        report_kind or "shared",
        input_digest,
    )
    if event.event_id != expected_event_id:
        raise GraphEventContractError(
            f"事件 ID 不匹配: {event.event_id} != {expected_event_id}"
        )
    expected_key = (
        f"graph.node.completed:{event.project_id}:{event.run_id}:{node_id}:"
        f"{report_kind or 'shared'}:{input_digest}"
    )
    if event.idempotency_key != expected_key:
        raise GraphEventContractError(
            f"幂等键不匹配: {event.idempotency_key} != {expected_key}"
        )


def graph_reducer(state: dict[str, Any], event: StoredWorkflowEvent) -> dict[str, Any]:
    """把一条规范事件归约到状态的确定性副本（绝不原地改写输入状态）。

    非图拥有的业务事件（如 Task 3.1–3.3 的 download_request_state_changed）
    安全 no-op 并保留在事件流与检查点血统中；任何以 ``graph.`` 开头的未知
    事件类型失败关闭；``graph.transition.accepted`` 与 ``graph.node.completed``
    载荷在归约前做完整契约校验（类型、声明边/合同、trigger/guard_id 或
    完成摘要/事件 ID/幂等键、当前状态、守卫重求值），伪造事件无法成为规范状态。
    """
    if event.event_type.startswith("graph."):
        if event.event_type not in GRAPH_EVENT_TYPES:
            raise GraphEventContractError(f"未知图事件类型: {event.event_type}")
    elif event.event_type not in _SIDE_EFFECT_EVENT_TYPES:
        return dict(state)
    result = dict(state)
    if event.event_type == "graph.transition.accepted":
        _validate_accepted_transition(state, event)
        family = str(event.payload["family"])
        family_state = dict(result.get(family, {}))
        family_state[str(event.payload["object_id"])] = str(event.payload["to_state"])
        result[family] = family_state
    elif event.event_type == "graph.transition.rejected":
        pass  # 拒绝是可审计事件，不改写规范状态
    elif event.event_type == "graph.node.completed":
        _validate_node_completed(event)
        result = _apply_node_completed(result, event)
    else:
        # 四类声明副作用
        ledger = dict(result.get(SIDE_EFFECT_LEDGER_KEY, {}))
        ledger[derive_side_effect_target(event.event_type, event.payload)] = {
            "op": event.event_type,
            "idempotency_key": event.idempotency_key,
        }
        result[SIDE_EFFECT_LEDGER_KEY] = ledger
    return result
