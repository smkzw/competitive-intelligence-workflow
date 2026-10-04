"""Shared research claims keep explicit source/synthesis/calculation semantics."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.application.source_research_service import ResearchClaim
from ci_workflow.domain.ids import stable_id
from ci_workflow.storage.snapshot_store import SnapshotStore
from ci_workflow.storage.sqlite import open_database
from tests.integration.test_review_r07_ingestion_invariants import _prepare


def synthesis_payload() -> dict[str, object]:
    return {
        'claim_id': 'claim-context', 'claim_text': 'AI 综合判断：跨原文段落关联结局与统计方法。',
        'claim_kind': 'synthesis', 'fact_ids': ['fact-context'],
        'synthesis_method_zh': '核对结局段、方法段及图注；保留不同统计程序，不重算结论。',
        'ai_disclosure_label_zh': 'AI 综合判断',
    }


def test_synthesis_supports_explicit_method_and_disclosure() -> None:
    claim = ResearchClaim.model_validate(synthesis_payload())
    serialized = claim.model_dump(mode='json')
    assert serialized['synthesis_method_zh'] == synthesis_payload()['synthesis_method_zh']
    assert serialized['ai_disclosure_label_zh'] == 'AI 综合判断'


@pytest.mark.parametrize('variant', ['no_method', 'blank_method', 'no_label', 'no_prefix'])
def test_synthesis_requires_all_explicit_semantics(variant: str) -> None:
    payload = synthesis_payload()
    if variant == 'no_method':
        payload.pop('synthesis_method_zh')
        payload.pop('ai_disclosure_label_zh')
    elif variant == 'blank_method':
        payload['synthesis_method_zh'] = '  '
    elif variant == 'no_label':
        payload.pop('ai_disclosure_label_zh')
    else:
        payload['claim_text'] = '跨原文段落关联结局与统计方法。'
    with pytest.raises(ValueError):
        ResearchClaim.model_validate(payload)


def test_calculation_kind_without_calculation_is_rejected() -> None:
    with pytest.raises(ValueError):
        ResearchClaim(claim_id='claim-calc', claim_text='不得伪造计算',
                      claim_kind='deterministic_calculation', fact_ids=('fact-a',))


def test_direct_claim_preserves_legacy_json_shape() -> None:
    claim = ResearchClaim(claim_id='claim-direct', claim_text='来源原文',
                          claim_kind='direct_evidence', fact_ids=('fact-a',))
    assert claim.model_dump(mode='json') == {
        'claim_id': 'claim-direct', 'claim_text': '来源原文',
        'claim_kind': 'direct_evidence', 'fact_ids': ['fact-a'],
    }


def test_direct_claim_cannot_smuggle_ai_method_fields() -> None:
    payload = synthesis_payload()
    payload['claim_kind'] = 'direct_evidence'
    with pytest.raises(ValueError):
        ResearchClaim.model_validate(payload)


def test_method_change_forms_new_claim_version_without_mutating_prior(
    tmp_path: Path,
) -> None:
    project, package, _ = _prepare(tmp_path)
    contract = verify_project_workspace(project).contract
    original = package.claims[0]
    payload = synthesis_payload()
    payload.update(claim_id=original.claim_id, fact_ids=original.fact_ids)
    first_claim = ResearchClaim.model_validate(payload)
    second_claim = ResearchClaim.model_validate({
        **payload, 'synthesis_method_zh': '重新核对方法和原文；不扩展人群、时间窗或统计程序。',
    })

    def ingest(claim: ResearchClaim):
        return ingest_research_evidence(
            project_root=project, project_id=contract.project_id, contract_version=1,
            report_kind='A', data_cutoff=package.data_cutoff,
            scientific_content_digest=hashlib.sha256(claim.model_dump_json().encode()).hexdigest(),
            created_at=package.scientific_review.reviewed_at, sources=package.sources,
            route_attempts=package.route_attempts, facts=package.facts,
            claims=(claim, *package.claims[1:]),
        )

    first = ingest(first_claim)
    first_bytes = (project / first.evidence_snapshot.relative_path).read_bytes()
    second = ingest(second_claim)
    repeated = ingest(second_claim)
    assert first.claim_version_ids[0] != second.claim_version_ids[0]
    assert second == repeated
    assert first.fact_version_ids == second.fact_version_ids
    assert (project / first.evidence_snapshot.relative_path).read_bytes() == first_bytes
    snapshot = SnapshotStore(project).read(second.evidence_snapshot)
    stored_claim = snapshot['closure']['claims'][0]['claim']
    assert stored_claim['synthesis_method_zh'] == second_claim.model_dump()['synthesis_method_zh']
    assert snapshot['closure']['claims'][0]['claim']['ai_disclosure_label_zh'] == 'AI 综合判断'
    with open_database(project / 'state/project.sqlite') as database:
        states = database.execute(
            'SELECT claim_kind FROM claim_versions WHERE claim_id=?', (original.claim_id,),
        ).fetchall()
    assert len(states) == 2
    assert all(row[0] == 'synthesis' for row in states)
    assert not (project / 'current.json').exists()


def test_synthesis_kind_does_not_reuse_direct_version(tmp_path: Path) -> None:
    project, package, _ = _prepare(tmp_path)
    contract = verify_project_workspace(project).contract
    original = package.claims[0]
    payload = synthesis_payload()
    payload.update(claim_id=original.claim_id, fact_ids=original.fact_ids)
    synthesis = ResearchClaim.model_validate(payload)
    direct = ResearchClaim(claim_id=synthesis.claim_id, claim_text=synthesis.claim_text,
                           claim_kind='direct_evidence', fact_ids=synthesis.fact_ids)
    results = []
    for claim in (direct, synthesis):
        results.append(ingest_research_evidence(
            project_root=project, project_id=contract.project_id, contract_version=1,
            report_kind='A', data_cutoff=package.data_cutoff,
            scientific_content_digest=hashlib.sha256(claim.model_dump_json().encode()).hexdigest(),
            created_at=package.scientific_review.reviewed_at, sources=package.sources,
            route_attempts=package.route_attempts, facts=package.facts,
            claims=(claim, *package.claims[1:]),
        ))
    assert results[0].claim_version_ids[0] != results[1].claim_version_ids[0]
    with open_database(project / 'state/project.sqlite') as database:
        rows = database.execute('SELECT claim_kind FROM claim_versions WHERE claim_id=?',
                                (original.claim_id,)).fetchall()
    assert {r[0] for r in rows} == {'direct_evidence', 'synthesis'}


def test_direct_claim_keeps_existing_content_addressed_version(tmp_path: Path) -> None:
    project, package, digest = _prepare(tmp_path)
    contract = verify_project_workspace(project).contract
    lineage = ingest_research_evidence(
        project_root=project, project_id=contract.project_id, contract_version=1,
        report_kind='A', data_cutoff=package.data_cutoff, scientific_content_digest=digest,
        created_at=package.scientific_review.reviewed_at, sources=package.sources,
        route_attempts=package.route_attempts, facts=package.facts, claims=package.claims,
    )
    for claim, version in zip(package.claims, lineage.claim_version_ids, strict=True):
        expected = stable_id('claim-version', claim.claim_id, claim.claim_text,
                             *(lineage.fact_version_by_ref[f] for f in claim.fact_ids))
        assert version == expected
