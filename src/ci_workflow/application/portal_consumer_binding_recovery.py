"""可移植恢复已核验portal消费者绑定（不改写历史快照字节）。

v2证据快照在A/B消费者登记**之前**锁定，因此 ``closure.facts[].consumer_binding``
只是摄取提示（报告类型+行引用），不是已核验消费者身份；恢复空项目时不得把它
当作已接受绑定。已核验绑定只存在于 ``source_portal_consumer_bindings``，本模块
用一个小的版本化sidecar把它绑定到唯一锁定证据快照，并在导入时逐项复核快照
身份、被引用的来源事实、绑定标识/摘要以及报告与领域行语义后才写入。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import tempfile
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from ci_workflow.domain.ids import stable_id
from ci_workflow.renderers.portal.active_fact_projection import (
    ActiveFactBinding,
    DomainCollection,
    ReportCode,
)
from ci_workflow.storage.migrations import apply_migrations
from ci_workflow.storage.snapshot_store import (
    LockedSnapshot,
    SnapshotIntegrityError,
    SnapshotStore,
    compute_locked_snapshot,
)
from ci_workflow.storage.sqlite import open_database

_SIDECAR_SCHEMA_VERSION: Final[Literal["1.0"]] = "1.0"
_BINDING_ID_KIND = "source-portal-binding"
_SNAPSHOT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REPORT_COLLECTIONS: dict[ReportCode, frozenset[str]] = {
    "A": frozenset({"efficacy", "safety"}),
    "B": frozenset({"efficacy", "safety"}),
    "C": frozenset({"observations"}),
}
# A/B consumers of one source atom must not drift apart in scientific identity.
_SHARED_REPORT_IDENTITY = (
    "product_id",
    "drug_name",
    "trial_id",
    "registry_id",
    "group_id",
    "arm",
    "cohort_id",
    "period",
    "endpoint_definition",
    "event_definition",
    "statistical_form",
    "measure_object",
    "unit",
    "normalized_unit",
    "source_version_id",
)
_BINDING_COLUMNS = (
    "binding_id",
    "source_fact_version_id",
    "report",
    "collection",
    "row_id",
    "binding_json",
    "binding_sha256",
    "created_at",
)


class PortalConsumerBindingRecoveryError(RuntimeError):
    """已核验消费者绑定无法作为可移植sidecar安全导出或恢复。"""


def _not_blank(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("消费者绑定恢复字段不能为空")
    return normalized


def _sha256_text(value: str) -> str:
    if _SHA256.fullmatch(value) is None:
        raise ValueError("消费者绑定恢复摘要必须是小写SHA-256")
    return value


def _canonical_json(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


class ConsumerBindingSidecarEntry(BaseModel):
    """One already-registered registry row, carried without re-derivation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    binding_id: str
    source_fact_version_id: str
    report: ReportCode
    collection: DomainCollection
    row_id: str
    binding_json: str
    binding_sha256: str
    created_at: str

    @field_validator(
        "binding_id", "source_fact_version_id", "row_id", "binding_json", "created_at"
    )
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("binding_sha256")
    @classmethod
    def _digest_is_sha256(cls, value: str) -> str:
        return _sha256_text(value)


class ConsumerBindingSidecar(BaseModel):
    """Versioned, snapshot-bound portable carrier of verified consumer bindings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    project_id: str
    contract_version: int = Field(ge=1)
    evidence_snapshot_id: str
    evidence_snapshot_sha256: str
    bindings: tuple[ConsumerBindingSidecarEntry, ...] = Field(min_length=1)

    @field_validator("project_id", "evidence_snapshot_id")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("evidence_snapshot_sha256")
    @classmethod
    def _digest_is_sha256(cls, value: str) -> str:
        return _sha256_text(value)


def _read_sidecar(sidecar_path: Path) -> ConsumerBindingSidecar:
    try:
        payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PortalConsumerBindingRecoveryError(
            "消费者绑定sidecar不可读或不是有效JSON"
        ) from error
    try:
        return ConsumerBindingSidecar.model_validate(payload)
    except ValidationError as error:
        raise PortalConsumerBindingRecoveryError("消费者绑定sidecar合同无效") from error


def _read_snapshot(project_root: Path, locked: LockedSnapshot) -> dict[str, Any]:
    if locked.kind != "evidence" or locked.report is not None:
        raise PortalConsumerBindingRecoveryError("消费者绑定恢复只接受证据快照")
    try:
        payload = SnapshotStore(project_root).read(locked)
    except SnapshotIntegrityError as error:
        raise PortalConsumerBindingRecoveryError(
            "证据快照字节、路径或合同不一致"
        ) from error
    if (
        compute_locked_snapshot(
            kind="evidence", report=None, manifest=payload
        ).snapshot_id
        != locked.snapshot_id
    ):
        raise PortalConsumerBindingRecoveryError("证据快照身份与内容不一致")
    return payload


def _read_locked_snapshot(
    project_root: Path, *, snapshot_id: str, snapshot_sha256: str
) -> dict[str, Any]:
    if _SNAPSHOT_ID.fullmatch(snapshot_id) is None:
        raise PortalConsumerBindingRecoveryError("证据快照标识不合法")
    relative = PurePosixPath("snapshots", "evidence", f"{snapshot_id}.json").as_posix()
    try:
        encoded = project_root.joinpath(*PurePosixPath(relative).parts).read_bytes()
    except OSError as error:
        raise PortalConsumerBindingRecoveryError("证据快照文件不存在或不可读") from error
    if hashlib.sha256(encoded).hexdigest() != snapshot_sha256:
        raise PortalConsumerBindingRecoveryError("证据快照字节摘要不匹配")
    try:
        locked = LockedSnapshot(
            snapshot_id=snapshot_id,
            kind="evidence",
            report=None,
            sha256=snapshot_sha256,
            relative_path=relative,
            byte_size=len(encoded),
        )
    except ValidationError as error:
        raise PortalConsumerBindingRecoveryError("证据快照元数据无效") from error
    return _read_snapshot(project_root, locked)


def _locator_matches_pointer(pointer: str, locator_text: str) -> bool:
    """A rows carry the exact field path; B/C rows carry the full locator object."""
    if pointer == locator_text:
        return True
    try:
        locator = json.loads(locator_text)
    except json.JSONDecodeError:
        return False
    return isinstance(locator, dict) and locator.get("field_path") == pointer


def _entry_from_row(row: Sequence[Any]) -> ConsumerBindingSidecarEntry:
    try:
        return ConsumerBindingSidecarEntry.model_validate(
            dict(zip(_BINDING_COLUMNS, (str(value) for value in row), strict=True))
        )
    except (ValidationError, ValueError) as error:
        raise PortalConsumerBindingRecoveryError(
            "已登记消费者绑定记录字段不合法"
        ) from error


def _validated_binding(
    database: sqlite3.Connection,
    entry: ConsumerBindingSidecarEntry,
    snapshot_versions: frozenset[str],
) -> ActiveFactBinding:
    # No production C registration path exists yet.  A self-consistent sidecar
    # is not proof that a design-observation consumer was ever verified.
    if entry.report == "C":
        raise PortalConsumerBindingRecoveryError(
            "C 消费者尚无已核验登记路线，不能作为恢复绑定"
        )
    if entry.collection not in _REPORT_COLLECTIONS[entry.report]:
        raise PortalConsumerBindingRecoveryError("消费者报告与领域集合不匹配")
    if entry.binding_id != stable_id(
        _BINDING_ID_KIND,
        entry.source_fact_version_id,
        entry.report,
        entry.collection,
        entry.row_id,
    ):
        raise PortalConsumerBindingRecoveryError("消费者绑定标识与来源事实身份不一致")
    if hashlib.sha256(entry.binding_json.encode("utf-8")).hexdigest() != (
        entry.binding_sha256
    ):
        raise PortalConsumerBindingRecoveryError("消费者绑定摘要与绑定内容不一致")
    try:
        binding = ActiveFactBinding.model_validate_json(entry.binding_json)
    except ValidationError as error:
        raise PortalConsumerBindingRecoveryError(
            "消费者绑定不是完整的原消费者科学身份"
        ) from error
    if (binding.report, binding.collection, binding.row_id) != (
        entry.report,
        entry.collection,
        entry.row_id,
    ):
        raise PortalConsumerBindingRecoveryError("消费者绑定记录与科学身份不一致")
    if entry.source_fact_version_id not in snapshot_versions:
        raise PortalConsumerBindingRecoveryError("消费者绑定不在该证据快照的传递闭包内")
    source = database.execute(
        "SELECT f.source_version_id,f.locator,v.scientific_context_json "
        "FROM fact_versions v "
        "JOIN evidence_fragments f ON f.fragment_id=v.primary_fragment_id "
        "WHERE v.fact_version_id=?",
        (entry.source_fact_version_id,),
    ).fetchone()
    if source is None:
        raise PortalConsumerBindingRecoveryError("消费者绑定引用的来源事实未持久化")
    if str(source[0]) != binding.source_version_id:
        raise PortalConsumerBindingRecoveryError("消费者绑定来源版本与来源事实不一致")
    if not _locator_matches_pointer(binding.source_pointer, str(source[1])):
        raise PortalConsumerBindingRecoveryError("消费者绑定来源指针与来源事实定位不一致")
    if entry.report in {"A", "B"}:
        try:
            result = json.loads(str(source[2]))["result_context"]
        except (TypeError, KeyError, json.JSONDecodeError) as error:
            raise PortalConsumerBindingRecoveryError(
                "消费者绑定缺少可复核的来源事实语境"
            ) from error
        domain = "adverse_events" if entry.collection == "safety" else "efficacy"
        if (
            not isinstance(result, dict)
            or str(result.get("trial_id", "")).casefold()
            != binding.trial_id.casefold()
            or result.get("group_id") != binding.group_id
            or result.get("domain") != domain
        ):
            raise PortalConsumerBindingRecoveryError(
                "消费者绑定试验、组别或领域与来源事实语境不一致"
            )
    return binding


def _report_relations(
    entries: tuple[ConsumerBindingSidecarEntry, ...],
) -> dict[str, dict[ReportCode, ActiveFactBinding]]:
    seen_ids: set[str] = set()
    seen_scope: set[tuple[str, str]] = set()
    by_fact: dict[str, dict[ReportCode, ActiveFactBinding]] = {}
    for entry in entries:
        if entry.binding_id in seen_ids:
            raise PortalConsumerBindingRecoveryError("消费者绑定标识重复")
        seen_ids.add(entry.binding_id)
        scope = (entry.source_fact_version_id, entry.report)
        if scope in seen_scope:
            raise PortalConsumerBindingRecoveryError("同一来源事实在同一报告存在冲突的消费者")
        seen_scope.add(scope)
        by_fact.setdefault(entry.source_fact_version_id, {})[entry.report] = (
            ActiveFactBinding.model_validate_json(entry.binding_json)
        )
    for reports in by_fact.values():
        a_binding = reports.get("A")
        b_binding = reports.get("B")
        if b_binding is not None and a_binding is None:
            raise PortalConsumerBindingRecoveryError("共享 B 消费者缺少已核验 A 来源身份")
        if (
            a_binding is not None
            and b_binding is not None
            and any(
                getattr(a_binding, field) != getattr(b_binding, field)
                for field in _SHARED_REPORT_IDENTITY
            )
        ):
            raise PortalConsumerBindingRecoveryError("A/B 消费者来源科学身份不一致")
    return by_fact


def _write_sidecar(destination: Path, sidecar: ConsumerBindingSidecar) -> None:
    try:
        encoded = (
            _canonical_json(sidecar.model_dump(mode="json")) + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise PortalConsumerBindingRecoveryError(
            "消费者绑定sidecar无法规范化序列化"
        ) from error
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        # The caller may choose a path already used by a different frozen
        # candidate.  Never replace those bytes; a matching replay is safe.
        try:
            os.link(temporary, destination)
        except FileExistsError as error:
            if destination.is_symlink() or destination.read_bytes() != encoded:
                raise PortalConsumerBindingRecoveryError(
                    "消费者绑定sidecar目标已存在且内容不同"
                ) from error
    finally:
        temporary.unlink(missing_ok=True)


def export_verified_consumer_bindings(
    project_root: Path,
    evidence_snapshot: LockedSnapshot,
    destination: Path,
) -> tuple[ActiveFactBinding, ...]:
    """Write only the registry rows bound to this one locked evidence snapshot."""
    payload = _read_snapshot(project_root, evidence_snapshot)
    snapshot_versions = frozenset(str(item) for item in payload["fact_version_ids"])
    database_path = project_root / "state/project.sqlite"
    apply_migrations(database_path)
    with open_database(database_path) as database:
        rows = database.execute(
            "SELECT binding_id,source_fact_version_id,report,collection,row_id,"
            "binding_json,binding_sha256,created_at FROM source_portal_consumer_bindings "
            "WHERE evidence_snapshot_id=? "
            "ORDER BY report,collection,row_id,source_fact_version_id",
            (evidence_snapshot.snapshot_id,),
        ).fetchall()
        if not rows:
            raise PortalConsumerBindingRecoveryError(
                "该证据快照没有已核验消费者绑定可导出"
            )
        entries = tuple(_entry_from_row(row) for row in rows)
        bindings = tuple(
            _validated_binding(database, entry, snapshot_versions) for entry in entries
        )
        _report_relations(entries)
    _write_sidecar(
        destination,
        ConsumerBindingSidecar(
            schema_version=_SIDECAR_SCHEMA_VERSION,
            project_id=str(payload["project_id"]),
            contract_version=int(payload["contract_version"]),
            evidence_snapshot_id=evidence_snapshot.snapshot_id,
            evidence_snapshot_sha256=evidence_snapshot.sha256,
            bindings=entries,
        ),
    )
    return bindings


def recover_verified_consumer_bindings(
    project_root: Path, sidecar_path: Path
) -> tuple[ActiveFactBinding, ...]:
    """Re-verify one sidecar against the locked snapshot and its restored facts.

    Rejects tampered, mismatched, hint-only and conflicting input before writing
    any registry row; replaying an already-recovered sidecar is a no-op.
    """
    sidecar = _read_sidecar(sidecar_path)
    payload = _read_locked_snapshot(
        project_root,
        snapshot_id=sidecar.evidence_snapshot_id,
        snapshot_sha256=sidecar.evidence_snapshot_sha256,
    )
    if (sidecar.project_id, sidecar.contract_version) != (
        str(payload["project_id"]),
        int(payload["contract_version"]),
    ):
        raise PortalConsumerBindingRecoveryError(
            "消费者绑定sidecar与证据快照的项目身份或合同版本不一致"
        )
    snapshot_versions = frozenset(str(item) for item in payload["fact_version_ids"])
    database_path = project_root / "state/project.sqlite"
    apply_migrations(database_path)
    with open_database(database_path) as database:
        bindings = tuple(
            _validated_binding(database, entry, snapshot_versions)
            for entry in sidecar.bindings
        )
        by_fact = _report_relations(sidecar.bindings)
        # Preflight the whole requested set before writing any append-only row.
        for entry in sidecar.bindings:
            existing = database.execute(
                "SELECT binding_id,collection,row_id,binding_json,binding_sha256,"
                "evidence_snapshot_id FROM source_portal_consumer_bindings "
                "WHERE source_fact_version_id=? AND report=?",
                (entry.source_fact_version_id, entry.report),
            ).fetchone()
            if existing is not None and tuple(existing) != (
                entry.binding_id,
                entry.collection,
                entry.row_id,
                entry.binding_json,
                entry.binding_sha256,
                sidecar.evidence_snapshot_id,
            ):
                raise PortalConsumerBindingRecoveryError("已登记消费者绑定与该来源事实冲突")
        for version_id, reports in by_fact.items():
            if "B" in reports and "A" not in reports:
                anchor = database.execute(
                    "SELECT binding_json,binding_sha256,evidence_snapshot_id FROM "
                    "source_portal_consumer_bindings WHERE source_fact_version_id=? "
                    "AND report='A'",
                    (version_id,),
                ).fetchone()
                if (
                    anchor is None
                    or str(anchor[2]) != sidecar.evidence_snapshot_id
                    or hashlib.sha256(str(anchor[0]).encode()).hexdigest() != str(anchor[1])
                ):
                    raise PortalConsumerBindingRecoveryError(
                        "共享 B 消费者缺少已核验 A 来源身份"
                    )
        for entry in sidecar.bindings:
            database.execute(
                "INSERT OR IGNORE INTO source_portal_consumer_bindings "
                "(binding_id,source_fact_version_id,evidence_snapshot_id,report,"
                "collection,row_id,binding_json,binding_sha256,created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    entry.binding_id,
                    entry.source_fact_version_id,
                    sidecar.evidence_snapshot_id,
                    entry.report,
                    entry.collection,
                    entry.row_id,
                    entry.binding_json,
                    entry.binding_sha256,
                    entry.created_at,
                ),
            )
    return bindings


__all__ = [
    "ConsumerBindingSidecar",
    "ConsumerBindingSidecarEntry",
    "PortalConsumerBindingRecoveryError",
    "export_verified_consumer_bindings",
    "recover_verified_consumer_bindings",
]
