"""Task 3.2 双重穷尽：搜索/恢复执行者与独立遗漏复核者的类型化分离契约。

- 搜索/恢复执行者与独立遗漏复核者是分离角色：不同角色枚举、不同标识、不同输入摘要。
- 每个阻断缺口必须绑定适用的路线证据（完成/不适用/访问阻断）与恢复证明；
  连续两轮饱和、无关键信息增益的恢复轮次。
- 科学缺失与技术失败分离：科学缺口必须绑定饱和的科学穷尽证明；技术缺口必须绑定
  独立技术诊断 + 同路径重试 + 替代策略证据，不得复用科学 not_found 证明。
- 遗漏复核结论必须与缺口类型相容：科学缺失/冲突只能 NO_MATERIAL_OMISSION；
  技术未解决必须 TECHNICAL_ACCESS_UNRESOLVED；MATERIAL_OMISSION_FOUND 一律不得
  生成审计包。
- 复核结论必须精确绑定其审阅的输入摘要（reviewed_inputs_digest）：由缺口身份、
  单元/对象/状态、适用路线计划、全部路线/回执、恢复/技术证明与逐缺口信息增益
  确定性计算，调用方不得随填；旧摘要、错摘要、换路线后沿用旧结论均失败。
- 路线证据与实际证明逐路线精确绑定：适用路线集合与证明路线完全一致；每条路线的
  回执、尝试次数与访问方式由实际回执派生；回执实体必须是缺口对象或显式声明的
  关联实体；科学 not_found 证明不得重贴到另一路线或塞给技术路线。
- 用户可见文本（路线名称、访问方式、复核说明、诊断说明）必须包含中文语境，
  拒绝纯英文 API/内部标识。
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
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
from ci_workflow.domain.evidence import EvidenceGap, InformationGainDiff, SourceReceipt
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

# 用户可见文本必须真正包含中文：英文专有来源名必须带中文说明
# （如 "ClinicalTrials.gov 登记页"）；NCT/PMID/DOI 只可作为中文句中的标识符。
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def has_chinese_context(value: str) -> bool:
    """机械要求至少含一个中文字符；纯英文专名不再豁免。"""
    return _CJK_RE.search(value) is not None


def assert_user_text_has_chinese_context(value: str) -> str:
    if not has_chinese_context(value):
        raise ValueError("用户可见文本必须包含中文语境，不得使用纯英文内部标识")
    return value


def _not_blank(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("文本不能为空")
    return normalized


def derive_terminal_result_class(
    receipts: Sequence[SourceReceipt],
) -> str:
    """路线最终结果类别由实际回执的确定性终端规则派生。

    终端回执 = 按 ended_at 时间最晚（稳定平局：receipt_id 升序）的最后一次尝试；
    其 result_class 即为路线最终类别。科学路线允许任意终端类别（成功取得内容
    但缺所需字段是合法的），技术访问阻断路线的终端类别必须属于技术失败类别。
    """
    if not receipts:
        raise ValueError("路线回执不能为空")
    terminal = max(
        receipts,
        key=lambda receipt: (receipt.ended_at, receipt.receipt_id),
    )
    return terminal.result_class


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


def compute_reviewer_inputs_digest_from_parts(
    *,
    gap_id: str,
    gate_unit_id: str,
    object_type: str,
    object_id: str,
    current_state: str,
    applicable_route_ids: Sequence[str],
    route_evidence: Sequence[GapRouteEvidence],
    recovery_exhaustion_proofs: Sequence[RecoveryExhaustionProof],
    same_path_retry_audit: SamePathRetryAudit | None,
    alternative_path_audit: AlternativePathAudit | None,
    information_gain_rounds: Sequence[InformationGainDiff],
    associated_entity_ids: Sequence[str],
    evidence_gap: EvidenceGap | None = None,
) -> str:
    """复核输入摘要的纯函数：由缺口身份、单元/对象/状态、适用路线计划、
    Phase2 证据缺口锚点、全部路线/回执、恢复/技术证明与逐缺口信息增益
    确定性计算。复核结论本身不参与本摘要（它是消费方，不是输入）。"""
    route_ids = tuple(sorted(route.route_id for route in route_evidence))
    receipt_ids = tuple(
        sorted(
            receipt_id
            for route in route_evidence
            for receipt_id in route.receipt_ids
        )
    )
    canonical = json.dumps(
        {
            "gap_id": gap_id,
            "gate_unit_id": gate_unit_id,
            "object_type": object_type,
            "object_id": object_id,
            "current_state": current_state,
            "applicable_route_ids": route_ids,
            "receipt_ids": receipt_ids,
            "associated_entity_ids": tuple(sorted(associated_entity_ids)),
            "evidence_gap": (
                evidence_gap.model_dump(mode="json")
                if evidence_gap is not None
                else None
            ),
            "recovery_exhaustion_proofs": [
                proof.model_dump(mode="json") for proof in recovery_exhaustion_proofs
            ],
            "same_path_retry_audit": (
                same_path_retry_audit.model_dump(mode="json")
                if same_path_retry_audit is not None
                else None
            ),
            "alternative_path_audit": (
                alternative_path_audit.model_dump(mode="json")
                if alternative_path_audit is not None
                else None
            ),
            "information_gain_rounds": [
                round_.model_dump(mode="json")
                for round_ in information_gain_rounds
            ],
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return stable_id("omission-review-inputs", canonical)


def compute_reviewer_inputs_digest(
    gap: GapDoubleExhaustion,  # noqa: F821
) -> str:
    """由缺口内容确定性计算复核输入摘要；调用方不得随填。"""
    return compute_reviewer_inputs_digest_from_parts(
        gap_id=gap.gap_id,
        gate_unit_id=gap.gate_unit_id,
        object_type=gap.object_type,
        object_id=gap.object_id,
        current_state=gap.current_state,
        applicable_route_ids=gap.applicable_route_ids,
        route_evidence=gap.route_evidence,
        recovery_exhaustion_proofs=gap.recovery_exhaustion_proofs,
        same_path_retry_audit=gap.same_path_retry_audit,
        alternative_path_audit=gap.alternative_path_audit,
        information_gain_rounds=gap.information_gain_rounds,
        associated_entity_ids=gap.associated_entity_ids,
        evidence_gap=gap.evidence_gap,
    )


def compute_omission_review_digest(review: GapOmissionReview) -> str:  # noqa: F811
    return stable_id(
        "omission-review",
        review.gap_id,
        review.reviewer_role_id,
        review.producer_context_digest,
        review.reviewer_context_digest,
        review.conclusion.value,
        review.review_notes_zh,
        review.reviewed_inputs_digest,
    )


class GapOmissionReview(BaseModel):
    """独立遗漏复核者对单一证据缺口的结论；逐缺口绑定，不能以一句话代替。

    必填 reviewed_inputs_digest 证明本结论审阅的是哪一份输入内容；缺口必须
    与摘要精确一致，结论摘要必须包含该摘要。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    gap_id: str = Field(min_length=1)
    reviewer_role_id: str = Field(min_length=1)
    producer_context_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_context_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    conclusion: OmissionReviewConclusion
    review_notes_zh: str = Field(min_length=1)
    reviewed_inputs_digest: str = Field(min_length=1)

    @field_validator("gap_id", "reviewer_role_id", "review_notes_zh")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("review_notes_zh")
    @classmethod
    def _notes_need_chinese_context(cls, value: str) -> str:
        return assert_user_text_has_chinese_context(value)

    @field_validator("reviewed_inputs_digest")
    @classmethod
    def _digest_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @model_validator(mode="after")
    def _review_context_is_independent(self) -> GapOmissionReview:
        if self.producer_context_digest == self.reviewer_context_digest:
            raise ValueError("遗漏复核必须来自独立干净上下文，不能复用生产者上下文")
        return self

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

    @field_validator("diagnosis_zh")
    @classmethod
    def _diagnosis_needs_chinese_context(cls, value: str) -> str:
        return assert_user_text_has_chinese_context(value)

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
    """单个缺口绑定的一条路线摘要；每条路线仅一行，可汇总多条互不重复的回执。"""

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

    @field_validator("route_name_zh")
    @classmethod
    def _route_name_needs_chinese_context(cls, value: str) -> str:
        return assert_user_text_has_chinese_context(value)

    @field_validator("receipt_ids", "access_methods")
    @classmethod
    def _items_not_blank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_not_blank(value) for value in values)

    @field_validator("access_methods")
    @classmethod
    def _access_methods_need_chinese_context(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            assert_user_text_has_chinese_context(value)
        return values


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


def _proof_receipts(proof: RecoveryExhaustionProof) -> tuple[SourceReceipt, ...]:
    """证明内全部来源回执：恢复轮次 + 替代策略 + 同路径重试。"""
    return tuple(
        [
            *[
                receipt
                for recovery_round in proof.recovery_history.rounds
                for receipt in recovery_round.source_receipts
            ],
            *proof.alternative_paths.source_receipts,
            *[
                receipt
                for audit in proof.same_path_retries
                for receipt in audit.receipts
            ],
        ]
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
    # 科学缺口：逐路线绑定饱和科学穷尽证明（每个适用科学路线一份证明）；
    # 技术缺口：同路径重试 + 替代策略审计。
    recovery_exhaustion_proofs: tuple[RecoveryExhaustionProof, ...] = ()
    same_path_retry_audit: SamePathRetryAudit | None = None
    alternative_path_audit: AlternativePathAudit | None = None
    omission_review: GapOmissionReview
    technical_diagnosis: GapTechnicalDiagnosis | None = None
    information_gain_rounds: tuple[InformationGainDiff, ...] = Field(min_length=2)
    # 显式声明的关联实体（产品缺口允许关联试验来源）；builder 用宇宙关系图验证。
    associated_entity_ids: tuple[str, ...] = ()
    # Phase2 证据缺口锚点：适用路线计划、缺口身份与信息增益的来源，不得自报。
    evidence_gap: EvidenceGap

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

    @field_validator("applicable_route_ids", "associated_entity_ids")
    @classmethod
    def _id_sets_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_not_blank(value) for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("标识集合不得重复")
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
    def _reviewed_inputs_digest_is_exact(self) -> GapDoubleExhaustion:
        expected = compute_reviewer_inputs_digest(self)
        if self.omission_review.reviewed_inputs_digest != expected:
            raise ValueError("遗漏复核必须精确绑定其审阅的输入摘要，摘要与缺口内容不一致")
        return self

    @model_validator(mode="after")
    def _applicable_routes_and_receipts_are_bound(self) -> GapDoubleExhaustion:
        route_ids = {route.route_id for route in self.route_evidence}
        if len(self.route_evidence) != len(self.applicable_route_ids):
            raise ValueError(
                "每个适用路线必须恰有一条路线摘要："
                f"摘要数={len(self.route_evidence)} 适用路线数={len(self.applicable_route_ids)}"
            )
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
    def _evidence_gap_binds_gap_content(self) -> GapDoubleExhaustion:
        """Phase2 EvidenceGap 必须与缺口内容精确一致：身份、候选路线、信息增益、
        已完成策略全部机械绑定，换旧证据缺口/删候选路线/错字段对象状态均失败。"""
        if self.evidence_gap.gap_id != self.gap_id:
            raise ValueError("证据缺口锚点必须绑定同一缺口标识")
        if self.evidence_gap.object_type != self.object_type:
            raise ValueError("证据缺口锚点对象类型与缺口不一致")
        if self.evidence_gap.object_id != self.object_id:
            raise ValueError("证据缺口锚点对象与缺口不一致")
        if self.evidence_gap.current_state != self.current_state:
            raise ValueError("证据缺口锚点状态与缺口不一致")
        if set(self.evidence_gap.candidate_sources) != set(self.applicable_route_ids):
            missing = sorted(
                set(self.applicable_route_ids) - set(self.evidence_gap.candidate_sources)
            )
            extra = sorted(
                set(self.evidence_gap.candidate_sources) - set(self.applicable_route_ids)
            )
            raise ValueError(
                "证据缺口候选路线必须与适用路线完全一致："
                f"缺失={missing} 多余={extra}"
            )
        if self.evidence_gap.information_gain_diff != self.information_gain_rounds:
            raise ValueError("证据缺口信息增益必须与逐缺口信息增益完全一致")
        expected_strategies = self._derive_completed_strategies()
        if tuple(sorted(self.evidence_gap.completed_strategies)) != tuple(
            sorted(expected_strategies)
        ):
            raise ValueError(
                "证据缺口已完成策略必须与实际证明/路线已完成策略相容"
            )
        return self

    def _derive_completed_strategies(self) -> frozenset[str]:
        """从实际证明/审计派生已完成策略标识集合。"""
        strategy_ids: set[str] = set()
        for proof in self.recovery_exhaustion_proofs:
            strategy_ids.update(proof.completed_strategy_unit_ids)
        if self.same_path_retry_audit is not None:
            strategy_ids.update(
                receipt.strategy_unit_id
                for receipt in self.same_path_retry_audit.receipts
            )
        if self.alternative_path_audit is not None:
            strategy_ids.update(
                unit.strategy_unit_id
                for unit in self.alternative_path_audit.strategy_units
                if unit.applicable and unit.completed
            )
        return frozenset(strategy_ids)

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
            # 科学缺口：禁止技术证据，必须绑定逐路线的饱和科学穷尽证明
            if has_technical or access_blocked:
                raise ValueError("科学缺口不得携带技术失败或访问阻断路线")
            if not self.recovery_exhaustion_proofs:
                raise ValueError("科学缺口必须绑定饱和的科学穷尽证明")
            for proof in self.recovery_exhaustion_proofs:
                if not (
                    proof.recovery_history.can_declare_information_saturated
                ):
                    raise ValueError("尚未形成连续两轮无新增关键信息的科学穷尽证据")
            if self.same_path_retry_audit is not None or self.alternative_path_audit is not None:
                raise ValueError("科学缺口不得携带技术重试/替代策略审计")
            if self.technical_diagnosis is not None:
                raise ValueError("科学缺口不得携带技术诊断")
            if (
                self.omission_review.conclusion
                is not OmissionReviewConclusion.NO_MATERIAL_OMISSION
            ):
                raise ValueError("仍发现实质遗漏时不得声明科学证据已穷尽")
            if any(
                item.new_fields or item.new_source_versions
                for item in self.information_gain_rounds
            ):
                raise ValueError(
                    "终态科学穷尽不得携带未由恢复历史绑定的自由字段或来源版本"
                )
        elif is_technical_state:
            # 技术缺口：不得复用科学 not_found 证明，必须绑定技术证据
            if self.recovery_exhaustion_proofs:
                raise ValueError("技术缺口不得复用科学 not_found 穷尽证明")
            if self.same_path_retry_audit is None or self.alternative_path_audit is None:
                raise ValueError("技术缺口必须绑定同路径重试与替代策略审计")
            if self.technical_diagnosis is None:
                raise ValueError("访问阻断结论必须绑定独立技术诊断")
            if not has_technical and not access_blocked:
                raise ValueError("技术缺口必须包含技术失败或访问阻断路线")
            if (
                self.omission_review.conclusion
                is not OmissionReviewConclusion.TECHNICAL_ACCESS_UNRESOLVED
            ):
                raise ValueError("技术缺口必须保留访问未解决的独立复核结论")
            if any(
                item.new_fields
                or item.new_source_versions
                or item.new_evidence_fragment_ids
                or item.changed_gate_unit_ids
                or item.reduced_conflict_set_ids
                for item in self.information_gain_rounds
            ):
                raise ValueError("技术访问未解决不得携带未由恢复历史证明的信息增益")
        return self

    @model_validator(mode="after")
    def _routes_bind_proofs_per_route(self) -> GapDoubleExhaustion:
        """路线证据与实际证明逐路线精确绑定：route IDs exact、每条路线回执 exact、
        attempt_count 与 access_methods 由实际回执派生。"""
        is_scientific = (
            self.current_state in SCIENCE_ABSENT_STATES or self.current_state == "conflicting"
        )
        if is_scientific:
            proof_routes = [
                proof.execution_context[0] for proof in self.recovery_exhaustion_proofs
            ]
            if len(proof_routes) != len(set(proof_routes)):
                raise ValueError("同一科学证明不得重复贴到同一路线")
            if set(proof_routes) != set(self.applicable_route_ids):
                missing = sorted(set(self.applicable_route_ids) - set(proof_routes))
                extra = sorted(set(proof_routes) - set(self.applicable_route_ids))
                raise ValueError(
                    "逐路线科学证明必须与适用路线集合完全一致："
                    f"缺失={missing} 多余={extra}"
                )
            for proof in self.recovery_exhaustion_proofs:
                route_id = proof.execution_context[0]
                route = next(
                    item for item in self.route_evidence if item.route_id == route_id
                )
                receipts = _proof_receipts(proof)
                self._assert_route_derived_from_receipts(route, receipts)
        else:
            # 技术缺口：每条适用路线都必须失败关闭验证。
            # 当前 Phase2 合同不能表示多路线技术/科学完成/不适用路线，
            # 故只接受访问阻断路线，且回执必须来自本路线的重试/替代审计；
            # 第二假路线、已完成科学路线、不适用路线一律拒绝。
            if self.same_path_retry_audit is None or self.alternative_path_audit is None:
                raise ValueError("技术缺口必须绑定同路径重试与替代策略审计")
            tech_receipts = (
                *self.same_path_retry_audit.receipts,
                *self.alternative_path_audit.source_receipts,
            )
            if len(self.route_evidence) != len(self.applicable_route_ids):
                raise ValueError("路线证据必须与适用路线集合一一对应")
            for route in self.route_evidence:
                if (
                    route.completion
                    is not RouteCompletionState.ACCESS_BLOCKED
                ):
                    raise ValueError(
                        "技术缺口当前合同只接受访问阻断路线，"
                        "不得接收自由完成的科学路线或自由不适用路线"
                    )
                route_receipts = tuple(
                    receipt
                    for receipt in tech_receipts
                    if receipt.route_id == route.route_id
                )
                self._assert_route_derived_from_receipts(route, route_receipts)
        return self

    @staticmethod
    def _assert_route_derived_from_receipts(
        route: GapRouteEvidence,
        receipts: Sequence[SourceReceipt],
    ) -> None:
        by_id: dict[str, SourceReceipt] = {}
        for receipt in receipts:
            by_id.setdefault(receipt.receipt_id, receipt)
        unique = tuple(by_id.values())
        receipt_ids = set(by_id)
        if set(route.receipt_ids) != receipt_ids:
            missing = sorted(receipt_ids - set(route.receipt_ids))
            extra = sorted(set(route.receipt_ids) - receipt_ids)
            raise ValueError(
                "路线回执必须与实际证明完全一致：缺失="
                f"{missing} 多余={extra}"
            )
        if route.attempt_count != len(receipt_ids):
            raise ValueError("路线尝试次数必须由实际回执数派生")
        derived_methods = tuple(sorted({receipt.access_method for receipt in unique}))
        if tuple(sorted(route.access_methods)) != derived_methods:
            raise ValueError("路线访问方式必须由实际回执派生")
        # 最终结果类别必须由实际回执终端规则派生，调用方不得自报
        derived_class = derive_terminal_result_class(unique)
        if route.final_result_class != derived_class:
            raise ValueError(
                "路线最终结果类别必须由实际回执终端规则派生："
                f"声明={route.final_result_class} 派生={derived_class}"
            )
        if (
            route.completion is RouteCompletionState.ACCESS_BLOCKED
            and derived_class not in TECHNICAL_RESULT_CLASSES
        ):
            raise ValueError(
                "访问阻断路线的最终结果类别必须是技术失败类别："
                f"派生={derived_class}"
            )

    @model_validator(mode="after")
    def _receipt_entities_bind_gap_or_associated(self) -> GapDoubleExhaustion:
        """回执 gap/entity/claim 上下文必须与缺口及显式关联实体一致。"""
        allowed_entities = frozenset({self.object_id, *self.associated_entity_ids})
        for receipt in self._all_receipts():
            if receipt.gap_id != self.gap_id:
                raise ValueError("缺口回执必须全部绑定同一证据缺口")
            if receipt.entity_id not in allowed_entities:
                raise ValueError(
                    f"回执实体 {receipt.entity_id} 必须绑定缺口对象或显式声明的关联实体"
                )
        return self

    def _all_receipts(self) -> tuple[SourceReceipt, ...]:
        receipts: list[SourceReceipt] = []
        for proof in self.recovery_exhaustion_proofs:
            receipts.extend(_proof_receipts(proof))
        if self.same_path_retry_audit is not None:
            receipts.extend(self.same_path_retry_audit.receipts)
        if self.alternative_path_audit is not None:
            receipts.extend(self.alternative_path_audit.source_receipts)
        return tuple(receipts)

    @model_validator(mode="after")
    def _information_gain_rounds_align_with_history(self) -> GapDoubleExhaustion:
        """信息增益轮次必须与每个科学证明的恢复历史逐轮对齐：
        摘要声明有增益 ⇔ 历史轮次有门槛相关增益；不得笼统宣称两轮无增益。"""
        if self.current_state in SCIENCE_ABSENT_STATES or self.current_state == "conflicting":
            for proof in self.recovery_exhaustion_proofs:
                history_rounds = proof.recovery_history.rounds
                if len(history_rounds) != len(self.information_gain_rounds):
                    raise ValueError("信息增益轮次必须与恢复历史轮次一一对应")
                for gain_diff, history_round in zip(
                    self.information_gain_rounds, history_rounds, strict=True
                ):
                    gain = history_round.information_gain
                    if (
                        tuple(gain_diff.new_evidence_fragment_ids)
                        != tuple(gain.new_evidence_fragment_ids)
                        or tuple(gain_diff.changed_gate_unit_ids)
                        != tuple(gain.changed_gate_unit_ids)
                        or tuple(gain_diff.reduced_conflict_set_ids)
                        != tuple(gain.reduced_conflict_set_ids)
                    ):
                        raise ValueError(
                            "信息增益证据标识必须与恢复历史逐轮完全一致"
                        )
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
