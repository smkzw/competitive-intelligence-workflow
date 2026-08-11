from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id

DisclosureKind = Literal[
    "company_regulatory_filing",
    "company_press_release",
    "topline_results",
    "conference_abstract",
    "conference_presentation",
    "pipeline_summary",
]

_SHA256 = re.compile(r"[0-9a-f]{64}")
_DISCLOSURE_PROPERTIES: dict[DisclosureKind, tuple[str, bool, bool]] = {
    "company_regulatory_filing": ("企业法定披露", True, True),
    "company_press_release": ("企业新闻披露", True, True),
    "topline_results": ("主要结果初步披露", True, True),
    "conference_abstract": ("学术会议摘要", False, True),
    "conference_presentation": ("学术会议披露", False, True),
    "pipeline_summary": ("企业管线概览", True, False),
}


def _required_text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("企业披露字段不能为空")
    return normalized


def _offset_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("企业披露日期时间必须包含明确时区")
    return parsed


class CompanyDisclosureVersion(BaseModel):
    """企业、topline 与会议披露的不可变版本及其证据成熟度。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    disclosure_kind: DisclosureKind
    source_record_id: str
    source_version_id: str
    issuer: str
    external_record_id: str
    title: str
    product_name: str
    trial_identifier: str | None
    disclosure_maturity_label_zh: str
    may_support_company_fact: bool
    may_support_numeric_result: bool
    is_trial_registry_result: bool = False
    is_peer_reviewed_publication: bool = False
    published_at: datetime
    acquired_at: datetime
    content_sha256: str
    source_url: str
    locator: EvidenceLocator

    @field_validator(
        "source_record_id",
        "source_version_id",
        "issuer",
        "external_record_id",
        "title",
        "product_name",
        "disclosure_maturity_label_zh",
        "source_url",
    )
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _required_text(value)

    @field_validator("trial_identifier")
    @classmethod
    def _optional_trial_identifier_is_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _required_text(value)

    @field_validator("content_sha256")
    @classmethod
    def _content_sha256_is_valid(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("企业披露摘要必须是小写 SHA-256")
        return value

    @field_validator("published_at", "acquired_at")
    @classmethod
    def _times_have_offsets(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("企业披露日期时间必须包含明确时区")
        return value

    @model_validator(mode="after")
    def _maturity_matches_disclosure_kind(self) -> CompanyDisclosureVersion:
        label, supports_company, supports_numbers = _DISCLOSURE_PROPERTIES[
            self.disclosure_kind
        ]
        if self.is_peer_reviewed_publication:
            raise ValueError("企业或会议披露不能标记为同行评议论文")
        if self.is_trial_registry_result:
            raise ValueError("企业或会议披露不能标记为试验登记结果")
        if (
            self.disclosure_maturity_label_zh != label
            or self.may_support_company_fact != supports_company
            or self.may_support_numeric_result != supports_numbers
        ):
            raise ValueError("企业披露成熟度与披露类型不一致")
        return self

    @classmethod
    def create(
        cls,
        *,
        disclosure_kind: DisclosureKind,
        issuer: str,
        external_record_id: str,
        title: str,
        product_name: str,
        trial_identifier: str | None,
        published_at: str,
        acquired_at: str,
        content_sha256: str,
        source_url: str,
        locator_label: str,
    ) -> CompanyDisclosureVersion:
        label, supports_company, supports_numbers = _DISCLOSURE_PROPERTIES[
            disclosure_kind
        ]
        issuer = _required_text(issuer)
        external_record_id = _required_text(external_record_id)
        source_record_id = stable_id(
            "company-disclosure", disclosure_kind, issuer, external_record_id
        )
        return cls(
            disclosure_kind=disclosure_kind,
            source_record_id=source_record_id,
            source_version_id=stable_id(
                "company-disclosure-version", source_record_id, content_sha256
            ),
            issuer=issuer,
            external_record_id=external_record_id,
            title=title,
            product_name=product_name,
            trial_identifier=trial_identifier,
            disclosure_maturity_label_zh=label,
            may_support_company_fact=supports_company,
            may_support_numeric_result=supports_numbers,
            published_at=_offset_datetime(published_at),
            acquired_at=_offset_datetime(acquired_at),
            content_sha256=content_sha256,
            source_url=source_url,
            locator=EvidenceLocator(
                document_role=label,
                paragraph=locator_label,
                url=source_url,
            ),
        )
