"""Production acquisition bridge: metadata-only must never become full text."""
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ci_workflow.application import source_research_service as service
from ci_workflow.sources.connectors.linked_jats import LinkedJatsIdentityError, LinkedJatsInspection
from ci_workflow.storage.source_derivation import verify_source_text_derivation

PMID = "31415926"
PMC = "PMC7654321"
DOI = "10.1234/example"
ACQUIRED = datetime(2026, 10, 4, tzinfo=UTC)


def _raw(body: str) -> bytes:
    return (
        '<pmc-articleset><article><front><article-meta>'
        f'<article-id pub-id-type="pmid">{PMID}</article-id>'
        f'<article-id pub-id-type="pmc">{PMC}</article-id>'
        f'<article-id pub-id-type="doi">{DOI}</article-id>'
        '<title-group><article-title>Exact original</article-title></title-group>'
        f'</article-meta></front>{body}</article></pmc-articleset>'
    ).encode()


def _capture(
    root: Path, raw: bytes, *, doi: str = DOI,
) -> tuple[LinkedJatsInspection, service.SourceCapture | None]:
    return service.source_capture_from_linked_jats_xml(
        root, raw, expected_pmid=PMID, expected_pmcid=PMC, expected_doi=doi,
        url=f"https://www.ebi.ac.uk/europepmc/webservices/rest/{PMC}/fullTextXML",
        acquired_at=ACQUIRED, media_type="application/xml",
    )


def test_native_wrapper_body_capture_is_bound_to_untouched_raw(tmp_path: Path) -> None:
    raw = _raw('<body><p>Observed estimate 82.3%; count 51/60.</p></body>')
    inspection, capture = _capture(tmp_path, raw)
    assert inspection.body_state == "body_present"
    assert capture is not None and capture.text_derivation is not None
    verify_source_text_derivation(tmp_path, capture.text_derivation, capture.content_text)
    assert capture.text_derivation.raw_asset.sha256 == inspection.raw_sha256
    assert "82.3%" in capture.content_text and "51/60" in capture.content_text
    assert capture.acquired_at == ACQUIRED
    assert capture.first_disclosed_at is capture.published_at is capture.effective_at is None
    assert not capture.is_available_by(ACQUIRED)


@pytest.mark.parametrize("body", ["", "<body/>", "<body><p> </p></body>"])
def test_metadata_only_retains_inspection_without_fulltext_capture(
    tmp_path: Path, body: str,
) -> None:
    inspection, capture = _capture(tmp_path, _raw(body))
    assert inspection.body_state == "metadata_only"
    assert capture is None
    assert not list(tmp_path.rglob("*.json"))


def test_identity_rejection_happens_before_storage(tmp_path: Path) -> None:
    with pytest.raises(LinkedJatsIdentityError):
        _capture(tmp_path, _raw("<body><p>Content.</p></body>"), doi="10.9999/wrong")
    assert not list(tmp_path.iterdir())


def test_invalid_media_does_not_write_assets(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="XML"):
        service.source_capture_from_linked_jats_xml(
            tmp_path, _raw("<body><p>Content.</p></body>"), expected_pmid=PMID,
            expected_pmcid=PMC, expected_doi=DOI, url="https://example.org/article",
            acquired_at=ACQUIRED, media_type="text/html",
        )
    assert not list(tmp_path.iterdir())
