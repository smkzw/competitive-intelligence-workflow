"""Task 3.2 用户可读证据不足说明与阻断包。

阻断时唯一用户产物是 blockers/<A|B|C>/<version>/{audit.json,audit.md}；
不得创建锁定快照、覆盖投影、格式任务、渲染队列、产物记录或报告目录。
发布入口是唯一公共原子 build_and_write_blocker_package；原始构造/写入保持私有。
用户说明使用中文临床试验语境，不显示内部枚举、状态词、路线标识、节点名、日志
或提示词；机器字段只进入 audit.json，不进 audit.md。
"""

from __future__ import annotations

import json
import os
import re
import shutil
from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from ci_workflow.domain.enums import ReportKind
from ci_workflow.domain.evidence import InformationGainDiff
from ci_workflow.domain.ids import stable_id
from ci_workflow.gates.exhaustion import (
    SCIENCE_ABSENT_STATES,
    DoubleExhaustionRecord,
    OmissionReviewConclusion,
)
from ci_workflow.gates.models import (
    ApplicableUniverseSnapshot,
    GateSpec,
    GateUnitOutcome,
    ReportDecision,
    ReportGateResult,
)
from ci_workflow.storage.sqlite import open_database

_VERSION_PATTERN = re.compile(r"^v[0-9]+(?:\.[0-9]+){0,2}(?:-[a-z0-9][a-z0-9.-]*)?$")
_GAP_STATES = frozenset(
    {"not_reported", "not_publicly_disclosed", "conflicting", "unresolved_due_to_route"}
)
_URL_PATTERN = re.compile(r"^https?://\S+$")

# 用户可见中文说明不得出现的内部/编程表达
_FORBIDDEN_USER_TOKENS = frozenset(
    {
        "reported_value", "reported_zero", "not_reported", "not_publicly_disclosed",
        "below_reporting_threshold", "unresolved_due_to_route", "conflicting",
        "not_applicable", "satisfied", "blocked", "passed", "queued", "generating",
        "quality_check", "delivery_ready", "superseded", "recovering",
        "evidence_blocked", "scientific_qc", "snapshot_locked", "collecting",
        "awaiting_user", "route_completed", "route_not_applicable",
        "route_access_blocked", "content_acquired", "not_found", "network_error",
        "rate_limited", "captcha_required", "permission_denied", "proxy_error",
        "dns_error", "tls_error", "http_error", "parser_error", "tool_unavailable",
        "content_truncated", "audit_digest", "gap_digest", "record_digest",
        "executor_role_id", "reviewer_role_id", "route_id", "gap_id", "receipt_id",
        "resume_node", "candidate_snapshot_id", "result_key", "universe_summary",
        "evidence_snapshot_id", "spec_fingerprint", "gate_result_key",
        "日志", "提示词", "DEBUG", "TODO", "print(", "traceback", "assert",
        "evidence_gap", "source_receipt", "gate_unit_id", "model_copy",
        "pydantic", "json", "schema", "recovery:",
    }
)


def _not_blank(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("文本不能为空")
    return normalized


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("日期时间必须包含明确时区偏移")
    return value


def assert_user_facing_zh_clean(text: str) -> None:
    """用户说明不得包含内部枚举、状态词、路线标识、节点名、日志或提示词。"""
    lowered = text.casefold()
    for token in _FORBIDDEN_USER_TOKENS:
        if token.casefold() in lowered:
            raise ValueError(f"用户说明包含内部表达：{token}")


class EmptyUniverseKind(StrEnum):
    """空/无适格对象场景的类型化判定，三种报告互不相同。"""

    A_NO_ELIGIBLE_INNOVATIVE_PRODUCT = "a_no_eligible_innovative_product"
    B_NO_ELIGIBLE_RESULT_TRIAL = "b_no_eligible_result_trial"
    C_NO_ELIGIBLE_CORE_DESIGN_TRIAL = "c_no_eligible_core_design_trial"

    def matches(self, report_kind: ReportKind) -> bool:
        return {
            EmptyUniverseKind.A_NO_ELIGIBLE_INNOVATIVE_PRODUCT: ReportKind.A,
            EmptyUniverseKind.B_NO_ELIGIBLE_RESULT_TRIAL: ReportKind.B,
            EmptyUniverseKind.C_NO_ELIGIBLE_CORE_DESIGN_TRIAL: ReportKind.C,
        }[self] is report_kind

    def eligibility_gate_unit_id(self) -> str:
        """空宇宙专用穷尽缺口的封闭单元标识，对应真实 GateSpec 单元。"""
        return {
            EmptyUniverseKind.A_NO_ELIGIBLE_INNOVATIVE_PRODUCT: "a_innovation_eligibility",
            EmptyUniverseKind.B_NO_ELIGIBLE_RESULT_TRIAL: "b_core_efficacy_endpoint",
            EmptyUniverseKind.C_NO_ELIGIBLE_CORE_DESIGN_TRIAL: "c_trial_identity_stage_role",
        }[self]


class EmptyUniverseEvidence(BaseModel):
    """空/无适格对象场景的不可变、类型化、可摘要证据。

    发生在报告 GateSpec 评估之前：
    - A：适格创新药产品 ID 为空（可真正为 0 个产品）；
    - B：达到最低结果门槛的适格试验 ID 为空；
    - C：达到设计核心门槛的适格核心试验 ID 为空。
    绑定资格规则/策略版本、发现/宇宙闭合摘要、候选/适格/排除对象与排除/检索回执，
    并绑定同报告的双重穷尽记录。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"
    evidence_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    report_kind: ReportKind
    contract_version: str = Field(min_length=1)
    report_version: str
    evidence_snapshot_id: str = Field(min_length=1)
    eligibility_rule_spec_id: str = Field(min_length=1)
    eligibility_rule_version: str = Field(min_length=1)
    eligibility_policy_id: str = Field(min_length=1)
    discovery_summary: str = Field(min_length=1)
    candidate_ids: tuple[str, ...] = ()
    eligible_ids: tuple[str, ...] = ()
    excluded_ids: tuple[str, ...] = ()
    exclusion_receipt_summary: tuple[str, ...] = Field(min_length=1)
    exhaustion: DoubleExhaustionRecord
    created_at: datetime

    @field_validator("evidence_id", "project_id", "eligibility_rule_spec_id")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("eligibility_rule_version", "eligibility_policy_id", "discovery_summary")
    @classmethod
    def _policy_text_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("report_version")
    @classmethod
    def _version_segment_is_safe(cls, value: str) -> str:
        if _VERSION_PATTERN.fullmatch(value) is None:
            raise ValueError("报告版本必须是单个小写 v 开头的安全路径段")
        return value

    @field_validator("candidate_ids", "eligible_ids", "excluded_ids", "exclusion_receipt_summary")
    @classmethod
    def _items_not_blank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_not_blank(value) for value in values)

    @field_validator("created_at")
    @classmethod
    def _created_at_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @model_validator(mode="after")
    def _eligible_is_empty_and_bound_to_report(self) -> EmptyUniverseEvidence:
        if self.eligible_ids:
            raise ValueError("空场景证据的适格对象集合必须为空")
        if self.exhaustion.project_id != self.project_id:
            raise ValueError("空场景双重穷尽记录必须绑定同一项目")
        if self.exhaustion.report_kind is not self.report_kind:
            raise ValueError("空场景双重穷尽记录必须绑定同一报告类型")
        expected_unit = self.kind().eligibility_gate_unit_id()
        for gap in self.exhaustion.gaps:
            if gap.gate_unit_id != expected_unit:
                raise ValueError(
                    "空场景穷尽缺口必须使用对应报告类型的封闭资格单元标识"
                )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def evidence_digest(self) -> str:
        content = json.dumps(
            self.model_dump(mode="json", exclude={"evidence_digest"}),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return stable_id("empty-universe-evidence", content)

    def kind(self) -> EmptyUniverseKind:
        return {
            ReportKind.A: EmptyUniverseKind.A_NO_ELIGIBLE_INNOVATIVE_PRODUCT,
            ReportKind.B: EmptyUniverseKind.B_NO_ELIGIBLE_RESULT_TRIAL,
            ReportKind.C: EmptyUniverseKind.C_NO_ELIGIBLE_CORE_DESIGN_TRIAL,
        }[self.report_kind]


def classify_empty_universe(
    report_kind: ReportKind,
    *,
    eligible_product_ids: Sequence[str] = (),
    eligible_result_trial_ids: Sequence[str] = (),
    eligible_core_design_trial_ids: Sequence[str] = (),
) -> EmptyUniverseKind | None:
    """按报告类型判定空/无适格对象类别；仅临床前项目不得自动视为空失败。"""
    if report_kind is ReportKind.A:
        return (
            EmptyUniverseKind.A_NO_ELIGIBLE_INNOVATIVE_PRODUCT
            if not eligible_product_ids
            else None
        )
    if report_kind is ReportKind.B:
        return (
            EmptyUniverseKind.B_NO_ELIGIBLE_RESULT_TRIAL
            if not eligible_result_trial_ids
            else None
        )
    if report_kind is ReportKind.C:
        return (
            EmptyUniverseKind.C_NO_ELIGIBLE_CORE_DESIGN_TRIAL
            if not eligible_core_design_trial_ids
            else None
        )
    raise ValueError("未知报告类型")


class FailedGateUnit(BaseModel):
    """一个被阻断的规则单元及其对象与字段。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    unit_id: str = Field(min_length=1)
    object_type: str = Field(min_length=1)
    object_id: str = Field(min_length=1)
    object_name_zh: str = Field(min_length=1)
    field_ids: tuple[str, ...] = Field(min_length=1)
    current_state: str
    user_label_zh: str = Field(min_length=1)
    missing_or_conflict_summary_zh: str = Field(min_length=1)
    impacted_product_ids: tuple[str, ...] = ()
    impacted_trial_ids: tuple[str, ...] = ()

    @field_validator("unit_id", "object_type", "object_id", "object_name_zh", "user_label_zh")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("current_state")
    @classmethod
    def _state_is_closed(cls, value: str) -> str:
        if value not in _GAP_STATES:
            raise ValueError("缺口状态必须是封闭集合成员")
        return value

    @field_validator("field_ids", "impacted_product_ids", "impacted_trial_ids")
    @classmethod
    def _items_not_blank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_not_blank(value) for value in values)

    @model_validator(mode="after")
    def _conflict_is_not_absence(self) -> FailedGateUnit:
        if self.current_state == "conflicting":
            assert_user_facing_zh_clean(self.missing_or_conflict_summary_zh)
            if "未公开" in self.missing_or_conflict_summary_zh:
                raise ValueError("冲突不得写成未公开")
            if "数值零" in self.missing_or_conflict_summary_zh or (
                "为 0" in self.missing_or_conflict_summary_zh
            ):
                raise ValueError("冲突不得写成数值零")
        return self


class RouteAuditSummary(BaseModel):
    """路线审计摘要：必须与双重穷尽记录中的路线证据逐项一致。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    gap_id: str = Field(min_length=1)
    route_id: str = Field(min_length=1)
    route_name_zh: str = Field(min_length=1)
    completion: str = Field(min_length=1)
    final_result_class: str = Field(min_length=1)
    attempt_count: int = Field(ge=1)
    receipt_ids: tuple[str, ...] = Field(min_length=1)
    access_methods: tuple[str, ...] = Field(min_length=1)

    @field_validator("gap_id", "route_id", "route_name_zh", "completion", "final_result_class")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("receipt_ids", "access_methods")
    @classmethod
    def _items_not_blank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_not_blank(value) for value in values)


class GapAuditSummary(BaseModel):
    """逐缺口机器审计摘要：缺口状态、对应失败单元、路线/回执、各自两轮信息增益、
    遗漏结论与可选技术诊断。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    gap_id: str = Field(min_length=1)
    gate_unit_id: str = Field(min_length=1)
    object_type: str = Field(min_length=1)
    object_id: str = Field(min_length=1)
    object_name_zh: str = Field(min_length=1)
    current_state: str
    field_ids: tuple[str, ...] = Field(min_length=1)
    user_label_zh: str = Field(min_length=1)
    missing_or_conflict_summary_zh: str = Field(min_length=1)
    route_summaries: tuple[RouteAuditSummary, ...] = Field(min_length=1)
    information_gain_rounds: tuple[InformationGainDiff, ...] = Field(min_length=2)
    omission_conclusion: OmissionReviewConclusion
    omission_notes_zh: str = Field(min_length=1)
    technical_diagnosis_zh: str | None = None
    gap_digest: str = Field(min_length=1)


def compute_audit_digest(
    audit_fields: dict[str, object],
) -> str:
    """由阻断说明内容确定性生成摘要；audit_digest 本身不参与。"""
    canonical = json.dumps(
        {key: value for key, value in audit_fields.items() if key != "audit_digest"},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return stable_id("blocker-audit", canonical)


def _audit_content_dump(audit: BlockerAudit) -> dict[str, object]:
    return audit.model_dump(mode="json", exclude={"audit_digest"})


class BlockerAudit(BaseModel):
    """证据不足阻断说明：唯一合法阻断产物（audit.json 与 audit.md 的内容源）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"
    audit_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    report_kind: ReportKind
    contract_version: str = Field(min_length=1)
    report_version: str
    rule_spec_id: str = Field(min_length=1)
    rule_version: str = Field(min_length=1)
    spec_fingerprint: str = Field(min_length=1)
    evidence_snapshot_id: str = Field(min_length=1)
    universe_summary: str = Field(min_length=1)
    gate_result_key: str = ""
    empty_universe: EmptyUniverseKind | None = None
    empty_evidence: EmptyUniverseEvidence | None = None
    empty_justification_zh: str | None = None
    failed_units: tuple[FailedGateUnit, ...] = ()
    impacted_products: tuple[str, ...] = ()
    impacted_trials: tuple[str, ...] = ()
    per_gap_audits: tuple[GapAuditSummary, ...] = Field(min_length=1)
    route_summaries: tuple[RouteAuditSummary, ...] = Field(min_length=1)
    omission_review_result_zh: str = Field(min_length=1)
    has_technical_access_issue: bool
    residual_uncertainty_zh: str = Field(min_length=1)
    user_help_needed: bool
    user_input_directory: str | None = None
    minimal_user_action_zh: str = Field(min_length=1)
    source_links: tuple[str, ...] = ()
    audit_directory: str = Field(min_length=1)
    resume_instruction_zh: str = Field(min_length=1)
    record_digest: str = Field(min_length=1)
    gap_digests: tuple[str, ...] = Field(min_length=1)
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def audit_digest(self) -> str:
        return compute_audit_digest(_audit_content_dump(self))

    @field_validator("project_id", "contract_version", "rule_spec_id", "rule_version")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("report_version")
    @classmethod
    def _version_segment_is_safe(cls, value: str) -> str:
        if _VERSION_PATTERN.fullmatch(value) is None:
            raise ValueError("报告版本必须是单个小写 v 开头的安全路径段")
        return value

    @field_validator(
        "spec_fingerprint",
        "evidence_snapshot_id",
        "universe_summary",
        "omission_review_result_zh",
        "residual_uncertainty_zh",
        "minimal_user_action_zh",
        "resume_instruction_zh",
    )
    @classmethod
    def _user_text_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("empty_justification_zh", "user_input_directory")
    @classmethod
    def _optional_text_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _not_blank(value)

    @field_validator("audit_directory", "source_links", "gap_digests")
    @classmethod
    def _path_and_link_items_not_blank(
        cls, value: str | tuple[str, ...]
    ) -> str | tuple[str, ...]:
        if isinstance(value, str):
            return _not_blank(value)
        return tuple(_not_blank(item) for item in value)

    @field_validator("created_at")
    @classmethod
    def _created_at_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @model_validator(mode="after")
    def _source_links_are_urls_or_relative_paths(self) -> BlockerAudit:
        for link in self.source_links:
            if _URL_PATTERN.fullmatch(link) is not None:
                continue
            # 非 http(s) 的带协议串（如 ftp://）不是工作区相对路径
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", link) is not None:
                raise ValueError("来源链接必须是 http/https 原文或工作区相对附件路径")
            path = PurePosixPath(link)
            if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
                raise ValueError("来源链接必须是 http/https 原文或工作区相对附件路径")
        return self

    @model_validator(mode="after")
    def _audit_directory_is_blocker_dir(self) -> BlockerAudit:
        if self.audit_directory != blocker_directory(
            self.report_kind, self.report_version
        ).as_posix():
            raise ValueError("审计说明目录必须与阻断包目录一致")
        return self

    @model_validator(mode="after")
    def _empty_and_failed_units_are_exclusive(self) -> BlockerAudit:
        if self.empty_universe is None and not self.failed_units:
            raise ValueError("阻断说明必须给出类型化空场景或至少一个失败单元")
        if self.empty_universe is not None:
            if self.failed_units:
                raise ValueError("类型化空场景不得同时携带失败单元")
            if not self.empty_universe.matches(self.report_kind):
                raise ValueError("类型化空场景与报告类型不一致")
            if self.empty_justification_zh is None:
                raise ValueError("类型化空场景必须给出中文依据")
            if self.empty_evidence is None:
                raise ValueError("类型化空场景必须绑定空场景证据")
        return self

    @model_validator(mode="after")
    def _user_input_directory_follows_help_flag(self) -> BlockerAudit:
        if self.user_help_needed and self.user_input_directory is None:
            raise ValueError("需要用户协助时必须指定唯一 manual-inbox 用户输入目录")
        if not self.user_help_needed and self.user_input_directory is not None:
            raise ValueError("不需要用户协助时不得指定用户输入目录")
        return self

    @model_validator(mode="after")
    def _per_gap_audits_bind_failed_units(self) -> BlockerAudit:
        if self.failed_units:
            failed_pairs = {(u.unit_id, u.object_id) for u in self.failed_units}
            gap_pairs = {(g.gate_unit_id, g.object_id) for g in self.per_gap_audits}
            if failed_pairs != gap_pairs:
                raise ValueError("逐缺口审计必须与失败单元完全一致")
            for gap in self.per_gap_audits:
                if gap.current_state in SCIENCE_ABSENT_STATES and (
                    gap.technical_diagnosis_zh is not None
                ):
                    raise ValueError("科学缺失缺口不得携带技术诊断")
                if gap.current_state == "unresolved_due_to_route" and (
                    gap.technical_diagnosis_zh is None
                ):
                    raise ValueError("技术访问未解决缺口必须绑定独立技术诊断")
                if gap.current_state == "conflicting" and (
                    gap.technical_diagnosis_zh is not None
                ):
                    raise ValueError("冲突缺口不得携带技术诊断")
        return self

    @model_validator(mode="after")
    def _user_facing_zh_is_clean(self) -> BlockerAudit:
        for field in (
            "omission_review_result_zh",
            "residual_uncertainty_zh",
            "minimal_user_action_zh",
            "resume_instruction_zh",
        ):
            assert_user_facing_zh_clean(getattr(self, field))
        if self.empty_justification_zh is not None:
            assert_user_facing_zh_clean(self.empty_justification_zh)
        for gap in self.per_gap_audits:
            assert_user_facing_zh_clean(gap.object_name_zh)
            assert_user_facing_zh_clean(gap.missing_or_conflict_summary_zh)
            for route in gap.route_summaries:
                assert_user_facing_zh_clean(route.route_name_zh)
            if gap.technical_diagnosis_zh is not None:
                assert_user_facing_zh_clean(gap.technical_diagnosis_zh)
        return self


class BlockerAuditDriftError(RuntimeError):
    """同一审计身份下的内容漂移：拒绝覆盖已接受审计历史。"""


class BlockerPackageIntegrityError(RuntimeError):
    """阻断目录内容不满足恰好两个文件、内容一致的合同。"""


def blocker_directory(report_kind: ReportKind, report_version: str) -> PurePosixPath:
    """阻断包唯一目录：blockers/<A|B|C>/<version>；不是报告目录。"""
    if _VERSION_PATTERN.fullmatch(report_version) is None:
        raise ValueError("报告版本必须是单个小写 v 开头的安全路径段")
    return PurePosixPath("blockers", report_kind.value, report_version)


def assert_no_report_downstream_artifacts(
    database_path: Path,
    *,
    project_id: str,
    report_kind: ReportKind,
    report_version: str,
    workspace_root: Path,
) -> None:
    """阻断前/后机械断言：无锁定快照、覆盖集/投影、格式任务、渲染队列、
    产物记录或 reports/<A|B|C|>/<version> 目录。阻断目录不是报告目录。"""
    report_dir = workspace_root / "reports" / report_kind.value / report_version
    if report_dir.exists():
        raise ValueError("阻断报告不得存在报告版本目录或占位门户")

    with open_database(database_path) as database:
        counts: dict[str, int] = {
            "report_snapshots": database.execute(
                "SELECT COUNT(*) FROM report_snapshots"
                " WHERE project_id=? AND report_kind=? AND report_version=?",
                (project_id, report_kind.value, report_version),
            ).fetchone()[0],
            "coverage_sets": database.execute(
                "SELECT COUNT(*) FROM coverage_sets cs"
                " JOIN report_snapshots rs ON cs.snapshot_id=rs.snapshot_id"
                " WHERE rs.project_id=? AND rs.report_kind=? AND rs.report_version=?",
                (project_id, report_kind.value, report_version),
            ).fetchone()[0],
            "coverage_projections": database.execute(
                "SELECT COUNT(*) FROM coverage_projections cp"
                " JOIN coverage_sets cs ON cp.coverage_set_id=cs.coverage_set_id"
                " JOIN report_snapshots rs ON cs.snapshot_id=rs.snapshot_id"
                " WHERE rs.project_id=? AND rs.report_kind=? AND rs.report_version=?",
                (project_id, report_kind.value, report_version),
            ).fetchone()[0],
            "format_jobs": database.execute(
                "SELECT COUNT(*) FROM format_jobs fj"
                " JOIN report_snapshots rs ON fj.snapshot_id=rs.snapshot_id"
                " WHERE rs.project_id=? AND rs.report_kind=? AND rs.report_version=?",
                (project_id, report_kind.value, report_version),
            ).fetchone()[0],
            "render_queue": database.execute(
                "SELECT COUNT(*) FROM render_queue rq"
                " JOIN format_jobs fj ON rq.format_job_id=fj.format_job_id"
                " JOIN report_snapshots rs ON fj.snapshot_id=rs.snapshot_id"
                " WHERE rs.project_id=? AND rs.report_kind=? AND rs.report_version=?",
                (project_id, report_kind.value, report_version),
            ).fetchone()[0],
            "artifact_records": database.execute(
                "SELECT COUNT(*) FROM artifact_records ar"
                " JOIN format_jobs fj ON ar.format_job_id=fj.format_job_id"
                " JOIN report_snapshots rs ON fj.snapshot_id=rs.snapshot_id"
                " WHERE rs.project_id=? AND rs.report_kind=? AND rs.report_version=?",
                (project_id, report_kind.value, report_version),
            ).fetchone()[0],
        }
    violated = [name for name, count in counts.items() if count > 0]
    if violated:
        raise ValueError(
            "阻断报告不得存在下游产物：" + "、".join(sorted(violated))
        )


_STATE_USER_TEXT = {
    "not_reported": "已核查的公开材料未列示该字段",
    "not_publicly_disclosed": "来源明确未披露或尚未公开",
    "conflicting": "不同来源信息不一致",
    "unresolved_due_to_route": "访问问题尚未解决，不能判断是否公开",
}


def _render_audit_markdown_zh(audit: BlockerAudit) -> str:
    """原生中文用户说明：逐缺口解释、真实医学对象语境、已尝试范围、原因、下一步。"""
    lines: list[str] = []
    lines.append("# 证据不足说明")
    lines.append("")
    lines.append(
        f"本说明针对「{_report_name_zh(audit.report_kind)}」版本 {audit.report_version}。"
        "该报告因下列关键医学内容证据不足，暂时无法完成，也不会生成任何报告文件。"
    )
    lines.append("")
    if audit.empty_universe is not None:
        lines.append("## 一、本次报告被阻断的内容")
        lines.append("")
        lines.append(f"- 结论：{audit.empty_justification_zh}")
        lines.append("")
    else:
        lines.append("## 一、本次报告被阻断的产品与内容")
        lines.append("")
        for gap in audit.per_gap_audits:
            lines.append(f"- 对象：{gap.object_name_zh}")
            lines.append(f"- 缺失或矛盾的内容：{gap.user_label_zh}")
            lines.append(
                f"- 现状说明：{gap.missing_or_conflict_summary_zh}"
                f"（{_STATE_USER_TEXT[gap.current_state]}）"
            )
            lines.append("")
    lines.append("## 二、已经尝试过的检索范围")
    lines.append("")
    seen_routes: set[tuple[str, int]] = set()
    for gap in audit.per_gap_audits:
        for route in gap.route_summaries:
            key = (route.route_name_zh, route.attempt_count)
            if key in seen_routes:
                continue
            seen_routes.add(key)
            lines.append(
                f"- {route.route_name_zh}：已完成 {route.attempt_count} 次尝试；"
                f"访问方式：{'、'.join(route.access_methods)}"
            )
    lines.append("- 已连续完成两轮穷尽核对，两轮之间没有取得新的关键信息。")
    lines.append("")
    lines.append("## 三、判断")
    lines.append("")
    if audit.empty_universe is not None:
        lines.append("- 经双重穷尽核对，本轮不存在符合条件的对象，未发现可归因遗漏。")
    elif audit.has_technical_access_issue:
        lines.append("- 部分内容属于访问问题尚未解决，不能判断是否公开。")
        for gap in audit.per_gap_audits:
            if gap.technical_diagnosis_zh is not None:
                lines.append(f"- 技术诊断（{gap.object_name_zh}）：{gap.technical_diagnosis_zh}")
    else:
        lines.append("- 本次缺失属于来源未披露或尚未公开；独立遗漏复核未发现可归因遗漏。")
    lines.append("")
    lines.append("## 四、您只需要做什么")
    lines.append("")
    if audit.user_help_needed:
        lines.append(f"- 您只需要：{audit.minimal_user_action_zh}")
        lines.append(f"- 请将相关材料放入：{audit.user_input_directory}")
    else:
        lines.append(f"- 您只需要：{audit.minimal_user_action_zh}")
    lines.append("")
    if audit.source_links:
        lines.append("## 五、原文链接")
        lines.append("")
        for link in audit.source_links:
            lines.append(f"- {link}")
        lines.append("")
    lines.append("## 六、本说明存放位置")
    lines.append("")
    lines.append(f"- {audit.audit_directory}")
    lines.append("")
    lines.append("## 七、补充材料后如何继续")
    lines.append("")
    lines.append(f"- {audit.resume_instruction_zh}")
    lines.append("")
    return "\n".join(lines)


def render_audit_markdown_zh(audit: BlockerAudit) -> str:
    """渲染后整体执行清洁检查：内部标识/状态词/日志不得进入用户全文。"""
    markdown = _render_audit_markdown_zh(audit)
    assert_user_facing_zh_clean(markdown)
    return markdown


def _report_name_zh(report_kind: ReportKind) -> str:
    return {
        ReportKind.A: "产品格局报告",
        ReportKind.B: "临床证据报告",
        ReportKind.C: "试验设计报告",
    }[report_kind]


def _empty_object_name_zh(object_id: str) -> str:
    return {
        "candidate-1": "候选创新产品 · 编号一",
        "trial-1": "候选临床研究 · 编号一",
    }.get(object_id, "候选研究对象")


def _empty_unit_label_zh(gate_unit_id: str) -> str:
    return {
        "a_innovation_eligibility": "创新本体纳排结论",
        "b_core_efficacy_endpoint": "核心疗效终点记录",
        "c_trial_identity_stage_role": "试验身份、阶段与开发角色",
    }.get(gate_unit_id, "关键证据单元")


def _derive_per_gap_audits(
    exhaustion: DoubleExhaustionRecord,
    failed_units: Sequence[FailedGateUnit],
) -> tuple[GapAuditSummary, ...]:
    """逐缺口审计由双重穷尽记录派生；失败单元状态必须与缺口一致。

    空/无适格路径没有失败单元：缺口对象名取自其 object_id 的医学语境映射。
    """
    failed_by_pair = {(u.unit_id, u.object_id): u for u in failed_units}
    audits: list[GapAuditSummary] = []
    for gap in exhaustion.gaps:
        unit = failed_by_pair.get((gap.gate_unit_id, gap.object_id))
        if unit is None:
            if failed_units:
                raise ValueError(
                    f"双重穷尽缺口未对应失败单元：{gap.gate_unit_id}/{gap.object_id}"
                )
            unit = FailedGateUnit(
                unit_id=gap.gate_unit_id,
                object_type=gap.object_type,
                object_id=gap.object_id,
                object_name_zh=_empty_object_name_zh(gap.object_id),
                field_ids=(gap.gate_unit_id,),
                current_state=gap.current_state,
                user_label_zh=_empty_unit_label_zh(gap.gate_unit_id),
                missing_or_conflict_summary_zh=(
                    "该产品/试验的相应内容经两轮穷尽检索仍未获得"
                    if gap.current_state
                    in ("not_reported", "not_publicly_disclosed")
                    else "该内容存在相互矛盾的来源值且尚未解决"
                ),
            )
        if unit.current_state != gap.current_state:
            raise ValueError(f"失败单元状态与缺口结论不一致：{gap.gate_unit_id}")
        routes = tuple(
            RouteAuditSummary(
                gap_id=gap.gap_id,
                route_id=route.route_id,
                route_name_zh=route.route_name_zh,
                completion=route.completion.value,
                final_result_class=route.final_result_class,
                attempt_count=route.attempt_count,
                receipt_ids=route.receipt_ids,
                access_methods=route.access_methods,
            )
            for route in gap.route_evidence
        )
        audits.append(
            GapAuditSummary(
                gap_id=gap.gap_id,
                gate_unit_id=gap.gate_unit_id,
                object_type=gap.object_type,
                object_id=gap.object_id,
                object_name_zh=unit.object_name_zh,
                current_state=gap.current_state,
                field_ids=unit.field_ids,
                user_label_zh=unit.user_label_zh,
                missing_or_conflict_summary_zh=unit.missing_or_conflict_summary_zh,
                route_summaries=routes,
                information_gain_rounds=gap.information_gain_rounds,
                omission_conclusion=gap.omission_review.conclusion,
                omission_notes_zh=gap.omission_review.review_notes_zh,
                technical_diagnosis_zh=(
                    gap.technical_diagnosis.diagnosis_zh
                    if gap.technical_diagnosis is not None
                    else None
                ),
                gap_digest=gap.gap_digest,
            )
        )
    return tuple(audits)


def _derive_omission_review_zh(exhaustion: DoubleExhaustionRecord) -> str:
    parts = [
        f"缺口 {gap.gap_id}：{gap.omission_review.review_notes_zh}"
        for gap in exhaustion.gaps
    ]
    return "；".join(parts)


def _derive_impacted_scope(
    failed_units: Sequence[FailedGateUnit],
    snapshot: ApplicableUniverseSnapshot | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """影响对象必须从失败单元派生，并与闭合宇宙关系核对。"""
    products = sorted(
        {product_id for unit in failed_units for product_id in unit.impacted_product_ids}
    )
    trials = sorted(
        {trial_id for unit in failed_units for trial_id in unit.impacted_trial_ids}
    )
    if snapshot is not None:
        if not set(products) <= set(snapshot.product_ids):
            raise ValueError("影响产品必须属于已闭合宇宙")
        if not set(trials) <= set(snapshot.trial_ids):
            raise ValueError("影响试验必须属于已闭合宇宙")
    return tuple(products), tuple(trials)


def _build_blocker_audit(
    *,
    project_id: str,
    report_kind: ReportKind,
    contract_version: str,
    report_version: str,
    spec: GateSpec,
    snapshot: ApplicableUniverseSnapshot | None,
    gate_result: ReportGateResult | None,
    failed_units: Sequence[FailedGateUnit],
    empty_universe: EmptyUniverseKind | None,
    empty_evidence: EmptyUniverseEvidence | None,
    empty_justification_zh: str | None,
    residual_uncertainty_zh: str,
    user_help_needed: bool,
    user_input_directory: str | None,
    minimal_user_action_zh: str,
    source_links: Sequence[str],
    resume_instruction_zh: str,
    exhaustion: DoubleExhaustionRecord,
    created_at: datetime | None = None,
) -> BlockerAudit:
    """组装阻断说明（私有）：必须绑定真实 GateSpec、宇宙与门槛评估结果。

    空/无适格路径不进行 GateSpec 评估（gate_result=None），身份取自
    EmptyUniverseEvidence；非空路径必须绑定 BLOCKED 的真实 gate_result。
    """
    _text(project_id)
    _text(residual_uncertainty_zh)
    _text(minimal_user_action_zh)
    _text(resume_instruction_zh)
    if empty_justification_zh is not None:
        _text(empty_justification_zh)

    if exhaustion.project_id != project_id or exhaustion.report_kind is not report_kind:
        raise ValueError("双重穷尽记录必须绑定同一项目与报告类型")
    if spec.report_kind is not report_kind:
        raise ValueError("GateSpec 与阻断说明报告类型不一致")
    if spec.spec_id != _expected_spec_id(report_kind):
        raise ValueError("GateSpec 标识与报告规则不符")

    if empty_universe is not None:
        # 空/无适格路径：不发生 GateSpec 评估，必须 gate_result=None
        if gate_result is not None:
            raise ValueError("类型化空场景不得伪造门槛评估结果")
        if empty_evidence is None:
            raise ValueError("类型化空场景必须绑定空场景证据")
        if failed_units:
            raise ValueError("类型化空场景不得同时携带失败单元")
        if empty_evidence.project_id != project_id:
            raise ValueError("空场景证据必须绑定同一项目")
        if empty_evidence.report_kind is not report_kind:
            raise ValueError("空场景证据必须绑定同一报告类型")
        if empty_evidence.report_version != report_version:
            raise ValueError("空场景证据必须绑定同一报告版本")
        if empty_evidence.contract_version != contract_version:
            raise ValueError("空场景证据必须绑定同一合同版本")
        if snapshot is not None and (
            snapshot.evidence_snapshot_id != empty_evidence.evidence_snapshot_id
        ):
            raise ValueError("空场景证据与宇宙快照证据快照不一致")
        classified = classify_empty_universe(
            report_kind,
            eligible_product_ids=empty_evidence.eligible_ids,
            eligible_result_trial_ids=empty_evidence.eligible_ids,
            eligible_core_design_trial_ids=empty_evidence.eligible_ids,
        )
        if classified != empty_universe:
            raise ValueError("空场景证据与类型化空场景判定不一致")
        resolved_snapshot_id = empty_evidence.evidence_snapshot_id
        resolved_universe_summary = (
            snapshot.universe_summary if snapshot is not None else empty_evidence.discovery_summary
        )
        resolved_gate_result_key = ""
    else:
        # 非空路径：必须绑定真实 BLOCKED 门槛评估结果
        if gate_result is None:
            raise ValueError("非空失败路径必须绑定门槛评估结果")
        if gate_result.report_kind is not report_kind:
            raise ValueError("门槛评估结果与阻断说明报告类型不一致")
        if gate_result.decision is not ReportDecision.BLOCKED:
            raise ValueError("非空失败路径必须绑定阻断的门槛评估结果")
        if gate_result.spec_version != spec.version:
            raise ValueError("门槛评估结果与 GateSpec 版本不一致")
        if gate_result.spec_fingerprint != spec.spec_fingerprint:
            raise ValueError("门槛评估结果与 GateSpec 指纹不一致")
        if gate_result.contract_version != contract_version:
            raise ValueError("门槛评估结果与阻断说明合同版本不一致")
        if snapshot is None:
            raise ValueError("非空路径必须绑定宇宙快照")
        if snapshot.project_id != project_id:
            raise ValueError("宇宙快照必须绑定同一项目")
        if snapshot.evidence_snapshot_id != gate_result.evidence_snapshot_id:
            raise ValueError("宇宙快照与门槛评估结果证据快照不一致")
        if snapshot.universe_summary != gate_result.universe_summary:
            raise ValueError("宇宙快照与门槛评估结果宇宙摘要不一致")
        resolved_snapshot_id = gate_result.evidence_snapshot_id
        resolved_universe_summary = gate_result.universe_summary
        resolved_gate_result_key = gate_result.result_key

        blocked_pairs = frozenset(
            (result.unit_id, result.object_id)
            for result in gate_result.unit_results
            if result.outcome is GateUnitOutcome.BLOCKED
        )
        failed_pairs = frozenset((unit.unit_id, unit.object_id) for unit in failed_units)
        if not failed_units:
            raise ValueError("非空路径必须提供至少一个失败单元")
        if blocked_pairs != failed_pairs:
            missing = sorted(blocked_pairs - failed_pairs)
            extra = sorted(failed_pairs - blocked_pairs)
            raise ValueError(
                "失败单元集合必须与门槛评估阻断集合完全一致："
                f"缺失={missing} 多余={extra}"
            )

    gaps_by_unit_object = {
        (gap.gate_unit_id, gap.object_id): gap for gap in exhaustion.gaps
    }
    for unit in failed_units:
        gap = gaps_by_unit_object.get((unit.unit_id, unit.object_id))
        if gap is None:
            raise ValueError(
                f"失败单元缺少逐缺口双重穷尽证据：{unit.unit_id}/{unit.object_id}"
            )
        if gap.omission_review.conclusion == OmissionReviewConclusion.MATERIAL_OMISSION_FOUND:
            raise ValueError("遗漏复核发现实质遗漏，不得生成证据不足说明")
        if gap.current_state in SCIENCE_ABSENT_STATES or gap.current_state == "conflicting":
            if gap.omission_review.conclusion is not OmissionReviewConclusion.NO_MATERIAL_OMISSION:
                raise ValueError("科学缺失/冲突缺口只接受无实质遗漏复核结论")
        elif gap.current_state == "unresolved_due_to_route":
            if (
                gap.omission_review.conclusion
                is not OmissionReviewConclusion.TECHNICAL_ACCESS_UNRESOLVED
            ):
                raise ValueError("技术未解决缺口必须得到技术访问未解决复核结论")
            if gap.technical_diagnosis is None:
                raise ValueError(
                    f"技术访问未解决的缺口必须绑定独立技术诊断：{unit.unit_id}"
                )

    per_gap_audits = _derive_per_gap_audits(exhaustion, failed_units)
    if empty_universe is not None:
        impacted_products = tuple(sorted(empty_evidence.candidate_ids)) if empty_evidence else ()
        impacted_trials = tuple(sorted(empty_evidence.candidate_ids)) if empty_evidence else ()
    else:
        impacted_products, impacted_trials = _derive_impacted_scope(failed_units, snapshot)
    route_summaries = tuple(
        route for gap in per_gap_audits for route in gap.route_summaries
    )
    omission_review_result_zh = _derive_omission_review_zh(exhaustion)
    has_technical = any(
        gap.technical_diagnosis_zh is not None for gap in per_gap_audits
    )

    audit_id = stable_id(
        "blocker-audit", project_id, report_kind.value, report_version
    )
    resolved_created_at = created_at or datetime.now().astimezone()
    fields: dict[str, object] = {
        "schema_version": "1.0",
        "audit_id": audit_id,
        "project_id": project_id,
        "report_kind": report_kind,
        "contract_version": contract_version,
        "report_version": report_version,
        "rule_spec_id": spec.spec_id,
        "rule_version": spec.version,
        "spec_fingerprint": spec.spec_fingerprint,
        "evidence_snapshot_id": resolved_snapshot_id,
        "universe_summary": resolved_universe_summary,
        "gate_result_key": resolved_gate_result_key,
        "empty_universe": empty_universe,
        "empty_evidence": empty_evidence,
        "empty_justification_zh": empty_justification_zh,
        "failed_units": tuple(failed_units),
        "impacted_products": impacted_products,
        "impacted_trials": impacted_trials,
        "per_gap_audits": per_gap_audits,
        "route_summaries": route_summaries,
        "omission_review_result_zh": omission_review_result_zh,
        "has_technical_access_issue": has_technical,
        "residual_uncertainty_zh": residual_uncertainty_zh,
        "user_help_needed": user_help_needed,
        "user_input_directory": user_input_directory,
        "minimal_user_action_zh": minimal_user_action_zh,
        "source_links": tuple(source_links),
        "audit_directory": blocker_directory(report_kind, report_version).as_posix(),
        "resume_instruction_zh": resume_instruction_zh,
        "record_digest": exhaustion.record_digest,
        "gap_digests": tuple(gap.gap_digest for gap in exhaustion.gaps),
        "created_at": resolved_created_at,
    }
    return BlockerAudit.model_validate(fields)


def _expected_spec_id(report_kind: ReportKind) -> str:
    return f"gate-spec-{report_kind.value.lower()}-v1"


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("文本不能为空")
    return normalized


class ScientificQcRejection(BaseModel):
    """独立科学质控否决的最小只读输入（Task 3.7 的服务另行实现）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"
    rejection_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    report_kind: ReportKind
    report_version: str
    candidate_snapshot_id: str = Field(min_length=1)
    gate_result_key: str = Field(min_length=1)
    verdict: str = "rejected"
    recoverable: bool
    exhausted: bool
    reviewer_id: str = Field(min_length=1)
    reason_zh: str = Field(min_length=1)

    @field_validator(
        "rejection_id", "project_id", "candidate_snapshot_id", "gate_result_key", "reviewer_id"
    )
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("report_version")
    @classmethod
    def _version_segment_is_safe(cls, value: str) -> str:
        if _VERSION_PATTERN.fullmatch(value) is None:
            raise ValueError("报告版本必须是单个小写 v 开头的安全路径段")
        return value

    @model_validator(mode="after")
    def _recoverable_or_exhausted_exactly_one(self) -> ScientificQcRejection:
        if self.recoverable == self.exhausted:
            raise ValueError("质控否决必须且只能声明可修复或已穷尽之一")
        if self.verdict != "rejected":
            raise ValueError("本输入只接受否决结论")
        assert_user_facing_zh_clean(self.reason_zh)
        return self


def apply_scientific_qc_rejection(
    rejection: ScientificQcRejection,
    *,
    gate_result: ReportGateResult,
    snapshot: ApplicableUniverseSnapshot,
    workspace_root: Path,
    database_path: Path,
    exhaustion: DoubleExhaustionRecord | None = None,
) -> str:
    """科学质控必须在 GateSpec 通过之后；可修复回 recovering，已穷尽进
    evidence_blocked。绑定项目/宇宙/快照；两者都不得产生任何下游报告产物。
    """
    if snapshot.project_id != rejection.project_id:
        raise ValueError("宇宙快照必须绑定同一项目")
    if snapshot.evidence_snapshot_id != rejection.candidate_snapshot_id:
        raise ValueError("宇宙快照必须绑定否决声明的候选快照")
    if gate_result.decision is not ReportDecision.PASSED:
        raise ValueError("科学质控否决必须绑定已通过的 GateSpec 结果")
    if gate_result.report_kind is not rejection.report_kind:
        raise ValueError("质控否决与 GateSpec 结果报告类型不一致")
    if gate_result.evidence_snapshot_id != rejection.candidate_snapshot_id:
        raise ValueError("质控否决必须绑定候选快照对应的 GateSpec 结果")
    if gate_result.evidence_snapshot_id != snapshot.evidence_snapshot_id:
        raise ValueError("GateSpec 结果与宇宙快照证据快照不一致")
    if gate_result.universe_summary != snapshot.universe_summary:
        raise ValueError("GateSpec 结果与宇宙快照宇宙摘要不一致")
    if gate_result.result_key != rejection.gate_result_key:
        raise ValueError("质控否决结果键与 GateSpec 结果不一致")

    if rejection.exhausted:
        if exhaustion is None:
            raise ValueError("已穷尽否决必须绑定双重穷尽记录")
        if exhaustion.project_id != rejection.project_id:
            raise ValueError("双重穷尽记录必须绑定同一项目")
        if exhaustion.report_kind is not rejection.report_kind:
            raise ValueError("双重穷尽记录必须绑定同一报告类型")
    assert_no_report_downstream_artifacts(
        database_path,
        project_id=rejection.project_id,
        report_kind=rejection.report_kind,
        report_version=rejection.report_version,
        workspace_root=workspace_root,
    )
    next_state = "recovering" if rejection.recoverable else "evidence_blocked"
    assert_no_report_downstream_artifacts(
        database_path,
        project_id=rejection.project_id,
        report_kind=rejection.report_kind,
        report_version=rejection.report_version,
        workspace_root=workspace_root,
    )
    return next_state


def build_and_write_blocker_package(
    *,
    project_id: str,
    report_kind: ReportKind,
    contract_version: str,
    report_version: str,
    spec: GateSpec,
    snapshot: ApplicableUniverseSnapshot | None,
    gate_result: ReportGateResult | None,
    failed_units: Sequence[FailedGateUnit],
    exhaustion: DoubleExhaustionRecord,
    empty_universe: EmptyUniverseKind | None = None,
    empty_evidence: EmptyUniverseEvidence | None = None,
    empty_justification_zh: str | None = None,
    residual_uncertainty_zh: str,
    user_help_needed: bool,
    user_input_directory: str | None = None,
    minimal_user_action_zh: str,
    source_links: Sequence[str],
    resume_instruction_zh: str,
    workspace_root: Path,
    database_path: Path,
    created_at: datetime | None = None,
) -> tuple[Path, Path]:
    """唯一公共原子发布入口：验证 GateSpec/snapshot/gate result/空证据/双重穷尽，
    生成审计，执行零下游断言并原子发布。原始构造/写入保持私有。"""
    audit = _build_blocker_audit(
        project_id=project_id,
        report_kind=report_kind,
        contract_version=contract_version,
        report_version=report_version,
        spec=spec,
        snapshot=snapshot,
        gate_result=gate_result,
        failed_units=failed_units,
        empty_universe=empty_universe,
        empty_evidence=empty_evidence,
        empty_justification_zh=empty_justification_zh,
        residual_uncertainty_zh=residual_uncertainty_zh,
        user_help_needed=user_help_needed,
        user_input_directory=user_input_directory,
        minimal_user_action_zh=minimal_user_action_zh,
        source_links=source_links,
        resume_instruction_zh=resume_instruction_zh,
        exhaustion=exhaustion,
        created_at=created_at,
    )
    return _write_blocker_package(
        audit,
        workspace_root=workspace_root,
        database_path=database_path,
    )


def _write_blocker_package(
    audit: BlockerAudit,
    *,
    workspace_root: Path,
    database_path: Path,
) -> tuple[Path, Path]:
    """写入唯一阻断产物 audit.json 与 audit.md（私有）；前后均断言无下游产物。"""
    assert_no_report_downstream_artifacts(
        database_path,
        project_id=audit.project_id,
        report_kind=audit.report_kind,
        report_version=audit.report_version,
        workspace_root=workspace_root,
    )
    final_dir = workspace_root / blocker_directory(
        audit.report_kind, audit.report_version
    )
    if final_dir.exists() and not final_dir.is_dir():
        raise BlockerPackageIntegrityError(
            "阻断包路径必须是目录，现有路径为文件"
        )
    audit_json_content = audit.model_dump_json(indent=2) + "\n"
    audit_md_content = render_audit_markdown_zh(audit)

    if final_dir.exists():
        _verify_existing_package(
            final_dir, audit_json_content, audit_md_content
        )
        return final_dir / "audit.json", final_dir / "audit.md"

    temp_dir = final_dir.with_name(
        f".{final_dir.name}.tmp-{os.getpid()}"
    )
    try:
        temp_dir.mkdir(parents=True)
        (temp_dir / "audit.json").write_text(audit_json_content, encoding="utf-8")
        (temp_dir / "audit.md").write_text(audit_md_content, encoding="utf-8")
        os.replace(temp_dir, final_dir)
    except BaseException:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    assert_no_report_downstream_artifacts(
        database_path,
        project_id=audit.project_id,
        report_kind=audit.report_kind,
        report_version=audit.report_version,
        workspace_root=workspace_root,
    )
    return final_dir / "audit.json", final_dir / "audit.md"


def _verify_existing_package(
    directory: Path,
    audit_json_content: str,
    audit_md_content: str,
) -> None:
    """既有阻断目录必须恰好包含 audit.json 与 audit.md 且内容一致。"""
    names = sorted(path.name for path in directory.iterdir())
    if names != ["audit.json", "audit.md"]:
        raise BlockerPackageIntegrityError(
            f"阻断目录必须恰好包含 audit.json 与 audit.md：{names}"
        )
    json_path = directory / "audit.json"
    md_path = directory / "audit.md"
    if json_path.read_text(encoding="utf-8") != audit_json_content:
        raise BlockerAuditDriftError("audit.json 内容漂移，拒绝覆盖已接受审计历史")
    if md_path.read_text(encoding="utf-8") != audit_md_content:
        raise BlockerAuditDriftError("audit.md 内容漂移，拒绝覆盖已接受审计历史")
