"""Task 9.4 HA02：Codex 薄适配器真实行为建模。

最小输入、中断、恢复与产物四类映射全部经共享基类对公共设施的调用
发生；本测试独立驱动真实 API 并断言 Codex 运行身份不进入语义面。
"""

from __future__ import annotations

from pathlib import Path

from ci_workflow.application.capability_preflight import StaticCapabilityProbe
from ci_workflow.hosts.codex import CodexHostAdapter
from tests.hosts._helpers import (
    append_project_state,
    make_project,
    selection,
    sha256_of,
    write_accepted_html_site,
    write_download_request,
)


def test_codex_adapter_maps_minimal_input_interrupt_resume_and_artifacts(
    tmp_path: Path,
) -> None:
    adapter = CodexHostAdapter(probe=StaticCapabilityProbe())
    assert adapter.host == "codex"

    # ── 最小输入映射：项目合同（冻结真源）→ 规范化最小输入 ──────────────
    project = make_project(tmp_path, reports=("A", "B"), outputs=("html",))
    minimal = adapter.resolve_minimal_input(project)
    assert minimal.indication == "特应性皮炎"
    assert minimal.reports == ("A", "B")
    assert minimal.outputs == ("html",)  # 首版真实输出只允许站点式 HTML

    # ── 中断映射：等待用户材料（手工收件箱）与关键证据不足 ──────────────
    append_project_state(project, from_state="running", to_state="awaiting_user")
    request = write_download_request(project)
    waiting = adapter.build_semantic_receipt(
        project_root=project, selection=selection(reports=("A", "B"))
    )
    assert waiting.canonical_state == "awaiting_user"
    assert waiting.primary_status_zh == "需要您补充关键资料后才能继续。"
    assert waiting.blocking_and_recovery.failure_class == "awaiting_user_materials"
    pending_item = waiting.blocking_and_recovery.manual_inbox_pending[0]
    assert pending_item.title == request["title"]
    assert pending_item.state_zh == "等待您放入文件"

    append_project_state(project, from_state="awaiting_user", to_state="blocked")
    blocked = adapter.build_semantic_receipt(
        project_root=project, selection=selection(reports=("A", "B"))
    )
    assert blocked.canonical_state == "blocked"
    assert blocked.blocking_and_recovery.failure_class == "insufficient_key_evidence"
    assert blocked.artifacts == ()  # no-draft：关键证据不足时不生成草稿
    assert any("不生成草稿" in reason for reason in blocked.blocking_and_recovery.reasons_zh)

    # ── 恢复映射：同一项目 + 环境修复只重排失败能力下游 ──────────────────
    broken = CodexHostAdapter(probe=StaticCapabilityProbe(blocked=("http_network",)))
    previous = broken.capability_matrix(
        project_root=project, selection=selection(reports=("A", "B"))
    )
    assert previous.overall_state == "blocked"
    recovered = adapter.build_semantic_receipt(
        project_root=project,
        selection=selection(reports=("A", "B")),
        previous_matrix=previous,
    )
    assert recovered.blocking_and_recovery.recovery_requeue_node_ids == (
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
    plan = adapter.invocation_plan(project)
    assert plan.resume_command == (
        "ci-workflow",
        "project",
        "run",
        "--root",
        str(project),
        "--resume",
    )

    # ── 产物定位：部分交付时站点入口与内容摘要 ─────────────────────────
    append_project_state(
        project, from_state="blocked", to_state="partially_delivered"
    )
    site = write_accepted_html_site(project, "A")
    delivered = adapter.build_semantic_receipt(
        project_root=project, selection=selection(reports=("A", "B"))
    )
    assert delivered.canonical_state == "partially_delivered"
    assert delivered.partial_delivery is not None
    assert delivered.partial_delivery.delivered[0].entry_relative_path == (
        "reports/A/v1/html/index.html"
    )
    assert delivered.partial_delivery.delivered[0].entry_sha256 == sha256_of(site)
    assert [(item.report, item.output) for item in delivered.partial_delivery.pending] == [
        ("B", "html")
    ]

    # ── Codex 运行身份：候选定位与通道（不进入语义回执） ────────────────
    identity = adapter.run_identity()
    assert identity.host == "codex"
    assert identity.host_label_zh == "Codex"
    assert identity.session_channel == "codex-cli-session"
    assert (Path.home() / ".codex") in adapter.install_entry_candidates()
