"""Task 9.4 HA05–HA08：三宿主语义一致性与等价测试。

HA05：Codex/Hermes/OMP 对同一 fixture 产生相同语义状态、失败分类、
恢复请求和产物摘要（``HostSemanticReceipt`` 完全相等，运行身份不参与
比较）。
HA06：能力缺失只阻断依赖项；首版站点 HTML 不因 PDF、HTML-PPT、
PPT Master 或 Office 不可用而阻断。
HA07：环境恢复只重排失败能力及其下游，三宿主恢复计划等价。
HA08：手工收件箱与部分交付在三宿主语义等价；宿主私有会话丢失后仍可
从项目文件恢复同一语义。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.capability_preflight import (
    CapabilityProbe,
    CapabilitySelection,
    plan_environment_recovery,
)
from ci_workflow.application.project_service import (
    create_project_workspace,
    verify_project_workspace,
)
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.hosts.base import (
    HostAdapter,
    HostSemanticReceipt,
    MinimalUserInput,
)
from ci_workflow.hosts.codex import CodexHostAdapter
from ci_workflow.hosts.hermes import HermesHostAdapter
from ci_workflow.hosts.omp import OmpHostAdapter
from ci_workflow.storage.event_store import EventStore, WorkflowEvent

_HOST_CLASSES = (CodexHostAdapter, HermesHostAdapter, OmpHostAdapter)
_HOST_LABELS = ("codex", "hermes", "omp")


def _adapters(probe: CapabilityProbe) -> tuple[HostAdapter, ...]:
    return tuple(cls(probe=probe) for cls in _HOST_CLASSES)


def _selection(
    *,
    reports: tuple[str, ...] = ("A",),
    outputs: tuple[str, ...] = ("html",),
) -> CapabilitySelection:
    return CapabilitySelection(
        reports=reports,  # type: ignore[arg-type]
        outputs=outputs,  # type: ignore[arg-type]
        source_routes=("public-http", "public-browser"),
        needs_document_ingestion=True,
        needs_ocr=False,
    )


def _make_project(
    tmp_path: Path,
    *,
    reports: tuple[str, ...] = ("A",),
    outputs: tuple[str, ...] = ("html",),
) -> Path:
    contract = create_project_contract(
        indication="特应性皮炎",
        reports=list(reports),
        outputs=list(outputs),
    )
    return create_project_workspace(tmp_path / "项目", contract)


_STATE_EVENT_SEQUENCE = 0


def _append_project_state(
    project_root: Path,
    *,
    to_state: str,
    from_state: str = "running",
) -> None:
    global _STATE_EVENT_SEQUENCE
    _STATE_EVENT_SEQUENCE += 1
    contract = verify_project_workspace(project_root).contract
    EventStore(project_root).append(
        WorkflowEvent(
            schema_version="1.0",
            event_id=f"event-project-state-{_STATE_EVENT_SEQUENCE}",
            project_id=contract.project_id,
            run_id="run_001",
            event_type="graph.transition.accepted",
            occurred_at=datetime.now(UTC),
            actor_id="graph-executor",
            idempotency_key=f"transition:project:{_STATE_EVENT_SEQUENCE}",
            payload={
                "family": "project",
                "object_id": contract.project_id,
                "from_state": from_state,
                "to_state": to_state,
            },
        )
    )


def _write_download_request(
    project_root: Path, *, state: str = "awaiting_user"
) -> dict[str, Any]:
    record = {
        "schema_version": "1.0",
        "request_id": "dr-001",
        "title": "Allocetra 首个人体临床试验全文",
        "reason_zh": "登记摘要缺少主要终点数值，需要论文原文核对。",
        "inbox_directory": "evidence/manual-inbox/dr-001",
        "state": state,
    }
    path = project_root / "receipts" / "download_requests.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    return record


def _receipts(
    adapters: tuple[HostAdapter, ...], **kwargs: Any
) -> tuple[HostSemanticReceipt, ...]:
    return tuple(
        adapter.build_semantic_receipt(**kwargs) for adapter in adapters
    )


def _assert_contains_chinese(text: str) -> None:
    assert any("\u4e00" <= char <= "\u9fff" for char in text)


# ── HA05：三宿主语义一致 ────────────────────────────────────────────────────


def test_three_hosts_produce_identical_semantic_receipts(tmp_path: Path) -> None:
    from ci_workflow.application.capability_preflight import StaticCapabilityProbe

    project = _make_project(tmp_path)
    receipts = _receipts(
        _adapters(StaticCapabilityProbe()),
        project_root=project,
        selection=_selection(),
    )
    assert len(receipts) == 3
    assert receipts[0] == receipts[1] == receipts[2]
    receipt = receipts[0]
    assert receipt.schema_version == "1.0"
    assert receipt.canonical_state == "not_started"
    assert receipt.minimal_input.indication == "特应性皮炎"
    assert receipt.minimal_input.reports == ("A",)
    assert receipt.minimal_input.outputs == ("html",)
    assert receipt.capability_selection.overall_state == "ready"
    assert receipt.blocking_and_recovery.failure_class == "none"
    assert receipt.partial_delivery is None
    _assert_contains_chinese(receipt.primary_status_zh)


def test_three_hosts_agree_on_failure_classification_when_blocked(
    tmp_path: Path,
) -> None:
    from ci_workflow.application.capability_preflight import StaticCapabilityProbe

    project = _make_project(tmp_path)
    _append_project_state(project, from_state="running", to_state="blocked")
    receipts = _receipts(
        _adapters(StaticCapabilityProbe()),
        project_root=project,
        selection=_selection(),
    )
    assert receipts[0] == receipts[1] == receipts[2]
    receipt = receipts[0]
    assert receipt.canonical_state == "blocked"
    assert receipt.blocking_and_recovery.failure_class == "insufficient_key_evidence"
    assert receipt.artifacts == ()
    for message in receipt.blocking_and_recovery.reasons_zh:
        _assert_contains_chinese(message)
    for message in receipt.blocking_and_recovery.user_actions_zh:
        _assert_contains_chinese(message)


def test_host_specific_identity_does_not_leak_into_semantic_receipt(
    tmp_path: Path,
) -> None:
    from ci_workflow.application.capability_preflight import StaticCapabilityProbe

    project = _make_project(tmp_path)
    adapters = _adapters(StaticCapabilityProbe())
    identities = tuple(adapter.run_identity() for adapter in adapters)
    assert tuple(identity.host for identity in identities) == _HOST_LABELS
    receipts = _receipts(
        adapters,
        project_root=project,
        selection=_selection(),
    )
    dumped = tuple(receipt.model_dump_json() for receipt in receipts)
    for label in _HOST_LABELS:
        assert label not in dumped[0]
    for adapter in adapters:
        plan = adapter.invocation_plan(project)
        assert plan.host == adapter.host
        assert plan.create_command is None
        assert plan.run_command == (
            "ci-workflow",
            "project",
            "run",
            "--root",
            str(project),
        )
        assert plan.resume_command[-1] == "--resume"


def test_minimal_input_maps_to_shared_project_create_command(
    tmp_path: Path,
) -> None:
    from ci_workflow.application.capability_preflight import StaticCapabilityProbe

    project = tmp_path / "项目"
    minimal = MinimalUserInput(
        schema_version="1.0",
        reports=("A", "B"),
        indication="特应性皮炎",
        outputs=("html",),
    )
    commands = []
    for adapter in _adapters(StaticCapabilityProbe()):
        plan = adapter.invocation_plan(project, minimal_input=minimal)
        assert plan.create_command is not None
        commands.append(plan.create_command)
    assert commands[0] == commands[1] == commands[2]
    expected = (
        "ci-workflow",
        "project",
        "create",
        "--root",
        str(project),
        "--indication",
        "特应性皮炎",
        "--reports",
        "A,B",
        "--outputs",
        "html",
    )
    assert commands[0] == expected


# ── HA06：选择性能力阻断 ────────────────────────────────────────────────────


def test_missing_delivery_components_do_not_block_first_version_html(
    tmp_path: Path,
) -> None:
    from ci_workflow.application.capability_preflight import StaticCapabilityProbe

    project = _make_project(tmp_path)
    for removed in ("ppt_master", "office_renderer", "native_pdf", "html_ppt_runtime"):
        with pytest.raises(ValueError, match="未知能力"):
            StaticCapabilityProbe(blocked=(removed,))
    probe = StaticCapabilityProbe()
    html_only = _selection(outputs=("html",))
    for adapter in _adapters(probe):
        matrix = adapter.capability_matrix(project_root=project, selection=html_only)
        html_delivery = next(
            item for item in matrix.deliveries if item.output == "html"
        )
        assert html_delivery.state == "ready"
        assert matrix.overall_state == "ready"



def test_research_capability_block_is_shared_across_hosts(tmp_path: Path) -> None:
    from ci_workflow.application.capability_preflight import StaticCapabilityProbe

    project = _make_project(tmp_path)
    probe = StaticCapabilityProbe(blocked=("http_network",))
    receipts = _receipts(
        _adapters(probe),
        project_root=project,
        selection=_selection(),
    )
    assert receipts[0] == receipts[1] == receipts[2]
    research = receipts[0].capability_selection.research_states[0]
    assert research.state == "blocked"
    assert research.blocked_by == ("http_network",)
    delivery = receipts[0].capability_selection.delivery_states[0]
    assert delivery.state == "blocked"
    assert delivery.blocked_by == ("http_network",)


# ── HA07：环境恢复 ──────────────────────────────────────────────────────────


def test_environment_recovery_requeues_only_failed_capability_downstream(
    tmp_path: Path,
) -> None:
    from ci_workflow.application.capability_preflight import StaticCapabilityProbe

    project = _make_project(tmp_path, reports=("A", "B"))
    selection = _selection(reports=("A", "B"))
    broken_probe = StaticCapabilityProbe(blocked=("http_network",))
    repaired_probe = StaticCapabilityProbe()
    recovery_plans = []
    for host_class in _HOST_CLASSES:
        broken = host_class(probe=broken_probe)
        previous = broken.capability_matrix(project_root=project, selection=selection)
        assert previous.overall_state == "blocked"
        repaired = host_class(probe=repaired_probe)
        current = repaired.capability_matrix(project_root=project, selection=selection)
        assert current.overall_state == "ready"
        receipt = repaired.build_semantic_receipt(
            project_root=project,
            selection=selection,
            previous_matrix=previous,
        )
        recovery_plans.append(receipt.blocking_and_recovery.recovery_requeue_node_ids)
    assert recovery_plans[0] == recovery_plans[1] == recovery_plans[2]
    assert set(recovery_plans[0]) == {
        "research:A", "analyze:A", "snapshot:A", "render:A:html", "verify:A:html",
        "research:B", "analyze:B", "snapshot:B", "render:B:html", "verify:B:html",
    }


def test_environment_recovery_rejects_cross_host_comparison(
    tmp_path: Path,
) -> None:
    from ci_workflow.application.capability_preflight import StaticCapabilityProbe

    project = _make_project(tmp_path)
    selection = _selection()
    previous = CodexHostAdapter(
        probe=StaticCapabilityProbe(blocked=("http_network",))
    ).capability_matrix(project_root=project, selection=selection)
    current = HermesHostAdapter(
        probe=StaticCapabilityProbe()
    ).capability_matrix(project_root=project, selection=selection)
    with pytest.raises(ValueError, match="同一宿主"):
        plan_environment_recovery(previous, current)


# ── HA08：手工收件箱与部分交付等价 ─────────────────────────────────────────


def test_manual_inbox_pending_is_equivalent_across_hosts(tmp_path: Path) -> None:
    from ci_workflow.application.capability_preflight import StaticCapabilityProbe

    project = _make_project(tmp_path)
    _append_project_state(project, from_state="running", to_state="awaiting_user")
    record = _write_download_request(project, state="awaiting_user")
    receipts = _receipts(
        _adapters(StaticCapabilityProbe()),
        project_root=project,
        selection=_selection(),
    )
    assert receipts[0] == receipts[1] == receipts[2]
    receipt = receipts[0]
    assert receipt.canonical_state == "awaiting_user"
    assert receipt.primary_status_zh == "需要您补充关键资料后才能继续。"
    blocking = receipt.blocking_and_recovery
    assert blocking.failure_class == "awaiting_user_materials"
    assert len(blocking.manual_inbox_pending) == 1
    item = blocking.manual_inbox_pending[0]
    assert item.request_id == record["request_id"]
    assert item.title == record["title"]
    assert item.inbox_directory == record["inbox_directory"]
    assert item.state_zh == "等待您放入文件"
    _assert_contains_chinese(item.reason_zh)
    assert "awaiting_user" not in item.state_zh


def test_partial_delivery_is_equivalent_across_hosts(tmp_path: Path) -> None:
    from ci_workflow.application.capability_preflight import StaticCapabilityProbe

    project = _make_project(tmp_path, reports=("A", "B"))
    _append_project_state(
        project, from_state="running", to_state="partially_delivered"
    )
    from tests.hosts._helpers import write_accepted_html_site

    write_accepted_html_site(project, "A")
    receipts = _receipts(
        _adapters(StaticCapabilityProbe()),
        project_root=project,
        selection=_selection(reports=("A", "B")),
    )
    assert receipts[0] == receipts[1] == receipts[2]
    receipt = receipts[0]
    assert receipt.canonical_state == "partially_delivered"
    assert receipt.partial_delivery is not None
    delivered = [
        (item.report, item.output) for item in receipt.partial_delivery.delivered
    ]
    pending = [
        (item.report, item.output) for item in receipt.partial_delivery.pending
    ]
    assert delivered == [("A", "html")]
    assert pending == [("B", "html")]
    assert receipt.artifacts[0].entry_relative_path == "reports/A/v1/html/index.html"
    assert len(receipt.artifacts[0].entry_sha256) == 64
    _assert_contains_chinese(receipt.primary_status_zh)


def test_semantic_receipt_rebuilds_from_project_files_after_host_session_loss(
    tmp_path: Path,
) -> None:
    from ci_workflow.application.capability_preflight import StaticCapabilityProbe

    project = _make_project(tmp_path)
    _append_project_state(project, from_state="running", to_state="awaiting_user")
    _write_download_request(project)
    before = OmpHostAdapter(probe=StaticCapabilityProbe()).build_semantic_receipt(
        project_root=project, selection=_selection()
    )
    # 宿主私有会话丢失：全新适配器实例只依赖项目文件重建同一语义。
    after = OmpHostAdapter(probe=StaticCapabilityProbe()).build_semantic_receipt(
        project_root=project, selection=_selection()
    )
    assert before == after


def test_cli_preflight_matches_adapter_semantics_for_all_hosts(
    tmp_path: Path,
) -> None:
    """CLI ``capability preflight --host ...`` 与适配器共享同一公共语义。"""
    import os
    import subprocess
    import sys

    from ci_workflow.application.capability_preflight import (
        CapabilityMatrix,
        RuntimeCapabilityProbe,
    )

    ROOT = Path(__file__).resolve().parents[2]
    project = _make_project(tmp_path, reports=("A", "B"))
    capabilities = {
        capability_id: True
        for capability_id in (
            "project_file_io",
            "script_runtime",
            "http_network",
            "search_browser",
            "login_browser",
            "document_ingestion",
            "ocr",
            "browser_validation",
            "independent_context",
        )
    }
    env = {
        **os.environ,
        "CI_WORKFLOW_TEST_MODE": "1",
        "CI_WORKFLOW_CAPABILITY_OVERRIDES": json.dumps(capabilities),
    }
    os.environ["CI_WORKFLOW_TEST_MODE"] = "1"
    os.environ["CI_WORKFLOW_CAPABILITY_OVERRIDES"] = json.dumps(capabilities)
    try:
        for host_label in _HOST_LABELS:
            receipt_path = tmp_path / f"preflight-{host_label}.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ci_workflow",
                    "capability",
                    "preflight",
                    "--host",
                    host_label,
                    "--project",
                    str(project),
                    "--json",
                    str(receipt_path),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            assert result.returncode == 0, result.stderr
            cli_matrix = CapabilityMatrix.model_validate(
                json.loads(receipt_path.read_text(encoding="utf-8"))
            )
            adapter = next(
                candidate
                for candidate in _adapters(RuntimeCapabilityProbe())
                if candidate.host == host_label
            )
            adapter_matrix = adapter.capability_matrix(
                project_root=project, selection=_selection(reports=("A", "B"))
            )
            assert cli_matrix.model_dump(exclude={"host"}) == adapter_matrix.model_dump(
                exclude={"host"}
            )
    finally:
        os.environ.pop("CI_WORKFLOW_TEST_MODE", None)
        os.environ.pop("CI_WORKFLOW_CAPABILITY_OVERRIDES", None)


def test_host_layer_imports_only_public_modules() -> None:
    """权能边界（结构面）：宿主层只导入公共 preflight/事件/检查点与项目合同，
    不导入门槛评估、来源策略、事实/声明、快照、修订批准或渲染内部实现。"""
    import ast

    hosts_root = Path(__file__).resolve().parents[2] / "src" / "ci_workflow" / "hosts"
    allowed_roots = (
        "ci_workflow.application.capability_preflight",
        "ci_workflow.application.project_service",
        "ci_workflow.application.delivered_artifacts",
        "ci_workflow.storage.event_store",
        "ci_workflow.storage.checkpoint_store",
        "ci_workflow.hosts",
    )
    for module_path in hosts_root.glob("*.py"):
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported = node.module
                if imported.startswith("ci_workflow"):
                    assert imported.startswith(allowed_roots), (
                        f"{module_path.name} 越权导入 {imported}"
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("ci_workflow"), (
                        f"{module_path.name} 越权导入 {alias.name}"
                    )
