"""Versioned source metadata must be covered by the universe review receipt."""

from copy import deepcopy
from typing import Any

import pytest

from ci_workflow.domain.research_package import ResearchPackage, compute_universe_review_digest
from tests.contract.test_v13_intake_package import _package_payload


def _digest(payload: dict[str, Any]) -> str:
    return compute_universe_review_digest(
        **{key: payload[key] for key in (
            "contract_identity", "data_cutoff", "source_policy_id", "source_policy_version",
            "entities", "routes", "expansion_receipts", "closure", "sources",
        )},
        report_payloads=payload.get("report_payloads", []),
    )


@pytest.mark.parametrize("change", [
    {"title": "不同来源标题"}, {"url": "https://example.org/changed"},
    {"locator": "another section"}, {"content_sha256": "b" * 64},
    {"published_at": "2026-01-01"}, {"effective_at": "2026-01-02"},
    {"retrieved_at": "2026-09-03T10:00:00+08:00"},
    {"source_role": "registry_history"}, {"limitations": ["历史版本不可用"]},
    {"locator_detail": {"document_role": "registry", "field_path": "changed.field"}},
])
def test_v2_source_change_invalidates_review(change: dict[str, Any]) -> None:
    payload = _package_payload()
    payload["closure"]["review_digest_version"] = "2"
    payload["closure"]["reviewed_universe_sha256"] = _digest(payload)
    ResearchPackage.model_validate(payload)
    modified = deepcopy(payload)
    modified["sources"][0].update(change)
    assert _digest(modified) != _digest(payload)
    with pytest.raises(ValueError, match="独立复核"):
        ResearchPackage.model_validate(modified)


def test_legacy_review_is_not_silently_promoted() -> None:
    payload = _package_payload()
    old_digest = payload["closure"]["reviewed_universe_sha256"]
    assert old_digest == "a82bd18a74fe406358882bd28f9257222b1c1aab6946962eef571aa1dbc6dc88"
    assert ResearchPackage.model_validate(payload).closure.review_digest_version == "1"
    payload["closure"]["review_digest_version"] = "2"
    assert _digest(payload) != old_digest
    with pytest.raises(ValueError, match="独立复核"):
        ResearchPackage.model_validate(payload)


def test_v2_order_and_timezone_equivalence_but_extra_source_changes_digest() -> None:
    payload = _package_payload()
    payload["closure"]["review_digest_version"] = "2"
    extra = deepcopy(payload["sources"][0])
    extra["source_id"] = "another-instance"
    original = _digest(payload)
    payload["sources"].append(extra)
    assert _digest(payload) != original
    both = _digest(payload)
    payload["sources"].reverse()
    assert _digest(payload) == both
    from datetime import UTC, datetime

    for source in payload["sources"]:
        source["retrieved_at"] = datetime.fromisoformat(
            source["retrieved_at"]
        ).astimezone(UTC).isoformat()
    assert _digest(payload) == both
    payload["sources"].append(deepcopy(extra))
    with pytest.raises(ValueError, match="重复来源"):
        _digest(payload)


def test_v2_cannot_hash_without_sources() -> None:
    payload = _package_payload()
    payload["closure"]["review_digest_version"] = "2"
    payload["sources"] = []
    with pytest.raises(ValueError, match="完整来源集合"):
        _digest(payload)
