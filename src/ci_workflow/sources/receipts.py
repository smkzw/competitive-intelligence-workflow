from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.evidence import EvidenceGap, SourceReceipt
from ci_workflow.sources.policy import SourceApplicability, SourceEligibility


class AttemptResultClass(StrEnum):
    CONTENT_ACQUIRED = "content_acquired"
    NOT_FOUND = "not_found"
    NETWORK_ERROR = "network_error"
    RATE_LIMITED = "rate_limited"
    CAPTCHA_REQUIRED = "captcha_required"
    PERMISSION_DENIED = "permission_denied"
    PROXY_ERROR = "proxy_error"
    DNS_ERROR = "dns_error"
    TLS_ERROR = "tls_error"
    HTTP_ERROR = "http_error"
    PARSER_ERROR = "parser_error"
    TOOL_UNAVAILABLE = "tool_unavailable"
    CONTENT_TRUNCATED = "content_truncated"


class RouteAttemptResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_id: str = Field(min_length=1)
    result_class: AttemptResultClass
    detail_zh: str = Field(min_length=1)

    @field_validator("attempt_id", "detail_zh")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("路线尝试结果字段不能为空")
        return normalized


class EvidenceAuditBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_receipts: tuple[SourceReceipt, ...] = ()
    source_eligibilities: tuple[SourceEligibility, ...] = Field(min_length=1)
    evidence_gap: EvidenceGap

    @model_validator(mode="after")
    def _receipts_bind_one_gap(self) -> EvidenceAuditBundle:
        if any(
            receipt.gap_id != self.evidence_gap.gap_id
            for receipt in self.source_receipts
        ):
            raise ValueError("来源回执与证据缺口标识不一致")
        if any(
            item.gap_id != self.evidence_gap.gap_id
            for item in self.source_eligibilities
        ):
            raise ValueError("来源适用性与证据缺口标识不一致")
        return self

    def assert_supports(
        self,
        *,
        route_id: str,
        completion_state: str,
        completed_strategy_unit_ids: tuple[str, ...],
    ) -> None:
        if any(receipt.route_id != route_id for receipt in self.source_receipts):
            raise ValueError("审计包包含其它来源路线的回执")
        if any(item.route_id != route_id for item in self.source_eligibilities):
            raise ValueError("审计包包含其它来源路线的适用性决定")
        receipt_strategy_ids = {
            receipt.strategy_unit_id for receipt in self.source_receipts
        }
        eligibility_by_strategy = {
            item.strategy_unit_id: item for item in self.source_eligibilities
        }
        completed_strategy_ids = set(completed_strategy_unit_ids)
        if not completed_strategy_ids <= set(eligibility_by_strategy):
            raise ValueError("路线完成策略缺少来源适用性决定")
        if not completed_strategy_ids <= set(self.evidence_gap.completed_strategies):
            raise ValueError("路线完成策略未写入证据缺口审计")
        selected_eligibilities = tuple(
            eligibility_by_strategy[item] for item in completed_strategy_unit_ids
        )
        if completion_state == "route_completed":
            if any(
                item.applicability is not SourceApplicability.APPLICABLE
                for item in selected_eligibilities
            ):
                raise ValueError("已完成路线的策略必须明确适用")
            if not completed_strategy_ids <= receipt_strategy_ids:
                raise ValueError("路线完成策略缺少来源回执")
        elif completion_state == "route_not_applicable":
            if any(
                item.applicability is not SourceApplicability.NOT_APPLICABLE
                for item in selected_eligibilities
            ):
                raise ValueError("不适用路线必须有对应适用性决定")
        elif completion_state == "route_access_blocked":
            if any(
                item.applicability is not SourceApplicability.ACCESS_BLOCKED
                for item in selected_eligibilities
            ):
                raise ValueError("访问阻断路线必须有对应适用性决定")
            if not completed_strategy_ids <= receipt_strategy_ids:
                raise ValueError("访问阻断路线缺少来源尝试回执")
            selected_receipts = tuple(
                receipt
                for receipt in self.source_receipts
                if receipt.strategy_unit_id in completed_strategy_ids
            )
            if any(
                receipt.result_class in {"content_acquired", "not_found"}
                for receipt in selected_receipts
            ):
                raise ValueError("访问阻断路线不能使用成功或未找到回执")
        else:
            raise ValueError("未知路线完成状态")
