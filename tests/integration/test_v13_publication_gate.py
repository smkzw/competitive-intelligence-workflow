from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ci_workflow.application.publication_manual_gate import (
    PublicationManualGateError,
    mark_publication_files_unavailable,
)
from ci_workflow.ingestion.publication_gate import (
    ManualSupplyGate,
    ManualSupplyLedger,
    ManualSupplyResponse,
    PublicationFetchAttempt,
    PublicationGateError,
    PublicationRecord,
    compute_publication_review_digest,
)

_NOW = datetime(2026, 9, 4, tzinfo=UTC)


def _publication(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "publication_id": "pub-1",
        "source_id": "src-pub-1",
        "product_id": "product-1",
        "linked_trial_ids": ["nct-1"],
        "registry_identifiers": ["NCT00000001"],
        "title": "Primary result",
        "source_url": "https://doi.org/10.1000/example",
        "publication_class": "primary_result",
        "model_suggestion": "primary_result",
        "classification_reason": "登记关联的主要结果论文",
        "producer_id": "publication-worker-1",
        "producer_context": "publication-context-1",
        "fetch_attempts": [
            {
                "attempt_id": "fetch-1",
                "strategy_id": "doi-full-text",
                "route_family": "publisher",
                "attempted_at": _NOW,
                "result_class": "acquired",
                "source_id": "src-pub-1",
            }
        ],
        "acquisition_disposition": "acquired",
        "affected_reports": ["A", "B"],
    }
    value.update(overrides)
    return value


def _request(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "request_id": "request-1",
        "product_id": "product-1",
        "trial_id": "nct-1",
        "registry_identifiers": ["NCT00000001"],
        "doi": "10.1000/example",
        "pmid": "12345678",
        "exact_title": "Primary result",
        "blocking_fields": ["主要疗效"],
        "attempted_paths": ["官方登记结果页", "出版社附件页"],
        "source_links": ["https://doi.org/10.1000/example"],
        "delivery_directory": "evidence/manual-inbox/gate-1",
        "minimum_user_action": "下载原始附件并保留原文件名",
        "affected_reports": ["A", "B"],
    }
    value.update(overrides)
    return value


def _gate(**overrides: object) -> ManualSupplyGate:
    value: dict[str, object] = {
        "gate_id": "gate-1",
        "snapshot_id": "snapshot-1",
        "requests": [_request()],
        "affected_reports": ["A", "B"],
    }
    value.update(overrides)
    return ManualSupplyGate.model_validate(value)


def test_publication_classification_requires_independent_review_on_disagreement() -> None:
    assert PublicationRecord.model_validate(_publication()).required is True
    assert (
        PublicationRecord.model_validate(
            _publication(
                publication_class="review",
                model_suggestion="review",
                classification_reason="综述不直接回答核心结果",
                fetch_attempts=[],
                acquisition_disposition="excluded",
                affected_reports=[],
            )
        ).decision
        == "excluded"
    )

    with pytest.raises(ValueError):
        PublicationRecord.model_validate(
            _publication(publication_class="review", model_suggestion="primary_result")
        )

    reviewed_payload = _publication(
        publication_class="review",
        model_suggestion="primary_result",
        independent_review_id="review-1",
        independent_reviewer_id="reviewer-1",
        independent_context="clean-context-1",
        classification_reason="独立审查后排除综述",
        fetch_attempts=[],
        acquisition_disposition="excluded",
        affected_reports=[],
    )
    reviewed_payload["reviewed_candidate_sha256"] = compute_publication_review_digest(
        reviewed_payload
    )
    reviewed = PublicationRecord.model_validate(reviewed_payload)
    assert reviewed.required is False


def test_publication_review_rejects_self_review_and_stale_digest() -> None:
    payload = _publication(
        review_state="boundary",
        independent_review_id="review-1",
        independent_reviewer_id="publication-worker-1",
        independent_context="clean-context-1",
    )
    payload["reviewed_candidate_sha256"] = compute_publication_review_digest(payload)
    with pytest.raises(ValueError, match="身份"):
        PublicationRecord.model_validate(payload)

    payload["independent_reviewer_id"] = "reviewer-1"
    payload["reviewed_candidate_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="字节"):
        PublicationRecord.model_validate(payload)


def test_required_missing_publication_needs_typed_attempt_and_manual_disposition() -> None:
    with pytest.raises(ValueError, match="获取尝试"):
        PublicationRecord.model_validate(
            _publication(fetch_attempts=[], acquisition_disposition="manual_required")
        )

    blocked_attempt = {
        "attempt_id": "fetch-1",
        "strategy_id": "publisher-full-text",
        "route_family": "publisher",
        "attempted_at": _NOW,
        "result_class": "access_or_permission_blocked",
        "diagnostic": "出版社要求机构权限",
    }
    with pytest.raises(ValueError, match="两种不同策略"):
        PublicationRecord.model_validate(
            _publication(
                fetch_attempts=[blocked_attempt],
                acquisition_disposition="manual_required",
                blocking_fields=["b_core_efficacy_endpoint"],
                affected_reports=["B"],
            )
        )
    with pytest.raises(ValueError, match="两种不同策略"):
        PublicationRecord.model_validate(
            _publication(
                fetch_attempts=[
                    blocked_attempt,
                    {
                        **blocked_attempt,
                        "attempt_id": "fetch-same-family",
                        "strategy_id": "publisher-fallback-url",
                    },
                ],
                acquisition_disposition="manual_required",
                blocking_fields=["b_core_efficacy_endpoint"],
                affected_reports=["B"],
            )
        )
    record = PublicationRecord.model_validate(
        _publication(
            fetch_attempts=[
                blocked_attempt,
                {
                    **blocked_attempt,
                    "attempt_id": "fetch-2",
                    "strategy_id": "repository-full-text",
                    "route_family": "open_repository",
                },
            ],
            acquisition_disposition="manual_required",
            blocking_fields=["b_core_efficacy_endpoint"],
            affected_reports=["B"],
        )
    )
    assert record.manual_supply_required is True


def test_fetch_attempt_keeps_technical_failure_distinct_from_no_evidence() -> None:
    attempt = PublicationFetchAttempt.model_validate(
        {
            "attempt_id": "fetch-1",
            "strategy_id": "pubmed-api",
            "route_family": "bibliographic_index",
            "attempted_at": _NOW,
            "result_class": "transient_network_failure",
            "diagnostic": "连接超时",
        }
    )
    assert attempt.retryable is True

    with pytest.raises(ValueError, match="诊断"):
        PublicationFetchAttempt.model_validate(
            {
                "attempt_id": "fetch-2",
                "strategy_id": "pubmed-api",
                "route_family": "bibliographic_index",
                "attempted_at": _NOW,
                "result_class": "parser_or_schema_failure",
            }
        )


def test_manual_gate_is_single_response_and_preserves_user_facing_markdown() -> None:
    gate = _gate()
    received = gate.record_user_response(
        ManualSupplyResponse(
            response_id="response-1",
            outcome="file_received",
            responded_at=_NOW,
            original_filenames=("publisher-original.pdf",),
            validation_receipts=(
                {
                    "request_id": "request-1",
                    "content_sha256": "a" * 64,
                    "canonical_relative_path": "evidence/manual-inbox/gate-1/nct-file.pdf",
                    "source_version_id": "source-version-1",
                },
            ),
        ),
        official_evidence_sufficient=False,
    )
    assert received.state == "accepted"
    assert received.user_response_count == 1
    assert "publisher-original.pdf" not in received.to_markdown()
    assert "精确标题" not in received.to_markdown()

    with pytest.raises(PublicationGateError):
        received.record_user_response(
            ManualSupplyResponse(
                response_id="response-2",
                outcome="file_unavailable",
                responded_at=_NOW,
            ),
            official_evidence_sufficient=True,
            limitation_zh="官方登记未披露该字段",
        )

    unavailable = _gate().record_user_response(
        ManualSupplyResponse(
            response_id="response-1",
            outcome="file_unavailable",
            responded_at=_NOW,
        ),
        official_evidence_sufficient=False,
    )
    assert unavailable.evidence_insufficiency_page is True
    assert unavailable.limitation_zh is None


def test_manual_gate_cannot_accept_unvalidated_file_response() -> None:
    with pytest.raises(PublicationGateError, match="核验|回执"):
        _gate().record_user_response(
            ManualSupplyResponse(
                response_id="response-1",
                outcome="file_received",
                responded_at=_NOW,
                original_filenames=("publisher-original.pdf",),
            ),
            official_evidence_sufficient=False,
        )


def test_manual_ledger_rejects_second_gate_for_snapshot() -> None:
    ledger = ManualSupplyLedger().add(_gate())
    with pytest.raises(PublicationGateError):
        ledger.add(_gate(gate_id="gate-2"))


def test_unavailable_response_is_recorded_once_and_splits_limited_from_insufficient(
    tmp_path: Path,
) -> None:
    def persist(root: Path) -> None:
        path = root / "state/manual-supply-gates/snapshot-1.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(_gate().model_dump(mode="json")), encoding="utf-8")

    limited_root = tmp_path / "limited"
    persist(limited_root)
    limited = mark_publication_files_unavailable(
        limited_root,
        snapshot_id="snapshot-1",
        official_evidence_sufficient=True,
        limitation_zh="官方登记可回答核心问题，但缺少论文全文核验。",
    )
    assert limited.limitation_zh
    assert limited.evidence_insufficiency_page is False
    with pytest.raises(PublicationManualGateError, match="不能重复"):
        mark_publication_files_unavailable(
            limited_root,
            snapshot_id="snapshot-1",
            official_evidence_sufficient=True,
            limitation_zh="重复回答",
        )

    insufficient_root = tmp_path / "insufficient"
    persist(insufficient_root)
    insufficient = mark_publication_files_unavailable(
        insufficient_root,
        snapshot_id="snapshot-1",
        official_evidence_sufficient=False,
    )
    assert insufficient.evidence_insufficiency_page is True
    assert insufficient.limitation_zh is None
