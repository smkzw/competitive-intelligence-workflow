"""Critical C coverage is not supplied by an exploratory/unknown endpoint.

Current C-v1 gate names primary and important secondary endpoints, not every
field assigned ENDPOINT/TIMEPOINT. Use the production selector and already
typed role/pairing key; never move an exploratory source atom into another
scientific domain just to avoid the gate.
"""

from __future__ import annotations

import pytest

from ci_workflow.application.fresh_c_research_package import (
    _unit_id_for,
    build_c_gate_bindings,
    evaluate_c_report_gate,
    validate_fresh_c_content,
)
from ci_workflow.gates.models import GateUnitOutcome, ReportDecision
from ci_workflow.reports.c import DesignFieldFamily, DesignObservation
from tests.integration.test_fresh_c_research_package import _content_payload, _observation

CRITICAL_UNIT = "c_endpoint_definitions_timepoints"


@pytest.mark.parametrize("family", [DesignFieldFamily.ENDPOINT, DesignFieldFamily.TIMEPOINT])
@pytest.mark.parametrize(
    ("role", "critical"),
    [
        ("primary_endpoint", True),
        ("important_secondary_endpoint", True),
        ("key_secondary_endpoint", True),
        ("secondary_endpoint", False),
        ("exploratory_endpoint", False),
        ("pharmacokinetic_endpoint", False),
        ("unknown_endpoint", False),
    ],
)
def test_only_explicit_primary_or_important_secondary_supplies_critical_coverage(
    family: DesignFieldFamily, role: str, critical: bool,
) -> None:
    field = role + ("_definition" if family is DesignFieldFamily.ENDPOINT else "_timepoint")
    observation = _observation(
        "trial-alpha-1", "product-alpha", family, field,
        "Explicit synthetic endpoint source material at Week16.", endpoint_key=role,
    )
    selected = _unit_id_for(observation)
    assert selected == (CRITICAL_UNIT if critical else None)
    assert observation.field_family is family
    assert observation.endpoint_key == role


def test_explicit_exploratory_role_is_not_overridden_by_a_legacy_primary_field_name() -> None:
    observation = _observation(
        "trial-alpha-1", "product-alpha", DesignFieldFamily.ENDPOINT,
        "primary_endpoint_definition", "Exploratory exposure response endpoint.",
        endpoint_key="exploratory_endpoint",
    )
    # Revalidation, not an unvalidated model_copy or a mock selector.
    observation = DesignObservation.model_validate(observation.model_dump())
    assert _unit_id_for(observation) is None


def test_exploratory_pair_remains_disclosed_but_cannot_fill_missing_critical_coverage() -> None:
    payload = _content_payload()
    rows = payload["report_data"]["observations"]
    for row in rows:
        if row["trial_id"] == "trial-alpha-1" and row["field_family"] in {"endpoint", "timepoint"}:
            row["endpoint_key"] = "exploratory_endpoint"
    content = validate_fresh_c_content(payload)
    exploratory = tuple(row for row in content.report_data.observations
                        if row.endpoint_key == "exploratory_endpoint")
    assert len(exploratory) == 2
    assert len(content.report_data.observations) == len(rows)
    bindings = build_c_gate_bindings(content)
    assert not any(binding.unit_id == CRITICAL_UNIT and binding.trial_id == "trial-alpha-1"
                   for binding in bindings)
    outcome = evaluate_c_report_gate(
        content, project_id="r24-role-fixture", evidence_snapshot_id="synthetic-role-source",
        contract_version="1",
    )
    assert outcome.result.decision is ReportDecision.BLOCKED
    blocked = [unit for unit in outcome.result.unit_results
               if unit.unit_id == CRITICAL_UNIT and unit.object_id == "trial-alpha-1"]
    assert len(blocked) == 1
    assert blocked[0].outcome is not GateUnitOutcome.SATISFIED
