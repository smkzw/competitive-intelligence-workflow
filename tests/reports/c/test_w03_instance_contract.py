from __future__ import annotations

from types import SimpleNamespace

import pytest

from ci_workflow.reports.c.arm_interventions import project_arm_interventions
from ci_workflow.reports.c.endpoint_instances import (
    EndpointInstanceError,
    validate_endpoint_timepoint_pairs,
)


def _obs(row_id: str, *, trial: str = "T1", outcome: str = "O1", family: str,
         role: str = "primary", group: str = "G1", cohort: str = "C1",
         period: str = "P1", window: str = "W12", text: str = "measure"):
    return SimpleNamespace(
        row_id=row_id, trial_id=trial, outcome_id=outcome, field_family=family,
        endpoint_key=role, group_id=group, cohort_id=cohort, period=period,
        assessment_timepoint=window, source_text=text, source_version_id="sv1",
    )


def test_full_universe_requires_per_study_instance_coverage() -> None:
    rows = [
        _obs("e1", family="endpoint"),
        _obs("t1", family="timepoint", text="Week 12"),
    ]
    with pytest.raises(EndpointInstanceError, match="T2"):
        validate_endpoint_timepoint_pairs(rows, universe_trial_ids={"T1", "T2"})


@pytest.mark.parametrize("changed", ["role", "group", "cohort", "period", "window"])
def test_instance_pair_requires_complete_identity(changed: str) -> None:
    endpoint = _obs("e1", family="endpoint")
    updates = {
        "role": "secondary", "group": "G2", "cohort": "C2",
        "period": "P2", "window": "W24",
    }
    timepoint = _obs("t1", family="timepoint", text="Week 12", **{changed: updates[changed]})
    with pytest.raises(EndpointInstanceError):
        validate_endpoint_timepoint_pairs([endpoint, timepoint], universe_trial_ids={"T1"})


def test_multiple_primary_instances_are_legal_when_each_is_paired() -> None:
    rows = [
        _obs("e1", family="endpoint", outcome="O1", text="Measure 1"),
        _obs("t1", family="timepoint", outcome="O1", text="Week 12"),
        _obs("e2", family="endpoint", outcome="O2", text="Measure 2", window="W24"),
        _obs("t2", family="timepoint", outcome="O2", text="Week 24", window="W24"),
    ]
    instances = validate_endpoint_timepoint_pairs(rows, universe_trial_ids={"T1"})
    assert {item.outcome_id for item in instances} == {"O1", "O2"}


def test_arm_interventions_follow_explicit_labels_without_arm1_fallback() -> None:
    rows = project_arm_interventions(
        trial_id="T1",
        arms=[
            {"label": "Drug X", "type": "EXPERIMENTAL"},
            {"label": "Placebo", "type": "PLACEBO_COMPARATOR"},
        ],
        interventions=[
            {"name": "Drug X 100 mg", "description": "100 mg QD", "armGroupLabels": ["Drug X"]},
            {"name": "Placebo", "description": "matching placebo", "armGroupLabels": ["Placebo"]},
        ],
    )
    assert {(row["group_id"], row["intervention_name"]) for row in rows} == {
        ("arm1", "Drug X 100 mg"), ("arm2", "Placebo")
    }


def test_unbound_intervention_is_explicit_blocking_relationship_gap() -> None:
    rows = project_arm_interventions(
        trial_id="T1",
        arms=[{"label": "Drug X", "type": "EXPERIMENTAL"}],
        interventions=[
            {"name": "Missing relation", "description": "100 mg QD"},
            {"name": "Unknown relation", "armGroupLabels": ["Placebo"]},
        ],
    )
    assert len(rows) == 2
    assert {row["relationship_status"] for row in rows} == {
        "missing_arm_labels", "unknown_arm_label"
    }
    assert all(row["blocking"] is True and row["group_id"] is None for row in rows)
