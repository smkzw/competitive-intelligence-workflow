"""登记终点标题、完整定义和时间窗分别保留，同一父级实例不可串配。"""

from __future__ import annotations

from pathlib import Path

import pytest

from ci_workflow.renderers.portal.report_c import (
    _page_observations,
    _registry_display_text,
    _table_rows,
)
from ci_workflow.reports.c.contracts import DesignObservation
from ci_workflow.reports.c.endpoint_instances import (
    EndpointInstanceError,
    validate_endpoint_timepoint_pairs,
)
from ci_workflow.storage.source_derivation import extract_locator_quote
from tests.integration.test_r24_c_source_consumers import _candidate
from tests.integration.test_r24_ctgov_c_design_projection import _fixed_capture, _project_fixed


def _data() -> tuple[tuple[DesignObservation, ...], dict[str, str]]:
    sources = tuple(_fixed_capture(nct) for nct in ("NCT02264639", "NCT03829449"))
    rows = _project_fixed("NCT02264639", "NCT03829449").observations
    return rows, {source.source_id: source.content_text for source in sources}


def test_complete_endpoint_descriptions_are_separate_precise_candidate_atoms() -> None:
    rows, sources = _data()
    descriptions = [row for row in rows if row.field.endswith("_endpoint_description")]
    assert len(descriptions) == 17
    assert all(row.review_state.value == "candidate" for row in descriptions)
    for row in descriptions:
        assert row.source_locator.field_path.endswith(".description")
        assert row.source_text == extract_locator_quote(
            sources[row.source_version_id], media_type="application/json",
            locator=row.source_locator,
        )
        title = next(item for item in rows if item.outcome_id == row.outcome_id
                     and item.trial_id == row.trial_id
                     and item.field.endswith("_endpoint_definition"))
        assert title.source_locator.field_path.rsplit(".", 1)[0] == (
            row.source_locator.field_path.rsplit(".", 1)[0]
        )
        assert title.source_text != ""
        assert row.group_id == title.group_id and row.cohort_id == title.cohort_id
    assert any("Cohort 4 only" in row.source_text for row in descriptions)
    assert len(validate_endpoint_timepoint_pairs(
        rows, protocol_sources=sources, universe_trial_ids={row.trial_id for row in rows},
    )) == 17  # Supplemental descriptions are not extra endpoint measures.


@pytest.mark.parametrize("variant", ["quote", "parent", "role", "group", "orphan"])
def test_description_cannot_escape_parent_or_rewrite_source(variant: str) -> None:
    rows, sources = _data()
    rows = list(rows)
    index = next((i for i, row in enumerate(rows)
                  if row.field.endswith("_endpoint_description")), None)
    assert index is not None
    row = rows[index]
    if variant == "orphan":
        rows = [item for item in rows if item is row or item.outcome_id != row.outcome_id]
    else:
        changes = {
            "quote": {"source_text": "invented source definition"},
            "parent": {"source_locator": row.source_locator.model_copy(update={
                "field_path": row.source_locator.field_path.replace("[0]", "[1]"),
            })},
            "role": {"endpoint_key": "secondary_endpoint"},
            "group": {"group_id": "not-the-source-scope"},
        }
        rows[index] = row.model_copy(update=changes[variant])
    with pytest.raises(EndpointInstanceError):
        validate_endpoint_timepoint_pairs(rows, protocol_sources=sources)


def test_normal_c_endpoint_page_retains_each_complete_definition_in_table(tmp_path: Path) -> None:
    _, _, report, _, _ = _candidate(tmp_path)
    page_rows = _page_observations(report, "endpoint-timepoint-matrix")
    table = _table_rows(report, page_rows, page_id="endpoint-timepoint-matrix")
    descriptions = [row for row in report.observations
                    if row.field.endswith("_endpoint_description")]
    assert len(descriptions) == 17
    by_id = {row["row_id"]: row for row in table}
    for row in descriptions:
        assert row.row_id in by_id
        # Registry Markdown escapes are presentation-only; source atoms above
        # still re-extract the original bytes without normalizing the quotation.
        assert _registry_display_text(row.source_text) in by_id[row.row_id]["value"]
