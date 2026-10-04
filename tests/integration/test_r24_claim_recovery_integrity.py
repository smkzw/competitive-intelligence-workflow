"""Restoration cannot change scientific claim semantics under a retained ID."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.application.source_research_service import ResearchClaim
from ci_workflow.storage.snapshot_store import SnapshotIntegrityError, SnapshotStore
from ci_workflow.storage.sqlite import open_database
from tests.integration.test_r24_research_claim_semantics import synthesis_payload
from tests.integration.test_review_r07_ingestion_invariants import _prepare


def _snapshot(tmp_path: Path):
    project, package, _ = _prepare(tmp_path / 'source')
    payload = synthesis_payload()
    payload.update(claim_id=package.claims[0].claim_id,
                   fact_ids=package.claims[0].fact_ids)
    claim = ResearchClaim.model_validate(payload)
    lineage = ingest_research_evidence(
        project_root=project,
        project_id=verify_project_workspace(project).contract.project_id,
        contract_version=1, report_kind='A', data_cutoff=package.data_cutoff,
        scientific_content_digest=hashlib.sha256(claim.model_dump_json().encode()).hexdigest(),
        created_at=package.scientific_review.reviewed_at, sources=package.sources,
        route_attempts=package.route_attempts, facts=package.facts,
        claims=(claim, *package.claims[1:]),
    )
    return project, lineage, SnapshotStore(project).read(lineage.evidence_snapshot)


@pytest.mark.parametrize('variant', [
    'missing_method', 'changed_method', 'changed_kind', 'changed_version',
    'missing_support', 'foreign_support', 'changed_claim_id', 'wrong_manifest_ids',
])
def test_restore_rejects_claim_contract_or_identity_drift_before_publishing(
    tmp_path: Path, variant: str,
) -> None:
    project, lineage, snapshot = _snapshot(tmp_path)
    original = (project / lineage.evidence_snapshot.relative_path).read_bytes()
    row = snapshot['closure']['claims'][0]
    if variant == 'missing_method':
        row['claim'].pop('synthesis_method_zh')
    elif variant == 'changed_method':
        row['claim']['synthesis_method_zh'] = '换用另一个科学方法。'
    elif variant == 'changed_kind':
        row['claim']['claim_kind'] = 'direct_evidence'
        row['claim'].pop('synthesis_method_zh')
        row['claim'].pop('ai_disclosure_label_zh')
    elif variant == 'changed_version':
        row['claim_version_id'] = 'claim-version-forged'
    elif variant == 'missing_support':
        row['fact_version_ids'] = []
    elif variant == 'foreign_support':
        row['claim']['fact_ids'] = ['outside-fact']
    elif variant == 'changed_claim_id':
        row['claim']['claim_id'] = 'different-logical-claim'
    else:
        snapshot['claim_version_ids'] = ['outside-claim-version']
    input_path = tmp_path / 'mutated-current.json'
    input_path.write_text(json.dumps(snapshot, ensure_ascii=False), encoding='utf-8')
    target = tmp_path / 'restore-target'
    with pytest.raises(SnapshotIntegrityError, match='声明'):
        SnapshotStore(target).restore_evidence_manifest(input_path)
    assert not target.exists()
    assert (project / lineage.evidence_snapshot.relative_path).read_bytes() == original


def test_restore_current_claim_preserves_method_kind_bindings_and_original_bytes(
    tmp_path: Path,
) -> None:
    project, lineage, snapshot = _snapshot(tmp_path)
    original_path = project / lineage.evidence_snapshot.relative_path
    original = original_path.read_bytes()
    target = tmp_path / 'restored'
    restored = SnapshotStore(target).restore_evidence_manifest(original_path)
    assert restored == lineage.evidence_snapshot
    assert SnapshotStore(target).read(restored) == snapshot
    assert (target / restored.relative_path).read_bytes() == original
    with open_database(target / 'state/project.sqlite') as database:
        rows = database.execute('SELECT claim_kind,review_state FROM claim_versions').fetchall()
    assert rows[0][0] == 'synthesis'
    assert {row[1] for row in rows} == {'candidate'}
    assert not (target / 'current.json').exists()
    assert original_path.read_bytes() == original
