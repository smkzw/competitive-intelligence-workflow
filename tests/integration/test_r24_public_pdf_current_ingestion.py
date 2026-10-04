"""Current official retrieval is evidence, not a fabricated first-disclosure date."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from ci_workflow.application.fresh_b_research_package import FreshBResearchContent
from ci_workflow.application.fresh_c_research_package import FreshCResearchContent
from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.source_research_service import (
    FreshAResearchContent,
    ResearchClaim,
    ResearchFact,
    SourceCapture,
)
from ci_workflow.sources.connectors.public_pdf_availability import (
    PdfHttpPage,
    PublicPdfAvailabilityError,
    capture_public_pdf_availability,
    verify_public_pdf_availability,
)
from ci_workflow.storage.content_store import ContentAddressedStore, EvidenceRepository
from ci_workflow.storage.migrations import apply_migrations
from ci_workflow.storage.snapshot_store import SnapshotStore
from ci_workflow.storage.source_derivation import capture_pdf_page_text
from ci_workflow.storage.sqlite import open_database
from tests.integration.test_fresh_a_research_package import _package_payload as a_payload
from tests.integration.test_fresh_c_research_package import _content_payload as c_payload
from tests.integration.test_r24_pdf_page_source_proof import _locator, _pdf_pages
from tests.unit.reports.b.test_fresh_b_research_package import _package_payload as b_payload

URL = 'https://cdn.clinicaltrials.gov/large-docs/39/NCT02264639/Prot_000.pdf'
OBS = datetime(2026, 7, 1, tzinfo=UTC)


def _source(root: Path, observed: datetime = OBS) -> SourceCapture:
    raw = _pdf_pages([['Synthetic alpha: 42 participants']])
    text, derivation = capture_pdf_page_text(root, raw, page=1)
    result = capture_public_pdf_availability(
        root, URL, derivation.raw_asset,
        transport=lambda url, timeout, max_bytes: PdfHttpPage(
            200, 'application/pdf', len(raw), raw, url,
        ), clock=lambda: observed,
    )
    assert result.witness is not None
    return SourceCapture(
        source_id='synthetic-current-pdf', route_id='official-pdf', source_type='protocol_sap',
        title='Synthetic test only', url=URL, query_or_identifier='synthetic', language='en',
        access_method='official_public_get', media_type='application/pdf', content_text=text,
        text_derivation=derivation, acquired_at=observed, published_at=None,
        effective_at=None, first_disclosed_at=None, locator=_locator(1, 'Synthetic alpha'),
        public_pdf_availability=result.witness,
    )


def _ingest(root: Path, source: SourceCapture, *, cutoff: datetime | None = None,
            request_id: str = 'first'):
    fact = ResearchFact(
        fact_id='synthetic-alpha', row_ref='design:alpha', entity_id='synthetic-study',
        entity_type='trial', canonical_name='Synthetic study', field_id='sample_size',
        raw_value='42', normalized_value=None, disclosure_state='reported_value',
        source_id=source.source_id, locator=_locator(1, 'Synthetic alpha'),
        original_text='Synthetic alpha: 42 participants',
    )
    claim = ResearchClaim(claim_id='synthetic-claim', claim_text='Synthetic only',
                          claim_kind='direct_evidence', fact_ids=(fact.fact_id,))
    return ingest_research_evidence(
        project_root=root, project_id='synthetic-project', contract_version=1, report_kind='C',
        data_cutoff=cutoff or source.acquired_at, scientific_content_digest='a' * 64,
        created_at=source.acquired_at, sources=(source,), route_attempts=(), facts=(fact,),
        claims=(claim,), request_id=request_id,
    )


def test_capture_persists_receipt_and_checks_cutoff_future_and_tamper(tmp_path: Path) -> None:
    source = _source(tmp_path)
    witness = source.public_pdf_availability
    assert witness is not None and witness.receipt_asset is not None
    store = ContentAddressedStore(tmp_path)
    receipt = json.loads(store.read_bytes(witness.receipt_asset))
    assert receipt['observed_available_at'] == OBS.isoformat().replace('+00:00', 'Z')
    assert receipt['request_started_at'] == receipt['observed_available_at']
    verify_public_pdf_availability(tmp_path, witness, URL, witness.raw_asset, OBS)
    with pytest.raises(PublicPdfAvailabilityError):
        verify_public_pdf_availability(tmp_path, witness, URL, witness.raw_asset,
                                       OBS - timedelta(microseconds=1))
    future = witness.model_copy(update={'observed_available_at': datetime.now(UTC)
                                       + timedelta(days=1)})
    with pytest.raises(PublicPdfAvailabilityError):
        verify_public_pdf_availability(tmp_path, future, URL, witness.raw_asset,
                                       future.observed_available_at)
    path = tmp_path / witness.receipt_asset.relative_path
    path.write_bytes(b'{}')
    with pytest.raises(PublicPdfAvailabilityError):
        verify_public_pdf_availability(tmp_path, witness, URL, witness.raw_asset, OBS)


@pytest.mark.parametrize('kind', ['A', 'B', 'C'])
def test_abc_temporal_gate_accepts_current_proof_but_not_unknown_or_backdated(
    tmp_path: Path, kind: str,
) -> None:
    factory, model = {'A': (a_payload, FreshAResearchContent),
                      'B': (b_payload, FreshBResearchContent),
                      'C': (c_payload, FreshCResearchContent)}[kind]
    payload = factory()
    payload.pop('scientific_review', None)
    current = _source(tmp_path)
    payload['sources'] = [*payload['sources'], current.model_dump(mode='json')]
    content = model.model_validate(payload)
    assert content.sources[-1].first_disclosed_at is None
    assert current.is_available_by(content.data_cutoff)
    late = _source(tmp_path, content.data_cutoff + timedelta(seconds=1))
    payload['sources'][-1] = late.model_dump(mode='json')
    with pytest.raises(ValueError):
        model.model_validate(payload)
    payload['sources'][-1] = current.model_dump(mode='json', exclude={'public_pdf_availability'})
    with pytest.raises(ValueError):
        model.model_validate(payload)


@pytest.mark.parametrize('field,value', [('url', URL.replace('Prot_000', 'SAP_000')),
                                        ('acquired_at', OBS - timedelta(seconds=1))])
def test_source_proof_must_bind_actual_raw_url_and_acquisition(
    tmp_path: Path, field: str, value: object,
) -> None:
    payload = _source(tmp_path).model_dump(mode='json')
    payload[field] = value
    with pytest.raises(ValidationError):
        SourceCapture.model_validate(payload)


def test_receipt_reopens_before_any_ingestion_write_and_snapshot_restores_it(
    tmp_path: Path,
) -> None:
    root = tmp_path / 'original'
    db = root / 'state/project.sqlite'
    apply_migrations(db)
    source = _source(root)
    witness = source.public_pdf_availability
    assert witness is not None and witness.receipt_asset is not None
    receipt_path = root / witness.receipt_asset.relative_path
    original = receipt_path.read_bytes()
    receipt_path.write_bytes(b'{}')
    with pytest.raises(PublicPdfAvailabilityError):
        _ingest(root, source)
    with open_database(db) as conn:
        for table in ('source_versions', 'evidence_fragments', 'fact_versions',
                      'source_acquisition_attempts'):
            assert conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0
    receipt_path.write_bytes(original)
    lineage = _ingest(root, source)
    restored_root = tmp_path / 'restored'
    SnapshotStore(restored_root).restore_evidence_manifest(
        root / lineage.evidence_snapshot.relative_path,
    )
    assert ContentAddressedStore(restored_root).read_bytes(witness.receipt_asset) == original
    assert _ingest(restored_root, source).source_version_ids == lineage.source_version_ids


def test_repeat_get_adds_acquisition_without_churning_source_or_fact_version(
    tmp_path: Path,
) -> None:
    apply_migrations(tmp_path / 'state/project.sqlite')
    first_source = _source(tmp_path)
    first = _ingest(tmp_path, first_source)
    second_source = _source(tmp_path, OBS + timedelta(minutes=5))
    second = _ingest(tmp_path, second_source, request_id='second')
    assert first.source_version_ids == second.source_version_ids
    assert first.fact_version_ids == second.fact_version_ids
    with open_database(tmp_path / 'state/project.sqlite') as conn:
        assert conn.execute('SELECT COUNT(*) FROM source_acquisition_attempts').fetchone()[0] == 2
        record = EvidenceRepository(tmp_path / 'state/project.sqlite',
                                    ContentAddressedStore(tmp_path))._read_source_version(
                                        conn, first.source_version_ids[0])
    assert record.first_disclosed_at.value is None
    assert record.acquired_at == first_source.acquired_at
    assert not record.first_disclosed_at.is_known_by(second_source.acquired_at)
