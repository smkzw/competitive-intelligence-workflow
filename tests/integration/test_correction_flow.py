"""Task 9.1 修订流程集成测试：合法迁移、批准分离、发布前置条件、追加历史与幂等。

修订控制图定义（``graph/definitions/correction.py``）把五类服务操作绑定到
v1.2 冻结修订迁移边；本文件用真实 ``GraphExecutor`` + ``EventStore`` 验证：

- 八条已声明迁移边全部经真实执行器接受，且与字面 fixture 逐边一致；
- `submitted` 可进入需补证据、拒绝或等待用户批准，补证据后回到提交状态；
- 验证动作不能写入批准：只有报告所有者显式决定可进入 `approved`；
- 发布前置条件（新快照、受影响产物重建、独立质控、批准 ID）缺一失败关闭；
- 事件流只追加：补证回环与拒绝不覆盖历史；
- 同一请求精确重放无新事件、漂移载荷冲突；批准 ID 幂等去重批准副作用。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ci_workflow.domain.ids import stable_id
from ci_workflow.graph.definitions.correction import (
    CORRECTION_TRANSITION_BINDINGS,
    INITIAL_STATE,
    INITIAL_STATE_OPERATIONS,
    OPERATION_ADD_EVIDENCE,
    OPERATION_PUBLISH,
    OPERATION_RECORD_OWNER_DECISION,
    OPERATION_SUBMIT,
    OPERATION_VALIDATE,
    CorrectionTransitionBinding,
    binding_for,
    bindings_for_operation,
    guard_spec_for,
)
from ci_workflow.graph.executor import (
    GraphExecutor,
    IdempotentSideEffects,
    SideEffectConflictError,
)
from ci_workflow.graph.types import TransitionRequest
from ci_workflow.storage.event_store import (
    EventConflictError,
    EventStore,
    StoredWorkflowEvent,
    WorkflowEvent,
)
from tests.graph.test_transition_matrix import (
    GT05_REVISION_FIXTURE,
    GT05_VALID_EVIDENCE,
    LiteralEdge,
)

_NOW = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)
_PROJECT_ID = "p_correction"
_RUN_ID = "run_correction"

# 触发器 → 执行身份：验证由 Agent 完成，决定必须来自报告所有者
_ACTOR_BY_TRIGGER: dict[str, str] = {
    "validation_needs_evidence": "agent_validator",
    "validation_rejected": "agent_validator",
    "validation_passed": "agent_validator",
    "new_evidence_appended": "contributor",
    "owner_explicit_approval": "report_owner",
    "owner_explicit_rejection": "report_owner",
    "owner_requests_evidence": "report_owner",
    "publish_after_rebuild_qc": "correction_service",
}


def _request(
    *,
    request_id: str,
    object_id: str,
    from_state: str | None,
    to_state: str,
    trigger: str,
    evidence: dict[str, object],
    actor_id: str | None = None,
) -> TransitionRequest:
    return TransitionRequest(
        schema_version="1.0",
        request_id=request_id,
        project_id=_PROJECT_ID,
        run_id=_RUN_ID,
        family="revision_approval",
        object_id=object_id,
        from_state=from_state,
        to_state=to_state,
        trigger=trigger,
        evidence=evidence,
        actor_id=actor_id or _ACTOR_BY_TRIGGER[trigger],
        occurred_at=_NOW,
    )


def _evidence(guard_id: str, **overrides: object) -> dict[str, object]:
    """字面守卫证据 fixture：与 GT05 冻结证据一致，可按需覆盖字段。"""
    evidence: dict[str, object] = dict(GT05_VALID_EVIDENCE[guard_id])
    evidence.update(overrides)
    return evidence


def _binding_edge(binding: CorrectionTransitionBinding) -> tuple[str, str, str, str]:
    return (binding.from_state, binding.to_state, binding.trigger, binding.guard_id)


def _position_path(target: str) -> tuple[LiteralEdge, ...]:
    """在字面修订迁移 fixture 内从起始状态 BFS 到目标源状态的声明路径。"""
    frontier: list[tuple[str, tuple[LiteralEdge, ...]]] = [(INITIAL_STATE, ())]
    seen: set[str] = {INITIAL_STATE}
    while frontier:
        current, path = frontier.pop(0)
        if current == target:
            return path
        for edge in GT05_REVISION_FIXTURE:
            if edge.from_state == current and edge.to_state not in seen:
                seen.add(edge.to_state)
                frontier.append((edge.to_state, (*path, edge)))
    raise AssertionError(f"字面修订迁移中不存在到 {target} 的声明路径")


def _position(executor: GraphExecutor, object_id: str, target: str) -> None:
    """经声明迁移把新建议定位到目标源状态；每步都必须被接受。"""
    for edge in _position_path(target):
        assert edge.from_state is not None
        event = executor.submit(
            _request(
                request_id=f"position:{object_id}:{edge.from_state}->{edge.to_state}",
                object_id=object_id,
                from_state=edge.from_state,
                to_state=edge.to_state,
                trigger=edge.trigger,
                evidence=_evidence(edge.guard_id),
            )
        )
        assert event.event_type == "graph.transition.accepted", (object_id, target, edge)


def _canonical_state(executor: GraphExecutor, object_id: str) -> str:
    current = executor.state()["revision_approval"].get(object_id)
    return INITIAL_STATE if current is None else str(current)


def _stream_fingerprint(store: EventStore) -> list[tuple[int, str]]:
    return [(event.sequence, event.event_digest) for event in store.read_all()]


def _read_jsonl(path: Path) -> list[dict[str, str]]:
    return [
        {key: str(value) for key, value in json.loads(line).items()}
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_correction_bindings_exactly_cover_frozen_revision_edges() -> None:
    """操作绑定与 v1.2 字面修订迁移逐边一致；守卫规则只引用不复制。"""
    literal = {
        (edge.from_state, edge.to_state): (edge.trigger, edge.guard_id)
        for edge in GT05_REVISION_FIXTURE
    }
    bound = {
        (binding.from_state, binding.to_state): (binding.trigger, binding.guard_id)
        for binding in CORRECTION_TRANSITION_BINDINGS
    }
    assert len(CORRECTION_TRANSITION_BINDINGS) == len(GT05_REVISION_FIXTURE) == 8
    assert bound == literal
    # 每条绑定的守卫即冻结注册表中的同一声明（引用而非复制状态规则）
    for binding in CORRECTION_TRANSITION_BINDINGS:
        spec = guard_spec_for(binding)
        assert spec.guard_id == binding.guard_id
        assert binding_for(binding.operation, binding.disposition) is binding
    # 提交只是建立类型化起始状态 submitted，不绑定迁移边
    assert INITIAL_STATE == "submitted"
    assert OPERATION_SUBMIT in INITIAL_STATE_OPERATIONS
    assert len(INITIAL_STATE_OPERATIONS) == 1
    assert bindings_for_operation(OPERATION_SUBMIT) == ()
    # 验证通过与所有者批准使用不同守卫：验证本身不能批准
    validation_pass = binding_for(OPERATION_VALIDATE, "validation_passed")
    approve = binding_for(OPERATION_RECORD_OWNER_DECISION, "decision_approve")
    assert validation_pass.guard_id != approve.guard_id
    # 发布前置条件由复用守卫声明：三项前置真键 + 批准 ID
    publish = binding_for(OPERATION_PUBLISH, "publish")
    publish_spec = guard_spec_for(publish)
    assert publish_spec.required_true == (
        "new_snapshot_built",
        "affected_artifacts_rebuilt",
        "independent_qc_passed",
    )
    assert publish_spec.required_fields == ("approval_id",)


def test_full_correction_lifecycle_through_all_legal_transitions(tmp_path: Path) -> None:
    """八条合法迁移全部经真实执行器接受；六种状态逐一到达且状态归约正确。"""
    executor = GraphExecutor(tmp_path / "项目", run_id=_RUN_ID)

    # 建议甲：提交 → 需补证据 → 补证回提交 → 验证通过 → 所有者批准 → 发布
    proposal_a = "rev_proposal_a"
    assert _canonical_state(executor, proposal_a) == "submitted"
    steps_a = (
        (OPERATION_VALIDATE, "needs_more_evidence"),
        (OPERATION_ADD_EVIDENCE, "evidence_appended"),
        (OPERATION_VALIDATE, "validation_passed"),
        (OPERATION_RECORD_OWNER_DECISION, "decision_approve"),
        (OPERATION_PUBLISH, "publish"),
    )
    for index, (operation, disposition) in enumerate(steps_a):
        binding = binding_for(operation, disposition)
        event = executor.submit(
            _request(
                request_id=f"proposal_a:{index}",
                object_id=proposal_a,
                from_state=binding.from_state,
                to_state=binding.to_state,
                trigger=binding.trigger,
                evidence=_evidence(binding.guard_id),
            )
        )
        assert event.event_type == "graph.transition.accepted", (operation, disposition)
        assert event.payload["trigger"] == binding.trigger
        assert event.payload["guard_id"] == binding.guard_id
        assert event.actor_id == _ACTOR_BY_TRIGGER[binding.trigger]
    assert _canonical_state(executor, proposal_a) == "published"

    # 建议乙：验证通过 → 所有者要求补证据 → 补证回提交 → 验证拒绝
    proposal_b = "rev_proposal_b"
    steps_b = (
        (OPERATION_VALIDATE, "validation_passed"),
        (OPERATION_RECORD_OWNER_DECISION, "decision_needs_evidence"),
        (OPERATION_ADD_EVIDENCE, "evidence_appended"),
        (OPERATION_VALIDATE, "validation_rejected"),
    )
    for index, (operation, disposition) in enumerate(steps_b):
        binding = binding_for(operation, disposition)
        event = executor.submit(
            _request(
                request_id=f"proposal_b:{index}",
                object_id=proposal_b,
                from_state=binding.from_state,
                to_state=binding.to_state,
                trigger=binding.trigger,
                evidence=_evidence(binding.guard_id),
            )
        )
        assert event.event_type == "graph.transition.accepted", (operation, disposition)
    assert _canonical_state(executor, proposal_b) == "rejected"

    # 建议丙：验证通过 → 所有者显式拒绝
    proposal_c = "rev_proposal_c"
    steps_c = (
        (OPERATION_VALIDATE, "validation_passed"),
        (OPERATION_RECORD_OWNER_DECISION, "decision_reject"),
    )
    for index, (operation, disposition) in enumerate(steps_c):
        binding = binding_for(operation, disposition)
        event = executor.submit(
            _request(
                request_id=f"proposal_c:{index}",
                object_id=proposal_c,
                from_state=binding.from_state,
                to_state=binding.to_state,
                trigger=binding.trigger,
                evidence=_evidence(binding.guard_id),
            )
        )
        assert event.event_type == "graph.transition.accepted", (operation, disposition)
    assert _canonical_state(executor, proposal_c) == "rejected"

    # 三条建议合计覆盖全部八条声明边，不多不少
    accepted_edges = {
        (event.payload["from_state"], event.payload["to_state"])
        for event in executor.store.read_all()
        if event.event_type == "graph.transition.accepted"
    }
    assert accepted_edges == {
        (binding.from_state, binding.to_state) for binding in CORRECTION_TRANSITION_BINDINGS
    }


def test_validation_cannot_approve_without_owner_decision(tmp_path: Path) -> None:
    """验证证据不能驱动批准边；只有报告所有者显式决定可进入 approved。"""
    executor = GraphExecutor(tmp_path / "项目", run_id=_RUN_ID)
    proposal = "rev_probe_approval"
    _position(executor, proposal, "validated_pending_user_approval")
    approve = binding_for(OPERATION_RECORD_OWNER_DECISION, "decision_approve")

    def probe_approval(
        request_id: str, evidence: dict[str, object], actor_id: str
    ) -> StoredWorkflowEvent:
        return executor.submit(
            _request(
                request_id=request_id,
                object_id=proposal,
                from_state=approve.from_state,
                to_state=approve.to_state,
                trigger=approve.trigger,
                evidence=evidence,
                actor_id=actor_id,
            )
        )

    # 验证通过证据缺所有者显式决定 → 拒绝，状态不变
    validation_only: dict[str, object] = {
        "validation_complete": True,
        "validation_passed": True,
        "disposition_reason_saved": True,
    }
    event = probe_approval("probe:validation_only", validation_only, "agent_validator")
    assert event.event_type == "graph.transition.rejected"
    assert event.payload["reason"] == "guard_failed"
    assert event.payload["guard_reason"].startswith("missing_evidence:owner_explicit_decision")
    assert _canonical_state(executor, proposal) == "validated_pending_user_approval"

    # 只有 owner_explicit_decision 而未给出批准方向 → 拒绝
    event = probe_approval(
        "probe:no_direction",
        {"owner_explicit_decision": True},
        "report_owner",
    )
    assert event.event_type == "graph.transition.rejected"
    assert event.payload["guard_reason"] == "missing_evidence:decision_approve"

    # 批准与其他决定并存（矛盾证据）→ 拒绝
    event = probe_approval(
        "probe:contradictory",
        {
            "owner_explicit_decision": True,
            "decision_approve": True,
            "decision_reject": True,
        },
        "report_owner",
    )
    assert event.event_type == "graph.transition.rejected"
    assert "contradictory_evidence" in event.payload["guard_reason"]
    assert _canonical_state(executor, proposal) == "validated_pending_user_approval"

    # 未声明的直达批准：submitted / needs_evidence → approved 一律失败关闭
    for from_state in ("submitted", "needs_evidence"):
        probe_id = f"rev_direct_{from_state}"
        if from_state == "needs_evidence":
            _position(executor, probe_id, "needs_evidence")
        event = executor.submit(
            _request(
                request_id=f"probe:direct:{from_state}",
                object_id=probe_id,
                from_state=from_state,
                to_state="approved",
                trigger=approve.trigger,
                evidence=_evidence(approve.guard_id),
            )
        )
        assert event.event_type == "graph.transition.rejected", from_state
        assert event.payload["reason"] == "undeclared_transition", from_state


def test_publish_prerequisites_fail_closed(tmp_path: Path) -> None:
    """发布前置条件缺一失败关闭：新快照、受影响产物重建、独立质控、批准 ID。"""
    executor = GraphExecutor(tmp_path / "项目", run_id=_RUN_ID)
    proposal = "rev_probe_publish"
    _position(executor, proposal, "approved")
    publish = binding_for(OPERATION_PUBLISH, "publish")
    base = _evidence(publish.guard_id)

    def publish_attempt(request_id: str, evidence: dict[str, object]) -> StoredWorkflowEvent:
        return executor.submit(
            _request(
                request_id=request_id,
                object_id=proposal,
                from_state=publish.from_state,
                to_state=publish.to_state,
                trigger=publish.trigger,
                evidence=evidence,
            )
        )

    # 三项前置条件任缺其一 → 拒绝且状态保持 approved
    for missing in ("new_snapshot_built", "affected_artifacts_rebuilt", "independent_qc_passed"):
        event = publish_attempt(
            f"publish:missing:{missing}",
            {key: value for key, value in base.items() if key != missing},
        )
        assert event.event_type == "graph.transition.rejected", missing
        assert event.payload["reason"] == "guard_failed"
        assert event.payload["guard_reason"] == f"missing_evidence:{missing}"
    # 前置条件显式为 False 同样拒绝
    event = publish_attempt(
        "publish:snapshot_false",
        {**base, "new_snapshot_built": False},
    )
    assert event.event_type == "graph.transition.rejected"
    assert event.payload["guard_reason"] == "guard_not_satisfied:new_snapshot_built"
    # 批准 ID 缺失 → 拒绝（发布以批准 ID 幂等，无身份不得发布）
    event = publish_attempt(
        "publish:no_approval_id",
        {key: value for key, value in base.items() if key != "approval_id"},
    )
    assert event.event_type == "graph.transition.rejected"
    assert event.payload["guard_reason"] == "missing_evidence:approval_id"
    assert _canonical_state(executor, proposal) == "approved"

    # validated_pending_user_approval 直达发布未声明：必须先经所有者批准
    pending = "rev_probe_pending"
    _position(executor, pending, "validated_pending_user_approval")
    event = executor.submit(
        _request(
            request_id="publish:from_pending",
            object_id=pending,
            from_state="validated_pending_user_approval",
            to_state="published",
            trigger=publish.trigger,
            evidence=base,
        )
    )
    assert event.event_type == "graph.transition.rejected"
    assert event.payload["reason"] == "undeclared_transition"

    # 全部前置条件满足 → 接受发布；published 为终态，任何再迁移未声明
    event = publish_attempt("publish:complete", base)
    assert event.event_type == "graph.transition.accepted"
    assert event.payload["guard_evidence"]["approval_id"] == "rev_001"
    assert _canonical_state(executor, proposal) == "published"
    event = executor.submit(
        _request(
            request_id="publish:terminal_probe",
            object_id=proposal,
            from_state="published",
            to_state="published",
            trigger=publish.trigger,
            evidence=base,
        )
    )
    assert event.event_type == "graph.transition.rejected"
    assert event.payload["reason"] == "undeclared_transition"


def test_append_only_history_preserved_across_evidence_cycles(tmp_path: Path) -> None:
    """补证回环与所有者要求补证据只追加事件；拒绝保留记录且不可复活。"""
    executor = GraphExecutor(tmp_path / "项目", run_id=_RUN_ID)
    proposal = "rev_proposal_history"
    seen = _stream_fingerprint(executor.store)
    cycle = (
        (OPERATION_VALIDATE, "needs_more_evidence"),
        (OPERATION_ADD_EVIDENCE, "evidence_appended"),
        (OPERATION_VALIDATE, "validation_passed"),
        (OPERATION_RECORD_OWNER_DECISION, "decision_needs_evidence"),
        (OPERATION_ADD_EVIDENCE, "evidence_appended"),
    )
    for index, (operation, disposition) in enumerate(cycle):
        binding = binding_for(operation, disposition)
        event = executor.submit(
            _request(
                request_id=f"history:{index}",
                object_id=proposal,
                from_state=binding.from_state,
                to_state=binding.to_state,
                trigger=binding.trigger,
                evidence=_evidence(binding.guard_id),
            )
        )
        assert event.event_type == "graph.transition.accepted", (operation, disposition)
        fingerprint = _stream_fingerprint(executor.store)
        # 只追加：此前全部事件（含第一次补证回环）原样保留
        assert fingerprint[: len(seen)] == seen
        assert len(fingerprint) > len(seen)
        seen = fingerprint
    assert _canonical_state(executor, proposal) == "submitted"

    # 验证拒绝：拒绝事件与全部历史保留，rejected 不可被补证复活
    rejected_binding = binding_for(OPERATION_VALIDATE, "validation_rejected")
    event = executor.submit(
        _request(
            request_id="history:reject",
            object_id=proposal,
            from_state=rejected_binding.from_state,
            to_state=rejected_binding.to_state,
            trigger=rejected_binding.trigger,
            evidence=_evidence(rejected_binding.guard_id),
        )
    )
    assert event.event_type == "graph.transition.accepted"
    assert _canonical_state(executor, proposal) == "rejected"
    before = _stream_fingerprint(executor.store)
    add_evidence = binding_for(OPERATION_ADD_EVIDENCE, "evidence_appended")
    event = executor.submit(
        _request(
            request_id="history:revive",
            object_id=proposal,
            from_state="rejected",
            to_state=add_evidence.to_state,
            trigger=add_evidence.trigger,
            evidence=_evidence(add_evidence.guard_id),
        )
    )
    assert event.event_type == "graph.transition.rejected"
    assert event.payload["reason"] == "undeclared_transition"
    assert _stream_fingerprint(executor.store)[: len(before)] == before
    # 历史事件仍然完整可读：两轮补证回环与拒绝事件全部在案
    triggers = [
        event.payload["trigger"]
        for event in executor.store.read_all()
        if event.event_type == "graph.transition.accepted"
    ]
    assert triggers.count("new_evidence_appended") == 2
    assert triggers.count("validation_rejected") == 1


def test_idempotent_replay_and_approval_keyed_publish(tmp_path: Path) -> None:
    """精确重放无新事件、漂移载荷冲突；批准副作用以批准 ID 幂等去重。"""
    executor = GraphExecutor(tmp_path / "项目", run_id=_RUN_ID)
    proposal = "rev_proposal_idem"
    _position(executor, proposal, "approved")
    publish = binding_for(OPERATION_PUBLISH, "publish")

    publish_request = _request(
        request_id=f"{proposal}:publish",
        object_id=proposal,
        from_state=publish.from_state,
        to_state=publish.to_state,
        trigger=publish.trigger,
        evidence=_evidence(publish.guard_id),
    )
    first = executor.submit(publish_request)
    assert first.event_type == "graph.transition.accepted"
    total = len(executor.store.read_all())

    # 精确重放同一发布请求：返回既有事件，不追加任何新事件
    replay = executor.submit(publish_request)
    assert replay == first
    assert replay.sequence == first.sequence
    assert len(executor.store.read_all()) == total

    # 同一请求身份、不同载荷 → 失败关闭冲突
    drifted = publish_request.model_copy(update={"trigger": "drifted"})
    with pytest.raises(EventConflictError):
        executor.submit(drifted)
    assert len(executor.store.read_all()) == total

    # 批准 ID 幂等：revision.approve 副作用按批准 ID 去重，重放不重复登记
    approval_id = "rev_001"
    approve_event = WorkflowEvent(
        schema_version="1.0",
        event_id=stable_id("correction-approval", _PROJECT_ID, _RUN_ID, approval_id),
        project_id=_PROJECT_ID,
        run_id=_RUN_ID,
        event_type="revision.approve",
        occurred_at=_NOW,
        actor_id="report_owner",
        idempotency_key=f"revision.approve:{approval_id}",
        payload={
            "approval_id": approval_id,
            "decision": "approved",
            "approver": "report_owner",
        },
    )
    executor.store.append(approve_event)
    executor.replay()
    approvals_path = executor.project_root / "state" / "approvals.jsonl"
    assert [record["approval_id"] for record in _read_jsonl(approvals_path)] == [approval_id]

    stored = next(
        event for event in executor.store.read_all() if event.event_type == "revision.approve"
    )
    effects = IdempotentSideEffects(executor.project_root)
    effects(stored)
    assert len(_read_jsonl(approvals_path)) == 1

    # 同一批准 ID 的不同决定 → 冲突失败关闭，账本不追加
    conflicting = stored.model_copy(
        update={
            "idempotency_key": f"revision.approve:{approval_id}:second",
            "payload": {
                "approval_id": approval_id,
                "decision": "rejected",
                "approver": "report_owner",
            },
        }
    )
    with pytest.raises(SideEffectConflictError):
        effects(conflicting)
    assert len(_read_jsonl(approvals_path)) == 1

    # 规范状态中的副作用账本按批准 ID 记录批准操作
    ledger = executor.state()["side_effects"]
    assert ledger[approval_id]["op"] == "revision.approve"
