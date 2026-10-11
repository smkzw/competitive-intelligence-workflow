"""Isolated real-source operation candidate; never edit the full current34 project.

SQLite backup preserves actual accepted states, not an invented review. Copy only
the source closure and identity assets required for the four real consumers.
Initialize with the ordinary current API; subsequent operations use the real UI.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from ci_workflow.application.latest_delivery import read_current_delivery
from ci_workflow.application.project_service import create_project_workspace, verify_project_workspace
from ci_workflow.application.source_research_service import project_locked_a_public_provenance
from ci_workflow.application.user_fact_edit import UserFactEditService
from ci_workflow.domain.evidence import ContentBlob
from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
from ci_workflow.reports.common.identity_projection import load_identity_binding
from ci_workflow.storage.content_store import ContentAddressedStore, EvidenceRepository
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore
from ci_workflow.storage.sqlite import open_database

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / '.artifacts/1007-abc-current-integration-v1/working/project'
INPUT = ROOT / '.artifacts/1007-publication-real-consumers-v3'
OUT = ROOT / '.artifacts/1007-publication-current-chain-v1'
PROJECT = OUT / 'project'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    assert not OUT.exists(), 'Resume actual preparation; never overwrite or repeat a save'
    recipe = Path(__file__).with_name('build-publication-real-consumers-v1.py')
    spec = importlib.util.spec_from_file_location('existing_source_checks', recipe)
    assert spec and spec.loader
    checks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checks)
    before = checks.scientific_state()
    full_current = read_current_delivery(SOURCE)
    assert full_current and full_current.revision == 34
    receipt_path = INPUT / 'actual.json'
    assert sha(receipt_path) == 'd791ade5aba119c8a2de46ab95936e4d5677bf0b6fc7bb3d6f4666e129a9921c'
    receipt = json.loads(receipt_path.read_bytes())
    contract = verify_project_workspace(SOURCE, read_only=True).contract
    create_project_workspace(PROJECT, contract)
    with sqlite3.connect((SOURCE/'state/project.sqlite').as_uri()+'?mode=ro', uri=True) as db:
        with sqlite3.connect(PROJECT/'state/project.sqlite') as backup:
            db.backup(backup)
    source_store, target_store = ContentAddressedStore(SOURCE), ContentAddressedStore(PROJECT)
    copied: dict[str, dict] = {}

    def copy_blob(blob: ContentBlob) -> None:
        if blob.sha256 not in copied:
            actual = target_store.put_bytes(source_store.read_bytes(blob), media_type=blob.media_type)
            assert actual == blob
            copied[blob.sha256] = blob.model_dump(mode='json')

    def copy_references(value: object) -> None:
        if isinstance(value, dict):
            if {'sha256','relative_path','byte_size','media_type'} <= value.keys():
                copy_blob(ContentBlob.model_validate(value))
            else:
                for item in value.values():
                    copy_references(item)
        elif isinstance(value, list):
            for item in value:
                copy_references(item)

    repository = EvidenceRepository(SOURCE/'state/project.sqlite', source_store)

    def copy_source(version_id: str) -> None:
        with open_database(SOURCE/'state/project.sqlite') as db:
            version = repository._read_source_version(db, version_id)
            size = db.execute('SELECT byte_size FROM content_blobs WHERE content_sha256=?',
                              (version.content_sha256,)).fetchone()[0]
        copy_blob(ContentBlob(sha256=version.content_sha256, byte_size=size,
                              relative_path=version.content_relative_path, media_type=version.media_type))
        copy_references(version.model_dump(mode='json'))

    snapshot = LockedSnapshot.model_validate(receipt['consumer_snapshot'])
    closure = SnapshotStore(SOURCE).read(snapshot)
    destination = PROJECT / snapshot.relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE/snapshot.relative_path, destination)
    assert sha(destination) == snapshot.sha256
    copy_references(closure)
    for source in closure['closure']['sources']:
        copy_source(source['source_version_id'])
    binding = json.loads((INPUT/'A/data/identity-context.json').read_bytes())
    graph_blob = ContentBlob.model_validate(binding['graph_asset'])
    copy_blob(graph_blob)
    graph = json.loads(source_store.read_bytes(graph_blob))
    copy_references(graph)
    for fragment_id in graph['source_fragment_ids']:
        copy_source(repository.read_fragment(fragment_id).source_version_id)
    identity = load_identity_binding(PROJECT, binding)
    verify_project_workspace(PROJECT, read_only=True)
    data, inputs, sites = {}, {}, {}
    for code, model in [('A',ReportAPortalData),('B',ReportBPortalData)]:
        path = INPUT / f'report-{code.lower()}-data.json'
        assert sha(path) == receipt['files'][path.name]
        data[code] = model.model_validate_json(path.read_bytes())
        inputs[code] = PROJECT / 'inputs' / path.name
        inputs[code].parent.mkdir(exist_ok=True)
        shutil.copy2(path, inputs[code])
        sites[code] = PROJECT / 'reports' / code / 'publication-initial' / 'html'
    provenance = project_locked_a_public_provenance(PROJECT, data['A'], snapshot)
    used = {row.source_version_id for row in data['A'].efficacy}
    provenance = provenance.model_copy(update={'sources':tuple(
        source for source in provenance.sources if source.source_version_id in used)})
    render_report_a_site(data['A'], sites['A'], identity_context=identity, public_provenance=provenance)
    render_report_b_site(data['B'], sites['B'], identity_context=identity)
    with open_database(PROJECT/'state/project.sqlite') as db:
        versions = tuple(db.execute('SELECT fact_version_id FROM fact_versions WHERE fact_id=? '
                                   'AND review_state=?',(row['source_fact']['fact_id'],'accepted'))
                         .fetchone()[0] for row in data['B'].efficacy_views['facts'])
    assert len(set(versions)) == 4
    service = UserFactEditService(PROJECT)
    current = service.initialize_current_delivery(project_id=contract.project_id,
        report_sites=sites, report_data_paths=inputs, fact_version_ids=versions, created_at=datetime.now(UTC))
    facts = service.current_facts()
    assert len(facts) == 4
    for fact in facts.values():
        assert fact['review_state'] == 'accepted' and fact['normalized_value'] is None
        assert {row['report'] for row in fact['consumer_bindings']} == {'A','B'}
    assert checks.scientific_state() == before and read_current_delivery(SOURCE) == full_current
    result = {'state':'ISOLATED_REAL_SOURCE_CURRENT_PREPARED_NO_USER_SAVE',
        'current':current.model_dump(mode='json'),'facts':facts,
        'copied_assets':copied,'asset_bytes':sum(x['byte_size'] for x in copied.values()),
        'source_project_current_unchanged':True,'source_science':before,
        'actual_source_acceptance':'SQLite backup of existing accepted states; no adoption or state rewrite',
        'scope':'Four source cells/two studies/one compound. Not complete universe or full current34 replacement.',
        'input_receipt_sha256':sha(receipt_path),'recipe_sha256':sha(Path(__file__)),
        'pending':['actual UI save/undo/clear/undo','same-current A+B graph/table/source sync','configuration and static sharing']}
    (OUT/'preparation.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True))
    print(json.dumps({'state':result['state'],'facts':len(facts),'asset_bytes':result['asset_bytes']}))


if __name__ == '__main__':
    main()
