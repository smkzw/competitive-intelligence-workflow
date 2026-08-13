"""Task 3.7 SQ03+SQ04：隔离审查只收到候选快照/标准/覆盖/来源引用；
否决可修复回恢复、不可修复+双重穷尽进证据阻断，均无下游产物。

SQ03：审查输入包只含候选快照/事实/声明、标准、覆盖与证据/来源/定位引用；
推理、思维链、草稿、提示词、日志、任务上下文、可变回调或审查结论不是合法
字段。公共边界以真实上下文/审查包/结论运行后候选内容字节不变；否决/接受
不能改写事实或声明；审查者身份由边界显式传入且与上下文生产者不同。

SQ04：可修复否决（veto_disposition=recoverable）→ 已接受图迁移
scientific_qc -> recovering；不可修复否决（exhausted）+ 原始重验证的双重
穷尽记录 → 已接受 scientific_qc -> evidence_blocked；参数化 A/B/C 复用
Task 3.2 全零下游断言。裸布尔伪造、非 SHA 摘要、错对象授权在对象已定位到
scientific_qc 后仍被守卫拒绝；伪造迁移证据可审计但不能改状态。
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ci_workflow.domain.enums import ReportKind
from ci_workflow.gates.exhaustion import DoubleExhaustionRecord
from ci_workflow.graph.types import TransitionRequest
from tests.integration.test_no_draft_when_blocked import (
    assert_no_downstream_artifacts,
    gap_exhaustion,
    now,
    prepare_workspace,
    snapshot_for,
)
from tests.integration.test_scientific_qc_gate import (
    PROJECT_ID,
    REVIEWER_ID,
    _accepted_trio,
    _candidate_digest,
    _passed_gate_result,
    _source_refs,
    _veto_trio,
)

PRODUCER_ID = "qc-producer-1"


def _setup_executor(tmp_path):
    from ci_workflow.graph.executor import GraphExecutor

    workspace_root = prepare_workspace(tmp_path)
    run_id = "run-sqc-1"
    executor = GraphExecutor(workspace_root, run_id=run_id)
    return workspace_root, executor, run_id


def _drive_to_scientific_qc(
    executor, *, object_id: str, project_id: str, run_id: str, request_counter: int
):
    from ci_workflow.graph.types import TransitionRequest
    from tests.graph.test_transition_matrix import _NOW

    executor.submit(
        TransitionRequest(
            schema_version="1.0",
            request_id=f"sqc:{request_counter}:collect",
            project_id=project_id,
            run_id=run_id,
            family="report_evidence",
            object_id=object_id,
            from_state="queued",
            to_state="collecting",
            trigger="candidate_scope_locked",
            evidence={"candidate_scope_locked": True},
            actor_id="builder",
            occurred_at=_NOW,
        )
    )
    executor.submit(
        TransitionRequest(
            schema_version="1.0",
            request_id=f"sqc:{request_counter + 1}:qc",
            project_id=project_id,
            run_id=run_id,
            family="report_evidence",
            object_id=object_id,
            from_state="collecting",
            to_state="scientific_qc",
            trigger="gate_deterministic_pass",
            evidence={
                "gate_deterministic_pass": True,
                "candidate_snapshot_established": True,
            },
            actor_id="builder",
            occurred_at=_NOW,
        )
    )


def _apply_boundary(
    *,
    current_context,
    verdict,
    review_bundle,
    gate_result,
    snapshot,
    workspace_root,
    database_path,
    reviewer_actor_id=REVIEWER_ID,
    executor=None,
    object_id=None,
    exhaustion=None,
) -> str:
    from ci_workflow.capabilities.scientific_qc import apply_scientific_qc_verdict

    return apply_scientific_qc_verdict(
        current_context=current_context,
        verdict=verdict,
        review_bundle=review_bundle,
        gate_result=gate_result,
        snapshot=snapshot,
        workspace_root=workspace_root,
        database_path=database_path,
        reviewer_actor_id=reviewer_actor_id,
        executor=executor,
        object_id=object_id,
        exhaustion=exhaustion,
    )


# ─── SQ03 ────────────────────────────────────────────────────────────────────


def test_scientific_qc_receives_artifact_and_criteria_not_worker_reasoning_context(
    tmp_path,
) -> None:
    """公共边界：真实上下文/审查包/结论；推理/提示词/日志被拒；候选内容不变。"""
    from ci_workflow.qc.scientific import (
        ScientificQcReviewBundle,
        ScientificQcVerdict,
    )

    workspace_root, executor, run_id = _setup_executor(tmp_path)
    database_path = workspace_root / "project.sqlite"
    report_kind = ReportKind.A
    gate_result = _passed_gate_result(report_kind)
    snapshot = snapshot_for(report_kind)
    report_version = "v1"
    object_id = "report_A"

    # ── 推理/思维链/提示词/日志/回调/审查结论 被拒 ───────────────────────────
    base_bundle = {
        "producer_id": PRODUCER_ID,
        "project_id": PROJECT_ID,
        "report_kind": report_kind.value,
        "report_version": report_version,
        "report_object_id": object_id,
        "candidate_snapshot_id": gate_result.evidence_snapshot_id,
        "candidate_content_digest": _candidate_digest(snapshot),
        "criteria_version": "1.0",
        "gate_result_key": gate_result.result_key,
        "coverage_set_id": "coverage-set-1",
        "coverage_digest": "a" * 64,
        "source_refs": _source_refs(),
        "locators": [
            {
                "fragment_id": "frag-1",
                "locator": {
                    "document_role": "registry",
                    "field_path": "primary_outcome.measure",
                    "url": "https://registry.example/NCT0001",
                },
            }
        ],
    }
    for forbidden_key in (
        "worker_reasoning",
        "chain_of_thought",
        "scratch_notes",
        "prompt",
        "log",
        "task_context",
        "mutable_callback",
        "review_verdict",
    ):
        with pytest.raises(ValidationError, match=f"额外的字段|{forbidden_key}|forbid"):
            ScientificQcReviewBundle.model_validate(
                {**base_bundle, forbidden_key: "value"}
            )

    # ── 候选内容字节不变：审查前后序列化字节一致 ─────────────────────────────
    snapshot_bytes_before = _candidate_digest(snapshot)
    _drive_to_scientific_qc(
        executor,
        object_id=object_id,
        project_id=PROJECT_ID,
        run_id=run_id,
        request_counter=1,
    )
    assert executor.state()["report_evidence"][object_id] == "scientific_qc"

    ctx_dict, bundle_dict, verdict_dict = _accepted_trio(
        report_kind, gate_result, snapshot
    )
    next_state = _apply_boundary(
        current_context=ctx_dict,
        verdict=verdict_dict,
        review_bundle=bundle_dict,
        gate_result=gate_result,
        snapshot=snapshot,
        workspace_root=workspace_root,
        database_path=database_path,
        executor=executor,
        object_id=object_id,
    )
    assert next_state == "snapshot_locked"
    assert executor.state()["report_evidence"][object_id] == "snapshot_locked"
    assert _candidate_digest(snapshot) == snapshot_bytes_before
    assert snapshot.model_dump(mode="json") is not None  # 内容未变

    # ── 否决/接受不能改写事实或声明：结论不含事实/声明字段，候选不可变 ──────
    ctx_veto, bundle_veto, verdict_veto = _veto_trio(
        report_kind, gate_result, snapshot, "recoverable"
    )
    verdict_model = ScientificQcVerdict.model_validate(verdict_veto)
    assert verdict_model.candidate_content_digest == _candidate_digest(snapshot)
    # 结论模型 extra=forbid，事实/声明字段无法混入
    with pytest.raises(ValidationError):
        ScientificQcVerdict.model_validate(
            {**verdict_veto, "rewritten_claim": {"value": "fabricated"}}
        )
    # 候选字节仍然不变
    assert _candidate_digest(snapshot) == snapshot_bytes_before

    # ── 生产者/审查者身份分离（真实边界）────────────────────────────────────
    # 上下文生产者 == 边界审查者 → 拒绝
    ctx_same, bundle_same, verdict_same = _accepted_trio(
        report_kind, gate_result, snapshot,
        producer_id=REVIEWER_ID, report_object_id=f"{object_id}_same",
    )
    _drive_to_scientific_qc(
        executor,
        object_id=f"{object_id}_same",
        project_id=PROJECT_ID,
        run_id=run_id,
        request_counter=8,
    )
    with pytest.raises(ValueError, match="不同身份"):
        _apply_boundary(
            current_context=ctx_same,
            verdict=verdict_same,
            review_bundle=bundle_same,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
            executor=executor,
            object_id=f"{object_id}_same",
        )
    assert executor.state()["report_evidence"][f"{object_id}_same"] == "scientific_qc"
    # 不同身份 → 接受（已在上方 accepted 路径证明）
    # 上下文生产者与结论审查者都被边界校验：结论审查者必须等于边界传入的
    # reviewer_actor_id，不能被结论自由选择
    ctx_distinct, bundle_distinct, verdict_distinct = _accepted_trio(
        report_kind, gate_result, snapshot,
        report_object_id=f"{object_id}_wrongrev",
    )
    verdict_distinct = dict(verdict_distinct)
    verdict_distinct["reviewer_id"] = "someone-else"
    _drive_to_scientific_qc(
        executor,
        object_id=f"{object_id}_wrongrev",
        project_id=PROJECT_ID,
        run_id=run_id,
        request_counter=9,
    )
    with pytest.raises(ValueError, match="审查者"):
        _apply_boundary(
            current_context=ctx_distinct,
            verdict=verdict_distinct,
            review_bundle=bundle_distinct,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
            executor=executor,
            object_id=f"{object_id}_wrongrev",
        )
    assert (
        executor.state()["report_evidence"][f"{object_id}_wrongrev"]
        == "scientific_qc"
    )


# ─── SQ04 ────────────────────────────────────────────────────────────────────


REPORT_KINDS = (ReportKind.A, ReportKind.B, ReportKind.C)


@pytest.mark.parametrize("report_kind", REPORT_KINDS, ids=("A", "B", "C"))
def test_recoverable_veto_routes_to_recovering_and_exhausted_veto_blocks_without_artifacts(
    report_kind: ReportKind,
    tmp_path,
) -> None:
    """可修复否决 → recovering；不可修复+双重穷尽 → evidence_blocked；
    A/B/C 全部零下游产物；裸布尔/非 SHA/错对象伪造被守卫拒绝。"""

    workspace_root, executor, run_id = _setup_executor(tmp_path)
    database_path = workspace_root / "project.sqlite"
    gate_result = _passed_gate_result(report_kind)
    snapshot = snapshot_for(report_kind)
    report_version = "v1"
    object_id = f"report_{report_kind.value}"

    # 1) 可修复否决 → scientific_qc -> recovering
    _drive_to_scientific_qc(
        executor,
        object_id=object_id,
        project_id=PROJECT_ID,
        run_id=run_id,
        request_counter=1,
    )
    assert executor.state()["report_evidence"][object_id] == "scientific_qc"

    ctx_recoverable, bundle_recoverable, verdict_recoverable = _veto_trio(
        report_kind, gate_result, snapshot, "recoverable"
    )
    next_state = _apply_boundary(
        current_context=ctx_recoverable,
        verdict=verdict_recoverable,
        review_bundle=bundle_recoverable,
        gate_result=gate_result,
        snapshot=snapshot,
        workspace_root=workspace_root,
        database_path=database_path,
        executor=executor,
        object_id=object_id,
    )
    assert next_state == "recovering"
    assert executor.state()["report_evidence"][object_id] == "recovering"
    assert_no_downstream_artifacts(
        workspace_root,
        project_id=PROJECT_ID,
        report_kind=report_kind,
        report_version=report_version,
    )

    # 1b) 可修复否决不得携带双重穷尽记录
    _drive_to_scientific_qc(
        executor,
        object_id=f"{object_id}_rec2",
        project_id=PROJECT_ID,
        run_id=run_id,
        request_counter=20,
    )
    ctx_rec2, bundle_rec2, verdict_rec2 = _veto_trio(
        report_kind, gate_result, snapshot, "recoverable",
        report_object_id=f"{object_id}_rec2",
    )
    with pytest.raises(ValueError, match="不得携带"):
        _apply_boundary(
            current_context=ctx_rec2,
            verdict=verdict_rec2,
            review_bundle=bundle_rec2,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
            executor=executor,
            object_id=f"{object_id}_rec2",
            exhaustion=_valid_exhaustion(report_kind),
        )
    assert_no_downstream_artifacts(
        workspace_root,
        project_id=PROJECT_ID,
        report_kind=report_kind,
        report_version=report_version,
    )

    # 2) 不可修复否决 + 匹配双重穷尽 → scientific_qc -> evidence_blocked
    blocked_id = f"{object_id}_blocked"
    _drive_to_scientific_qc(
        executor,
        object_id=blocked_id,
        project_id=PROJECT_ID,
        run_id=run_id,
        request_counter=30,
    )
    ctx_exhausted, bundle_exhausted, verdict_exhausted = _veto_trio(
        report_kind, gate_result, snapshot, "exhausted",
        report_object_id=blocked_id,
    )
    exhaustion = _valid_exhaustion(report_kind)
    next_state_exhausted = _apply_boundary(
        current_context=ctx_exhausted,
        verdict=verdict_exhausted,
        review_bundle=bundle_exhausted,
        gate_result=gate_result,
        snapshot=snapshot,
        workspace_root=workspace_root,
        database_path=database_path,
        executor=executor,
        object_id=blocked_id,
        exhaustion=exhaustion,
    )
    assert next_state_exhausted == "evidence_blocked"
    assert executor.state()["report_evidence"][blocked_id] == "evidence_blocked"
    assert_no_downstream_artifacts(
        workspace_root,
        project_id=PROJECT_ID,
        report_kind=report_kind,
        report_version=report_version,
    )

    # 2b) 已穷尽否决缺记录 → 拒绝
    _drive_to_scientific_qc(
        executor,
        object_id=f"{object_id}_ex2",
        project_id=PROJECT_ID,
        run_id=run_id,
        request_counter=40,
    )
    ctx_ex2, bundle_ex2, verdict_ex2 = _veto_trio(
        report_kind, gate_result, snapshot, "exhausted",
        report_object_id=f"{object_id}_ex2",
    )
    with pytest.raises(ValueError, match="双重穷尽记录"):
        _apply_boundary(
            current_context=ctx_ex2,
            verdict=verdict_ex2,
            review_bundle=bundle_ex2,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
            executor=executor,
            object_id=f"{object_id}_ex2",
        )
    assert_no_downstream_artifacts(
        workspace_root,
        project_id=PROJECT_ID,
        report_kind=report_kind,
        report_version=report_version,
    )

    # 2c) 已穷尽否决 + 错项目/错报告记录 → 拒绝
    _drive_to_scientific_qc(
        executor,
        object_id=f"{object_id}_ex3",
        project_id=PROJECT_ID,
        run_id=run_id,
        request_counter=50,
    )
    wrong_record = _valid_exhaustion(report_kind).model_copy(
        update={"project_id": "project-other"}
    )
    with pytest.raises(ValueError, match="项目"):
        _apply_boundary(
            current_context=ctx_ex2,
            verdict=verdict_ex2,
            review_bundle=bundle_ex2,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
            executor=executor,
            object_id=f"{object_id}_ex3",
            exhaustion=wrong_record,
        )
    wrong_kind_record = _valid_exhaustion(
        ReportKind.B if report_kind is ReportKind.A else ReportKind.A
    )
    with pytest.raises(ValueError, match="报告类型"):
        _apply_boundary(
            current_context=ctx_ex2,
            verdict=verdict_ex2,
            review_bundle=bundle_ex2,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
            executor=executor,
            object_id=f"{object_id}_ex3",
            exhaustion=wrong_kind_record,
        )
    assert_no_downstream_artifacts(
        workspace_root,
        project_id=PROJECT_ID,
        report_kind=report_kind,
        report_version=report_version,
    )

    # 2d) 已穷尽否决 + model_copy 伪造角色记录 → 原始重验证拒绝
    from ci_workflow.gates.exhaustion import ExhaustionRole

    _drive_to_scientific_qc(
        executor,
        object_id=f"{object_id}_ex4",
        project_id=PROJECT_ID,
        run_id=run_id,
        request_counter=60,
    )
    forged_record = _valid_exhaustion(report_kind)
    forged_gap = forged_record.gaps[0].model_copy(
        update={"executor_role": ExhaustionRole.REVIEWER}
    )
    forged_record = forged_record.model_copy(update={"gaps": (forged_gap,)})
    with pytest.raises(ValueError, match="执行者角色"):
        _apply_boundary(
            current_context=ctx_ex2,
            verdict=verdict_ex2,
            review_bundle=bundle_ex2,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
            executor=executor,
            object_id=f"{object_id}_ex4",
            exhaustion=forged_record,
        )
    assert_no_downstream_artifacts(
        workspace_root,
        project_id=PROJECT_ID,
        report_kind=report_kind,
        report_version=report_version,
    )

    # 3) 裸布尔伪造（对象已定位到 scientific_qc）→ 守卫拒绝，不改状态 ────────
    forged_id = f"{object_id}_forged"
    _drive_to_scientific_qc(
        executor,
        object_id=forged_id,
        project_id=PROJECT_ID,
        run_id=run_id,
        request_counter=70,
    )
    assert executor.state()["report_evidence"][forged_id] == "scientific_qc"
    forged_event = executor.submit(
        TransitionRequest(
            schema_version="1.0",
            request_id=f"sqc:forged:{report_kind.value}",
            project_id=PROJECT_ID,
            run_id=run_id,
            family="report_evidence",
            object_id=forged_id,
            from_state="scientific_qc",
            to_state="snapshot_locked",
            trigger="isolated_qc_accepted",
            evidence={"isolated_qc_accepted": True},
            actor_id="forged-actor",
            occurred_at=now(),
        )
    )
    assert forged_event.event_type == "graph.transition.rejected"
    assert forged_event.payload["reason"] == "guard_failed"
    assert forged_event.payload["guard_id"] == "g_report_scientific_qc_snapshot_locked"
    assert forged_event.payload["guard_reason"].startswith(
        "missing_evidence:qc_verdict_id"
    )
    assert executor.state()["report_evidence"][forged_id] == "scientific_qc"
    assert_no_downstream_artifacts(
        workspace_root,
        project_id=PROJECT_ID,
        report_kind=report_kind,
        report_version=report_version,
    )

    # 3b) 非 SHA 摘要授权（对象已定位）→ 守卫拒绝，不改状态 ──────────────────
    non_sha_id = f"{object_id}_nonsha"
    _drive_to_scientific_qc(
        executor,
        object_id=non_sha_id,
        project_id=PROJECT_ID,
        run_id=run_id,
        request_counter=80,
    )
    non_sha_evidence = {
        "isolated_qc_accepted": True,
        "qc_verdict_id": "v1",
        "qc_verdict_digest": "not-a-digest",
        "qc_candidate_snapshot_id": "snap-1",
        "qc_candidate_content_digest": "b" * 64,
        "qc_review_input_digest": "c" * 64,
        "qc_report_object_id": non_sha_id,
        "qc_context_digest": "d" * 64,
        "qc_authorization_id": f"auth-nonsha-{report_kind.value}",
    }
    non_sha_event = executor.submit(
        TransitionRequest(
            schema_version="1.0",
            request_id=f"sqc:nonsha:{report_kind.value}",
            project_id=PROJECT_ID,
            run_id=run_id,
            family="report_evidence",
            object_id=non_sha_id,
            from_state="scientific_qc",
            to_state="snapshot_locked",
            trigger="isolated_qc_accepted",
            evidence=non_sha_evidence,
            actor_id="forged-actor",
            occurred_at=now(),
        )
    )
    assert non_sha_event.event_type == "graph.transition.rejected"
    assert non_sha_event.payload["reason"] == "guard_failed"
    assert non_sha_event.payload["guard_reason"].startswith(
        "guard_not_satisfied:qc_verdict_digest"
    )
    assert executor.state()["report_evidence"][non_sha_id] == "scientific_qc"

    # 3c) 错对象授权（对象已定位）→ 守卫拒绝，不改状态 ───────────────────────
    wrong_obj_id = f"{object_id}_wrongobj"
    _drive_to_scientific_qc(
        executor,
        object_id=wrong_obj_id,
        project_id=PROJECT_ID,
        run_id=run_id,
        request_counter=90,
    )
    wrong_obj_evidence = {
        "isolated_qc_accepted": True,
        "qc_verdict_id": "v1",
        "qc_verdict_digest": "a" * 64,
        "qc_candidate_snapshot_id": "snap-1",
        "qc_candidate_content_digest": "b" * 64,
        "qc_review_input_digest": "c" * 64,
        "qc_report_object_id": "report_OTHER",
        "qc_context_digest": "d" * 64,
        "qc_authorization_id": f"auth-wrongobj-{report_kind.value}",
    }
    wrong_obj_event = executor.submit(
        TransitionRequest(
            schema_version="1.0",
            request_id=f"sqc:wrongobj:{report_kind.value}",
            project_id=PROJECT_ID,
            run_id=run_id,
            family="report_evidence",
            object_id=wrong_obj_id,
            from_state="scientific_qc",
            to_state="snapshot_locked",
            trigger="isolated_qc_accepted",
            evidence=wrong_obj_evidence,
            actor_id="forged-actor",
            occurred_at=now(),
        )
    )
    assert wrong_obj_event.event_type == "graph.transition.rejected"
    assert wrong_obj_event.payload["reason"] == "guard_failed"
    assert wrong_obj_event.payload["guard_reason"].startswith(
        "scope_mismatch:object:qc_report_object_id"
    )
    assert executor.state()["report_evidence"][wrong_obj_id] == "scientific_qc"

    # 3d) 已穷尽迁移缺穷尽记录摘要（对象已定位）→ 守卫拒绝，不改状态 ────────
    no_exh_id = f"{object_id}_noexh"
    _drive_to_scientific_qc(
        executor,
        object_id=no_exh_id,
        project_id=PROJECT_ID,
        run_id=run_id,
        request_counter=100,
    )
    no_exh_event = executor.submit(
        TransitionRequest(
            schema_version="1.0",
            request_id=f"sqc:noexh:{report_kind.value}",
            project_id=PROJECT_ID,
            run_id=run_id,
            family="report_evidence",
            object_id=no_exh_id,
            from_state="scientific_qc",
            to_state="evidence_blocked",
            trigger="qc_veto_unfixable_exhausted",
            evidence={
                "qc_veto": True,
                "qc_veto_unfixable": True,
                "recovery_exhausted": True,
                "independent_review_exhausted": True,
                "no_continuable_user_action": True,
                "qc_verdict_id": "v1",
                "qc_verdict_digest": "a" * 64,
                "qc_candidate_snapshot_id": "snap-1",
                "qc_candidate_content_digest": "b" * 64,
                "qc_review_input_digest": "c" * 64,
                "qc_report_object_id": no_exh_id,
                "qc_context_digest": "d" * 64,
                "qc_authorization_id": f"auth-noexh-{report_kind.value}",
            },
            actor_id="forged-actor",
            occurred_at=now(),
        )
    )
    assert no_exh_event.event_type == "graph.transition.rejected"
    assert no_exh_event.payload["reason"] == "guard_failed"
    assert no_exh_event.payload["guard_reason"].startswith(
        "missing_evidence:qc_exhaustion_record_digest"
    )
    assert executor.state()["report_evidence"][no_exh_id] == "scientific_qc"

    # 3e) 可修复否决携带穷尽记录摘要（对象已定位）→ 守卫拒绝 ─────────────────
    rec_exh_id = f"{object_id}_recexh"
    _drive_to_scientific_qc(
        executor,
        object_id=rec_exh_id,
        project_id=PROJECT_ID,
        run_id=run_id,
        request_counter=110,
    )
    rec_exh_event = executor.submit(
        TransitionRequest(
            schema_version="1.0",
            request_id=f"sqc:recexh:{report_kind.value}",
            project_id=PROJECT_ID,
            run_id=run_id,
            family="report_evidence",
            object_id=rec_exh_id,
            from_state="scientific_qc",
            to_state="recovering",
            trigger="qc_veto_fixable",
            evidence={
                "qc_veto": True,
                "qc_veto_fixable": True,
                "qc_verdict_id": "v1",
                "qc_verdict_digest": "a" * 64,
                "qc_candidate_snapshot_id": "snap-1",
                "qc_candidate_content_digest": "b" * 64,
                "qc_review_input_digest": "c" * 64,
                "qc_report_object_id": rec_exh_id,
                "qc_context_digest": "d" * 64,
                "qc_exhaustion_record_digest": "e" * 64,
                "qc_authorization_id": f"auth-recexh-{report_kind.value}",
            },
            actor_id="forged-actor",
            occurred_at=now(),
        )
    )
    assert rec_exh_event.event_type == "graph.transition.rejected"
    assert rec_exh_event.payload["reason"] == "guard_failed"
    assert rec_exh_event.payload["guard_reason"].startswith(
        "guard_not_satisfied:qc_exhaustion_record_digest"
    )
    assert executor.state()["report_evidence"][rec_exh_id] == "scientific_qc"


def _valid_exhaustion(report_kind: ReportKind) -> DoubleExhaustionRecord:
    """构造绑定同一项目/报告类型的双重穷尽记录。"""
    return DoubleExhaustionRecord(
        project_id=PROJECT_ID,
        report_kind=report_kind,
        gaps=(gap_exhaustion(gap_id="gap-sqc"),),
        created_at=now(),
    )
