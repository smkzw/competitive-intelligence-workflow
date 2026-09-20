from __future__ import annotations

import pytest

from ci_workflow.domain.research_package import ResearchPackage, ResearchPackageValidationError
from tests.contract.test_v13_intake_package import _bind_reviewed_universe, _package_payload


def _expansion(
    receipt_id: str,
    dimension: str,
    *,
    round_id: str,
    discovered_entity_ids: list[str] | None = None,
    result_class: str | None = None,
) -> dict[str, object]:
    discovered = discovered_entity_ids or []
    resolved_result = result_class or (
        "success_with_evidence" if discovered else "searched_no_evidence"
    )
    return {
        "receipt_id": receipt_id,
        "dimension": dimension,
        "round_id": round_id,
        "strategy_id": f"{dimension}-reverse-search-{round_id}",
        "route_ids": ["global-registry" if round_id == "0" else "china-registry"],
        "attempt_ids": [f"attempt-{receipt_id}"],
        "input_entity_ids": ["product-1"],
        "discovered_entity_ids": discovered,
        "source_ids": ["src-1"] if discovered else [],
        "query_sha256": "a" * 64,
        "result_class": resolved_result,
        "diagnostic": "已完成反向扩展，未发现新增实体" if not discovered else None,
    }


def _package_with_expansion_receipts() -> dict[str, object]:
    payload = _package_payload()
    payload["source_policy_id"] = "source-policy-v1"
    payload["source_policy_version"] = "1.1"
    payload["expansion_receipts"] = [
        _expansion("exp-alias", "alias", round_id="0", discovered_entity_ids=["product-1"]),
        _expansion("exp-target", "target", round_id="0"),
        _expansion("exp-company", "company", round_id="1"),
        _expansion("exp-trial", "trial", round_id="1"),
        _expansion("exp-alias-2", "alias", round_id="2"),
        _expansion("exp-target-2", "target", round_id="2"),
    ]
    closure = payload["closure"]
    assert isinstance(closure, dict)
    closure["alias_expansion_receipts"] = ["exp-alias", "exp-alias-2"]
    closure["target_expansion_receipts"] = ["exp-target", "exp-target-2"]
    closure["new_entity_ids_by_round"] = {"0": ["product-1"], "1": [], "2": []}
    closure["convergence_round_ids"] = ["1", "2"]
    closure.pop("convergence_round_id", None)
    _bind_reviewed_universe(payload)
    return payload


def test_universe_closure_requires_global_china_and_all_reverse_expansions() -> None:
    payload = _package_with_expansion_receipts()
    assert ResearchPackage.model_validate(payload).closure.closed is True

    routes = payload["routes"]
    assert isinstance(routes, list)
    routes[1] = dict(routes[1], result_class="network_error", diagnostic="网络失败")
    with pytest.raises(ValueError):
        ResearchPackage.model_validate(payload).assert_gate_ready()

    payload = _package_with_expansion_receipts()
    closure = payload["closure"]
    assert isinstance(closure, dict)
    closure["trial_expansion_receipts"] = []
    with pytest.raises(ValueError):
        ResearchPackage.model_validate(payload)

    payload = _package_with_expansion_receipts()
    closure = payload["closure"]
    assert isinstance(closure, dict)
    payload["producer_context"] = closure["independent_context"]
    with pytest.raises(ValueError):
        ResearchPackage.model_validate(payload)

    payload = _package_with_expansion_receipts()
    closure = payload["closure"]
    assert isinstance(closure, dict)
    closure["new_entity_ids_by_round"] = {"0": ["product-1"]}
    closure["convergence_round_ids"] = []
    with pytest.raises(ValueError, match="收敛"):
        ResearchPackage.model_validate(payload)


def test_empty_universe_is_representable_but_cannot_enter_report_gate() -> None:
    payload = _package_payload()
    payload["entities"] = []
    payload["sources"] = []
    payload["routes"] = [
        dict(route, result_class="not_applicable", source_ids=[], diagnostic="无适格项目")
        for route in payload["routes"]  # type: ignore[index]
    ]
    payload["closure"] = dict(
        payload["closure"],  # type: ignore[arg-type]
        candidate_entity_ids=[],
        new_entity_ids_by_round={"0": [], "1": []},
        convergence_round_ids=["0", "1"],
    )
    payload["expansion_receipts"] = [
        {
            **item,
            "input_entity_ids": [],
            "discovered_entity_ids": [],
            "source_ids": [],
            "result_class": "searched_no_evidence",
            "diagnostic": "穷尽检索后未发现适格实体",
            "round_id": "0" if index < 3 else "1",
        }
        for index, item in enumerate(payload["expansion_receipts"])  # type: ignore[arg-type]
    ]
    closure = payload["closure"]
    assert isinstance(closure, dict)
    closure["new_entity_ids_by_round"] = {"0": [], "1": []}
    payload["extraction_candidates"] = []
    _bind_reviewed_universe(payload)
    package = ResearchPackage.model_validate(payload)
    with pytest.raises(ResearchPackageValidationError, match="非空|证据不足"):
        package.assert_gate_ready()


def test_diagnosed_access_blocked_route_counts_as_completed_route() -> None:
    payload = _package_payload()
    payload["routes"] = [
        dict(payload["routes"][0], result_class="access_blocked", diagnostic="权限受限"),  # type: ignore[index]
        payload["routes"][1],  # type: ignore[index]
    ]
    _bind_reviewed_universe(payload)
    ResearchPackage.model_validate(payload).assert_gate_ready()


def test_independent_review_binds_distinct_identity_and_exact_universe_bytes() -> None:
    payload = _package_with_expansion_receipts()
    ResearchPackage.model_validate(payload).assert_gate_ready()

    closure = payload["closure"]
    assert isinstance(closure, dict)
    closure["independent_reviewer_id"] = payload["producer_id"]
    with pytest.raises(ValueError, match="生产者身份"):
        ResearchPackage.model_validate(payload)

    payload = _package_with_expansion_receipts()
    entities = payload["entities"]
    assert isinstance(entities, list)
    entities[0] = dict(entities[0], name="复核后被篡改的名称")
    with pytest.raises(ValueError, match="候选字节"):
        ResearchPackage.model_validate(payload)


def test_candidate_and_excluded_sets_require_matching_ontology_disposition() -> None:
    payload = _package_with_expansion_receipts()
    entities = payload["entities"]
    assert isinstance(entities, list)
    entities[0] = dict(entities[0], disposition="excluded")
    _bind_reviewed_universe(payload)
    with pytest.raises(ValueError, match="纳入处置"):
        ResearchPackage.model_validate(payload)


def test_recovery_is_conditional_and_last_two_rounds_prove_saturation() -> None:
    payload = _package_payload()
    payload["recovery_rounds"] = []
    payload["gap_strategies"] = [
        dict(payload["gap_strategies"][0], recovery_required=False)  # type: ignore[index]
    ]
    ResearchPackage.model_validate(payload).assert_gate_ready()

    payload = _package_payload()
    payload["recovery_rounds"] = [
        dict(payload["recovery_rounds"][0], information_gain="new_evidence"),  # type: ignore[index]
        dict(payload["recovery_rounds"][1], round_number=2),  # type: ignore[index]
        dict(
            payload["recovery_rounds"][0],  # type: ignore[index]
            round_number=3,
            strategy_id="third-regulatory-route",
            strategy_kind="regulatory-recovery",
            information_gain="no-new-evidence",
        ),
    ]
    ResearchPackage.model_validate(payload).assert_gate_ready()

    payload["recovery_rounds"][-1] = dict(  # type: ignore[index]
        payload["recovery_rounds"][-1],
        information_gain="new_evidence",  # type: ignore[index]
    )
    with pytest.raises(ResearchPackageValidationError, match="饱和"):
        ResearchPackage.model_validate(payload).assert_gate_ready()


def test_research_package_gate_readiness_rejects_same_strategy_or_network_failure() -> None:
    payload = _package_payload()
    package = ResearchPackage.model_validate(payload)
    package.assert_gate_ready()

    payload = _package_payload()
    payload["routes"] = [
        dict(payload["routes"][0], result_class="network_error", diagnostic="网络失败"),  # type: ignore[index]
        payload["routes"][1],  # type: ignore[index]
    ]
    _bind_reviewed_universe(payload)
    with pytest.raises(ResearchPackageValidationError):
        ResearchPackage.model_validate(payload).assert_gate_ready()

    payload = _package_payload()
    payload["recovery_rounds"] = [
        payload["recovery_rounds"][0],  # type: ignore[index]
        dict(payload["recovery_rounds"][1], strategy_kind="identifier-recovery"),  # type: ignore[index]
    ]
    with pytest.raises(ResearchPackageValidationError):
        ResearchPackage.model_validate(payload).assert_gate_ready()


def test_expansion_receipts_are_real_objects_bound_to_dimension_and_entities() -> None:
    payload = _package_with_expansion_receipts()
    ResearchPackage.model_validate(payload).assert_gate_ready()

    closure = payload["closure"]
    assert isinstance(closure, dict)
    closure["trial_expansion_receipts"] = ["phantom-receipt"]
    _bind_reviewed_universe(payload)
    with pytest.raises(ValueError, match="扩展回执"):
        ResearchPackage.model_validate(payload)


def test_closed_universe_rejects_failed_or_truncated_expansion() -> None:
    payload = _package_with_expansion_receipts()
    receipts = payload["expansion_receipts"]
    assert isinstance(receipts, list)
    receipts[-1] = _expansion(
        "exp-target-2",
        "target",
        round_id="2",
        result_class="network_error",
    )
    _bind_reviewed_universe(payload)
    with pytest.raises(ResearchPackageValidationError, match="扩展.*未完成|network_error"):
        ResearchPackage.model_validate(payload).assert_gate_ready()


def test_closed_universe_requires_two_consecutive_zero_new_entity_rounds() -> None:
    payload = _package_with_expansion_receipts()
    closure = payload["closure"]
    assert isinstance(closure, dict)
    closure["convergence_round_ids"] = ["2"]
    with pytest.raises(ValueError, match="连续.*零新增|两轮"):
        ResearchPackage.model_validate(payload)
