"""Pending evidence is neither missing source nor scientific acceptance."""
from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.reports.c import contracts
from tests.integration.test_r24_c_source_consumers import _candidate
from tests.reports.c.test_design_gate import _core_design_observations, _observation


def test_pending_registry_families_keep_the_gate_closed_without_claiming_source_missing():
    rows = tuple(row.model_copy(update={"review_state": FactReviewState.CANDIDATE})
                 for row in _core_design_observations(contracts))
    result = contracts.evaluate_design_gate(rows, core_trial_ids=("trial-1",))
    assert result.decision is contracts.DesignGateDecision.BLOCKED
    assert len(result.failures) == 4
    for failure in result.failures:
        assert "已取得" in failure.user_note_zh and "复核" in failure.user_note_zh
        assert "缺少" not in failure.user_note_zh


def test_pending_statistical_evidence_preserves_source_disclosure_without_accepting_it():
    rows = tuple(row.model_copy(update={"review_state": FactReviewState.CANDIDATE})
                 for row in _core_design_observations(contracts, include_statistical=True))
    result = contracts.evaluate_design_gate(rows, core_trial_ids=("trial-1",))
    assert len(result.nonblocking_gaps) == 5
    assert result.decision is contracts.DesignGateDecision.BLOCKED
    for gap in result.nonblocking_gaps:
        assert gap.disclosure_state is FactDisclosureState.REPORTED_VALUE
        assert "复核" in gap.user_note_zh and "尚未公开" not in gap.user_note_zh


def test_pending_conflicting_disclosure_does_not_choose_the_first_candidate():
    base = _core_design_observations(contracts)
    reported = _observation(
        contracts, row_id="stat-pending", field="analysis_population",
        field_family=contracts.DesignFieldFamily.STATISTICAL,
        review_state=FactReviewState.CANDIDATE,
    )
    conflicting = reported.model_copy(update={
        "row_id": "stat-conflicting", "disclosure_state": FactDisclosureState.CONFLICTING,
    })
    for candidates in ((reported, conflicting), (conflicting, reported)):
        result = contracts.evaluate_design_gate((*base, *candidates), core_trial_ids=("trial-1",))
        gaps = [gap for gap in result.nonblocking_gaps if gap.field_id == "analysis_population"]
        assert {gap.disclosure_state for gap in gaps} == {
            FactDisclosureState.CONFLICTING, FactDisclosureState.REPORTED_VALUE,
        }
        conflict = next(
            gap for gap in gaps if gap.disclosure_state is FactDisclosureState.CONFLICTING
        )
        assert "冲突" in conflict.user_note_zh and "尚未公开" not in conflict.user_note_zh


def test_different_group_disclosures_remain_separate_not_invented_conflict():
    base = _core_design_observations(contracts)
    reported = _observation(
        contracts, row_id="stat-reported", field="analysis_population", group_id="group-1",
        field_family=contracts.DesignFieldFamily.STATISTICAL,
        review_state=FactReviewState.CANDIDATE,
    )
    missing = reported.model_copy(update={
        "row_id": "stat-unreported", "group_id": "group-2",
        "disclosure_state": FactDisclosureState.NOT_REPORTED,
    })
    for rows in ((reported, missing), (missing, reported)):
        result = contracts.evaluate_design_gate((*base, *rows), core_trial_ids=("trial-1",))
        gaps = [gap for gap in result.nonblocking_gaps if gap.field_id == "analysis_population"]
        assert {(gap.group_id, gap.disclosure_state) for gap in gaps} == {
            ("group-1", FactDisclosureState.REPORTED_VALUE),
            ("group-2", FactDisclosureState.NOT_REPORTED),
        }
        assert all("冲突" not in gap.user_note_zh for gap in gaps)


def test_absent_statistical_evidence_does_not_claim_it_was_never_published():
    result = contracts.evaluate_design_gate(_core_design_observations(contracts),
                                           core_trial_ids=("trial-1",))
    assert result.decision is contracts.DesignGateDecision.PASSED
    for gap in result.nonblocking_gaps:
        assert "当前资料" in gap.user_note_zh
        assert "尚未公开" not in gap.user_note_zh


def test_pinned_real_c_candidate_remains_unaccepted_and_pending_not_missing(tmp_path):
    # Rebuild the versioned native-source fixture, not a workstation artifact path.
    _root, _snapshot, data, _versions, _captures = _candidate(tmp_path)
    original = data.model_dump_json()
    result = contracts.evaluate_design_gate(data.observations, core_trial_ids=data.trial_ids)
    assert result.decision is contracts.DesignGateDecision.BLOCKED
    assert len(result.failures) == 8
    assert all("缺少" not in failure.user_note_zh for failure in result.failures)
    assert all(row.review_state is FactReviewState.CANDIDATE for row in data.observations)
    assert data.model_dump_json() == original
