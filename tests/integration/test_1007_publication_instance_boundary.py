"""Copied typed publication/package instances must fail closed at public boundaries.

Root-cause family for ci-1007: ``model_copy(update=...)`` skips construction-time
validation, so an already-instantiated ``PublicationRecord``, a nested
``PublicationFetchAttempt``, or a whole ``ResearchPackage`` could reach the
public classifier, the package closure boundary, and the snapshot manual gate
carrying forged content.

All fixtures below are synthetic contract-shaped placeholders; they are not
evidence for any real trial, product, publication, or retrieved source bytes.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import pytest

from ci_workflow.application.publication_manual_gate import (
    PublicationManualGateError,
    materialize_publication_manual_gate,
)
from ci_workflow.domain.publication import PublicationRecord
from ci_workflow.domain.research_package import (
    ResearchPackage,
    ResearchPackageValidationError,
    compute_universe_review_digest,
    validate_research_package,
)
from ci_workflow.ingestion.publication_gate import classify_publication

_SNAPSHOT_ID = "snapshot-syn-1"
_RETRIEVED_AT = "2026-09-04T10:00:00+00:00"

_RECORD_FORGERY_CASES = (
    ("stale-review", "复核"),
    ("dropped-fetch-attempts", "获取尝试"),
    ("dropped-affected-reports", "受影响报告"),
    ("forged-nested-attempt", "诊断"),
)

_PACKAGE_FORGERY_CASES = (
    "stale-review",
    "dropped-fetch-attempts",
    "dropped-affected-reports",
    "forged-nested-attempt",
    "empty-reports",
    "forged-closure-digest",
)


def _synthetic_record_payload() -> dict[str, object]:
    return {
        "publication_id": "pub-syn-1",
        "source_id": "src-pub-syn-1",
        "product_id": "product-syn-1",
        "linked_trial_ids": ["trial-syn-1"],
        "registry_identifiers": ["NCT00000001"],
        "title": "合成主要结果论文",
        "source_url": "https://doi.org/10.1000/example",
        "publication_class": "primary_result",
        "model_suggestion": "primary_result",
        "classification_reason": "合成夹具：登记关联的主要结果论文",
        "producer_id": "publication-worker-syn-1",
        "producer_context": "publication-context-syn-1",
        "fetch_attempts": [
            {
                "attempt_id": "fetch-syn-1",
                "strategy_id": "publisher-full-text",
                "route_family": "publisher",
                "attempted_at": _RETRIEVED_AT,
                "result_class": "access_or_permission_blocked",
                "diagnostic": "合成夹具：出版社要求机构权限",
            },
            {
                "attempt_id": "fetch-syn-2",
                "strategy_id": "repository-full-text",
                "route_family": "open_repository",
                "attempted_at": "2026-09-04T10:05:00+00:00",
                "result_class": "searched_no_evidence",
                "diagnostic": "合成夹具：开放仓储未找到全文",
            },
        ],
        "acquisition_disposition": "manual_required",
        "blocking_fields": ["b_core_efficacy_endpoint"],
        "affected_reports": ["B"],
    }


def _expansion_receipts() -> list[dict[str, object]]:
    receipts: list[dict[str, object]] = []
    for round_id in ("1", "2"):
        for dimension in ("alias", "target", "company", "trial"):
            receipts.append(
                {
                    "receipt_id": f"exp-{dimension}-r{round_id}",
                    "dimension": dimension,
                    "round_id": round_id,
                    "strategy_id": f"{dimension}-reverse-search-{round_id}",
                    "route_ids": ["global-registry-syn"],
                    "attempt_ids": [f"exp-attempt-{dimension}-{round_id}"],
                    "input_entity_ids": ["product-syn-1"],
                    "discovered_entity_ids": [],
                    "source_ids": [],
                    "query_sha256": hashlib.sha256(
                        f"exp-{dimension}-{round_id}".encode()
                    ).hexdigest(),
                    "result_class": "searched_no_evidence",
                    "diagnostic": "合成夹具：本轮无新增实体",
                }
            )
    return receipts


def _synthetic_package_payload() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "1.3",
        "package_id": "rp-syn-1",
        "contract_identity": {
            "project_id": "project-syn-1",
            "indication": "合成适应症",
            "contract_version": "1.3",
        },
        "reports": ["B"],
        "data_cutoff": "2026-09-04",
        "source_policy_id": "source-policy-syn-1",
        "source_policy_version": "1.0",
        "producer_id": "research-worker-syn-1",
        "producer_context": "research-context-syn-1",
        "entities": [
            {
                "entity_id": "product-syn-1",
                "entity_type": "product",
                "name": "合成产品",
                "aliases": ["合成别名"],
                "identity_status": "resolved",
                "disposition": "included",
                "ontology_rule_id": "innovation-therapy-v1",
                "identity_evidence_ids": ["src-syn-1"],
            },
            {
                "entity_id": "trial-syn-1",
                "entity_type": "trial",
                "name": "NCT00000001",
                "identity_status": "resolved",
                "disposition": "included",
                "ontology_rule_id": "innovation-therapy-v1",
                "identity_evidence_ids": ["src-syn-1"],
            },
        ],
        "sources": [
            {
                "source_id": "src-syn-1",
                "title": "合成登记结果",
                "source_role": "official_registry",
                "source_type": "registry",
                "url": "https://clinicaltrials.gov/study/NCT00000001",
                "locator": "Results, Table 1",
                "content_sha256": "a" * 64,
                "retrieved_at": _RETRIEVED_AT,
                "access_state": "available",
                "publication_classification": "not_applicable",
            },
            {
                "source_id": "src-pub-syn-1",
                "title": "合成主要结果论文",
                "source_role": "primary_publication",
                "source_type": "publication",
                "url": "https://doi.org/10.1000/example",
                "locator": "full text",
                "content_sha256": None,
                "retrieved_at": _RETRIEVED_AT,
                "linked_trial_ids": ["trial-syn-1"],
                "publication_classification": "primary_result",
                "access_state": "not_accessible",
            },
        ],
        "publication_records": [_synthetic_record_payload()],
        "publication_search_receipts": [
            {
                "search_id": "publication-search-syn-1",
                "trial_id": "trial-syn-1",
                "registry_identifiers": ["NCT00000001"],
                "route_families": ["registry_attachment", "bibliographic_index"],
                "attempt_ids": ["search-attempt-syn-1", "search-attempt-syn-2"],
                "query_sha256": "b" * 64,
                "result": "publications_classified",
                "discovered_publication_ids": ["pub-syn-1"],
            }
        ],
        "routes": [
            {
                "route_id": "global-registry-syn",
                "region": "global",
                "strategy_id": "registry-by-indication-syn",
                "result_class": "completed",
                "attempt_ids": ["route-attempt-syn-1"],
                "source_ids": ["src-syn-1"],
            },
            {
                "route_id": "china-registry-syn",
                "region": "china",
                "strategy_id": "registry-by-indication-cn-syn",
                "result_class": "completed",
                "attempt_ids": ["route-attempt-syn-2"],
                "source_ids": ["src-syn-1"],
            },
        ],
        "expansion_receipts": _expansion_receipts(),
        "closure": {
            "review_digest_version": "2",
            "closed": True,
            "global_route_ids": ["global-registry-syn"],
            "china_route_ids": ["china-registry-syn"],
            "alias_expansion_receipts": ["exp-alias-r1", "exp-alias-r2"],
            "target_expansion_receipts": ["exp-target-r1", "exp-target-r2"],
            "company_expansion_receipts": ["exp-company-r1", "exp-company-r2"],
            "trial_expansion_receipts": ["exp-trial-r1", "exp-trial-r2"],
            "independent_review_id": "universe-review-syn-1",
            "independent_reviewer_id": "independent-reviewer-syn-1",
            "independent_context": "clean-context-syn-1",
            "candidate_entity_ids": [],
            "excluded_entity_ids": [],
            "new_entity_ids_by_round": {"1": [], "2": []},
            "convergence_round_ids": ["1", "2"],
        },
        "metadata": {"origin": "synthetic-fixture", "redaction_version": "1"},
    }
    _bind_reviewed_universe(payload)
    return payload


def _bind_reviewed_universe(payload: dict[str, object]) -> None:
    closure = payload["closure"]
    assert isinstance(closure, dict)
    closure["reviewed_universe_sha256"] = compute_universe_review_digest(
        contract_identity=payload["contract_identity"],  # type: ignore[arg-type]
        data_cutoff=payload["data_cutoff"],  # type: ignore[arg-type]
        source_policy_id=str(payload["source_policy_id"]),
        source_policy_version=str(payload["source_policy_version"]),
        entities=payload["entities"],  # type: ignore[arg-type]
        routes=payload["routes"],  # type: ignore[arg-type]
        expansion_receipts=payload["expansion_receipts"],  # type: ignore[arg-type]
        closure=closure,
        sources=payload["sources"],  # type: ignore[arg-type]
    )


def _synthetic_package() -> ResearchPackage:
    return ResearchPackage.model_validate(_synthetic_package_payload())


def _forged_record(record: PublicationRecord, case: str) -> PublicationRecord:
    """Build the forged copy for one case without re-running validation."""

    if case == "stale-review":
        return record.model_copy(update={"model_suggestion": "review"})
    if case == "dropped-fetch-attempts":
        return record.model_copy(update={"fetch_attempts": ()})
    if case == "dropped-affected-reports":
        return record.model_copy(update={"affected_reports": ()})
    if case == "forged-nested-attempt":
        forged_attempt = record.fetch_attempts[0].model_copy(update={"diagnostic": None})
        return record.model_copy(
            update={"fetch_attempts": (forged_attempt, *record.fetch_attempts[1:])}
        )
    raise AssertionError(f"unknown record forgery case: {case}")


def _forged_package(case: str) -> ResearchPackage:
    """Build a copied package that never passed construction-time validation."""

    package = _synthetic_package()
    if case == "empty-reports":
        return package.model_copy(update={"reports": ()})
    if case == "forged-closure-digest":
        return package.model_copy(
            update={
                "closure": package.closure.model_copy(update={"reviewed_universe_sha256": "f" * 64})
            }
        )
    forged_record = _forged_record(package.publication_records[0], case)
    return package.model_copy(update={"publication_records": (forged_record,)})


def test_valid_verdict_and_manual_gate_behavior_are_preserved(tmp_path: Path) -> None:
    record = PublicationRecord.model_validate(_synthetic_record_payload())
    assert classify_publication(record).required is True
    assert classify_publication(_synthetic_record_payload()).required is True

    materialized = materialize_publication_manual_gate(
        tmp_path, _synthetic_package(), snapshot_id=_SNAPSHOT_ID
    )
    assert materialized is not None
    assert materialized.replayed is False
    assert materialized.gate.state == "awaiting_user"
    assert materialized.gate.affected_reports == ("B",)
    assert materialized.gate.requests[0].blocking_fields == ("b_core_efficacy_endpoint",)
    assert materialized.gate.requests[0].attempted_paths == (
        "publisher-full-text",
        "repository-full-text",
    )
    assert (tmp_path / materialized.relative_path).is_file()
    assert (tmp_path / "logs/manual-supply-request.md").is_file()


@pytest.mark.parametrize(("case", "match"), _RECORD_FORGERY_CASES)
def test_copied_publication_record_cannot_bypass_public_classification(
    case: str, match: str
) -> None:
    record = PublicationRecord.model_validate(_synthetic_record_payload())
    forged = _forged_record(record, case)
    assert forged != record

    with pytest.raises(ValueError, match=match):
        classify_publication(forged)
    with pytest.raises(ValueError, match=match):
        classify_publication(forged.model_dump(mode="json"))

    # The source instance the copy was taken from is untouched and still valid.
    assert record.model_suggestion == "primary_result"
    assert record.affected_reports == ("B",)
    assert len(record.fetch_attempts) == 2
    assert classify_publication(record).required is True


def test_forged_package_instance_cannot_bypass_package_closure_boundary() -> None:
    package = _synthetic_package()
    assert validate_research_package(_synthetic_package_payload()) == package
    assert validate_research_package(package) == package

    forged_record = _forged_record(package.publication_records[0], "stale-review")
    forged_records = package.model_copy(update={"publication_records": (forged_record,)})
    with pytest.raises(ResearchPackageValidationError):
        validate_research_package(forged_records)

    forged_closure = package.model_copy(
        update={
            "closure": package.closure.model_copy(update={"reviewed_universe_sha256": "f" * 64})
        }
    )
    with pytest.raises(ResearchPackageValidationError, match="字节"):
        validate_research_package(forged_closure)


def test_mapping_with_copied_nested_attempt_rechecks_field_validators() -> None:
    record = PublicationRecord.model_validate(_synthetic_record_payload())
    mapping = record.model_dump(mode="python")
    mapping["fetch_attempts"] = (
        record.fetch_attempts[0].model_copy(update={"attempted_at": datetime(2026, 9, 4)}),
        record.fetch_attempts[1],
    )
    with pytest.raises(ValueError, match="时区"):
        classify_publication(mapping)
    assert record.fetch_attempts[0].attempted_at.tzinfo is not None


def test_mapping_with_copied_nested_verdict_rechecks_field_validators() -> None:
    package = _synthetic_package()
    mapping = package.model_dump(mode="python")
    mapping["publication_records"] = (
        package.publication_records[0].model_copy(update={"title": ""}),
    )
    with pytest.raises(ResearchPackageValidationError, match="title"):
        validate_research_package(mapping)
    assert package.publication_records[0].title == "合成主要结果论文"


@pytest.mark.parametrize("case", _PACKAGE_FORGERY_CASES)
def test_forged_copied_package_cannot_reach_manual_gate_boundary(case: str, tmp_path: Path) -> None:
    package = _synthetic_package()
    forged = _forged_package(case)
    assert forged != package

    with pytest.raises(PublicationManualGateError) as error:
        materialize_publication_manual_gate(tmp_path, forged, snapshot_id=_SNAPSHOT_ID)
    assert "合同校验" in str(error.value)

    # Fail closed before any child request, inbox directory, gate file,
    # user-facing markdown, receipt, event, or project database write.
    assert list(tmp_path.rglob("*")) == []

    # The source package is unchanged and the same snapshot still gate-materializes.
    assert package == _synthetic_package()
    assert package.publication_records[0].acquisition_disposition == "manual_required"
