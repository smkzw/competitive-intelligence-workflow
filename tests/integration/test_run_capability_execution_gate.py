from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from ci_workflow.application.capability_preflight import (
    CapabilityPersistenceError,
    ProbeOutcome,
    RuntimeCapabilityProbe,
    StaticCapabilityProbe,
    load_persisted_capability_matrix,
    persist_capability_matrix,
    run_capability_preflight,
    selection_from_project,
)
from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.application.run_service import run_project
from ci_workflow.application.yaozh_access import answer_yaozh_access
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.storage.event_store import EventStore


def _project(tmp_path: Path) -> Path:
    contract = create_project_contract(
        indication="重度哮喘", reports=["A"], outputs=["html"]
    )
    return create_project_workspace(tmp_path / "项目", contract)


def test_required_research_capability_blocks_before_source_research(tmp_path: Path) -> None:
    project = _project(tmp_path)

    result = run_project(
        project,
        capability_probe=StaticCapabilityProbe(blocked=("independent_context",)),
    )

    assert result.outcome == "capability_blocked"
    assert result.exit_code == 5
    assert result.node_summary == {"intake": "completed", "preflight": "completed"}
    assert not (project / "state/work-items/source-research.json").exists()
    matrix = load_persisted_capability_matrix(project)
    assert matrix.capability("independent_context").state == "blocked"
    assert json.loads((project / "manifests/current_run.json").read_text())["outcome"] == (
        "capability_blocked"
    )
    assert "执行环境" in (project / "logs/status.md").read_text(encoding="utf-8")


def test_delivery_only_blocker_allows_research_to_start(tmp_path: Path) -> None:
    project = _project(tmp_path)

    result = run_project(
        project,
        capability_probe=StaticCapabilityProbe(blocked=("browser_validation",)),
    )

    assert result.outcome == "running"
    assert result.node_summary["universe"] == "awaiting_source_research"
    matrix = load_persisted_capability_matrix(project)
    assert matrix.research[0].state == "ready"
    assert matrix.deliveries[0].state == "blocked"


def test_delivery_only_blocker_prevents_existing_report_data_from_rendering(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    source = (
        Path(__file__).resolve().parents[2]
        / "fixtures/synthetic/a-complete/inputs/report-data.json"
    )
    target = project / "evidence/library/report-data.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["indication"] = "重度哮喘"
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = run_project(
        project,
        capability_probe=StaticCapabilityProbe(blocked=("browser_validation",)),
    )

    assert result.outcome == "capability_blocked"
    assert result.node_summary["format:A"] == "capability_blocked"
    assert not any((project / "reports/A").rglob("*"))
    manifest = json.loads((project / "manifests/current_run.json").read_text())
    assert manifest["report_states"] == {"A": "delivery_capability_blocked"}
    assert manifest["format_states"] == {"A": {"html": "capability_blocked"}}


def test_optional_yaozh_login_blocker_does_not_stop_core_run(tmp_path: Path) -> None:
    project = _project(tmp_path)
    answer_yaozh_access(project, "available")

    result = run_project(
        project,
        capability_probe=StaticCapabilityProbe(blocked=("login_browser",)),
    )

    assert result.outcome == "running"
    assert load_persisted_capability_matrix(project).overall_state == "ready"
    assert (project / "state/work-items/source-research.json").is_file()


class _CountingProbe:
    def __init__(self) -> None:
        self.calls = 0

    def check(self, capability_id: str, *, project_root: Path) -> ProbeOutcome:
        del project_root
        self.calls += 1
        return ProbeOutcome(available=True, detail="已确认可用", user_action="无需处理")


def test_resume_rechecks_runtime_capabilities_instead_of_reusing_preflight(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    probe = _CountingProbe()

    first = run_project(project, capability_probe=probe)
    calls_after_first = probe.calls
    second = run_project(project, resume=True, capability_probe=probe)

    assert first.outcome == second.outcome == "running"
    assert calls_after_first > 0
    assert probe.calls == calls_after_first * 2
    assert second.node_summary["preflight"] == "completed"
    reused_nodes = {
        event.payload.get("node_id")
        for event in EventStore(project).read_all()
        if event.run_id == second.run_id and event.event_type == "run.node.reused"
    }
    assert "preflight" not in reused_nodes


def test_recovered_research_capability_resumes_same_project(tmp_path: Path) -> None:
    project = _project(tmp_path)
    blocked = run_project(
        project,
        capability_probe=StaticCapabilityProbe(blocked=("http_network",)),
    )

    resumed = run_project(
        project,
        resume=True,
        capability_probe=StaticCapabilityProbe(),
    )

    assert blocked.outcome == "capability_blocked"
    assert resumed.outcome == "running"
    assert resumed.node_summary["intake"] == "reused"
    assert resumed.node_summary["preflight"] == "completed"
    assert resumed.node_summary["universe"] == "awaiting_source_research"
    assert load_persisted_capability_matrix(project).overall_state == "ready"


def test_capability_receipt_rejects_symlink_without_replacing_target(tmp_path: Path) -> None:
    project = _project(tmp_path)
    matrix = run_capability_preflight(
        selection_from_project(project),
        host="local",
        probe=StaticCapabilityProbe(),
        project_root=project,
    )
    outside = tmp_path / "outside.json"
    outside.write_text("unchanged", encoding="utf-8")
    receipt = project / "capabilities/preflight.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(outside, receipt)

    with pytest.raises(CapabilityPersistenceError, match="软链接"):
        persist_capability_matrix(project, matrix)

    assert receipt.is_symlink()
    assert outside.read_text(encoding="utf-8") == "unchanged"


def test_loading_missing_receipt_does_not_create_capability_directory(tmp_path: Path) -> None:
    project = _project(tmp_path)

    with pytest.raises(CapabilityPersistenceError, match="尚未生成"):
        load_persisted_capability_matrix(project)

    assert not (project / "capabilities").exists()


class _CountingRuntimeProbe(RuntimeCapabilityProbe):
    def __init__(self) -> None:
        super().__init__()
        self.real_calls = 0

    def _check_real(self, capability_id: str, *, project_root: Path) -> tuple[bool, str]:
        del capability_id, project_root
        self.real_calls += 1
        return True, "已执行实机检查"


def test_reused_runtime_probe_discards_previous_flight_cache(tmp_path: Path) -> None:
    project = _project(tmp_path)
    selection = selection_from_project(project)
    probe = _CountingRuntimeProbe()

    run_capability_preflight(
        selection,
        host="local",
        probe=probe,
        project_root=project,
    )
    calls_after_first = probe.real_calls
    run_capability_preflight(
        selection,
        host="local",
        probe=probe,
        project_root=project,
    )

    assert calls_after_first > 0
    assert probe.real_calls == calls_after_first * 2
