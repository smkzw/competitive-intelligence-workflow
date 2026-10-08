"""A literal registration mention is not an index-result relationship."""
from __future__ import annotations

import pytest

from ci_workflow.reports.b.contracts import build_trial_role_output
from ci_workflow.reports.common.study_roles import StudyRole
from ci_workflow.sources.connectors.pubmed import PubMedRecord, classify_pubmed_records
from tests.reports.b.test_trial_roles import _candidate


def _record(abstract: str, *, registry: tuple[str, ...] = ()) -> PubMedRecord:
    return PubMedRecord(
        pmid="99900100", title="Long-term trial report", abstract=abstract,
        publication_types=("Randomized Controlled Trial",), registry_nct_ids=registry,
    )


@pytest.mark.parametrize("context", (
    "Adults completed phase 2b (NCT00000001) lead-in trials.",
    "Participants from the lead-in trial NCT00000001 entered this extension.",
    "A previous trial (NCT00000001) reported benefit.",
    "Prior studies including NCT00000001 reported improvement.",
))
def test_contextual_id_cannot_replace_index_primary_result(context: str) -> None:
    record = _record(
        context + " The primary endpoint was response. Results showed efficacy. "
        "Clinical trial registration: NCT00000002.", registry=("NCT00000002",),
    )
    result, = classify_pubmed_records((record,), target_nct_ids=("NCT00000001",))
    assert result.matched_nct_ids == ()
    assert result.model_dump().get("contextual_nct_ids") == ("NCT00000001",)
    assert not result.can_replace_primary_report
    assert result.record == record
    output = build_trial_role_output(_candidate(), publication=result)
    assert output.study_role is StudyRole.CORE
    assert output.publication_matched_study_ids == ()
    assert output.model_dump().get("publication_contextual_study_ids") == ("NCT00000001",)


def test_index_and_lead_in_scope_are_stable_under_target_order_and_registry_overlap() -> None:
    record = _record(
        "Adults completed phase 2b (NCT00000001) lead-in trials. "
        "The primary endpoint was response. Results showed efficacy. "
        "Clinical trial registration: NCT00000002.",
        registry=("NCT00000001", "NCT00000002"),
    )
    for targets in (("NCT00000001", "NCT00000002"), ("NCT00000002", "NCT00000001")):
        result, = classify_pubmed_records((record,), target_nct_ids=targets)
        assert result.matched_nct_ids == ("NCT00000002",)
        assert result.model_dump().get("contextual_nct_ids") == ("NCT00000001",)
        assert result.role == "primary_report"  # rule suggestion, not accepted LTE role
        assert result.record == record


def test_explicit_index_registration_elsewhere_is_not_deleted_by_background_mention() -> None:
    record = _record(
        "A previous trial (NCT00000001) was reported. "
        "The primary endpoint was response. Results showed efficacy. "
        "This follow-up reports NCT00000001. Clinical trial registration: NCT00000001.",
    )
    result, = classify_pubmed_records((record,), target_nct_ids=("NCT00000001",))
    assert result.matched_nct_ids == ("NCT00000001",)
    assert result.model_dump().get("contextual_nct_ids", ()) == ()
    assert result.record == record


def test_background_treatment_history_is_not_prior_trial_evidence() -> None:
    record = _record(
        "Patients previously received topical treatment in NCT00000001. "
        "The primary endpoint was response. Results showed efficacy.",
    )
    result, = classify_pubmed_records((record,), target_nct_ids=("NCT00000001",))
    assert result.matched_nct_ids == ("NCT00000001",)
    assert result.role == "primary_report"


def test_secondary_instrument_paper_is_not_a_primary_report_or_deleted_study() -> None:
    record = PubMedRecord(
        pmid="99900101", title="Itch scale: A Secondary Analysis of 2 Randomized Trials",
        abstract="In this secondary analysis, we validated psychometric properties. "
        "The original primary endpoint response rate was 55%. NCT00000001.",
        publication_types=("Randomized Controlled Trial",),
    )
    result, = classify_pubmed_records((record,), target_nct_ids=("NCT00000001",))
    assert result.role == "ad_hoc_analysis"
    assert not result.can_replace_primary_report
    assert result.record == record
    assert build_trial_role_output(_candidate(), publication=result).study_role is StudyRole.CORE


def test_copied_context_scope_cannot_be_forged_into_result_binding() -> None:
    record = _record(
        "The lead-in trial NCT00000001 contributed patients. "
        "The primary endpoint results showed efficacy. Registration: NCT00000002.",
    )
    result, = classify_pubmed_records((record,), target_nct_ids=("NCT00000001",))
    forged = result.model_copy(update={"matched_nct_ids": ("NCT00000001",),
                                       "contextual_nct_ids": (), "role": "primary_report",
                                       "can_replace_primary_report": True})
    with pytest.raises(ValueError, match="重新分类"):
        build_trial_role_output(_candidate(), publication=forged)
