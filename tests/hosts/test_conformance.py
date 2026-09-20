"""Task 9.4 HA05–HA08：三宿主语义一致性精确节点。

四个节点各自对真实 API 独立建模：同一 fixture 的语义状态完全一致、
选择性能力阻断逐宿主成立、环境恢复逐宿主重排相同节点、手工收件箱与
部分交付逐宿主语义等价。宿主运行身份不参与任何比较。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ci_workflow.application.capability_preflight import (
    StaticCapabilityProbe,
    plan_environment_recovery,
)
from ci_workflow.hosts.base import HostAdapter
from ci_workflow.hosts.codex import CodexHostAdapter
from ci_workflow.hosts.hermes import HermesHostAdapter
from ci_workflow.hosts.omp import OmpHostAdapter
from tests.hosts._helpers import (
    append_project_state,
    make_project,
    selection,
    sha256_of,
    write_accepted_html_site,
    write_download_request,
)

_HOST_CLASSES = (CodexHostAdapter, HermesHostAdapter, OmpHostAdapter)
_HOST_LABELS = ("codex", "hermes", "omp")


def _adapters(probe: StaticCapabilityProbe) -> tuple[HostAdapter, ...]:
    return tuple(host_class(probe=probe) for host_class in _HOST_CLASSES)


# ── HA05：三宿主语义一致 ────────────────────────────────────────────────────


def test_three_hosts_emit_identical_semantic_state_for_same_fixture(
    tmp_path: Path,
) -> None:
    probe = StaticCapabilityProbe()
    simple = make_project(tmp_path / "simple")
    rich = make_project(tmp_path / "rich", reports=("A", "B"))
    append_project_state(rich, from_state="running", to_state="awaiting_user")
    write_download_request(rich)
    append_project_state(rich, from_state="awaiting_user", to_state="partially_delivered")
    write_accepted_html_site(rich, "A")

    for project, reports in ((simple, ("A",)), (rich, ("A", "B"))):
        chosen = selection(reports=reports)
        receipts = [
            adapter.build_semantic_receipt(project_root=project, selection=chosen)
            for adapter in _adapters(probe)
        ]
        assert receipts[0] == receipts[1] == receipts[2]
    # 语义回执序列化后不含任何宿主运行身份标记。
    final = _adapters(probe)[0].build_semantic_receipt(
        project_root=rich, selection=selection(reports=("A", "B"))
    )
    serialized = final.model_dump_json()
    for label in _HOST_LABELS:
        assert label not in serialized


# ── HA06：HTML-only 能力边界 ────────────────────────────────────────────────


def test_capability_preflight_rejects_future_formats_and_covers_html_only(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="未知能力"):
        StaticCapabilityProbe(blocked=("native_pdf",))

    project = make_project(tmp_path)
    for adapter in _adapters(StaticCapabilityProbe()):
        matrix = adapter.capability_matrix(
            project_root=project, selection=selection(outputs=("html",))
        )
        assert matrix.overall_state == "ready"
        assert tuple((item.report, item.output) for item in matrix.deliveries) == (("A", "html"),)
        assert matrix.capability("independent_context").state == "ready"

    with pytest.raises(ValueError):
        selection(outputs=("html", "pptx"))


# ── HA07：环境恢复 ──────────────────────────────────────────────────────────


def test_environment_recovery_requeues_same_failed_nodes_on_each_host(
    tmp_path: Path,
) -> None:
    project = make_project(tmp_path, reports=("A", "B"))
    chosen = selection(reports=("A", "B"))
    expected_nodes = (
        "research:A",
        "analyze:A",
        "snapshot:A",
        "render:A:html",
        "verify:A:html",
        "research:B",
        "analyze:B",
        "snapshot:B",
        "render:B:html",
        "verify:B:html",
    )
    for host_class in _HOST_CLASSES:
        broken = host_class(probe=StaticCapabilityProbe(blocked=("http_network",)))
        previous = broken.capability_matrix(project_root=project, selection=chosen)
        assert previous.overall_state == "blocked"
        repaired = host_class(probe=StaticCapabilityProbe())
        current = repaired.capability_matrix(project_root=project, selection=chosen)
        assert current.overall_state == "ready"
        plan = plan_environment_recovery(previous, current)
        assert plan.repaired_capability_ids == ("http_network",)
        assert plan.requeue_node_ids == expected_nodes
        receipt = repaired.build_semantic_receipt(
            project_root=project, selection=chosen, previous_matrix=previous
        )
        assert receipt.blocking_and_recovery.recovery_requeue_node_ids == expected_nodes
    # 公共合同：环境恢复比较必须绑定同一宿主。
    cross_host_previous = CodexHostAdapter(
        probe=StaticCapabilityProbe(blocked=("http_network",))
    ).capability_matrix(project_root=project, selection=chosen)
    cross_host_current = HermesHostAdapter(
        probe=StaticCapabilityProbe()
    ).capability_matrix(project_root=project, selection=chosen)
    with pytest.raises(ValueError, match="同一宿主"):
        plan_environment_recovery(cross_host_previous, cross_host_current)


# ── HA08：手工收件箱与部分交付等价 ────────────────────────────────────────


def test_manual_inbox_and_partial_delivery_are_equivalent_on_each_host(
    tmp_path: Path,
) -> None:
    probe = StaticCapabilityProbe()
    waiting_project = make_project(tmp_path / "waiting")
    append_project_state(
        waiting_project, from_state="running", to_state="awaiting_user"
    )
    request = write_download_request(waiting_project)
    partial_project = make_project(tmp_path / "partial", reports=("A", "B"))
    append_project_state(
        partial_project, from_state="running", to_state="partially_delivered"
    )
    site = write_accepted_html_site(partial_project, "A")

    waiting_receipts = [
        adapter.build_semantic_receipt(
            project_root=waiting_project, selection=selection()
        )
        for adapter in _adapters(probe)
    ]
    partial_receipts = [
        adapter.build_semantic_receipt(
            project_root=partial_project, selection=selection(reports=("A", "B"))
        )
        for adapter in _adapters(probe)
    ]

    for receipt in waiting_receipts:
        assert receipt.canonical_state == "awaiting_user"
        assert receipt.blocking_and_recovery.failure_class == "awaiting_user_materials"
        assert receipt.partial_delivery is None
        inbox = receipt.blocking_and_recovery.manual_inbox_pending
        assert len(inbox) == 1
        assert inbox[0].request_id == request["request_id"]
        assert inbox[0].state_zh == "等待您放入文件"  # 不暴露后端状态词
        assert receipt.primary_status_zh == "需要您补充关键资料后才能继续。"
    for receipt in partial_receipts:
        assert receipt.canonical_state == "partially_delivered"
        assert receipt.partial_delivery is not None
        assert [
            (item.report, item.output)
            for item in receipt.partial_delivery.delivered
        ] == [("A", "html")]
        assert [
            (item.report, item.output) for item in receipt.partial_delivery.pending
        ] == [("B", "html")]
        assert receipt.artifacts[0].entry_relative_path == "reports/A/v1/html/index.html"
        assert receipt.artifacts[0].entry_sha256 == sha256_of(site)

    assert waiting_receipts[0] == waiting_receipts[1] == waiting_receipts[2]
    assert partial_receipts[0] == partial_receipts[1] == partial_receipts[2]
