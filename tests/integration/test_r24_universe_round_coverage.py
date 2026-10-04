"""Convergence means complete expansion rounds, not two empty partial queries."""

from copy import deepcopy
from typing import Any

import pytest

from ci_workflow.domain.research_package import ResearchPackage, compute_universe_review_digest
from tests.contract.test_v13_intake_package import _package_payload


def _bind_reviewed_universe(payload: dict[str, Any]) -> None:
    payload["closure"]["reviewed_universe_sha256"] = compute_universe_review_digest(
        **{key: payload[key] for key in (
            "contract_identity", "data_cutoff", "source_policy_id", "source_policy_version",
            "entities", "routes", "expansion_receipts", "closure", "sources",
        )},
        report_payloads=payload.get("report_payloads", []),
    )


def _complete_round_payload() -> dict[str, Any]:
    payload: dict[str, Any] = deepcopy(_package_payload())
    receipts = payload["expansion_receipts"]
    for round_id, dimensions in (("1", ("alias", "target")), ("2", ("company", "trial"))):
        for dimension in dimensions:
            template = next(item for item in receipts if item["dimension"] == dimension)
            receipt_id = f"complete-{dimension}-{round_id}"
            receipts.append({
                **template,
                "receipt_id": receipt_id,
                "round_id": round_id,
                "strategy_id": f"complete-{dimension}-{round_id}",
                "attempt_ids": [f"attempt-{receipt_id}"],
                "discovered_entity_ids": [],
                "source_ids": [],
                "result_class": "searched_no_evidence",
                "diagnostic": "该维度本轮完成，无新增",
            })
            payload["closure"][f"{dimension}_expansion_receipts"].append(receipt_id)
    payload["closure"]["review_digest_version"] = "2"
    _bind_reviewed_universe(payload)
    return payload


@pytest.mark.parametrize("dimension,round_id", [
    ("alias", "1"), ("target", "1"), ("company", "2"), ("trial", "2"),
])
def test_partial_zero_round_cannot_prove_universe_convergence(
    dimension: str, round_id: str,
) -> None:
    payload = _complete_round_payload()
    removed = [item for item in payload["expansion_receipts"]
               if item["dimension"] == dimension and item["round_id"] == round_id]
    payload["expansion_receipts"] = [item for item in payload["expansion_receipts"]
                                     if item not in removed]
    payload["closure"][f"{dimension}_expansion_receipts"] = [
        item["receipt_id"] for item in payload["expansion_receipts"]
        if item["dimension"] == dimension
    ]
    _bind_reviewed_universe(payload)
    package = ResearchPackage.model_validate(payload)
    with pytest.raises(ValueError, match="收敛轮次.*四类反向扩展"):
        package.assert_gate_ready()


def test_access_failure_cannot_be_counted_as_zero_new_entities() -> None:
    payload = _complete_round_payload()
    receipt = next(item for item in payload["expansion_receipts"]
                   if item["dimension"] == "company" and item["round_id"] == "2")
    receipt.update(result_class="access_or_permission_blocked", diagnostic="接口拒绝访问")
    _bind_reviewed_universe(payload)
    with pytest.raises(ValueError, match="收敛.*访问受限"):
        ResearchPackage.model_validate(payload).assert_gate_ready()


def test_complete_zero_rounds_pass_without_requiring_more_entities() -> None:
    ResearchPackage.model_validate(_complete_round_payload()).assert_gate_ready()


def test_historical_v1_partial_round_remains_readable_without_rehashing() -> None:
    payload = _package_payload()
    assert payload["closure"]["reviewed_universe_sha256"] == (
        "a82bd18a74fe406358882bd28f9257222b1c1aab6946962eef571aa1dbc6dc88"
    )
    assert ResearchPackage.model_validate(payload).closure.review_digest_version == "1"
