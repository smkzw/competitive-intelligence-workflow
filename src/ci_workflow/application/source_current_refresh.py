"""来源当前刷新：把已入库、已科学接受的来源事实替换接入当前交付。

边界（ci-r24-100 execution context）：

- 来源刷新不是用户保存。只接受已经入库且 ``review_state='accepted'`` 的来源
  事实原子；候选或未接受原子一律拒绝，来源候选不得自动晋级，也不得伪造
  ``user_modified`` 或改写既有来源原子。
- 用户修订/清除层通过既有 typed 三方比较（base source / user current /
  new source，复用 :class:`~ci_workflow.application.refresh_service.RefreshService`）
  追加式重基线到新来源，保留原来源/用户谱系与 provenance；字段分歧或来源
  撤回必须显式解决，本层失败关闭且不切换 current。
- 受影响报告由新来源原子已登记的 portal 消费者绑定确定；调用方必须为每个
  受影响报告提供哈希钉住的新普通 builder 输入，未受影响的报告不得强制重建。
- 重建复用既有渲染事务、current journal（unprepared/committed generation）
  与 append-only 事件回执：失败后旧 current 整体保持可见；同一请求幂等重试
  复用已暂存事实与产物，不重复版本；同一请求不同载荷或过期 expected_revision
  失败关闭。
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.application.delivered_artifacts import _ordinary
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
from ci_workflow.application.refresh_service import RefreshService, RefreshServiceError
from ci_workflow.application.user_fact_edit import (
    CurrentDeliveryConflictError,
    RefreshConflictComparison,
    RefreshFieldState,
    UserFactEditService,
    UserFactSaveError,
    build_current_report,
    current_delivery_lock,
    fact_revision_digest,
    preflight_current_report,
)
from ci_workflow.domain.ids import stable_id
from ci_workflow.renderers.portal.report_a import ReportAPortalData
from ci_workflow.renderers.portal.report_b import ReportBPortalData, _b_source_view_row
from ci_workflow.renderers.portal.report_c import ReportCPortalData
from ci_workflow.storage.event_store import EventStore, WorkflowEvent
from ci_workflow.storage.migrations import apply_migrations
from ci_workflow.storage.sqlite import open_database

ReportCode = Literal["A", "B", "C"]
_REPORTS: tuple[ReportCode, ...] = ("A", "B", "C")
_EVENT_TYPE = "source.current.refresh.recorded"
_EVENT_KIND = "source-current-refresh"
_RUN_ID = "source-current-refresh"
_OPERATION = "source.current.refresh"
_BUILDER_INPUT_DIR = "state/source-refresh-builder-inputs"
_RESOURCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class SourceCurrentRefreshError(RuntimeError):
    """来源当前刷新合同失败；消息中文陈述事实。"""


class SourceCurrentRefreshConflictError(SourceCurrentRefreshError):
    """请求标识、载荷或 expected_revision 与当前状态冲突。"""


class SourceFactRefusalError(SourceCurrentRefreshError):
    """来源候选、用户层分歧或绑定漂移，刷新必须失败关闭。"""


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("来源刷新字段不能为空")
    return normalized


def _offset(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("来源刷新时间必须包含明确时区")
    return value


def _canonical(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


# ── 机器合同 ─────────────────────────────────────────────────────────────────


class SourceFactReplacement(BaseModel):
    """一个逻辑事实的来源替换：当前活动版本 → 已接受的来源事实原子。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_id: str
    current_fact_version_id: str
    replacement_fact_version_id: str
    replacement_source_version_id: str
    base_fact_version_id: str | None = None
    user_fact_version_id: str | None = None
    rationale_zh: str

    @field_validator(
        "fact_id",
        "current_fact_version_id",
        "replacement_fact_version_id",
        "replacement_source_version_id",
        "base_fact_version_id",
        "user_fact_version_id",
    )
    @classmethod
    def _ids_are_resources(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = _text(value)
        if _RESOURCE_ID.fullmatch(normalized) is None:
            raise ValueError("来源替换身份不是合法资源标识")
        return normalized

    @field_validator("rationale_zh")
    @classmethod
    def _rationale_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @model_validator(mode="after")
    def _lineage_pair_is_explicit(self) -> SourceFactReplacement:
        if (self.base_fact_version_id is None) != (self.user_fact_version_id is None):
            raise ValueError("用户层重基线必须同时声明base与user事实版本")
        if self.replacement_fact_version_id == self.current_fact_version_id:
            raise ValueError("来源替换必须指向新的来源事实版本，不能原地重登记")
        return self


class SourceReportBuilderInput(BaseModel):
    """一个受影响报告的哈希钉住普通 builder 输入。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    report: ReportCode
    input_relative_path: str
    input_sha256: str

    @field_validator("input_relative_path")
    @classmethod
    def _path_is_project_relative(cls, value: str) -> str:
        normalized = _text(value)
        candidate = Path(normalized)
        if candidate.is_absolute() or ".." in candidate.parts or "\\" in normalized:
            raise ValueError("builder输入必须是项目内相对路径")
        if candidate.suffix.lower() != ".json":
            raise ValueError("builder输入必须是JSON载荷")
        return normalized

    @field_validator("input_sha256")
    @classmethod
    def _sha_is_lower_hex(cls, value: str) -> str:
        normalized = _text(value)
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError("builder输入摘要必须是小写SHA-256")
        return normalized


class SourceCurrentRefreshCommand(BaseModel):
    """来源当前刷新命令：请求身份、期望版本、来源替换与 builder 输入。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    request_id: str
    project_id: str
    expected_revision: int = Field(ge=0)
    requested_by: str
    requested_at: datetime
    replacements: tuple[SourceFactReplacement, ...] = Field(min_length=1)
    builder_inputs: tuple[SourceReportBuilderInput, ...] = Field(min_length=1)

    @field_validator("request_id", "project_id", "requested_by")
    @classmethod
    def _ids_are_resources(cls, value: str) -> str:
        normalized = _text(value)
        if _RESOURCE_ID.fullmatch(normalized) is None:
            raise ValueError("来源刷新身份字段不合法")
        return normalized

    @field_validator("requested_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset(value)

    @model_validator(mode="after")
    def _sets_are_unique(self) -> SourceCurrentRefreshCommand:
        fact_ids = [item.fact_id for item in self.replacements]
        if len(set(fact_ids)) != len(fact_ids):
            raise ValueError("同一逻辑事实只能有一条来源替换")
        reports = [item.report for item in self.builder_inputs]
        if len(set(reports)) != len(reports):
            raise ValueError("同一报告只能提供一个builder输入")
        return self


class SourceCurrentRefreshResult(BaseModel):
    """来源刷新的追加式结果回执。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    request_id: str
    project_id: str
    revision: int
    rebuilt_reports: tuple[ReportCode, ...]
    effective_fact_version_ids: dict[str, str]
    appended_fact_version_ids: tuple[str, ...]
    replacement_source_version_ids: tuple[str, ...]
    current_generation_sha256: str


class _ResolvedReplacement(BaseModel):
    """一个来源替换在通过全部身份/绑定/接受校验后的解析结果。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_id: str
    previous_fact_version_id: str
    effective_fact_version_id: str
    replacement_fact_version_id: str
    replacement_source_version_id: str
    rebased_context_json: str | None = None
    rebased_raw_value: str | None = None
    rebased_normalized_value: str | None = None
    rebase_version_id: str | None = None
    comparison: RefreshConflictComparison | None = None
    bindings: tuple[dict[str, Any], ...]
    binding_reports: tuple[ReportCode, ...]


# ── 服务 ─────────────────────────────────────────────────────────────────────


class SourceCurrentRefreshService:
    """把已接受的来源事实替换接入当前交付的受限应用服务。"""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.database_path = self.project_root / "state" / "project.sqlite"
        apply_migrations(self.database_path)
        self.event_store = EventStore(self.project_root)
        # 复用既有 current/user 事实读取与用户修订语义，不复制事实合同。
        self._facts = UserFactEditService(self.project_root)
        self._refresh: RefreshService | None = None
        self._after_report_built: Callable[[ReportCode], None] = lambda _report: None

    # ── 公开入口 ───────────────────────────────────────────────────────────

    def refresh(self, command: SourceCurrentRefreshCommand) -> SourceCurrentRefreshResult:
        """执行一次来源当前刷新；相同请求精确重放返回同一结果。"""
        command = SourceCurrentRefreshCommand.model_validate(
            command.model_dump(mode="python", exclude_unset=True)
        )
        request_digest = _digest(command.model_dump(mode="json", exclude_unset=True))
        claim_key = f"{_OPERATION}:{command.request_id}"
        with current_delivery_lock(self.project_root):
            claimed = self._ledger_entry(claim_key)
            if claimed is not None:
                if claimed["operation"] != _OPERATION or claimed["result_digest"] != _digest(
                    {"request_digest": request_digest}
                ):
                    raise SourceCurrentRefreshConflictError("同一刷新请求标识对应了不同载荷")
                committed = self._committed_result(command)
                if committed is not None:
                    return committed
            current = self._require_current(command)
            resolved = self._resolve_replacements(command, current)
            affected_reports = self._affected_reports(resolved)
            revision = current.revision + 1
            new_active_ids = self._new_active_ids(current, resolved)
            builder_pins = self._verify_builder_inputs(command, affected_reports)
            self._verify_source_builder_values(resolved, builder_pins)
            appended = self._stage_rebases(
                occurred_at=command.requested_at, resolved=resolved
            )
            public_by_version = {
                version_id: self._public_fact(version_id) for version_id in new_active_ids
            }
            report_fact_ids = self._report_fact_ids(
                affected_reports, new_active_ids, public_by_version
            )
            report_public_facts = {
                report: {
                    self._fact_id_of(public_by_version[version_id]): public_by_version[version_id]
                    for version_id in version_ids
                }
                for report, version_ids in report_fact_ids.items()
            }
            # 受影响集合整体预检先于任何渲染事务：后面的坏消费者不能在前面
            # 留下暂存产物。
            for report in affected_reports:
                previous = self._previous_report(current, report)
                try:
                    preflight_current_report(
                        self.project_root,
                        previous,
                        revision=revision,
                        request_id=command.request_id,
                        fact_version_ids=report_fact_ids[report],
                        public_facts=report_public_facts[report],
                        builder_binding=builder_pins[report],
                    )
                except CurrentDeliveryConflictError as error:
                    raise SourceFactRefusalError(
                        f"{report}类报告builder输入未通过核验：{error}"
                    ) from error
            reports: list[CurrentReportDelivery] = []
            for delivery in current.reports:
                if delivery.report not in affected_reports:
                    reports.append(delivery)
                    continue
                changed_fact_id = next(
                    item.fact_id
                    for item in resolved
                    if delivery.report in item.binding_reports
                )
                try:
                    built = build_current_report(
                        self.project_root,
                        delivery,
                        revision=revision,
                        request_id=command.request_id,
                        changed_fact_id=changed_fact_id,
                        fact_version_ids=report_fact_ids[delivery.report],
                        public_facts=report_public_facts[delivery.report],
                        report_version=f"v1-source-r{revision}",
                        builder_binding=builder_pins[delivery.report],
                    )
                except CurrentDeliveryConflictError as error:
                    raise SourceFactRefusalError(
                        f"{delivery.report}类报告重建未通过核验：{error}"
                    ) from error
                reports.append(built)
                self._after_report_built(delivery.report)
            new_bundle = CurrentDeliveryBundle(
                project_id=command.project_id,
                revision=revision,
                request_id=command.request_id,
                active_fact_version_ids=new_active_ids,
                fact_revision_digest=fact_revision_digest(new_active_ids),
                reports=tuple(reports),
                created_at=command.requested_at,
            )
            try:
                prepare_current_transaction(
                    self.project_root,
                    request_id=command.request_id,
                    previous=current,
                    candidate=new_bundle,
                )
            except ValueError as error:
                raise SourceCurrentRefreshConflictError(
                    f"刷新事务journal与既有记录不一致：{error}"
                ) from error
            result = SourceCurrentRefreshResult(
                request_id=command.request_id,
                project_id=command.project_id,
                revision=revision,
                rebuilt_reports=affected_reports,
                effective_fact_version_ids={
                    item.fact_id: item.effective_fact_version_id for item in resolved
                },
                appended_fact_version_ids=tuple(sorted(appended)),
                replacement_source_version_ids=tuple(
                    sorted({item.replacement_source_version_id for item in resolved})
                ),
                current_generation_sha256=current_bundle_sha256(new_bundle),
            )
            self._record_claim(claim_key, request_digest=request_digest)
            self.event_store.append(
                WorkflowEvent(
                    schema_version="1.0",
                    event_id=stable_id(
                        _EVENT_KIND, command.project_id, command.request_id
                    ),
                    project_id=command.project_id,
                    run_id=_RUN_ID,
                    event_type=_EVENT_TYPE,
                    occurred_at=command.requested_at,
                    actor_id=command.requested_by,
                    idempotency_key=claim_key,
                    payload={
                        "request_id": command.request_id,
                        "command": command.model_dump(mode="json", exclude_unset=True),
                        "result": result.model_dump(mode="json"),
                    },
                )
            )
            commit_current_transaction(
                self.project_root,
                request_id=command.request_id,
                candidate=new_bundle,
            )
            publish_current_delivery(
                self.project_root, new_bundle, expected_revision=current.revision
            )
            return result

    # ── 当前交付与请求恢复 ─────────────────────────────────────────────────

    def _require_current(
        self, command: SourceCurrentRefreshCommand
    ) -> CurrentDeliveryBundle:
        current = read_current_delivery(self.project_root)
        if current is None:
            raise SourceCurrentRefreshConflictError("当前交付尚未初始化，不能执行来源刷新")
        if current.project_id != command.project_id:
            raise SourceCurrentRefreshConflictError("刷新请求与当前项目身份不一致")
        if current.revision != command.expected_revision:
            raise SourceCurrentRefreshConflictError("版本冲突：当前事实已被其他更新推进")
        return current

    def _ledger_entry(self, key: str) -> dict[str, Any] | None:
        with open_database(self.database_path) as database:
            row = database.execute(
                "SELECT operation,result_digest FROM idempotency_keys WHERE idempotency_key=?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        return {"operation": str(row[0]), "result_digest": str(row[1])}

    def _record_claim(self, key: str, *, request_digest: str) -> None:
        expected = _digest({"request_digest": request_digest})
        with open_database(self.database_path) as database:
            database.execute(
                "INSERT OR IGNORE INTO idempotency_keys "
                "(idempotency_key,operation,result_digest,created_at) VALUES (?,?,?,?)",
                (key, _OPERATION, expected, datetime.now().astimezone().isoformat()),
            )
            row = database.execute(
                "SELECT operation,result_digest FROM idempotency_keys WHERE idempotency_key=?",
                (key,),
            ).fetchone()
        if row is None or str(row[0]) != _OPERATION or str(row[1]) != expected:
            raise SourceCurrentRefreshConflictError("同一刷新请求标识对应了不同载荷")

    def _committed_result(
        self, command: SourceCurrentRefreshCommand
    ) -> SourceCurrentRefreshResult | None:
        """只有已提交 current generation 才构成完成证明；事件标题与 prepared journal 不算。"""
        current = read_current_delivery(self.project_root)
        if (
            current is None
            or current.request_id != command.request_id
            or current.revision != command.expected_revision + 1
            or not current_transaction_committed(self.project_root, command.request_id)
        ):
            return None
        for event in self.event_store.read_all():
            if event.event_type != _EVENT_TYPE:
                continue
            if event.payload.get("request_id") != command.request_id:
                continue
            result = SourceCurrentRefreshResult.model_validate(event.payload["result"])
            if (
                result.revision != current.revision
                or result.project_id != command.project_id
                or result.current_generation_sha256 != current_bundle_sha256(current)
            ):
                raise SourceCurrentRefreshConflictError("已记录刷新结果与已提交current不一致")
            return result
        return None

    # ── 替换解析 ───────────────────────────────────────────────────────────

    def _resolve_replacements(
        self,
        command: SourceCurrentRefreshCommand,
        current: CurrentDeliveryBundle,
    ) -> tuple[_ResolvedReplacement, ...]:
        resolved: list[_ResolvedReplacement] = []
        for replacement in command.replacements:
            if replacement.current_fact_version_id not in current.active_fact_version_ids:
                raise SourceCurrentRefreshConflictError("替换目标不是当前revision的活动事实")
            current_row = self._fact_row(replacement.current_fact_version_id)
            if str(current_row["fact_id"]) != replacement.fact_id:
                raise SourceCurrentRefreshConflictError("替换目标事实身份与当前记录不一致")
            replacement_row = self._fact_row(replacement.replacement_fact_version_id)
            self._assert_accepted_atom(replacement, current_row, replacement_row)
            if replacement.user_fact_version_id is not None:
                resolved.append(
                    self._resolve_user_lineage(command, replacement, current_row, replacement_row)
                )
            else:
                if str(current_row["review_state"]) == "user_modified":
                    raise SourceFactRefusalError(
                        "当前事实存在用户修订层，来源刷新必须显式声明base/user谱系"
                    )
                resolved.append(
                    self._resolved_plain_replacement(replacement, replacement_row)
                )
        return tuple(resolved)

    def _assert_accepted_atom(
        self,
        replacement: SourceFactReplacement,
        current_row: dict[str, Any],
        replacement_row: dict[str, Any],
    ) -> None:
        """只在已接受来源原子上证明同一事实、实体、字段与真实来源绑定。"""
        review_state = str(replacement_row["review_state"])
        if review_state != "accepted":
            raise SourceFactRefusalError(
                f"来源替换必须是已接受事实，当前状态为{review_state}，候选不得自动晋级"
            )
        if str(replacement_row["fact_id"]) != replacement.fact_id:
            raise SourceFactRefusalError("来源替换事实身份不一致")
        for key in ("entity_id", "field_id"):
            if str(replacement_row[key]) != str(current_row[key]):
                raise SourceFactRefusalError(f"来源替换跨越了同一逻辑事实的{key}")
        context_text = str(replacement_row["scientific_context_json"] or "")
        try:
            context = json.loads(context_text)
        except json.JSONDecodeError as error:
            raise SourceFactRefusalError("来源替换缺少可读取的科学语义上下文") from error
        if not isinstance(context, dict) or not context:
            raise SourceFactRefusalError("来源替换缺少完整科学语义上下文")
        for column in ("raw_value", "normalized_value", "entity_id", "field_id"):
            if column in context and context[column] != replacement_row[column]:
                raise SourceFactRefusalError(f"来源替换的{column}与科学语义上下文不一致")
        fragment = self._fragment_row(str(replacement_row["primary_fragment_id"]))
        if str(fragment["source_version_id"]) != replacement.replacement_source_version_id:
            raise SourceFactRefusalError("来源替换的声明来源版本与实际片段绑定不一致")
        with open_database(self.database_path) as database:
            evidence = database.execute(
                "SELECT 1 FROM fact_evidence WHERE fact_version_id=? AND fragment_id=? "
                "AND evidence_role='primary'",
                (
                    str(replacement_row["fact_version_id"]),
                    str(replacement_row["primary_fragment_id"]),
                ),
            ).fetchone()
        if evidence is None:
            raise SourceFactRefusalError("来源替换缺少主证据片段绑定")

    def _resolved_plain_replacement(
        self,
        replacement: SourceFactReplacement,
        replacement_row: dict[str, Any],
    ) -> _ResolvedReplacement:
        public = self._public_fact_for_row(replacement_row)
        bindings, reports = self._legal_bindings(public)
        return _ResolvedReplacement(
            fact_id=replacement.fact_id,
            previous_fact_version_id=replacement.current_fact_version_id,
            effective_fact_version_id=replacement.replacement_fact_version_id,
            replacement_fact_version_id=replacement.replacement_fact_version_id,
            replacement_source_version_id=replacement.replacement_source_version_id,
            bindings=bindings,
            binding_reports=reports,
        )

    def _resolve_user_lineage(
        self,
        command: SourceCurrentRefreshCommand,
        replacement: SourceFactReplacement,
        current_row: dict[str, Any],
        replacement_row: dict[str, Any],
    ) -> _ResolvedReplacement:
        base_id = replacement.base_fact_version_id
        user_id = replacement.user_fact_version_id
        if base_id is None or user_id is None:
            raise SourceFactRefusalError("用户层重基线缺少base/user事实版本")
        base_row = self._fact_row(base_id)
        user_row = self._fact_row(user_id)
        for row in (base_row, user_row):
            if str(row["fact_id"]) != replacement.fact_id:
                raise SourceFactRefusalError("用户层谱系跨越了逻辑事实身份")
        self._assert_rebase_lineage(current_row, replacement, base_id, user_id)
        public = self._public_fact_for_row(replacement_row)
        bindings, reports = self._legal_bindings(public)
        try:
            comparison = self._compare_service().compare_user_fact_refresh(
                fact_id=replacement.fact_id,
                base_fact_version_id=base_id,
                user_fact_version_id=user_id,
                source_version_id=replacement.replacement_source_version_id,
                source_fields=_comparison_fields(replacement_row),
                source_withdrawn=False,
                request_id=f"{command.request_id}:{replacement.fact_id}",
                compared_at=command.requested_at,
                actor_id=command.requested_by,
            )
        except RefreshServiceError as error:
            raise SourceFactRefusalError(f"三方比较失败关闭：{error}") from error
        if comparison.requires_explicit_resolution:
            conflicts = sorted(
                field
                for field, state in comparison.field_states.items()
                if state in {RefreshFieldState.CONFLICT, RefreshFieldState.SOURCE_WITHDRAWN}
            )
            raise SourceFactRefusalError(
                "用户层与新来源在字段上分歧或来源撤回，必须先显式解决："
                + "、".join(conflicts)
            )
        context, raw_value, normalized_value, version_id = self._rebase_payload(
            command,
            replacement,
            base_id=base_id,
            user_row=user_row,
            source_public=public,
            comparison=comparison,
            bindings=bindings,
        )
        return _ResolvedReplacement(
            fact_id=replacement.fact_id,
            previous_fact_version_id=replacement.current_fact_version_id,
            effective_fact_version_id=version_id,
            replacement_fact_version_id=replacement.replacement_fact_version_id,
            replacement_source_version_id=replacement.replacement_source_version_id,
            rebased_context_json=context,
            rebased_raw_value=raw_value,
            rebased_normalized_value=normalized_value,
            rebase_version_id=version_id,
            comparison=comparison,
            bindings=bindings,
            binding_reports=reports,
        )

    def _assert_rebase_lineage(
        self,
        current_row: dict[str, Any],
        replacement: SourceFactReplacement,
        base_id: str,
        user_id: str,
    ) -> None:
        """当前活动版本必须是声明的用户版本本身或其已记录的追加rebase。"""
        if str(current_row["fact_version_id"]) == user_id:
            return
        context = current_row.get("context_payload")
        user_edit = context.get("user_edit") if isinstance(context, dict) else None
        rebase = user_edit.get("rebase") if isinstance(user_edit, dict) else None
        if (
            not isinstance(rebase, dict)
            or rebase.get("original_user_fact_version_id") != user_id
            or rebase.get("original_base_fact_version_id") != base_id
        ):
            raise SourceFactRefusalError("当前事实不是声明用户谱系的追加rebase")

    def _rebase_payload(
        self,
        command: SourceCurrentRefreshCommand,
        replacement: SourceFactReplacement,
        *,
        base_id: str,
        user_row: dict[str, Any],
        source_public: dict[str, Any],
        comparison: RefreshConflictComparison,
        bindings: tuple[dict[str, Any], ...],
    ) -> tuple[str, str | None, str | None, str]:
        """按既有typed三方比较结果重基线用户层；不借用旧来源标识或行摘要。"""
        user_context = user_row.get("context_payload")
        user_edit = user_context.get("user_edit") if isinstance(user_context, dict) else None
        if not isinstance(user_edit, dict):
            raise SourceFactRefusalError("用户事实版本缺少完整user_edit provenance")
        # 基线取新来源的完整公共载荷（含权威科学身份与来源绑定），再按typed
        # 三方比较逐字段落定：用户修改/收敛保留用户值，其余跟随新来源。
        target: dict[str, Any] = {
            key: value
            for key, value in source_public.items()
            if key not in {"user_edit", "consumer_bindings", "review_state", "fact_version_id"}
        }
        for field, item in comparison.field_comparisons.items():
            target[field] = (
                item.user_value
                if item.state in {RefreshFieldState.USER_MODIFIED, RefreshFieldState.CONVERGED}
                else item.source_value
            )
        # 绑定由新来源原子提供：重基线版本不得携带旧来源版本或旧行摘要。
        target["consumer_bindings"] = [dict(binding) for binding in bindings]
        cleared = user_edit.get("cleared") is True
        raw_value = target.get("raw_value")
        normalized_value = target.get("normalized_value")
        if cleared and (raw_value is not None or normalized_value is not None):
            raise SourceFactRefusalError("显式清除的用户层重基线后恢复了数值，必须失败关闭")
        if not cleared and raw_value is None and normalized_value is None:
            raise SourceFactRefusalError("用户层重基线缺少当前数值且并非显式清除")
        user_id = replacement.user_fact_version_id
        target["user_edit"] = {
            **user_edit,
            "rebase": {
                "original_user_fact_version_id": user_id,
                "original_base_fact_version_id": base_id,
                "rebased_on_source_fact_version_id": replacement.replacement_fact_version_id,
                "rebased_on_source_version_id": replacement.replacement_source_version_id,
                "refresh_request_id": command.request_id,
                "rebased_by": command.requested_by,
                "rebased_at": command.requested_at.isoformat(),
            },
        }
        context_json = _canonical(target)
        content_sha256 = _sha256_bytes(context_json.encode("utf-8"))
        version_id = stable_id(
            "fact-version",
            "source-current-rebase",
            replacement.fact_id,
            str(command.expected_revision + 1),
            command.request_id,
            content_sha256,
        )
        return context_json, raw_value, normalized_value, version_id

    # ── 暂存重基线事实（append-only，幂等） ────────────────────────────────

    def _stage_rebases(
        self,
        *,
        occurred_at: datetime,
        resolved: tuple[_ResolvedReplacement, ...],
    ) -> tuple[str, ...]:
        appended: list[str] = []
        for item in resolved:
            if item.rebase_version_id is None or item.rebased_context_json is None:
                continue
            appended.append(item.rebase_version_id)
            content_sha256 = _sha256_bytes(item.rebased_context_json.encode("utf-8"))
            with open_database(self.database_path) as database:
                existing = database.execute(
                    "SELECT content_sha256,scientific_context_json FROM fact_versions "
                    "WHERE fact_version_id=?",
                    (item.rebase_version_id,),
                ).fetchone()
                if existing is not None:
                    if tuple(existing) != (content_sha256, item.rebased_context_json):
                        raise SourceCurrentRefreshConflictError("同一rebase事实版本对应了不同内容")
                    continue
                replacement_row = self._fact_row(item.replacement_fact_version_id)
                database.execute("BEGIN IMMEDIATE")
                database.execute(
                    "INSERT INTO fact_versions (fact_version_id,fact_id,entity_id,field_id,"
                    "raw_value,normalized_value,disclosure_state,review_state,"
                    "primary_fragment_id,supersedes_fact_version_id,created_at,content_sha256,"
                    "scientific_context_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        item.rebase_version_id,
                        item.fact_id,
                        replacement_row["entity_id"],
                        replacement_row["field_id"],
                        item.rebased_raw_value,
                        item.rebased_normalized_value,
                        replacement_row["disclosure_state"],
                        "user_modified",
                        replacement_row["primary_fragment_id"],
                        item.replacement_fact_version_id,
                        occurred_at.isoformat(),
                        content_sha256,
                        item.rebased_context_json,
                    ),
                )
                fragments = database.execute(
                    "SELECT fragment_id,evidence_role FROM fact_evidence WHERE fact_version_id=?",
                    (str(replacement_row["fact_version_id"]),),
                ).fetchall()
                for fragment_id, role in fragments:
                    database.execute(
                        "INSERT OR IGNORE INTO fact_evidence "
                        "(fact_version_id,fragment_id,evidence_role,created_at) VALUES (?,?,?,?)",
                        (item.rebase_version_id, fragment_id, role, occurred_at.isoformat()),
                    )
        return tuple(appended)

    # ── 受影响报告与builder输入 ────────────────────────────────────────────

    def _affected_reports(
        self, resolved: tuple[_ResolvedReplacement, ...]
    ) -> tuple[ReportCode, ...]:
        reports = {report for item in resolved for report in item.binding_reports}
        return tuple(sorted(reports, key=lambda item: _REPORTS.index(item)))

    def _verify_builder_inputs(
        self,
        command: SourceCurrentRefreshCommand,
        affected_reports: tuple[ReportCode, ...],
    ) -> dict[ReportCode, tuple[str, str]]:
        declared = {item.report: item for item in command.builder_inputs}
        missing = sorted(
            (report for report in affected_reports if report not in declared),
            key=lambda item: _REPORTS.index(item),
        )
        if missing:
            raise SourceFactRefusalError(
                "受影响报告缺少新builder输入，不能重建：" + "、".join(missing)
            )
        extra = sorted(
            (report for report in declared if report not in affected_reports),
            key=lambda item: _REPORTS.index(item),
        )
        if extra:
            raise SourceFactRefusalError(
                "builder输入包含未受影响报告，禁止强制重建：" + "、".join(extra)
            )
        pins: dict[ReportCode, tuple[str, str]] = {}
        for report in affected_reports:
            item = declared[report]
            source = self.project_root / item.input_relative_path
            try:
                _ordinary(self.project_root, source)
            except ValueError as error:
                raise SourceFactRefusalError(f"{report}类报告builder输入路径越界") from error
            if source.is_symlink() or not source.is_file():
                raise SourceFactRefusalError(f"{report}类报告builder输入不存在或不可读")
            payload = source.read_bytes()
            if _sha256_bytes(payload) != item.input_sha256:
                raise SourceFactRefusalError(f"{report}类报告builder输入哈希不一致")
            pinned = self.project_root / _BUILDER_INPUT_DIR / f"{item.input_sha256}.json"
            pinned.parent.mkdir(parents=True, exist_ok=True)
            if pinned.is_file():
                if _sha256_bytes(pinned.read_bytes()) != item.input_sha256:
                    raise SourceCurrentRefreshConflictError(
                        f"{report}类报告内容寻址builder输入已存在但字节不一致"
                    )
            else:
                descriptor, temporary = tempfile.mkstemp(
                    prefix=".source-builder-", dir=pinned.parent
                )
                try:
                    with os.fdopen(descriptor, "wb") as stream:
                        stream.write(payload)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(temporary, pinned)
                finally:
                    Path(temporary).unlink(missing_ok=True)
            pins[report] = (pinned.relative_to(self.project_root).as_posix(), item.input_sha256)
        return pins

    def _new_active_ids(
        self,
        current: CurrentDeliveryBundle,
        resolved: tuple[_ResolvedReplacement, ...],
    ) -> tuple[str, ...]:
        replacements = {
            item.previous_fact_version_id: item.effective_fact_version_id for item in resolved
        }
        return tuple(replacements.get(version_id, version_id)
                     for version_id in current.active_fact_version_ids)

    def _report_fact_ids(
        self,
        affected_reports: tuple[ReportCode, ...],
        new_active_ids: tuple[str, ...],
        public_by_version: dict[str, dict[str, Any]],
    ) -> dict[ReportCode, tuple[str, ...]]:
        by_report: dict[ReportCode, tuple[str, ...]] = {}
        for report in affected_reports:
            selected = tuple(
                version_id
                for version_id in new_active_ids
                if report in self._binding_reports_of(public_by_version[version_id])
            )
            if not selected:
                raise SourceFactRefusalError(f"{report}类报告没有合法活动事实消费者")
            by_report[report] = selected
        return by_report

    def _verify_source_builder_values(
        self, resolved: tuple[_ResolvedReplacement, ...],
        pins: dict[ReportCode, tuple[str, str]],
    ) -> None:
        """Identity-correct input must also preserve the new source value/context.

        Validate source rows before staging user rebases; never substitute the
        user's edited/cleared value into a new original-source builder payload.
        Estimated values are not recomputed from n/N. Direct atoms without a
        declared numeric value or exact text fail closed, not guessed derivations.
        """
        models: dict[ReportCode, ReportAPortalData | ReportBPortalData | ReportCPortalData] = {}
        for report, (relative, _) in pins.items():
            raw = (self.project_root / relative).read_bytes()
            if report == "A":
                models[report] = ReportAPortalData.model_validate_json(raw)
            elif report == "B":
                models[report] = ReportBPortalData.model_validate_json(raw)
            else:
                models[report] = ReportCPortalData.model_validate_json(raw)
        for item in resolved:
            source = self._public_fact(item.replacement_fact_version_id)
            for binding in item.bindings:
                report = binding["report"]
                data = models[report]
                rows = getattr(data, binding["collection"])
                matches = [row for row in rows if row.row_id == binding["row_id"]]
                if len(matches) != 1:
                    raise SourceFactRefusalError(f"{report}来源builder没有唯一事实行")
                row = matches[0]
                if report == "C":
                    expected = source.get("threshold_value", source.get("normalized_value"))
                    if expected is not None:
                        if str(row.threshold_value) != str(expected):
                            raise SourceFactRefusalError("C来源数值与builder不一致")
                    elif row.source_text != source["source_quote"]:
                        raise SourceFactRefusalError("C来源原文与builder不一致")
                    continue
                quote = getattr(row, "source_text", None)
                if quote is not None and quote != source["source_quote"]:
                    raise SourceFactRefusalError(f"{report}来源原文与builder不一致")
                value = source.get("normalized_value")
                if value is None:
                    value = source.get("raw_value")
                if value is None:
                    raise SourceFactRefusalError("来源数值缺失，不以零代替")
                try:
                    numeric = float(value)
                except (TypeError, ValueError) as error:
                    raise SourceFactRefusalError("来源数值缺少可核验直接值，不猜测派生") from error
                if (isinstance(value, bool) or not math.isfinite(numeric)
                        or row.value is None or row.value != numeric):
                    raise SourceFactRefusalError(f"{report}来源数值与builder不一致")
                for field in ("numerator", "denominator", "population", "timepoint", "time_window"):
                    if (field in source and hasattr(row, field)
                            and getattr(row, field) != source[field]):
                        raise SourceFactRefusalError(f"{report}来源{field}与builder不一致")
                if isinstance(data, ReportBPortalData):
                    view = _b_source_view_row(data, binding["collection"], binding["row_id"])
                    quote = view.get("source_text")
                    if quote is not None and quote != source["source_quote"]:
                        raise SourceFactRefusalError("B来源原文与明细view不一致")
                    for field in ("value", "numerator", "denominator"):
                        expected = numeric if field == "value" else source.get(field)
                        if (field == "value" or field in source) and view.get(field) != expected:
                            raise SourceFactRefusalError(f"B来源{field}与明细view不一致")

    def _previous_report(
        self, current: CurrentDeliveryBundle, report: ReportCode
    ) -> CurrentReportDelivery:
        for delivery in current.reports:
            if delivery.report == report:
                return delivery
        raise SourceCurrentRefreshConflictError(f"当前交付缺少{report}类报告，不能重建")

    # ── 事实读取（复用既有 W04 读取语义） ───────────────────────────────────

    def _fact_row(self, fact_version_id: str) -> dict[str, Any]:
        try:
            return self._facts._fact_row(fact_version_id)
        except UserFactSaveError as error:
            raise SourceFactRefusalError(str(error)) from error

    def _public_fact(self, fact_version_id: str) -> dict[str, Any]:
        return self._public_fact_for_row(self._fact_row(fact_version_id))

    def _public_fact_for_row(self, row: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._facts._public_fact(dict(row))
        except UserFactSaveError as error:
            raise SourceFactRefusalError(f"来源事实消费者绑定无法验证：{error}") from error

    def _fragment_row(self, fragment_id: str) -> dict[str, Any]:
        with open_database(self.database_path) as database:
            row = database.execute(
                "SELECT source_version_id,locator,content_text FROM evidence_fragments "
                "WHERE fragment_id=?",
                (fragment_id,),
            ).fetchone()
        if row is None:
            raise SourceFactRefusalError("来源事实主片段不存在")
        return {
            "source_version_id": str(row[0]),
            "locator": str(row[1]),
            "content_text": str(row[2]),
        }

    def _compare_service(self) -> RefreshService:
        if self._refresh is None:
            self._refresh = RefreshService(self.project_root)
        return self._refresh

    @staticmethod
    def _fact_id_of(public: dict[str, Any]) -> str:
        return str(public["fact_id"])

    @classmethod
    def _binding_reports_of(cls, public: dict[str, Any]) -> tuple[ReportCode, ...]:
        bindings = public.get("consumer_bindings")
        if not isinstance(bindings, (list, tuple)):
            return ()
        reports: list[ReportCode] = []
        for binding in bindings:
            if not isinstance(binding, dict):
                continue
            report = str(binding.get("report") or "")
            if report in _REPORTS and report not in reports:
                reports.append(report)
        return tuple(reports)

    def _legal_bindings(
        self, public: dict[str, Any]
    ) -> tuple[tuple[dict[str, Any], ...], tuple[ReportCode, ...]]:
        bindings = public.get("consumer_bindings")
        if not isinstance(bindings, (list, tuple)) or not bindings:
            raise SourceFactRefusalError("来源替换缺少已登记portal消费者绑定，无法确定合法消费者")
        declared: list[dict[str, Any]] = []
        for binding in bindings:
            if not isinstance(binding, dict):
                raise SourceFactRefusalError("来源替换的portal消费者绑定不是对象")
            report = str(binding.get("report") or "")
            if report not in _REPORTS:
                raise SourceFactRefusalError("来源替换的portal消费者绑定报告类型不合法")
            declared.append(dict(binding))
        reports = self._binding_reports_of(public)
        if not reports:
            raise SourceFactRefusalError("来源替换没有可重建的合法消费者报告")
        return tuple(declared), reports


def _comparison_fields(row: dict[str, Any]) -> dict[str, Any]:
    """既有三方比较的事实字段视图：完整科学上下文 + 原值/实体/字段/主片段。"""
    context = dict(row.get("context_payload") or {})
    context.pop("user_edit", None)
    for key in ("raw_value", "normalized_value", "entity_id", "field_id", "primary_fragment_id"):
        context[key] = row.get(key)
    return context


__all__ = [
    "SourceCurrentRefreshCommand",
    "SourceCurrentRefreshConflictError",
    "SourceCurrentRefreshError",
    "SourceCurrentRefreshResult",
    "SourceCurrentRefreshService",
    "SourceFactRefusalError",
    "SourceFactReplacement",
    "SourceReportBuilderInput",
]
