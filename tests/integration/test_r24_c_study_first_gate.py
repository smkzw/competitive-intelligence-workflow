"""Study-first C closure without fabricated products or weakened evidence gates."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ci_workflow.application import fresh_c_research_package as c
from ci_workflow.gates.evaluator import evaluate_report
from ci_workflow.gates.models import (
    ApplicableUniverseSnapshot,
    GateEvaluationError,
    GateObjectType,
    GateSpec,
    ReportDecision,
    compute_universe_summary,
)
from tests.integration.test_fresh_c_research_package import (
    PROJECT_ID,
    ROOT,
    _content_payload,
)


def _study_content(*, mixed: bool = False) -> c.FreshCResearchContent:
    payload = _content_payload()
    data = payload['report_data']
    unknown = {'trial-alpha-1', 'trial-alpha-2'} if mixed else {
        row['id'] for row in data['trials']
    }
    for row in data['trials']:
        if row['id'] in unknown:
            row['product_id'] = None
    for row in data['observations']:
        if row['trial_id'] in unknown:
            row['product_id'] = None
    known = {row['product_id'] for row in data['trials']} - {None}
    data['products'] = [row for row in data['products'] if row['id'] in known]
    return c.validate_fresh_c_content(payload)


def _evaluate(content: c.FreshCResearchContent, **kwargs: object):
    return c.evaluate_c_report_gate(
        content, project_id=PROJECT_ID, evidence_snapshot_id='r24-study-evidence',
        contract_version='1', **kwargs,
    )


@pytest.mark.parametrize('mixed', (False, True))
def test_current_c_gate_evaluates_every_unassigned_study(mixed: bool) -> None:
    content = _study_content(mixed=mixed)
    outcome = _evaluate(content)
    assert outcome.spec_id == 'gate-spec-c-v2'
    assert outcome.spec_version == '2.0'
    assert outcome.snapshot.schema_version == '1.1'
    assert outcome.result.decision is ReportDecision.PASSED
    assert set(outcome.snapshot.trial_ids) == set(content.universe_trial_ids)
    assert set(outcome.snapshot.product_ids) == set(content.universe_product_ids)
    assert all(edge.parent_id is not None for edge in outcome.snapshot.relationship_edges)
    assert not any(proof.object_type is GateObjectType.PRODUCT
                   for proof in outcome.snapshot.empty_set_proofs)
    identity = {row.object_id for row in outcome.result.unit_results
                if row.unit_id == 'c_trial_identity_stage_role'}
    assert identity == set(content.universe_trial_ids)


def test_unassigned_c_still_blocks_missing_critical_population() -> None:
    content = _study_content()
    data = content.report_data.model_copy(update={'observations': tuple(
        row for row in content.report_data.observations
        if not (row.trial_id == 'trial-alpha-1' and row.field_family.value == 'population')
    )})
    # Population is not the design anchor in this fixture. All other scopes and
    # original source bytes remain unchanged; only the adopted evidence is absent.
    content = c.validate_fresh_c_content({
        **content.model_dump(mode='json'), 'report_data': data.model_dump(mode='json'),
    })
    outcome = _evaluate(content)
    assert outcome.result.decision is not ReportDecision.PASSED
    assert any(row.unit_id == 'c_target_population_criteria'
               and row.object_id == 'trial-alpha-1' for row in outcome.result.unit_results
               if row.outcome.value != 'satisfied')


def test_legacy_c_policy_remains_product_first() -> None:
    spec = GateSpec.from_yaml(ROOT / 'policies/gates/C-v1.yaml')
    assert spec.spec_id == 'gate-spec-c-v1' and spec.version == '1.0'
    assert all(unit.scope_parent is GateObjectType.PRODUCT for unit in spec.units)
    content = c.validate_fresh_c_content(_content_payload())
    outcome = _evaluate(content, spec=spec)
    assert outcome.snapshot.schema_version == '1.0'
    assert outcome.result.decision is ReportDecision.PASSED
    with pytest.raises((ValueError, GateEvaluationError)):
        _evaluate(_study_content(), spec=spec)


def test_study_snapshot_cannot_be_used_to_weaken_a_or_b_gate() -> None:
    outcome = _evaluate(_study_content())
    for kind in ('A', 'B'):
        spec = GateSpec.from_yaml(ROOT / f'policies/gates/{kind}-v1.yaml')
        with pytest.raises(GateEvaluationError, match='C|研究|trial|试验'):
            evaluate_report(spec, outcome.snapshot, (), contract_version='1')


def test_study_snapshot_requires_trials_and_binds_root_in_summary() -> None:
    outcome = _evaluate(_study_content())
    snapshot = outcome.snapshot
    kwargs = snapshot.model_dump(mode='python')
    kwargs.pop('schema_version')
    kwargs.pop('enumeration_complete')
    kwargs.pop('universe_summary')
    for name in ('empty_set_proofs', 'relationship_edges', 'trial_design_evidence'):
        kwargs[name] = getattr(snapshot, name)
    assert snapshot.universe_summary != compute_universe_summary(**kwargs)
    with pytest.raises((ValidationError, GateEvaluationError)):
        ApplicableUniverseSnapshot.model_validate({
            **snapshot.model_dump(mode='python'), 'trial_ids': (),
            'trial_design_evidence': (),
        })


def test_study_root_keeps_unknown_edges_and_cross_trial_scope_fail_closed() -> None:
    outcome = _evaluate(_study_content(mixed=True))
    binding = outcome.bindings[0].model_copy(update={'trial_id': 'trial-beta-1'})
    spec = GateSpec.from_yaml(ROOT / 'policies/gates/C-v2.yaml')
    with pytest.raises(GateEvaluationError, match='作用域|评估对象'):
        evaluate_report(spec, outcome.snapshot, (binding,), contract_version='1')
    tampered = outcome.snapshot.model_copy(update={'enumeration_complete': False})
    with pytest.raises(GateEvaluationError, match='穷举'):
        evaluate_report(spec, tampered, (), contract_version='1')
