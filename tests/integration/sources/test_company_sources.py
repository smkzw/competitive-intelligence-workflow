from __future__ import annotations

import pytest


def test_company_and_topline_sources_keep_disclosure_maturity() -> None:
    from ci_workflow.sources.connectors.company import CompanyDisclosureVersion

    filing = CompanyDisclosureVersion.create(
        disclosure_kind="company_regulatory_filing",
        issuer="测试生物医药有限公司",
        external_record_id="HKEX-2026-001",
        title="临床试验进展公告",
        product_name="测试创新药",
        trial_identifier="CTR20260001",
        published_at="2026-07-01T08:00:00+08:00",
        acquired_at="2026-08-11T09:00:00+08:00",
        content_sha256="7" * 64,
        source_url="https://www.hkexnews.hk/example/2026-001.pdf",
        locator_label="第 3 页：临床开发进展",
    )
    topline = CompanyDisclosureVersion.create(
        disclosure_kind="topline_results",
        issuer="测试生物医药有限公司",
        external_record_id="NEWS-2026-008",
        title="III 期研究达到主要终点",
        product_name="测试创新药",
        trial_identifier="NCT01234567",
        published_at="2026-07-15T08:00:00+08:00",
        acquired_at="2026-08-11T09:00:00+08:00",
        content_sha256="8" * 64,
        source_url="https://example-pharma.com/news/2026-008",
        locator_label="疗效结果第 2 段",
    )
    conference = CompanyDisclosureVersion.create(
        disclosure_kind="conference_presentation",
        issuer="测试生物医药有限公司",
        external_record_id="EAACI-2026-P101",
        title="测试创新药 III 期研究结果",
        product_name="测试创新药",
        trial_identifier="NCT01234567",
        published_at="2026-06-20T08:00:00+02:00",
        acquired_at="2026-08-11T09:00:00+08:00",
        content_sha256="9" * 64,
        source_url="https://eaaci.org/example/P101.pdf",
        locator_label="图 2：第 24 周 NPS 变化",
    )
    pipeline = CompanyDisclosureVersion.create(
        disclosure_kind="pipeline_summary",
        issuer="测试生物医药有限公司",
        external_record_id="PIPELINE-2026H1",
        title="在研管线概览",
        product_name="测试创新药",
        trial_identifier=None,
        published_at="2026-06-30T08:00:00+08:00",
        acquired_at="2026-08-11T09:00:00+08:00",
        content_sha256="a" * 64,
        source_url="https://example-pharma.com/pipeline",
        locator_label="免疫管线第 2 行",
    )

    assert filing.disclosure_maturity_label_zh == "企业法定披露"
    assert topline.disclosure_maturity_label_zh == "主要结果初步披露"
    assert conference.disclosure_maturity_label_zh == "学术会议披露"
    assert pipeline.disclosure_maturity_label_zh == "企业管线概览"
    assert filing.may_support_company_fact is True
    assert topline.may_support_numeric_result is True
    assert conference.may_support_numeric_result is True
    assert pipeline.may_support_numeric_result is False
    assert all(
        item.is_trial_registry_result is False
        for item in (filing, topline, conference, pipeline)
    )
    assert all(
        item.is_peer_reviewed_publication is False
        for item in (filing, topline, conference, pipeline)
    )
    assert topline.locator.paragraph == "疗效结果第 2 段"
    assert topline.source_record_id != conference.source_record_id

    with pytest.raises(ValueError, match="企业或会议披露不能标记为同行评议论文"):
        CompanyDisclosureVersion.model_validate(
            {
                **topline.model_dump(),
                "is_peer_reviewed_publication": True,
            }
        )
