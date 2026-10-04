"""Page proof must survive the ordinary ingestion/reopen boundary, not only a helper."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from ci_workflow.application.fresh_research_ingestion import (
    ResearchIngestionError,
    ingest_research_evidence,
)
from ci_workflow.application.source_research_service import (
    ResearchClaim,
    ResearchFact,
    SourceCapture,
)
from ci_workflow.domain.evidence import SourceTextDerivation
from ci_workflow.storage.content_store import ContentAddressedStore, EvidenceRepository
from ci_workflow.storage.migrations import apply_migrations
from ci_workflow.storage.source_derivation import (
    SourceDerivationError,
    capture_pdf_page_text,
    capture_source_text,
    verify_source_text_derivation,
)
from ci_workflow.storage.sqlite import open_database
from tests.integration.test_r24_pdf_page_source_proof import _locator, _pdf_pages

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("field", ["page", "page_count"])
def test_legacy_pdf_cannot_carry_half_a_page_scope(tmp_path: Path, field: str) -> None:
    _, legacy = capture_source_text(
        tmp_path, _pdf_pages([["Synthetic page"]]), media_type="application/pdf",
    )
    with pytest.raises(ValidationError):
        SourceTextDerivation.model_validate({**legacy.model_dump(mode="json"), field: 1})


@pytest.mark.parametrize("field", ["page", "page_count"])
def test_boolean_is_not_a_typed_page_number(tmp_path: Path, field: str) -> None:
    _, receipt = capture_pdf_page_text(tmp_path, _pdf_pages([["Synthetic page"]]), page=1)
    with pytest.raises(ValidationError):
        SourceTextDerivation.model_validate({**receipt.model_dump(mode="json"), field: True})


def test_capture_rejects_boolean_before_creating_evidence(tmp_path: Path) -> None:
    with pytest.raises(SourceDerivationError):
        capture_pdf_page_text(tmp_path, _pdf_pages([["Synthetic page"]]), page=True)
    assert not (tmp_path / "evidence").exists()


@pytest.mark.parametrize("name", ["source-version.schema.json", "research-package.schema.json"])
def test_current_schemas_allow_explicit_page_method_but_no_half_legacy_scope(
    tmp_path: Path, name: str,
) -> None:
    _, receipt = capture_pdf_page_text(tmp_path, _pdf_pages([["Synthetic page"]]), page=1)
    full = json.loads((ROOT / "schemas" / name).read_text())
    schema = full["$defs"]["source_text_derivation"]
    validator = Draft202012Validator(schema)
    payload = receipt.model_dump(mode="json")
    assert not list(validator.iter_errors(payload))
    for field in ("page", "page_count"):
        half = {k: v for k, v in payload.items() if k != field}
        assert list(validator.iter_errors(half))
        half["method"] = "pypdf-text-v1"
        assert list(validator.iter_errors(half))
    assert list(validator.iter_errors({**payload, "page": True}))


def _ingest_page(project: Path, *, wrong_page: bool = False, unknown_disclosure: bool = False):
    raw = _pdf_pages([["Synthetic alpha: 42 participants"], ["Synthetic beta: 57 participants"]])
    text, receipt = capture_pdf_page_text(project, raw, page=1)
    now = datetime(2026, 10, 3, tzinfo=UTC)
    source = SourceCapture(
        source_id="synthetic-page-1", route_id="synthetic-test", source_type="protocol_sap",
        title="Synthetic source, not clinical evidence", url="https://example.org/test.pdf",
        query_or_identifier="test", language="en", access_method="synthetic_test",
        media_type="application/pdf", content_text=text, text_derivation=receipt,
        acquired_at=now, published_at=now, effective_at=None,
        first_disclosed_at=None if unknown_disclosure else now,
        locator=_locator(1, "Synthetic alpha"),
    )
    fact = ResearchFact(
        fact_id="synthetic-alpha", row_ref="design:alpha", entity_id="synthetic-study",
        entity_type="trial", canonical_name="Synthetic study", field_id="sample_size",
        raw_value="42", normalized_value=None, disclosure_state="reported_value",
        source_id=source.source_id, locator=_locator(2 if wrong_page else 1, "Synthetic alpha"),
        original_text="Synthetic alpha: 42 participants",
    )
    claim = ResearchClaim(
        claim_id="synthetic-claim", claim_text="Synthetic test only",
        claim_kind="direct_evidence", fact_ids=(fact.fact_id,),
    )
    return ingest_research_evidence(
        project_root=project, project_id="synthetic-project", contract_version=1,
        report_kind="C", data_cutoff=now, scientific_content_digest="a" * 64,
        created_at=now, sources=(source,), route_attempts=(), facts=(fact,), claims=(claim,),
    )


def test_explicit_page_proof_ingests_reopens_and_remains_candidate(tmp_path: Path) -> None:
    database_path = tmp_path / "state/project.sqlite"
    apply_migrations(database_path)
    lineage = _ingest_page(tmp_path)
    repository = EvidenceRepository(database_path, ContentAddressedStore(tmp_path))
    fragment = repository.read_fragment(lineage.fragment_by_fact_id["synthetic-alpha"])
    reopened = repository.verify_reopened_fragment_record(
        fragment, reopened_original_text=fragment.original_text,
        source_version_id=lineage.source_version_ids[0],
    )
    assert reopened.text_derivation is not None
    assert reopened.text_derivation.page == 1
    verify_source_text_derivation(tmp_path, reopened.text_derivation, fragment.original_text)
    with open_database(database_path) as database:
        state = database.execute("SELECT review_state FROM fact_versions").fetchone()[0]
        assert state == "candidate"
    assert _ingest_page(tmp_path).fact_version_ids == lineage.fact_version_ids


def test_wrong_page_fails_before_persisting_any_source_or_fact(tmp_path: Path) -> None:
    database_path = tmp_path / "state/project.sqlite"
    apply_migrations(database_path)
    with pytest.raises(ResearchIngestionError, match="页码"):
        _ingest_page(tmp_path, wrong_page=True)
    with open_database(database_path) as database:
        for table in ("source_versions", "evidence_fragments", "fact_versions"):
            assert database.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_pdf_candidate_with_unknown_public_date_reopens_but_is_not_historically_eligible(
    tmp_path: Path,
) -> None:
    from ci_workflow.sources.planner import HistoricalCutoffState, assess_historical_source

    apply_migrations(tmp_path / "state/project.sqlite")
    lineage = _ingest_page(tmp_path, unknown_disclosure=True)
    repository = EvidenceRepository(
        tmp_path / "state/project.sqlite", ContentAddressedStore(tmp_path),
    )
    with open_database(tmp_path / "state/project.sqlite") as database:
        source = repository._read_source_version(database, lineage.source_version_ids[0])
        assert database.execute("SELECT review_state FROM fact_versions").fetchone()[0] == (
            "candidate"
        )
    assert source.first_disclosed_at.value is None
    assessment = assess_historical_source(
        source, cutoff=datetime(2099, 1, 1, tzinfo=UTC), key_evidence=True,
    )
    assert assessment.state is HistoricalCutoffState.BLOCKED_UNKNOWN_DISCLOSURE
    assert not assessment.can_enter_snapshot
