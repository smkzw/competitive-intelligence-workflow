"""Atomic per-report publication pointers; candidate directories are never latest."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ci_workflow.application.delivered_artifacts import _ordinary, read_accepted_html_artifacts
from ci_workflow.storage.manifest_store import ArtifactManifest, ManifestStore
from ci_workflow.storage.sqlite import open_database


class LatestDelivery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    project_id: str
    contract_version: int = Field(ge=1)
    report: Literal["A", "B", "C"]
    report_version: str
    manifest_id: str
    report_snapshot_id: str
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    entry_relative_path: str
    accepted_at: datetime


def _projection(manifest: ArtifactManifest) -> LatestDelivery:
    return LatestDelivery(
        project_id=manifest.project_id, contract_version=manifest.contract_version,
        report=manifest.report, report_version=manifest.report_version,
        manifest_id=manifest.manifest_id, report_snapshot_id=manifest.report_snapshot_id,
        artifact_sha256=manifest.artifact.sha256,
        entry_relative_path=f"{manifest.artifact.relative_path}/index.html",
        accepted_at=manifest.render_verdict.verified_at,
    )


def _pointer(root: Path, report: str) -> Path:
    if report not in {"A", "B", "C"}:
        raise ValueError("最新版报告类型只能是A/B/C")
    path = root / "reports" / report / "latest.json"
    _ordinary(root, path)
    return path


def read_latest_delivery(project_root: Path, report: str) -> LatestDelivery | None:
    root = project_root.expanduser().resolve()
    path = _pointer(root, report)
    if not path.exists():
        return None
    pointer = LatestDelivery.model_validate_json(path.read_bytes())
    artifacts = read_accepted_html_artifacts(root, contract_version=pointer.contract_version)
    matches = [
        item for item in artifacts
        if item.manifest_id == pointer.manifest_id and item.report == report
    ]
    if len(matches) != 1 or _projection(matches[0]) != pointer:
        raise ValueError("最新版指针未绑定可验证的已接受产物")
    return pointer


def publish_latest_delivery(project_root: Path, manifest_id: str) -> LatestDelivery:
    root = project_root.expanduser().resolve()
    matches = [
        item for item in read_accepted_html_artifacts(root) if item.manifest_id == manifest_id
    ]
    if len(matches) != 1:
        raise ValueError("仅唯一的已接受产物可以发布最新版")
    manifest = matches[0]
    candidate = _projection(manifest)
    path = _pointer(root, manifest.report)
    encoded = (candidate.model_dump_json() + "\n").encode()
    for _attempt in range(3):
        previous_bytes = path.read_bytes() if path.exists() else None
        previous = read_latest_delivery(root, manifest.report)
        if previous == candidate:
            return candidate
        if previous is not None and (
            previous.contract_version > candidate.contract_version
            or previous.accepted_at >= candidate.accepted_at
        ):
            raise ValueError("不得自动回退或以同一接受时刻覆盖最新版")
        # Serialize publishers using the existing project DB, then compare-and-swap.
        with open_database(root / "state/project.sqlite") as database:
            database.execute("BEGIN IMMEDIATE")
            _ordinary(root, path)
            current_bytes = path.read_bytes() if path.exists() else None
            if current_bytes != previous_bytes:
                continue
            ManifestStore(root).verify_artifact(manifest)
            descriptor, temporary = tempfile.mkstemp(prefix=".latest-", dir=path.parent)
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(encoded)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, path)
            finally:
                Path(temporary).unlink(missing_ok=True)
            return candidate
    raise ValueError("最新版被并发更新，请重新验证后重试")
