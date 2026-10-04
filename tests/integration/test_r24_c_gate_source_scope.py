"""Current C gate scope is source-backed design objects, not a discovery claim."""

from __future__ import annotations

import pytest

from ci_workflow.application import fresh_c_research_package as c
from ci_workflow.domain.enums import FactReviewState
from ci_workflow.gates.models import (
    EmptySetReasonCode,
    GateObjectType,
    GateUnitOutcome,
)
from tests.integration.test_r24_c_study_first_gate import _evaluate, _study_content


def test_current_c_snapshot_enumerates_real_endpoint_and_time_instances() -> None:
    content = _study_content()
    outcome = _evaluate(content)
    endpoints = {row.outcome_id for row in content.report_data.observations
                 if row.field_family.value == 'endpoint'}
    assert len(outcome.snapshot.endpoint_ids) == len(endpoints) == 4
    assert len(outcome.snapshot.timepoint_ids) == 4
    assert not any(proof.object_type in {GateObjectType.ENDPOINT, GateObjectType.TIMEPOINT}
                   for proof in outcome.snapshot.empty_set_proofs)
    endpoint_parents = {edge.child_id: edge.parent_id
                        for edge in outcome.snapshot.relationship_edges
                        if edge.parent_type is GateObjectType.TRIAL
                        and edge.child_type is GateObjectType.ENDPOINT}
    time_parents = {edge.child_id: edge.parent_id for edge in outcome.snapshot.relationship_edges
                    if edge.child_type is GateObjectType.TIMEPOINT}
    assert set(endpoint_parents) == set(outcome.snapshot.endpoint_ids)
    assert set(time_parents) == set(outcome.snapshot.timepoint_ids)
    assert set(time_parents.values()) == set(outcome.snapshot.endpoint_ids)


def test_current_c_wrong_family_design_anchor_cannot_close_grouping() -> None:
    content = _study_content()
    population = next(row for row in content.report_data.observations
                      if row.trial_id == 'trial-alpha-1' and row.field_family.value == 'population')
    designs = tuple(row.model_copy(update={'observation_id': population.observation_id})
                    if row.trial_id == population.trial_id else row
                    for row in content.trial_designs)
    changed = c.validate_fresh_c_content({
        **content.model_dump(mode='json'),
        'trial_designs': [row.model_dump(mode='json') for row in designs],
    })
    outcome = _evaluate(changed)
    assert any(row.unit_id == 'c_arm_randomization_blinding'
               and row.object_id == population.trial_id and row.outcome is GateUnitOutcome.BLOCKED
               for row in outcome.result.unit_results)


@pytest.mark.parametrize('changed', ('anchor', 'source_bytes'))
def test_current_c_design_evidence_identity_tracks_scientific_anchor_and_source(
    changed: str,
) -> None:
    content = _study_content()
    before = _evaluate(content)
    raw = content.model_dump(mode='json')
    if changed == 'anchor':
        design = raw['trial_designs'][0]
        anchor = next(row for row in raw['report_data']['observations']
                      if row['observation_id'] == design['observation_id'])
        # Same observation/source IDs, but a changed scientific design attribute.
        anchor['randomization'] = '非随机'
    else:
        # SourceCapture trims boundary whitespace. Change internal JSON bytes
        # without changing any quoted scientific values or their locator.
        raw['sources'][0]['content_text'] = raw['sources'][0]['content_text'].replace(
            '"observations":', '"observations" :', 1,
        )
    after = _evaluate(c.validate_fresh_c_content(raw))
    assert before.snapshot.trial_design_evidence != after.snapshot.trial_design_evidence


def test_single_arm_scope_empty_comparison_is_not_exhaustive_discovery() -> None:
    content = _study_content()
    single = next(design.trial_id for design in content.trial_designs
                  if design.design_kind.value == 'single_arm')
    raw = content.model_dump(mode='json')
    raw['report_data']['trials'] = [
        row for row in raw['report_data']['trials'] if row['id'] == single
    ]
    raw['report_data']['observations'] = [row for row in raw['report_data']['observations']
                                          if row['trial_id'] == single]
    raw['trial_designs'] = [row for row in raw['trial_designs'] if row['trial_id'] == single]
    retained = {row['row_id'] for row in raw['report_data']['observations']}
    raw['claims'] = [{**raw['claims'][0], 'fact_ids': sorted(retained)}]
    raw['design_paths']['candidate_paths'] = [
        row for row in raw['design_paths']['candidate_paths'] if row['trial_ids'] == [single]
    ]
    outcome = _evaluate(c.validate_fresh_c_content(raw))
    proof = next(proof for proof in outcome.snapshot.empty_set_proofs
                 if proof.object_type is GateObjectType.COMPARISON)
    assert proof.reason_code is EmptySetReasonCode.STUDY_DESIGN_SINGLE_ARM
    assert proof.evidence_version_id not in {'c-empty-comparison-v1', 'c-empty-comparison-v2'}


def test_current_c_unaccepted_anchor_cannot_be_laundered_by_other_grouping() -> None:
    content = _study_content()
    design = content.trial_designs[0]
    raw = content.model_dump(mode='json')
    anchor = next(row for row in raw['report_data']['observations']
                  if row['observation_id'] == design.observation_id)
    extra = {**anchor, 'row_id': 'accepted-other-group', 'observation_id': 'accepted-other-group'}
    raw['report_data']['observations'].append(extra)
    anchor['review_state'] = FactReviewState.CANDIDATE.value
    outcome = _evaluate(c.validate_fresh_c_content(raw))
    assert any(row.unit_id == 'c_arm_randomization_blinding'
               and row.object_id == design.trial_id and row.outcome is GateUnitOutcome.BLOCKED
               for row in outcome.result.unit_results)


def test_design_scientific_identity_ignores_consumer_display_changes() -> None:
    content = _study_content()
    before = _evaluate(content)
    raw = content.model_dump(mode='json')
    anchor = next(row for row in raw['report_data']['observations']
                  if row['observation_id'] == raw['trial_designs'][0]['observation_id'])
    anchor['display_text'] = '另一个页面的显示名称'
    anchor['difference_labels_zh'] = ['页面标记']
    after = _evaluate(c.validate_fresh_c_content(raw))
    assert before.snapshot.trial_design_evidence == after.snapshot.trial_design_evidence


def test_same_outcome_in_distinct_group_contexts_stays_two_instances() -> None:
    content = _study_content()
    raw = content.model_dump(mode='json')
    trial = 'trial-alpha-1'
    rows = [row for row in raw['report_data']['observations']
            if row['trial_id'] == trial and row['field_family'] in {'endpoint', 'timepoint'}]
    for row in rows:
        duplicate = {**row, 'row_id': row['row_id'] + '-other-group',
                     'observation_id': row['observation_id'] + '-other-group',
                     'group_id': f'group-{trial}-arm-2'}
        raw['report_data']['observations'].append(duplicate)
    outcome = _evaluate(c.validate_fresh_c_content(raw))
    assert len(outcome.snapshot.endpoint_ids) == len(outcome.snapshot.timepoint_ids) == 5
    groups = {edge.child_id for edge in outcome.snapshot.relationship_edges
              if edge.parent_type is GateObjectType.ENDPOINT
              and edge.child_type is GateObjectType.GROUP}
    assert {rows[0]['group_id'], f'group-{trial}-arm-2'} <= groups
