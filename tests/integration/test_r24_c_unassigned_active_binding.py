"""Explicit null C identity is comparable; it is never a missing proof bypass."""
import json
from pathlib import Path

import pytest

from ci_workflow.renderers.portal.active_fact_projection import (
    ActiveFact,
    ActiveFactBinding,
    validate_active_fact_binding,
)
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    active_fact_binding_for_c,
)

ROOT = Path(__file__).resolve().parents[2]


def _known() -> tuple[ReportCPortalData, dict]:
    data = ReportCPortalData.model_validate_json(
        (ROOT / 'fixtures/acceptance/full-matrix-v1/inputs/report-c-data.json').read_bytes(),
    )
    return data, active_fact_binding_for_c(data, data.observations[0].row_id).model_dump()


def _unassigned() -> tuple[ReportCPortalData, ActiveFactBinding]:
    data, binding = _known()
    payload = data.model_dump(mode='json')
    payload['products'] = []
    payload['trials'] = [{**row, 'product_id': None} for row in payload['trials']]
    payload['observations'] = [{**row, 'product_id': None} for row in payload['observations']]
    report = ReportCPortalData.model_validate(payload)
    actual = active_fact_binding_for_c(report, binding['row_id'])
    assert actual.product_id is None and actual.drug_name is None
    return report, actual


def _fact(binding: ActiveFactBinding) -> ActiveFact:
    extra = binding.model_dump(exclude={
        'report', 'collection', 'row_id', 'source_version_id', 'source_pointer',
        'original_row_sha256',
    })
    return ActiveFact(
        fact_id='source-fact', fact_version_id='source-fact-version', field_id='c.design',
        primary_fragment_id='fragment', source_version_id=binding.source_version_id,
        source_locator=binding.source_pointer, source_quote='原始来源', **extra,
    )


def test_c_explicit_null_binding_and_same_fact_proof() -> None:
    _, binding = _unassigned()
    fact = _fact(binding)
    assert validate_active_fact_binding(fact, binding, binding) == binding
    assert fact.model_extra['product_id'] is None
    assert json.loads(binding.model_dump_json())['drug_name'] is None


@pytest.mark.parametrize('field', ('product_id', 'drug_name'))
def test_missing_nullable_identity_is_not_explicit_null(field: str) -> None:
    _, binding = _unassigned()
    payload = _fact(binding).model_dump(mode='json')
    payload.pop(field)
    with pytest.raises(ValueError, match='身份.*缺少|缺少.*身份'):
        validate_active_fact_binding(ActiveFact.model_validate(payload), binding, binding)


def test_known_null_binding_drift_is_rejected() -> None:
    _, unknown = _unassigned()
    _, known_payload = _known()
    known = ActiveFactBinding.model_validate(known_payload)
    with pytest.raises(ValueError, match='原消费者科学身份不一致'):
        validate_active_fact_binding(_fact(unknown), known, unknown)


@pytest.mark.parametrize(('report', 'collection'), (('A', 'efficacy'), ('B', 'efficacy')))
def test_a_b_product_requirement_not_relaxed(report: str, collection: str) -> None:
    _, known = _known()
    with pytest.raises(ValueError):
        ActiveFactBinding.model_validate({**known, 'report': report, 'collection': collection,
                                          'product_id': None, 'drug_name': None})


def test_nullable_binding_keys_required_and_pair_cannot_be_half_unknown() -> None:
    _, known = _known()
    with pytest.raises(ValueError):
        ActiveFactBinding.model_validate({**known, 'product_id': None})
    payload = {**known, 'product_id': None, 'drug_name': None}
    payload.pop('drug_name')
    with pytest.raises(ValueError):
        ActiveFactBinding.model_validate(payload)


def test_real_source_null_consumer_registration_and_original_proof(tmp_path: Path) -> None:
    from datetime import timedelta

    from ci_workflow.application.c_portal_consumer_registry import register_c_source_consumers
    from ci_workflow.application.portal_consumer_binding_recovery import (
        _CPortalOriginalProof,
        export_verified_consumer_bindings,
        recover_verified_consumer_bindings,
    )
    from ci_workflow.renderers.portal.active_fact_projection import canonical_sha256
    from ci_workflow.storage.snapshot_store import SnapshotStore
    from tests.integration.test_r24_c_source_consumers import _AT, _candidate

    root, snapshot, known, versions, sources = _candidate(tmp_path)
    payload = known.model_dump(mode='json')
    payload['products'] = []
    payload['trials'] = [{**row, 'product_id': None} for row in payload['trials']]
    payload['observations'] = [{**row, 'product_id': None} for row in payload['observations']]
    report = ReportCPortalData.model_validate(payload)
    before = known.model_dump_json()
    bindings = register_c_source_consumers(
        root, snapshot, report, versions, sources, registered_at=_AT + timedelta(seconds=1),
    )
    assert len(bindings) == len(report.observations) == 85
    assert all(binding.product_id is None and binding.drug_name is None for binding in bindings)
    repeated = register_c_source_consumers(
        root, snapshot, report, versions, sources, registered_at=_AT + timedelta(seconds=2),
    )
    assert repeated == bindings and known.model_dump_json() == before
    proof = _CPortalOriginalProof(report, canonical_sha256(report.model_dump(mode='json')))
    for row in report.observations:
        proof.require_product_trial_alignment(row)
        assert proof.original_binding(row.row_id).product_id is None
    assert not (root / 'reports/current.json').exists()
    original = tmp_path / 'original-null-c.json'
    original.write_text(report.model_dump_json(), encoding='utf-8')
    sidecar = tmp_path / 'null-c-consumers.json'
    exported = export_verified_consumer_bindings(root, snapshot, sidecar,
                                                c_report_data_path=original)
    assert exported == bindings
    restored = tmp_path / 'restored-null-c'
    SnapshotStore(restored).restore_evidence_manifest(root / snapshot.relative_path)
    recovered = recover_verified_consumer_bindings(restored, sidecar,
                                                   c_report_data_path=original)
    assert recovered == exported
    assert recover_verified_consumer_bindings(restored, sidecar,
                                              c_report_data_path=original) == recovered
    assert not (restored / 'reports/current.json').exists()
