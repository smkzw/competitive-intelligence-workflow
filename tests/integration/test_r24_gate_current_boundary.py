"""Production counterexamples for copied inputs, graph and projection identity.

These are deterministic fail-closed boundaries, not science adoption receipts.
R242 structural-only review hypotheses must fail against real production calls.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from ci_workflow.application import fresh_c_research_package as c
from ci_workflow.gates.evaluator import evaluate_report
from ci_workflow.gates.models import (
    GateEvaluationError,
    GateSpec,
    ReportKind,
    _aggregate_report_gates,
    _GateEvaluationBatch,
    assert_applicable_universe_closed,
    compute_universe_summary,
)
from tests.integration.test_fresh_c_research_package import (
    PROJECT_ID,
    ROOT,
    _content_payload,
    _ready_package_and_outcome,
)
from tests.integration.test_no_draft_when_blocked import (
    _make_record,
    applicable_critical_units,
    failed_gate_unit,
    prepare_workspace,
    public_write_blocker_package,
    real_blocked_result_for,
    snapshot_for,
    spec_yaml,
)
from tests.integration.test_r24_c_study_first_gate import _evaluate, _study_content
from tests.unit.test_gate_evaluator import (
    _design_record,
    _edge_payload,
    _identity_unit,
    _matrix_results,
    _minimal_spec,
    _snapshot,
)


def _resummarize(snapshot, **updates):
    copied = snapshot.model_copy(update=updates)
    fields = copied.model_dump(mode='python', exclude={
        'schema_version', 'enumeration_complete', 'universe_summary',
    })
    for name in ('empty_set_proofs', 'relationship_edges', 'trial_design_evidence'):
        fields[name] = getattr(copied, name)
    return copied.model_copy(update={'universe_summary': compute_universe_summary(
        **fields, root_object_type=copied.root_object_type,
    )})


def test_copied_reported_binding_without_source_location_is_rejected() -> None:
    outcome = _evaluate(_study_content())
    bindings = tuple(binding.model_copy(update={'source_location': None})
                     for binding in outcome.bindings)
    spec = GateSpec.from_yaml(ROOT / 'policies/gates/C-v2.yaml')
    with pytest.raises((ValueError, GateEvaluationError), match='来源|source|定位'):
        evaluate_report(spec, outcome.snapshot, bindings, contract_version='1')


def test_recomputed_summary_cannot_hide_missing_trial_design_evidence() -> None:
    outcome = _evaluate(_study_content())
    bad = _resummarize(outcome.snapshot, trial_design_evidence=())
    with pytest.raises((ValueError, GateEvaluationError), match='设计|试验'):
        assert_applicable_universe_closed(bad)


@pytest.mark.parametrize('association', ('endpoint-group', 'comparison-endpoint'))
def test_graph_rejects_cross_trial_association_without_scoped_binding(association: str) -> None:
    edges = (
        _edge_payload('product', 'product-a', 'trial', 'trial-1'),
        _edge_payload('product', 'product-a', 'trial', 'trial-2'),
        _edge_payload('trial', 'trial-1', 'comparison', 'comparison-1'),
        _edge_payload('trial', 'trial-1', 'group', 'group-1'),
        _edge_payload('trial', 'trial-1', 'group', 'group-2'),
        _edge_payload('trial', 'trial-2', 'group', 'group-3'),
        _edge_payload('trial', 'trial-1', 'endpoint', 'endpoint-1'),
        _edge_payload('trial', 'trial-2', 'endpoint', 'endpoint-2'),
        _edge_payload('comparison', 'comparison-1', 'group', 'group-1'),
        _edge_payload('comparison', 'comparison-1', 'group', 'group-2'),
        (_edge_payload('endpoint', 'endpoint-1', 'group', 'group-3')
         if association == 'endpoint-group' else
         _edge_payload('comparison', 'comparison-1', 'endpoint', 'endpoint-2')),
    )
    snapshot = _snapshot(
        trial_ids=('trial-1', 'trial-2'), group_ids=('group-1', 'group-2', 'group-3'),
        endpoint_ids=('endpoint-1', 'endpoint-2'), relationship_edges=edges,
        trial_design_evidence=(_design_record('trial-1', 'comparative'),
                               _design_record('trial-2', 'single_arm')),
    )
    with pytest.raises((ValueError, GateEvaluationError), match='同一试验|跨试验'):
        assert_applicable_universe_closed(snapshot)


def test_recomputed_batch_key_cannot_lower_policy_threshold() -> None:
    spec = _minimal_spec(_identity_unit(threshold=2))
    snapshot = _snapshot()
    results = tuple(result.model_copy(update={
        'threshold': 1, 'satisfied_count': 1,
        'fact_version_ids': result.fact_version_ids[:1],
    }) for result in _matrix_results(spec, snapshot))
    batch = _GateEvaluationBatch.from_evaluation(
        spec=spec, snapshot=snapshot, unit_results=results,
    )
    with pytest.raises(GateEvaluationError, match='阈值|threshold'):
        _aggregate_report_gates(spec=spec, snapshot=snapshot, batch=batch,
                                contract_version='1')


@pytest.mark.parametrize('kind', ('producer', 'digest'))
def test_model_instance_cannot_reuse_stale_independent_authorization(kind: str) -> None:
    package, _ = _ready_package_and_outcome(c)
    review = package.scientific_review.model_copy(update={
        'reviewer_id' if kind == 'producer' else 'reviewed_content_digest':
            package.producer_id if kind == 'producer' else '0' * 64,
    })
    forged = package.model_copy(update={'scientific_review': review})
    with pytest.raises((ValueError, ValidationError), match='独立|摘要|复核'):
        c.validate_fresh_c_package(forged)


@pytest.mark.parametrize('field', ('project_id', 'contract_version', 'evidence_snapshot_id',
                                  'spec_fingerprint', 'gate_result_key'))
def test_projection_rejects_changed_gate_identity_before_writing(
    tmp_path: Path, field: str,
) -> None:
    package, outcome = _ready_package_and_outcome(c)
    forged = replace(outcome, **{field: 'changed-identity'})
    with pytest.raises((ValueError, GateEvaluationError), match='绑定|身份|不一致|摘要|规格'):
        c.project_c_report_snapshot(
            package, outcome=forged, project_root=tmp_path, project_id=PROJECT_ID,
            contract_version=1, evidence_snapshot_id='evidence-snapshot-1',
        )
    assert not (tmp_path / 'snapshots').exists()


def test_c_gate_rejects_unsupported_policy_id_version_pair() -> None:
    spec = GateSpec.from_yaml(ROOT / 'policies/gates/C-v2.yaml').model_copy(
        update={'version': '1.0'},
    )
    with pytest.raises(ValueError, match='版本|规格|规则'):
        _evaluate(_study_content(), spec=spec)


def test_c_content_instance_revalidates_nested_observations() -> None:
    content = c.validate_fresh_c_content(_content_payload())
    data = content.report_data.model_copy(update={'observations': ()})
    forged = content.model_copy(update={'report_data': data})
    with pytest.raises(ValueError, match='观察|observation|字段|design'):
        c.validate_fresh_c_content(forged)


def test_blocker_cannot_publish_old_result_against_unclosed_current_snapshot(
    tmp_path: Path,
) -> None:
    kind = ReportKind.A
    spec = spec_yaml('A')
    snapshot = snapshot_for(kind)
    unit_id = applicable_critical_units(spec, snapshot)[0]
    result = real_blocked_result_for(spec, snapshot, unit_id)
    failed = tuple(failed_gate_unit(spec, row.unit_id, row.object_id,
                                    current_state='not_reported')
                   for row in result.unit_results if row.outcome.value == 'blocked')
    record = _make_record(kind, failed)
    workspace = prepare_workspace(tmp_path)
    with pytest.raises((ValueError, GateEvaluationError), match='穷举|快照|候选'):
        public_write_blocker_package(
            report_kind=kind, spec=spec,
            snapshot=snapshot.model_copy(update={'enumeration_complete': False}),
            gate_result=result, failed_units=failed, record=record, workspace_root=workspace,
        )
    assert not (workspace / 'blockers').exists()


@pytest.mark.parametrize('changed', (
    None, 'evidence_digest', 'spec_fingerprint', 'candidate_snapshot_digest',
    'result_key', 'evidence_snapshot_id', 'missing_identity', 'current_policy',
))
def test_research_gate_resume_checks_current_policy_and_snapshot_without_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed: str | None,
) -> None:
    from ci_workflow.application.run_service import (
        ContractConfigError,
        _research_gate_input_digest,
        _restored_research_gate_digest,
    )

    package, outcome = _ready_package_and_outcome(c)
    path = tmp_path / 'package.json'
    path.write_text(json.dumps(package.model_dump(mode='json')), encoding='utf-8')
    result = outcome.result
    outputs = {
        'evidence_digest': package.research_content_digest,
        'gate_passed': result.decision.value == 'passed',
        'failures': result.blocked_unit_ids,
    }
    stored_result = result
    content_digest = package.research_content_digest
    if changed == 'current_policy':
        spec = GateSpec.from_yaml(ROOT / 'policies/gates/C-v1.yaml')
        policy = tmp_path / 'changed-policy.yaml'
        policy.write_text(json.dumps(spec.model_copy(update={
            'units': tuple(unit.model_copy(update={'threshold': unit.threshold + 1})
                           for unit in spec.units),
        }).model_dump(mode='json')), encoding='utf-8')
        monkeypatch.setattr(c, '_C_GATE_SPEC_PATH', policy)
    elif changed == 'missing_identity':
        stored_result = result.model_copy(update={'spec_fingerprint': ''})
    elif changed == 'evidence_digest':
        content_digest = 'changed-identity'
        outputs[changed] = content_digest
    elif changed is not None:
        stored_result = result.model_copy(update={changed: 'changed-identity'})
    last_gate = {'outputs': outputs, 'input_digest': _research_gate_input_digest(
        'C', 1, content_digest, stored_result,
    )}
    replay_snapshot_id = ('changed-identity' if changed == 'evidence_snapshot_id'
                          else result.evidence_snapshot_id)
    contract = SimpleNamespace(project_id=PROJECT_ID, contract_version=1)
    if changed is None:
        assert _restored_research_gate_digest(
            path, 'C', contract, last_gate, evidence_snapshot_id=result.evidence_snapshot_id,
        ) == (
            _research_gate_input_digest('C', 1, package.research_content_digest, result)
        )
    else:
        with pytest.raises(ContractConfigError, match='变化|版本绑定'):
            _restored_research_gate_digest(
                path, 'C', contract, last_gate, evidence_snapshot_id=replay_snapshot_id,
            )
    assert not (tmp_path / 'snapshots').exists()
    assert not (tmp_path / 'state').exists()
