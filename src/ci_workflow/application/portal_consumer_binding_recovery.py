"""可移植恢复已核验portal消费者绑定（不改写历史快照字节）。

v2证据快照在A/B消费者登记**之前**锁定，因此 ``closure.facts[].consumer_binding``
只是摄取提示（报告类型+行引用），不是已核验消费者身份；恢复空项目时不得把它
当作已接受绑定。已核验绑定只存在于 ``source_portal_consumer_bindings``，本模块
用一个小的版本化sidecar把它绑定到唯一锁定证据快照，并在导入时逐项复核快照
身份、被引用的来源事实、绑定标识/摘要以及报告与领域行语义后才写入。

C 消费者的 ``binding_json`` 使用捕获实例标识承载来源身份，持久化片段使用不可变
来源版本标识；因此 C 绑定必须同时提供外部钉固的原始 C 报告数据（按摘要记入
sidecar），由现行 C 投影从真实类型化观察行重建身份，再逐项对照锁定闭包与已登记
来源事实：行/字段/族/试验、产品—试验关联、披露状态与来源语境、完整定位、捕获
实例→不可变版本的闭包映射、逐字原文与已声明资格分段。缺省该证明时不得恢复 C；
不含 C 的 sidecar 序列化字节与调用方式保持原样。
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

from ci_workflow.application.ctgov_c_design_projection import (
    ELIGIBILITY_SECTION_COMPATIBILITY_RULE,
    replay_ctgov_eligibility_section,
)
from ci_workflow.domain.ids import stable_id
from ci_workflow.renderers.portal.active_fact_projection import (
    ActiveFactBinding,
    DomainCollection,
    ReportCode,
    canonical_source_pointer,
)
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    active_fact_binding_for_c,
)
from ci_workflow.reports.c import DesignObservation
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
# 资格标准分段行：允许按已公布规则从父级原文重放，其余字段必须逐字等于父级标量。
_SECTION_FIELDS = frozenset({"inclusion_criterion", "exclusion_criterion"})


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
    # 可选 C 原始报告证明：仅当存在 C 绑定时必须提供，其摘要同时钉固报告数据。
    c_report_data_sha256: str | None = None

    @field_validator("project_id", "evidence_snapshot_id")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("evidence_snapshot_sha256")
    @classmethod
    def _digest_is_sha256(cls, value: str) -> str:
        return _sha256_text(value)

    @field_validator("c_report_data_sha256")
    @classmethod
    def _optional_digest_is_sha256(cls, value: str | None) -> str | None:
        if value is None:
            return None
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


class _CPortalOriginalProof:
    """外部钉固的原始 C 报告数据，按行重建真实类型化观察身份。

    只有锁定来源事实与原始报告行都齐备时，C 绑定的 ``source_version_id`` 才是
    可靠的科学身份；拒绝自洽但无原始行支撑的 ``binding_json``。
    """

    def __init__(self, report: ReportCPortalData, report_data_sha256: str) -> None:
        rows: dict[str, DesignObservation] = {}
        for row in report.observations:
            if row.row_id in rows:
                raise PortalConsumerBindingRecoveryError(
                    "C 消费者原始报告观察行标识不唯一"
                )
            rows[row.row_id] = row
        self._report = report
        self._rows = rows
        self._products = {item.id: item for item in report.products}
        self._trials = {item.id: item for item in report.trials}
        self._bindings: dict[str, ActiveFactBinding] = {}
        self.sha256 = report_data_sha256

    def row(self, row_id: str) -> DesignObservation:
        try:
            return self._rows[row_id]
        except KeyError as error:
            raise PortalConsumerBindingRecoveryError(
                "C 消费者绑定引用的观察行不在原始报告中"
            ) from error

    def require_product_trial_alignment(self, row: DesignObservation) -> None:
        product = self._products.get(row.product_id) if row.product_id is not None else None
        trial = self._trials.get(row.trial_id)
        if (trial is None or trial.product_id != row.product_id
                or (row.product_id is not None and product is None)):
            raise PortalConsumerBindingRecoveryError("C 消费者产品—试验关联与原始报告不一致")

    def original_binding(self, row_id: str) -> ActiveFactBinding:
        if row_id not in self._bindings:
            try:
                self._bindings[row_id] = active_fact_binding_for_c(self._report, row_id)
            except ValueError as error:
                raise PortalConsumerBindingRecoveryError(
                    "C 消费者原始报告不能重建该观察行绑定"
                ) from error
        return self._bindings[row_id]


class _CPortalClosure:
    """锁定闭包中证明 C 捕获实例→不可变来源版本的显式映射。"""

    def __init__(self, payload: dict[str, Any]) -> None:
        closure = payload.get("closure")
        if not isinstance(closure, dict):
            raise PortalConsumerBindingRecoveryError("C 消费者需要带锁定闭包的证据快照")
        facts = closure.get("facts")
        sources = closure.get("sources")
        if not isinstance(facts, list) or not isinstance(sources, list):
            raise PortalConsumerBindingRecoveryError("C 消费者锁定闭包缺少事实或来源集合")
        fact_by_version: dict[str, dict[str, Any]] = {}
        for item in facts:
            if not isinstance(item, dict):
                raise PortalConsumerBindingRecoveryError("C 消费者锁定闭包事实记录无效")
            version_id = item.get("fact_version_id")
            if (
                not isinstance(version_id, str)
                or not version_id
                or version_id in fact_by_version
            ):
                raise PortalConsumerBindingRecoveryError(
                    "C 消费者锁定闭包事实标识缺失或重复"
                )
            fact_by_version[version_id] = item
        capture_version_by_id: dict[str, str] = {}
        for item in sources:
            if not isinstance(item, dict):
                raise PortalConsumerBindingRecoveryError("C 消费者锁定闭包来源记录无效")
            capture = item.get("capture")
            source_version_id = item.get("source_version_id")
            if (
                not isinstance(capture, dict)
                or not isinstance(source_version_id, str)
                or not source_version_id
            ):
                raise PortalConsumerBindingRecoveryError("C 消费者锁定闭包来源版本缺少采集记录")
            capture_id = capture.get("source_id")
            if (
                not isinstance(capture_id, str)
                or not capture_id
                or capture_id in capture_version_by_id
            ):
                raise PortalConsumerBindingRecoveryError(
                    "C 消费者锁定闭包来源实例缺失或重复"
                )
            capture_version_by_id[capture_id] = source_version_id
        self.fact_by_version = fact_by_version
        self.capture_version_by_id = capture_version_by_id


def _read_c_original_proof(
    path: Path, *, expected_sha256: str | None = None
) -> _CPortalOriginalProof:
    try:
        encoded = path.read_bytes()
    except OSError as error:
        raise PortalConsumerBindingRecoveryError("C 消费者原始报告数据不可读") from error
    digest = hashlib.sha256(encoded).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise PortalConsumerBindingRecoveryError("C 消费者原始报告数据摘要不匹配")
    try:
        report = ReportCPortalData.model_validate_json(encoded)
    except ValidationError as error:
        raise PortalConsumerBindingRecoveryError("C 消费者原始报告数据不符合合同") from error
    return _CPortalOriginalProof(report, digest)


def _require_c_original_binding(
    entry: ConsumerBindingSidecarEntry,
    binding: ActiveFactBinding,
    source: Sequence[Any],
    c_proof: _CPortalOriginalProof,
    c_closure: _CPortalClosure,
) -> None:
    """Prove one C binding against the pinned report row and locked source facts."""
    row = c_proof.row(binding.row_id)
    original = c_proof.original_binding(binding.row_id)
    if original != binding:
        differing = [
            field
            for field in ActiveFactBinding.model_fields
            if getattr(original, field) != getattr(binding, field)
        ]
        raise PortalConsumerBindingRecoveryError(
            "C 消费者绑定与原始报告行身份不一致：" + ",".join(differing)
        )
    c_proof.require_product_trial_alignment(row)
    closure_fact = c_closure.fact_by_version.get(entry.source_fact_version_id)
    if closure_fact is None:
        raise PortalConsumerBindingRecoveryError("C 消费者绑定不在该证据快照的传递闭包内")
    immutable_source_version_id = str(source[0])
    context_json_text = str(source[2])
    content_text = str(source[3])
    closure_scientific_fact = closure_fact.get("fact")
    if not isinstance(closure_scientific_fact, dict):
        raise PortalConsumerBindingRecoveryError("C 消费者锁定闭包缺少科学事实")
    if (
        closure_fact.get("scientific_context_json") != context_json_text
        or closure_fact.get("primary_fragment_id") != str(source[8])
        or hashlib.sha256(context_json_text.encode("utf-8")).hexdigest()
        != closure_fact.get("content_sha256")
        or source[9] != closure_scientific_fact.get("raw_value")
        or source[10] != closure_scientific_fact.get("normalized_value")
        or source[11] != closure_fact.get("review_state")
        or source[12] != closure_fact.get("content_sha256")
    ):
        raise PortalConsumerBindingRecoveryError("C 消费者来源事实与锁定闭包不一致")
    try:
        context = json.loads(context_json_text)
        persisted_locator = json.loads(str(source[1]))
    except json.JSONDecodeError as error:
        raise PortalConsumerBindingRecoveryError(
            "C 消费者来源事实语境或定位不是有效JSON"
        ) from error
    if not isinstance(context, dict) or not isinstance(persisted_locator, dict):
        raise PortalConsumerBindingRecoveryError("C 消费者来源事实语境或定位不是对象")
    expected_field_id = f"c.{row.field_family.value}.{row.field}"
    source_clause_context = (
        row.source_clause_context.model_dump(mode="json")
        if row.source_clause_context is not None
        else None
    )
    if (
        c_closure.capture_version_by_id.get(binding.source_version_id)
        != immutable_source_version_id
    ):
        raise PortalConsumerBindingRecoveryError("C 消费者来源实例与锁定来源版本不一致")
    if (
        context.get("fact_id") != binding.row_id
        or str(source[4]) != binding.row_id
        or context.get("entity_id") != binding.trial_id
        or str(source[5]) != binding.trial_id
        or context.get("field_id") != str(source[6])
        or str(source[6]) != expected_field_id
        or context.get("disclosure_state") != str(source[7])
        or str(source[7]) != row.disclosure_state.value
        or context.get("source_clause_context") != source_clause_context
        or context.get("source_id") != binding.source_version_id
        or not row.group_id.strip()
        or not row.cohort_id.strip()
        or row.relationship_blocking
    ):
        raise PortalConsumerBindingRecoveryError(
            "C 消费者来源事实身份、字段、披露或语境与原始报告不一致"
        )
    canonical_locator = canonical_source_pointer(row.source_locator.model_dump(mode="json"))
    if (
        canonical_source_pointer(context.get("locator")) != canonical_locator
        or canonical_source_pointer(persisted_locator) != canonical_locator
        or canonical_source_pointer(binding.source_pointer) != canonical_locator
    ):
        raise PortalConsumerBindingRecoveryError("C 消费者来源定位与原始报告或来源事实不一致")
    if (
        context.get("original_text") != content_text
        or context.get("raw_value") != content_text
        or context.get("normalized_value") != row.source_text
    ):
        raise PortalConsumerBindingRecoveryError(
            "C 消费者原文、规范值或资格分段与原始报告或来源事实不一致"
        )
    if row.field in _SECTION_FIELDS:
        section_ok = row.compatibility_rule == ELIGIBILITY_SECTION_COMPATIBILITY_RULE
        if section_ok:
            try:
                section_ok = (
                    replay_ctgov_eligibility_section(content_text, row.field)
                    == row.source_text
                )
            except ValueError:
                section_ok = False
        if not section_ok:
            raise PortalConsumerBindingRecoveryError(
                "C 消费者原文、规范值或资格分段与原始报告或来源事实不一致"
            )
    elif row.source_text != content_text:
        raise PortalConsumerBindingRecoveryError(
            "C 消费者原文、规范值或资格分段与原始报告或来源事实不一致"
        )


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
    *,
    c_proof: _CPortalOriginalProof | None = None,
    c_closure: _CPortalClosure | None = None,
) -> ActiveFactBinding:
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
        "SELECT f.source_version_id,f.locator,v.scientific_context_json,"
        "f.content_text,v.fact_id,v.entity_id,v.field_id,v.disclosure_state,"
        "v.primary_fragment_id,v.raw_value,v.normalized_value,v.review_state,v.content_sha256 "
        "FROM fact_versions v "
        "JOIN evidence_fragments f ON f.fragment_id=v.primary_fragment_id "
        "WHERE v.fact_version_id=?",
        (entry.source_fact_version_id,),
    ).fetchone()
    if source is None:
        raise PortalConsumerBindingRecoveryError("消费者绑定引用的来源事实未持久化")
    if entry.report == "C":
        if c_proof is None or c_closure is None:
            raise PortalConsumerBindingRecoveryError(
                "C 消费者缺少外部钉固的原始报告证明"
            )
        _require_c_original_binding(entry, binding, source, c_proof, c_closure)
        return binding
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
    seen_row_scope: set[tuple[str, str]] = set()
    by_fact: dict[str, dict[ReportCode, ActiveFactBinding]] = {}
    for entry in entries:
        if entry.binding_id in seen_ids:
            raise PortalConsumerBindingRecoveryError("消费者绑定标识重复")
        seen_ids.add(entry.binding_id)
        row_scope = (entry.report, entry.row_id)
        if row_scope in seen_row_scope:
            raise PortalConsumerBindingRecoveryError("同一报告行的消费者绑定重复")
        seen_row_scope.add(row_scope)
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
            _canonical_json(
                sidecar.model_dump(mode="json", exclude_none=True)
            ) + "\n"
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
    *,
    c_report_data_path: Path | None = None,
) -> tuple[ActiveFactBinding, ...]:
    """Write only the registry rows bound to this one locked evidence snapshot.

    C bindings additionally require the original C portal report data; its digest
    is pinned in the sidecar and every C row is re-proven against it before any
    byte is written.
    """
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
        c_proof: _CPortalOriginalProof | None = None
        c_closure: _CPortalClosure | None = None
        if any(entry.report == "C" for entry in entries):
            if c_report_data_path is None:
                raise PortalConsumerBindingRecoveryError(
                    "C 消费者导出缺少原始报告数据证明"
                )
            c_proof = _read_c_original_proof(c_report_data_path)
            c_closure = _CPortalClosure(payload)
        bindings = tuple(
            _validated_binding(
                database, entry, snapshot_versions,
                c_proof=c_proof, c_closure=c_closure,
            )
            for entry in entries
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
            c_report_data_sha256=None if c_proof is None else c_proof.sha256,
        ),
    )
    return bindings


def recover_verified_consumer_bindings(
    project_root: Path, sidecar_path: Path, *, c_report_data_path: Path | None = None
) -> tuple[ActiveFactBinding, ...]:
    """Re-verify one sidecar against the locked snapshot and its restored facts.

    Rejects tampered, mismatched, hint-only and conflicting input before writing
    any registry row; replaying an already-recovered sidecar is a no-op.  C
    bindings must be accompanied by the pinned original C report data.
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
    c_proof: _CPortalOriginalProof | None = None
    c_closure: _CPortalClosure | None = None
    if any(entry.report == "C" for entry in sidecar.bindings):
        if sidecar.c_report_data_sha256 is None:
            raise PortalConsumerBindingRecoveryError("C 消费者侧车缺少原始报告数据证明")
        if c_report_data_path is None:
            raise PortalConsumerBindingRecoveryError("C 消费者恢复缺少原始报告数据")
        c_proof = _read_c_original_proof(
            c_report_data_path, expected_sha256=sidecar.c_report_data_sha256
        )
        c_closure = _CPortalClosure(payload)
    database_path = project_root / "state/project.sqlite"
    apply_migrations(database_path)
    with open_database(database_path) as database:
        bindings = tuple(
            _validated_binding(
                database, entry, snapshot_versions,
                c_proof=c_proof, c_closure=c_closure,
            )
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
