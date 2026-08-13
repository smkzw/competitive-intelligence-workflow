"""Task 3.4 检查点重放：副作用崩溃窗口幂等（GT11 唯一顶层节点）。

在“副作用成功、检查点未保存”崩溃窗口重放 publish/move/approve/delete，
四类副作用各只执行一次；非图拥有的业务事件安全 no-op 且保留在检查点血统。
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

_NOW = datetime(2026, 8, 13, 9, 30, tzinfo=UTC)


def test_replay_never_duplicates_publish_move_approve_or_delete(
    tmp_path: Path,
) -> None:
    """GT11：崩溃窗口重放四类副作用各一次；外来业务事件保留在血统中。"""
    from ci_workflow.domain.ids import stable_id
    from ci_workflow.graph.executor import GraphExecutor, IdempotentSideEffects
    from ci_workflow.graph.reducer import (
        GraphEventContractError,
        SideEffectTargetError,
        graph_reducer,
    )
    from ci_workflow.graph.state import initial_state
    from ci_workflow.storage.checkpoint_store import CheckpointStore
    from ci_workflow.storage.event_store import (
        EventConflictError,
        EventStore,
        WorkflowEvent,
    )

    project_root = tmp_path / "项目"
    store = EventStore(project_root)
    checkpoints = CheckpointStore(project_root)
    effects = IdempotentSideEffects(project_root)

    # 布置临时文件与目标
    staging = project_root / "staging"
    staging.mkdir(parents=True)
    publish_source = staging / "report.html"
    publish_source.write_text("<html>v1</html>", encoding="utf-8")
    move_source = staging / "draft.pdf"
    move_source.write_text("pdf-bytes", encoding="utf-8")
    delete_target = staging / "obsolete.json"
    delete_target.write_text("{}", encoding="utf-8")

    def op_event(
        *,
        event_type: str,
        idempotency_key: str,
        payload: dict[str, object],
        event_id: str | None = None,
    ) -> WorkflowEvent:
        return WorkflowEvent(
            schema_version="1.0",
            event_id=event_id
            or stable_id("side-effect", "p_gt11", "run_gt11", event_type, idempotency_key),
            project_id="p_gt11",
            run_id="run_gt11",
            event_type=event_type,
            occurred_at=_NOW,
            actor_id="gt11",
            idempotency_key=idempotency_key,
            payload=payload,
        )

    events = (
        op_event(
            event_type="artifact.publish",
            idempotency_key="publish:B:v1:html",
            payload={
                "target_identity": "artifact:B:v1:html",
                "source_path": "staging/report.html",
                "destination_path": "artifacts/report.html",
            },
        ),
        op_event(
            event_type="artifact.move",
            idempotency_key="move:B:v1:pdf",
            payload={
                "target_identity": "artifact:B:v1:pdf",
                "source_path": "staging/draft.pdf",
                "destination_path": "delivery/draft.pdf",
            },
        ),
        op_event(
            event_type="revision.approve",
            idempotency_key="approve:rev_001",
            payload={"approval_id": "rev_001", "decision": "approved", "approver": "owner"},
        ),
        op_event(
            event_type="artifact.delete",
            idempotency_key="delete:obsolete",
            payload={"target_identity": "staging/obsolete.json", "path": "staging/obsolete.json"},
        ),
    )
    for event in events:
        store.append(event)

    # 非图拥有的 Task 3.1–3.3 业务事件：与图事件共享同一规范 EventStore
    foreign = WorkflowEvent(
        schema_version="1.0",
        event_id=stable_id("download-request", "p_gt11", "run_gt11", "foreign_001"),
        project_id="p_gt11",
        run_id="run_gt11",
        event_type="download_request_state_changed",
        occurred_at=_NOW,
        actor_id="gt11",
        idempotency_key="download.request:foreign_001",
        payload={"request_id": "foreign_001", "to_state": "accepted"},
    )
    store.append(foreign)

    # 崩溃窗口：第一个副作用成功后、检查点保存前中断
    interrupted = False

    def crash_after_first(event: object) -> None:
        nonlocal interrupted
        effects(event)  # type: ignore[arg-type]
        if not interrupted:
            interrupted = True
            raise RuntimeError("模拟副作用完成后、检查点保存前中断")

    with pytest.raises(RuntimeError, match="模拟副作用"):
        checkpoints.replay(
            store,
            run_id="run_gt11",
            initial_state=initial_state(),
            reducer=graph_reducer,
            side_effect=crash_after_first,  # type: ignore[arg-type]
        )

    # 恢复重放：四类副作用各只执行一次，外来事件安全 no-op 且留在血统中
    checkpoint = checkpoints.replay(
        store,
        run_id="run_gt11",
        initial_state=initial_state(),
        reducer=graph_reducer,
        side_effect=effects,
    )
    # publish 恰好一次
    published = project_root / "artifacts" / "report.html"
    assert published.read_text(encoding="utf-8") == "<html>v1</html>"
    # move 恰好一次：源消失、目标内容一致
    assert not move_source.exists()
    assert (project_root / "delivery" / "draft.pdf").read_bytes() == b"pdf-bytes"
    # approve 恰好一次
    approvals_path = project_root / "state" / "approvals.jsonl"
    approvals = approvals_path.read_text(encoding="utf-8").splitlines()
    assert len(approvals) == 1
    approval_record = json.loads(approvals[0])
    assert approval_record["approval_id"] == "rev_001"
    assert approval_record["decision"] == "approved"
    # delete 恰好一次
    assert not delete_target.exists()
    # 幂等账本恰好四条；检查点状态记录四个目标
    ledger_path = project_root / "state" / "side_effect_ledger.jsonl"
    ledger_lines = ledger_path.read_text(encoding="utf-8").splitlines()
    assert len(ledger_lines) == 4
    side_effects = checkpoint.state["side_effects"]
    assert set(side_effects) == {
        "artifact:B:v1:html",
        "artifact:B:v1:pdf",
        "rev_001",
        "staging/obsolete.json",
    }
    # 外来事件保留在检查点血统中
    assert foreign.event_id in checkpoint.applied_event_ids
    assert checkpoint.last_sequence == 5
    assert checkpoint.event_stream_digest == store.stream_digest()

    # 检查点已保存后再次重放：无新事件、无重复副作用、返回同一检查点
    ledger_before = len(ledger_lines)
    replay_again = checkpoints.replay(
        store,
        run_id="run_gt11",
        initial_state=initial_state(),
        reducer=graph_reducer,
        side_effect=effects,
    )
    assert replay_again == checkpoint
    assert len(ledger_path.read_text(encoding="utf-8").splitlines()) == ledger_before
    # 执行器自身重放路径也返回同一检查点
    executor = GraphExecutor(project_root, run_id="run_gt11")
    assert executor.replay() == checkpoint

    # 非图业务事件保持 no-op；未知 graph.* 事件类型失败关闭（独立流，不污染成功流）
    malformed_root = tmp_path / "项目_malformed"
    malformed_store = EventStore(malformed_root)
    malformed_checkpoints = CheckpointStore(malformed_root)
    malformed = WorkflowEvent(
        schema_version="1.0",
        event_id=stable_id("graph-unknown", "p_malformed", "run_malformed"),
        project_id="p_malformed",
        run_id="run_malformed",
        event_type="graph.unknown",
        occurred_at=_NOW,
        actor_id="gt11",
        idempotency_key="graph.unknown:1",
        payload={},
    )
    malformed_store.append(malformed)
    with pytest.raises(ValueError, match="未知图事件类型"):
        malformed_checkpoints.replay(
            malformed_store,
            run_id="run_malformed",
            initial_state=initial_state(),
            reducer=graph_reducer,
            side_effect=IdempotentSideEffects(malformed_root),
        )
    # 成功流未被污染：外来业务事件仍留在血统中
    assert foreign.event_id in checkpoints.latest(run_id="run_gt11").applied_event_ids

    # 独立流：artifact.delete 只带 path（无 target_identity）→ 删除一次并记录路径身份
    delete_root = tmp_path / "项目_delete_path"
    delete_store = EventStore(delete_root)
    delete_checkpoints = CheckpointStore(delete_root)
    delete_effects = IdempotentSideEffects(delete_root)
    delete_dir = delete_root / "staging"
    delete_dir.mkdir(parents=True)
    delete_file = delete_dir / "old.txt"
    delete_file.write_text("old", encoding="utf-8")
    delete_event = WorkflowEvent(
        schema_version="1.0",
        event_id=stable_id("side-effect", "p_del", "run_del", "delete", "delete:path-only"),
        project_id="p_del",
        run_id="run_del",
        event_type="artifact.delete",
        occurred_at=_NOW,
        actor_id="gt11",
        idempotency_key="delete:path-only",
        payload={"path": "staging/old.txt"},
    )
    delete_store.append(delete_event)
    delete_checkpoint = delete_checkpoints.replay(
        delete_store,
        run_id="run_del",
        initial_state=initial_state(),
        reducer=graph_reducer,
        side_effect=delete_effects,
    )
    assert not delete_file.exists()
    delete_ledger_path = delete_root / "state" / "side_effect_ledger.jsonl"
    delete_ledger = delete_ledger_path.read_text(encoding="utf-8").splitlines()
    assert len(delete_ledger) == 1
    delete_record = json.loads(delete_ledger[0])
    assert delete_record["op"] == "artifact.delete"
    assert delete_record["target_identity"] == "staging/old.txt"
    # 规范状态记录同一路径身份
    assert (
        delete_checkpoint.state["side_effects"]["staging/old.txt"]["op"]
        == "artifact.delete"
    )
    # 精确重放不重复
    delete_replay = delete_checkpoints.replay(
        delete_store,
        run_id="run_del",
        initial_state=initial_state(),
        reducer=graph_reducer,
        side_effect=delete_effects,
    )
    assert delete_replay == delete_checkpoint
    assert len(delete_ledger_path.read_text(encoding="utf-8").splitlines()) == 1
    assert not delete_file.exists()

    # 非法目标载荷：缺失/类型错误的每操作 payload 以图域错误失败关闭，而非 KeyError
    malformed_cases = (
        ("artifact.publish", {"source_path": "a", "destination_path": "b"}),
        ("artifact.move", {"source_path": "a", "destination_path": "b"}),
        ("revision.approve", {"decision": "approved"}),
        ("artifact.delete", {}),
        ("artifact.publish", {"target_identity": 5, "source_path": "a", "destination_path": "b"}),
    )
    for index, (event_type, payload) in enumerate(malformed_cases):
        case_root = tmp_path / f"项目_malformed_target_{index}"
        case_store = EventStore(case_root)
        case_checkpoints = CheckpointStore(case_root)
        case_event = WorkflowEvent(
            schema_version="1.0",
            event_id=stable_id("side-effect", "p_mal", "run_mal", event_type, str(index)),
            project_id="p_mal",
            run_id="run_mal",
            event_type=event_type,
            occurred_at=_NOW,
            actor_id="gt11",
            idempotency_key=f"{event_type}:malformed:{index}",
            payload=payload,
        )
        case_store.append(case_event)
        with pytest.raises(SideEffectTargetError):
            case_checkpoints.replay(
                case_store,
                run_id="run_mal",
                initial_state=initial_state(),
                reducer=graph_reducer,
                side_effect=IdempotentSideEffects(case_root),
            )

    # 直接向共享 EventStore 追加的伪造/错配 graph.transition.accepted 载荷：
    # 归约时以图事件契约错误失败关闭，且不保存任何检查点（不依赖 submit 包装）
    def raw_accepted(
        *,
        family: str,
        object_id: str,
        from_state: str | None,
        to_state: str,
        trigger: str,
        guard_id: str,
        guard_evidence: dict[str, object] | None = None,
        request_digest: str = "d" * 64,
        suffix: str,
    ) -> WorkflowEvent:
        return WorkflowEvent(
            schema_version="1.0",
            event_id=stable_id(
                "graph-transition", "p_raw", "run_raw", family, object_id, suffix
            ),
            project_id="p_raw",
            run_id="run_raw",
            event_type="graph.transition.accepted",
            occurred_at=_NOW,
            actor_id="gt11",
            idempotency_key=f"graph.transition:raw:run_raw:{suffix}",
            payload={
                "family": family,
                "object_id": object_id,
                "from_state": from_state,
                "to_state": to_state,
                "trigger": trigger,
                "guard_id": guard_id,
                "guard_evidence": guard_evidence or {},
                "request_digest": request_digest,
            },
        )

    def assert_raw_replay_fails(
        root_name: str,
        events: tuple[WorkflowEvent, ...],
        match: str,
    ) -> None:
        root = tmp_path / root_name
        raw_store = EventStore(root)
        for raw_event in events:
            raw_store.append(raw_event)
        with pytest.raises(GraphEventContractError, match=match):
            CheckpointStore(root).replay(
                raw_store,
                run_id="run_raw",
                initial_state=initial_state(),
                reducer=graph_reducer,
                side_effect=IdempotentSideEffects(root),
            )
        assert not list((root / "state" / "checkpoints").glob("*.json"))

    # 1) 未声明边伪造：queued -> snapshot_locked 不存在
    assert_raw_replay_fails(
        "项目_forge_undeclared",
        (
            raw_accepted(
                family="report_evidence",
                object_id="report_1",
                from_state="queued",
                to_state="snapshot_locked",
                trigger="isolated_qc_accepted",
                guard_id="g_report_scientific_qc_snapshot_locked",
                guard_evidence={
                    "isolated_qc_accepted": True,
                    "qc_verdict_id": "qc-verdict-1",
                    "qc_verdict_digest": "a" * 64,
                    "qc_candidate_snapshot_id": "snap-1",
                    "qc_candidate_content_digest": "b" * 64,
                    "qc_review_input_digest": "c" * 64,
                    "qc_report_object_id": "report_B",
                    "qc_context_digest": "d" * 64,
                },
                suffix="undeclared",
            ),
        ),
        "未声明迁移",
    )
    # 2) 合法边但 trigger 错误
    assert_raw_replay_fails(
        "项目_forge_trigger",
        (
            raw_accepted(
                family="project",
                object_id="obj_1",
                from_state=None,
                to_state="running",
                trigger="WRONG_TRIGGER",
                guard_id="g_project_create_running",
                guard_evidence={
                    "project_contract_established": True,
                    "preflight_records_established": True,
                },
                suffix="trigger",
            ),
        ),
        "trigger 不匹配",
    )
    # 3) 合法边但守卫证据缺失 → 重求值拒绝
    assert_raw_replay_fails(
        "项目_forge_guard",
        (
            raw_accepted(
                family="report_evidence",
                object_id="report_2",
                from_state="queued",
                to_state="collecting",
                trigger="candidate_scope_locked",
                guard_id="g_report_queued_collecting",
                guard_evidence={},
                suffix="guard",
            ),
        ),
        "守卫重求值拒绝",
    )
    # 4) 合法边但 from_state 与已归约当前状态不一致
    assert_raw_replay_fails(
        "项目_forge_current",
        (
            raw_accepted(
                family="report_evidence",
                object_id="report_3",
                from_state="queued",
                to_state="collecting",
                trigger="candidate_scope_locked",
                guard_id="g_report_queued_collecting",
                guard_evidence={"candidate_scope_locked": True},
                suffix="first",
            ),
            raw_accepted(
                family="report_evidence",
                object_id="report_3",
                from_state="recovering",
                to_state="scientific_qc",
                trigger="gate_deterministic_pass",
                guard_id="g_report_recovering_scientific_qc",
                guard_evidence={
                    "gate_deterministic_pass": True,
                    "candidate_snapshot_established": True,
                },
                suffix="second",
            ),
        ),
        "当前状态不匹配",
    )
    # 5) 合法边但 guard_id 与声明边不一致
    assert_raw_replay_fails(
        "项目_forge_guard_id",
        (
            raw_accepted(
                family="report_evidence",
                object_id="report_4",
                from_state="queued",
                to_state="collecting",
                trigger="candidate_scope_locked",
                guard_id="g_report_collecting_recovering",
                guard_evidence={"candidate_scope_locked": True},
                suffix="guard_id",
            ),
        ),
        "guard_id 不匹配",
    )
    # 6) 状态值/类型错误：to_state 不在族内、from_state 类型错误
    assert_raw_replay_fails(
        "项目_forge_value",
        (
            raw_accepted(
                family="report_evidence",
                object_id="report_5",
                from_state="queued",
                to_state="bogus",
                trigger="candidate_scope_locked",
                guard_id="g_report_queued_collecting",
                guard_evidence={"candidate_scope_locked": True},
                suffix="value",
            ),
        ),
        "不存在状态",
    )
    assert_raw_replay_fails(
        "项目_forge_type",
        (
            raw_accepted(
                family="report_evidence",
                object_id="report_6",
                from_state=123,  # type: ignore[arg-type]
                to_state="collecting",
                trigger="candidate_scope_locked",
                guard_id="g_report_queued_collecting",
                guard_evidence={"candidate_scope_locked": True},
                suffix="type",
            ),
        ),
        "from_state",
    )
    # 7) 一条完全合法的原始 accepted 事件可正常重放：这是校验而非一律拒绝
    legal_root = tmp_path / "项目_raw_legal"
    legal_store = EventStore(legal_root)
    legal_store.append(
        raw_accepted(
            family="project",
            object_id="obj_legal",
            from_state=None,
            to_state="running",
            trigger="project_contract_and_preflight",
            guard_id="g_project_create_running",
            guard_evidence={
                "project_contract_established": True,
                "preflight_records_established": True,
            },
            suffix="legal",
        )
    )
    legal_executor = GraphExecutor(legal_root, run_id="run_raw")
    assert legal_executor.state()["project"]["obj_legal"] == "running"
    legal_checkpoint = CheckpointStore(legal_root).replay(
        legal_store,
        run_id="run_raw",
        initial_state=initial_state(),
        reducer=graph_reducer,
        side_effect=IdempotentSideEffects(legal_root),
    )
    assert legal_checkpoint.state["project"]["obj_legal"] == "running"
    assert len(list((legal_root / "state" / "checkpoints").glob("*.json"))) == 1
    legal_again = CheckpointStore(legal_root).replay(
        legal_store,
        run_id="run_raw",
        initial_state=initial_state(),
        reducer=graph_reducer,
        side_effect=IdempotentSideEffects(legal_root),
    )
    assert legal_again == legal_checkpoint

    # 8) 科学质控迁移重放必须消费边界签发的授权：直接追加的
    #    "scientific_qc -> snapshot_locked" 接受事件（无授权事件背书）
    #    在归约/重放时失败关闭，不能成为规范状态。
    assert_raw_replay_fails(
        "项目_raw_qc_forged",
        (
            raw_accepted(
                family="report_evidence",
                object_id="report_1",
                from_state="queued",
                to_state="collecting",
                trigger="candidate_scope_locked",
                guard_id="g_report_queued_collecting",
                guard_evidence={"candidate_scope_locked": True},
                suffix="collect",
            ),
            raw_accepted(
                family="report_evidence",
                object_id="report_1",
                from_state="collecting",
                to_state="scientific_qc",
                trigger="gate_deterministic_pass",
                guard_id="g_report_collecting_scientific_qc",
                guard_evidence={
                    "gate_deterministic_pass": True,
                    "candidate_snapshot_established": True,
                },
                suffix="qc",
            ),
            raw_accepted(
                family="report_evidence",
                object_id="report_1",
                from_state="scientific_qc",
                to_state="snapshot_locked",
                trigger="isolated_qc_accepted",
                guard_id="g_report_scientific_qc_snapshot_locked",
                guard_evidence={
                    "isolated_qc_accepted": True,
                    "qc_verdict_id": "v1",
                    "qc_verdict_digest": "a" * 64,
                    "qc_candidate_snapshot_id": "snap-1",
                    "qc_candidate_content_digest": "b" * 64,
                    "qc_review_input_digest": "c" * 64,
                    "qc_report_object_id": "report_1",
                    "qc_context_digest": "d" * 64,
                    "qc_authorization_id": "forged-auth",
                },
                suffix="locked",
            ),
        ),
        "消费了未签发的授权",
    )

    # 直接向共享 EventStore 追加的伪造/漂移 graph.node.completed 载荷：
    # 归约时以图事件契约错误失败关闭且不保存检查点（与 complete_node 边界一致）
    def node_digest(
        *,
        node_id: str,
        report_kind: str | None,
        input_digest: str,
        outputs: dict[str, object],
    ) -> str:
        encoded = (
            json.dumps(
                {
                    "node_id": node_id,
                    "report_kind": report_kind,
                    "input_digest": input_digest,
                    "outputs": outputs,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def raw_completed(
        *,
        node_id: str,
        report_kind: str | None,
        scope: str,
        input_digest: str,
        outputs: dict[str, object],
        completion_digest: str | None = None,
        event_id: str | None = None,
        idempotency_key: str | None = None,
        suffix: str,
    ) -> WorkflowEvent:
        scope_part = report_kind or "shared"
        digest = completion_digest or node_digest(
            node_id=node_id,
            report_kind=report_kind,
            input_digest=input_digest,
            outputs=outputs,
        )
        return WorkflowEvent(
            schema_version="1.0",
            event_id=event_id
            or stable_id(
                "graph-node-completed", "p_raw", "run_raw", node_id, scope_part, input_digest
            ),
            project_id="p_raw",
            run_id="run_raw",
            event_type="graph.node.completed",
            occurred_at=_NOW,
            actor_id="gt11",
            idempotency_key=idempotency_key
            or f"graph.node.completed:p_raw:run_raw:{node_id}:{scope_part}:{input_digest}",
            payload={
                "node_id": node_id,
                "report_kind": report_kind,
                "scope": scope,
                "input_digest": input_digest,
                "completion_digest": digest,
                "outputs": outputs,
            },
        )

    valid_gate_outputs = {"gate_passed": True, "failures": [], "evidence_digest": "d" * 64}
    # 1) 输出类型错误（含验证者复现的 gate_passed="YES"）
    assert_raw_replay_fails(
        "项目_node_wrong_types",
        (
            raw_completed(
                node_id="gate",
                report_kind="A",
                scope="report",
                input_digest="gate:A:1",
                outputs={
                    "gate_passed": "YES",
                    "failures": "not-a-list",
                    "evidence_digest": "",
                },
                suffix="wrong_types",
            ),
        ),
        "输出类型",
    )
    # 2) scope / 报告类型不匹配
    assert_raw_replay_fails(
        "项目_node_scope_mismatch",
        (
            raw_completed(
                node_id="gate",
                report_kind="A",
                scope="shared",
                input_digest="gate:A:1",
                outputs=valid_gate_outputs,
                suffix="scope",
            ),
        ),
        "scope 不匹配",
    )
    assert_raw_replay_fails(
        "项目_node_report_mismatch",
        (
            raw_completed(
                node_id="gate",
                report_kind="X",
                scope="report",
                input_digest="gate:A:1",
                outputs=valid_gate_outputs,
                suffix="report",
            ),
        ),
        "需要报告类型",
    )
    assert_raw_replay_fails(
        "项目_node_shared_mismatch",
        (
            raw_completed(
                node_id="resolve",
                report_kind="A",
                scope="shared",
                input_digest="resolve:1",
                outputs={
                    "evidence_references": [
                        {"fragment_id": "f1", "sha256": "0" * 64}
                    ]
                },
                suffix="shared",
            ),
        ),
        "不接受 report_kind",
    )
    # 3) 缺少/多余输出键
    assert_raw_replay_fails(
        "项目_node_missing_output",
        (
            raw_completed(
                node_id="gate",
                report_kind="A",
                scope="report",
                input_digest="gate:A:1",
                outputs={"gate_passed": True, "failures": []},
                suffix="missing",
            ),
        ),
        "输出与声明不符",
    )
    assert_raw_replay_fails(
        "项目_node_extra_output",
        (
            raw_completed(
                node_id="gate",
                report_kind="A",
                scope="report",
                input_digest="gate:A:1",
                outputs={**valid_gate_outputs, "bogus": 1},
                suffix="extra",
            ),
        ),
        "输出与声明不符",
    )
    # 4) 完成谓词拒绝（键齐但值为 None）
    assert_raw_replay_fails(
        "项目_node_predicate",
        (
            raw_completed(
                node_id="gate",
                report_kind="A",
                scope="report",
                input_digest="gate:A:1",
                outputs={"gate_passed": None, "failures": [], "evidence_digest": "d" * 64},
                suffix="predicate",
            ),
        ),
        "完成谓词",
    )
    # 5) completion_digest 漂移
    assert_raw_replay_fails(
        "项目_node_digest_drift",
        (
            raw_completed(
                node_id="gate",
                report_kind="A",
                scope="report",
                input_digest="gate:A:1",
                outputs=valid_gate_outputs,
                completion_digest="f" * 64,
                suffix="digest",
            ),
        ),
        "completion_digest",
    )
    # 6) 事件 ID 漂移
    assert_raw_replay_fails(
        "项目_node_event_id_drift",
        (
            raw_completed(
                node_id="gate",
                report_kind="A",
                scope="report",
                input_digest="gate:A:1",
                outputs=valid_gate_outputs,
                event_id=stable_id(
                    "graph-node-completed", "p_raw", "run_raw", "gate", "A", "other"
                ),
                suffix="event_id",
            ),
        ),
        "事件 ID 不匹配",
    )
    # 7) 幂等键漂移
    assert_raw_replay_fails(
        "项目_node_key_drift",
        (
            raw_completed(
                node_id="gate",
                report_kind="A",
                scope="report",
                input_digest="gate:A:1",
                outputs=valid_gate_outputs,
                idempotency_key="graph.node.completed:WRONG:run_raw:gate:A:gate:A:1",
                suffix="key",
            ),
        ),
        "幂等键不匹配",
    )
    # 8) 合法节点完成（经 complete_node 写入）被全新执行器重放成功：非一律拒绝
    legal_node_root = tmp_path / "项目_node_legal"
    node_executor = GraphExecutor(legal_node_root, run_id="run_node_legal")
    node_event = node_executor.complete_node(
        "resolve",
        outputs={
            "evidence_references": [
                {"fragment_id": "frag_legal", "sha256": "0" * 64}
            ]
        },
        input_digest="resolve:legal:1",
        project_id="p_node_legal",
        actor_id="gt11",
        occurred_at=_NOW,
    )
    fresh_executor = GraphExecutor(legal_node_root, run_id="run_node_legal")
    fresh_state = fresh_executor.state()
    assert fresh_state["evidence"]["evidence_references"][0]["fragment_id"] == "frag_legal"
    node_checkpoint = CheckpointStore(legal_node_root).replay(
        EventStore(legal_node_root),
        run_id="run_node_legal",
        initial_state=initial_state(),
        reducer=graph_reducer,
        side_effect=IdempotentSideEffects(legal_node_root),
    )
    assert node_event.event_id in node_checkpoint.applied_event_ids
    assert len(list((legal_node_root / "state" / "checkpoints").glob("*.json"))) == 1

    # 同一幂等键、不同操作载荷 → 通过 EventStore 失败关闭
    drifted = op_event(
        event_type="artifact.publish",
        idempotency_key="publish:B:v1:html",
        payload={
            "target_identity": "artifact:B:v1:other",
            "source_path": "staging/report.html",
            "destination_path": "artifacts/other.html",
        },
        event_id=stable_id("side-effect", "p_gt11", "run_gt11", "drifted", "publish:B:v1:html"),
    )
    with pytest.raises(EventConflictError):
        store.append(drifted)
