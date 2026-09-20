"""Read-only delivery projection shared by all thin host adapters."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from zoneinfo import ZoneInfo

from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.domain.contracts import ProjectContract
from ci_workflow.domain.enums import ReportKind
from ci_workflow.qc.browser import load_locked_sitemap_source
from ci_workflow.storage.event_store import EventStore
from ci_workflow.storage.manifest_store import ArtifactManifest, ManifestStore


def _ordinary(root: Path, path: Path) -> None:
    if not path.is_relative_to(root):
        raise ValueError("交付记录路径越界")
    if ".." in path.relative_to(root).parts:
        raise ValueError("交付记录路径不得包含父目录跳转")
    for component in (path, *path.parents):
        if component == root:
            break
        if component.is_symlink():
            raise ValueError("交付记录不得使用符号链接")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("交付记录路径越界")


def read_accepted_html_artifacts(
    project_root: Path, *, contract_version: int | None = None,
) -> tuple[ArtifactManifest, ...]:
    """Require immutable successor, snapshot, whole-site bytes and delivery event."""
    root = project_root.expanduser().resolve()
    contract = verify_project_workspace(root).contract
    if contract_version is not None and contract_version != contract.contract_version:
        database_path = root / "state/project.sqlite"
        _ordinary(root, database_path)
        database = sqlite3.connect(f"{database_path.as_uri()}?mode=ro", uri=True)
        try:
            row = database.execute(
                "SELECT contract_json FROM project_contract_versions "
                "WHERE project_id = ? AND contract_version = ?",
                (contract.project_id, contract_version),
            ).fetchone()
        finally:
            database.close()
        if row is None:
            raise ValueError("历史交付缺少已登记的合同版本")
        historical = ProjectContract.model_validate_json(row[0])
        if (
            historical.project_id != contract.project_id
            or historical.contract_version != contract_version
        ):
            raise ValueError("历史交付合同身份不一致")
        contract = historical
    directory = root / "manifests/artifacts"
    _ordinary(root, directory)
    if not directory.exists():
        return ()
    events = EventStore(root).read_all()
    accepted = []
    identities: set[tuple[str, str]] = set()
    for path in sorted(directory.glob("*.json")):
        _ordinary(root, path)
        payload = json.loads(path.read_bytes())
        if not isinstance(payload, dict):
            raise ValueError("产物清单不是对象")
        if payload.get("status") != "accepted":
            continue
        manifest = ArtifactManifest.model_validate(payload)
        if manifest.artifact.media_type != "directory":
            continue
        if path.stem != manifest.manifest_id or manifest.project_id != contract.project_id:
            raise ValueError("已接受产物清单身份不一致")
        if manifest.contract_version != contract.contract_version:
            continue
        # Public cutoff is a calendar date, as in research submission admission.
        zone = ZoneInfo(contract.timezone)
        report_cutoff = manifest.data_cutoff.astimezone(zone).date()
        if report_cutoff != contract.data_cutoff.astimezone(zone).date():
            raise ValueError("已接受产物截止时间与当前项目合同不一致")
        if not manifest.supersedes_manifest_id:
            raise ValueError("已接受产物缺少不可变候选前驱")
        predecessor_path = directory / f"{manifest.supersedes_manifest_id}.json"
        _ordinary(root, predecessor_path)
        predecessor = ArtifactManifest.model_validate_json(predecessor_path.read_bytes())
        if predecessor.manifest_id != manifest.supersedes_manifest_id:
            raise ValueError("前驱清单身份不一致")
        mutable = {
            "manifest_id", "render_verdict", "accepted_by", "status", "supersedes_manifest_id",
        }
        before, after = predecessor.model_dump(), manifest.model_dump()
        if any(before[key] != after[key] for key in before if key not in mutable):
            raise ValueError("已接受产物未保留候选绑定")
        report_root = root / "reports" / manifest.report / manifest.report_version
        manifest_path = report_root / "html.manifest.json"
        _ordinary(root, manifest_path)
        snapshot_path = (
            root / "snapshots/reports" / manifest.report / f"{manifest.report_snapshot_id}.json"
        )
        _ordinary(root, snapshot_path)
        store = ManifestStore(root)
        store.verify_artifact(manifest)
        source = load_locked_sitemap_source(
            root, ReportKind(manifest.report), manifest.report_version,
        )
        if source.manifest not in (predecessor, manifest):
            raise ValueError("站点当前清单不是已接受候选或其继承清单")
        has_delivery = any(
            event.project_id == manifest.project_id
            and event.event_type == "graph.transition.accepted"
            and event.payload.get("family") == "format_artifact"
            and event.payload.get("to_state") == "delivery_ready"
            and event.occurred_at >= manifest.render_verdict.verified_at
            and isinstance(event.payload.get("guard_evidence"), dict)
            and all(
                event.payload["guard_evidence"].get(key) == value
                for key, value in {
                    "candidate_snapshot_id": manifest.report_snapshot_id,
                    "candidate_artifact_digest": manifest.artifact.sha256,
                    "visual_verdict_id": manifest.render_verdict.verdict_id,
                    "verifier_identity": manifest.accepted_by,
                    "format": "html",
                }.items()
            )
            for event in events
        )
        if not has_delivery:
            raise ValueError("已接受产物缺少绑定同一快照、字节与复核者的交付事件")
        identity = (manifest.report, manifest.report_version)
        if identity in identities:
            raise ValueError("同一报告版本存在冲突的已接受产物")
        identities.add(identity)
        accepted.append(manifest)
    return tuple(accepted)
