"""Task 3.6 EX01–EX02：`project run` 从已保存项目合同启动真实类型化图并支持精确恢复。

- EX01：最小项目（reports=A、outputs=html）经 RunService 从 `project.yaml` 加载当前
  合同，持久化新 run_id、事件流、检查点和当前运行清单；共享阶段（intake/preflight）
  真实完成。未提供宇宙输入（不传 run_context）时证据管线保持待定，本次运行以
  `running`/exit 0 结束，不宣称完成。
- EX02：`--resume` 是唯一允许复用历史节点的入口；非 resume 的已使用项目失败关闭。
  运行 1 以缺失的规范宇宙输入（evidence/library/universe.json）失败并落检查点/清单；
  运行 2 在规范路径创建有效输入后无调用方路径 resume，自动发现并绑定输入，
  universe 及其下游在运行 2 真实执行并完成阻断（exit 4）；运行 3 未变化输入 resume
  只记录当前运行复用/终态决策事件与阻断产物引用，不重提终态迁移、不产生新完成事件；
  运行 4 证据内容变化时拒绝继续并给出显式重新打开的中文指引。
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, cast

import pytest

from ci_workflow.application.capability_preflight import StaticCapabilityProbe
from ci_workflow.application.project_service import (
    create_project_workspace,
    verify_project_workspace,
)
from ci_workflow.application.run_service import (
    ContractConfigError,
    RunContext,
    RunError,
    run_project,
    validate_run_manifest,
)
from ci_workflow.application.yaozh_access import answer_yaozh_access
from ci_workflow.domain.contracts import ProjectContract, create_project_contract
from ci_workflow.storage.event_store import EventStore


def _run_ready_project(project_root: Path, **kwargs: Any) -> Any:
    """Project-run tests declare their deterministic host capabilities explicitly."""
    return run_project(
        project_root,
        capability_probe=StaticCapabilityProbe(),
        **kwargs,
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _create_minimal_project(tmp_path: Path) -> tuple[Path, ProjectContract]:
    contract = create_project_contract(
        indication="非小细胞肺癌",
        reports=["A"],
        outputs=["html"],
    )
    project_root = create_project_workspace(tmp_path / "项目", contract)
    return project_root, contract


def _load_manifest(project_root: Path) -> dict[str, Any]:
    manifest_path = project_root / "manifests" / "current_run.json"
    assert manifest_path.is_file()
    return cast(dict[str, Any], json.loads(manifest_path.read_text(encoding="utf-8")))


def test_project_run_dispatches_typed_graph_from_saved_project_contract(
    tmp_path: Path,
) -> None:
    """EX01：正常项目从最小输入合同启动真实图并持久化本次运行身份。"""
    project_root, contract = _create_minimal_project(tmp_path)

    result = _run_ready_project(project_root)

    # RunResult 字段：新 run 身份 + 已保存合同绑定
    assert result.run_id
    assert result.project_id == contract.project_id
    assert result.contract_version == 1
    assert result.outcome == "running"
    assert result.exit_code == 0
    assert result.node_summary.get("intake") == "completed"
    assert result.node_summary.get("preflight") == "completed"
    assert result.node_summary.get("universe") == "awaiting_source_research"
    work_item = json.loads(
        (project_root / "state/work-items/source-research.json").read_text(encoding="utf-8")
    )
    assert work_item["state"] == "awaiting_host_research"
    assert work_item["package_target"]["audit_path"] == ("evidence/library/research-package.json")
    assert work_item["package_target"]["report_payload_paths"] == {
        "A": "evidence/library/a-research-package.json"
    }
    assert {route["route_id"] for route in work_item["routes"]} >= {
        "global-baseline",
        "china-baseline",
        "reverse-alias",
        "reverse-target",
        "reverse-company",
        "reverse-trial",
        "report-a-evidence",
    }

    # 事件流非空且全部属于本次新运行身份
    events = EventStore(project_root).read_all()
    assert events
    assert {event.run_id for event in events} == {result.run_id}

    # 共享阶段节点完成：intake/preflight（scope=shared，report_kind 为空）
    completed = {
        (event.payload["node_id"], event.payload.get("report_kind"))
        for event in events
        if event.event_type == "graph.node.completed"
    }
    assert ("intake", None) in completed
    assert ("preflight", None) in completed

    # 检查点与当前运行清单已持久化并绑定 run_id
    checkpoints = list((project_root / "state" / "checkpoints").glob("*.json"))
    assert checkpoints
    manifest = _load_manifest(project_root)
    assert manifest["run_id"] == result.run_id

    # 运行后项目工作区仍可核验（合同未漂移），当前运行清单可重新打开校验
    verification = verify_project_workspace(project_root)
    assert verification.contract.project_id == contract.project_id
    validated = validate_run_manifest(project_root)
    assert isinstance(validated, dict)
    assert validated.get("run_id") == result.run_id


def test_source_research_work_item_refreshes_after_once_only_yaozh_answer(
    tmp_path: Path,
) -> None:
    project_root, _contract = _create_minimal_project(tmp_path)

    first = _run_ready_project(project_root)
    assert first.outcome == "running"
    before = json.loads(
        (project_root / "state/work-items/source-research.json").read_text(encoding="utf-8")
    )
    assert before["yaozh_access"]["state"] == "answer_required_once"

    answer_yaozh_access(project_root, "available")
    resumed = _run_ready_project(project_root, resume=True)
    assert resumed.outcome == "running"
    after = json.loads(
        (project_root / "state/work-items/source-research.json").read_text(encoding="utf-8")
    )
    assert after["yaozh_access"]["state"] == "route_enabled"
    yaozh_route = next(
        route for route in after["routes"] if route["route_id"] == "yaozh-optional-browser"
    )
    assert yaozh_route["required"] is False


def test_project_resume_discovers_agent_prepared_report_data_and_binds_current_input(
    tmp_path: Path,
) -> None:
    """宿主 Agent 完成来源研究后把规范数据包放入项目，默认执行器可恢复生成。"""
    contract = create_project_contract(indication="特应性皮炎", reports=["A"], outputs=["html"])
    project_root = create_project_workspace(tmp_path / "项目", contract)

    first = _run_ready_project(project_root)
    assert first.outcome == "running"

    source = (
        Path(__file__).resolve().parents[2]
        / "fixtures/synthetic/a-complete/inputs/report-data.json"
    )
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["report_version"] = "v1"
    canonical = project_root / "evidence/library/report-data.json"
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    second = _run_ready_project(project_root, resume=True)
    assert second.outcome == "completed"
    manifest = _load_manifest(project_root)
    assert manifest["run_id"] == second.run_id
    assert manifest["input_hashes"] == {
        "evidence/library/report-data.json": _sha256_file(canonical)
    }
    assert (project_root / "reports/A/v1/html/overview.html").is_file()
    assert validate_run_manifest(project_root)["run_id"] == second.run_id


_FIXTURE_UNIVERSE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "synthetic"
    / "no-draft-a-empty"
    / "inputs"
    / "universe.json"
)


def test_project_run_resume_requeues_only_interrupted_or_failed_nodes_and_downstream(
    tmp_path: Path,
) -> None:
    """EX02：resume 语义——只有 resume=True 复用历史节点；非 resume 的已使用
    项目失败关闭；resume 从持久化事件/检查点派生真值。

    运行 1 以缺失的规范宇宙输入（evidence/library/universe.json）失败并落检查点/
    清单；运行 2 在规范路径创建有效输入后无调用方路径 resume，自动发现并绑定，
    universe 及其下游在运行 2 真实执行并完成阻断（evidence_blocked/exit 4）；
    运行 3 未变化输入 resume：只记录当前运行节点复用事件、终态决策事件与阻断
    产物引用（reused_artifacts），不重提终态迁移、不产生新完成事件；
    运行 4 证据解析内容变化：拒绝继续并给出显式重新打开的中文指引。
    """
    project_root, contract = _create_minimal_project(tmp_path)
    canonical_input = project_root / "evidence" / "library" / "universe.json"
    run_context = RunContext(
        project_root=project_root,
        contract=contract,
        universe_input_path=canonical_input,
    )

    # 运行 1：universe 节点因缺少规范输入失败（exit 2），检查点与清单已持久化
    first = _run_ready_project(project_root, run_context=run_context)
    assert first.run_id
    assert first.outcome == "failed"
    assert first.exit_code == 2
    assert first.node_summary.get("universe") == "failed"
    first_manifest_bytes = (project_root / "manifests" / "current_run.json").read_bytes()
    assert list((project_root / "state" / "checkpoints").glob(f"{first.run_id}--*.json"))

    # 运行 2（resume）：规范路径创建有效输入；无调用方路径 → 自动发现并绑定
    canonical_input.parent.mkdir(parents=True, exist_ok=True)
    canonical_input.write_bytes(_FIXTURE_UNIVERSE.read_bytes())
    resumed = _run_ready_project(project_root, resume=True)
    assert resumed.run_id != first.run_id
    assert resumed.outcome == "evidence_blocked"
    assert resumed.exit_code == 4
    assert resumed.node_summary.get("intake") == "reused"
    assert resumed.node_summary.get("preflight") == "completed"
    assert resumed.node_summary.get("universe") == "completed"
    assert resumed.node_summary.get("gate:A") == "completed"
    assert resumed.node_summary.get("recovery:A") == "completed"
    events = EventStore(project_root).read_all()
    # 运行 1 的陈旧失败不污染运行 2：universe/gate 完成事件属于运行 2
    universe_runs = {
        event.run_id
        for event in events
        if event.event_type == "graph.node.completed" and event.payload["node_id"] == "universe"
    }
    assert universe_runs == {resumed.run_id}
    gate_runs = {
        event.run_id
        for event in events
        if event.event_type == "graph.node.completed" and event.payload["node_id"] == "gate"
    }
    assert gate_runs == {resumed.run_id}
    intake_runs = {
        event.run_id
        for event in events
        if event.event_type == "graph.node.completed" and event.payload["node_id"] == "intake"
    }
    preflight_runs = {
        event.run_id
        for event in events
        if event.event_type == "graph.node.completed" and event.payload["node_id"] == "preflight"
    }
    assert intake_runs == {first.run_id}
    assert preflight_runs == {first.run_id, resumed.run_id}
    # 复用记录携带运行 1 的 run_id
    reused_by_node = {item["node_id"]: item for item in resumed.reused}
    assert set(reused_by_node) == {"intake"}
    assert reused_by_node["intake"]["run_id"] == first.run_id
    # 项目族一致性：运行 1 bootstrap 后运行 2 在当前运行内重新确立项目对象，
    # 并经声明迁移 running -> blocked（不依赖 bootstrap 与阻断同运行）
    project_running_transitions = [
        event
        for event in events
        if event.event_type == "graph.transition.accepted"
        and event.payload.get("family") == "project"
        and event.payload.get("to_state") == "running"
    ]
    assert len(project_running_transitions) == 2
    assert len([e for e in project_running_transitions if e.run_id == resumed.run_id]) == 1
    project_blocked = [
        event
        for event in events
        if event.event_type == "graph.transition.accepted"
        and event.payload.get("family") == "project"
        and event.payload.get("to_state") == "blocked"
    ]
    assert len(project_blocked) == 1
    assert project_blocked[0].run_id == resumed.run_id
    assert project_blocked[0].payload.get("from_state") == "running"
    # 运行 2 新产出：两个阻断文件进入 outputs；复用产物为空
    manifest2 = _load_manifest(project_root)
    assert manifest2["run_id"] == resumed.run_id
    assert {o["relative_path"] for o in manifest2["outputs"]} == {
        "blockers/A/v1/audit.json",
        "blockers/A/v1/audit.md",
    }
    assert manifest2["reused_artifacts"] == []

    # 运行 1 的清单恢复后仍可独立重新校验（事件绑定属于各自运行）
    manifest_path = project_root / "manifests" / "current_run.json"
    run2_manifest_bytes = manifest_path.read_bytes()
    manifest_path.write_bytes(first_manifest_bytes)
    assert validate_run_manifest(project_root).get("run_id") == first.run_id
    manifest_path.write_bytes(run2_manifest_bytes)
    assert validate_run_manifest(project_root).get("run_id") == resumed.run_id

    # 运行 3：全新上下文对象、未变化输入的 resume → 只记录当前运行证据
    ctx3 = RunContext(
        project_root=project_root,
        contract=contract,
        universe_input_path=canonical_input,
    )
    resumed3 = _run_ready_project(project_root, resume=True, run_context=ctx3)
    assert resumed3.run_id not in {first.run_id, resumed.run_id}
    assert resumed3.outcome == "evidence_blocked"
    assert resumed3.exit_code == 4
    for key in ("intake", "universe", "gate:A", "recovery:A"):
        assert resumed3.node_summary.get(key) == "reused"
    assert resumed3.node_summary.get("preflight") == "completed"
    events3 = EventStore(project_root).read_all()
    # 易变 preflight 重检，其余 4 个节点各一条当前运行复用事件
    reuse_events = [
        event
        for event in events3
        if event.event_type == "run.node.reused" and event.run_id == resumed3.run_id
    ]
    assert len(reuse_events) == 4
    universe_reuse = next(event for event in reuse_events if event.payload["node_id"] == "universe")
    assert universe_reuse.payload["source_run_id"] == resumed.run_id
    assert universe_reuse.payload["source_event_id"]
    assert universe_reuse.payload["source_input_digest"]
    assert universe_reuse.payload["source_completion_digest"]
    assert universe_reuse.payload["input_digest"]
    completed_run3 = [
        event.payload["node_id"]
        for event in events3
        if event.run_id == resumed3.run_id and event.event_type == "graph.node.completed"
    ]
    assert completed_run3 == ["preflight"]
    # 终态未变化 resume 不重复项目迁移（不隐式重新打开）
    assert not any(
        event.run_id == resumed3.run_id
        and event.event_type == "graph.transition.accepted"
        and event.payload.get("family") == "project"
        for event in events3
    )
    # 终态决策事件：唯一、决策来源为复用、绑定原决策与证据摘要
    terminal_events = [
        event
        for event in events3
        if event.event_type == "run.terminal_decision.recorded" and event.run_id == resumed3.run_id
    ]
    assert len(terminal_events) == 1
    terminal_payload = terminal_events[0].payload
    assert terminal_payload["report_kind"] == "A"
    assert terminal_payload["decision_source"] == "reused"
    assert terminal_payload["source_run_id"] == resumed.run_id
    assert terminal_payload["source_event_id"]
    assert terminal_payload["gate_input_digest"]
    assert {a["relative_path"] for a in terminal_payload["artifacts"]} == {
        "blockers/A/v1/audit.json",
        "blockers/A/v1/audit.md",
    }
    # 清单：无新产出，阻断文件作为复用产物引用（精确哈希/mtime）
    manifest3 = _load_manifest(project_root)
    assert manifest3["run_id"] == resumed3.run_id
    assert manifest3["outputs"] == []
    assert {a["relative_path"] for a in manifest3["reused_artifacts"]} == {
        "blockers/A/v1/audit.json",
        "blockers/A/v1/audit.md",
    }
    for artifact in manifest3["reused_artifacts"]:
        path = project_root / artifact["relative_path"]
        assert _sha256_file(path) == artifact["sha256"]
        assert path.stat().st_size == artifact["byte_size"]
        assert path.stat().st_mtime_ns == artifact["mtime_ns"]
    # 本次运行有当前检查点与事件计数（不靠旧状态冒充）
    assert manifest3["event_count"] > 0
    assert manifest3["checkpoint_id"]
    assert list((project_root / "state" / "checkpoints").glob(f"{resumed3.run_id}--*.json"))
    assert validate_run_manifest(project_root).get("run_id") == resumed3.run_id

    # 篡改复用阻断文件 → 重开校验失败关闭；恢复内容与精确 mtime 后可再校验
    audit_md = project_root / "blockers" / "A" / "v1" / "audit.md"
    original_stat = audit_md.stat()
    original_md = audit_md.read_bytes()
    audit_md.write_bytes(original_md + "<!-- 篡改 -->\n".encode())
    with pytest.raises(RunError, match="复用产物"):
        validate_run_manifest(project_root)
    audit_md.write_bytes(original_md)
    os.utime(
        audit_md,
        ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns),
    )
    assert validate_run_manifest(project_root).get("run_id") == resumed3.run_id

    # 运行 4：复用同一 RunContext 对象（ctx3）但宇宙证据解析内容变化
    # （evidence_id 变化 → 证据摘要变化）→ 不得信任缓存的 universe_evidence，
    # 必须重新从文件字节水合并在派发前失败关闭给出显式重新打开指引
    changed = json.loads(_FIXTURE_UNIVERSE.read_text(encoding="utf-8"))
    changed["evidence_id"] = "empty-a-no-draft-v2"
    canonical_input.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    events_before_run4 = len(EventStore(project_root).read_all())
    with pytest.raises(ContractConfigError, match="重新打开"):
        _run_ready_project(project_root, resume=True, run_context=ctx3)
    assert len(EventStore(project_root).read_all()) == events_before_run4
