from __future__ import annotations

from pathlib import Path

import pytest


def test_named_wechat_accounts_are_authoritative_only_for_approved_claim_domains() -> None:
    from ci_workflow.sources.connectors.authoritative_wechat import (
        APPROVED_WECHAT_ACCOUNT_LABELS,
        AuthoritativeWechatArticleVersion,
    )
    from ci_workflow.sources.policy import ClaimDomain, SourceAuthority, SourcePolicy

    policy = SourcePolicy.from_yaml(
        Path("policies/sources/source-policy-v1.yaml")
    )
    expected_accounts = {
        "medical_cube_info": "医药魔方info",
        "pharnex_circle": "药融圈",
        "dxy_insight_database": "丁香园Insight数据库",
        "menet": "米内网",
        "china_drug_review": "中国药审",
    }
    direct_domains = {
        ClaimDomain.EFFICACY_SAFETY_RESULTS,
        ClaimDomain.CHINA_DEVELOPMENT_REGULATORY_STATUS,
        ClaimDomain.COMPANY_RELATIONSHIPS_TRANSACTIONS,
        ClaimDomain.PATENTS_PROTECTION,
    }

    assert expected_accounts == APPROVED_WECHAT_ACCOUNT_LABELS
    for source_id, account_label in expected_accounts.items():
        article = AuthoritativeWechatArticleVersion.create(
            policy=policy,
            source_id=source_id,
            account_label_zh=account_label,
            external_record_id=f"{source_id}-20260801",
            title="测试创新药最新临床与国内开发进展",
            product_identity="测试创新药",
            trial_identity="NCT01234567",
            event_identity="第 24 周主要结果",
            published_at="2026-08-01T08:00:00+08:00",
            acquired_at="2026-08-11T09:00:00+08:00",
            source_url=f"https://mp.weixin.qq.com/s/{source_id}",
            content_snapshot="测试创新药在 NCT01234567 的第 24 周主要结果已披露。",
            locator_label="测试创新药在 NCT01234567 的第 24 周主要结果已披露。",
        )
        assert article.account_label_zh == account_label
        assert set(article.direct_claim_domains) == direct_domains
        assert article.source_role_label_zh == "指定行业信息来源"
        for domain in ClaimDomain:
            expected = (
                SourceAuthority.DIRECT
                if domain in direct_domains
                else SourceAuthority.CROSS_CHECK
            )
            assert article.authority_for(domain) == expected


def test_wechat_numbers_never_claim_peer_reviewed_publication_status() -> None:
    from ci_workflow.sources.connectors.authoritative_wechat import (
        AuthoritativeWechatArticleVersion,
    )
    from ci_workflow.sources.policy import SourcePolicy

    policy = SourcePolicy.from_yaml(
        Path("policies/sources/source-policy-v1.yaml")
    )
    article = AuthoritativeWechatArticleVersion.create(
        policy=policy,
        source_id="medical_cube_info",
        account_label_zh="医药魔方info",
        external_record_id="medical-cube-20260801",
        title="测试创新药 III 期主要结果",
        product_identity="测试创新药",
        trial_identity="NCT01234567",
        event_identity="第 24 周主要终点结果",
        published_at="2026-08-01T08:00:00+08:00",
        acquired_at="2026-08-11T09:00:00+08:00",
        source_url="https://mp.weixin.qq.com/s/medical-cube-20260801",
        content_snapshot="结果部分第 2 段：试验组 -2.1，安慰剂组 -0.8",
        locator_label="结果部分第 2 段：试验组 -2.1，安慰剂组 -0.8",
    )

    assert article.article_role == "authoritative_secondary_disclosure"
    assert article.source_role_label_zh == "指定行业信息来源"
    assert article.disclosure_maturity_label_zh == "行业信息文章披露"
    assert article.is_peer_reviewed_publication is False
    assert article.product_identity == "测试创新药"
    assert article.trial_identity == "NCT01234567"
    assert article.event_identity == "第 24 周主要终点结果"
    assert article.locator.paragraph is not None
    assert "试验组 -2.1" in article.locator.paragraph

    with pytest.raises(ValueError, match="微信公众号文章不能标记为同行评议论文"):
        AuthoritativeWechatArticleVersion.model_validate(
            {
                **article.model_dump(),
                "is_peer_reviewed_publication": True,
            }
        )


def test_wechat_article_requires_real_snapshot_url_and_clinical_identity() -> None:
    from ci_workflow.sources.connectors.authoritative_wechat import (
        AuthoritativeWechatArticleVersion,
    )
    from ci_workflow.sources.policy import SourcePolicy

    policy = SourcePolicy.from_yaml(Path("policies/sources/source-policy-v1.yaml"))
    base = {
        "policy": policy,
        "source_id": "medical_cube_info",
        "account_label_zh": "医药魔方info",
        "external_record_id": "medical-cube-20260802",
        "title": "测试创新药主要结果",
        "published_at": "2026-08-01T08:00:00+08:00",
        "acquired_at": "2026-08-11T09:00:00+08:00",
        "source_url": "https://mp.weixin.qq.com/s/medical-cube-20260802",
        "content_snapshot": "测试创新药 NCT01234567 第 24 周主要结果为 -2.1。",
        "locator_label": "测试创新药 NCT01234567 第 24 周主要结果为 -2.1。",
        "product_identity": "测试创新药",
        "trial_identity": "NCT01234567",
        "event_identity": "第 24 周主要结果",
    }
    article = AuthoritativeWechatArticleVersion.create(**base)
    assert article.content_sha256
    assert article.content_snapshot.startswith("测试创新药")

    for missing_identity in ("product_identity", "trial_identity", "event_identity"):
        with pytest.raises(ValueError, match="产品、试验和披露事件身份"):
            AuthoritativeWechatArticleVersion.create(
                **{**base, missing_identity: None}
            )

    with pytest.raises(ValueError, match="微信公众平台文章链接"):
        AuthoritativeWechatArticleVersion.create(
            **{**base, "source_url": "https://example.invalid/copied-article"}
        )
    with pytest.raises(ValueError, match="完整段落"):
        AuthoritativeWechatArticleVersion.create(
            **{**base, "locator_label": "正文中不存在的数字 999"}
        )
    with pytest.raises(ValueError, match="定位链接必须与已保存文章链接一致"):
        AuthoritativeWechatArticleVersion.model_validate(
            {
                **article.model_dump(),
                "locator": {
                    **article.locator.model_dump(),
                    "url": "https://evil.invalid/other",
                },
            }
        )
    with pytest.raises(ValueError, match="完整段落"):
        AuthoritativeWechatArticleVersion.model_validate(
            {
                **article.model_dump(),
                "locator": {
                    **article.locator.model_dump(),
                    "paragraph": "测试",
                },
            }
        )
