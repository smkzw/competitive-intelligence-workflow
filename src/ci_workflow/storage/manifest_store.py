from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256 = re.compile(r"[0-9a-f]{64}")
_COMMIT = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")


class ManifestIntegrityError(RuntimeError):
    """产物清单不能与当前文件、快照或验收记录相互证明。"""


def _not_blank(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("产物清单字段不能为空")
    return normalized


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("产物清单时间必须包含明确时区偏移")
    return value


def _canonical_json(value: object) -> bytes:
    try:
        return (
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ManifestIntegrityError("产物清单必须是有限、可序列化的 JSON") from error


class DesignContractBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    roles: tuple[str, ...] = Field(min_length=1)
    digest: str
    applicable_sections: tuple[str, ...] = Field(min_length=1)

    @field_validator("roles", "applicable_sections")
    @classmethod
    def _items_are_unique_and_nonblank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_not_blank(value) for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("设计合同角色或章节不得重复")
        return normalized

    @field_validator("digest")
    @classmethod
    def _digest_is_sha256(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("设计合同摘要必须是小写 SHA-256")
        return value


class RendererBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    version: str

    @field_validator("name", "version")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class DeterministicCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    check_id: str
    status: Literal["passed", "failed"]
    receipt: str

    @field_validator("check_id", "receipt")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class RenderVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    verdict_id: str
    status: Literal["accepted", "rejected"]
    verified_at: datetime
    anchor_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("verdict_id")
    @classmethod
    def _verdict_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("anchor_ids")
    @classmethod
    def _anchors_are_unique_and_nonblank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_not_blank(value) for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("真实渲染锚点不得重复")
        return normalized

    @field_validator("verified_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)


class ArtifactFileBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    relative_path: str
    sha256: str
    byte_size: int = Field(ge=1)
    modified_at: datetime
    media_type: str

    @field_validator("relative_path")
    @classmethod
    def _path_is_project_relative(cls, value: str) -> str:
        pure = PurePosixPath(value)
        if pure.is_absolute() or ".." in pure.parts or "\\" in value:
            raise ValueError("产物路径必须是项目内 POSIX 相对路径")
        return _not_blank(value)

    @field_validator("sha256")
    @classmethod
    def _digest_is_sha256(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("产物摘要必须是小写 SHA-256")
        return value

    @field_validator("modified_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @field_validator("media_type")
    @classmethod
    def _media_type_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class ArtifactManifest(BaseModel):
    """附录 C 的完整、当前运行绑定产物清单。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    manifest_id: str
    project_id: str
    contract_version: int = Field(ge=1)
    report: Literal["A", "B", "C"]
    report_version: str
    data_cutoff: datetime
    producer_run_id: str
    source_commit: str
    package_digest: str
    evidence_snapshot_id: str
    claim_snapshot_id: str
    report_snapshot_id: str
    coverage_set_id: str
    coverage_projection_id: str
    structured_exceptions: tuple[dict[str, Any], ...]
    pages_or_sections: tuple[str, ...] = Field(min_length=1)
    product_ids: tuple[str, ...]
    trial_ids: tuple[str, ...]
    claim_ids: tuple[str, ...] = Field(min_length=1)
    chart_ids: tuple[str, ...]
    table_ids: tuple[str, ...]
    evidence_reference_ids: tuple[str, ...] = Field(min_length=1)
    design_contract: DesignContractBinding
    renderer: RendererBinding
    filter_state: dict[str, Any]
    generated_at: datetime
    deterministic_checks: tuple[DeterministicCheck, ...] = Field(min_length=1)
    render_verdict: RenderVerdict
    accepted_by: str | None
    artifact: ArtifactFileBinding
    status: Literal["generated", "quality_check", "accepted", "failed", "superseded"]
    supersedes_manifest_id: str | None

    @field_validator(
        "manifest_id",
        "project_id",
        "report_version",
        "producer_run_id",
        "evidence_snapshot_id",
        "claim_snapshot_id",
        "report_snapshot_id",
        "coverage_set_id",
        "coverage_projection_id",
    )
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("accepted_by", "supersedes_manifest_id")
    @classmethod
    def _optional_text_is_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _not_blank(value)

    @field_validator(
        "pages_or_sections",
        "product_ids",
        "trial_ids",
        "claim_ids",
        "chart_ids",
        "table_ids",
        "evidence_reference_ids",
    )
    @classmethod
    def _lists_are_unique_and_nonblank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_not_blank(value) for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("产物清单列表不得重复")
        return normalized

    @field_validator("source_commit")
    @classmethod
    def _commit_is_hex(cls, value: str) -> str:
        if _COMMIT.fullmatch(value) is None:
            raise ValueError("源代码提交摘要必须是 40 或 64 位小写十六进制")
        return value

    @field_validator("package_digest")
    @classmethod
    def _package_digest_is_sha256(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("安装包摘要必须是小写 SHA-256")
        return value

    @field_validator("data_cutoff", "generated_at")
    @classmethod
    def _times_have_offsets(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @model_validator(mode="after")
    def _accepted_manifest_has_current_acceptance(self) -> ArtifactManifest:
        if self.supersedes_manifest_id == self.manifest_id:
            raise ValueError("产物清单不能取代自身")
        if self.artifact.modified_at < self.generated_at:
            raise ValueError("产物修改时间不得早于生成开始")
        if self.render_verdict.verified_at < self.artifact.modified_at:
            raise ValueError("真实渲染验收不得早于当前产物")
        if self.status == "accepted":
            if self.accepted_by is None:
                raise ValueError("已接受产物必须记录独立接受者")
            if self.render_verdict.status != "accepted":
                raise ValueError("已接受产物必须通过真实渲染验收")
            if any(check.status != "passed" for check in self.deterministic_checks):
                raise ValueError("已接受产物的确定性检查必须全部通过")
        return self


class ManifestWriteContext(BaseModel):
    """由当前运行提供的权威身份；防止旧运行或旧快照被重新标成已接受。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    contract_version: int = Field(ge=1)
    report: Literal["A", "B", "C"]
    report_version: str
    data_cutoff: datetime
    producer_run_id: str
    source_commit: str
    package_digest: str
    evidence_snapshot_id: str
    claim_snapshot_id: str
    report_snapshot_id: str
    coverage_set_id: str
    coverage_projection_id: str

    @field_validator(
        "project_id",
        "report_version",
        "producer_run_id",
        "evidence_snapshot_id",
        "claim_snapshot_id",
        "report_snapshot_id",
        "coverage_set_id",
        "coverage_projection_id",
    )
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("source_commit")
    @classmethod
    def _commit_is_hex(cls, value: str) -> str:
        if _COMMIT.fullmatch(value) is None:
            raise ValueError("当前运行的源代码提交摘要无效")
        return value

    @field_validator("package_digest")
    @classmethod
    def _package_digest_is_sha256(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("当前运行的安装包摘要无效")
        return value

    @field_validator("data_cutoff")
    @classmethod
    def _cutoff_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)


class ManifestStore:
    """验证当前文件后写入不可变逐产物清单。"""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.directory = self.project_root / "manifests" / "artifacts"
        self.directory.mkdir(parents=True, exist_ok=True)

    def _artifact_path(self, manifest: ArtifactManifest) -> Path:
        path = self.project_root.joinpath(*PurePosixPath(manifest.artifact.relative_path).parts)
        for component in (path, *path.parents):
            if component == self.project_root:
                break
            if component.is_symlink():
                raise ManifestIntegrityError("产物路径不得包含符号链接")
        resolved = path.resolve()
        if not resolved.is_relative_to(self.project_root):
            raise ManifestIntegrityError("产物路径离开了项目目录")
        return resolved

    @staticmethod
    def _directory_digest(path: Path) -> tuple[str, int, float]:
        """计算与门户验收一致的目录摘要、总字节数和最新文件时间。"""
        if path.is_symlink():
            raise ManifestIntegrityError("产物目录不得是符号链接")
        digest = hashlib.sha256()
        total = 0
        latest_mtime: float | None = None
        try:
            paths = sorted(path.rglob("*"))
        except OSError as error:
            raise ManifestIntegrityError("产物目录不存在或不可读") from error
        for child in paths:
            if child.is_symlink():
                raise ManifestIntegrityError("产物目录不得包含符号链接")
            if not child.is_file():
                continue
            try:
                content = child.read_bytes()
                mtime = child.stat().st_mtime
            except OSError as error:
                raise ManifestIntegrityError("产物目录不存在或不可读") from error
            digest.update(child.relative_to(path).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(content)
            total += len(content)
            latest_mtime = mtime if latest_mtime is None else max(latest_mtime, mtime)
        if latest_mtime is None:
            raise ManifestIntegrityError("产物目录不包含可读文件")
        return digest.hexdigest(), total, latest_mtime

    def _verify_artifact(self, manifest: ArtifactManifest) -> None:
        path = self._artifact_path(manifest)
        if manifest.artifact.media_type == "directory":
            if not path.is_dir():
                raise ManifestIntegrityError("产物目录不存在或不可读")
            actual_digest, actual_bytes, latest_mtime = self._directory_digest(path)
            if actual_bytes != manifest.artifact.byte_size:
                raise ManifestIntegrityError("产物字节数与清单不一致")
            if actual_digest != manifest.artifact.sha256:
                raise ManifestIntegrityError("产物摘要与清单不一致")
            modified_at = datetime.fromtimestamp(
                latest_mtime, tz=manifest.artifact.modified_at.tzinfo
            )
        else:
            try:
                content = path.read_bytes()
                modified_at = datetime.fromtimestamp(
                    path.stat().st_mtime, tz=manifest.artifact.modified_at.tzinfo
                )
            except OSError as error:
                raise ManifestIntegrityError("产物不存在或不可读") from error
            if len(content) != manifest.artifact.byte_size:
                raise ManifestIntegrityError("产物字节数与清单不一致")
            if hashlib.sha256(content).hexdigest() != manifest.artifact.sha256:
                raise ManifestIntegrityError("产物摘要与清单不一致")
        if abs((modified_at - manifest.artifact.modified_at).total_seconds()) > 1.0:
            raise ManifestIntegrityError("产物修改时间与清单不一致")

    def verify_artifact(self, manifest: ArtifactManifest) -> None:
        """只读校验清单引用的当前文件或目录产物。"""
        self._verify_artifact(manifest)

    def _verify_current_context(
        self,
        manifest: ArtifactManifest,
        current_context: ManifestWriteContext | None,
    ) -> None:
        if manifest.status != "accepted":
            return
        if current_context is None:
            raise ManifestIntegrityError("接受产物前必须提供当前运行与快照身份")
        manifest_identity = {
            key: getattr(manifest, key) for key in ManifestWriteContext.model_fields
        }
        if ManifestWriteContext.model_validate(manifest_identity) != current_context:
            raise ManifestIntegrityError("产物清单引用的运行或快照不是当前接受对象")

    def write(
        self,
        manifest: ArtifactManifest,
        *,
        current_context: ManifestWriteContext | None = None,
    ) -> Path:
        self._verify_current_context(manifest, current_context)
        self._verify_artifact(manifest)
        encoded = _canonical_json(manifest.model_dump(mode="json"))
        path = self.directory / f"{manifest.manifest_id}.json"
        if path.exists():
            if path.read_bytes() != encoded:
                raise ManifestIntegrityError("同一产物清单身份对应了不同内容")
            return path
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=self.directory
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return path
