"""C 展示不可凭局部短语补出原文没有的入排条件。"""

from __future__ import annotations

from pathlib import Path

import pytest

from ci_workflow.renderers.portal.report_c import _eligibility_source_text, _value_text
from tests.integration.test_r24_c_source_consumers import _candidate


@pytest.mark.parametrize(("field", "source", "unsupported"), [
    ("inclusion_criterion", "Participants must be 12 years or older.", "EASI"),
    ("inclusion_criterion", "Inadequate response is defined by the investigator.", "28天"),
    ("inclusion_criterion", "Investigator's Global Assessment (IGA) score of 2 to 3.", "第8周"),
    ("exclusion_criterion", "Pregnant or breastfeeding participants are excluded.", "90天"),
    ("exclusion_criterion", "Known history of or suspected significant current "
     "immunosuppression.", "恶性肿瘤"),
    ("exclusion_criterion", "Pregnant or breastfeeding; a 30-day restriction applies.", "90天"),
])
def test_eligibility_display_preserves_complete_source_without_invented_requirements(
    field: str, source: str, unsupported: str,
) -> None:
    displayed = _eligibility_source_text(field, source)
    assert source in displayed
    assert unsupported not in displayed
    assert "原文" in displayed


def test_eligibility_display_retains_negation_parent_condition_and_exact_time_window() -> None:
    source = (
        "Not excluded solely for prior biological therapy. "
        "If receiving maintenance treatment, keep the dose stable for 14 days."
    )
    assert source in _eligibility_source_text("exclusion_criterion", source)


@pytest.mark.parametrize("source", [
    "Participation in a prior dupilumab clinical trial is not required.",
    "No prior treatment with dupilumab or tralokinumab, unless the washout is complete.",
    "Treatment with TCS within 1 week before the baseline visit is permitted if stable.",
])
def test_normal_c_value_path_retains_all_eligibility_qualifiers(
    tmp_path: Path, source: str,
) -> None:
    _, _, report, _, _ = _candidate(tmp_path)
    row = next(item for item in report.observations if item.field == "inclusion_criterion")
    row = row.model_copy(update={"source_text": source, "display_text": None})
    assert source in _value_text(report, row)
