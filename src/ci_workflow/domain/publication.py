"""Authoritative v1.3 publication verdict and acquisition receipts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any, Literal, Self
from urllib.parse import urlsplit

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator

PublicationClass = Literal[
    "primary_result",
    "extension_primary_result",
    "key_safety_or_long_term",
    "review",
    "ad_hoc",
    "irrelevant_exploratory",
]
PublicationDecision = Literal["required", "excluded"]
ClassificationReviewState = Literal["accepted", "boundary", "rejected"]
PublicationFetchResult = Literal[
    "acquired",
    "searched_no_evidence",
    "not_publicly_disclosed",
    "access_or_permission_blocked",
    "transient_network_failure",
    "rate_limited",
    "anti_bot_or_captcha",
    "source_unavailable",
    "parser_or_schema_failure",
    "tool_capability_gap",
    "content_truncated",
]
PublicationFetchRouteFamily = Literal[
    "publisher",
    "bibliographic_index",
    "open_repository",
    "registry_attachment",
    "regulatory_repository",
]
PublicationSearchResult = Literal[
    "publications_classified",
    "searched_no_linked_publication",
]
PublicationAcquisitionDisposition = Literal[
    "acquired",
    "manual_required",
    "excluded",
]
ReportName = Literal["A", "B", "C"]

REQUIRED_PUBLICATION_CLASSES: frozenset[PublicationClass] = frozenset(
    {"primary_result", "extension_primary_result", "key_safety_or_long_term"}
)
EXCLUDED_PUBLICATION_CLASSES: frozenset[PublicationClass] = frozenset(
    {"review", "ad_hoc", "irrelevant_exploratory"}
)
RETRYABLE_FETCH_RESULTS: frozenset[PublicationFetchResult] = frozenset(
    {
        "transient_network_failure",
        "rate_limited",
        "anti_bot_or_captcha",
        "source_unavailable",
        "parser_or_schema_failure",
        "tool_capability_gap",
        "content_truncated",
    }
)


class PublicationContractError(ValueError):
    """A publication verdict or acquisition receipt is incoherent."""


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


def _text(value: str, label: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{label}不能为空")
    return normalized


def _items(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    normalized = tuple(_text(value, label) for value in values)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{label}不能重复")
    return normalized


class PublicationFetchAttempt(_StrictModel):
    """One typed attempt to acquire a required publication."""

    attempt_id: str
    strategy_id: str
    route_family: PublicationFetchRouteFamily
    attempted_at: datetime
    result_class: PublicationFetchResult
    source_id: str | None = None
    diagnostic: str | None = None

    @field_validator("attempt_id", "strategy_id")
    @classmethod
    def _ids(cls, value: str, info: Any) -> str:
        return _text(value, str(info.field_name))

    @field_validator("attempted_at")
    @classmethod
    def _time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("获取尝试时间必须包含明确时区")
        return value

    @field_validator("source_id", "diagnostic")
    @classmethod
    def _optional_text(cls, value: str | None, info: Any) -> str | None:
        return None if value is None else _text(value, str(info.field_name))

    @model_validator(mode="after")
    def _result_is_auditable(self) -> Self:
        if self.result_class == "acquired" and not self.source_id:
            raise PublicationContractError("成功获取必须绑定来源版本")
        if self.result_class != "acquired" and not self.diagnostic:
            raise PublicationContractError("未获取 publication 的尝试必须保留细粒度诊断")
        return self

    @property
    def retryable(self) -> bool:
        return self.result_class in RETRYABLE_FETCH_RESULTS


class PublicationSearchReceipt(_StrictModel):
    """Auditable proof that publication discovery ran for one included trial."""

    search_id: str
    trial_id: str
    registry_identifiers: tuple[str, ...] = Field(min_length=1)
    route_families: tuple[PublicationFetchRouteFamily, ...] = Field(min_length=2)
    attempt_ids: tuple[str, ...] = Field(min_length=2)
    query_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    result: PublicationSearchResult
    discovered_publication_ids: tuple[str, ...] = ()
    diagnostic: str | None = None

    @field_validator("search_id", "trial_id")
    @classmethod
    def _search_ids(cls, value: str, info: Any) -> str:
        return _text(value, str(info.field_name))

    @field_validator(
        "registry_identifiers",
        "route_families",
        "attempt_ids",
        "discovered_publication_ids",
    )
    @classmethod
    def _search_items(cls, values: tuple[str, ...], info: Any) -> tuple[str, ...]:
        return _items(values, str(info.field_name))

    @field_validator("diagnostic")
    @classmethod
    def _search_diagnostic(cls, value: str | None) -> str | None:
        return None if value is None else _text(value, "diagnostic")

    @model_validator(mode="after")
    def _search_result_is_coherent(self) -> Self:
        if self.result == "publications_classified" and not self.discovered_publication_ids:
            raise PublicationContractError("发现 publication 时必须绑定正式 verdict 标识")
        if self.result == "searched_no_linked_publication" and (
            self.discovered_publication_ids or not self.diagnostic
        ):
            raise PublicationContractError("未发现关联 publication 必须保留诊断且不得绑定 verdict")
        return self


class _PublicationReviewMaterial(_StrictModel):
    schema_version: Literal["1.3"] = "1.3"
    publication_id: str
    source_id: str
    product_id: str
    linked_trial_ids: tuple[str, ...] = Field(
        min_length=1, validation_alias=AliasChoices("linked_trial_ids", "trial_ids")
    )
    registry_identifiers: tuple[str, ...] = Field(min_length=1)
    title: str
    source_url: str
    publication_class: PublicationClass = Field(
        validation_alias=AliasChoices("publication_class", "classification")
    )
    rule_version: Literal["1.3"] = "1.3"
    model_suggestion: PublicationClass
    classification_reason: str
    review_state: ClassificationReviewState = "accepted"
    producer_id: str
    producer_context: str
    doi: str | None = None
    pmid: str | None = None
    fetch_attempts: tuple[PublicationFetchAttempt, ...] = ()
    acquisition_disposition: PublicationAcquisitionDisposition
    blocking_fields: tuple[str, ...] = ()
    affected_reports: tuple[ReportName, ...] = ()


def compute_publication_review_digest(payload: Mapping[str, Any]) -> str:
    """Hash the exact classification/acquisition candidate seen by the reviewer."""

    review_only = {
        "independent_review_id",
        "independent_reviewer_id",
        "independent_context",
        "reviewed_candidate_sha256",
    }
    material = _PublicationReviewMaterial.model_validate(
        {key: value for key, value in payload.items() if key not in review_only}
    ).model_dump(mode="json")
    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class PublicationRecord(_PublicationReviewMaterial):
    """The sole authoritative, registry-bound publication verdict."""

    independent_review_id: str | None = None
    independent_reviewer_id: str | None = None
    independent_context: str | None = None
    reviewed_candidate_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator(
        "publication_id",
        "source_id",
        "product_id",
        "title",
        "classification_reason",
        "producer_id",
        "producer_context",
    )
    @classmethod
    def _text_fields(cls, value: str, info: Any) -> str:
        return _text(value, str(info.field_name))

    @field_validator("linked_trial_ids", "registry_identifiers", "blocking_fields")
    @classmethod
    def _unique_items(cls, values: tuple[str, ...], info: Any) -> tuple[str, ...]:
        return _items(values, str(info.field_name))

    @field_validator("affected_reports")
    @classmethod
    def _reports(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _items(values, "affected_reports")

    @field_validator("source_url")
    @classmethod
    def _url(cls, value: str) -> str:
        normalized = _text(value, "source_url")
        parsed = urlsplit(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("source_url必须是外部 http(s) 地址")
        return normalized

    @field_validator(
        "doi",
        "pmid",
        "independent_review_id",
        "independent_reviewer_id",
        "independent_context",
    )
    @classmethod
    def _optional_fields(cls, value: str | None, info: Any) -> str | None:
        return None if value is None else _text(value, str(info.field_name))

    @model_validator(mode="after")
    def _verdict_is_closed(self) -> Self:
        needs_review = (
            self.model_suggestion != self.publication_class or self.review_state == "boundary"
        )
        review_fields = (
            self.independent_review_id,
            self.independent_reviewer_id,
            self.independent_context,
            self.reviewed_candidate_sha256,
        )
        if needs_review and not all(review_fields):
            raise PublicationContractError("分歧或边界 publication 必须由独立上下文复核")
        if any(review_fields) and not all(review_fields):
            raise PublicationContractError("独立复核身份、上下文和摘要必须完整记录")
        if self.independent_reviewer_id == self.producer_id:
            raise PublicationContractError("publication 独立复核不得复用生产者身份")
        if self.independent_context == self.producer_context:
            raise PublicationContractError("publication 独立复核不得复用生产上下文")
        if self.reviewed_candidate_sha256 and self.reviewed_candidate_sha256 != (
            compute_publication_review_digest(self.model_dump(mode="python"))
        ):
            raise PublicationContractError("独立复核未绑定当前 publication 候选字节")
        if self.review_state == "rejected" and self.required:
            raise PublicationContractError("必需 publication 不能以 rejected 状态通过分类")
        if self.required:
            if not self.fetch_attempts:
                raise PublicationContractError("必需 publication 必须记录至少一次自动获取尝试")
            attempt_ids = tuple(item.attempt_id for item in self.fetch_attempts)
            if len(attempt_ids) != len(set(attempt_ids)):
                raise PublicationContractError("publication 获取尝试标识不能重复")
            if not self.affected_reports:
                raise PublicationContractError("必需 publication 必须标明受影响报告")
            acquired = any(item.result_class == "acquired" for item in self.fetch_attempts)
            if acquired != (self.acquisition_disposition == "acquired"):
                raise PublicationContractError("获取尝试与 publication 处置不一致")
            if not acquired and (
                len(self.fetch_attempts) < 2
                or len({item.route_family for item in self.fetch_attempts}) < 2
            ):
                raise PublicationContractError(
                    "未取得必需 publication 前必须完成两种不同策略的恢复获取"
                )
            if self.acquisition_disposition == "manual_required" and not self.blocking_fields:
                raise PublicationContractError("人工补件 publication 必须标明阻断字段")
            if self.acquisition_disposition == "manual_required" and (
                any(
                    not any(
                        field.startswith(f"{report.lower()}_") for report in self.affected_reports
                    )
                    for field in self.blocking_fields
                )
                or any(
                    not any(
                        field.startswith(f"{report.lower()}_") for field in self.blocking_fields
                    )
                    for report in self.affected_reports
                )
            ):
                raise PublicationContractError(
                    "人工补件阻断字段必须按每个受影响报告绑定正式 GateSpec 单元"
                )
            if self.acquisition_disposition == "excluded":
                raise PublicationContractError("必需 publication 不能标记为 excluded")
        elif self.fetch_attempts or self.acquisition_disposition != "excluded":
            raise PublicationContractError("排除的 review/ad hoc 不得触发获取或人工补件")
        return self

    @property
    def required(self) -> bool:
        return self.publication_class in REQUIRED_PUBLICATION_CLASSES

    @property
    def decision(self) -> PublicationDecision:
        return "required" if self.required else "excluded"

    @property
    def manual_supply_required(self) -> bool:
        return self.acquisition_disposition == "manual_required"


def classify_publication(payload: PublicationRecord | Mapping[str, object]) -> PublicationRecord:
    if isinstance(payload, PublicationRecord):
        return payload
    return PublicationRecord.model_validate(payload)


__all__ = [
    "ClassificationReviewState",
    "EXCLUDED_PUBLICATION_CLASSES",
    "PublicationAcquisitionDisposition",
    "PublicationClass",
    "PublicationContractError",
    "PublicationDecision",
    "PublicationFetchAttempt",
    "PublicationFetchRouteFamily",
    "PublicationFetchResult",
    "PublicationSearchReceipt",
    "PublicationSearchResult",
    "PublicationRecord",
    "REQUIRED_PUBLICATION_CLASSES",
    "RETRYABLE_FETCH_RESULTS",
    "classify_publication",
    "compute_publication_review_digest",
]
