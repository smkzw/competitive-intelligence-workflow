from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]


def test_source_domains_and_claim_authority_match_v12() -> None:
    from ci_workflow.sources.policy import ClaimDomain, SourceAuthority, SourcePolicy

    policy = SourcePolicy.from_yaml(
        ROOT / "policies" / "sources" / "source-policy-v1.yaml"
    )

    assert set(policy.claim_domains) == set(ClaimDomain)
    assert policy.authority_for(
        "clinicaltrials_gov", ClaimDomain.TRIAL_IDENTITY_DESIGN_STATUS
    ) is SourceAuthority.DIRECT
    assert policy.authority_for(
        "clinicaltrials_gov", ClaimDomain.EFFICACY_SAFETY_RESULTS
    ) is SourceAuthority.DIRECT
    assert policy.authority_for(
        "pubmed", ClaimDomain.TRIAL_IDENTITY_DESIGN_STATUS
    ) is SourceAuthority.CROSS_CHECK
    assert policy.authority_for(
        "pubmed", ClaimDomain.EFFICACY_SAFETY_RESULTS
    ) is SourceAuthority.DIRECT
    assert policy.authority_for(
        "company_disclosure", ClaimDomain.TRIAL_IDENTITY_DESIGN_STATUS
    ) is SourceAuthority.CROSS_CHECK
    assert policy.authority_for(
        "conference_disclosure", ClaimDomain.EFFICACY_SAFETY_RESULTS
    ) is SourceAuthority.CROSS_CHECK

    for source_id in ("cde", "chinadrugtrials", "dxy_drug_assistant"):
        assert policy.source(source_id).required_for_china is True
    assert policy.source("clinicaltrials_gov").required_global_baseline is True

    authorized_cn_sources = {
        "medical_cube_info",
        "pharnex_circle",
        "dxy_insight_database",
        "menet",
        "china_drug_review",
    }
    authorized_cn_domains = {
        ClaimDomain.EFFICACY_SAFETY_RESULTS,
        ClaimDomain.CHINA_DEVELOPMENT_REGULATORY_STATUS,
        ClaimDomain.COMPANY_RELATIONSHIPS_TRANSACTIONS,
        ClaimDomain.PATENTS_PROTECTION,
    }
    for source_id in authorized_cn_sources:
        source = policy.source(source_id)
        assert source.authoritative_secondary is True
        assert {
            domain
            for domain in ClaimDomain
            if policy.authority_for(source_id, domain) is SourceAuthority.DIRECT
        } == authorized_cn_domains

    assert policy.authority_for(
        "medical_cube_info", ClaimDomain.TRIAL_IDENTITY_DESIGN_STATUS
    ) is SourceAuthority.CROSS_CHECK
    assert policy.authority_for(
        "conference_disclosure", ClaimDomain.PATENTS_PROTECTION
    ) is SourceAuthority.LEAD_ONLY


def test_route_attempt_results_are_exact_and_never_fact_states() -> None:
    from ci_workflow.sources.receipts import AttemptResultClass, RouteAttemptResult

    assert {item.value for item in AttemptResultClass} == {
        "content_acquired",
        "not_found",
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
    accepted = RouteAttemptResult(
        attempt_id="attempt-001",
        strategy_unit_id="registry-nct-id",
        entity_id="trial-001",
        gap_id="gap-trial-identity",
        claim_domain="trial_identity_design_status",
        result_class=AttemptResultClass.NOT_FOUND,
        detail_zh="在完成本次精确查询后未找到匹配记录",
    )
    assert accepted.result_class is AttemptResultClass.NOT_FOUND

    for fact_state in (
        "reported",
        "not_reported",
        "not_publicly_disclosed",
        "conflicting",
        "unresolved_due_to_route",
    ):
        with pytest.raises(ValidationError):
            RouteAttemptResult.model_validate(
                {
                    "attempt_id": "attempt-invalid",
                    "result_class": fact_state,
                    "detail_zh": "事实状态不能伪装成路线尝试结果",
                }
            )
