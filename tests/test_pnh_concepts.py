"""Configuration-only separation of a clinical endpoint from its measurement condition."""

from pathlib import Path

import pytest

from ciw.config import load_indication
from ciw.normalize.semantics import classify


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Proportion of Participants Who Remain Free From Transfusions", ("efficacy", "transfusion_avoidance")),
        (
            "Percentage of Subjects Who Achieved Reticulocyte Normalization in the Absence of Transfusions at Week 16",
            ("pd", "reticulocyte_normalization"),
        ),
        (
            "Percentage of Subjects Who Did Not Require a Transfusion (Transfusion Avoidance) During the RCP",
            ("efficacy", "transfusion_avoidance"),
        ),
        ("Hemoglobin normalization in the absence of transfusions", ("efficacy", "hb_normalization")),
        ("Reticulocyte count without blood transfusion", ("other", None)),
    ],
)
def test_transfusion_as_a_condition_does_not_replace_the_actual_outcome(title, expected):
    cfg = load_indication(Path(__file__).parents[1] / "indications/pnh.yaml")
    assert classify(title, cfg) == expected
