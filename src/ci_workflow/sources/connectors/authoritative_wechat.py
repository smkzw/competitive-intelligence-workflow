from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id
from ci_workflow.sources.policy import (
    ClaimDomain,
    SourceAuthority,
    SourcePolicy,
)

APPROVED_WECHAT_ACCOUNT_LABELS = {
    "medical_cube_info": "医药魔方info",
    "pharnex_circle": "药融圈",
    "dxy_insight_database": "丁香园Insight数据库",
    "menet": "米内网",
    "china_drug_review": "中国药审",
}

_APPROVED_DIRECT_DOMAINS = frozenset(
    {
        ClaimDomain.EFFICACY_SAFETY_RESULTS,
        ClaimDomain.CHINA_DEVELOPMENT_REGULATORY_STATUS,
        ClaimDomain.COMPANY_RELATIONSHIPS_TRANSACTIONS,
        ClaimDomain.PATENTS_PROTECTION,
    }
)
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _required_text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("指定行业信息来源字段不能为空")
    return normalized


def _offset_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("指定行业信息来源日期时间必须包含明确时区")
    return parsed


class AuthoritativeWechatArticleVersion(BaseModel):
    """用户指定行业公众号文章的不可变版本与限定证据角色。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    account_label_zh: str
    source_record_id: str
    source_version_id: str
    external_record_id: str
    title: str
    article_role: Literal["authoritative_secondary_disclosure"] = (
        "authoritative_secondary_disclosure"
    )
    source_role_label_zh: Literal["指定行业信息来源"] = "指定行业信息来源"
    disclosure_maturity_label_zh: str = "行业信息文章披露"
    is_peer_reviewed_publication: bool = False
    direct_claim_domains: tuple[ClaimDomain, ...]
    authorities: dict[ClaimDomain, SourceAuthority]
    policy_id: str
    policy_version: str
    product_identity: str | None = None
    trial_identity: str | None = None
    event_identity: str | None = None
    published_at: datetime
    acquired_at: datetime
    content_snapshot: str
    content_sha256: str
    source_url: str
    locator: EvidenceLocator

    @field_validator(
        "source_id",
        "account_label_zh",
        "source_record_id",
        "source_version_id",
        "external_record_id",
        "title",
        "disclosure_maturity_label_zh",
        "policy_id",
        "policy_version",
        "source_url",
        "content_snapshot",
    )
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        return _required_text(value)

    @field_validator("product_identity", "trial_identity", "event_identity")
    @classmethod
    def _optional_identity_is_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _required_text(value)

    @field_validator("content_sha256")
    @classmethod
    def _content_sha_is_valid(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("指定行业信息来源摘要必须是小写 SHA-256")
        return value

    @field_validator("published_at", "acquired_at")
    @classmethod
    def _times_have_offsets(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("指定行业信息来源日期时间必须包含明确时区")
        return value

    @model_validator(mode="after")
    def _account_and_authority_are_limited(self) -> AuthoritativeWechatArticleVersion:
        if APPROVED_WECHAT_ACCOUNT_LABELS.get(self.source_id) != self.account_label_zh:
            raise ValueError("公众号不在用户指定行业信息来源清单中")
        if self.is_peer_reviewed_publication:
            raise ValueError("微信公众号文章不能标记为同行评议论文")
        if set(self.direct_claim_domains) != _APPROVED_DIRECT_DOMAINS:
            raise ValueError("指定行业信息来源的直接支持范围超出批准领域")
        if set(self.authorities) != set(ClaimDomain):
            raise ValueError("指定行业信息来源的声明范围不完整")
        for domain, authority in self.authorities.items():
            expected = (
                SourceAuthority.DIRECT
                if domain in _APPROVED_DIRECT_DOMAINS
                else SourceAuthority.CROSS_CHECK
            )
            if authority != expected:
                raise ValueError("指定行业信息来源的声明权限与批准范围不一致")
        if not all((self.product_identity, self.trial_identity, self.event_identity)):
            raise ValueError("公众号临床证据必须绑定产品、试验和披露事件身份")
        parts = urlsplit(self.source_url)
        if (
            parts.scheme != "https"
            or parts.hostname != "mp.weixin.qq.com"
            or not parts.path.startswith("/s/")
        ):
            raise ValueError("公众号证据必须使用微信公众平台文章链接")
        expected_digest = hashlib.sha256(
            self.content_snapshot.encode("utf-8")
        ).hexdigest()
        if self.content_sha256 != expected_digest:
            raise ValueError("公众号文章摘要与已保存正文不一致")
        paragraph = self.locator.paragraph
        if self.locator.url != self.source_url:
            raise ValueError("公众号定位链接必须与已保存文章链接一致")
        if self.locator.document_role != f"微信公众号：{self.account_label_zh}":
            raise ValueError("公众号定位必须标明对应账号")
        stored_paragraphs = {
            item.strip() for item in self.content_snapshot.splitlines() if item.strip()
        }
        if paragraph is None or paragraph.strip() not in stored_paragraphs:
            raise ValueError("公众号定位必须使用已保存正文中的完整段落")
        expected_record_id = stable_id(
            "authoritative-wechat-article", self.source_id, self.external_record_id
        )
        expected_version_id = stable_id(
            "authoritative-wechat-version", expected_record_id, self.content_sha256
        )
        if self.source_record_id != expected_record_id:
            raise ValueError("公众号文章标识与账号及文章编号不一致")
        if self.source_version_id != expected_version_id:
            raise ValueError("公众号文章版本与已保存正文不一致")
        return self

    def authority_for(self, claim_domain: ClaimDomain) -> SourceAuthority:
        return self.authorities[claim_domain]

    @classmethod
    def create(
        cls,
        *,
        policy: SourcePolicy,
        source_id: str,
        account_label_zh: str,
        external_record_id: str,
        title: str,
        published_at: str,
        acquired_at: str,
        source_url: str,
        content_snapshot: str,
        locator_label: str,
        product_identity: str | None = None,
        trial_identity: str | None = None,
        event_identity: str | None = None,
    ) -> AuthoritativeWechatArticleVersion:
        expected_label = APPROVED_WECHAT_ACCOUNT_LABELS.get(source_id)
        if expected_label is None or expected_label != account_label_zh:
            raise ValueError("公众号不在用户指定行业信息来源清单中")
        source_definition = policy.source(source_id)
        if (
            source_definition.label_zh != account_label_zh
            or not source_definition.authoritative_secondary
        ):
            raise ValueError("来源策略未把该公众号标记为指定行业信息来源")
        expected_authorities = {
            domain: (
                SourceAuthority.DIRECT
                if domain in _APPROVED_DIRECT_DOMAINS
                else SourceAuthority.CROSS_CHECK
            )
            for domain in ClaimDomain
        }
        if source_definition.authorities != expected_authorities:
            raise ValueError("来源策略中的公众号声明权限与批准范围不一致")
        external_record_id = _required_text(external_record_id)
        content_snapshot = _required_text(content_snapshot)
        content_sha256 = hashlib.sha256(content_snapshot.encode("utf-8")).hexdigest()
        source_record_id = stable_id(
            "authoritative-wechat-article", source_id, external_record_id
        )
        return cls(
            source_id=source_id,
            account_label_zh=account_label_zh,
            source_record_id=source_record_id,
            source_version_id=stable_id(
                "authoritative-wechat-version", source_record_id, content_sha256
            ),
            external_record_id=external_record_id,
            title=title,
            direct_claim_domains=tuple(
                domain for domain in ClaimDomain if domain in _APPROVED_DIRECT_DOMAINS
            ),
            authorities=expected_authorities,
            policy_id=policy.policy_id,
            policy_version=policy.version,
            product_identity=product_identity,
            trial_identity=trial_identity,
            event_identity=event_identity,
            published_at=_offset_datetime(published_at),
            acquired_at=_offset_datetime(acquired_at),
            content_snapshot=content_snapshot,
            content_sha256=content_sha256,
            source_url=source_url,
            locator=EvidenceLocator(
                document_role=f"微信公众号：{account_label_zh}",
                paragraph=locator_label,
                url=source_url,
            ),
        )
