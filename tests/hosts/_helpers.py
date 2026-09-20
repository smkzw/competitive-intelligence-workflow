"""Task 9.4 tests/hosts 共享构造 helper。

提供真实项目工作区、规范项目状态事件、手工收件箱请求与站点式 HTML
产物入口的最小构造；测试用它们对适配器真实 API 独立建模，不复制被测
业务逻辑。
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ci_workflow.application.capability_preflight import (
    CapabilitySelection,
)
from ci_workflow.application.project_service import (
    create_project_workspace,
    verify_project_workspace,
)
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.storage.event_store import EventStore, WorkflowEvent

_STATE_EVENT_SEQUENCE = 0


def make_project(
    tmp_path: Path,
    *,
    reports: tuple[str, ...] = ("A",),
    outputs: tuple[str, ...] = ("html",),
) -> Path:
    """创建带冻结合同的真实项目工作区（首版真实输出只允许 html）。"""
    contract = create_project_contract(
        indication="特应性皮炎",
        reports=list(reports),
        outputs=list(outputs),
    )
    return create_project_workspace(tmp_path / "项目", contract)


def selection(
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


def append_project_state(
    project_root: Path, *, to_state: str, from_state: str = "running"
) -> None:
    """按真实事件流追加一条项目族规范迁移（last-wins 推导的真源）。"""
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


def write_download_request(
    project_root: Path, *, state: str = "awaiting_user"
) -> dict[str, Any]:
    """写入一条活跃手工收件箱请求（receipts 真源格式）。"""
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


def write_html_site(
    project_root: Path, report: str, version: str = "v1"
) -> Path:
    """按项目相对约定写入站点式 HTML 入口并返回入口路径。"""
    entry = project_root / "reports" / report / version / "html" / "index.html"
    entry.parent.mkdir(parents=True)
    entry.write_text(
        f"<!doctype html><title>{report} 类报告站点</title>", encoding="utf-8"
    )
    return entry


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def write_accepted_html_site(project_root: Path, report: str, version: str = "v1") -> Path:
    """Synthetic acceptance chain for adapter mapping tests, not real report QA."""
    from ci_workflow.storage.manifest_store import ArtifactManifest, ManifestStore
    from ci_workflow.storage.snapshot_store import ReportSnapshotManifest, SnapshotStore
    from tests.contract.test_artifact_manifest import _manifest

    entry = write_html_site(project_root, report, version)
    contract = verify_project_workspace(project_root).contract
    now = datetime.now(UTC)
    payload = _manifest()
    payload.update(
        project_id=contract.project_id, contract_version=contract.contract_version,
        report=report, report_version=version, data_cutoff=contract.data_cutoff.isoformat(),
        manifest_id=f"candidate-{report}-{version}", generated_at=now.isoformat(),
        status="quality_check", accepted_by=None,
    )
    snapshot = ReportSnapshotManifest.model_validate({
        key: payload[key] for key in ReportSnapshotManifest.model_fields if key != "created_at"
    } | {"created_at": now.isoformat()})
    locked = SnapshotStore(project_root).lock_report_snapshot(
        report=report, manifest=snapshot.model_dump(mode="json"),  # type: ignore[arg-type]
    )
    digest, size, _ = ManifestStore._directory_digest(entry.parent)
    payload.update(
        report_snapshot_id=locked.snapshot_id,
        artifact={
            "relative_path": entry.parent.relative_to(project_root).as_posix(),
            "sha256": digest, "byte_size": size, "modified_at": now.isoformat(),
            "media_type": "directory",
        },
        render_verdict={
            "verdict_id": f"verdict-{report}-{version}", "status": "accepted",
            "verified_at": now.isoformat(), "anchor_ids": ["synthetic-adapter-fixture"],
        },
    )
    candidate = ArtifactManifest.model_validate(payload)
    accepted = ArtifactManifest.model_validate(payload | {
        "manifest_id": f"accepted-{report}-{version}", "status": "accepted",
        "accepted_by": "synthetic-independent-reviewer",
        "supersedes_manifest_id": candidate.manifest_id,
    })
    store = ManifestStore(project_root)
    for manifest in (candidate, accepted):
        (store.directory / f"{manifest.manifest_id}.json").write_text(manifest.model_dump_json())
    (entry.parent.parent / "html.manifest.json").write_text(candidate.model_dump_json())
    EventStore(project_root).append(WorkflowEvent(
        schema_version="1.0", event_id=f"delivery-{report}-{version}",
        project_id=contract.project_id, run_id="synthetic-acceptance-run",
        event_type="graph.transition.accepted", occurred_at=now, actor_id="graph-executor",
        idempotency_key=f"delivery-{report}-{version}", payload={
            "family": "format_artifact", "to_state": "delivery_ready",
            "object_id": f"format-report_{report}-html",
            "guard_evidence": {
                "candidate_snapshot_id": accepted.report_snapshot_id,
                "candidate_artifact_digest": accepted.artifact.sha256,
                "visual_verdict_id": accepted.render_verdict.verdict_id,
                "verifier_identity": accepted.accepted_by, "format": "html",
            },
        },
    ))
    return entry
