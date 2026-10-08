"""Unreviewed native clauses must persist through the real evidence boundary."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ci_workflow.storage.content_store import ContentAddressedStore, EvidenceRepository
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore
from ci_workflow.storage.sqlite import open_database
from tests.integration.test_r24_pdf_page_source_proof import _pdf_pages

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 3, 15, tzinfo=UTC)


def _materialize(**kwargs):
    module = "tools.materialize_pdf_scope_candidate"
    assert importlib.util.find_spec(module) is not None, "Native clause ingestion is not connected"
    from tools.materialize_pdf_scope_candidate import materialize

    return materialize(**kwargs)


def _fixture(tmp_path: Path) -> dict:
    source = tmp_path / "source"
    raw = _pdf_pages([["Synthetic alpha: 42 participants", "Synthetic beta: 57 participants"],
                      ["Synthetic gamma: long-term safety"]])
    blob = ContentAddressedStore(source).put_bytes(raw, media_type="application/pdf")
    acquisition = {"documents": [{
        "name": "synthetic.pdf", "raw_asset": blob.model_dump(mode="json"),
        "registered_url": "https://example.org/synthetic.pdf",
        "local_download_completed_at": "2026-10-03T09:48:54+00:00",
        "timestamp_kind": "local_file_mtime_not_http_publication_date",
    }]}
    proposal = {"accepted": False, "status": "proposal_only", "documents": [{
        "filename": "synthetic.pdf", "raw_sha256": blob.sha256,
        "url": "https://example.org/synthetic.pdf", "trial_id": "SYNTHETIC-ONLY",
    }], "atoms": [{
        "proposal_id": f"synthetic-{index}", "document_filename": "synthetic.pdf",
        "document_raw_sha256": blob.sha256, "physical_page": page,
        "original_quote": quote, "trial_id": "SYNTHETIC-ONLY",
        "scientific_scope": {"synthetic": True},
        "conflict_links": ["synthetic-unresolved"] if index == 0 else [],
    } for index, (page, quote) in enumerate([
        (1, "Synthetic alpha: 42 participants"), (1, "Synthetic beta: 57 participants"),
        (2, "Synthetic gamma: long-term safety"),
    ])], "conflicts": [{"conflict_id": "synthetic-unresolved", "resolution": "unresolved"}],
        "gaps": [{"gap_id": "synthetic-not-a-real-study"}]}
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(json.dumps(proposal))
    acquisition_blob = ContentAddressedStore(source).put_bytes(
        json.dumps(acquisition).encode(), media_type="application/json",
    )
    return dict(source_root=source, proposal_path=proposal_path,
                proposal_sha256=hashlib.sha256(proposal_path.read_bytes()).hexdigest(),
                acquisition_asset=acquisition_blob, output=tmp_path / "candidate", observed_at=NOW)


def test_three_clauses_reopen_after_move_with_one_raw_pdf_and_no_acceptance(tmp_path: Path):
    args = _fixture(tmp_path)
    manifest = _materialize(**args)
    output = args["output"]
    moved = tmp_path / "moved-candidate"
    shutil.move(str(output), moved)
    snapshot = LockedSnapshot.model_validate(manifest["evidence_snapshot"])
    closure = SnapshotStore(moved).read(snapshot)["closure"]
    assert len(closure["facts"]) == 3
    assert len(closure["sources"]) == 2
    assert sum(s["raw_asset_b64"] is not None for s in closure["sources"]) == 1
    repository = EvidenceRepository(moved / "state/project.sqlite", ContentAddressedStore(moved))
    for fact in closure["facts"]:
        fragment = repository.read_fragment(fact["primary_fragment_id"])
        repository.verify_reopened_fragment_record(
            fragment, reopened_original_text=fragment.original_text,
            source_version_id=fragment.source_version_id,
        )
        assert fact["review_state"] == "candidate"
    assert not manifest["accepted"]
    assert not (moved / "reports/current.json").exists()
    with open_database(moved / "state/project.sqlite") as db:
        assert db.execute("SELECT COUNT(*) FROM source_portal_consumer_bindings").fetchone()[0] == 0


def test_local_acquisition_is_preserved_and_not_turned_into_publication(tmp_path: Path):
    manifest = _materialize(**_fixture(tmp_path))
    closure = SnapshotStore(tmp_path / "candidate").read(
        LockedSnapshot.model_validate(manifest["evidence_snapshot"]),
    )["closure"]
    for source in closure["sources"]:
        capture = source["capture"]
        assert capture["acquired_at"].startswith("2026-10-03T09:48:54")
        assert capture["first_disclosed_at"] is None
        assert capture["published_at"] is None
        assert capture["effective_at"] is None
        assert capture["access_method"] == "saved_public_pdf_local_acquisition_replay"
    assert manifest["historical_cutoff_eligible"] is False
    assert all("截止日适格" not in r["completeness_checks"] for r in closure["receipts"])


@pytest.mark.parametrize("padding", [" ", "\n", "\t"])
def test_boundary_whitespace_uses_replayed_quote_without_rewriting_proposal(tmp_path: Path,
                                                                          padding: str):
    args = _fixture(tmp_path)
    proposal_path = args["proposal_path"]
    proposal = json.loads(proposal_path.read_bytes())
    original = proposal["atoms"][0]["original_quote"]
    proposal["atoms"][0]["original_quote"] = padding + original + padding
    proposal_path.write_text(json.dumps(proposal))
    pinned = proposal_path.read_bytes()
    args["proposal_sha256"] = hashlib.sha256(pinned).hexdigest()

    manifest = _materialize(**args)
    closure = SnapshotStore(args["output"]).read(
        LockedSnapshot.model_validate(manifest["evidence_snapshot"]),
    )["closure"]
    fact = next(f["fact"] for f in closure["facts"] if f["fact"]["fact_id"] == "synthetic-0")
    assert fact["original_text"] == fact["raw_value"] == original
    assert proposal_path.read_bytes() == pinned
    store = ContentAddressedStore(args["output"])
    from ci_workflow.domain.evidence import ContentBlob

    assert store.read_bytes(ContentBlob.model_validate(manifest["proposal_asset"])) == pinned
    assert not manifest["accepted"]


def test_internal_quote_change_is_not_corrected_as_boundary_whitespace(tmp_path: Path):
    args = _fixture(tmp_path)
    proposal_path = args["proposal_path"]
    proposal = json.loads(proposal_path.read_bytes())
    proposal["atoms"][0]["original_quote"] = "Synthetic alpha: 43 participants "
    proposal_path.write_text(json.dumps(proposal))
    args["proposal_sha256"] = hashlib.sha256(proposal_path.read_bytes()).hexdigest()
    with pytest.raises(ValueError):
        _materialize(**args)
    assert not args["output"].exists()


@pytest.mark.parametrize("damage", ["wrong_page", "wrong_pdf", "changed_proposal"])
def test_bad_source_or_page_fails_before_output_is_created(tmp_path: Path, damage: str):
    args = _fixture(tmp_path)
    path = args["proposal_path"]
    proposal = json.loads(path.read_text())
    if damage == "wrong_page":
        proposal["atoms"][0]["physical_page"] = 2
    elif damage == "wrong_pdf":
        proposal["atoms"][0]["document_raw_sha256"] = "a" * 64
    else:
        proposal["unexpected"] = True
    path.write_text(json.dumps(proposal))
    if damage != "changed_proposal":
        args["proposal_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError):
        _materialize(**args)
    assert not args["output"].exists()


def test_existing_candidate_is_never_replaced(tmp_path: Path):
    args = _fixture(tmp_path)
    args["output"].mkdir()
    sentinel = args["output"] / "keep.txt"
    sentinel.write_text("preserve unrelated bytes")
    with pytest.raises(ValueError, match="fresh"):
        _materialize(**args)
    assert sentinel.read_text() == "preserve unrelated bytes"


def test_real_fixed_64_clause_proposal_reopens_without_report_consumers(tmp_path: Path):
    from ci_workflow.domain.evidence import ContentBlob

    proposal = ROOT / ".artifacts/r24-150-pdf-complete-scope-20261003/proposal-v6.json"
    acquisition_root = ROOT / ".artifacts/r24-96-c-public-documents-20261003"
    acquisition_sha = "00802de9d3f459b0331f70c207dc1beb2c420264cd6e9df948b3d39cb93e7234"
    relative = f"evidence/raw/sha256/00/{acquisition_sha}.bin"
    acquired = acquisition_root / relative
    manifest = _materialize(
        source_root=acquisition_root, proposal_path=proposal,
        proposal_sha256="e152c0c3e3a10dd5842b0aa71c8d0fb2b7b68821bf0c8822e635597ed93b349e",
        acquisition_asset=ContentBlob(sha256=acquisition_sha, relative_path=relative,
                                      byte_size=acquired.stat().st_size,
                                      media_type="application/json"),
        output=tmp_path / "real-candidate", observed_at=NOW,
    )
    assert manifest["counts"]["clauses"] == 64
    assert manifest["counts"]["raw_documents"] == 4
    assert manifest["counts"]["reopened_clauses"] == 64
    assert manifest["counts"]["accepted_facts"] == 0
    assert manifest["counts"]["consumer_bindings"] == 0


def _official_fixture(tmp_path: Path) -> dict:
    from ci_workflow.sources.connectors.public_pdf_availability import (
        PdfHttpPage,
        capture_public_pdf_availability,
    )

    args = _fixture(tmp_path)
    store = ContentAddressedStore(args['source_root'])
    acquisition = json.loads(store.read_bytes(args['acquisition_asset']))
    proposal = json.loads(args['proposal_path'].read_bytes())
    url = 'https://cdn.clinicaltrials.gov/large-docs/39/NCT02264639/Prot_000.pdf'
    acquisition['documents'][0]['registered_url'] = url
    proposal['documents'][0]['url'] = url
    args['proposal_path'].write_text(json.dumps(proposal))
    args['proposal_sha256'] = hashlib.sha256(args['proposal_path'].read_bytes()).hexdigest()
    args['acquisition_asset'] = store.put_bytes(json.dumps(acquisition).encode(),
                                               media_type='application/json')
    from ci_workflow.domain.evidence import ContentBlob

    raw_blob = ContentBlob.model_validate(acquisition['documents'][0]['raw_asset'])
    raw = store.read_bytes(raw_blob)
    capture = capture_public_pdf_availability(
        args['source_root'], url, raw_blob,
        transport=lambda url, timeout, max_bytes: PdfHttpPage(
            200, 'application/pdf', len(raw), raw, url,
        ), clock=lambda: NOW,
    )
    payload = {'records': [{'filename': 'synthetic.pdf',
                            'capture': capture.model_dump(mode='json')}],
               'proposal_sha256': args['proposal_sha256']}
    manifest_path = tmp_path / 'availability-manifest.json'
    manifest_path.write_text(json.dumps(payload))
    args['availability_root'] = args['source_root']
    args['availability_manifest'] = manifest_path
    args['availability_sha256'] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    return args


def test_official_receipt_persists_all_page_proofs_without_churning_source(tmp_path: Path):
    args = _official_fixture(tmp_path)
    local_args = {k: v for k, v in args.items() if not k.startswith('availability_')}
    local_args['output'] = tmp_path / 'local'
    local = _materialize(**local_args)
    current = _materialize(**args)
    assert current['source_version_ids'] == local['source_version_ids']
    assert current['fact_version_by_ref'] == local['fact_version_by_ref']
    assert current['current_availability_eligible'] is True
    assert current['historical_cutoff_eligible'] is False
    closure = SnapshotStore(args['output']).read(
        LockedSnapshot.model_validate(current['evidence_snapshot']),
    )['closure']
    assert all(s['capture']['first_disclosed_at'] is None for s in closure['sources'])
    assert all(s['availability_receipt_b64'] for s in closure['sources'])
    assert current['counts']['accepted_facts'] == current['counts']['consumer_bindings'] == 0


@pytest.mark.parametrize('damage', ['receipt', 'manifest_hash', 'earlier_cutoff'])
def test_official_receipt_failure_is_closed_before_candidate_creation(tmp_path: Path, damage: str):
    args = _official_fixture(tmp_path)
    if damage == 'receipt':
        payload = json.loads(args['availability_manifest'].read_bytes())
        relative = payload['records'][0]['capture']['witness']['receipt_asset']['relative_path']
        (args['source_root'] / relative).write_bytes(b'{}')
    elif damage == 'manifest_hash':
        args['availability_sha256'] = 'f' * 64
    else:
        from datetime import timedelta

        args['observed_at'] = NOW - timedelta(seconds=1)
    with pytest.raises(ValueError):
        _materialize(**args)
    assert not args['output'].exists()
