"""Task 3.5 场景二：终态部分交付阻断与显式重新打开（唯一顶层节点）。

从场景一状态继续：C 与所有剩余选定对象均终态阻断且没有运行对象时，
项目从 partially_delivered 进入 partial_delivery_blocked；没有任何已交付
产物时相同终态只能到 blocked。静默 reconcile 不能离开两个 blocked 终态。
显式 reopen 只接受用户材料、环境/生成器修复或新合同版本；格式 blocked
只能经环境/生成器修复或新合同版本回 queued；旧阻断报告版本保持不可变，
恢复报告必须经显式重开 + 显式目标重绑使用新版本/新对象身份。

本文件同时覆盖 P1 修正的精确重现场景：

- 阻断进入代次：项目与格式各完成两个完整 block/reopen 周期，每个新阻断
  代次恰好一个被接受的 reopen，同代次重放不追加事件、原因漂移失败关闭；
- 新合同版本重开必须高于进入阻断态时的版本：v1 阻断后 v1 声称新版本被拒，
  v2 显式重开被接受；
- 目标重绑：错误类型 / 非阻断旧报告 / 复用既有对象 / 阻断期漂移全部失败
  关闭；合法重绑持久化且重放幂等，随后 conditions/reconcile 解析到新对象，
  旧对象在规范状态中保持 evidence_blocked 不可变；
- 重绑与选择绑定均为非图业务事件，归约器安全 no-op，不改写图状态。
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

_NOW = datetime(2026, 8, 13, 10, 30, tzinfo=UTC)
_PROJECT_ID = "p_35b"
_RUN_ID = "run_35b"


def _canonical_digest(value: object) -> str:
    encoded = (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
_PROJECT_OBJECT = "proj_1"


def _contract(contract_id: str = "contract_35b", version: int = 1) -> object:
    from ci_workflow.graph.recovery import DeliveryContract

    return DeliveryContract(
        contract_id=contract_id,
        contract_version=version,
        reports=("A", "B", "C"),
        optional_formats=("pptx",),
    )


def test_terminal_partial_delivery_requires_explicit_reopen_before_resume(
    tmp_path: Path,
) -> None:
    """GT35-2：部分交付阻断、无交付阻断、显式重开、目标重绑与版本证明。"""
    from ci_workflow.graph.executor import GraphExecutor
    from ci_workflow.graph.recovery import (
        ContractDriftError,
        CoordinationError,
        DeliveryContract,
        PartialDeliveryCoordinator,
        format_object_id,
    )
    from ci_workflow.graph.types import TransitionRequest
    from ci_workflow.storage.event_store import EventConflictError

    executor = GraphExecutor(tmp_path / "项目", run_id=_RUN_ID)
    coordinator = PartialDeliveryCoordinator(executor)
    contract = _contract()

    def submit(
        *,
        family: str,
        object_id: str,
        from_state: str | None,
        to_state: str,
        trigger: str,
        evidence: dict[str, object],
        request_id: str,
    ) -> None:
        if trigger == "isolated_qc_accepted":
            evidence = dict(evidence)
            evidence_without_auth = {
                k: v for k, v in evidence.items()
                if k != "qc_authorization_id"
            }
            evidence_digest = _canonical_digest(evidence_without_auth)
            from tests.graph._qc_authorization_fixture import (
                issue_test_qc_authorization,
            )

            auth_id = issue_test_qc_authorization(
                executor,
                report_object_id=object_id,
                from_state=str(from_state),
                to_state=to_state,
                verdict="accepted",
                evidence_digest=evidence_digest,
                actor_id="pi_35b",
                project_id=_PROJECT_ID,
                occurred_at=_NOW,
            )
            evidence["qc_authorization_id"] = auth_id
        event = executor.submit(
            TransitionRequest(
                schema_version="1.0",
                request_id=request_id,
                project_id=_PROJECT_ID,
                run_id=_RUN_ID,
                family=family,
                object_id=object_id,
                from_state=from_state,
                to_state=to_state,
                trigger=trigger,
                evidence=evidence,
                actor_id="pi_35b",
                occurred_at=_NOW,
            )
        )
        assert event.event_type == "graph.transition.accepted", event.payload

    # ── 阶段 1：与场景一相同的部分交付状态 ─────────────────────────────────
    submit(
        family="project", object_id=_PROJECT_OBJECT,
        from_state=None, to_state="running",
        trigger="project_contract_and_preflight",
        evidence={"project_contract_established": True, "preflight_records_established": True},
        request_id="35b:project:create",
    )
    a_path = (
        ("queued", "collecting", "candidate_scope_locked",
         {"candidate_scope_locked": True}, "35b:A:collecting"),
        ("collecting", "scientific_qc", "gate_deterministic_pass",
         {"gate_deterministic_pass": True, "candidate_snapshot_established": True},
         "35b:A:qc"),
        ("scientific_qc", "snapshot_locked", "isolated_qc_accepted",
         {"isolated_qc_accepted": True,
          "qc_verdict_id": "qc-verdict-1",
          "qc_verdict_digest": "a" * 64,
          "qc_candidate_snapshot_id": "snap-1",
          "qc_candidate_content_digest": "b" * 64,
          "qc_review_input_digest": "c" * 64,
          "qc_report_object_id": "report_A",
          "qc_context_digest": "d" * 64}, "35b:A:locked"),
    )
    for from_state, to_state, trigger, evidence, request_id in a_path:
        submit(
            family="report_evidence", object_id="report_A",
            from_state=from_state, to_state=to_state,
            trigger=trigger, evidence=evidence, request_id=request_id,
        )
    submit(
        family="report_evidence", object_id="report_B",
        from_state="queued", to_state="collecting",
        trigger="candidate_scope_locked",
        evidence={"candidate_scope_locked": True}, request_id="35b:B:collecting",
    )
    submit(
        family="report_evidence", object_id="report_B",
        from_state="collecting", to_state="evidence_blocked",
        trigger="recovery_exhausted_gap_remains",
        evidence={"critical_units_still_failing": True, "recovery_exhausted": True,
                  "independent_review_exhausted": True, "no_continuable_user_action": True},
        request_id="35b:B:blocked",
    )
    submit(
        family="report_evidence", object_id="report_C",
        from_state="queued", to_state="collecting",
        trigger="candidate_scope_locked",
        evidence={"candidate_scope_locked": True}, request_id="35b:C:collecting",
    )
    for fmt, request_prefix in (("html", "35b:A:html"), ("pptx", "35b:A:pptx")):
        submit(
            family="format_artifact", object_id=format_object_id("report_A", fmt),
            from_state="queued", to_state="generating",
            trigger="snapshot_locked_ready",
            evidence={"report_snapshot_locked": True},
            request_id=f"{request_prefix}:generating",
        )
    for request_id, to_state, trigger, evidence in (
        ("35b:A:html:quality_check", "quality_check", "artifact_built",
         {"artifact_built": True}),
        ("35b:A:html:passed", "passed", "acceptance_records_complete",
         {"deterministic_check_recorded": True, "coverage_check_recorded": True,
          "real_render_check_recorded": True}),
        ("35b:A:html:delivery_ready", "delivery_ready", "atomic_publish_manifest",
         {"atomic_publish_complete": True, "manifest_digest_recorded": True}),
    ):
        submit(
            family="format_artifact", object_id=format_object_id("report_A", "html"),
            from_state={
                "35b:A:html:quality_check": "generating",
                "35b:A:html:passed": "quality_check",
                "35b:A:html:delivery_ready": "passed",
            }[request_id],
            to_state=to_state, trigger=trigger, evidence=evidence, request_id=request_id,
        )
    submit(
        family="format_artifact", object_id=format_object_id("report_A", "pptx"),
        from_state="generating", to_state="blocked",
        trigger="format_recovery_exhausted",
        evidence={"format_recovery_exhausted": True, "failure_evidence_saved": True},
        request_id="35b:A:pptx:blocked",
    )
    first = coordinator.reconcile(contract, actor_id="pi_35b", occurred_at=_NOW)
    assert first.submitted is not None
    assert first.submitted.payload["to_state"] == "partially_delivered"
    assert executor.state()["project"][_PROJECT_OBJECT] == "partially_delivered"

    # ── 阶段 2：C 与全部剩余选定对象终态阻断、无运行对象 → 部分交付阻断 ──
    submit(
        family="report_evidence", object_id="report_C",
        from_state="collecting", to_state="evidence_blocked",
        trigger="recovery_exhausted_gap_remains",
        evidence={"critical_units_still_failing": True, "recovery_exhausted": True,
                  "independent_review_exhausted": True, "no_continuable_user_action": True},
        request_id="35b:C:blocked",
    )
    terminal = coordinator.reconcile(contract, actor_id="pi_35b", occurred_at=_NOW)
    assert terminal.submitted is not None
    assert terminal.submitted.event_type == "graph.transition.accepted"
    assert terminal.submitted.payload["to_state"] == "partial_delivery_blocked"
    state = executor.state()
    assert state["project"][_PROJECT_OBJECT] == "partial_delivery_blocked"
    conditions = terminal.conditions
    assert conditions.at_least_one_artifact_delivered is True
    assert conditions.remaining_selected_exhausted_blocked is True
    assert conditions.no_running_selected_object is True
    assert conditions.selected_objects_continuable is False
    assert conditions.continuable_targets == ()
    assert conditions.at_least_one_artifact_delivery_ready is True

    # 静默 reconcile 不能离开 partial_delivery_blocked
    total_before = len(executor.store.read_all())
    silent = coordinator.reconcile(contract, actor_id="pi_35b", occurred_at=_NOW)
    assert silent.submitted is None
    assert len(executor.store.read_all()) == total_before
    assert executor.state()["project"][_PROJECT_OBJECT] == "partial_delivery_blocked"

    # 同合同身份下放弃 PPTX：失败关闭
    drifted = DeliveryContract(
        contract_id="contract_35b",
        contract_version=1,
        reports=("A", "B", "C"),
        optional_formats=(),
    )
    with pytest.raises(ContractDriftError):
        coordinator.reconcile(drifted, actor_id="pi_35b", occurred_at=_NOW)

    # ── 阶段 3：格式显式重新打开（环境/生成器修复），阻断代次 1 ──────────
    reopened = coordinator.reopen_format(
        contract, report_kind="A", fmt="pptx",
        reason="environment_fixed", actor_id="pi_35b", occurred_at=_NOW,
    )
    assert reopened.submitted is not None
    assert reopened.submitted.event_type == "graph.transition.accepted"
    state = executor.state()
    assert state["format_artifact"][format_object_id("report_A", "pptx")] == "queued"
    assert state["format_artifact"][format_object_id("report_A", "html")] == "delivery_ready"

    # 重放同一重开动作：返回原事件，不追加
    total_before = len(executor.store.read_all())
    replay = coordinator.reopen_format(
        contract, report_kind="A", fmt="pptx",
        reason="environment_fixed", actor_id="pi_35b", occurred_at=_NOW,
    )
    assert replay.submitted is not None
    assert replay.submitted.event_type == "graph.transition.accepted"
    assert len(executor.store.read_all()) == total_before

    # 身份相同但原因漂移：失败关闭
    with pytest.raises(EventConflictError):
        coordinator.reopen_format(
            contract, report_kind="A", fmt="pptx",
            reason="generator_fixed", actor_id="pi_35b", occurred_at=_NOW,
        )
    # 用户材料不能重开格式
    with pytest.raises(CoordinationError):
        coordinator.reopen_format(
            contract, report_kind="A", fmt="pptx",
            reason="user_material_accepted", actor_id="pi_35b", occurred_at=_NOW,
        )
    # 未阻断对象的格式重开：拒绝并留审计事件（不静默通过）
    not_blocked = coordinator.reopen_format(
        contract, report_kind="B", fmt="pptx",
        reason="environment_fixed", actor_id="pi_35b", occurred_at=_NOW,
    )
    assert not_blocked.submitted is not None
    assert not_blocked.submitted.event_type == "graph.transition.rejected"
    assert not_blocked.submitted.payload["reason"] == "current_state_mismatch"

    # ── 阶段 4：项目显式重新打开（用户材料，代次 1）+ 目标重绑 ───────────
    reopened_project = coordinator.reopen_project(
        contract, reason="user_material_accepted",
        actor_id="pi_35b", occurred_at=_NOW,
    )
    assert reopened_project.submitted is not None
    assert reopened_project.submitted.event_type == "graph.transition.accepted"
    assert executor.state()["project"][_PROJECT_OBJECT] == "running"
    assert executor.state()["report_evidence"]["report_C"] == "evidence_blocked"

    # 重绑攻击：错误类型 / 非阻断旧报告 / 复用既有对象 → 全部失败关闭
    with pytest.raises(CoordinationError):
        coordinator.rebind_report(
            contract, kind="A", old_object_id="report_B", new_object_id="report_A_v9",
            reason="user_material_accepted", actor_id="pi_35b", occurred_at=_NOW,
        )
    with pytest.raises(CoordinationError):
        coordinator.rebind_report(
            contract, kind="A", old_object_id="report_A", new_object_id="report_A_v2",
            reason="user_material_accepted", actor_id="pi_35b", occurred_at=_NOW,
        )
    with pytest.raises(CoordinationError):
        coordinator.rebind_report(
            contract, kind="B", old_object_id="report_B", new_object_id="report_A",
            reason="user_material_accepted", actor_id="pi_35b", occurred_at=_NOW,
        )
    # 原因与已接受重开事件不匹配（没有任何环境修复重开）→ 失败关闭
    with pytest.raises(CoordinationError):
        coordinator.rebind_report(
            contract, kind="C", old_object_id="report_C", new_object_id="report_C_v2",
            reason="environment_fix_confirmed", actor_id="pi_35b", occurred_at=_NOW,
        )

    # 合法重绑：C 从不可变 report_C 推进到 report_C_v2，锚定重开事件
    rebind = coordinator.rebind_report(
        contract, kind="C", old_object_id="report_C", new_object_id="report_C_v2",
        reason="user_material_accepted", actor_id="pi_35b", occurred_at=_NOW,
    )
    assert rebind.submitted is not None
    assert rebind.submitted.event_type == "coordinator.report_target_bound"
    rebind_payload = rebind.submitted.payload
    assert rebind_payload["kind"] == "C"
    assert rebind_payload["old_object_id"] == "report_C"
    assert rebind_payload["new_object_id"] == "report_C_v2"
    assert rebind_payload["reason"] == "user_material_accepted"
    assert rebind_payload["contract_id"] == "contract_35b"
    assert rebind_payload["contract_version"] == 1
    assert rebind_payload["blocked_occurrence"] == 1
    # 重绑持久化具体重开事件身份与摘要
    assert rebind_payload["reopen_event_id"] == reopened_project.submitted.event_id
    assert (
        rebind_payload["reopen_event_digest"]
        == reopened_project.submitted.event_digest
    )
    # 重绑返回的条件已解析新目标（无需二次公开读取）
    rebind_target_ids = {t.report_object_id for t in rebind.conditions.target_matrix}
    assert "report_C_v2" in rebind_target_ids
    assert "report_C" not in rebind_target_ids

    # 重放同一重绑：no-op 不追加
    total_before = len(executor.store.read_all())
    rebind_replay = coordinator.rebind_report(
        contract, kind="C", old_object_id="report_C", new_object_id="report_C_v2",
        reason="user_material_accepted", actor_id="pi_35b", occurred_at=_NOW,
    )
    assert rebind_replay.submitted is None
    assert rebind_replay.note == "replay_noop"
    assert len(executor.store.read_all()) == total_before
    # 同身份原因漂移：失败关闭
    with pytest.raises(ContractDriftError):
        coordinator.rebind_report(
            contract, kind="C", old_object_id="report_C", new_object_id="report_C_v2",
            reason="environment_fix_confirmed", actor_id="pi_35b", occurred_at=_NOW,
        )

    # 重绑事件是非图业务事件：归约器安全 no-op
    from ci_workflow.graph.reducer import graph_reducer
    from ci_workflow.graph.state import initial_state

    rebind_events = [
        event for event in executor.store.read_all()
        if event.event_type == "coordinator.report_target_bound"
    ]
    assert len(rebind_events) == 1
    assert graph_reducer(initial_state(), rebind_events[0]) == initial_state()

    # conditions/reconcile 解析到当前目标 report_C_v2；旧 report_C 仍阻断
    conds = coordinator.conditions(contract)
    cond_report_ids = {t.report_object_id for t in conds.target_matrix}
    assert "report_C_v2" in cond_report_ids
    assert "report_C" not in cond_report_ids
    assert executor.state()["report_evidence"]["report_C"] == "evidence_blocked"
    # 恢复用新对象身份：report_C_v2 queued -> collecting
    submit(
        family="report_evidence", object_id="report_C_v2",
        from_state="queued", to_state="collecting",
        trigger="candidate_scope_locked",
        evidence={"candidate_scope_locked": True}, request_id="35b:C:v2:collecting",
    )
    state = executor.state()
    assert state["report_evidence"]["report_C"] == "evidence_blocked"
    assert state["report_evidence"]["report_C_v2"] == "collecting"
    # 不能把旧 evidence_blocked 原地改 queued（未声明迁移 → 拒绝审计事件）
    illegal_flip = executor.submit(
        TransitionRequest(
            schema_version="1.0",
            request_id="35b:C:illegal:flip",
            project_id=_PROJECT_ID,
            run_id=_RUN_ID,
            family="report_evidence",
            object_id="report_C",
            from_state="evidence_blocked",
            to_state="queued",
            trigger="environment_fixed_reopen",
            evidence={"environment_fixed": True},
            actor_id="pi_35b",
            occurred_at=_NOW,
        )
    )
    assert illegal_flip.event_type == "graph.transition.rejected"
    assert illegal_flip.payload["reason"] == "undeclared_transition"
    # 非法重开原因：失败关闭
    with pytest.raises(CoordinationError):
        coordinator.reopen_project(
            contract, reason="random_reason", actor_id="pi_35b", occurred_at=_NOW,
        )

    # ── 阶段 5：第二个完整 block/reopen 周期（阻断代次 2）─────────────────
    cycle2 = coordinator.reconcile(contract, actor_id="pi_35b", occurred_at=_NOW)
    assert cycle2.submitted is not None
    assert cycle2.submitted.payload["to_state"] == "partially_delivered"
    assert executor.state()["project"][_PROJECT_OBJECT] == "partially_delivered"
    # A:pptx 再次进入阻断（格式代次 2）
    submit(
        family="format_artifact", object_id=format_object_id("report_A", "pptx"),
        from_state="queued", to_state="generating",
        trigger="snapshot_locked_ready",
        evidence={"report_snapshot_locked": True}, request_id="35b:A:pptx:v2:generating",
    )
    submit(
        family="format_artifact", object_id=format_object_id("report_A", "pptx"),
        from_state="generating", to_state="blocked",
        trigger="format_recovery_exhausted",
        evidence={"format_recovery_exhausted": True, "failure_evidence_saved": True},
        request_id="35b:A:pptx:v2:blocked",
    )
    # C_v2 证据穷尽阻断
    submit(
        family="report_evidence", object_id="report_C_v2",
        from_state="collecting", to_state="evidence_blocked",
        trigger="recovery_exhausted_gap_remains",
        evidence={"critical_units_still_failing": True, "recovery_exhausted": True,
                  "independent_review_exhausted": True, "no_continuable_user_action": True},
        request_id="35b:C:v2:blocked",
    )
    terminal2 = coordinator.reconcile(contract, actor_id="pi_35b", occurred_at=_NOW)
    assert terminal2.submitted is not None
    assert terminal2.submitted.payload["to_state"] == "partial_delivery_blocked"
    assert executor.state()["project"][_PROJECT_OBJECT] == "partial_delivery_blocked"
    # 新阻断代次的重放 reconcile：不追加事件
    total_before = len(executor.store.read_all())
    terminal2_replay = coordinator.reconcile(contract, actor_id="pi_35b", occurred_at=_NOW)
    assert terminal2_replay.submitted is None
    assert len(executor.store.read_all()) == total_before

    # 项目重开代次 2：恰好一次被接受；重放不追加；原因漂移失败关闭
    reopen2 = coordinator.reopen_project(
        contract, reason="user_material_accepted",
        actor_id="pi_35b", occurred_at=_NOW,
    )
    assert reopen2.submitted is not None
    assert reopen2.submitted.event_type == "graph.transition.accepted"
    assert executor.state()["project"][_PROJECT_OBJECT] == "running"
    total_before = len(executor.store.read_all())
    reopen2_replay = coordinator.reopen_project(
        contract, reason="user_material_accepted",
        actor_id="pi_35b", occurred_at=_NOW,
    )
    assert reopen2_replay.submitted is not None
    assert reopen2_replay.submitted.event_type == "graph.transition.accepted"
    assert len(executor.store.read_all()) == total_before
    with pytest.raises(EventConflictError):
        coordinator.reopen_project(
            contract, reason="environment_fix_confirmed",
            actor_id="pi_35b", occurred_at=_NOW,
        )

    # 格式重开代次 2：恰好一次被接受；重放不追加；原因漂移失败关闭
    format_reopen2 = coordinator.reopen_format(
        contract, report_kind="A", fmt="pptx",
        reason="environment_fixed", actor_id="pi_35b", occurred_at=_NOW,
    )
    assert format_reopen2.submitted is not None
    assert format_reopen2.submitted.event_type == "graph.transition.accepted"
    assert executor.state()["format_artifact"][format_object_id("report_A", "pptx")] == "queued"
    total_before = len(executor.store.read_all())
    format_reopen2_replay = coordinator.reopen_format(
        contract, report_kind="A", fmt="pptx",
        reason="environment_fixed", actor_id="pi_35b", occurred_at=_NOW,
    )
    assert format_reopen2_replay.submitted is not None
    assert len(executor.store.read_all()) == total_before
    with pytest.raises(EventConflictError):
        coordinator.reopen_format(
            contract, report_kind="A", fmt="pptx",
            reason="generator_fixed", actor_id="pi_35b", occurred_at=_NOW,
        )

    # ── 阶段 6：没有任何已交付产物的终态阻断只能到 blocked ────────────────
    blocked_root = tmp_path / "项目_无交付"
    blocked_executor = GraphExecutor(blocked_root, run_id="run_35c")
    blocked_coordinator = PartialDeliveryCoordinator(blocked_executor)
    blocked_contract = _contract()

    def submit_blocked(
        *,
        family: str,
        object_id: str,
        from_state: str | None,
        to_state: str,
        trigger: str,
        evidence: dict[str, object],
        request_id: str,
    ) -> None:
        event = blocked_executor.submit(
            TransitionRequest(
                schema_version="1.0",
                request_id=request_id,
                project_id="p_35c",
                run_id="run_35c",
                family=family,
                object_id=object_id,
                from_state=from_state,
                to_state=to_state,
                trigger=trigger,
                evidence=evidence,
                actor_id="pi_35b",
                occurred_at=_NOW,
            )
        )
        assert event.event_type == "graph.transition.accepted", event.payload

    submit_blocked(
        family="project", object_id=_PROJECT_OBJECT,
        from_state=None, to_state="running",
        trigger="project_contract_and_preflight",
        evidence={"project_contract_established": True, "preflight_records_established": True},
        request_id="35c:project:create",
    )
    for kind in ("A", "B", "C"):
        submit_blocked(
            family="report_evidence", object_id=f"report_{kind}",
            from_state="queued", to_state="collecting",
            trigger="candidate_scope_locked",
            evidence={"candidate_scope_locked": True},
            request_id=f"35c:{kind}:collecting",
        )
        submit_blocked(
            family="report_evidence", object_id=f"report_{kind}",
            from_state="collecting", to_state="evidence_blocked",
            trigger="recovery_exhausted_gap_remains",
            evidence={"critical_units_still_failing": True, "recovery_exhausted": True,
                      "independent_review_exhausted": True, "no_continuable_user_action": True},
            request_id=f"35c:{kind}:blocked",
        )
    blocked_result = blocked_coordinator.reconcile(
        blocked_contract, actor_id="pi_35b", occurred_at=_NOW,
    )
    assert blocked_result.submitted is not None
    assert blocked_result.submitted.payload["to_state"] == "blocked"
    assert blocked_executor.state()["project"][_PROJECT_OBJECT] == "blocked"
    assert blocked_result.conditions.no_deliverable_artifact is True
    assert blocked_result.conditions.at_least_one_artifact_delivered is False
    assert blocked_result.conditions.at_least_one_terminal_blocked is True
    assert blocked_result.conditions.no_running_selected_object is True
    # 阻断期（未显式重开）目标漂移：失败关闭
    with pytest.raises(CoordinationError):
        blocked_coordinator.rebind_report(
            blocked_contract, kind="A", old_object_id="report_A",
            new_object_id="report_A_v2", reason="user_material_accepted",
            actor_id="pi_35b", occurred_at=_NOW,
        )
    # 静默 reconcile 不能离开 blocked
    total_before = len(blocked_executor.store.read_all())
    silent_blocked = blocked_coordinator.reconcile(
        blocked_contract, actor_id="pi_35b", occurred_at=_NOW,
    )
    assert silent_blocked.submitted is None
    assert len(blocked_executor.store.read_all()) == total_before
    assert blocked_executor.state()["project"][_PROJECT_OBJECT] == "blocked"
    # 环境修复显式重开
    env_reopen = blocked_coordinator.reopen_project(
        blocked_contract, reason="environment_fix_confirmed",
        actor_id="pi_35b", occurred_at=_NOW,
    )
    assert env_reopen.submitted is not None
    assert env_reopen.submitted.event_type == "graph.transition.accepted"
    assert blocked_executor.state()["project"][_PROJECT_OBJECT] == "running"
    # 合法重绑：A report_A → report_A_v2（env 重开、阻断代次 1）
    rebind_a = blocked_coordinator.rebind_report(
        blocked_contract, kind="A", old_object_id="report_A",
        new_object_id="report_A_v2", reason="environment_fix_confirmed",
        actor_id="pi_35b", occurred_at=_NOW,
    )
    assert rebind_a.submitted is not None
    assert rebind_a.submitted.event_type == "coordinator.report_target_bound"
    # A_v2 在重开之后再次阻断（新的阻断进入事件）
    submit_blocked(
        family="report_evidence", object_id="report_A_v2",
        from_state="queued", to_state="collecting",
        trigger="candidate_scope_locked",
        evidence={"candidate_scope_locked": True}, request_id="35c:A:v2:collecting",
    )
    submit_blocked(
        family="report_evidence", object_id="report_A_v2",
        from_state="collecting", to_state="evidence_blocked",
        trigger="recovery_exhausted_gap_remains",
        evidence={"critical_units_still_failing": True, "recovery_exhausted": True,
                  "independent_review_exhausted": True, "no_continuable_user_action": True},
        request_id="35c:A:v2:blocked",
    )
    # 陈旧重开攻击：env 重开先于 A_v2 阻断进入 → 失败关闭
    with pytest.raises(CoordinationError):
        blocked_coordinator.rebind_report(
            blocked_contract, kind="A", old_object_id="report_A_v2",
            new_object_id="report_A_v3", reason="environment_fix_confirmed",
            actor_id="pi_35b", occurred_at=_NOW,
        )

    # ── 阶段 6b：项目仍运行（B 阻断、C 可继续、无显式重开）→ 重绑失败关闭 ─
    running_root = tmp_path / "项目_仍运行"
    running_executor = GraphExecutor(running_root, run_id="run_35f")
    running_coordinator = PartialDeliveryCoordinator(running_executor)
    running_contract = _contract()

    def submit_running(
        *,
        family: str,
        object_id: str,
        from_state: str | None,
        to_state: str,
        trigger: str,
        evidence: dict[str, object],
        request_id: str,
    ) -> None:
        event = running_executor.submit(
            TransitionRequest(
                schema_version="1.0",
                request_id=request_id,
                project_id="p_35f",
                run_id="run_35f",
                family=family,
                object_id=object_id,
                from_state=from_state,
                to_state=to_state,
                trigger=trigger,
                evidence=evidence,
                actor_id="pi_35b",
                occurred_at=_NOW,
            )
        )
        assert event.event_type == "graph.transition.accepted", event.payload

    submit_running(
        family="project", object_id=_PROJECT_OBJECT,
        from_state=None, to_state="running",
        trigger="project_contract_and_preflight",
        evidence={"project_contract_established": True, "preflight_records_established": True},
        request_id="35f:project:create",
    )
    submit_running(
        family="report_evidence", object_id="report_B",
        from_state="queued", to_state="collecting",
        trigger="candidate_scope_locked",
        evidence={"candidate_scope_locked": True}, request_id="35f:B:collecting",
    )
    submit_running(
        family="report_evidence", object_id="report_B",
        from_state="collecting", to_state="evidence_blocked",
        trigger="recovery_exhausted_gap_remains",
        evidence={"critical_units_still_failing": True, "recovery_exhausted": True,
                  "independent_review_exhausted": True, "no_continuable_user_action": True},
        request_id="35f:B:blocked",
    )
    # C 仍可继续 → 项目保持 running（reconcile 无候选）
    submit_running(
        family="report_evidence", object_id="report_C",
        from_state="queued", to_state="collecting",
        trigger="candidate_scope_locked",
        evidence={"candidate_scope_locked": True}, request_id="35f:C:collecting",
    )
    still = running_coordinator.reconcile(
        running_contract, actor_id="pi_35b", occurred_at=_NOW,
    )
    assert still.submitted is None
    assert running_executor.state()["project"][_PROJECT_OBJECT] == "running"
    # 报告 B 已阻断但没有任何接受的项目重开事件 → 重绑失败关闭
    with pytest.raises(CoordinationError):
        running_coordinator.rebind_report(
            running_contract, kind="B", old_object_id="report_B",
            new_object_id="report_B_v2", reason="user_material_accepted",
            actor_id="pi_35b", occurred_at=_NOW,
        )

    # ── 阶段 7：新合同版本重开必须高于进入阻断时的版本 ────────────────────
    new_root = tmp_path / "项目_新合同"
    new_executor = GraphExecutor(new_root, run_id="run_35d")
    new_coordinator = PartialDeliveryCoordinator(new_executor)
    new_contract = _contract()

    def submit_new(
        *,
        family: str,
        object_id: str,
        from_state: str | None,
        to_state: str,
        trigger: str,
        evidence: dict[str, object],
        request_id: str,
    ) -> None:
        event = new_executor.submit(
            TransitionRequest(
                schema_version="1.0",
                request_id=request_id,
                project_id="p_35d",
                run_id="run_35d",
                family=family,
                object_id=object_id,
                from_state=from_state,
                to_state=to_state,
                trigger=trigger,
                evidence=evidence,
                actor_id="pi_35b",
                occurred_at=_NOW,
            )
        )
        assert event.event_type == "graph.transition.accepted", event.payload

    submit_new(
        family="project", object_id=_PROJECT_OBJECT,
        from_state=None, to_state="running",
        trigger="project_contract_and_preflight",
        evidence={"project_contract_established": True, "preflight_records_established": True},
        request_id="35d:project:create",
    )
    for kind in ("A", "B", "C"):
        submit_new(
            family="report_evidence", object_id=f"report_{kind}",
            from_state="queued", to_state="collecting",
            trigger="candidate_scope_locked",
            evidence={"candidate_scope_locked": True},
            request_id=f"35d:{kind}:collecting",
        )
        submit_new(
            family="report_evidence", object_id=f"report_{kind}",
            from_state="collecting", to_state="evidence_blocked",
            trigger="recovery_exhausted_gap_remains",
            evidence={"critical_units_still_failing": True, "recovery_exhausted": True,
                      "independent_review_exhausted": True, "no_continuable_user_action": True},
            request_id=f"35d:{kind}:blocked",
        )
    new_blocked = new_coordinator.reconcile(
        new_contract, actor_id="pi_35b", occurred_at=_NOW,
    )
    assert new_blocked.submitted is not None
    assert new_blocked.submitted.payload["to_state"] == "blocked"
    assert new_executor.state()["project"][_PROJECT_OBJECT] == "blocked"
    # v1 阻断后声称"新合同版本"：版本没有更高 → 失败关闭
    with pytest.raises(CoordinationError):
        new_coordinator.reopen_project(
            new_contract, reason="new_contract_version_reopens",
            actor_id="pi_35b", occurred_at=_NOW,
        )
    # 显式绑定并重开 v2：合法的新合同版本重开
    new_contract_v2 = _contract(version=2)
    contract_reopen = new_coordinator.reopen_project(
        new_contract_v2, reason="new_contract_version_reopens",
        actor_id="pi_35b", occurred_at=_NOW,
    )
    assert contract_reopen.submitted is not None
    assert contract_reopen.submitted.event_type == "graph.transition.accepted"
    assert new_executor.state()["project"][_PROJECT_OBJECT] == "running"
    # v2 选择绑定只记录一次；重开后 reconcile 同选择合法回到 blocked（代次 2）
    selection_bindings = [
        event for event in new_executor.store.read_all()
        if event.event_type == "coordinator.selection_bound"
    ]
    assert [binding.payload["contract_version"] for binding in selection_bindings] == [1, 2]
    reblocked = new_coordinator.reconcile(
        new_contract_v2, actor_id="pi_35b", occurred_at=_NOW,
    )
    assert reblocked.submitted is not None
    assert reblocked.submitted.payload["to_state"] == "blocked"
    assert new_executor.state()["project"][_PROJECT_OBJECT] == "blocked"

    # ── 阶段 8：伪造 report_target_bound 事件读路径失败关闭（独立项目根）──
    import hashlib
    import json

    from ci_workflow.domain.ids import stable_id
    from ci_workflow.graph.recovery import (
        REBIND_EVENT,
        CoordinatorEventContractError,
    )
    from ci_workflow.storage.event_store import WorkflowEvent

    def test_selection_digest(reports: list[str], formats: list[str]) -> str:
        encoded = (
            json.dumps(
                {
                    "contract_id": "contract_35h",
                    "contract_version": 1,
                    "reports": list(reports),
                    "optional_formats": list(formats),
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def fresh_rebind_root(
        name: str,
    ) -> tuple[GraphExecutor, PartialDeliveryCoordinator, DeliveryContract, object]:
        root = tmp_path / name
        root_executor = GraphExecutor(root, run_id="run_35h")
        root_coordinator = PartialDeliveryCoordinator(root_executor)
        root_contract = DeliveryContract(
            contract_id="contract_35h", contract_version=1,
            reports=("A", "B", "C"), optional_formats=("pptx",),
        )

        def submit_h(
            *,
            family: str,
            object_id: str,
            from_state: str | None,
            to_state: str,
            trigger: str,
            evidence: dict[str, object],
            request_id: str,
        ) -> None:
            event = root_executor.submit(
                TransitionRequest(
                    schema_version="1.0",
                    request_id=request_id,
                    project_id="p_35h",
                    run_id="run_35h",
                    family=family,
                    object_id=object_id,
                    from_state=from_state,
                    to_state=to_state,
                    trigger=trigger,
                    evidence=evidence,
                    actor_id="pi_35b",
                    occurred_at=_NOW,
                )
            )
            assert event.event_type == "graph.transition.accepted", event.payload

        submit_h(
            family="project", object_id=_PROJECT_OBJECT,
            from_state=None, to_state="running",
            trigger="project_contract_and_preflight",
            evidence={"project_contract_established": True,
                      "preflight_records_established": True},
            request_id="35h:project:create",
        )
        for kind in ("A", "B", "C"):
            submit_h(
                family="report_evidence", object_id=f"report_{kind}",
                from_state="queued", to_state="collecting",
                trigger="candidate_scope_locked",
                evidence={"candidate_scope_locked": True},
                request_id=f"35h:{kind}:collecting",
            )
            submit_h(
                family="report_evidence", object_id=f"report_{kind}",
                from_state="collecting", to_state="evidence_blocked",
                trigger="recovery_exhausted_gap_remains",
                evidence={"critical_units_still_failing": True,
                          "recovery_exhausted": True,
                          "independent_review_exhausted": True,
                          "no_continuable_user_action": True},
                request_id=f"35h:{kind}:blocked",
            )
        blocked = root_coordinator.reconcile(
            root_contract, actor_id="pi_35b", occurred_at=_NOW,
        )
        assert blocked.submitted is not None
        assert blocked.submitted.payload["to_state"] == "blocked"
        env_reopen = root_coordinator.reopen_project(
            root_contract, reason="environment_fix_confirmed",
            actor_id="pi_35b", occurred_at=_NOW,
        )
        assert env_reopen.submitted is not None
        assert env_reopen.submitted.event_type == "graph.transition.accepted"
        return root_executor, root_coordinator, root_contract, env_reopen.submitted

    def forged_rebind_event(
        *,
        kind: str,
        old: str,
        new: str,
        reason: str,
        reopen: object | None,
        occurrence: int = 1,
    ) -> WorkflowEvent:
        reopen_event_id = (
            reopen.event_id if reopen is not None else "reopen_fake_0000"
        )
        reopen_digest = (
            reopen.event_digest if reopen is not None else "0" * 64
        )
        payload = {
            "kind": kind,
            "old_object_id": old,
            "new_object_id": new,
            "reason": reason,
            "contract_id": "contract_35h",
            "contract_version": 1,
            "selection_digest": test_selection_digest(["A", "B", "C"], ["pptx"]),
            "reports": ["A", "B", "C"],
            "optional_formats": ["pptx"],
            "blocked_occurrence": occurrence,
            "reopen_event_id": reopen_event_id,
            "reopen_event_digest": reopen_digest,
        }
        return WorkflowEvent(
            schema_version="1.0",
            event_id=stable_id(
                "coordinator-rebind", "p_35h", "run_35h", "contract_35h", "1",
                kind, old, new, f"blocked:{occurrence}", reopen_event_id,
            ),
            project_id="p_35h",
            run_id="run_35h",
            event_type=REBIND_EVENT,
            occurred_at=_NOW,
            actor_id="forger",
            idempotency_key=(
                f"coordinator.rebind:run_35h:contract_35h:1:{kind}:{old}:{new}:"
                f"blocked:{occurrence}:{reopen_event_id}"
            ),
            payload=payload,
        )

    # 攻击 1：重开回执不存在
    ex1, co1, ct1, reopen1 = fresh_rebind_root("项目_伪造_无回执")
    ex1.store.append(
        forged_rebind_event(
            kind="B", old="report_B", new="report_B_v2",
            reason="environment_fix_confirmed", reopen=None,
        )
    )
    with pytest.raises(CoordinatorEventContractError):
        co1.conditions(ct1)

    # 攻击 2：重开回执原因与重绑原因不匹配
    ex2, co2, ct2, reopen2 = fresh_rebind_root("项目_伪造_原因不匹配")
    ex2.store.append(
        forged_rebind_event(
            kind="B", old="report_B", new="report_B_v2",
            reason="user_material_accepted", reopen=reopen2,
        )
    )
    with pytest.raises(CoordinatorEventContractError):
        co2.conditions(ct2)

    # 攻击 3：伪造重定向（新目标复用其他报告当前目标）
    ex3, co3, ct3, reopen3 = fresh_rebind_root("项目_伪造_重定向")
    ex3.store.append(
        forged_rebind_event(
            kind="B", old="report_B", new="report_A",
            reason="environment_fix_confirmed", reopen=reopen3,
        )
    )
    with pytest.raises(CoordinatorEventContractError):
        co3.conditions(ct3)

    # 攻击 4：重绑链断裂（合法重绑后旧目标不再是当前目标）
    ex4, co4, ct4, reopen4 = fresh_rebind_root("项目_伪造_链断裂")
    legal4 = co4.rebind_report(
        ct4, kind="B", old_object_id="report_B", new_object_id="report_B_v2",
        reason="environment_fix_confirmed", actor_id="pi_35b", occurred_at=_NOW,
    )
    assert legal4.submitted is not None
    ex4.store.append(
        forged_rebind_event(
            kind="B", old="report_B", new="report_B_v9",
            reason="environment_fix_confirmed", reopen=reopen4,
        )
    )
    with pytest.raises(CoordinatorEventContractError):
        co4.conditions(ct4)

    # 攻击 5：陈旧重开回执（重开先于新阻断进入）
    ex5, co5, ct5, reopen5 = fresh_rebind_root("项目_伪造_陈旧回执")
    legal5 = co5.rebind_report(
        ct5, kind="B", old_object_id="report_B", new_object_id="report_B_v2",
        reason="environment_fix_confirmed", actor_id="pi_35b", occurred_at=_NOW,
    )
    assert legal5.submitted is not None
    # B_v2 在重开之后阻断（新的阻断进入事件）
    for to_state, trigger, evidence, request_id in (
        ("collecting", "candidate_scope_locked",
         {"candidate_scope_locked": True}, "35h:B:v2:collecting"),
        ("evidence_blocked", "recovery_exhausted_gap_remains",
         {"critical_units_still_failing": True, "recovery_exhausted": True,
          "independent_review_exhausted": True, "no_continuable_user_action": True},
         "35h:B:v2:blocked"),
    ):
        from_state = "queued" if to_state == "collecting" else "collecting"
        event = ex5.submit(
            TransitionRequest(
                schema_version="1.0",
                request_id=request_id,
                project_id="p_35h",
                run_id="run_35h",
                family="report_evidence",
                object_id="report_B_v2",
                from_state=from_state,
                to_state=to_state,
                trigger=trigger,
                evidence=evidence,
                actor_id="pi_35b",
                occurred_at=_NOW,
            )
        )
        assert event.event_type == "graph.transition.accepted", event.payload
    ex5.store.append(
        forged_rebind_event(
            kind="B", old="report_B_v2", new="report_B_v3",
            reason="environment_fix_confirmed", reopen=reopen5,
        )
    )
    with pytest.raises(CoordinatorEventContractError):
        co5.conditions(ct5)

    # counter-case：合法重绑 + 重放不追加事件（独立根）
    ex6, co6, ct6, _ = fresh_rebind_root("项目_伪造_合法重放")
    first_rebind = co6.rebind_report(
        ct6, kind="B", old_object_id="report_B", new_object_id="report_B_v2",
        reason="environment_fix_confirmed", actor_id="pi_35b", occurred_at=_NOW,
    )
    assert first_rebind.submitted is not None
    before = len(ex6.store.read_all())
    replay_rebind = co6.rebind_report(
        ct6, kind="B", old_object_id="report_B", new_object_id="report_B_v2",
        reason="environment_fix_confirmed", actor_id="pi_35b", occurred_at=_NOW,
    )
    assert replay_rebind.submitted is None
    assert replay_rebind.note == "replay_noop"
    assert len(ex6.store.read_all()) == before

    # 攻击 6：目标身份未规范化（尾随/内部重复空白）→ 在规范化检查失败关闭，
    # 不消费重开、不重定向目标解析（错误信息锚定规范化检查，先于消费记账）
    for label, old_value, new_value in (
        ("旧目标尾随空白", "report_B ", "report_B_v2"),
        ("旧目标内部重复空白", "report  B", "report_B_v2"),
        ("新目标尾随空白", "report_B", "report_B_v2 "),
        ("新目标内部重复空白", "report_B", "report_B  v2"),
    ):
        ex_ws, co_ws, ct_ws, reopen_ws = fresh_rebind_root(
            f"项目_伪造_空白_{label}"
        )
        ex_ws.store.append(
            forged_rebind_event(
                kind="B", old=old_value, new=new_value,
                reason="environment_fix_confirmed", reopen=reopen_ws,
            )
        )
        with pytest.raises(CoordinatorEventContractError, match="未规范化"):
            co_ws.conditions(ct_ws)

    # ── 阶段 9：v1.2 §10.2 勘误——有交付且剩余对象穷尽阻断时，running /
    #           awaiting_user 直接进入 partial_delivery_blocked（不经中间状态）──
    def fresh_erratum_root(
        name: str, run_id: str, project_id: str,
    ) -> tuple[GraphExecutor, PartialDeliveryCoordinator, object]:
        root = tmp_path / name
        root_executor = GraphExecutor(root, run_id=run_id)
        root_coordinator = PartialDeliveryCoordinator(root_executor)

        def submit_erratum(
            *,
            family: str,
            object_id: str,
            from_state: str | None,
            to_state: str,
            trigger: str,
            evidence: dict[str, object],
            request_id: str,
        ) -> None:
            if trigger == "isolated_qc_accepted":
                evidence = dict(evidence)
                evidence_without_auth = {
                    k: v for k, v in evidence.items()
                    if k != "qc_authorization_id"
                }
                evidence_digest = _canonical_digest(evidence_without_auth)
                from tests.graph._qc_authorization_fixture import (
                    issue_test_qc_authorization,
                )

                auth_id = issue_test_qc_authorization(
                    root_executor,
                    report_object_id=object_id,
                    from_state=str(from_state),
                    to_state=to_state,
                    verdict="accepted",
                    evidence_digest=evidence_digest,
                    actor_id="pi_35b",
                    project_id=project_id,
                    occurred_at=_NOW,
                )
                evidence["qc_authorization_id"] = auth_id
            event = root_executor.submit(
                TransitionRequest(
                    schema_version="1.0",
                    request_id=request_id,
                    project_id=project_id,
                    run_id=run_id,
                    family=family,
                    object_id=object_id,
                    from_state=from_state,
                    to_state=to_state,
                    trigger=trigger,
                    evidence=evidence,
                    actor_id="pi_35b",
                    occurred_at=_NOW,
                )
            )
            assert event.event_type == "graph.transition.accepted", event.payload

        submit_erratum(
            family="project", object_id=_PROJECT_OBJECT,
            from_state=None, to_state="running",
            trigger="project_contract_and_preflight",
            evidence={"project_contract_established": True,
                      "preflight_records_established": True},
            request_id=f"{run_id}:create",
        )
        return root_executor, root_coordinator, submit_erratum

    def drive_a_locked_b_blocked_a_html(
        submit_erratum: object, run_id: str, *,
        b_blocked: bool,
        a_pptx: bool,
    ) -> None:
        for kind in ("A", "B"):
            submit_erratum(
                family="report_evidence", object_id=f"report_{kind}",
                from_state="queued", to_state="collecting",
                trigger="candidate_scope_locked",
                evidence={"candidate_scope_locked": True},
                request_id=f"{run_id}:{kind}:collecting",
            )
        submit_erratum(
            family="report_evidence", object_id="report_A",
            from_state="collecting", to_state="scientific_qc",
            trigger="gate_deterministic_pass",
            evidence={"gate_deterministic_pass": True,
                      "candidate_snapshot_established": True},
            request_id=f"{run_id}:A:qc",
        )
        submit_erratum(
            family="report_evidence", object_id="report_A",
            from_state="scientific_qc", to_state="snapshot_locked",
            trigger="isolated_qc_accepted",
            evidence={"isolated_qc_accepted": True,
                      "qc_verdict_id": "qc-verdict-1",
                      "qc_verdict_digest": "a" * 64,
                      "qc_candidate_snapshot_id": "snap-1",
                      "qc_candidate_content_digest": "b" * 64,
                      "qc_review_input_digest": "c" * 64,
                      "qc_report_object_id": "report_A",
                      "qc_context_digest": "d" * 64},
            request_id=f"{run_id}:A:locked",
        )
        if b_blocked:
            submit_erratum(
                family="report_evidence", object_id="report_B",
                from_state="collecting", to_state="evidence_blocked",
                trigger="recovery_exhausted_gap_remains",
                evidence={"critical_units_still_failing": True,
                          "recovery_exhausted": True,
                          "independent_review_exhausted": True,
                          "no_continuable_user_action": True},
                request_id=f"{run_id}:B:blocked",
            )
        submit_erratum(
            family="format_artifact", object_id=format_object_id("report_A", "html"),
            from_state="queued", to_state="generating",
            trigger="snapshot_locked_ready",
            evidence={"report_snapshot_locked": True},
            request_id=f"{run_id}:A:html:generating",
        )
        submit_erratum(
            family="format_artifact", object_id=format_object_id("report_A", "html"),
            from_state="generating", to_state="quality_check",
            trigger="artifact_built",
            evidence={"artifact_built": True},
            request_id=f"{run_id}:A:html:quality_check",
        )
        submit_erratum(
            family="format_artifact", object_id=format_object_id("report_A", "html"),
            from_state="quality_check", to_state="passed",
            trigger="acceptance_records_complete",
            evidence={"deterministic_check_recorded": True,
                      "coverage_check_recorded": True,
                      "real_render_check_recorded": True},
            request_id=f"{run_id}:A:html:passed",
        )
        submit_erratum(
            family="format_artifact", object_id=format_object_id("report_A", "html"),
            from_state="passed", to_state="delivery_ready",
            trigger="atomic_publish_manifest",
            evidence={"atomic_publish_complete": True,
                      "manifest_digest_recorded": True},
            request_id=f"{run_id}:A:html:delivery_ready",
        )
        if a_pptx:
            submit_erratum(
                family="format_artifact", object_id=format_object_id("report_A", "pptx"),
                from_state="queued", to_state="generating",
                trigger="snapshot_locked_ready",
                evidence={"report_snapshot_locked": True},
                request_id=f"{run_id}:A:pptx:generating",
            )
            submit_erratum(
                family="format_artifact", object_id=format_object_id("report_A", "pptx"),
                from_state="generating", to_state="blocked",
                trigger="format_recovery_exhausted",
                evidence={"format_recovery_exhausted": True,
                          "failure_evidence_saved": True},
                request_id=f"{run_id}:A:pptx:blocked",
            )

    def project_transition_states(executor: GraphExecutor) -> list[str]:
        return [
            str(event.payload["to_state"])
            for event in executor.store.read_all()
            if event.event_type == "graph.transition.accepted"
            and event.payload.get("family") == "project"
        ]

    # 9a：A HTML 交付 + B evidence_blocked（无可选格式）→ 直接 partial_delivery_blocked
    er_ab, co_ab, submit_ab = fresh_erratum_root("项目_直接阻断_AB", "run_35i", "p_35i")
    er_contract_ab = DeliveryContract(
        contract_id="contract_35i", contract_version=1,
        reports=("A", "B"), optional_formats=(),
    )
    drive_a_locked_b_blocked_a_html(submit_ab, "run_35i", b_blocked=True, a_pptx=False)
    direct_ab = co_ab.reconcile(er_contract_ab, actor_id="pi_35b", occurred_at=_NOW)
    assert direct_ab.submitted is not None
    assert direct_ab.submitted.payload["to_state"] == "partial_delivery_blocked"
    assert "partially_delivered" not in project_transition_states(er_ab)
    # 重开后若无对象实际重开/重绑，静默 reconcile 回到 partial_delivery_blocked
    reopen_ab = co_ab.reopen_project(
        er_contract_ab, reason="user_material_accepted",
        actor_id="pi_35b", occurred_at=_NOW,
    )
    assert reopen_ab.submitted is not None
    assert reopen_ab.submitted.event_type == "graph.transition.accepted"
    assert er_ab.state()["project"][_PROJECT_OBJECT] == "running"
    back_ab = co_ab.reconcile(er_contract_ab, actor_id="pi_35b", occurred_at=_NOW)
    assert back_ab.submitted is not None
    assert back_ab.submitted.payload["to_state"] == "partial_delivery_blocked"
    assert back_ab.submitted.payload["from_state"] == "running"

    # 9b：仅 A 报告、HTML 交付 + PPTX 阻断 → 直接 partial_delivery_blocked
    er_a, co_a, submit_a = fresh_erratum_root("项目_直接阻断_A", "run_35j", "p_35j")
    er_contract_a = DeliveryContract(
        contract_id="contract_35j", contract_version=1,
        reports=("A",), optional_formats=("pptx",),
    )
    drive_a_locked_b_blocked_a_html(submit_a, "run_35j", b_blocked=False, a_pptx=True)
    direct_a = co_a.reconcile(er_contract_a, actor_id="pi_35b", occurred_at=_NOW)
    assert direct_a.submitted is not None
    assert direct_a.submitted.payload["to_state"] == "partial_delivery_blocked"
    assert "partially_delivered" not in project_transition_states(er_a)

    # 9c：awaiting_user + 已交付目标 + 剩余终态阻断 → 直接 partial_delivery_blocked
    er_aw, co_aw, submit_aw = fresh_erratum_root("项目_直接阻断_awaiting", "run_35k", "p_35k")
    er_contract_aw = DeliveryContract(
        contract_id="contract_35k", contract_version=1,
        reports=("A", "B"), optional_formats=(),
    )
    drive_a_locked_b_blocked_a_html(submit_aw, "run_35k", b_blocked=True, a_pptx=False)
    submit_aw(
        family="project", object_id=_PROJECT_OBJECT,
        from_state="running", to_state="awaiting_user",
        trigger="double_exhaustion_critical_gap",
        evidence={"double_exhaustion_complete": True,
                  "critical_gap_remains": True,
                  "audit_package_written": True,
                  "request_written": True,
                  "audit_package_path": "blockers/A/v1/"},
        request_id="35k:awaiting",
    )
    direct_aw = co_aw.reconcile(er_contract_aw, actor_id="pi_35b", occurred_at=_NOW)
    assert direct_aw.submitted is not None
    assert direct_aw.submitted.payload["to_state"] == "partial_delivery_blocked"
    assert direct_aw.submitted.payload["from_state"] == "awaiting_user"
    assert "partially_delivered" not in project_transition_states(er_aw)

    # ── 阶段 10：连续两个 running -> awaiting_user -> running 周期 ────────
    await_executor, await_coordinator, submit_await = fresh_erratum_root(
        "项目_awaiting周期", "run_35l", "p_35l",
    )
    await_contract = DeliveryContract(
        contract_id="contract_35l", contract_version=1,
        reports=("A",), optional_formats=(),
    )
    bind_await = await_coordinator.reconcile(
        await_contract, actor_id="pi_35b", occurred_at=_NOW,
    )
    assert bind_await.submitted is None
    for cycle in (1, 2):
        submit_await(
            family="project", object_id=_PROJECT_OBJECT,
            from_state="running", to_state="awaiting_user",
            trigger="double_exhaustion_critical_gap",
            evidence={"double_exhaustion_complete": True,
                      "critical_gap_remains": True,
                      "audit_package_written": True,
                      "request_written": True,
                      "audit_package_path": "blockers/A/v1/"},
            request_id=f"35l:await:{cycle}",
        )
        reopen_await = await_coordinator.reopen_project(
            await_contract, reason="user_material_accepted",
            actor_id="pi_35b", occurred_at=_NOW,
        )
        assert reopen_await.submitted is not None
        assert reopen_await.submitted.event_type == "graph.transition.accepted"
        assert await_executor.state()["project"][_PROJECT_OBJECT] == "running"
        # 同一 awaiting 代次内重放：不追加
        total_before = len(await_executor.store.read_all())
        replay_await = await_coordinator.reopen_project(
            await_contract, reason="user_material_accepted",
            actor_id="pi_35b", occurred_at=_NOW,
        )
        assert replay_await.submitted is not None
        assert replay_await.submitted.event_type == "graph.transition.accepted"
        assert len(await_executor.store.read_all()) == total_before
        # 同一 awaiting 代次内原因漂移：失败关闭
        with pytest.raises(EventConflictError):
            await_coordinator.reopen_project(
                await_contract, reason="environment_fix_confirmed",
                actor_id="pi_35b", occurred_at=_NOW,
            )
    accepted_reopens = [
        event for event in await_executor.store.read_all()
        if event.event_type == "graph.transition.accepted"
        and event.payload.get("family") == "project"
        and event.payload.get("to_state") == "running"
        and event.payload.get("from_state") == "awaiting_user"
    ]
    assert len(accepted_reopens) == 2
    assert accepted_reopens[0].event_id != accepted_reopens[1].event_id

    # awaiting 重开不与更早的阻断重开碰撞（独立根）
    mix_executor, mix_coordinator, submit_mix = fresh_erratum_root(
        "项目_阻断awaiting混合", "run_35m", "p_35m",
    )
    mix_contract = DeliveryContract(
        contract_id="contract_35m", contract_version=1,
        reports=("A",), optional_formats=(),
    )
    for kind in ("A", "B", "C"):
        submit_mix(
            family="report_evidence", object_id=f"report_{kind}",
            from_state="queued", to_state="collecting",
            trigger="candidate_scope_locked",
            evidence={"candidate_scope_locked": True},
            request_id=f"35m:{kind}:collecting",
        )
        submit_mix(
            family="report_evidence", object_id=f"report_{kind}",
            from_state="collecting", to_state="evidence_blocked",
            trigger="recovery_exhausted_gap_remains",
            evidence={"critical_units_still_failing": True,
                      "recovery_exhausted": True,
                      "independent_review_exhausted": True,
                      "no_continuable_user_action": True},
            request_id=f"35m:{kind}:blocked",
        )
    mix_blocked = mix_coordinator.reconcile(
        mix_contract, actor_id="pi_35b", occurred_at=_NOW,
    )
    assert mix_blocked.submitted is not None
    assert mix_blocked.submitted.payload["to_state"] == "blocked"
    mix_reopen_blocked = mix_coordinator.reopen_project(
        mix_contract, reason="environment_fix_confirmed",
        actor_id="pi_35b", occurred_at=_NOW,
    )
    assert mix_reopen_blocked.submitted is not None
    assert mix_reopen_blocked.submitted.event_type == "graph.transition.accepted"
    submit_mix(
        family="project", object_id=_PROJECT_OBJECT,
        from_state="running", to_state="awaiting_user",
        trigger="double_exhaustion_critical_gap",
        evidence={"double_exhaustion_complete": True,
                  "critical_gap_remains": True,
                  "audit_package_written": True,
                  "request_written": True,
                  "audit_package_path": "blockers/A/v1/"},
        request_id="35m:awaiting",
    )
    mix_reopen_awaiting = mix_coordinator.reopen_project(
        mix_contract, reason="user_material_accepted",
        actor_id="pi_35b", occurred_at=_NOW,
    )
    assert mix_reopen_awaiting.submitted is not None
    assert mix_reopen_awaiting.submitted.event_type == "graph.transition.accepted"
    assert mix_reopen_blocked.submitted.event_id != mix_reopen_awaiting.submitted.event_id
    assert mix_executor.state()["project"][_PROJECT_OBJECT] == "running"

    # ── 阶段 11：格式新合同版本重开——阻断版本取自事件之前的最近绑定 ───────
    fmt_executor, fmt_coordinator, submit_fmt = fresh_erratum_root(
        "项目_格式版本", "run_35n", "p_35n",
    )
    fmt_contract_v1 = DeliveryContract(
        contract_id="contract_35n", contract_version=1,
        reports=("A",), optional_formats=("pptx",),
    )
    fmt_contract_v2 = DeliveryContract(
        contract_id="contract_35n", contract_version=2,
        reports=("A",), optional_formats=("pptx",),
    )
    # 先绑定 v1（无候选迁移，仅落库绑定）；随后驱动格式阻断
    bind_v1 = fmt_coordinator.reconcile(
        fmt_contract_v1, actor_id="pi_35b", occurred_at=_NOW,
    )
    assert bind_v1.submitted is None
    drive_a_locked_b_blocked_a_html(submit_fmt, "run_35n", b_blocked=False, a_pptx=True)
    fmt_blocked_state = fmt_coordinator.reconcile(
        fmt_contract_v1, actor_id="pi_35b", occurred_at=_NOW,
    )
    assert fmt_blocked_state.submitted is not None
    assert fmt_blocked_state.submitted.payload["to_state"] == "partial_delivery_blocked"
    # v1 声称新合同版本：不高于阻断时最近绑定 v1 → 失败关闭
    with pytest.raises(CoordinationError):
        fmt_coordinator.reopen_format(
            fmt_contract_v1, report_kind="A", fmt="pptx",
            reason="new_contract_version_reopens",
            actor_id="pi_35b", occurred_at=_NOW,
        )
    # 绑定 v2（项目在 partial_delivery_blocked，reconcile 只绑定不迁移）
    fmt_coordinator.reconcile(fmt_contract_v2, actor_id="pi_35b", occurred_at=_NOW)
    # v2 新合同版本重开：阻断时最近绑定为 v1，v2 > v1 → 接受
    fmt_reopen_v2 = fmt_coordinator.reopen_format(
        fmt_contract_v2, report_kind="A", fmt="pptx",
        reason="new_contract_version_reopens",
        actor_id="pi_35b", occurred_at=_NOW,
    )
    assert fmt_reopen_v2.submitted is not None
    assert fmt_reopen_v2.submitted.event_type == "graph.transition.accepted"
    assert fmt_executor.state()["format_artifact"][
        format_object_id("report_A", "pptx")
    ] == "queued"
    # 保留环境/生成器行为：v2 重新阻断后 environment_fixed 重开
    submit_fmt(
        family="format_artifact", object_id=format_object_id("report_A", "pptx"),
        from_state="queued", to_state="generating",
        trigger="snapshot_locked_ready",
        evidence={"report_snapshot_locked": True},
        request_id="35n:A:pptx:regen",
    )
    submit_fmt(
        family="format_artifact", object_id=format_object_id("report_A", "pptx"),
        from_state="generating", to_state="blocked",
        trigger="format_recovery_exhausted",
        evidence={"format_recovery_exhausted": True,
                  "failure_evidence_saved": True},
        request_id="35n:A:pptx:reblock",
    )
    fmt_env_reopen = fmt_coordinator.reopen_format(
        fmt_contract_v2, report_kind="A", fmt="pptx",
        reason="environment_fixed",
        actor_id="pi_35b", occurred_at=_NOW,
    )
    assert fmt_env_reopen.submitted is not None
    assert fmt_env_reopen.submitted.event_type == "graph.transition.accepted"
    assert fmt_executor.state()["format_artifact"][
        format_object_id("report_A", "pptx")
    ] == "queued"
