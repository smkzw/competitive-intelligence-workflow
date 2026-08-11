from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

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
        "result_class": "content_acquired",
        "error_class": None,
        "completeness_checks": ["页面身份一致", "结果模块完整"],
        "alternative_paths": ["PubMed NCT 号检索", "申办方结果公告"],
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


def test_source_receipt_and_evidence_gap_require_v12_audit_fields() -> None:
    receipt = _receipt()
    gap = _gap()
    receipt_validator = _validator("source-receipt.schema.json")
    gap_validator = _validator("evidence-gap.schema.json")

    receipt_validator.validate(receipt)
    gap_validator.validate(gap)
    assert SourceReceipt.model_validate(receipt).content_sha256 == "a" * 64
    assert EvidenceGap.model_validate(gap).field_id == "efficacy.primary_endpoint"

    for required in receipt:
        if required == "error_class" or required == "parent_attempt_id":
            continue
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

    with pytest.raises(ValidationError):
        receipt_validator.validate({**receipt, "password": "secret"})
    with pytest.raises(PydanticValidationError):
        SourceReceipt.model_validate({**receipt, "password": "secret"})

    failed_route = {
        **receipt,
        "result_class": "technical_failure",
        "error_class": "network_timeout",
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


@pytest.mark.parametrize(
    "field,value",
    (
        ("attempt_index", 0),
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
