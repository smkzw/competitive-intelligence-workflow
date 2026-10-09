"""Typed user fact saves with append-only versions and atomic A/B/C current delivery.

This is deliberately separate from the historical correction proposal/owner/QC flow.
An explicit user save authorizes the save itself; scientific acceptance remains a
separate state and is never inherited by the new fact version.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import re
import shutil
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from importlib import metadata
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.application.latest_delivery import (
    CurrentDeliveryBundle,
    CurrentReportDelivery,
    commit_current_transaction,
    current_bundle_sha256,
    current_transaction_committed,
    prepare_current_transaction,
    publish_current_delivery,
    read_committed_historical_generation,
    read_current_delivery,
)
from ci_workflow.domain.ids import stable_id
from ci_workflow.domain.public_provenance import PublicProvenance
from ci_workflow.graph.impact import ImpactEdge, ImpactGraph, ImpactLayer, ImpactNode
from ci_workflow.renderers.portal.active_fact_projection import (
    ActiveFact,
    ActiveFactBinding,
    ActiveFactRevision,
    PortalConsumerNode,
    PortalRenderReceipt,
)
from ci_workflow.renderers.portal.report_a import (
    ReportAPortalData,
    render_report_a_site,
    validate_active_fact_revision_a,
)
from ci_workflow.renderers.portal.report_b import (
    ReportBPortalData,
    render_report_b_site,
    validate_active_fact_revision_b,
)
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    render_report_c_site,
    validate_active_fact_revision_c,
)
from ci_workflow.reports.common.identity_projection import (
    PortalIdentityContext,
    load_identity_binding,
)
from ci_workflow.storage.event_store import EventStore, WorkflowEvent
from ci_workflow.storage.migrations import apply_migrations
from ci_workflow.storage.render_transaction import UnpublishedRenderTransaction
from ci_workflow.storage.sqlite import open_database

ReportCode = Literal["A", "B", "C"]
_REPORTS: tuple[ReportCode, ...] = ("A", "B", "C")
_RESOURCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_PRESENTATION_SOURCE_ROOTS: tuple[tuple[str, Path], ...] = (
    # Conservative retry boundary includes shared science/projection/build code,
    # not just JS/templates: changing any installed first-party source refuses
    # an incomplete retry instead of combining outputs from two versions.
    ("workflow", Path(__file__).resolve().parent.parent),
)
_PRESENTATION_SOURCE_EVENT_TYPE = "user.presentation.render.source"
_PRESENTATION_CANDIDATE_EVENT_TYPE = "user.presentation.rebuilt"
_PRESENTATION_SOURCE_EVENT_KIND = "user-presentation-render-source"
_PRESENTATION_CANDIDATE_EVENT_KIND = "user-presentation-rebuild"
_PRESENTATION_RUN_ID = "user-presentation-rebuild"


class UserFactSaveError(RuntimeError):
    """The typed fact save cannot be applied safely."""


class UserFactSaveConflictError(UserFactSaveError):
    """A request id or expected revision conflicts with current state."""


class CurrentDeliveryConflictError(UserFactSaveError):
    """The atomic current pointer or one of its bound files is invalid."""


class PresentationRebuildError(RuntimeError):
    """The presentation-only current rebuild cannot be applied safely."""


class PresentationRebuildConflictError(PresentationRebuildError):
    """A request id, revision, project, or render-source conflict blocks the rebuild."""


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("用户事实编辑字段不能为空")
    return normalized


def _offset(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("用户事实保存时间必须包含明确时区")
    return value


def _canonical(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _file_hashes(site: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(site.rglob("*")):
        if path.is_symlink():
            raise CurrentDeliveryConflictError("当前交付站点不得包含符号链接")
        if path.is_file():
            result[path.relative_to(site).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return result


def _fact_digest(fact_version_ids: tuple[str, ...]) -> str:
    return hashlib.sha256(
        json.dumps(sorted(fact_version_ids), ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def _source_count_denominator(context: dict[str, Any]) -> int:
    result = context.get("result_context")
    if not isinstance(result, dict):
        raise UserFactSaveError("直接报告人数缺少来源统计上下文")
    candidates = result.get("denominator_candidates")
    if not isinstance(candidates, list):
        raise UserFactSaveError("直接报告人数缺少独立同组分母")
    values = {
        item.get("parsed_value")
        for item in candidates
        if isinstance(item, dict) and item.get("group_id") == result.get("group_id")
        and isinstance(item.get("parsed_value"), int)
    }
    if len(values) != 1:
        raise UserFactSaveError("直接报告人数的分母缺失或存在冲突")
    denominator = next(iter(values))
    if not isinstance(denominator, int) or denominator <= 0:
        raise UserFactSaveError("直接报告人数的分母不可用于当前计数")
    return denominator


def _presentation_source_files(root: Path) -> tuple[tuple[str, str], ...]:
    """Hash the installed presentation files under one component root.

    Byte caches never decide rendered output and must not enter the digest.
    """
    records: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        if "__pycache__" in path.parts or path.suffix == ".pyc" or not path.is_file():
            continue
        records.append(
            (path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
        )
    return tuple(records)


def _installed_presentation_versions() -> dict[str, str]:
    try:
        return {
            "jinja2": metadata.version("jinja2"),
            "pydantic": metadata.version("pydantic"),
        }
    except metadata.PackageNotFoundError as error:
        raise PresentationRebuildError("已安装呈现依赖版本无法读取") from error


def _presentation_render_source_digest() -> str:
    """Digest the exact installed presentation that decides rendered bytes.

    Installed first-party code/templates/assets and Jinja/pydantic versions
    are covered; caches are excluded. This is not a clinical acceptance digest.
    """
    files: list[list[str]] = []
    for name, root in _PRESENTATION_SOURCE_ROOTS:
        if not root.is_dir():
            raise PresentationRebuildError(f"呈现来源目录缺失：{name}")
        files.extend(
            [f"{name}/{relative}", digest]
            for relative, digest in _presentation_source_files(root)
        )
    return _digest({"files": files, "versions": _installed_presentation_versions(),
                    "shared_builder_sha256": hashlib.sha256(
                        Path(__file__).read_bytes()).hexdigest()})


def _presentation_selection(
    current: CurrentDeliveryBundle, requested: tuple[ReportCode, ...] | None
) -> tuple[ReportCode, ...]:
    """Resolve the requested presentation rebuild set against the committed bundle.

    A selection that names a report the committed generation does not contain
    fails closed; it never invents a missing report.
    """
    existing = tuple(item.report for item in current.reports)
    selected = existing if requested is None else requested
    missing = tuple(code for code in selected if code not in existing)
    if missing:
        raise PresentationRebuildConflictError(
            "当前交付不存在所选报告，拒绝凭空重建：" + ",".join(missing)
        )
    return selected


class FactTargetIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_id: str
    fact_version_id: str
    entity_id: str
    field_id: str

    @field_validator("fact_id", "fact_version_id", "entity_id", "field_id")
    @classmethod
    def _valid_id(cls, value: str) -> str:
        normalized = _text(value)
        if _RESOURCE_ID.fullmatch(normalized) is None:
            raise ValueError("事实目标身份不是合法资源标识")
        return normalized


class FactEdit(BaseModel):
    """Closed edit surface; omitted fields retain their current value."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    raw_value: str | None = None
    normalized_value: str | int | float | bool | None = None
    numerator: int | None = Field(default=None, ge=0)
    denominator: int | None = Field(default=None, gt=0)
    timepoint: str | None = None
    time_window: str | None = None
    unit: str | None = None
    normalized_unit: str | None = None
    population: str | None = None
    context: str | None = None
    arm_id: str | None = None
    cohort_id: str | None = None
    endpoint_definition: str | None = None
    event_definition: str | None = None
    scale: str | None = None
    direction: Literal["higher_is_better", "lower_is_better", "neutral"] | None = None
    estimand: str | None = None
    analysis_set: str | None = None
    statistical_form: (
        Literal["crude_rate", "count", "threshold", "adjusted_rate", "ls_mean"] | None
    ) = None
    group: str | None = None
    period: str | None = None
    measure_object: Literal["participants", "events", "person_time", "estimate"] | None = None
    threshold_operator: Literal["<", "<=", ">", ">=", "="] | None = None
    threshold_value: float | None = None
    threshold_unit: str | None = None

    @field_validator(
        "raw_value",
        "timepoint",
        "time_window",
        "unit",
        "normalized_unit",
        "population",
        "context",
        "arm_id",
        "cohort_id",
        "endpoint_definition",
        "event_definition",
        "scale",
        "estimand",
        "analysis_set",
        "group",
        "period",
        "threshold_unit",
    )
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        return None if value is None else _text(value)

    @model_validator(mode="after")
    def _counts_are_consistent(self) -> FactEdit:
        if (
            self.statistical_form == "crude_rate"
            and self.measure_object == "participants"
            and self.numerator is not None
            and self.denominator is not None
            and self.numerator > self.denominator
        ):
            raise ValueError("人数粗率的分子不得大于分母")
        return self

    def changes(self) -> dict[str, object]:
        # A patch is presence-aware: omission and explicit null are distinct.
        return self.model_dump(exclude_unset=True)


class UserFactSaveCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    request_id: str
    project_id: str
    expected_revision: int = Field(ge=0)
    operation: Literal["save", "undo"] = "save"
    target: FactTargetIdentity
    edits: FactEdit
    user_basis: str
    saved_by: str
    saved_at: datetime

    @field_validator("request_id", "project_id", "saved_by")
    @classmethod
    def _id_text(cls, value: str) -> str:
        normalized = _text(value)
        if _RESOURCE_ID.fullmatch(normalized) is None:
            raise ValueError("保存命令身份字段不合法")
        return normalized

    @field_validator("user_basis")
    @classmethod
    def _basis(cls, value: str) -> str:
        return _text(value)

    @field_validator("saved_at")
    @classmethod
    def _saved_at(cls, value: datetime) -> datetime:
        return _offset(value)

    @model_validator(mode="after")
    def _save_has_changes(self) -> UserFactSaveCommand:
        if self.operation == "save" and not self.edits.changes():
            raise ValueError("保存命令至少需要一个合法可编辑字段")
        return self


class UserFactSaveResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str
    project_id: str
    revision: int
    fact_id: str
    fact_version_id: str
    supersedes_fact_version_id: str
    review_state: Literal["user_modified"] = "user_modified"
    derived_crude_rate: float | None = None
    rebuilt_reports: tuple[Literal["A", "B", "C"], ...]
    current_generation_sha256: str
    independent_scientific_acceptance: Literal["not_inherited"] = "not_inherited"


class CurrentPresentationRebuildCommand(BaseModel):
    """Presentation-only current rebuild; it never carries a clinical edit."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    request_id: str
    project_id: str
    expected_revision: int = Field(ge=0)
    reports: tuple[ReportCode, ...] | None = None
    requested_by: str
    requested_at: datetime

    @field_validator("request_id", "project_id", "requested_by")
    @classmethod
    def _id_text(cls, value: str) -> str:
        normalized = _text(value)
        if _RESOURCE_ID.fullmatch(normalized) is None:
            raise ValueError("呈现重建命令身份字段不合法")
        return normalized

    @field_validator("reports")
    @classmethod
    def _reports(
        cls, value: tuple[ReportCode, ...] | None
    ) -> tuple[ReportCode, ...] | None:
        if value is None:
            return None
        if not value:
            raise ValueError("呈现重建报告选择不能为空")
        if len(set(value)) != len(value):
            raise ValueError("呈现重建报告选择不得重复")
        return value

    @field_validator("requested_at")
    @classmethod
    def _requested_at(cls, value: datetime) -> datetime:
        return _offset(value)


class RefreshFieldState(StrEnum):
    UNCHANGED = "unchanged"
    USER_MODIFIED = "user_modified"
    SOURCE_CHANGED = "source_changed"
    CONVERGED = "converged"
    CONFLICT = "conflict"
    SOURCE_WITHDRAWN = "source_withdrawn"


class RefreshFieldComparison(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    field: str
    base_value: Any = None
    user_value: Any = None
    source_value: Any = None
    base_present: bool
    user_present: bool
    source_present: bool
    source_inherited_from_base: bool
    state: RefreshFieldState
    source_version_id: str
    resolution_required: bool
    resolution_options: tuple[Literal["keep_user", "accept_source", "manual"], ...] = ()


class RefreshConflictComparison(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    conflict_id: str
    fact_id: str
    base_fact_version_id: str
    user_fact_version_id: str
    source_version_id: str
    user_lineage: tuple[str, ...]
    field_states: dict[str, RefreshFieldState]
    field_comparisons: dict[str, RefreshFieldComparison]
    requires_explicit_resolution: bool


@contextmanager
def current_delivery_lock(project_root: Path) -> Iterator[None]:
    """Exclusive write lock for the atomic current delivery.

    Shared by the user save path and the source current refresh so two writers
    can never interleave two current generations.
    """
    path = project_root / "state" / "user-fact-edit.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def fact_revision_digest(fact_version_ids: tuple[str, ...]) -> str:
    """Content digest of one current-delivery fact closure."""
    return _fact_digest(fact_version_ids)


def _fact_impact_graph(
    revision: int,
    consumers: tuple[PortalConsumerNode, ...],
    facts: dict[str, dict[str, Any]],
) -> ImpactGraph:
    nodes: list[ImpactNode] = []
    edges: list[ImpactEdge] = []
    for consumer in consumers:
        fact_payload = facts[consumer.fact_id]
        binding_digest = _digest(consumer.binding_identity.model_dump(mode="json"))
        fact = ImpactNode(
            layer=ImpactLayer.FACT,
            object_id=consumer.fact_id,
            revision=revision,
        )
        semantic = ImpactNode(
            layer=ImpactLayer.MEDICAL_SEMANTIC,
            object_id=f"semantic:{consumer.fact_id}:{binding_digest}",
            revision=revision,
        )
        facet = ImpactNode(
            layer=ImpactLayer.FACET,
            object_id=(
                f"facet:{consumer.report}:{consumer.collection}:{consumer.row_id}:"
                f"{consumer.original_row_sha256}"
            ),
            revision=revision,
        )
        page = ImpactNode(
            layer=ImpactLayer.PAGE,
            object_id=f"page:{consumer.report}:{consumer.page_relative_path}",
            report_kinds=frozenset({consumer.report}),
            revision=revision,
        )
        fmt = ImpactNode(
            layer=ImpactLayer.FORMAT,
            object_id=f"html:{consumer.report}",
            revision=revision,
        )
        identities = {
            ImpactLayer.CHART: consumer.chart_consumer,
            ImpactLayer.TABLE: consumer.table_consumer,
            ImpactLayer.NARRATIVE: consumer.narrative_consumer,
            ImpactLayer.INDEX: consumer.index_consumer,
            ImpactLayer.SOURCE_POINTER: consumer.source_binding_consumer,
        }
        artifact_nodes = {
            layer: ImpactNode(layer, identity, revision=revision)
            for layer, identity in identities.items()
        }
        nodes.extend((fact, semantic, facet, page, fmt, *artifact_nodes.values()))
        edges.extend(
            (
                ImpactEdge(fact, semantic),
                ImpactEdge(semantic, facet),
                ImpactEdge(fact, artifact_nodes[ImpactLayer.SOURCE_POINTER]),
                ImpactEdge(page, fmt),
            )
        )
        if (
            fact_payload.get("statistical_form") == "crude_rate"
            and fact_payload.get("measure_object") == "participants"
        ):
            derivation = ImpactNode(
                layer=ImpactLayer.DERIVATION,
                object_id=f"derived:participant-crude-rate:{consumer.fact_id}",
                revision=revision,
            )
            nodes.append(derivation)
            edges.extend((ImpactEdge(fact, derivation), ImpactEdge(derivation, facet)))
        for layer in (
            ImpactLayer.CHART,
            ImpactLayer.TABLE,
            ImpactLayer.NARRATIVE,
            ImpactLayer.INDEX,
        ):
            edges.append(ImpactEdge(facet, artifact_nodes[layer]))
        for artifact_node in artifact_nodes.values():
            edges.append(ImpactEdge(artifact_node, page))
    return ImpactGraph(nodes=tuple(nodes), edges=tuple(edges))


def _bound_builder_input(
    project_root: Path,
    previous: CurrentReportDelivery,
    builder_binding: tuple[str, str] | None,
) -> tuple[Path, str, str]:
    """Resolve and verify the hash-pinned builder input for one report build."""
    if builder_binding is None:
        relative = previous.builder_input_relative_path
        expected = previous.builder_input_sha256
        if relative is None or expected is None:
            raise CurrentDeliveryConflictError("当前交付缺少原portal builder输入绑定")
    else:
        relative, expected = builder_binding
    builder_input = project_root / relative
    if (
        not builder_input.is_file()
        or hashlib.sha256(builder_input.read_bytes()).hexdigest() != expected
    ):
        raise CurrentDeliveryConflictError("原portal builder输入哈希不一致")
    return builder_input, relative, expected


def _bound_identity_context(
    project_root: Path, previous: CurrentReportDelivery,
) -> PortalIdentityContext | None:
    """Restore only the pinned prior source context; never silently discard it."""
    from ci_workflow.storage.content_store import ContentAddressedStore, ContentIntegrityError
    from ci_workflow.storage.source_derivation import source_json_decoder

    store = ContentAddressedStore(project_root)
    relative = f"{previous.site_relative_path}/data/identity-context.json"
    try:
        path = store.resolve_relative(relative)
        projection = store.resolve_relative(
            f"{previous.site_relative_path}/data/identity-projection.json"
        )
        if not path.exists():
            if "data/identity-context.json" in previous.file_hashes:
                raise ValueError("已绑定的身份来源上下文丢失")
            if projection.exists() and json.loads(projection.read_bytes()):
                raise ValueError("旧身份展示缺少可恢复的来源绑定")
            return None
        if hashlib.sha256(path.read_bytes()).hexdigest() != previous.file_hashes.get(
            "data/identity-context.json"
        ):
            raise ValueError("身份来源上下文哈希不一致")
        payload = source_json_decoder().decode(path.read_text())
        if payload.get("schema_version") != "portal-identity-context-1" or not payload.get(
            "graph_asset"
        ):
            raise ValueError("身份来源上下文缺少可重放的资产")
        return load_identity_binding(project_root, payload)
    except (ValueError, KeyError, OSError, ContentIntegrityError) as error:
        raise CurrentDeliveryConflictError(f"身份来源无法恢复：{error}") from error


def preflight_current_report(
    project_root: Path,
    previous: CurrentReportDelivery,
    *,
    revision: int,
    request_id: str,
    fact_version_ids: tuple[str, ...],
    public_facts: Mapping[str, dict[str, Any]],
    builder_binding: tuple[str, str] | None = None,
) -> None:
    """Validate one report's hash-pinned builder input against an active revision.

    Performs no staging write: callers use it to prove the complete affected
    set before any report render transaction begins.
    """
    facts = {fact_id: dict(payload) for fact_id, payload in public_facts.items()}
    active_revision = ActiveFactRevision(
        revision=revision,
        request_id=request_id,
        fact_revision_digest=_fact_digest(fact_version_ids),
        facts=tuple(ActiveFact.model_validate(fact) for fact in facts.values()),
    )
    builder_input, _relative, _expected = _bound_builder_input(
        project_root, previous, builder_binding
    )
    identity_context = _bound_identity_context(project_root, previous)
    try:
        data: ReportAPortalData | ReportBPortalData | ReportCPortalData
        if previous.report == "A":
            data = ReportAPortalData.model_validate_json(builder_input.read_bytes())
            validate_active_fact_revision_a(
                data,
                active_revision,
            )
        elif previous.report == "B":
            data = ReportBPortalData.model_validate_json(builder_input.read_bytes())
            validate_active_fact_revision_b(
                data,
                active_revision,
            )
        else:
            data = ReportCPortalData.model_validate_json(builder_input.read_bytes())
            validate_active_fact_revision_c(
                data,
                active_revision,
            )
        if identity_context is not None:
            identity_context.project(data.product_ids, cutoff=data.data_cutoff)
    except ValueError as error:
        raise CurrentDeliveryConflictError(str(error)) from error


def build_current_report(
    project_root: Path,
    previous: CurrentReportDelivery,
    *,
    revision: int,
    request_id: str,
    changed_fact_id: str,
    fact_version_ids: tuple[str, ...],
    public_facts: Mapping[str, dict[str, Any]],
    report_version: str,
    builder_binding: tuple[str, str] | None = None,
    changed_fact_ids: tuple[str, ...] | None = None,
) -> CurrentReportDelivery:
    """Build one immutable current report version from a hash-pinned builder input.

    ``public_facts`` carries the caller-resolved active fact payloads so the
    user save path and the source current refresh share this exact render
    transaction. ``builder_binding`` re-pins the new delivery's builder input;
    when omitted the previous binding is retained.
    """
    report = previous.report
    version_root = project_root / "reports" / report / report_version
    manifest_path = version_root / "html.manifest.json"
    site = version_root / "html"
    facts = {fact_id: dict(payload) for fact_id, payload in public_facts.items()}
    fact_digest = _fact_digest(fact_version_ids)
    active_revision = ActiveFactRevision(
        revision=revision,
        request_id=request_id,
        fact_revision_digest=fact_digest,
        facts=tuple(ActiveFact.model_validate(fact) for fact in facts.values()),
    )
    builder_input, builder_relative, builder_sha256 = _bound_builder_input(
        project_root, previous, builder_binding
    )
    identity_context = _bound_identity_context(project_root, previous)
    data_a: ReportAPortalData | None = None
    data_b: ReportBPortalData | None = None
    data_c: ReportCPortalData | None = None
    try:
        if report == "A":
            data_a = ReportAPortalData.model_validate_json(builder_input.read_bytes())
            validate_active_fact_revision_a(data_a, active_revision)
        elif report == "B":
            data_b = ReportBPortalData.model_validate_json(builder_input.read_bytes())
            validate_active_fact_revision_b(data_b, active_revision)
        else:
            data_c = ReportCPortalData.model_validate_json(builder_input.read_bytes())
            validate_active_fact_revision_c(data_c, active_revision)
        identity_data = data_a or data_b or data_c
        if identity_context is not None and identity_data is not None:
            identity_context.project(identity_data.product_ids, cutoff=identity_data.data_cutoff)
    except ValueError as error:
        raise CurrentDeliveryConflictError(str(error)) from error
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            manifest.get("request_id") != request_id
            or manifest.get("revision") != revision
            or manifest.get("fact_version_ids") != list(fact_version_ids)
        ):
            raise CurrentDeliveryConflictError("已存在的用户修订产物与重试材料不一致")
        hashes = _file_hashes(site)
        if hashes != manifest.get("file_hashes"):
            raise CurrentDeliveryConflictError("已存在的用户修订产物哈希不一致")
    else:
        transaction = UnpublishedRenderTransaction(
            project_root,
            report=report,
            report_version=report_version,
            run_id=f"user-r{revision}-{report.lower()}",
        )
        staging = transaction.begin()
        if report == "A":
            assert data_a is not None
            # Read only the already hash-bound previous site, never a browser
            # patch or guessed source URL. Legacy sites have no such context.
            context_path = project_root / previous.site_relative_path / "data/render-context.json"
            public = None
            limitation = None
            if context_path.is_file():
                expected = previous.file_hashes.get("data/render-context.json")
                if (
                    context_path.is_symlink()
                    or hashlib.sha256(context_path.read_bytes()).hexdigest() != expected
                ):
                    raise CurrentDeliveryConflictError("来源呈现上下文哈希不一致")
                context = json.loads(context_path.read_bytes())
                if context.get("schema_version") != "a-public-render-context-1":
                    raise CurrentDeliveryConflictError("来源呈现上下文版本不支持")
                if context["public_provenance"] is not None:
                    public = PublicProvenance.model_validate(context["public_provenance"])
                limitation = context["publication_limitation_zh"]
            render_report_a_site(data_a, staging, active_revision=active_revision,
                                 public_provenance=public,
                                 publication_limitation_zh=limitation,
                                 identity_context=identity_context)
        elif report == "B":
            assert data_b is not None
            render_report_b_site(data_b, staging, active_revision=active_revision,
                                 identity_context=identity_context)
        else:
            assert data_c is not None
            render_report_c_site(data_c, staging, active_revision=active_revision,
                                 identity_context=identity_context)
        receipt_path = staging / "data/consumer-receipt.json"
        receipt = PortalRenderReceipt.model_validate_json(receipt_path.read_bytes())
        graph = _fact_impact_graph(revision, receipt.consumers, facts)
        changed_ids = set(changed_fact_ids if changed_fact_ids is not None else (changed_fact_id,))
        changed = tuple(
            node for node in graph.nodes
            if node.layer is ImpactLayer.FACT and node.object_id in changed_ids
        )
        impact_plan = graph.impact_closure(changed) if changed else None
        hashes = _file_hashes(staging)
        manifest = {
            "schema_version": "1.0",
            "report": report,
            "revision": revision,
            "request_id": request_id,
            "fact_version_ids": list(fact_version_ids),
            "fact_revision_digest": fact_digest,
            "file_hashes": hashes,
            "portal_integration": receipt.model_dump(mode="json"),
            "impact_bindings": [
                {
                    "fact_id": consumer.fact_id,
                    "fact_version_id": consumer.fact_version_id,
                    "binding_identity": consumer.binding_identity.model_dump(mode="json"),
                    "original_row_sha256": consumer.original_row_sha256,
                }
                for consumer in receipt.consumers
            ],
            "impact_plan_digest": (
                impact_plan.plan_digest
                if impact_plan is not None
                else _digest({"report": report, "revision": revision, "affected": []})
            ),
            "affected_objects": [
                {"layer": node.layer.value, "object_id": node.object_id}
                for node in (() if impact_plan is None else impact_plan.affected)
            ],
        }
        transaction.commit((_canonical(manifest) + "\n").encode())
    manifest_relative = manifest_path.relative_to(project_root).as_posix()
    return CurrentReportDelivery(
        report=report,
        revision=revision,
        request_id=request_id,
        report_version=report_version,
        site_relative_path=site.relative_to(project_root).as_posix(),
        file_hashes=_file_hashes(site),
        fact_version_ids=fact_version_ids,
        fact_revision_digest=_fact_digest(fact_version_ids),
        transaction_manifest_relative_path=manifest_relative,
        transaction_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        builder_input_relative_path=builder_relative,
        builder_input_sha256=builder_sha256,
    )


class UserFactEditService:
    """The sole W04 write path for an explicit user fact save."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.database_path = self.project_root / "state" / "project.sqlite"
        apply_migrations(self.database_path)
        self.event_store = EventStore(self.project_root)
        self._after_report_built: Callable[[ReportCode], None] = lambda _report: None
        self._source_scope_cache: dict[str, str] | None = None
        self._source_scope_cache_key: str | None = None

    @contextmanager
    def _exclusive(self) -> Any:
        with current_delivery_lock(self.project_root):
            yield

    def initialize_current_delivery(
        self,
        *,
        project_id: str,
        report_sites: dict[str, Path],
        report_data_paths: dict[str, Path],
        fact_version_ids: tuple[str, ...],
        created_at: datetime,
    ) -> CurrentDeliveryBundle:
        """Bind existing report directories once; it never invents missing reports."""
        if read_current_delivery(self.project_root) is not None:
            raise CurrentDeliveryConflictError("当前交付已经初始化")
        reports: list[CurrentReportDelivery] = []
        digest = _fact_digest(fact_version_ids)
        # The reports being adopted define the actual rendered source scope:
        # resolve it from the exact caller bytes before any public fact reads
        # consumer declarations that exist under more than one snapshot.
        scopes: dict[str, str] = {}
        for report, data_path in report_data_paths.items():
            try:
                encoded = Path(data_path).read_bytes()
            except OSError:
                continue
            scope = self._portal_data_scope_from_bytes(encoded)
            if scope is not None:
                scopes[str(report)] = scope
        self._source_scope_cache = scopes
        self._source_scope_cache_key = None
        public_facts = {
            version_id: self._public_fact(self._fact_row(version_id), source_scopes=scopes)
            for version_id in fact_version_ids
        }
        input_dir = self.project_root / "state/user-fact-builder-inputs"
        input_dir.mkdir(parents=True, exist_ok=True)
        for report in _REPORTS:
            site = report_sites.get(report)
            if site is None:
                continue
            source_input = report_data_paths.get(report)
            if (
                source_input is None
                or source_input.suffix.lower() != ".json"
                or source_input.is_symlink()
                or not source_input.is_file()
            ):
                raise CurrentDeliveryConflictError(f"{report}缺少可验证的原builder输入")
            builder_input = input_dir / f"report-{report.lower()}-data.json"
            shutil.copy2(source_input, builder_input)
            resolved = site.resolve()
            if not resolved.is_relative_to(self.project_root) or site.is_symlink():
                raise CurrentDeliveryConflictError("初始报告站点必须位于项目内且不能是符号链接")
            relative = resolved.relative_to(self.project_root).as_posix()
            version = resolved.parent.name
            reports.append(
                CurrentReportDelivery(
                    report=report,
                    revision=0,
                    report_version=version,
                    site_relative_path=relative,
                    file_hashes=_file_hashes(resolved),
                    fact_version_ids=tuple(
                        version_id
                        for version_id, fact in public_facts.items()
                        if any(
                            binding.get("report") == report
                            for binding in fact.get("consumer_bindings", ())
                            if isinstance(binding, dict)
                        )
                    ),
                    fact_revision_digest=_fact_digest(
                        tuple(
                            version_id
                            for version_id, fact in public_facts.items()
                            if any(
                                binding.get("report") == report
                                for binding in fact.get("consumer_bindings", ())
                                if isinstance(binding, dict)
                            )
                        )
                    ),
                    builder_input_relative_path=builder_input.relative_to(
                        self.project_root
                    ).as_posix(),
                    builder_input_sha256=hashlib.sha256(builder_input.read_bytes()).hexdigest(),
                )
            )
        if not reports:
            raise CurrentDeliveryConflictError("没有已存在报告可初始化")
        bundle = CurrentDeliveryBundle(
            project_id=project_id,
            revision=0,
            active_fact_version_ids=fact_version_ids,
            fact_revision_digest=digest,
            reports=tuple(reports),
            created_at=_offset(created_at),
        )
        try:
            return publish_current_delivery(self.project_root, bundle, expected_revision=0)
        except ValueError as error:
            raise CurrentDeliveryConflictError(str(error)) from error

    def read_current_delivery(self) -> CurrentDeliveryBundle:
        try:
            current = read_current_delivery(self.project_root)
        except ValueError as error:
            raise CurrentDeliveryConflictError(str(error)) from error
        if current is None:
            raise CurrentDeliveryConflictError("当前交付尚未初始化")
        return current

    def _fact_row(self, fact_version_id: str) -> dict[str, Any]:
        with open_database(self.database_path) as database:
            row = database.execute(
                "SELECT fact_version_id,fact_id,entity_id,field_id,raw_value,normalized_value,"
                "disclosure_state,review_state,primary_fragment_id,supersedes_fact_version_id,"
                "created_at,content_sha256,scientific_context_json FROM fact_versions "
                "WHERE fact_version_id=?",
                (fact_version_id,),
            ).fetchone()
        if row is None:
            raise UserFactSaveError("目标事实版本不存在")
        names = (
            "fact_version_id",
            "fact_id",
            "entity_id",
            "field_id",
            "raw_value",
            "normalized_value",
            "disclosure_state",
            "review_state",
            "primary_fragment_id",
            "supersedes_fact_version_id",
            "created_at",
            "content_sha256",
            "scientific_context_json",
        )
        result = dict(zip(names, row, strict=True))
        try:
            context = json.loads(result["scientific_context_json"] or "{}")
        except json.JSONDecodeError as error:
            raise UserFactSaveError("目标事实科学语义无法读取") from error
        if not isinstance(context, dict):
            raise UserFactSaveError("目标事实科学语义不是对象")
        result["context_payload"] = context
        return result

    def current_facts(self) -> dict[str, dict[str, Any]]:
        current = self.read_current_delivery()
        return self._public_facts([self._fact_row(v) for v in current.active_fact_version_ids])

    def _public_facts(self, rows: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        # One fully verified scope per batch, never a cross-request bypass of
        # current validation. Repeated whole-site hashing per fact is quadratic.
        scopes = self._current_source_scopes()
        facts: dict[str, dict[str, Any]] = {}
        for row in rows:
            facts[str(row["fact_id"])] = self._public_fact(row, source_scopes=scopes)
        return facts

    def _registered_source_bindings(
        self, row: dict[str, Any], *, source_scopes: Mapping[str, str] | None = None,
    ) -> tuple[ActiveFactBinding, ...]:
        """Follow user revisions to their immutable source-side consumer declarations.

        One scientific fact may carry separately verified consumers under more
        than one immutable evidence snapshot. Identical declarations collapse to
        one; conflicting declarations for the same report row are resolved only
        by the source scope of the actual current rendering, never by insertion
        order or by returning every duplicate declaration. With no resolvable
        current scope a unique single candidate is preserved and genuine
        ambiguity fails closed.
        """
        version_id = str(row["fact_version_id"])
        visited: set[str] = set()
        with open_database(self.database_path) as database:
            while version_id:
                if version_id in visited:
                    raise UserFactSaveError("事实版本继承链存在循环")
                visited.add(version_id)
                records = database.execute(
                    "SELECT report,collection,row_id,binding_json,binding_sha256,"
                    "evidence_snapshot_id FROM source_portal_consumer_bindings "
                    "WHERE source_fact_version_id=? "
                    "ORDER BY report,collection,row_id,evidence_snapshot_id",
                    (version_id,),
                ).fetchall()
                if records:
                    return self._scoped_source_bindings(records, source_scopes=source_scopes)
                predecessor = database.execute(
                    "SELECT supersedes_fact_version_id,fact_id FROM fact_versions "
                    "WHERE fact_version_id=?", (version_id,),
                ).fetchone()
                if predecessor is None or predecessor[1] != row["fact_id"]:
                    raise UserFactSaveError("来源消费者绑定继承链身份不一致")
                version_id = str(predecessor[0]) if predecessor[0] else ""
        return ()

    def _scoped_source_bindings(
        self, records: Sequence[Sequence[Any]], *,
        source_scopes: Mapping[str, str] | None = None,
    ) -> tuple[ActiveFactBinding, ...]:
        """One verified declaration per report row inside the legitimate scope."""
        grouped: dict[tuple[str, str, str], dict[str, list[str]]] = {}
        current_scopes = self._current_source_scopes() if source_scopes is None else source_scopes
        for report, collection, row_id, encoded, digest, snapshot_id in records:
            text = str(encoded)
            if hashlib.sha256(text.encode()).hexdigest() != str(digest):
                raise UserFactSaveError("来源消费者绑定摘要不一致")
            # Current scope excludes historical rows even when a display row
            # was renamed or its bytes happen to be identical.
            scope = current_scopes.get(str(report))
            if scope is not None and str(snapshot_id) != scope:
                continue
            grouped.setdefault(
                (str(report), str(collection), str(row_id)), {}
            ).setdefault(str(snapshot_id), []).append(text)
        bindings: list[ActiveFactBinding] = []
        for key in sorted(grouped):
            by_snapshot = grouped[key]
            variants = {text for texts in by_snapshot.values() for text in texts}
            if len(variants) == 1:
                bindings.append(ActiveFactBinding.model_validate_json(next(iter(variants))))
                continue
            scope = current_scopes.get(key[0])
            scoped = {text for text in by_snapshot.get(scope, ())} if scope is not None else set()
            if len(scoped) == 1:
                bindings.append(ActiveFactBinding.model_validate_json(next(iter(scoped))))
                continue
            raise UserFactSaveError(
                "同一报告行存在多个来源快照的消费者声明，且无法由当前渲染来源作用域裁决"
            )
        return tuple(bindings)

    def _current_source_scopes(self) -> dict[str, str]:
        """Report → evidence snapshot scope of the actual current rendering.

        The scope is read from the hash-pinned builder input of each committed
        current report. A legacy input without that binding yields no scope;
        an explicitly pinned but unavailable/corrupt input fails closed. Cache
        entries belong to the current bundle, not a long-lived service instance.
        """
        try:
            current = read_current_delivery(self.project_root)
        except ValueError as error:
            raise UserFactSaveError("当前交付来源作用域不可核验") from error
        key = current_bundle_sha256(current) if current is not None else None
        if self._source_scope_cache is None or self._source_scope_cache_key != key:
            scopes: dict[str, str] = {}
            if current is not None:
                for delivery in current.reports:
                    relative = delivery.builder_input_relative_path
                    expected = delivery.builder_input_sha256
                    if relative is None or expected is None:
                        continue
                    try:
                        encoded = (self.project_root / relative).read_bytes()
                    except OSError as error:
                        raise UserFactSaveError("当前报告钉固的来源输入不可读") from error
                    if hashlib.sha256(encoded).hexdigest() != expected:
                        raise UserFactSaveError("当前报告钉固的来源输入摘要不一致")
                    scope = self._portal_data_scope_from_bytes(encoded)
                    if scope is not None:
                        scopes[delivery.report] = scope
            self._source_scope_cache = scopes
            self._source_scope_cache_key = key
        return self._source_scope_cache

    @staticmethod
    def _portal_data_scope_from_bytes(encoded: bytes) -> str | None:
        """Evidence snapshot scope declared by one report-data builder input."""
        try:
            payload = json.loads(encoded)
        except json.JSONDecodeError:
            return None
        scope = payload.get("source_evidence_snapshot_id") if isinstance(payload, dict) else None
        return scope if isinstance(scope, str) and scope else None

    def _public_fact(
        self, row: dict[str, Any], *, source_scopes: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        context = dict(row["context_payload"])
        registered = self._registered_source_bindings(row, source_scopes=source_scopes)
        if registered:
            declarations = [binding.model_dump(mode="json") for binding in registered]
            existing = context.get("consumer_bindings")
            if existing is not None and existing != declarations:
                raise UserFactSaveError("来源消费者绑定与事实内旧绑定冲突")
            context["consumer_bindings"] = declarations
            # Legacy projection still expects one common scientific identity.
            # Reject divergent report semantics here rather than silently
            # assigning an A presentation to a B consumer.
            identity_fields = (
                "product_id", "drug_name", "trial_id", "registry_id", "group_id",
                "arm", "cohort_id", "period", "endpoint_definition",
                "event_definition", "statistical_form", "measure_object", "unit",
                "normalized_unit",
            )
            for field in identity_fields:
                values = {json.dumps(getattr(binding, field)) for binding in registered}
                if len(values) != 1:
                    raise UserFactSaveError("多报告消费者科学口径不一致：" + field)
                value = getattr(registered[0], field)
                if field in context and context[field] != value:
                    raise UserFactSaveError("事实与外置消费者身份冲突：" + field)
                context[field] = value
            if (
                registered[0].statistical_form == "count"
                and registered[0].measure_object == "participants"
                and registered[0].collection != "baseline"
            ):
                denominator = _source_count_denominator(context)
                user_edit = context.get("user_edit")
                if isinstance(user_edit, dict) and user_edit.get("cleared") is True:
                    context["numerator"] = None
                    context["denominator"] = None
                else:
                    try:
                        current = float(str(row["normalized_value"]))
                    except (TypeError, ValueError) as error:
                        raise UserFactSaveError("当前报告人数不是可核验整数") from error
                    if (
                        not current.is_integer() or current < 0 or current > denominator
                    ):
                        raise UserFactSaveError("当前报告人数与来源分母矛盾")
                    context["numerator"] = int(current)
                    context["denominator"] = denominator
        with open_database(self.database_path) as database:
            source = database.execute(
                "SELECT f.locator,f.content_text,f.source_version_id "
                "FROM evidence_fragments f WHERE f.fragment_id=?",
                (row["primary_fragment_id"],),
            ).fetchone()
        if source is None:
            raise UserFactSaveError("事实主来源片段不存在")
        context.update(
            {
                "fact_id": row["fact_id"],
                "fact_version_id": row["fact_version_id"],
                "entity_id": row["entity_id"],
                "field_id": row["field_id"],
                "raw_value": row["raw_value"],
                "normalized_value": row["normalized_value"],
                # Source disclosure is immutable in SQLite. The effective
                # current user layer is explicitly overlaid from edit lineage.
                "disclosure_state": (
                    "user_cleared"
                    if isinstance(context.get("user_edit"), dict)
                    and context["user_edit"].get("cleared") is True
                    else row["disclosure_state"]
                ),
                "review_state": row["review_state"],
                "primary_fragment_id": row["primary_fragment_id"],
                "source_locator": str(source[0]),
                "source_quote": str(source[1]),
                "source_version_id": str(source[2]),
            }
        )
        return context

    def save(self, command: UserFactSaveCommand) -> UserFactSaveResult:
        # Revalidate caller data without materializing omitted nested edit fields:
        # doing a full dump here would turn every default None into an explicit clear.
        command = UserFactSaveCommand.model_validate(
            command.model_dump(mode="python", exclude_unset=True)
        )
        request_digest = _digest(command.model_dump(mode="json", exclude_unset=True))
        with self._exclusive():
            existing = self._request_row(command.request_id)
            if existing is not None:
                if existing["request_digest"] != request_digest:
                    raise UserFactSaveConflictError("同一请求标识对应了不同保存载荷")
                if existing["status"] == "complete":
                    completed_result = self._validate_completed_save_request(
                        command, request_digest, existing
                    )
                    committed = read_committed_historical_generation(
                        self.project_root,
                        request_id=command.request_id,
                        project_id=command.project_id,
                        revision=completed_result.revision,
                        generation_sha256=completed_result.current_generation_sha256,
                        previous_fact_version_id=command.target.fact_version_id,
                        fact_version_id=completed_result.fact_version_id,
                    )
                    if committed is not None:
                        rebuilt_reports = tuple(
                            item.report for item in committed.reports
                            if item.revision == completed_result.revision
                        )
                        if completed_result.rebuilt_reports != rebuilt_reports:
                            raise UserFactSaveConflictError(
                                "已完成请求结果与历史current generation不一致"
                            )
                        return completed_result
                result_fact_id = str(existing["result_fact_version_id"])
                revision = int(existing["result_revision"])
                derived_rate = self._derivation_rate(revision, result_fact_id)
            else:
                current = self.read_current_delivery()
                if current.project_id != command.project_id:
                    raise UserFactSaveConflictError("保存命令与当前项目身份不一致")
                if current.revision != command.expected_revision:
                    raise UserFactSaveConflictError("版本冲突：当前事实已被另一标签页更新")
                active_ids = current.active_fact_version_ids
                if command.target.fact_version_id not in active_ids:
                    raise UserFactSaveConflictError("版本冲突：目标事实不是当前revision")
                source = self._fact_row(command.target.fact_version_id)
                if any(
                    source[key] != getattr(command.target, key)
                    for key in ("fact_id", "fact_version_id", "entity_id", "field_id")
                ):
                    raise UserFactSaveConflictError("目标事实完整身份与当前记录不一致")
                revision = current.revision + 1
                result_fact_id, derived_rate = self._stage_fact(
                    command, source=source, revision=revision, request_digest=request_digest
                )
            result = self._finish_save(
                command,
                revision=revision,
                result_fact_version_id=result_fact_id,
                derived_rate=derived_rate,
            )
            return result

    def _request_row(self, request_id: str) -> dict[str, Any] | None:
        with open_database(self.database_path) as database:
            row = database.execute(
                "SELECT request_id,project_id,request_digest,expected_revision,"
                "target_fact_id,target_fact_version_id,result_fact_version_id,"
                "result_revision,status,command_json,result_json "
                "FROM user_fact_edit_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
        if row is None:
            return None
        return dict(
            zip(
                (
                    "request_id",
                    "project_id",
                    "request_digest",
                    "expected_revision",
                    "target_fact_id",
                    "target_fact_version_id",
                    "result_fact_version_id",
                    "result_revision",
                    "status",
                    "command_json",
                    "result_json",
                ),
                row,
                strict=True,
            )
        )

    def _validate_completed_save_request(
        self,
        command: UserFactSaveCommand,
        request_digest: str,
        existing: dict[str, Any],
    ) -> UserFactSaveResult:
        try:
            stored_command = UserFactSaveCommand.model_validate_json(
                str(existing["command_json"])
            )
            result = UserFactSaveResult.model_validate_json(str(existing["result_json"]))
            expected_revision = int(existing["expected_revision"])
            result_revision = int(existing["result_revision"])
        except (TypeError, ValueError) as error:
            raise UserFactSaveConflictError("已完成请求记录无法核验") from error
        if (
            existing["request_id"] != command.request_id
            or existing["project_id"] != command.project_id
            or existing["request_digest"] != request_digest
            or _digest(stored_command.model_dump(mode="json", exclude_unset=True))
            != request_digest
            or expected_revision != command.expected_revision
            or existing["target_fact_id"] != command.target.fact_id
            or existing["target_fact_version_id"] != command.target.fact_version_id
            or existing["result_fact_version_id"] != result.fact_version_id
            or result_revision != command.expected_revision + 1
            or result.request_id != command.request_id
            or result.project_id != command.project_id
            or result.revision != command.expected_revision + 1
            or result.fact_id != command.target.fact_id
            or result.fact_version_id == command.target.fact_version_id
            or result.supersedes_fact_version_id != command.target.fact_version_id
        ):
            raise UserFactSaveConflictError("已完成请求与原保存结果身份不一致")
        with open_database(self.database_path) as database:
            target = database.execute(
                "SELECT fact_id FROM fact_versions WHERE fact_version_id=?",
                (command.target.fact_version_id,),
            ).fetchone()
            result_fact = database.execute(
                "SELECT fact_id,supersedes_fact_version_id FROM fact_versions "
                "WHERE fact_version_id=?",
                (result.fact_version_id,),
            ).fetchone()
        if (
            target is None
            or result_fact is None
            or str(target[0]) != command.target.fact_id
            or str(result_fact[0]) != command.target.fact_id
            or str(result_fact[1]) != command.target.fact_version_id
        ):
            raise UserFactSaveConflictError("已完成请求事实版本与保存结果身份不一致")
        return result

    def _stage_fact(
        self,
        command: UserFactSaveCommand,
        *,
        source: dict[str, Any],
        revision: int,
        request_digest: str,
    ) -> tuple[str, float | None]:
        if command.operation == "undo":
            previous_id = source["supersedes_fact_version_id"]
            if not previous_id:
                raise UserFactSaveError("当前事实没有可撤销的前一版本")
            previous = self._fact_row(str(previous_id))
            context = dict(previous["context_payload"])
            raw_value = previous["raw_value"]
            normalized_value = previous["normalized_value"]
            previous_edit = context.get("user_edit")
            disclosure_state = (
                "user_cleared"
                if isinstance(previous_edit, dict) and previous_edit.get("cleared") is True
                else previous["disclosure_state"]
            )
        else:
            context = dict(source["context_payload"])
            changes = command.edits.changes()
            bindings = self._registered_source_bindings(source)
            source_direct_count = bool(bindings) and all(
                binding.statistical_form == "count"
                and binding.measure_object == "participants"
                and binding.collection != "baseline" for binding in bindings
            )
            if source_direct_count and changes:
                if set(changes) - {"raw_value", "normalized_value"}:
                    raise UserFactSaveError("直接来源人数须单独编辑当前原值，分母是另一来源原子")
                if all(value is not None for value in changes.values()):
                    if set(changes) != {"raw_value", "normalized_value"}:
                        raise UserFactSaveError("直接来源人数修订须同时提供数值文本和规范值")
                    source_denominator = _source_count_denominator(context)
                    try:
                        raw_number = float(str(changes["raw_value"]))
                        normalized_number = float(str(changes["normalized_value"]))
                    except (TypeError, ValueError) as error:
                        raise UserFactSaveError("直接来源人数修订不是有限数值") from error
                    if (
                        not raw_number.is_integer() or raw_number != normalized_number
                        or raw_number < 0 or raw_number > source_denominator
                    ):
                        raise UserFactSaveError("直接来源人数原值、规范值或分母矛盾")
            clear_fields = {field for field, value in changes.items() if value is None}
            numeric_fields = {
                "raw_value", "normalized_value", "numerator", "denominator",
                "threshold_value",
            }
            unsupported_clear = clear_fields - numeric_fields
            if unsupported_clear:
                raise UserFactSaveError(
                    "此字段尚不支持显式清除：" + ",".join(sorted(unsupported_clear))
                )
            if bindings and not source_direct_count and not clear_fields:
                if ("raw_value" in changes) != ("normalized_value" in changes):
                    raise UserFactSaveError("直接来源数值修订须同时提供数值文本和规范值")
                if {"numerator", "denominator", "threshold_value"} & changes.keys():
                    raise UserFactSaveError("来源计数或阈值是独立原子，尚不能随当前数值改写")
            if clear_fields and any(
                field in numeric_fields and value is not None
                for field, value in changes.items()
            ):
                raise UserFactSaveError("同一次保存不能同时清除和设置数值字段")
            is_estimated_value = context.get("statistical_form") in {
                "estimate", "adjusted_rate", "ls_mean",
            }
            if (
                not clear_fields
                and is_estimated_value
                and (("raw_value" in changes) != ("normalized_value" in changes))
            ):
                raise UserFactSaveError("估计值修订必须同时提供当前数值文本和规范值")
            if (
                not clear_fields
                and is_estimated_value
                and ("numerator" in changes or "denominator" in changes)
                and not {"raw_value", "normalized_value"}.issubset(changes)
            ):
                raise UserFactSaveError("估计值的原始计数变化必须同时提供重新核实的估计值")
            context.update(changes)
            declarations = (
                [binding.model_dump(mode="json") for binding in bindings]
                if bindings else (context.get("consumer_bindings") or [])
            )
            sample_size = any(
                isinstance(binding, dict) and binding.get("report") == "C"
                and binding.get("collection") == "observations"
                and binding.get("endpoint_definition") == "planned_or_actual_sample_size"
                for binding in declarations
            )
            if sample_size and not clear_fields and (
                {"raw_value", "normalized_value"} & changes.keys()
            ):
                if not {"raw_value", "normalized_value"}.issubset(changes):
                    raise UserFactSaveError("样本量修订须同时提供数值文本和规范值")
                try:
                    raw_number = float(str(changes["raw_value"]))
                    number = float(str(changes["normalized_value"]))
                    exact = Decimal(str(changes["normalized_value"]))
                    raw_exact = Decimal(str(changes["raw_value"]))
                except (TypeError, ValueError, InvalidOperation) as error:
                    raise UserFactSaveError("样本量须为非负整数，原值与规范值一致") from error
                if (isinstance(changes["normalized_value"], bool)
                    or not math.isfinite(number) or number < 0 or not number.is_integer()
                    or raw_number != number or raw_exact != exact
                    or Decimal(str(number)) != exact):
                    raise UserFactSaveError("样本量须为非负整数，原值与规范值一致")
                # This is the user current axis, never an update to source evidence.
                # Prevent the legacy threshold calculation from reviving the old N.
                context["threshold_value"] = number
                context.setdefault("threshold_unit", context.get("unit"))
            raw_value = changes.get("raw_value", source["raw_value"])
            normalized_value = changes.get("normalized_value", source["normalized_value"])
            source_edit = context.get("user_edit")
            disclosure_state = (
                "user_cleared"
                if isinstance(source_edit, dict) and source_edit.get("cleared") is True
                else source["disclosure_state"]
            )
            if clear_fields:
                raw_value = None
                normalized_value = None
                for field in ("numerator", "denominator", "threshold_value"):
                    context[field] = None
                disclosure_state = "user_cleared"
            elif any(field in numeric_fields for field in changes):
                if disclosure_state == "user_cleared":
                    disclosure_state = "reported_value"
        numerator = context.get("numerator")
        denominator = context.get("denominator")
        is_participant_crude_rate = (
            context.get("statistical_form") == "crude_rate"
            and context.get("measure_object") == "participants"
        )
        if (
            disclosure_state != "user_cleared"
            and is_participant_crude_rate
            and isinstance(numerator, int)
            and isinstance(denominator, int)
            and numerator > denominator
        ):
            raise UserFactSaveError("人数粗率的分子不得大于分母")
        derived_rate: float | None = None
        if (
            is_participant_crude_rate
            and isinstance(numerator, int)
            and isinstance(denominator, int)
        ):
            derived_rate = round(numerator / denominator * 100, 10)
            normalized_value = str(derived_rate)
            raw_value = f"{derived_rate:g}% ({numerator}/{denominator})"
        elif (
            disclosure_state != "user_cleared"
            and context.get("statistical_form") == "threshold"
            and context.get("threshold_value") is not None
        ):
            normalized_value = str(context["threshold_value"])
            raw_value = (
                f"{context.get('threshold_operator', '')}{context['threshold_value']:g} "
                f"{context.get('threshold_unit', context.get('unit', ''))}"
            ).strip()
        if disclosure_state in {"reported_value", "reported_zero"} and (
            raw_value is None or normalized_value is None
        ):
            raise UserFactSaveError("恢复当前数值必须提供完整数值或有效分子/分母")
        context["user_edit"] = {
            "request_id": command.request_id,
            "revision": revision,
            "basis": command.user_basis,
            "saved_by": command.saved_by,
            "saved_at": command.saved_at.isoformat(),
            "operation": command.operation,
            "cleared": disclosure_state == "user_cleared",
            "independent_scientific_acceptance": "not_inherited",
        }
        context_json = _canonical(context)
        content_sha256 = hashlib.sha256(context_json.encode()).hexdigest()
        fact_version_id = stable_id(
            "fact-version", source["fact_id"], str(revision), request_digest, content_sha256
        )
        with open_database(self.database_path) as database:
            database.execute("BEGIN IMMEDIATE")
            database.execute(
                "INSERT INTO fact_versions (fact_version_id,fact_id,entity_id,field_id,raw_value,"
                "normalized_value,disclosure_state,review_state,primary_fragment_id,"
                "supersedes_fact_version_id,created_at,content_sha256,scientific_context_json) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    fact_version_id,
                    source["fact_id"],
                    source["entity_id"],
                    source["field_id"],
                    raw_value,
                    normalized_value,
                    source["disclosure_state"],
                    "user_modified",
                    source["primary_fragment_id"],
                    source["fact_version_id"],
                    command.saved_at.isoformat(),
                    content_sha256,
                    context_json,
                ),
            )
            fragments = database.execute(
                "SELECT fragment_id,evidence_role FROM fact_evidence WHERE fact_version_id=?",
                (source["fact_version_id"],),
            ).fetchall()
            for fragment_id, role in fragments:
                database.execute(
                    "INSERT INTO fact_evidence "
                    "(fact_version_id,fragment_id,evidence_role,created_at) "
                    "VALUES (?,?,?,?)",
                    (fact_version_id, fragment_id, role, command.saved_at.isoformat()),
                )
            if derived_rate is not None:
                derivation_id = stable_id("user-derivation", fact_version_id, "crude-rate")
                database.execute(
                    "INSERT INTO user_fact_derivations (derivation_id,revision,derivation_kind,"
                    "input_fact_version_ids_json,rule_id,rule_version,parameters_json,output_json,"
                    "unit,formula,applicability,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        derivation_id,
                        revision,
                        "crude_rate",
                        _canonical([fact_version_id]),
                        "explicit-n-over-N",
                        "1.0",
                        _canonical({"numerator": numerator, "denominator": denominator}),
                        _canonical({"value": derived_rate}),
                        "%",
                        "numerator / denominator * 100",
                        "仅适用于明确人数分子/分母的粗率；不覆盖调整率或LS mean",
                        command.saved_at.isoformat(),
                    ),
                )
            database.execute(
                "INSERT INTO user_fact_edit_requests (request_id,project_id,request_digest,"
                "expected_revision,target_fact_id,target_fact_version_id,result_fact_version_id,"
                "result_revision,status,command_json,result_json,created_at) "
                "VALUES (?,?,?,?,?,?,?,?,? ,?,NULL,?)",
                (
                    command.request_id,
                    command.project_id,
                    request_digest,
                    command.expected_revision,
                    command.target.fact_id,
                    command.target.fact_version_id,
                    fact_version_id,
                    revision,
                    "staging",
                    command.model_dump_json(exclude_unset=True),
                    command.saved_at.isoformat(),
                ),
            )
        return fact_version_id, derived_rate

    def _derivation_rate(self, revision: int, fact_version_id: str) -> float | None:
        with open_database(self.database_path) as database:
            row = database.execute(
                "SELECT output_json FROM user_fact_derivations WHERE revision=? AND "
                "derivation_kind='crude_rate' AND input_fact_version_ids_json=?",
                (revision, _canonical([fact_version_id])),
            ).fetchone()
        if row is None:
            return None
        value = json.loads(str(row[0])).get("value")
        return float(value) if isinstance(value, int | float) else None

    def _finish_save(
        self,
        command: UserFactSaveCommand,
        *,
        revision: int,
        result_fact_version_id: str,
        derived_rate: float | None,
    ) -> UserFactSaveResult:
        current = self.read_current_delivery()
        if current.revision == revision and current.request_id == command.request_id:
            new_bundle = current
        else:
            if current.revision != command.expected_revision:
                raise UserFactSaveConflictError("版本冲突：当前交付已发生其他更新")
            new_ids = tuple(
                result_fact_version_id if item == command.target.fact_version_id else item
                for item in current.active_fact_version_ids
            )
            if result_fact_version_id not in new_ids:
                raise UserFactSaveConflictError("当前事实闭包已不包含目标版本")
            active_rows = [self._fact_row(version_id) for version_id in new_ids]
            active_facts = self._public_facts(active_rows)
            affected_reports = {
                str(binding["report"])
                for binding in active_facts[command.target.fact_id].get(
                    "consumer_bindings", ()
                )
                if isinstance(binding, dict) and binding.get("report") in _REPORTS
            }
            if not affected_reports:
                raise UserFactSaveError("目标事实没有已声明的真实portal消费者")
            report_fact_ids: dict[str, tuple[str, ...]] = {}
            for report in current.reports:
                if report.report not in affected_reports:
                    continue
                report_fact_ids[report.report] = tuple(
                    version_id
                    for version_id in new_ids
                    if any(
                        isinstance(binding, dict)
                        and binding.get("report") == report.report
                        for binding in active_facts[
                            str(self._fact_row(version_id)["fact_id"])
                        ].get("consumer_bindings", ())
                    )
                )
            # Validate the complete affected set before any report transaction begins.
            # A bad later binding therefore cannot leave an earlier report staging tree.
            for report in current.reports:
                if report.report in affected_reports:
                    self._preflight_report(
                        report,
                        revision=revision,
                        request_id=command.request_id,
                        fact_version_ids=report_fact_ids[report.report],
                    )
            reports: list[CurrentReportDelivery] = []
            for report in current.reports:
                if report.report in affected_reports:
                    reports.append(
                        self._build_report(
                            report,
                            revision=revision,
                            request_id=command.request_id,
                            changed_fact_id=command.target.fact_id,
                            fact_version_ids=report_fact_ids[report.report],
                        )
                    )
                    self._after_report_built(report.report)
                else:
                    reports.append(report)
            new_bundle = CurrentDeliveryBundle(
                project_id=command.project_id,
                revision=revision,
                request_id=command.request_id,
                active_fact_version_ids=new_ids,
                fact_revision_digest=_fact_digest(new_ids),
                reports=tuple(reports),
                created_at=command.saved_at,
            )
            prepare_current_transaction(
                self.project_root,
                request_id=command.request_id,
                previous=current,
                candidate=new_bundle,
            )
        result = UserFactSaveResult(
            request_id=command.request_id,
            project_id=command.project_id,
            revision=revision,
            fact_id=command.target.fact_id,
            fact_version_id=result_fact_version_id,
            supersedes_fact_version_id=command.target.fact_version_id,
            derived_crude_rate=derived_rate,
            rebuilt_reports=tuple(
                item.report for item in new_bundle.reports if item.revision == revision
            ),
            current_generation_sha256=current_bundle_sha256(new_bundle),
        )
        event = WorkflowEvent(
            schema_version="1.0",
            event_id=stable_id("user-fact-save", command.project_id, command.request_id),
            project_id=command.project_id,
            run_id="user-fact-edit",
            event_type="user.fact.saved",
            occurred_at=command.saved_at,
            actor_id=command.saved_by,
            idempotency_key=f"user.fact.save:{command.request_id}",
            payload={
                "command": command.model_dump(mode="json", exclude_unset=True),
                "result": result.model_dump(mode="json"),
                "current_delivery": new_bundle.model_dump(mode="json"),
            },
        )
        self._complete_request(command.request_id, result)
        self.event_store.append(event)
        commit_current_transaction(
            self.project_root,
            request_id=command.request_id,
            candidate=new_bundle,
        )
        if current.revision != revision:
            try:
                publish_current_delivery(
                    self.project_root, new_bundle, expected_revision=command.expected_revision
                )
            except ValueError as error:
                raise UserFactSaveConflictError(str(error)) from error
        return result

    def _complete_request(self, request_id: str, result: UserFactSaveResult) -> None:
        with open_database(self.database_path) as database:
            database.execute(
                "UPDATE user_fact_edit_requests SET status='complete',result_json=? "
                "WHERE request_id=? AND status='staging'",
                (result.model_dump_json(), request_id),
            )

    def _preflight_report(
        self,
        previous: CurrentReportDelivery,
        *,
        revision: int,
        request_id: str,
        fact_version_ids: tuple[str, ...],
    ) -> None:
        rows = [self._fact_row(version_id) for version_id in fact_version_ids]
        facts = self._public_facts(rows)
        preflight_current_report(
            self.project_root,
            previous,
            revision=revision,
            request_id=request_id,
            fact_version_ids=fact_version_ids,
            public_facts=facts,
        )

    def _build_report(
        self,
        previous: CurrentReportDelivery,
        *,
        revision: int,
        request_id: str,
        changed_fact_id: str,
        fact_version_ids: tuple[str, ...],
    ) -> CurrentReportDelivery:
        rows = [self._fact_row(version_id) for version_id in fact_version_ids]
        facts = self._public_facts(rows)
        return build_current_report(
            self.project_root,
            previous,
            revision=revision,
            request_id=request_id,
            changed_fact_id=changed_fact_id,
            fact_version_ids=fact_version_ids,
            public_facts=facts,
            report_version=f"v1-user-r{revision}",
        )

    def rebuild_current_presentation(
        self, command: CurrentPresentationRebuildCommand
    ) -> CurrentDeliveryBundle:
        """Rebuild only the presentation of the selected existing reports.

        The generation revision advances exactly once while the active fact
        closure, source bindings, derivations, and prior user edits stay as
        committed; unselected reports keep their existing delivery.
        """
        command = CurrentPresentationRebuildCommand.model_validate(
            command.model_dump(mode="python", exclude_unset=True)
        )
        request_digest = _digest(command.model_dump(mode="json", exclude_unset=True))
        with self._exclusive():
            current = self.read_current_delivery()
            if current.project_id != command.project_id:
                raise PresentationRebuildConflictError("重建请求与当前项目身份不一致")
            recovered = self._recover_presentation_candidate(
                command, request_digest=request_digest, current=current
            )
            if recovered is not None:
                return recovered
            if current.revision != command.expected_revision:
                raise PresentationRebuildConflictError("版本冲突：当前交付已发生其他更新")
            selected = _presentation_selection(current, command.reports)
            self._bind_presentation_render_source(command, request_digest=request_digest)
            revision = current.revision + 1
            # Validate the complete selected set before any report transaction
            # begins, so a bad later report cannot leave an earlier staging tree.
            for report in current.reports:
                if report.report not in selected:
                    continue
                try:
                    self._preflight_report(
                        report,
                        revision=revision,
                        request_id=command.request_id,
                        fact_version_ids=report.fact_version_ids,
                    )
                except UserFactSaveError as error:
                    raise PresentationRebuildConflictError(
                        f"{report.report}类报告预检未通过：{error}"
                    ) from error
            reports: list[CurrentReportDelivery] = []
            for report in current.reports:
                if report.report not in selected:
                    reports.append(report)
                    continue
                try:
                    rebuilt = self._rebuild_presentation_report(
                        report, revision=revision, request_id=command.request_id
                    )
                except UserFactSaveError as error:
                    raise PresentationRebuildConflictError(
                        f"{report.report}类报告重建未通过核验：{error}"
                    ) from error
                reports.append(rebuilt)
                self._after_report_built(report.report)
                # Verify after each complete render as well as before starting.
                # Mid-batch deployment must never select a mixed generation.
                self._bind_presentation_render_source(command, request_digest=request_digest)
            candidate = CurrentDeliveryBundle(
                project_id=command.project_id,
                revision=revision,
                request_id=command.request_id,
                active_fact_version_ids=current.active_fact_version_ids,
                fact_revision_digest=_fact_digest(current.active_fact_version_ids),
                reports=tuple(reports),
                created_at=command.requested_at,
            )
            self._publish_presentation_candidate(
                command,
                previous=current,
                candidate=candidate,
                request_digest=request_digest,
                announce=True,
            )
            return candidate

    def _recover_presentation_candidate(
        self,
        command: CurrentPresentationRebuildCommand,
        *,
        request_digest: str,
        current: CurrentDeliveryBundle,
    ) -> CurrentDeliveryBundle | None:
        """Return the committed or recorded candidate for an exact replay."""
        payload = self._presentation_event_payload(
            _PRESENTATION_CANDIDATE_EVENT_TYPE, command.request_id
        )
        if payload is None:
            return None
        if str(payload.get("command_digest")) != request_digest:
            raise PresentationRebuildConflictError("同一请求标识对应了不同重建载荷")
        try:
            candidate = CurrentDeliveryBundle.model_validate(payload["candidate"])
        except (KeyError, ValueError) as error:
            raise PresentationRebuildConflictError("已记录重建候选无法读取") from error
        if candidate.project_id != command.project_id:
            raise PresentationRebuildConflictError("已记录重建候选与请求项目不一致")
        if current.request_id == command.request_id:
            if (
                current.revision != candidate.revision
                or current_bundle_sha256(current) != current_bundle_sha256(candidate)
                or not current_transaction_committed(self.project_root, command.request_id)
            ):
                raise PresentationRebuildConflictError("已记录重建结果与已提交current不一致")
            return current
        if current.revision != command.expected_revision:
            raise PresentationRebuildConflictError("版本冲突：当前交付已发生其他更新")
        # The recorded candidate is recovered byte for byte; a retry never
        # re-renders reports and never mixes old and new presentation assets.
        self._publish_presentation_candidate(
            command,
            previous=current,
            candidate=candidate,
            request_digest=request_digest,
            announce=False,
        )
        return candidate

    def _bind_presentation_render_source(
        self, command: CurrentPresentationRebuildCommand, *, request_digest: str
    ) -> None:
        """Record or re-verify the installed render source before any rendering."""
        digest = _presentation_render_source_digest()
        payload = self._presentation_event_payload(
            _PRESENTATION_SOURCE_EVENT_TYPE, command.request_id
        )
        if payload is not None:
            if str(payload.get("command_digest")) != request_digest:
                raise PresentationRebuildConflictError("同一请求标识对应了不同重建载荷")
            if str(payload.get("render_source_digest")) != digest:
                raise PresentationRebuildConflictError("呈现资源已变化，拒绝混用旧新渲染资源")
            return
        self.event_store.append(
            WorkflowEvent(
                schema_version="1.0",
                event_id=stable_id(
                    _PRESENTATION_SOURCE_EVENT_KIND, command.project_id, command.request_id
                ),
                project_id=command.project_id,
                run_id=_PRESENTATION_RUN_ID,
                event_type=_PRESENTATION_SOURCE_EVENT_TYPE,
                occurred_at=command.requested_at,
                actor_id=command.requested_by,
                idempotency_key=f"user.presentation.render.source:{command.request_id}",
                payload={
                    "request_id": command.request_id,
                    "command_digest": request_digest,
                    "render_source_digest": digest,
                },
            )
        )

    def _publish_presentation_candidate(
        self,
        command: CurrentPresentationRebuildCommand,
        *,
        previous: CurrentDeliveryBundle,
        candidate: CurrentDeliveryBundle,
        request_digest: str,
        announce: bool,
    ) -> None:
        """Journal, record, and atomically select one immutable candidate."""
        try:
            prepare_current_transaction(
                self.project_root,
                request_id=command.request_id,
                previous=previous,
                candidate=candidate,
            )
        except ValueError as error:
            raise PresentationRebuildConflictError(
                f"重建事务journal与既有记录不一致：{error}"
            ) from error
        if announce:
            self.event_store.append(
                WorkflowEvent(
                    schema_version="1.0",
                    event_id=stable_id(
                        _PRESENTATION_CANDIDATE_EVENT_KIND,
                        command.project_id,
                        command.request_id,
                    ),
                    project_id=command.project_id,
                    run_id=_PRESENTATION_RUN_ID,
                    event_type=_PRESENTATION_CANDIDATE_EVENT_TYPE,
                    occurred_at=command.requested_at,
                    actor_id=command.requested_by,
                    idempotency_key=f"user.presentation.rebuilt:{command.request_id}",
                    payload={
                        "request_id": command.request_id,
                        "command_digest": request_digest,
                        "candidate": candidate.model_dump(mode="json"),
                    },
                )
            )
        try:
            commit_current_transaction(
                self.project_root, request_id=command.request_id, candidate=candidate
            )
        except ValueError as error:
            raise PresentationRebuildConflictError(
                f"重建事务journal与候选不一致：{error}"
            ) from error
        try:
            publish_current_delivery(
                self.project_root, candidate, expected_revision=previous.revision
            )
        except ValueError as error:
            raise PresentationRebuildConflictError(str(error)) from error

    def _rebuild_presentation_report(
        self,
        previous: CurrentReportDelivery,
        *,
        revision: int,
        request_id: str,
    ) -> CurrentReportDelivery:
        """Rebuild one selected report from its pinned inputs and current facts.

        ``changed_fact_id=""`` keeps the impact record explicitly empty: this
        operation stages no fact, derivation, or source replacement.
        """
        rows = [self._fact_row(version_id) for version_id in previous.fact_version_ids]
        facts = self._public_facts(rows)
        return build_current_report(
            self.project_root,
            previous,
            revision=revision,
            request_id=request_id,
            changed_fact_id="",
            fact_version_ids=previous.fact_version_ids,
            public_facts=facts,
            report_version=f"v1-presentation-r{revision}",
        )

    def _presentation_event_payload(
        self, event_type: str, request_id: str
    ) -> dict[str, Any] | None:
        for event in self.event_store.read_all():
            if event.event_type == event_type and event.payload.get("request_id") == request_id:
                return dict(event.payload)
        return None

    def _copy_tree(self, source: Path, destination: Path) -> None:
        if not source.is_dir() or not source.resolve().is_relative_to(self.project_root):
            raise CurrentDeliveryConflictError("当前报告源目录无效")
        for path in source.rglob("*"):
            if path.is_symlink():
                raise CurrentDeliveryConflictError("报告源目录不得包含符号链接")
        shutil.copytree(source, destination, dirs_exist_ok=True)

    @staticmethod
    def _impact_graph(
        revision: int,
        consumers: tuple[PortalConsumerNode, ...],
        facts: dict[str, dict[str, Any]],
    ) -> ImpactGraph:
        return _fact_impact_graph(revision, consumers, facts)

    def compare_refresh(
        self,
        *,
        fact_id: str,
        base_fact_version_id: str,
        user_fact_version_id: str,
        source_fields: dict[str, object],
        source_version_id: str = "source-version-unspecified",
        source_withdrawn: bool = False,
        request_id: str,
        compared_at: datetime,
        actor_id: str = "refresh-worker",
    ) -> RefreshConflictComparison:
        from ci_workflow.application.refresh_service import RefreshService

        return RefreshService(self.project_root).compare_user_fact_refresh(
            fact_id=fact_id,
            base_fact_version_id=base_fact_version_id,
            user_fact_version_id=user_fact_version_id,
            source_version_id=source_version_id,
            source_fields=source_fields,
            source_withdrawn=source_withdrawn,
            request_id=request_id,
            compared_at=compared_at,
            actor_id=actor_id,
        )
