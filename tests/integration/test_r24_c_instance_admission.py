"""Production counterexamples from the independent R24-74 source review."""

from __future__ import annotations

from typing import Any

import pytest

from ci_workflow.reports.c.endpoint_instances import (
    EndpointInstanceError,
    validate_endpoint_timepoint_pairs,
)
from tests.integration.test_r24_ctgov_c_design_projection import _fixed_capture, _project_fixed


@pytest.mark.parametrize("variant", [
    "invented_period", "blank_period", "wrong_trial", "cross_product",
    "forged_group", "forged_cohort", "renamed_outcome", "duplicate_outcome",
    "duplicate_definition", "duplicate_timepoint", "query_url", "fragment_url",
    "foreign_unpaired_trial",
])
def test_source_proven_protocol_does_not_admit_forged_identity(variant: str) -> None:
    projection = _project_fixed("NCT02264639")
    rows = list(projection.observations)
    endpoint_index = next(index for index, row in enumerate(rows)
                          if row.field_family == "endpoint")
    endpoint = rows[endpoint_index]
    time_index = next(index for index, row in enumerate(rows)
                      if row.field_family == "timepoint" and row.outcome_id == endpoint.outcome_id)
    changes: dict[str, Any] = {}
    selected = [endpoint_index, time_index]
    universe = {"nct02264639"}
    if variant in {"invented_period", "blank_period"}:
        changes["period"] = "screening" if variant == "invented_period" else " "
    elif variant == "wrong_trial":
        selected = [i for i, row in enumerate(rows)
                    if row.field_family in {"endpoint", "timepoint"}]
        changes["trial_id"] = "not-the-nct"
        universe = {"not-the-nct"}
    elif variant == "cross_product":
        selected = [time_index]
        changes["product_id"] = "other-product"
    elif variant in {"forged_group", "forged_cohort"}:
        changes["group_id" if variant == "forged_group" else "cohort_id"] = "arm-forged"
    elif variant == "renamed_outcome":
        changes["outcome_id"] = "not-the-proven-parent"
    elif variant == "duplicate_outcome":
        selected = [i for i, row in enumerate(rows)
                    if row.outcome_id and row.outcome_id != endpoint.outcome_id
                    and row.field_family in {"endpoint", "timepoint"}][:2]
        changes["outcome_id"] = endpoint.outcome_id
    elif variant in {"duplicate_definition", "duplicate_timepoint"}:
        original = rows[endpoint_index if variant == "duplicate_definition" else time_index]
        rows.append(original.model_copy(update={"row_id": "duplicate-instance"}))
        selected = []
    elif variant in {"query_url", "fragment_url"}:
        suffix = "?rank=1" if variant == "query_url" else "#results"
        for index in selected:
            row = rows[index]
            rows[index] = row.model_copy(update={"source_locator": row.source_locator.model_copy(
                update={"url": str(row.source_locator.url) + suffix},
            )})
        selected = []
    else:
        rows.append(endpoint.model_copy(update={
            "row_id": "foreign-unpaired", "trial_id": "nct-extra",
        }))
        selected = []
    for index in selected:
        rows[index] = rows[index].model_copy(update=changes)
    capture = _fixed_capture("NCT02264639")
    with pytest.raises(EndpointInstanceError):
        validate_endpoint_timepoint_pairs(
            rows, universe_trial_ids=universe,
            protocol_sources={capture.source_id: capture.content_text},
        )


def test_untouched_protocol_instances_keep_distinct_parents_and_unknown_period() -> None:
    projection = _project_fixed("NCT02264639", "NCT03829449")
    sources = [_fixed_capture(nct) for nct in ("NCT02264639", "NCT03829449")]
    instances = validate_endpoint_timepoint_pairs(
        projection.observations, universe_trial_ids={"nct02264639", "nct03829449"},
        protocol_sources={source.source_id: source.content_text for source in sources},
    )
    assert len(instances) == 17
    assert all(instance.period is None and instance.timepoint for instance in instances)
    assert len({(instance.trial_id, instance.outcome_id) for instance in instances}) == 17
