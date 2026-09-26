"""Pin an evidence snapshot and its verified consumers as one recovery candidate.

The caller must obtain the manifest digest from an independently retained
candidate receipt.  A digest supplied from the same untrusted directory is not
an approval.  The two inputs are restored in staging and published together.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ci_workflow.application.portal_consumer_binding_recovery import (
    PortalConsumerBindingRecoveryError,
    export_verified_consumer_bindings,
    recover_verified_consumer_bindings,
)
from ci_workflow.renderers.portal.active_fact_projection import ActiveFactBinding
from ci_workflow.storage.snapshot_store import (
    LockedSnapshot,
    SnapshotIntegrityError,
    SnapshotStore,
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class VerifiedCandidateRecoveryError(RuntimeError):
    """The pinned recovery pair is incomplete, mismatched, or unsafe to publish."""


class VerifiedCandidateManifest(BaseModel):
    """Small path-free identity for one locked evidence/consumer pair."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    project_id: str = Field(min_length=1)
    evidence_snapshot_id: str = Field(min_length=1)
    evidence_snapshot_sha256: str = Field(pattern=_SHA256.pattern)
    evidence_snapshot_bytes: int = Field(ge=1)
    consumer_sidecar_sha256: str = Field(pattern=_SHA256.pattern)
    consumer_sidecar_bytes: int = Field(ge=1)
    consumer_binding_count: int = Field(ge=1)


def _digest(encoded: bytes) -> str:
    return hashlib.sha256(encoded).hexdigest()


def _encoded(manifest: VerifiedCandidateManifest) -> bytes:
    return (
        json.dumps(
            manifest.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_without_replacing(destination: Path, encoded: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError as error:
            if destination.is_symlink() or destination.read_bytes() != encoded:
                raise VerifiedCandidateRecoveryError(
                    "候选 manifest 目标已存在且字节不同"
                ) from error
    finally:
        temporary.unlink(missing_ok=True)


def seal_verified_candidate(
    project_root: Path,
    evidence_snapshot: LockedSnapshot,
    sidecar_path: Path,
    manifest_path: Path,
) -> str:
    """Seal exactly the registered rows, not a sidecar-selected subset."""
    try:
        evidence = SnapshotStore(project_root).read(evidence_snapshot)
        sidecar_bytes = sidecar_path.read_bytes()
        with tempfile.TemporaryDirectory(prefix="ci-candidate-consumers-") as directory:
            expected_path = Path(directory) / "verified-consumers.json"
            bindings = export_verified_consumer_bindings(
                project_root, evidence_snapshot, expected_path
            )
            if expected_path.read_bytes() != sidecar_bytes:
                raise VerifiedCandidateRecoveryError(
                    "候选消费者侧车与当前已核验登记集合不一致"
                )
        manifest = VerifiedCandidateManifest(
            schema_version="1.0",
            project_id=str(evidence["project_id"]),
            evidence_snapshot_id=evidence_snapshot.snapshot_id,
            evidence_snapshot_sha256=evidence_snapshot.sha256,
            evidence_snapshot_bytes=evidence_snapshot.byte_size,
            consumer_sidecar_sha256=_digest(sidecar_bytes),
            consumer_sidecar_bytes=len(sidecar_bytes),
            consumer_binding_count=len(bindings),
        )
    except (OSError, SnapshotIntegrityError, PortalConsumerBindingRecoveryError) as error:
        raise VerifiedCandidateRecoveryError("候选证据或消费者登记不可封存") from error
    encoded = _encoded(manifest)
    _write_without_replacing(manifest_path, encoded)
    return _digest(encoded)


def restore_verified_candidate(
    manifest_path: Path,
    evidence_manifest_path: Path,
    sidecar_path: Path,
    target: Path,
    *,
    expected_manifest_sha256: str,
) -> tuple[LockedSnapshot, tuple[ActiveFactBinding, ...]]:
    """Restore both pinned inputs off-target; publish only the complete pair."""
    if _SHA256.fullmatch(expected_manifest_sha256) is None:
        raise VerifiedCandidateRecoveryError("批准的候选 manifest 摘要无效")
    try:
        manifest_bytes = manifest_path.read_bytes()
        if _digest(manifest_bytes) != expected_manifest_sha256:
            raise VerifiedCandidateRecoveryError("候选 manifest 摘要不匹配")
        manifest = VerifiedCandidateManifest.model_validate_json(manifest_bytes)
        evidence_bytes = evidence_manifest_path.read_bytes()
        sidecar_bytes = sidecar_path.read_bytes()
    except (OSError, ValidationError) as error:
        raise VerifiedCandidateRecoveryError("候选恢复输入不可读或合同无效") from error
    if (
        len(evidence_bytes) != manifest.evidence_snapshot_bytes
        or _digest(evidence_bytes) != manifest.evidence_snapshot_sha256
        or len(sidecar_bytes) != manifest.consumer_sidecar_bytes
        or _digest(sidecar_bytes) != manifest.consumer_sidecar_sha256
    ):
        raise VerifiedCandidateRecoveryError("证据或消费者侧车字节/摘要不匹配")
    if target.is_symlink() or (target.exists() and (not target.is_dir() or any(target.iterdir()))):
        raise VerifiedCandidateRecoveryError("恢复目标已存在且非空或不是普通空目录")

    target.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=f".{target.name}.candidate-", dir=target.parent))
    try:
        locked = SnapshotStore(staged).restore_evidence_manifest(evidence_manifest_path)
        if (
            locked.snapshot_id != manifest.evidence_snapshot_id
            or locked.sha256 != manifest.evidence_snapshot_sha256
            or SnapshotStore(staged).read(locked)["project_id"] != manifest.project_id
        ):
            raise VerifiedCandidateRecoveryError("恢复出的证据快照身份不匹配")
        bindings = recover_verified_consumer_bindings(staged, sidecar_path)
        if len(bindings) != manifest.consumer_binding_count:
            raise VerifiedCandidateRecoveryError("已核验消费者数量与候选 manifest 不一致")
        try:
            os.replace(staged, target)
        except OSError as error:
            raise VerifiedCandidateRecoveryError("恢复目标在提交时不可替换") from error
        return locked, bindings
    except (SnapshotIntegrityError, PortalConsumerBindingRecoveryError) as error:
        raise VerifiedCandidateRecoveryError("候选证据或消费者恢复校验失败") from error
    finally:
        if staged.exists():
            shutil.rmtree(staged)


__all__ = [
    "VerifiedCandidateManifest",
    "VerifiedCandidateRecoveryError",
    "restore_verified_candidate",
    "seal_verified_candidate",
]
