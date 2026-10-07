"""Display-only transcription and evidence preserve real scientific identities."""

from copy import deepcopy

import pytest

from ci_workflow.renderers.portal import report_a, report_b
from ci_workflow.reports.common.evidence_view import EvidenceObservationKind
from tests.reports.b.test_baseline_active_projection import _data


@pytest.mark.parametrize("word", ["Randomized", "STANDARD_DEVIATION", "Candy", "Landiolol"])
def test_b_transcription_never_splits_and_inside_a_source_word(word):
    assert report_b._native_text(word) == word


@pytest.mark.parametrize("word", ["Randomized", "STANDARD", "Landiolol"])
def test_a_time_fallback_never_splits_and_inside_a_source_word(word):
    assert report_a._native_timepoint_zh(word) == word


@pytest.mark.parametrize("label", ["Male and Female", "Male AND Female"])
def test_b_real_conjunction_still_transcribes(label):
    assert report_b._native_text(label) == "男性、女性"


def test_a_actual_time_conjunction_still_transcribes():
    assert report_a._native_timepoint_zh("Day 1 and Day 2") == "第1天、第2天"


def _evidence(data, source):
    row = report_b._project_record(source, domain="baseline", names={},
        trial_names={source["trial_id"]: "NCT12345678"}, fallback=source["row_id"])
    view = report_b._evidence_view(data, row=row, source=source,
        page_id="baseline-overview", observation_kind=EvidenceObservationKind.BASELINE_OBSERVATION,
        names={}, trial_names={source["trial_id"]: "NCT12345678"})
    return row, view


@pytest.mark.parametrize("role", ["reported_measure", "dispersion", "denominator"])
def test_evidence_keeps_exact_result_group_even_when_product_relation_unknown(role):
    data = _data()
    source = next(r for r in data.baseline_views["facts"] if r["source_value_role"] == role)
    original = deepcopy(source)
    row, evidence = _evidence(data, source)
    assert row["group_id"] == source["group_id"]
    assert evidence.row.group_id == source["group_id"]
    assert evidence.row.product_id is None
    assert evidence.original_text == source["source_text"]
    assert source == original


def test_missing_group_is_not_guessed_from_the_label_or_array_order():
    data = _data()
    source = deepcopy(data.baseline_views["facts"][0])
    source.pop("group_id")
    source["source_group_title"] = "BG001 / Experimental"
    _, evidence = _evidence(data, source)
    assert evidence.row.group_id is None
    assert evidence.row.product_id is None
