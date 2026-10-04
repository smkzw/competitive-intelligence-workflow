"""An availability witness proves only current public retrieval, never first publication."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import URLError

import pytest

from ci_workflow.domain.evidence import ContentBlob
from ci_workflow.sources.connectors.public_pdf_availability import (
    PdfHttpPage,
    PublicPdfAvailabilityError,
    PublicPdfAvailabilityWitness,
    capture_public_pdf_availability,
    verify_public_pdf_availability,
)
from ci_workflow.storage.content_store import ContentAddressedStore

OFFICIAL_URL = "https://cdn.clinicaltrials.gov/large-docs/39/NCT02264639/Prot_000.pdf"
OTHER_OFFICIAL_URL = "https://clinicaltrials.gov/uploaded-docs/49/NCT03829449/SAP_001.pdf"
OBSERVED_AT = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)
LATER_CUTOFF = OBSERVED_AT + timedelta(hours=1)
WITNESS_FIELDS = {
    "schema_version", "request_url", "final_url", "observed_available_at",
    "http_status", "content_type", "content_length", "expected_raw_asset", "raw_asset",
    "request_started_at", "receipt_asset",
}
_PDF_A_HEADER = b"%PDF-1.7\n% synthesized official protocol attachment\n"
_PDF_B_HEADER = b"%PDF-1.7\n% synthesized genuinely different later version\n"
PDF_A = _PDF_A_HEADER + b"A" * (1024 - len(_PDF_A_HEADER))
PDF_B = _PDF_B_HEADER + b"B" * (1024 - len(_PDF_B_HEADER))
assert len(PDF_A) == len(PDF_B)


def _pin(tmp_path: Path, content: bytes) -> ContentBlob:
    return ContentAddressedStore(tmp_path).put_bytes(content, media_type="application/pdf")


def _cassette(status: int = 200, body: bytes = PDF_A, final_url: str | None = None,
              content_type: str = "application/pdf", content_length: int | None = None,
              error: Exception | None = None) -> tuple[object, list[str]]:
    """One-shot fake transport in the style of the ctgov fetch tests."""
    calls: list[str] = []

    def transport(url: str, timeout: float, max_bytes: int) -> PdfHttpPage:
        calls.append(url)
        if error is not None:
            raise error
        return PdfHttpPage(
            status, content_type,
            len(body) if content_length is None else content_length,
            body, url if final_url is None else final_url,
        )

    return transport, calls


def _witness(tmp_path: Path) -> tuple[ContentBlob, PublicPdfAvailabilityWitness]:
    pinned = _pin(tmp_path, PDF_A)
    transport, _ = _cassette()
    capture = capture_public_pdf_availability(
        tmp_path, OFFICIAL_URL, pinned, timeout=10, transport=transport,
        clock=lambda: OBSERVED_AT,
    )
    assert capture.status == "available" and capture.witness is not None
    return pinned, capture.witness


def test_available_witness_preserves_exact_bytes_and_whitelisted_headers(
    tmp_path: Path,
) -> None:
    pinned = _pin(tmp_path, PDF_A)
    transport, calls = _cassette()
    capture = capture_public_pdf_availability(
        tmp_path, OFFICIAL_URL, pinned, timeout=10, transport=transport,
        clock=lambda: OBSERVED_AT,
    )
    witness = capture.witness
    assert capture.status == "available" and witness is not None
    assert calls == [OFFICIAL_URL]
    assert witness.request_url == witness.final_url == OFFICIAL_URL
    assert witness.observed_available_at == OBSERVED_AT
    assert witness.observed_available_at.tzinfo is UTC
    assert witness.http_status == 200
    assert witness.content_type == "application/pdf"
    assert witness.content_length == len(PDF_A)
    assert witness.expected_raw_asset == pinned
    assert witness.raw_asset.sha256 == pinned.sha256
    assert ContentAddressedStore(tmp_path).read_bytes(witness.raw_asset) == PDF_A
    # The compact receipt persists only whitelisted harmless content headers;
    # no cookies, authorization material or response timestamp header survives.
    assert set(witness.model_dump()) == WITNESS_FIELDS
    assert PublicPdfAvailabilityWitness.model_validate_json(
        witness.model_dump_json(),
    ) == witness


def test_repeat_same_byte_retrieval_reuses_cas_blob_without_identity_churn(
    tmp_path: Path,
) -> None:
    pinned = _pin(tmp_path, PDF_A)
    first = capture_public_pdf_availability(
        tmp_path, OFFICIAL_URL, pinned, timeout=10, transport=_cassette()[0],
        clock=lambda: OBSERVED_AT,
    )
    second = capture_public_pdf_availability(
        tmp_path, OFFICIAL_URL, pinned, timeout=10, transport=_cassette()[0],
        clock=lambda: OBSERVED_AT + timedelta(minutes=5),
    )
    assert first.witness is not None and second.witness is not None
    assert second.witness.raw_asset == first.witness.raw_asset == pinned
    stored = list((tmp_path / "evidence/raw/sha256").rglob("*.bin"))
    assert len(stored) == 3  # One pinned PDF, two distinct actual acquisition receipts.


def test_verify_reopens_exact_raw_bytes_when_cutoff_covers_observation(
    tmp_path: Path,
) -> None:
    pinned, witness = _witness(tmp_path)
    assert verify_public_pdf_availability(
        tmp_path, witness, OFFICIAL_URL, pinned, cutoff=LATER_CUTOFF,
    ) == PDF_A
    assert verify_public_pdf_availability(
        tmp_path, witness, OFFICIAL_URL, pinned, cutoff=OBSERVED_AT,
    ) == PDF_A


def test_verify_fails_closed_when_cutoff_precedes_observation(tmp_path: Path) -> None:
    pinned, witness = _witness(tmp_path)
    with pytest.raises(PublicPdfAvailabilityError):
        verify_public_pdf_availability(
            tmp_path, witness, OFFICIAL_URL, pinned,
            cutoff=OBSERVED_AT - timedelta(microseconds=1),
        )


@pytest.mark.parametrize("case", [
    "short_body", "oversize_body", "different_bytes", "html_mime", "missing_magic",
    "empty_body", "truncation_header", "nonofficial_redirect", "not_found",
    "forbidden", "server_error", "redirected_status", "network_failure",
])
def test_failed_capture_keeps_scoped_reason_without_retry_or_new_blob(
    tmp_path: Path, case: str,
) -> None:
    pinned = _pin(tmp_path, PDF_A)
    longer = PDF_A + b">"
    shorter = PDF_A[:-1]
    same_size_other = PDF_B
    cases = {
        "short_body": _cassette(body=shorter),
        "oversize_body": _cassette(body=longer),
        "different_bytes": _cassette(body=same_size_other),
        "html_mime": _cassette(content_type="text/html"),
        "missing_magic": _cassette(content_type="application/pdf", body=b"not pdf at all"),
        "empty_body": _cassette(body=b""),
        "truncation_header": _cassette(content_length=len(PDF_A) - 1),
        "nonofficial_redirect": _cassette(final_url="https://mirror.example.com/x.pdf"),
        "not_found": _cassette(status=404),
        "forbidden": _cassette(status=403),
        "server_error": _cassette(status=500),
        "redirected_status": _cassette(status=302),
        "network_failure": _cassette(error=URLError("connection refused")),
    }
    transport, calls = cases[case]
    capture = capture_public_pdf_availability(
        tmp_path, OFFICIAL_URL, pinned, timeout=10, transport=transport,
        clock=lambda: OBSERVED_AT,
    )
    assert capture.status != "available" and capture.witness is None
    assert capture.diagnostic.strip()
    assert len(calls) == 1  # One bounded attempt; never a retry loop.
    stored = list((tmp_path / "evidence/raw/sha256").rglob("*.bin"))
    assert len(stored) == 1  # Nothing beyond the pinned original is persisted.


@pytest.mark.parametrize("url", [
    "http://cdn.clinicaltrials.gov/large-docs/39/NCT02264639/Prot_000.pdf",
    "https://evil.example.com/large-docs/39/NCT02264639/Prot_000.pdf",
    "https://cdn.clinicaltrials.gov/large-docs/39/NCT02264639/Prot_000.pdf?token=x",
    "https://user:secret@cdn.clinicaltrials.gov/large-docs/39/NCT02264639/Prot_000.pdf",
    "https://cdn.clinicaltrials.gov:8443/large-docs/39/NCT02264639/Prot_000.pdf",
    "https://cdn.clinicaltrials.gov/large-docs/39/NCT02264639/index.html",
])
def test_non_admitted_urls_are_rejected_before_any_request(tmp_path: Path, url: str) -> None:
    pinned = _pin(tmp_path, PDF_A)
    transport, calls = _cassette()
    with pytest.raises(PublicPdfAvailabilityError):
        capture_public_pdf_availability(
            tmp_path, url, pinned, timeout=10, transport=transport,
            clock=lambda: OBSERVED_AT,
        )
    assert calls == []
    with pytest.raises(PublicPdfAvailabilityError):
        verify_public_pdf_availability(
            tmp_path, _witness(tmp_path)[1], url, pinned, cutoff=LATER_CUTOFF,
        )


def test_other_official_host_large_document_path_is_admitted(tmp_path: Path) -> None:
    pinned = _pin(tmp_path, PDF_A)
    transport, calls = _cassette()
    capture = capture_public_pdf_availability(
        tmp_path, OTHER_OFFICIAL_URL, pinned, timeout=10, transport=transport,
        clock=lambda: OBSERVED_AT,
    )
    assert capture.status == "available" and calls == [OTHER_OFFICIAL_URL]


def test_verify_rederives_every_field_against_model_copy_forgery(tmp_path: Path) -> None:
    pinned, witness = _witness(tmp_path)

    def verify(witness: PublicPdfAvailabilityWitness) -> None:
        verify_public_pdf_availability(
            tmp_path, witness, OFFICIAL_URL, pinned, cutoff=LATER_CUTOFF,
        )

    verify(witness)
    for field, value in (
        ("content_length", 1), ("http_status", 500), ("content_type", "text/html"),
        ("final_url", "https://mirror.example.com/x.pdf"),
        ("request_url", OTHER_OFFICIAL_URL),
        ("observed_available_at", OBSERVED_AT.replace(tzinfo=None)),
        ("expected_raw_asset", _pin(tmp_path, PDF_B)),
    ):
        forged = witness.model_copy(update={field: value})
        with pytest.raises(PublicPdfAvailabilityError):
            verify(forged)
    with pytest.raises(PublicPdfAvailabilityError):
        verify_public_pdf_availability(
            tmp_path, witness, OFFICIAL_URL, pinned,
            cutoff=OBSERVED_AT.replace(tzinfo=None),
        )


def test_verify_fails_closed_on_raw_or_pinned_tampering_and_version_change(
    tmp_path: Path,
) -> None:
    pinned, witness = _witness(tmp_path)
    blob_path = tmp_path / witness.raw_asset.relative_path
    blob_path.write_bytes(PDF_A[:-1] + b">")
    with pytest.raises(PublicPdfAvailabilityError):
        verify_public_pdf_availability(
            tmp_path, witness, OFFICIAL_URL, pinned, cutoff=LATER_CUTOFF,
        )
    blob_path.write_bytes(PDF_A)
    verify_public_pdf_availability(
        tmp_path, witness, OFFICIAL_URL, pinned, cutoff=LATER_CUTOFF,
    )
    with pytest.raises(PublicPdfAvailabilityError):
        verify_public_pdf_availability(
            tmp_path, witness, OFFICIAL_URL, _pin(tmp_path, PDF_B), cutoff=LATER_CUTOFF,
        )


def test_capture_rejects_unusable_pinned_asset_and_bounded_configuration(
    tmp_path: Path,
) -> None:
    pinned = _pin(tmp_path, PDF_A)
    transport, _ = _cassette()
    with pytest.raises(PublicPdfAvailabilityError):
        capture_public_pdf_availability(
            tmp_path, OFFICIAL_URL, _pin(tmp_path, PDF_A).model_copy(
                update={"media_type": "application/json"},
            ), timeout=10, transport=transport, clock=lambda: OBSERVED_AT,
        )
    missing = ContentBlob(
        sha256="0" * 64, relative_path="evidence/raw/sha256/00/" + "0" * 64 + ".bin",
        byte_size=1, media_type="application/pdf",
    )
    with pytest.raises(PublicPdfAvailabilityError):
        capture_public_pdf_availability(
            tmp_path, OFFICIAL_URL, missing, timeout=10, transport=transport,
            clock=lambda: OBSERVED_AT,
        )
    for bad_timeout in (0, 61):
        with pytest.raises(ValueError):
            capture_public_pdf_availability(
                tmp_path, OFFICIAL_URL, pinned, timeout=bad_timeout,
                transport=transport, clock=lambda: OBSERVED_AT,
            )
    with pytest.raises(ValueError):
        capture_public_pdf_availability(
            tmp_path, OFFICIAL_URL, pinned, timeout=10, transport=transport,
            clock=lambda: OBSERVED_AT.replace(tzinfo=None),
        )
