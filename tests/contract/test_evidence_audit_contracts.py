from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError
from pydantic import ValidationError as PydanticValidationError

from ci_workflow.domain.evidence import EvidenceGap, SourceReceipt

ROOT = Path(__file__).resolve().parents[2]


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _receipt() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "receipt_id": "receipt_001",
        "route_id": "clinicaltrials-registry",
        "strategy_unit_id": "registry-nct-id",
        "entity_id": "drug_001",
        "gap_id": "gap_001",
        "claim_domain": "主要疗效",
        "query_or_identifier": "NCT01234567",
        "language": "en",
        "access_method": "公开登记页面",
        "attempt_index": 1,
        "started_at": "2026-08-11T10:00:00+08:00",
        "ended_at": "2026-08-11T10:00:05+08:00",
        "scheduled_backoff_ms": 0,
        "actual_backoff_ms": 0,
        "result_class": "content_acquired",
        "error_class": None,
        "completeness_checks": ["页面身份一致", "结果模块完整"],
        "alternative_paths": ["PubMed NCT 号检索", "申办方结果公告"],
        "source_version_id": "source-version-registry-001",
        "content_sha256": "a" * 64,
        "diagnostic_confidence": "high",
        "parent_attempt_id": None,
        "recovery_round": 0,
    }


def _gap() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "gap_id": "gap_001",
        "gate_spec_id": "B-主要疗效-核心结果",
        "object_type": "trial",
        "object_id": "trial_001",
        "field_id": "efficacy.primary_endpoint",
        "current_state": "not_publicly_disclosed",
        "required_context": "主要终点定义、时间点、治疗组与对照组结果",
        "candidate_sources": ["ClinicalTrials.gov", "主要结果论文", "申办方公告"],
        "completed_strategies": ["registry-nct-id", "pubmed-nct-id"],
        "information_gain_diff": [
            {"round": 1, "new_fields": [], "new_source_versions": []}
        ],
        "next_legal_action": "检查申办方结果公告；仍无披露则保持未公开状态",
    }


def _source_eligibility() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "source_eligibility_id": "source-eligibility-001",
        "route_id": "clinicaltrials-registry",
        "strategy_unit_id": "registry-nct-id",
        "entity_id": "trial-001",
        "gap_id": "gap_001",
        "claim_domain": "trial_identity_design_status",
        "applicability": "applicable",
        "required_by_policy": True,
        "rationale_zh": "全球基线路线，且该试验存在 NCT 标识符",
        "policy_id": "source-policy-v1",
        "policy_version": "1.0",
        "evidence_fragment_ids": ["fragment-route-applicability"],
        "decided_by": "source-planner-v1",
        "decided_at": "2026-08-11T10:00:00+08:00",
    }


def _source_version() -> dict[str, object]:
    locator = {
        "document_role": "临床试验登记结果",
        "field_path": "resultsSection",
        "heading": None,
        "page": None,
        "table": None,
        "row": None,
        "column": None,
        "paragraph": None,
        "url": None,
    }
    return {
        "schema_version": "1.0",
        "source_version_id": "source-version-registry-001",
        "source_id": "clinicaltrials_gov",
        "content_sha256": "a" * 64,
        "content_relative_path": f"evidence/raw/sha256/aa/{'a' * 64}.bin",
        "media_type": "application/json",
        "acquired_at": "2026-08-11T10:00:00+08:00",
        "acquired_locator": locator,
        "published_at": {
            "state": "reported",
            "value": "2026-08-01T00:00:00+08:00",
            "locator": locator,
        },
        "effective_at": {
            "state": "not_applicable",
            "value": None,
            "locator": locator,
        },
        "first_disclosed_at": {
            "state": "reported",
            "value": "2026-08-01T00:00:00+08:00",
            "locator": locator,
        },
        "created_at": "2026-08-11T10:00:00+08:00",
    }


def test_source_receipt_and_evidence_gap_require_v12_audit_fields() -> None:
    from ci_workflow.domain.evidence import SourceVersionRecord
    from ci_workflow.sources.planner import (
        RouteCompletion,
        RouteCompletionState,
        RouteProgress,
    )
    from ci_workflow.sources.policy import SourceEligibility
    from ci_workflow.sources.receipts import (
        AttemptResultClass,
        EvidenceAuditBundle,
        RouteAttemptResult,
    )

    receipt = _receipt()
    gap = _gap()
    source_eligibility = _source_eligibility()
    receipt_validator = _validator("source-receipt.schema.json")
    gap_validator = _validator("evidence-gap.schema.json")
    source_eligibility_validator = _validator("source-eligibility.schema.json")

    receipt_validator.validate(receipt)
    gap_validator.validate(gap)
    source_eligibility_validator.validate(source_eligibility)
    assert SourceReceipt.model_validate(receipt).content_sha256 == "a" * 64
    assert EvidenceGap.model_validate(gap).field_id == "efficacy.primary_endpoint"
    assert SourceEligibility.model_validate(source_eligibility).required_by_policy is True

    with pytest.raises(PydanticValidationError, match="正文路径必须与内容摘要一致"):
        SourceVersionRecord.model_validate(
            {**_source_version(), "content_relative_path": "not-content-addressed.bin"}
        )

    for required in receipt:
        invalid = deepcopy(receipt)
        invalid.pop(required)
        with pytest.raises(ValidationError):
            receipt_validator.validate(invalid)
        with pytest.raises(PydanticValidationError):
            SourceReceipt.model_validate(invalid)

    for required in gap:
        invalid = deepcopy(gap)
        invalid.pop(required)
        with pytest.raises(ValidationError):
            gap_validator.validate(invalid)
        with pytest.raises(PydanticValidationError):
            EvidenceGap.model_validate(invalid)

    for invalid_rounds in (
        [
            {"round": 1, "new_fields": [], "new_source_versions": []},
            {"round": 1, "new_fields": [], "new_source_versions": []},
        ],
        [
            {"round": 1, "new_fields": [], "new_source_versions": []},
            {"round": 3, "new_fields": [], "new_source_versions": []},
        ],
    ):
        with pytest.raises(PydanticValidationError, match="信息增益轮次必须从一开始连续递增"):
            EvidenceGap.model_validate(
                {**gap, "information_gain_diff": invalid_rounds}
            )

    for required in source_eligibility:
        invalid = deepcopy(source_eligibility)
        invalid.pop(required)
        with pytest.raises(ValidationError):
            source_eligibility_validator.validate(invalid)
        with pytest.raises(PydanticValidationError):
            SourceEligibility.model_validate(invalid)

    with pytest.raises(ValidationError):
        receipt_validator.validate({**receipt, "password": "secret"})
    with pytest.raises(PydanticValidationError):
        SourceReceipt.model_validate({**receipt, "password": "secret"})

    failed_route = {
        **receipt,
        "result_class": "network_error",
        "error_class": "network_timeout",
        "source_version_id": None,
        "content_sha256": None,
    }
    receipt_validator.validate(failed_route)
    SourceReceipt.model_validate(failed_route)

    for invalid in (
        {**receipt, "content_sha256": None},
        {**failed_route, "error_class": None},
    ):
        with pytest.raises(ValidationError):
            receipt_validator.validate(invalid)
        with pytest.raises(PydanticValidationError):
            SourceReceipt.model_validate(invalid)

    audit_bundle = EvidenceAuditBundle(
        source_receipts=(SourceReceipt.model_validate(receipt),),
        source_versions=(SourceVersionRecord.model_validate(_source_version()),),
        source_eligibilities=(SourceEligibility.model_validate(source_eligibility),),
        evidence_gap=EvidenceGap.model_validate(gap),
    )
    with pytest.raises(PydanticValidationError, match="同一来源版本注册表"):
        EvidenceAuditBundle(
            source_receipts=(SourceReceipt.model_validate(receipt),),
            source_versions=(
                SourceVersionRecord.model_validate(
                    {
                        **_source_version(),
                        "content_sha256": "b" * 64,
                        "content_relative_path": (
                            f"evidence/raw/sha256/bb/{'b' * 64}.bin"
                        ),
                    }
                ),
            ),
            source_eligibilities=(
                SourceEligibility.model_validate(source_eligibility),
            ),
            evidence_gap=EvidenceGap.model_validate(gap),
        )
    completion = RouteCompletion(
        state=RouteCompletionState.COMPLETED,
        rationale_zh="已完成全部适用策略并核对完整审计包",
        completed_strategy_unit_ids=("registry-nct-id",),
    )
    route = RouteProgress(
        route_id="clinicaltrials-registry",
        attempts=(
            RouteAttemptResult(
                attempt_id=receipt["receipt_id"],
                strategy_unit_id=receipt["strategy_unit_id"],
                entity_id=receipt["entity_id"],
                gap_id=receipt["gap_id"],
                claim_domain=receipt["claim_domain"],
                result_class=AttemptResultClass.CONTENT_ACQUIRED,
                detail_zh="已取得并保存登记原文",
            ),
        ),
    )
    completed_route = route.complete(completion, audit_bundle=audit_bundle)
    assert completed_route.is_complete is True

    second_required = SourceEligibility.model_validate(
        {
            **source_eligibility,
            "source_eligibility_id": "source-eligibility-002",
            "strategy_unit_id": "registry-secondary-required",
        }
    )
    with pytest.raises(ValueError, match="遗漏政策必查来源单元"):
        route.complete(
            completion,
            audit_bundle=EvidenceAuditBundle(
                source_receipts=(SourceReceipt.model_validate(receipt),),
                source_versions=(
                    SourceVersionRecord.model_validate(_source_version()),
                ),
                source_eligibilities=(
                    SourceEligibility.model_validate(source_eligibility),
                    second_required,
                ),
                evidence_gap=EvidenceGap.model_validate(gap),
            ),
        )

    with pytest.raises(TypeError):
        cast(Any, route.complete)(completion)

    not_applicable_eligibility = SourceEligibility.model_validate(
        {**source_eligibility, "applicability": "not_applicable"}
    )
    not_applicable_route = RouteProgress(route_id="clinicaltrials-registry")
    not_applicable_bundle = EvidenceAuditBundle(
        source_eligibilities=(not_applicable_eligibility,),
        evidence_gap=EvidenceGap.model_validate(gap),
    )
    assert not_applicable_route.complete(
        completion.model_copy(
            update={"state": RouteCompletionState.NOT_APPLICABLE}
        ),
        audit_bundle=not_applicable_bundle,
    ).is_complete
    second_not_applicable = second_required.model_copy(
        update={"applicability": "not_applicable"}
    )
    with pytest.raises(ValueError, match="路线终态遗漏政策必查来源单元"):
        not_applicable_route.complete(
            completion.model_copy(
                update={"state": RouteCompletionState.NOT_APPLICABLE}
            ),
            audit_bundle=EvidenceAuditBundle(
                source_eligibilities=(
                    not_applicable_eligibility,
                    second_not_applicable,
                ),
                evidence_gap=EvidenceGap.model_validate(gap),
            ),
        )

    access_blocked_eligibility = SourceEligibility.model_validate(
        {**source_eligibility, "applicability": "access_blocked"}
    )
    with pytest.raises(ValueError, match="访问阻断路线不能使用成功或未找到回执"):
        route.complete(
            completion.model_copy(
                update={"state": RouteCompletionState.ACCESS_BLOCKED}
            ),
            audit_bundle=EvidenceAuditBundle(
                source_receipts=(SourceReceipt.model_validate(receipt),),
                source_versions=(
                    SourceVersionRecord.model_validate(_source_version()),
                ),
                source_eligibilities=(access_blocked_eligibility,),
                evidence_gap=EvidenceGap.model_validate(gap),
            ),
        )

    blocked_bundle = EvidenceAuditBundle(
        source_receipts=(SourceReceipt.model_validate(failed_route),),
        source_eligibilities=(access_blocked_eligibility,),
        evidence_gap=EvidenceGap.model_validate(gap),
    )
    blocked_route = RouteProgress(
        route_id="clinicaltrials-registry",
        attempts=(
            RouteAttemptResult(
                attempt_id=failed_route["receipt_id"],
                strategy_unit_id=failed_route["strategy_unit_id"],
                entity_id=failed_route["entity_id"],
                gap_id=failed_route["gap_id"],
                claim_domain=failed_route["claim_domain"],
                result_class=AttemptResultClass.NETWORK_ERROR,
                detail_zh="网络连接失败",
            ),
        ),
    )
    assert blocked_route.complete(
        completion.model_copy(
            update={"state": RouteCompletionState.ACCESS_BLOCKED}
        ),
        audit_bundle=blocked_bundle,
    ).is_complete
    mismatched_attempt_route = RouteProgress(
        route_id="clinicaltrials-registry",
        attempts=(
            RouteAttemptResult(
                attempt_id=failed_route["receipt_id"],
                strategy_unit_id=failed_route["strategy_unit_id"],
                entity_id=failed_route["entity_id"],
                gap_id=failed_route["gap_id"],
                claim_domain=failed_route["claim_domain"],
                result_class=AttemptResultClass.CONTENT_ACQUIRED,
                detail_zh="错误地声称已取得内容",
            ),
        ),
    )
    with pytest.raises(ValueError, match="路线尝试内容与来源审计回执不一致"):
        mismatched_attempt_route.complete(
            completion.model_copy(
                update={"state": RouteCompletionState.ACCESS_BLOCKED}
            ),
            audit_bundle=blocked_bundle,
        )
    second_access_blocked = second_required.model_copy(
        update={"applicability": "access_blocked"}
    )
    with pytest.raises(ValueError, match="路线终态遗漏政策必查来源单元"):
        blocked_route.complete(
            completion.model_copy(
                update={"state": RouteCompletionState.ACCESS_BLOCKED}
            ),
            audit_bundle=EvidenceAuditBundle(
                source_receipts=(SourceReceipt.model_validate(failed_route),),
                source_eligibilities=(
                    access_blocked_eligibility,
                    second_access_blocked,
                ),
                evidence_gap=EvidenceGap.model_validate(gap),
            ),
        )


@pytest.mark.parametrize(
    "field,value",
    (
        ("attempt_index", 0),
        ("scheduled_backoff_ms", -1),
        ("actual_backoff_ms", -1),
        ("content_sha256", "not-a-digest"),
        ("diagnostic_confidence", "certain"),
        ("started_at", "2026-08-11T10:00:00"),
        ("alternative_paths", []),
    ),
)
def test_receipt_rejects_incomplete_or_ambiguous_audit_values(
    field: str, value: object
) -> None:
    payload = {**_receipt(), field: value}
    with pytest.raises(ValidationError):
        _validator("source-receipt.schema.json").validate(payload)
    with pytest.raises(PydanticValidationError):
        SourceReceipt.model_validate(payload)
