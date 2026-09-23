"""Typed user fact saves with append-only versions and atomic A/B/C current delivery.

This is deliberately separate from the historical correction proposal/owner/QC flow.
An explicit user save authorizes the save itself; scientific acceptance remains a
separate state and is never inherited by the new fact version.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import shutil
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime
from enum import StrEnum
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
    read_current_delivery,
)
from ci_workflow.domain.ids import stable_id
from ci_workflow.graph.impact import ImpactEdge, ImpactGraph, ImpactLayer, ImpactNode
from ci_workflow.renderers.portal.active_fact_projection import (
    ActiveFact,
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
from ci_workflow.storage.event_store import EventStore, WorkflowEvent
from ci_workflow.storage.migrations import apply_migrations
from ci_workflow.storage.render_transaction import UnpublishedRenderTransaction
from ci_workflow.storage.sqlite import open_database

ReportCode = Literal["A", "B", "C"]
_REPORTS: tuple[ReportCode, ...] = ("A", "B", "C")
_RESOURCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class UserFactSaveError(RuntimeError):
    """The typed fact save cannot be applied safely."""


class UserFactSaveConflictError(UserFactSaveError):
    """A request id or expected revision conflicts with current state."""


class CurrentDeliveryConflictError(UserFactSaveError):
    """The atomic current pointer or one of its bound files is invalid."""


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


class UserFactEditService:
    """The sole W04 write path for an explicit user fact save."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.database_path = self.project_root / "state" / "project.sqlite"
        apply_migrations(self.database_path)
        self.event_store = EventStore(self.project_root)
        self._after_report_built: Callable[[ReportCode], None] = lambda _report: None

    @contextmanager
    def _exclusive(self) -> Any:
        path = self.project_root / "state" / "user-fact-edit.lock"
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

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
        public_facts = {
            version_id: self._public_fact(self._fact_row(version_id))
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
        facts: dict[str, dict[str, Any]] = {}
        for version_id in current.active_fact_version_ids:
            row = self._fact_row(version_id)
            facts[str(row["fact_id"])] = self._public_fact(row)
        return facts

    def _public_fact(self, row: dict[str, Any]) -> dict[str, Any]:
        context = dict(row["context_payload"])
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
                    visible = self.read_current_delivery()
                    legacy_visible = (
                        visible.request_id == command.request_id
                        and visible.revision == int(existing["result_revision"])
                    )
                    if current_transaction_committed(
                        self.project_root, command.request_id
                    ) or legacy_visible:
                        return UserFactSaveResult.model_validate_json(existing["result_json"])
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
                "SELECT request_digest,status,result_fact_version_id,result_revision,result_json "
                "FROM user_fact_edit_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
        if row is None:
            return None
        return dict(
            zip(
                (
                    "request_digest",
                    "status",
                    "result_fact_version_id",
                    "result_revision",
                    "result_json",
                ),
                row,
                strict=True,
            )
        )

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
            active_facts = {
                str(row["fact_id"]): self._public_fact(row) for row in active_rows
            }
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
        facts = {str(row["fact_id"]): self._public_fact(row) for row in rows}
        active_revision = ActiveFactRevision(
            revision=revision,
            request_id=request_id,
            fact_revision_digest=_fact_digest(fact_version_ids),
            facts=tuple(ActiveFact.model_validate(fact) for fact in facts.values()),
        )
        if (
            previous.builder_input_relative_path is None
            or previous.builder_input_sha256 is None
        ):
            raise CurrentDeliveryConflictError("当前交付缺少原portal builder输入绑定")
        builder_input = self.project_root / previous.builder_input_relative_path
        if (
            not builder_input.is_file()
            or hashlib.sha256(builder_input.read_bytes()).hexdigest()
            != previous.builder_input_sha256
        ):
            raise CurrentDeliveryConflictError("原portal builder输入哈希不一致")
        try:
            if previous.report == "A":
                validate_active_fact_revision_a(
                    ReportAPortalData.model_validate_json(builder_input.read_bytes()),
                    active_revision,
                )
            elif previous.report == "B":
                validate_active_fact_revision_b(
                    ReportBPortalData.model_validate_json(builder_input.read_bytes()),
                    active_revision,
                )
            else:
                validate_active_fact_revision_c(
                    ReportCPortalData.model_validate_json(builder_input.read_bytes()),
                    active_revision,
                )
        except ValueError as error:
            raise CurrentDeliveryConflictError(str(error)) from error

    def _build_report(
        self,
        previous: CurrentReportDelivery,
        *,
        revision: int,
        request_id: str,
        changed_fact_id: str,
        fact_version_ids: tuple[str, ...],
    ) -> CurrentReportDelivery:
        report = previous.report
        version = f"v1-user-r{revision}"
        version_root = self.project_root / "reports" / report / version
        manifest_path = version_root / "html.manifest.json"
        site = version_root / "html"
        rows = [self._fact_row(version_id) for version_id in fact_version_ids]
        facts = {str(row["fact_id"]): self._public_fact(row) for row in rows}
        fact_digest = _fact_digest(fact_version_ids)
        active_revision = ActiveFactRevision(
            revision=revision,
            request_id=request_id,
            fact_revision_digest=fact_digest,
            facts=tuple(ActiveFact.model_validate(fact) for fact in facts.values()),
        )
        if (
            previous.builder_input_relative_path is None
            or previous.builder_input_sha256 is None
        ):
            raise CurrentDeliveryConflictError("当前交付缺少原portal builder输入绑定")
        builder_input = self.project_root / previous.builder_input_relative_path
        if (
            not builder_input.is_file()
            or hashlib.sha256(builder_input.read_bytes()).hexdigest()
            != previous.builder_input_sha256
        ):
            raise CurrentDeliveryConflictError("原portal builder输入哈希不一致")
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
                self.project_root,
                report=report,
                report_version=version,
                run_id=f"user-r{revision}-{report.lower()}",
            )
            staging = transaction.begin()
            if report == "A":
                assert data_a is not None
                render_report_a_site(data_a, staging, active_revision=active_revision)
            elif report == "B":
                assert data_b is not None
                render_report_b_site(data_b, staging, active_revision=active_revision)
            else:
                assert data_c is not None
                render_report_c_site(data_c, staging, active_revision=active_revision)
            receipt_path = staging / "data/consumer-receipt.json"
            receipt = PortalRenderReceipt.model_validate_json(receipt_path.read_bytes())
            graph = self._impact_graph(revision, receipt.consumers, facts)
            changed = next(
                (
                    node
                    for node in graph.nodes
                    if node.layer is ImpactLayer.FACT and node.object_id == changed_fact_id
                ),
                None,
            )
            impact_plan = graph.impact_closure((changed,)) if changed is not None else None
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
        manifest_relative = manifest_path.relative_to(self.project_root).as_posix()
        return CurrentReportDelivery(
            report=report,
            revision=revision,
            request_id=request_id,
            report_version=version,
            site_relative_path=site.relative_to(self.project_root).as_posix(),
            file_hashes=_file_hashes(site),
            fact_version_ids=fact_version_ids,
            fact_revision_digest=_fact_digest(fact_version_ids),
            transaction_manifest_relative_path=manifest_relative,
            transaction_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            builder_input_relative_path=previous.builder_input_relative_path,
            builder_input_sha256=previous.builder_input_sha256,
        )

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
