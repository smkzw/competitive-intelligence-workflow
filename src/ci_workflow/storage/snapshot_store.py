from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from base64 import b64decode
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.ids import stable_id

_SHA256 = re.compile(r"[0-9a-f]{64}")


class SnapshotIntegrityError(RuntimeError):
    """快照身份、路径、内容或摘要不一致。"""


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
        raise SnapshotIntegrityError("快照必须是有限、可序列化的 JSON") from error


def _not_blank(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("快照字段不能为空")
    return normalized


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("快照时间必须包含明确时区偏移")
    return value


class EvidenceSnapshotManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0", "2.0"]
    project_id: str
    contract_version: int = Field(ge=1)
    data_cutoff: datetime
    source_version_ids: tuple[str, ...] = Field(min_length=1)
    fragment_ids: tuple[str, ...] = Field(min_length=1)
    fact_version_ids: tuple[str, ...] = Field(min_length=1)
    claim_version_ids: tuple[str, ...] = ()
    derivation_ids: tuple[str, ...] = ()
    receipt_ids: tuple[str, ...] = ()
    scientific_content_digest: str
    created_at: datetime
    closure: dict[str, Any] | None = None

    @field_validator("project_id")
    @classmethod
    def _project_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator(
        "source_version_ids",
        "fragment_ids",
        "fact_version_ids",
        "claim_version_ids",
        "derivation_ids",
        "receipt_ids",
    )
    @classmethod
    def _ids_are_unique_and_nonblank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_not_blank(value) for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("快照标识列表不得重复")
        return normalized

    @field_validator("scientific_content_digest")
    @classmethod
    def _digest_is_sha256(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("科学证据内容摘要必须是小写 SHA-256")
        return value

    @field_validator("data_cutoff", "created_at")
    @classmethod
    def _times_have_offsets(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @model_validator(mode="after")
    def _v2_contains_portable_transitive_closure(self) -> EvidenceSnapshotManifest:
        if self.schema_version == "1.0":
            if self.closure is not None:
                raise ValueError("历史1.0快照不得补写传递闭包")
            return self
        if self.closure is None:
            raise ValueError("2.0证据快照必须包含可移植传递闭包")
        required = {
            "sources",
            "fragments",
            "facts",
            "claims",
            "derivations",
            "acquisition_attempts",
            "receipts",
        }
        if set(self.closure) != required:
            raise ValueError("证据快照传递闭包字段不完整")
        if not all(isinstance(self.closure[key], list) for key in required):
            raise ValueError("证据快照传递闭包各集合必须是列表")
        return self


def _require_fact_context_matches_closure(item: object) -> None:
    """闭包事实、其规范JSON与内容摘要必须互相一致。

    ``consumer_binding`` 只是摄取提示，不是已核验消费者身份；若 ``fact``、
    ``scientific_context_json`` 与 ``content_sha256`` 三者可以互相矛盾，恢复出的
    ``scientific_context_json`` 就能携带未经登记的消费者声明，并随后被当作已声明
    绑定投影到门户。恢复前逐项复核可关闭该入口。
    """
    if not isinstance(item, dict):
        raise SnapshotIntegrityError("事实闭包记录无效")
    fact = item.get("fact")
    context_json = item.get("scientific_context_json")
    if not isinstance(context_json, str):
        raise SnapshotIntegrityError("事实闭包科学语境、规范JSON或内容摘要不一致")
    try:
        context = json.loads(context_json)
    except json.JSONDecodeError as error:
        raise SnapshotIntegrityError("事实闭包科学语境不是有效JSON") from error
    if (
        not isinstance(fact, dict)
        or context != fact
        or hashlib.sha256(context_json.encode("utf-8")).hexdigest()
        != item.get("content_sha256")
    ):
        raise SnapshotIntegrityError("事实闭包科学语境、规范JSON或内容摘要不一致")


def _evidence_payload(manifest: EvidenceSnapshotManifest) -> dict[str, Any]:
    """Keep historical 1.0 bytes unchanged; never backfill new closure fields."""
    excluded = (
        {"claim_version_ids", "derivation_ids", "receipt_ids", "closure"}
        if manifest.schema_version == "1.0"
        else set()
    )
    return manifest.model_dump(mode="json", exclude=excluded)


class ReportSnapshotManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    project_id: str
    contract_version: int = Field(ge=1)
    report: Literal["A", "B", "C"]
    report_version: str
    data_cutoff: datetime
    evidence_snapshot_id: str
    claim_snapshot_id: str
    coverage_set_id: str
    claim_ids: tuple[str, ...] = Field(min_length=1)
    created_at: datetime

    @field_validator(
        "project_id",
        "report_version",
        "evidence_snapshot_id",
        "claim_snapshot_id",
        "coverage_set_id",
    )
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("claim_ids")
    @classmethod
    def _claims_are_unique_and_nonblank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_not_blank(value) for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("报告快照声明不得重复")
        return normalized

    @field_validator("data_cutoff", "created_at")
    @classmethod
    def _times_have_offsets(cls, value: datetime) -> datetime:
        return _offset_datetime(value)


class LockedSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot_id: str
    kind: Literal["evidence", "report"]
    report: Literal["A", "B", "C"] | None
    sha256: str
    relative_path: str
    byte_size: int = Field(ge=1)

    @field_validator("snapshot_id", "relative_path")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("sha256")
    @classmethod
    def _digest_is_sha256(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("快照摘要必须是小写 SHA-256")
        return value


def compute_locked_snapshot(
    *,
    kind: Literal["evidence", "report"],
    report: Literal["A", "B", "C"] | None,
    manifest: dict[str, Any],
) -> LockedSnapshot:
    """公共纯校验函数：按本模块同一规范 JSON 算法计算锁定快照身份。

    与 ``SnapshotStore._lock`` 使用完全同一算法（规范 JSON → SHA-256 →
    stable_id → 相对路径 → 字节数），供视图权威校验逐项比对锁定元数据，
    避免在调用方复制一套将来会漂移的算法。
    """
    validated = (
        EvidenceSnapshotManifest.model_validate(manifest)
        if kind == "evidence"
        else ReportSnapshotManifest.model_validate(manifest)
    )
    payload = (
        _evidence_payload(validated)
        if isinstance(validated, EvidenceSnapshotManifest)
        else validated.model_dump(mode="json")
    )
    encoded = _canonical_json(payload)
    digest = hashlib.sha256(encoded).hexdigest()
    identity_parts = (digest,) if report is None else (report, digest)
    snapshot_id = stable_id(f"{kind}-snapshot", *identity_parts)
    if kind == "evidence":
        relative = PurePosixPath("snapshots", "evidence", f"{snapshot_id}.json")
    else:
        if report is None:
            raise SnapshotIntegrityError("报告快照必须声明报告类型")
        relative = PurePosixPath(
            "snapshots", "reports", report, f"{snapshot_id}.json"
        )
    return LockedSnapshot(
        snapshot_id=snapshot_id,
        kind=kind,
        report=report,
        sha256=digest,
        relative_path=relative.as_posix(),
        byte_size=len(encoded),
    )


class SnapshotStore:
    """项目内不可覆盖、按规范 JSON 内容寻址的证据与报告快照。"""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    def _lock(
        self,
        *,
        kind: Literal["evidence", "report"],
        report: Literal["A", "B", "C"] | None,
        payload: dict[str, Any],
    ) -> LockedSnapshot:
        locked = compute_locked_snapshot(kind=kind, report=report, manifest=payload)
        path = self.project_root.joinpath(*PurePosixPath(locked.relative_path).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = _canonical_json(payload)
        if path.exists():
            if path.read_bytes() != encoded:
                raise SnapshotIntegrityError("同一快照身份对应了不同内容")
        else:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
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
        return locked

    def lock_evidence_snapshot(self, manifest: dict[str, Any]) -> LockedSnapshot:
        validated = EvidenceSnapshotManifest.model_validate(manifest)
        return self._lock(
            kind="evidence", report=None, payload=_evidence_payload(validated)
        )

    def lock_report_snapshot(
        self, *, report: Literal["A", "B", "C"], manifest: dict[str, Any]
    ) -> LockedSnapshot:
        validated = ReportSnapshotManifest.model_validate(manifest)
        if validated.report != report:
            raise SnapshotIntegrityError("报告快照的路径和报告类型不一致")
        return self._lock(
            kind="report", report=report, payload=validated.model_dump(mode="json")
        )

    def _resolve(self, relative_path: str) -> Path:
        pure = PurePosixPath(relative_path)
        if pure.is_absolute() or ".." in pure.parts or "\\" in relative_path:
            raise SnapshotIntegrityError("快照路径必须是项目内相对路径")
        path = self.project_root.joinpath(*pure.parts).resolve()
        if not path.is_relative_to(self.project_root):
            raise SnapshotIntegrityError("快照路径离开了项目目录")
        return path

    def read(self, snapshot: LockedSnapshot) -> dict[str, Any]:
        path = self._resolve(snapshot.relative_path)
        try:
            encoded = path.read_bytes()
        except OSError as error:
            raise SnapshotIntegrityError("快照文件不存在或不可读") from error
        if len(encoded) != snapshot.byte_size:
            raise SnapshotIntegrityError("快照字节数不匹配")
        if hashlib.sha256(encoded).hexdigest() != snapshot.sha256:
            raise SnapshotIntegrityError("快照摘要不匹配")
        try:
            payload = json.loads(encoded)
        except json.JSONDecodeError as error:
            raise SnapshotIntegrityError("快照不是有效 JSON") from error
        if not isinstance(payload, dict):
            raise SnapshotIntegrityError("快照根节点必须是对象")
        if snapshot.kind == "evidence":
            EvidenceSnapshotManifest.model_validate(payload)
        else:
            validated = ReportSnapshotManifest.model_validate(payload)
            if validated.report != snapshot.report:
                raise SnapshotIntegrityError("报告快照身份不匹配")
        return payload

    def restore_evidence_manifest(self, manifest_path: Path) -> LockedSnapshot:
        """Publish a fully restored v2 chain only after every source passes."""
        if any(self.project_root.iterdir()) if self.project_root.exists() else False:
            raise SnapshotIntegrityError("manifest恢复目标必须是空目录")
        self.project_root.parent.mkdir(parents=True, exist_ok=True)
        staged = Path(tempfile.mkdtemp(
            prefix=f".{self.project_root.name}.restore-", dir=self.project_root.parent
        ))
        try:
            restored = SnapshotStore(staged)._restore_evidence_into_empty(manifest_path)
            try:
                os.replace(staged, self.project_root)
            except OSError as error:
                raise SnapshotIntegrityError("manifest恢复目标在提交时不可替换") from error
            return restored
        finally:
            if staged.exists():
                shutil.rmtree(staged)

    def _restore_evidence_into_empty(self, manifest_path: Path) -> LockedSnapshot:
        """Build only inside an isolated staging directory."""
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = EvidenceSnapshotManifest.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            raise SnapshotIntegrityError("证据manifest不可读或合同无效") from error
        if manifest.schema_version != "2.0" or manifest.closure is None:
            raise SnapshotIntegrityError("历史快照只读保留，不能迁移补签或单manifest恢复")
        # Preflight the declared fact context before any byte of the target project
        # is created, so an inconsistent closure cannot half-restore.
        for item in manifest.closure["facts"]:
            _require_fact_context_matches_closure(item)

        from ci_workflow.application.source_research_service import SourceCapture
        from ci_workflow.storage.content_store import (
            ContentAddressedStore,
            ContentIntegrityError,
            EvidenceRepository,
        )
        from ci_workflow.storage.migrations import apply_migrations
        from ci_workflow.storage.sqlite import open_database

        self.project_root.mkdir(parents=True, exist_ok=True)
        database_path = self.project_root / "state/project.sqlite"
        apply_migrations(database_path)
        content_store = ContentAddressedStore(self.project_root)
        repository = EvidenceRepository(database_path, content_store)
        closure = manifest.closure

        restored_raw_assets: set[tuple[str, str]] = set()
        for item in closure["sources"]:
            if not isinstance(item, dict):
                raise SnapshotIntegrityError("来源闭包记录无效")
            capture = SourceCapture.model_validate(item.get("capture"))
            raw_b64 = item.get("raw_asset_b64")
            if capture.text_derivation is not None:
                raw_asset = capture.text_derivation.raw_asset
                raw_key = (raw_asset.sha256, raw_asset.media_type)
                if isinstance(raw_b64, str):
                    raw_blob = content_store.put_bytes(
                        b64decode(raw_b64, validate=True), media_type=raw_asset.media_type,
                    )
                    if raw_blob != raw_asset:
                        raise SnapshotIntegrityError("恢复原始资产与派生回执不一致")
                    restored_raw_assets.add(raw_key)
                elif raw_b64 is None and raw_key in restored_raw_assets:
                    try:
                        content_store.read_bytes(raw_asset)
                    except (OSError, ContentIntegrityError) as error:
                        raise SnapshotIntegrityError("复用的原始资产字节不可核验") from error
                else:
                    raise SnapshotIntegrityError("来源派生闭包缺少原始资产字节")
            version = repository.add_source_version(
                source_id=capture.source_id,
                content=capture.content_text.encode("utf-8"),
                media_type=(
                    "text/plain"
                    if capture.media_type == "application/pdf"
                    else capture.media_type
                ),
                text_derivation=capture.text_derivation,
                acquired_at=capture.acquired_at,
                published_at=capture.date_evidence("published_at"),
                effective_at=capture.date_evidence("effective_at"),
                first_disclosed_at=capture.date_evidence("first_disclosed_at"),
            )
            if version.source_version_id != item.get("source_version_id"):
                raise SnapshotIntegrityError("恢复来源版本身份不一致")

        for item in closure["fragments"]:
            if not isinstance(item, dict):
                raise SnapshotIntegrityError("片段闭包记录无效")
            from ci_workflow.domain.evidence import EvidenceFragmentRecord

            fragment = EvidenceFragmentRecord.model_validate(item)
            restored_fragment = repository.add_fragment(
                source_version_id=fragment.source_version_id,
                locator=fragment.locator,
                original_text=fragment.original_text,
                created_at=fragment.created_at,
            )
            if restored_fragment.fragment_id != fragment.fragment_id:
                raise SnapshotIntegrityError("恢复片段身份不一致")

        with open_database(database_path) as database:
            for item in closure["facts"]:
                fact = item["fact"]
                database.execute(
                    "INSERT OR IGNORE INTO entities "
                    "(entity_id,entity_type,canonical_name,created_at) VALUES (?,?,?,?)",
                    (
                        fact["entity_id"],
                        fact["entity_type"],
                        fact["canonical_name"],
                        item["created_at"],
                    ),
                )
                database.execute(
                    """INSERT INTO fact_versions (
                    fact_version_id,fact_id,entity_id,field_id,raw_value,normalized_value,
                    disclosure_state,review_state,primary_fragment_id,
                    supersedes_fact_version_id,created_at,content_sha256,
                    scientific_context_json) VALUES (?,?,?,?,?,?,?,?,?,NULL,?,?,?)""",
                    (
                        item["fact_version_id"],
                        fact["fact_id"],
                        fact["entity_id"],
                        fact["field_id"],
                        fact.get("raw_value"),
                        fact.get("normalized_value"),
                        fact["disclosure_state"],
                        item["review_state"],
                        item["primary_fragment_id"],
                        item["created_at"],
                        item["content_sha256"],
                        item["scientific_context_json"],
                    ),
                )
                database.execute(
                    "INSERT INTO fact_evidence "
                    "(fact_version_id,fragment_id,evidence_role,created_at) VALUES (?,?,?,?)",
                    (
                        item["fact_version_id"],
                        item["primary_fragment_id"],
                        "primary",
                        item["created_at"],
                    ),
                )
            for item in closure["claims"]:
                claim = item["claim"]
                database.execute(
                    """INSERT INTO claim_versions (
                    claim_version_id,claim_id,claim_text,claim_kind,review_state,
                    supersedes_claim_version_id,created_at) VALUES (?,?,?,?,?,NULL,?)""",
                    (
                        item["claim_version_id"],
                        claim["claim_id"],
                        claim["claim_text"],
                        claim["claim_kind"],
                        item["review_state"],
                        item["created_at"],
                    ),
                )
                for fact_version_id in item["fact_version_ids"]:
                    database.execute(
                        "INSERT INTO claim_facts "
                        "(claim_version_id,fact_version_id,support_role,created_at) "
                        "VALUES (?,?,?,?)",
                        (
                            item["claim_version_id"],
                            fact_version_id,
                            "supports",
                            item["created_at"],
                        ),
                    )
            for item in closure["derivations"]:
                database.execute(
                    "INSERT INTO evidence_derivations "
                    "(derivation_id,derivation_kind,input_fragment_ids_json,rule_id,"
                    "rule_version,output_json,created_at) VALUES (?,?,?,?,?,?,?)",
                    (
                        item["derivation_id"],
                        item["derivation_kind"],
                        json.dumps(item["input_fragment_ids"], ensure_ascii=False),
                        item["rule_id"],
                        item["rule_version"],
                        json.dumps(item["output"], ensure_ascii=False, sort_keys=True),
                        item["created_at"],
                    ),
                )
            for item in closure["acquisition_attempts"]:
                database.execute(
                    """INSERT INTO source_acquisition_attempts (
                    attempt_id,request_id,source_id,source_version_id,receipt_id,
                    attempt_index,acquired_at,created_at) VALUES (?,?,?,?,?,?,?,?)""",
                    tuple(item[key] for key in (
                        "attempt_id", "request_id", "source_id", "source_version_id",
                        "receipt_id", "attempt_index", "acquired_at", "created_at",
                    )),
                )

        receipt_path = self.project_root / "receipts/source_receipts.jsonl"
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(
            "".join(
                json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n"
                for item in closure["receipts"]
            ),
            encoding="utf-8",
        )
        restored_snapshot = self.lock_evidence_snapshot(manifest.model_dump(mode="json"))
        expected = compute_locked_snapshot(
            kind="evidence", report=None, manifest=manifest.model_dump(mode="json")
        )
        if restored_snapshot != expected:
            raise SnapshotIntegrityError("恢复快照身份不一致")
        return restored_snapshot
