"""Task 3.2 双重穷尽：搜索/恢复执行者与独立遗漏复核者的类型化分离契约。

- 搜索/恢复执行者与独立遗漏复核者是分离角色：不同角色枚举、不同标识、不同输入摘要。
- 每个阻断缺口必须绑定适用的路线证据（完成/不适用/访问阻断）与恢复证明；
  连续两轮饱和、无关键信息增益的恢复轮次。
- 科学缺失与技术失败分离：科学缺口必须绑定饱和的科学穷尽证明；技术缺口必须绑定
  独立技术诊断 + 同路径重试 + 替代策略证据，不得复用科学 not_found 证明。
- 遗漏复核结论必须与缺口类型相容：科学缺失/冲突只能 NO_MATERIAL_OMISSION；
  技术未解决必须 TECHNICAL_ACCESS_UNRESOLVED；MATERIAL_OMISSION_FOUND 一律不得
  生成审计包。
- 复核输入摘要由缺口内容确定性计算，调用方不得随填。
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum

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
from ci_workflow.sources.planner import RouteCompletionState
from ci_workflow.sources.retries import (
    AlternativePathAudit,
    RecoveryExhaustionProof,
    SamePathRetryAudit,
)

TECHNICAL_RESULT_CLASSES = frozenset(
    {
        "network_error",
        "rate_limited",
        "captcha_required",
        "permission_denied",
        "proxy_error",
        "dns_error",
        "tls_error",
        "http_error",
        "parser_error",
        "tool_unavailable",
        "content_truncated",
    }
)

SCIENCE_ABSENT_STATES = frozenset({"not_reported", "not_publicly_disclosed"})

GAP_STATES = frozenset(
    {"not_reported", "not_publicly_disclosed", "conflicting", "unresolved_due_to_route"}
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


class ExhaustionRole(StrEnum):
    """双重穷尽的两类分离角色。"""

    EXECUTOR = "search_recovery_executor"
    REVIEWER = "independent_omission_reviewer"


class OmissionReviewConclusion(StrEnum):
    """独立遗漏复核者的逐缺口结论。"""

    NO_MATERIAL_OMISSION = "no_material_omission"
    MATERIAL_OMISSION_FOUND = "material_omission_found"
    TECHNICAL_ACCESS_UNRESOLVED = "technical_access_unresolved"


def compute_reviewer_inputs_digest(
    gap: GapDoubleExhaustion,  # noqa: F821
) -> str:
    """复核输入摘要由缺口内容确定性计算：缺口、单元/对象/状态、适用路线、
    路线回执、恢复证明与信息增益轮次全部参与，调用方不得随填。"""
    route_ids = tuple(sorted(route.route_id for route in gap.route_evidence))
    receipt_ids = tuple(
        sorted(
            receipt_id
            for route in gap.route_evidence
            for receipt_id in route.receipt_ids
        )
    )
    proof_digest = (
        gap.recovery_exhaustion_proof.model_dump(mode="json")
        if gap.recovery_exhaustion_proof is not None
        else None
    )
    retry_digest = (
        gap.same_path_retry_audit.model_dump(mode="json")
        if gap.same_path_retry_audit is not None
        else None
    )
    alternative_digest = (
        gap.alternative_path_audit.model_dump(mode="json")
        if gap.alternative_path_audit is not None
        else None
    )
    canonical = json.dumps(
        {
            "gap_id": gap.gap_id,
            "gate_unit_id": gap.gate_unit_id,
            "object_type": gap.object_type,
            "object_id": gap.object_id,
            "current_state": gap.current_state,
            "applicable_route_ids": route_ids,
            "receipt_ids": receipt_ids,
            "recovery_exhaustion_proof": proof_digest,
            "same_path_retry_audit": retry_digest,
            "alternative_path_audit": alternative_digest,
            "information_gain_rounds": [
                round_.model_dump(mode="json")
                for round_ in gap.information_gain_rounds
            ],
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return stable_id("omission-review-inputs", canonical)


def compute_omission_review_digest(review: GapOmissionReview) -> str:  # noqa: F811
    return stable_id(
        "omission-review",
        review.gap_id,
        review.reviewer_role_id,
        review.conclusion.value,
        review.review_notes_zh,
    )


class GapOmissionReview(BaseModel):
    """独立遗漏复核者对单一证据缺口的结论；逐缺口绑定，不能以一句话代替。

    复核输入摘要由所属缺口确定性计算，故不在复核对象上存储。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    gap_id: str = Field(min_length=1)
    reviewer_role_id: str = Field(min_length=1)
    conclusion: OmissionReviewConclusion
    review_notes_zh: str = Field(min_length=1)

    @field_validator("gap_id", "reviewer_role_id", "review_notes_zh")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def conclusion_digest(self) -> str:
        return compute_omission_review_digest(self)


def compute_technical_diagnosis_digest(diagnosis: GapTechnicalDiagnosis) -> str:  # noqa: F811
    return stable_id(
        "technical-diagnosis",
        diagnosis.gap_id,
        diagnosis.reviewer_role_id,
        *tuple(sorted(diagnosis.technical_result_classes)),
        str(diagnosis.same_path_retry_completed),
        str(diagnosis.alternative_strategies_completed),
        diagnosis.diagnosis_zh,
    )


class GapTechnicalDiagnosis(BaseModel):
    """独立技术诊断：技术失败不得改写为科学缺失。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    gap_id: str = Field(min_length=1)
    reviewer_role_id: str = Field(min_length=1)
    technical_result_classes: tuple[str, ...] = Field(min_length=1)
    same_path_retry_completed: bool
    alternative_strategies_completed: bool
    diagnosis_zh: str = Field(min_length=1)

    @field_validator("gap_id", "reviewer_role_id", "diagnosis_zh")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("technical_result_classes")
    @classmethod
    def _technical_classes_are_unique_and_closed(
        cls, values: tuple[str, ...]
    ) -> tuple[str, ...]:
        normalized = tuple(_not_blank(value) for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("技术失败类别不得重复")
        if not set(normalized) <= TECHNICAL_RESULT_CLASSES:
            raise ValueError("技术失败类别必须是封闭集合成员")
        return normalized

    @computed_field  # type: ignore[prop-decorator]
    @property
    def diagnosis_digest(self) -> str:
        return compute_technical_diagnosis_digest(self)

    @model_validator(mode="after")
    def _diagnosis_requires_completed_retries_and_alternatives(self) -> GapTechnicalDiagnosis:
        if not self.same_path_retry_completed or not self.alternative_strategies_completed:
            raise ValueError("技术诊断必须建立在已完成的同路径重试与替代策略之上")
        return self


class GapRouteEvidence(BaseModel):
    """单个缺口绑定的路线证据摘要；路线 ID 可重复（多条回执），但 receipt 互不相交。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    route_id: str = Field(min_length=1)
    route_name_zh: str = Field(min_length=1)
    completion: RouteCompletionState
    final_result_class: str = Field(min_length=1)
    attempt_count: int = Field(ge=1)
    receipt_ids: tuple[str, ...] = Field(min_length=1)
    access_methods: tuple[str, ...] = Field(min_length=1)

    @field_validator("route_id", "route_name_zh", "final_result_class")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("receipt_ids", "access_methods")
    @classmethod
    def _items_not_blank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_not_blank(value) for value in values)


def compute_gap_digest(gap: GapDoubleExhaustion) -> str:  # noqa: F811
    """缺口穷尽摘要必须覆盖全部证据内容。"""
    content = json.dumps(
        gap.model_dump(mode="json", exclude={"gap_digest"}),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return stable_id(
        "gap-exhaustion",
        gap.gap_id,
        gap.gate_unit_id,
        gap.object_type,
        gap.object_id,
        gap.current_state,
        content,
    )


class GapDoubleExhaustion(BaseModel):
    """单个证据缺口的双重穷尽证据：角色分离、复核输入绑定、路线与证明绑定。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    gap_id: str = Field(min_length=1)
    gate_unit_id: str = Field(min_length=1)
    object_type: str = Field(min_length=1)
    object_id: str = Field(min_length=1)
    current_state: str
    executor_role: ExhaustionRole = ExhaustionRole.EXECUTOR
    reviewer_role: ExhaustionRole = ExhaustionRole.REVIEWER
    executor_role_id: str = Field(min_length=1)
    reviewer_role_id: str = Field(min_length=1)
    applicable_route_ids: tuple[str, ...] = Field(min_length=1)
    route_evidence: tuple[GapRouteEvidence, ...] = Field(min_length=1)
    # 科学缺口：饱和科学穷尽证明；技术缺口：同路径重试 + 替代策略审计
    recovery_exhaustion_proof: RecoveryExhaustionProof | None = None
    same_path_retry_audit: SamePathRetryAudit | None = None
    alternative_path_audit: AlternativePathAudit | None = None
    omission_review: GapOmissionReview
    technical_diagnosis: GapTechnicalDiagnosis | None = None
    information_gain_rounds: tuple[InformationGainDiff, ...] = Field(min_length=2)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def gap_digest(self) -> str:
        return compute_gap_digest(self)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def reviewer_inputs_digest(self) -> str:
        return compute_reviewer_inputs_digest(self)

    @field_validator("gap_id", "gate_unit_id", "object_type", "object_id")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("applicable_route_ids")
    @classmethod
    def _applicable_routes_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_not_blank(value) for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("适用路线集合不得重复")
        return normalized

    @field_validator("current_state")
    @classmethod
    def _current_state_is_closed(cls, value: str) -> str:
        if value not in GAP_STATES:
            raise ValueError("缺口当前状态必须是封闭集合成员")
        return value

    @model_validator(mode="after")
    def _roles_are_separate_and_typed(self) -> GapDoubleExhaustion:
        if self.executor_role is not ExhaustionRole.EXECUTOR:
            raise ValueError("执行者角色必须是 search_recovery_executor")
        if self.reviewer_role is not ExhaustionRole.REVIEWER:
            raise ValueError("复核者角色必须是 independent_omission_reviewer")
        if self.executor_role_id == self.reviewer_role_id:
            raise ValueError("搜索/恢复执行者与独立遗漏复核者必须是不同角色")
        if self.omission_review.gap_id != self.gap_id:
            raise ValueError("遗漏复核必须绑定同一证据缺口")
        if self.omission_review.reviewer_role_id != self.reviewer_role_id:
            raise ValueError("遗漏复核者必须与缺口声明的复核者一致")
        if self.technical_diagnosis is not None and (
            self.technical_diagnosis.gap_id != self.gap_id
            or self.technical_diagnosis.reviewer_role_id != self.reviewer_role_id
        ):
            raise ValueError("技术诊断必须由独立复核者针对同一缺口给出")
        return self

    @model_validator(mode="after")
    def _applicable_routes_and_receipts_are_bound(self) -> GapDoubleExhaustion:
        route_ids = {route.route_id for route in self.route_evidence}
        if route_ids != set(self.applicable_route_ids):
            missing = sorted(set(self.applicable_route_ids) - route_ids)
            extra = sorted(route_ids - set(self.applicable_route_ids))
            raise ValueError(
                f"路线证据必须与适用路线集合一致：缺失={missing} 多余={extra}"
            )
        all_receipts: list[str] = []
        for route in self.route_evidence:
            all_receipts.extend(route.receipt_ids)
        if len(set(all_receipts)) != len(all_receipts):
            raise ValueError("不同路线的来源回执必须互不相交")
        return self

    @model_validator(mode="after")
    def _gap_type_binds_compatible_evidence(self) -> GapDoubleExhaustion:
        final_classes = {route.final_result_class for route in self.route_evidence}
        has_technical = bool(final_classes & TECHNICAL_RESULT_CLASSES)
        access_blocked = any(
            route.completion is RouteCompletionState.ACCESS_BLOCKED
            for route in self.route_evidence
        )
        is_technical_state = self.current_state == "unresolved_due_to_route"

        if self.current_state in SCIENCE_ABSENT_STATES or self.current_state == "conflicting":
            # 科学缺口：禁止技术证据，必须绑定饱和科学穷尽证明
            if has_technical or access_blocked:
                raise ValueError("科学缺口不得携带技术失败或访问阻断路线")
            if self.recovery_exhaustion_proof is None:
                raise ValueError("科学缺口必须绑定饱和的科学穷尽证明")
            if not (
                self.recovery_exhaustion_proof.recovery_history
                .can_declare_information_saturated
            ):
                raise ValueError("尚未形成连续两轮无新增关键信息的科学穷尽证据")
            if self.same_path_retry_audit is not None or self.alternative_path_audit is not None:
                raise ValueError("科学缺口不得携带技术重试/替代策略审计")
            if self.technical_diagnosis is not None:
                raise ValueError("科学缺口不得携带技术诊断")
        elif is_technical_state:
            # 技术缺口：不得复用科学 not_found 证明，必须绑定技术证据
            if self.recovery_exhaustion_proof is not None:
                raise ValueError("技术缺口不得复用科学 not_found 穷尽证明")
            if self.same_path_retry_audit is None or self.alternative_path_audit is None:
                raise ValueError("技术缺口必须绑定同路径重试与替代策略审计")
            if self.technical_diagnosis is None:
                raise ValueError("访问阻断结论必须绑定独立技术诊断")
            if not has_technical and not access_blocked:
                raise ValueError("技术缺口必须包含技术失败或访问阻断路线")
        return self

    @model_validator(mode="after")
    def _routes_bind_proof_receipts(self) -> GapDoubleExhaustion:
        if self.recovery_exhaustion_proof is not None:
            proof_receipt_ids = {
                receipt.receipt_id
                for recovery_round in self.recovery_exhaustion_proof.recovery_history.rounds
                for receipt in recovery_round.source_receipts
            }
            proof_gap_ids = {
                receipt.gap_id
                for recovery_round in self.recovery_exhaustion_proof.recovery_history.rounds
                for receipt in recovery_round.source_receipts
            }
            if proof_gap_ids != {self.gap_id}:
                raise ValueError("恢复证明回执必须全部绑定同一缺口")
            for route in self.route_evidence:
                if not set(route.receipt_ids) <= proof_receipt_ids:
                    raise ValueError("科学路线回执必须来自恢复证明")
                for receipt_id in route.receipt_ids:
                    matching = [
                        r
                        for recovery_round in self.recovery_exhaustion_proof.recovery_history.rounds
                        for r in recovery_round.source_receipts
                        if r.receipt_id == receipt_id
                    ]
                    if not matching or matching[0].route_id != route.route_id:
                        raise ValueError("路线回执与恢复证明路线不一致")
        if self.same_path_retry_audit is not None:
            retry_receipt_ids = {r.receipt_id for r in self.same_path_retry_audit.receipts}
            route_receipt_ids = {
                r for route in self.route_evidence for r in route.receipt_ids
            }
            if not retry_receipt_ids <= route_receipt_ids:
                raise ValueError("技术重试回执必须进入缺口路线证据")
            if any(r.gap_id != self.gap_id for r in self.same_path_retry_audit.receipts):
                raise ValueError("技术重试回执必须绑定同一缺口")
        if self.alternative_path_audit is not None:
            alternative_receipt_ids = {
                r.receipt_id for r in self.alternative_path_audit.source_receipts
            }
            route_receipt_ids = {
                r for route in self.route_evidence for r in route.receipt_ids
            }
            if not alternative_receipt_ids <= route_receipt_ids:
                raise ValueError("替代策略回执必须进入缺口路线证据")
        return self

    @model_validator(mode="after")
    def _information_gain_rounds_are_contiguous(self) -> GapDoubleExhaustion:
        rounds = tuple(item.round for item in self.information_gain_rounds)
        if rounds != tuple(range(1, len(rounds) + 1)):
            raise ValueError("信息增益轮次必须从一开始连续递增")
        return self


def compute_record_digest(record: DoubleExhaustionRecord) -> str:  # noqa: F811
    return stable_id(
        "double-exhaustion",
        record.project_id,
        record.report_kind.value,
        *tuple(gap.gap_digest for gap in record.gaps),
    )


class DoubleExhaustionRecord(BaseModel):
    """整个项目报告的双重穷尽记录：所有阻断缺口逐一绑定。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"
    project_id: str = Field(min_length=1)
    report_kind: ReportKind
    gaps: tuple[GapDoubleExhaustion, ...] = Field(min_length=1)
    created_at: datetime

    @field_validator("project_id")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("created_at")
    @classmethod
    def _created_at_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @model_validator(mode="after")
    def _record_gap_identities_are_unique(self) -> DoubleExhaustionRecord:
        gap_ids = tuple(gap.gap_id for gap in self.gaps)
        if len(set(gap_ids)) != len(gap_ids):
            raise ValueError("双重穷尽记录不得包含重复缺口标识")
        identities = tuple(
            (gap.gate_unit_id, gap.object_id) for gap in self.gaps
        )
        if len(set(identities)) != len(identities):
            raise ValueError("同一单元同一对象不得重复声明双重穷尽缺口")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def record_digest(self) -> str:
        return compute_record_digest(self)


def assert_gap_technical_failure_not_reclassified(gap: GapDoubleExhaustion) -> None:
    """技术失败不得被改写成科学缺失；任何缺口违反即失败关闭。"""
    final_classes = {route.final_result_class for route in gap.route_evidence}
    has_technical = bool(final_classes & TECHNICAL_RESULT_CLASSES)
    if gap.current_state in SCIENCE_ABSENT_STATES and has_technical:
        raise ValueError("技术失败不得写成未报告或未公开")
