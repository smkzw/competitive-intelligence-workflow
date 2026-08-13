"""Task 3.5 场景一：报告与格式独立渐进交付，项目为部分交付（唯一顶层节点）。

字面场景：A 证据已锁定（snapshot_locked）且 HTML delivery_ready；
B evidence_blocked；C 仍 collecting；A 的 PPTX 因 PPT Master 不可用而
format blocked。结果：A HTML 保持交付，PPTX 阻断不撤销 HTML，
B 不污染 A/C，项目为 partially_delivered 而非 complete/blocked。

期望数据全部写成独立字面场景：A/B/C 报告对象与 A:html/A:pptx 格式对象
经真实 GraphExecutor.submit() 声明迁移驱动；聚合条件由协调器从规范状态
机械计算，测试绝不向协调器传入任何结论布尔值。

本文件同时覆盖 P1 修正的精确重现场景：

- 合同拒绝重复可选格式 / 重复报告 / 非正整数版本（"banana"）；
- 无迁移候选的首次协调仍把不可变选择绑定持久化到 EventStore（归约器
  安全 no-op），同合同身份下放弃 PPTX 立即失败关闭；
- 版本序：v2 先绑定后，旧 v1 不能出现在其后。
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

_NOW = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
_PROJECT_ID = "p_35a"
_RUN_ID = "run_35a"


def _canonical_digest(value: object) -> str:
    encoded = (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
_PROJECT_OBJECT = "proj_1"


def test_reports_and_formats_progress_independently_with_partial_delivery(
    tmp_path: Path,
) -> None:
    """GT35-1：A HTML 交付、A PPTX 阻断、B 阻断、C 运行 → partially_delivered。"""
    from ci_workflow.graph.executor import GraphExecutor
    from ci_workflow.graph.recovery import (
        ContractDriftError,
        CoordinationError,
        DeliveryContract,
        PartialDeliveryCoordinator,
        format_object_id,
    )
    from ci_workflow.graph.state import report_scoped_key
    from ci_workflow.graph.types import TransitionRequest

    executor = GraphExecutor(tmp_path / "项目", run_id=_RUN_ID)
    coordinator = PartialDeliveryCoordinator(executor)
    contract = DeliveryContract(
        contract_id="contract_35a",
        contract_version=1,
        reports=("A", "B", "C"),
        optional_formats=("pptx",),
    )

    # ── P1-1：字面非法合同一律失败关闭 ────────────────────────────────────
    with pytest.raises(ValueError):
        DeliveryContract(
            contract_id="contract_35a", contract_version=1, reports=("A",),
            optional_formats=("pptx", "pptx"),
        )
    with pytest.raises(ValueError):
        DeliveryContract(
            contract_id="contract_35a", contract_version=1, reports=("A", "A"),
        )
    with pytest.raises(ValueError):
        DeliveryContract(
            contract_id="contract_35a", contract_version="banana", reports=("A",),
        )
    with pytest.raises(ValueError):
        DeliveryContract(
            contract_id="contract_35a", contract_version=0, reports=("A",),
        )
    with pytest.raises(ValueError):
        DeliveryContract(
            contract_id="contract_35a", contract_version=True, reports=("A",),
        )

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
                actor_id="pi_35a",
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
                actor_id="pi_35a",
                occurred_at=_NOW,
            )
        )
        assert event.event_type == "graph.transition.accepted", event.payload

    # 项目合同与预检 → running
    submit(
        family="project",
        object_id=_PROJECT_OBJECT,
        from_state=None,
        to_state="running",
        trigger="project_contract_and_preflight",
        evidence={"project_contract_established": True, "preflight_records_established": True},
        request_id="35a:project:create",
    )

    # ── P1-2：无迁移候选的首次协调仍持久化选择绑定（归约器安全 no-op）────
    from ci_workflow.graph.reducer import graph_reducer
    from ci_workflow.graph.state import initial_state

    quiet = coordinator.reconcile(contract, actor_id="pi_35a", occurred_at=_NOW)
    assert quiet.submitted is None
    assert quiet.note == "no_candidate"
    assert quiet.conditions.selected_objects_continuable is True
    assert quiet.conditions.no_deliverable_artifact is True
    bound_events = [
        event
        for event in executor.store.read_all()
        if event.event_type == "coordinator.selection_bound"
    ]
    assert len(bound_events) == 1
    bound = bound_events[0]
    assert bound.project_id == _PROJECT_ID
    assert bound.run_id == _RUN_ID
    assert bound.payload["contract_id"] == "contract_35a"
    assert bound.payload["contract_version"] == 1
    assert bound.payload["reports"] == ["A", "B", "C"]
    assert bound.payload["mandatory_html"] == "html"
    assert bound.payload["optional_formats"] == ["pptx"]
    assert bound.payload["selection_digest"]
    # 绑定事件是非图业务事件：归约器安全 no-op，不改写图状态
    assert graph_reducer(initial_state(), bound) == initial_state()
    state_after_bind = executor.state()
    assert state_after_bind["project"][_PROJECT_OBJECT] == "running"
    assert "coordinator" not in state_after_bind
    # 同合同身份下放弃 PPTX（尚无任何迁移事件）→ 失败关闭，不静默删除选择
    drifted = DeliveryContract(
        contract_id="contract_35a",
        contract_version=1,
        reports=("A", "B", "C"),
        optional_formats=(),
    )
    with pytest.raises(ContractDriftError):
        coordinator.reconcile(drifted, actor_id="pi_35a", occurred_at=_NOW)

    # ── P1-3 版本序：v2 先绑定后，旧 v1 不能出现在其后（独立项目根）──────
    order_root = tmp_path / "项目_版本序"
    order_executor = GraphExecutor(order_root, run_id="run_35e")
    order_coordinator = PartialDeliveryCoordinator(order_executor)
    order_event = order_executor.submit(
        TransitionRequest(
            schema_version="1.0",
            request_id="35e:project:create",
            project_id="p_35e",
            run_id="run_35e",
            family="project",
            object_id="proj_e",
            from_state=None,
            to_state="running",
            trigger="project_contract_and_preflight",
            evidence={"project_contract_established": True, "preflight_records_established": True},
            actor_id="pi_35a",
            occurred_at=_NOW,
        )
    )
    assert order_event.event_type == "graph.transition.accepted", order_event.payload
    v2_first = DeliveryContract(
        contract_id="contract_35e",
        contract_version=2,
        reports=("A",),
        optional_formats=("pdf",),
    )
    order_quiet = order_coordinator.reconcile(v2_first, actor_id="pi_35a", occurred_at=_NOW)
    assert order_quiet.submitted is None
    v1_late = DeliveryContract(
        contract_id="contract_35e",
        contract_version=1,
        reports=("A",),
        optional_formats=("pdf",),
    )
    with pytest.raises(ContractDriftError):
        order_coordinator.reconcile(v1_late, actor_id="pi_35a", occurred_at=_NOW)
    # 同一更高版本同选择重放：绑定不追加事件
    order_before = len(order_executor.store.read_all())
    order_coordinator.reconcile(v2_first, actor_id="pi_35a", occurred_at=_NOW)
    assert len(order_executor.store.read_all()) == order_before

    # ── 主场景：A 锁定 + HTML 交付；B 阻断；C 收集；A:pptx 阻断 ───────────
    a_path = (
        ("queued", "collecting", "candidate_scope_locked",
         {"candidate_scope_locked": True}, "35a:A:collecting"),
        ("collecting", "scientific_qc", "gate_deterministic_pass",
         {"gate_deterministic_pass": True, "candidate_snapshot_established": True}, "35a:A:qc"),
        ("scientific_qc", "snapshot_locked", "isolated_qc_accepted",
         {"isolated_qc_accepted": True,
          "qc_verdict_id": "qc-verdict-1",
          "qc_verdict_digest": "a" * 64,
          "qc_candidate_snapshot_id": "snap-1",
          "qc_candidate_content_digest": "b" * 64,
          "qc_review_input_digest": "c" * 64,
          "qc_report_object_id": "report_A",
          "qc_context_digest": "d" * 64}, "35a:A:locked"),
    )
    for from_state, to_state, trigger, evidence, request_id in a_path:
        submit(
            family="report_evidence", object_id="report_A",
            from_state=from_state, to_state=to_state,
            trigger=trigger, evidence=evidence, request_id=request_id,
        )

    b_path = (
        ("queued", "collecting", "candidate_scope_locked",
         {"candidate_scope_locked": True}, "35a:B:collecting"),
        ("collecting", "evidence_blocked", "recovery_exhausted_gap_remains",
         {"critical_units_still_failing": True, "recovery_exhausted": True,
          "independent_review_exhausted": True, "no_continuable_user_action": True},
         "35a:B:blocked"),
    )
    for from_state, to_state, trigger, evidence, request_id in b_path:
        submit(
            family="report_evidence", object_id="report_B",
            from_state=from_state, to_state=to_state,
            trigger=trigger, evidence=evidence, request_id=request_id,
        )

    submit(
        family="report_evidence", object_id="report_C",
        from_state="queued", to_state="collecting",
        trigger="candidate_scope_locked",
        evidence={"candidate_scope_locked": True},
        request_id="35a:C:collecting",
    )

    html_path = (
        ("queued", "generating", "snapshot_locked_ready",
         {"report_snapshot_locked": True}, "35a:A:html:generating"),
        ("generating", "quality_check", "artifact_built",
         {"artifact_built": True}, "35a:A:html:quality_check"),
        ("quality_check", "passed", "acceptance_records_complete",
         {"deterministic_check_recorded": True, "coverage_check_recorded": True,
          "real_render_check_recorded": True}, "35a:A:html:passed"),
        ("passed", "delivery_ready", "atomic_publish_manifest",
         {"atomic_publish_complete": True, "manifest_digest_recorded": True},
         "35a:A:html:delivery_ready"),
    )
    for from_state, to_state, trigger, evidence, request_id in html_path:
        submit(
            family="format_artifact", object_id=format_object_id("report_A", "html"),
            from_state=from_state, to_state=to_state,
            trigger=trigger, evidence=evidence, request_id=request_id,
        )

    pptx_path = (
        ("queued", "generating", "snapshot_locked_ready",
         {"report_snapshot_locked": True}, "35a:A:pptx:generating"),
        ("generating", "blocked", "format_recovery_exhausted",
         {"format_recovery_exhausted": True, "failure_evidence_saved": True},
         "35a:A:pptx:blocked"),
    )
    for from_state, to_state, trigger, evidence, request_id in pptx_path:
        submit(
            family="format_artifact", object_id=format_object_id("report_A", "pptx"),
            from_state=from_state, to_state=to_state,
            trigger=trigger, evidence=evidence, request_id=request_id,
        )

    executor.complete_node(
        "gate",
        outputs={"gate_passed": True, "failures": [], "evidence_digest": "d" * 64},
        input_digest="35a:gate:A", report_kind="A",
        project_id=_PROJECT_ID, actor_id="pi_35a", occurred_at=_NOW,
    )
    executor.complete_node(
        "gate",
        outputs={"gate_passed": False, "failures": ["unit_b"], "evidence_digest": "d" * 64},
        input_digest="35a:gate:B", report_kind="B",
        project_id=_PROJECT_ID, actor_id="pi_35a", occurred_at=_NOW,
    )

    # 协调器只接收合同，聚合条件由规范状态机械计算
    result = coordinator.reconcile(contract, actor_id="pi_35a", occurred_at=_NOW)
    assert result.submitted is not None
    assert result.submitted.event_type == "graph.transition.accepted"
    assert result.submitted.payload["to_state"] == "partially_delivered"

    state = executor.state()
    assert state["project"][_PROJECT_OBJECT] == "partially_delivered"
    assert state["report_evidence"]["report_A"] == "snapshot_locked"
    assert state["report_evidence"]["report_B"] == "evidence_blocked"
    assert state["report_evidence"]["report_C"] == "collecting"
    assert state["format_artifact"][format_object_id("report_A", "html")] == "delivery_ready"
    assert state["format_artifact"][format_object_id("report_A", "pptx")] == "blocked"
    assert state[report_scoped_key("gate", "A")]["gate_passed"] is True
    assert state[report_scoped_key("gate", "B")]["gate_passed"] is False

    conditions = result.conditions
    assert conditions.at_least_one_artifact_delivery_ready is True
    assert conditions.selected_objects_continuable is True
    assert conditions.no_deliverable_artifact is False
    assert conditions.at_least_one_terminal_blocked is True
    assert conditions.no_running_selected_object is False
    assert conditions.remaining_selected_exhausted_blocked is False
    assert conditions.all_selected_html_delivery_ready is False
    assert conditions.all_selected_optional_formats_delivery_ready is False
    assert {t.object_id for t in conditions.delivered_targets} == {
        format_object_id("report_A", "html")
    }
    assert {t.object_id for t in conditions.terminal_blocked_targets} == {
        format_object_id("report_A", "pptx"),
        format_object_id("report_B", "html"),
        format_object_id("report_B", "pptx"),
    }
    assert {t.object_id for t in conditions.continuable_targets} == {
        format_object_id("report_C", "html"),
        format_object_id("report_C", "pptx"),
    }

    # 证据事件携带合同绑定与机械计算的聚合键（调用者未传入结论布尔值）
    guard_evidence = result.submitted.payload["guard_evidence"]
    assert guard_evidence["contract_id"] == "contract_35a"
    assert guard_evidence["contract_version"] == 1
    assert guard_evidence["reports"] == ["A", "B", "C"]
    assert guard_evidence["mandatory_html"] == "html"
    assert guard_evidence["optional_formats"] == ["pptx"]
    assert guard_evidence["targets"] == {
        "A": "report_A", "B": "report_B", "C": "report_C",
    }
    assert guard_evidence["at_least_one_artifact_delivery_ready"] is True
    assert guard_evidence["selected_objects_continuable"] is True
    assert guard_evidence["all_selected_html_delivery_ready"] is False

    # 同合同同状态重放：不追加事件（绑定事件亦不重复）
    total_before = len(executor.store.read_all())
    replay = coordinator.reconcile(contract, actor_id="pi_35a", occurred_at=_NOW)
    assert replay.submitted is None
    assert len(executor.store.read_all()) == total_before
    assert executor.state()["project"][_PROJECT_OBJECT] == "partially_delivered"

    # 同合同身份下放弃 PPTX：失败关闭（改变选择必须使用更高的新合同版本）
    with pytest.raises(ContractDriftError):
        coordinator.reconcile(drifted, actor_id="pi_35a", occurred_at=_NOW)

    # 新合同版本是放弃 PPTX 的合法路径：矩阵不含 pptx，且 B/C HTML 未交付不能 complete
    new_version = DeliveryContract(
        contract_id="contract_35a",
        contract_version=2,
        reports=("A", "B", "C"),
        optional_formats=(),
    )
    result_v2 = coordinator.reconcile(new_version, actor_id="pi_35a", occurred_at=_NOW)
    assert result_v2.submitted is None
    assert all(t.fmt == "html" for t in result_v2.conditions.target_matrix)
    assert result_v2.conditions.all_selected_html_delivery_ready is False
    assert executor.state()["project"][_PROJECT_OBJECT] == "partially_delivered"

    # ── 伪造 selection_bound 事件：读路径失败关闭（独立项目根）────────────
    import hashlib
    import json

    from ci_workflow.domain.ids import stable_id
    from ci_workflow.graph.recovery import (
        SELECTION_BOUND_EVENT,
        CoordinatorEventContractError,
    )
    from ci_workflow.storage.event_store import WorkflowEvent

    def test_digest(
        *,
        contract_id: str,
        version: int,
        reports: list[str],
        formats: list[str],
    ) -> str:
        encoded = (
            json.dumps(
                {
                    "contract_id": contract_id,
                    "contract_version": version,
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

    def fresh_selection_root(
        name: str,
    ) -> tuple[GraphExecutor, PartialDeliveryCoordinator, DeliveryContract]:
        root = tmp_path / name
        root_executor = GraphExecutor(root, run_id="run_35g")
        root_coordinator = PartialDeliveryCoordinator(root_executor)
        root_contract = DeliveryContract(
            contract_id="contract_35g", contract_version=1,
            reports=("A", "B"), optional_formats=("pptx",),
        )
        created = root_executor.submit(
            TransitionRequest(
                schema_version="1.0",
                request_id="35g:project:create",
                project_id="p_35g",
                run_id="run_35g",
                family="project",
                object_id=_PROJECT_OBJECT,
                from_state=None,
                to_state="running",
                trigger="project_contract_and_preflight",
                evidence={
                    "project_contract_established": True,
                    "preflight_records_established": True,
                },
                actor_id="pi_35a",
                occurred_at=_NOW,
            )
        )
        assert created.event_type == "graph.transition.accepted", created.payload
        return root_executor, root_coordinator, root_contract

    def forged_selection_event(
        *,
        digest: str,
        event_id: str | None = None,
        idempotency_key: str | None = None,
        optional_formats: tuple[str, ...] = ("pptx",),
    ) -> WorkflowEvent:
        payload = {
            "contract_id": "contract_35g",
            "contract_version": 1,
            "reports": ["A", "B"],
            "mandatory_html": "html",
            "optional_formats": list(optional_formats),
        }
        payload["selection_digest"] = digest
        return WorkflowEvent(
            schema_version="1.0",
            event_id=event_id
            or stable_id(
                "coordinator-selection", "p_35g", "run_35g", "contract_35g", "1"
            ),
            project_id="p_35g",
            run_id="run_35g",
            event_type=SELECTION_BOUND_EVENT,
            occurred_at=_NOW,
            actor_id="forger",
            idempotency_key=idempotency_key
            or "coordinator.selection:run_35g:contract_35g:1",
            payload=payload,
        )

    # 合法绑定 + 重放 counter-case：先 reconcile 落库，重放不追加且不报错
    legal_executor, legal_coordinator, legal_contract = fresh_selection_root("项目_伪造_合法")
    first_legal = legal_coordinator.reconcile(
        legal_contract, actor_id="pi_35a", occurred_at=_NOW,
    )
    assert first_legal.submitted is None
    legal_bindings = [
        event for event in legal_executor.store.read_all()
        if event.event_type == SELECTION_BOUND_EVENT
    ]
    assert len(legal_bindings) == 1
    before = len(legal_executor.store.read_all())
    legal_coordinator.reconcile(legal_contract, actor_id="pi_35a", occurred_at=_NOW)
    assert len(legal_executor.store.read_all()) == before

    # 攻击 1：选择摘要伪造（载荷/身份正确、摘要漂移）→ 读路径失败关闭
    forger_executor, forger_coordinator, forger_contract = fresh_selection_root(
        "项目_伪造_摘要"
    )
    forger_executor.store.append(
        forged_selection_event(digest="f" * 64)
    )
    with pytest.raises(CoordinatorEventContractError):
        forger_coordinator.conditions(forger_contract)

    # 攻击 2：事件 ID/幂等键漂移（摘要正确、身份错配）→ 失败关闭
    drifted_executor, drifted_coordinator, drifted_contract = fresh_selection_root(
        "项目_伪造_身份"
    )
    drifted_executor.store.append(
        forged_selection_event(
            digest=test_digest(
                contract_id="contract_35g", version=1,
                reports=["A", "B"], formats=["pptx"],
            ),
            event_id="forged_selection_event_id",
        )
    )
    with pytest.raises(CoordinatorEventContractError):
        drifted_coordinator.conditions(drifted_contract)

    # 攻击 3：重复可选格式（合法摘要按重复列表自洽，重复校验先行拒绝）→ 失败关闭
    duplicate_executor, duplicate_coordinator, duplicate_contract = fresh_selection_root(
        "项目_伪造_重复格式"
    )
    duplicate_executor.store.append(
        forged_selection_event(
            digest=test_digest(
                contract_id="contract_35g", version=1,
                reports=["A", "B"], formats=["pptx", "pptx"],
            ),
            optional_formats=("pptx", "pptx"),
        )
    )
    with pytest.raises(CoordinatorEventContractError):
        duplicate_coordinator.conditions(duplicate_contract)

    # ── 过期合同版本：v2 绑定后 v1 全部公开方法（含只读 conditions）拒绝 ──
    # v1 曾绑定，但 v2 已是当前绑定版本：只读聚合条件拒绝
    with pytest.raises(ContractDriftError):
        coordinator.conditions(contract)
    # 未绑定版本不是权威版本：聚合条件拒绝
    unbound = DeliveryContract(
        contract_id="contract_35a", contract_version=3, reports=("A",),
        optional_formats=(),
    )
    with pytest.raises(CoordinationError):
        coordinator.conditions(unbound)
    # 同版本选择不一致也从 conditions() 失败关闭
    mismatched_v2 = DeliveryContract(
        contract_id="contract_35a", contract_version=2, reports=("A",),
        optional_formats=("pdf",),
    )
    with pytest.raises(ContractDriftError):
        coordinator.conditions(mismatched_v2)
    # 当前绑定版本 v2 的权威聚合条件可读，且不因 v1 曾绑定而 complete
    authoritative = coordinator.conditions(new_version)
    assert authoritative.all_selected_html_delivery_ready is False
    assert authoritative.all_selected_optional_formats_delivery_ready is True
    # v1 不能推进项目：v2 仍要求未交付格式时，reconcile(v1) 失败关闭，
    # 不能让项目在 v2 缺交付格式时用 v1 完成
    with pytest.raises(ContractDriftError):
        coordinator.reconcile(contract, actor_id="pi_35a", occurred_at=_NOW)
