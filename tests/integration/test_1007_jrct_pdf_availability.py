"""Bounded jRCT numeric download-path admission reuses the exact-byte witness.

All PDF bytes, response headers and observation instants in this file are
synthesized: these tests prove path admission, transport bounding and
fail-closed content identity on the production functions. They are not
evidence that the observed owner download URL still serves 200
application/pdf at any later instant, and no session token is captured or
persisted anywhere.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import URLError

import pytest

from ci_workflow.domain.evidence import ContentBlob
from ci_workflow.sources.connectors.public_pdf_availability import (
    PdfHttpPage,
    PdfTransport,
    PublicPdfAvailabilityError,
    PublicPdfAvailabilityWitness,
    capture_public_pdf_availability,
    verify_public_pdf_availability,
)
from ci_workflow.storage.content_store import ContentAddressedStore

JRCT_URL = "https://jrct.mhlw.go.jp/reports/file-download/100021941"
OBSERVED_AT = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
LATER_CUTOFF = OBSERVED_AT + timedelta(hours=1)
_PDF_A_HEADER = b"%PDF-1.7\n% synthesized jRCT public attachment\n"
_PDF_B_HEADER = b"%PDF-1.7\n% synthesized later jRCT version\n"
PDF_A = _PDF_A_HEADER + b"A" * (1024 - len(_PDF_A_HEADER))
PDF_B = _PDF_B_HEADER + b"B" * (1024 - len(_PDF_B_HEADER))
assert len(PDF_A) == len(PDF_B)


def _pin(root: Path, content: bytes) -> ContentBlob:
    return ContentAddressedStore(root).put_bytes(content, media_type="application/pdf")


def _cassette(
    status: int = 200,
    body: bytes = PDF_A,
    final_url: str | None = None,
    content_type: str = "application/pdf",
    content_length: int | None = None,
    error: Exception | None = None,
) -> tuple[PdfTransport, list[str]]:
    """One-shot fake transport; records every attempt so bounds are observable."""
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


def _witness(root: Path) -> tuple[ContentBlob, PublicPdfAvailabilityWitness]:
    pinned = _pin(root, PDF_A)
    transport, _ = _cassette()
    capture = capture_public_pdf_availability(
        root, JRCT_URL, pinned, timeout=10, transport=transport, clock=lambda: OBSERVED_AT,
    )
    assert capture.status == "available" and capture.witness is not None
    return pinned, capture.witness


def test_jrct_numeric_download_path_reuses_same_exact_byte_witness(tmp_path: Path) -> None:
    pinned = _pin(tmp_path, PDF_A)
    transport, calls = _cassette()
    capture = capture_public_pdf_availability(
        tmp_path, JRCT_URL, pinned, timeout=10, transport=transport, clock=lambda: OBSERVED_AT,
    )
    witness = capture.witness
    assert capture.status == "available" and witness is not None
    assert calls == [JRCT_URL]
    assert witness.request_url == witness.final_url == JRCT_URL
    assert witness.observed_available_at == OBSERVED_AT
    assert witness.content_type == "application/pdf"
    assert witness.raw_asset == pinned
    assert witness.receipt_asset is not None
    assert ContentAddressedStore(tmp_path).read_bytes(witness.raw_asset) == PDF_A
    assert verify_public_pdf_availability(
        tmp_path, witness, JRCT_URL, pinned, cutoff=LATER_CUTOFF,
    ) == PDF_A
    assert verify_public_pdf_availability(
        tmp_path, witness, JRCT_URL, pinned, cutoff=OBSERVED_AT,
    ) == PDF_A


@pytest.mark.parametrize("url", [
    "https://jrct.mhlw.go.jp/reports/file-download/7",
    "https://jrct.mhlw.go.jp/reports/file-download/12345678901234567890",
])
def test_jrct_identifier_length_bounds_admit_one_and_twenty_digits(
    tmp_path: Path, url: str,
) -> None:
    pinned = _pin(tmp_path, PDF_A)
    transport, calls = _cassette()
    capture = capture_public_pdf_availability(
        tmp_path, url, pinned, timeout=10, transport=transport, clock=lambda: OBSERVED_AT,
    )
    assert capture.status == "available" and capture.witness is not None
    assert calls == [url]


@pytest.mark.parametrize("url", [
    "http://jrct.mhlw.go.jp/reports/file-download/100021941",
    "https://jrct.mhlw.go.jp.evil.example/reports/file-download/100021941",
    "https://evil.jrct.mhlw.go.jp/reports/file-download/100021941",
    "https://jrct.mhlw.go.jp/reports/file-download/100021941?token=secret",
    "https://jrct.mhlw.go.jp/reports/file-download/100021941#fragment",
    "https://user:secret@jrct.mhlw.go.jp/reports/file-download/100021941",
    "https://jrct.mhlw.go.jp:8443/reports/file-download/100021941",
    "https://jrct.mhlw.go.jp/reports/file-download/100021941.pdf",
    "https://jrct.mhlw.go.jp/reports/file-download/",
    "https://jrct.mhlw.go.jp/reports/file-download/abc123",
    "https://jrct.mhlw.go.jp/reports/file-download/123456789012345678901",
    "https://jrct.mhlw.go.jp/reports/file-download/100021941/extra",
    "https://jrct.mhlw.go.jp/other/100021941",
])
def test_jrct_non_admitted_urls_are_rejected_before_any_request(
    tmp_path: Path, url: str,
) -> None:
    pinned = _pin(tmp_path, PDF_A)
    transport, calls = _cassette()
    with pytest.raises(PublicPdfAvailabilityError):
        capture_public_pdf_availability(
            tmp_path, url, pinned, timeout=10, transport=transport, clock=lambda: OBSERVED_AT,
        )
    assert calls == []
    with pytest.raises(PublicPdfAvailabilityError):
        verify_public_pdf_availability(
            tmp_path, _witness(tmp_path)[1], url, pinned, cutoff=LATER_CUTOFF,
        )


@pytest.mark.parametrize("url", [
    "https://cdn.clinicaltrials.gov/reports/file-download/100021941",
    "https://clinicaltrials.gov/reports/file-download/100021941",
    "https://www.accessdata.fda.gov/reports/file-download/100021941",
    "https://jrct.mhlw.go.jp/foobar.pdf",
])
def test_jrct_admission_does_not_relax_other_host_or_path_rules(
    tmp_path: Path, url: str,
) -> None:
    pinned = _pin(tmp_path, PDF_A)
    transport, calls = _cassette()
    with pytest.raises(PublicPdfAvailabilityError):
        capture_public_pdf_availability(
            tmp_path, url, pinned, timeout=10, transport=transport, clock=lambda: OBSERVED_AT,
        )
    assert calls == []


def test_jrct_witness_temporal_gates_reject_backdating_and_future_claims(
    tmp_path: Path,
) -> None:
    pinned, witness = _witness(tmp_path)
    with pytest.raises(PublicPdfAvailabilityError, match="截止早于"):
        verify_public_pdf_availability(
            tmp_path, witness, JRCT_URL, pinned,
            cutoff=OBSERVED_AT - timedelta(microseconds=1),
        )
    future = witness.model_copy(
        update={"observed_available_at": datetime.now(UTC) + timedelta(days=1)},
    )
    with pytest.raises(PublicPdfAvailabilityError):
        verify_public_pdf_availability(
            tmp_path, future, JRCT_URL, pinned, cutoff=future.observed_available_at,
        )


@pytest.mark.parametrize("case", [
    "short_body", "oversize_body", "different_bytes", "html_mime", "missing_magic",
    "truncation_header", "nonofficial_redirect", "not_found", "forbidden",
    "server_error", "redirected_status", "network_failure",
])
def test_jrct_capture_still_fails_closed_on_content_and_network_boundaries(
    tmp_path: Path, case: str,
) -> None:
    pinned = _pin(tmp_path, PDF_A)
    cases = {
        "short_body": _cassette(body=PDF_A[:-1]),
        "oversize_body": _cassette(body=PDF_A + b">"),
        "different_bytes": _cassette(body=PDF_B),
        "html_mime": _cassette(content_type="text/html"),
        "missing_magic": _cassette(content_type="application/pdf", body=b"not a pdf at all"),
        "truncation_header": _cassette(content_length=len(PDF_A) - 1),
        "nonofficial_redirect": _cassette(
            final_url="https://mirror.example.com/reports/file-download/100021941",
        ),
        "not_found": _cassette(status=404),
        "forbidden": _cassette(status=403),
        "server_error": _cassette(status=500),
        "redirected_status": _cassette(status=302),
        "network_failure": _cassette(error=URLError("connection refused")),
    }
    transport, calls = cases[case]
    capture = capture_public_pdf_availability(
        tmp_path, JRCT_URL, pinned, timeout=10, transport=transport, clock=lambda: OBSERVED_AT,
    )
    assert capture.status != "available" and capture.witness is None
    assert capture.diagnostic.strip()
    assert calls == [JRCT_URL]  # One bounded attempt; never a retry loop.
    stored = list((tmp_path / "evidence/raw/sha256").rglob("*.bin"))
    assert len(stored) == 1  # Nothing beyond the pinned original is persisted.
