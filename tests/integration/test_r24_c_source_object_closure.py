"""Whole-source objects cannot disappear when a submitted observation is removed.

Accepted fixture states are contract assumptions, not source adoption receipts.
The fixed official source bytes are retained unchanged for every production call.
"""

import pytest

from ci_workflow.application import fresh_c_research_package as c
from ci_workflow.gates.models import GateUnitOutcome, ReportDecision
from tests.integration.test_fresh_c_research_package import PROJECT_ID
from tests.integration.test_r24_c_compound_source_coverage import _source_content


@pytest.mark.parametrize(('variant', 'unit_id'), (
    ('whole_primary_object_removed', 'c_endpoint_definitions_timepoints'),
    ('arm_label_only', 'c_intervention_control_rescue'),
    ('one_cohort_dosing_only', 'c_dose_schedule_followup'),
    ('study_type_without_stage', 'c_trial_identity_stage_role'),
))
def test_removing_whole_source_objects_blocks_compound_coverage(
    variant: str, unit_id: str,
) -> None:
    content = _source_content()
    raw = content.model_dump(mode='json')
    rows = raw['report_data']['observations']
    if variant == 'whole_primary_object_removed':
        rows[:] = [row for row in rows if row['outcome_id'] != 'outcome-nct02264639-pri-0']
    elif variant == 'arm_label_only':
        rows[:] = [row for row in rows if row['field_family'] != 'intervention'
                   or row['row_id'] == 'c-nct02264639-arm-0-label']
    elif variant == 'one_cohort_dosing_only':
        rows[:] = [row for row in rows if row['field_family'] != 'dose_schedule'
                   or row['row_id'] == 'c-nct02264639-arm-0-dosing']
    else:
        rows[:] = [row for row in rows if row['field_family'] != 'trial_identity'
                   or row['source_field_name'] == 'studyType']
    raw['claims'][0]['fact_ids'] = [row['row_id'] for row in rows]
    changed = c.validate_fresh_c_content(raw)
    assert changed.sources == content.sources
    assert len(c.derive_c_research_facts(changed)) == len(rows)
    outcome = c.evaluate_c_report_gate(changed, project_id=PROJECT_ID,
        evidence_snapshot_id='source-object-negative', contract_version='1')
    assert next(row for row in outcome.result.unit_results
                if row.unit_id == unit_id).outcome is GateUnitOutcome.BLOCKED
    assert outcome.result.decision is ReportDecision.BLOCKED


def test_complete_source_objects_remain_satisfied() -> None:
    outcome = c.evaluate_c_report_gate(_source_content(), project_id=PROJECT_ID,
        evidence_snapshot_id='source-object-positive', contract_version='1')
    assert outcome.result.decision is ReportDecision.PASSED
