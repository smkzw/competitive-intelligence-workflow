"""Source-backed compound counterexamples; fixture acceptance is not adoption."""

from __future__ import annotations

import pytest

from ci_workflow.application import fresh_c_research_package as c
from ci_workflow.gates.models import GateUnitOutcome
from tests.integration.test_fresh_c_research_package import PROJECT_ID
from tests.integration.test_r24_ctgov_c_design_projection import _fixed_capture, _project_fixed


def _source_content() -> c.FreshCResearchContent:
    source = _fixed_capture('NCT02264639')
    projection = _project_fixed('NCT02264639')
    rows = [{**row.model_dump(mode='json'), 'product_id': None, 'review_state': 'accepted'}
            for row in projection.observations]
    anchor = next(row for row in rows if row['source_field_name'] == 'interventionModel')
    # This is a test fixture assuming upstream acceptance, never a runtime
    # scientific receipt or mutation of the fixed raw source/candidate.
    return c.validate_fresh_c_content({
        'schema_version': '1.0', 'indication_id': 'pnh', 'indication': 'PNH',
        'data_cutoff': '2026-10-04T00:00:00+00:00', 'report_version': 'compound-probe',
        'producer_id': 'test-only', 'sources': [source.model_dump(mode='json')],
        'report_data': {
            'schema_version': '1.0', 'indication_id': 'pnh', 'indication': 'PNH',
            'data_cutoff': '2026-10-04T00:00:00+00:00', 'report_version': 'compound-probe',
            'products': [], 'trials': [{
                'id': 'nct02264639', 'display_id': 'NCT02264639', 'product_id': None,
                'name': 'Fixed registry study', 'phase': 'I', 'region': '全球',
                'status': 'COMPLETED', 'sample_size': 9, 'role': '测试来源研究',
            }], 'observations': rows,
        },
        'claims': [{'claim_id': 'test-claim', 'claim_text': '来源测试',
                    'claim_kind': 'direct_evidence', 'fact_ids': [row['row_id'] for row in rows]}],
        'trial_designs': [{'trial_id': 'nct02264639', 'design_kind': 'comparative',
                           'observation_id': anchor['observation_id']}],
        'design_paths': {'indication_id': 'pnh', 'patterns': [], 'differences': [],
                         'outliers': [], 'candidate_paths': []},
    })


@pytest.mark.parametrize(('variant', 'unit_id'), (
    ('age_only', 'c_target_population_criteria'),
    ('allocation_only', 'c_arm_randomization_blinding'),
    ('missing_masking', 'c_arm_randomization_blinding'),
    ('one_unaccepted_primary_time', 'c_endpoint_definitions_timepoints'),
    ('one_unaccepted_primary_definition', 'c_endpoint_definitions_timepoints'),
    ('contradictory_single_arm_declaration', 'c_arm_randomization_blinding'),
    ('entire_primary_instance_unaccepted', 'c_endpoint_definitions_timepoints'),
))
def test_partial_compound_source_family_cannot_satisfy_whole_unit(
    variant: str, unit_id: str,
) -> None:
    raw = _source_content().model_dump(mode='json')
    rows = raw['report_data']['observations']
    if variant == 'age_only':
        rows[:] = [row for row in rows if row['field_family'] != 'population'
                   or row['source_field_name'] == 'minimumAge']
    elif variant == 'allocation_only':
        rows[:] = [row for row in rows if row['field_family'] != 'grouping'
                   or row['source_field_name'] == 'allocation']
        raw['trial_designs'][0]['observation_id'] = next(
            row['observation_id'] for row in rows if row['source_field_name'] == 'allocation'
        )
    elif variant == 'missing_masking':
        rows[:] = [row for row in rows if row['source_field_name'] != 'masking']
    elif variant == 'contradictory_single_arm_declaration':
        # Actual pinned source declares PARALLEL. Do not infer one group from
        # a caller's label, array ordering or sample-size coincidence.
        raw['trial_designs'][0]['design_kind'] = 'single_arm'
    elif variant == 'entire_primary_instance_unaccepted':
        instance_id = next(row['outcome_id'] for row in rows
                           if row['field_family'] == 'endpoint'
                           and row['endpoint_key'] == 'primary_endpoint')
        for row in rows:
            if row['outcome_id'] == instance_id:
                row['review_state'] = 'candidate'
    else:
        family = 'timepoint' if variant.endswith('_time') else 'endpoint'
        row = next(row for row in rows if row['field_family'] == family
                   and row['endpoint_key'] == 'primary_endpoint'
                   and not row['field'].endswith('_description'))
        row['review_state'] = 'candidate'
    raw['claims'][0]['fact_ids'] = [row['row_id'] for row in rows]
    content = c.validate_fresh_c_content(raw)
    outcome = c.evaluate_c_report_gate(
        content, project_id=PROJECT_ID, evidence_snapshot_id='compound-source-test',
        contract_version='1',
    )
    result = next(row for row in outcome.result.unit_results
                  if row.unit_id == unit_id and row.object_id == 'nct02264639')
    assert result.outcome is GateUnitOutcome.BLOCKED


def test_complete_fixed_compound_families_still_meet_their_units() -> None:
    content = _source_content()
    outcome = c.evaluate_c_report_gate(
        content, project_id=PROJECT_ID, evidence_snapshot_id='compound-source-positive',
        contract_version='1',
    )
    for unit_id in ('c_target_population_criteria', 'c_arm_randomization_blinding',
                    'c_endpoint_definitions_timepoints'):
        assert next(row for row in outcome.result.unit_results
                    if row.unit_id == unit_id).outcome is GateUnitOutcome.SATISFIED
