"""Page-aware native PDF derivation: the proof is pinned to the exact page and one unique anchor."""

from __future__ import annotations

import hashlib
import io
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError
from pypdf import PdfReader

from ci_workflow.domain.evidence import (
    DateEvidence,
    EvidenceLocator,
    SourceTextDerivation,
)
from ci_workflow.storage.content_store import ContentAddressedStore, EvidenceRepository
from ci_workflow.storage.migrations import apply_migrations
from ci_workflow.storage.source_derivation import (
    SourceDerivationError,
    capture_pdf_page_text,
    capture_source_text,
    verify_pdf_page_text_derivation,
    verify_source_text_derivation,
)
from ci_workflow.storage.sqlite import open_database

ROOT = Path(__file__).resolve().parents[2]
_REAL_PDF_DIR = ROOT / ".artifacts/r24-96-c-public-documents-20261003/downloads"
_MIXED_PDF = "NCT03829449-Prot_000.pdf"  # 129 pages, 34 image-only pages
_MIXED_IMAGE_ONLY_PAGE = 5
_NATIVE_PDF = "NCT02264639-Prot_000.pdf"  # 72 native-text pages


def _pdf_pages(pages: list[list[str] | None]) -> bytes:
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    for lines in pages:
        page = writer.add_blank_page(width=320, height=200)
        if lines is None:
            continue
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({
                NameObject("/F1"): DictionaryObject({
                    NameObject("/Type"): NameObject("/Font"),
                    NameObject("/Subtype"): NameObject("/Type1"),
                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                }),
            }),
        })
        operations = ["BT /F1 10 Tf 20 160 Td"]
        for index, line in enumerate(lines):
            if index:
                operations.append("0 -16 Td")
            operations.append(f"({line}) Tj")
        operations.append("ET")
        stream = DecodedStreamObject()
        stream.set_data(" ".join(operations).encode("ascii"))
        page[NameObject("/Contents")] = stream
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _real_pdf(name: str) -> bytes:
    path = _REAL_PDF_DIR / name
    if not path.is_file():
        pytest.skip(f"缺少只读公共来源PDF：{name}")
    return path.read_bytes()


def _page_texts(raw: bytes) -> list[str]:
    return [(page.extract_text() or "").strip() for page in PdfReader(io.BytesIO(raw)).pages]


def _distinctive_line(page_text: str, other_text: str) -> str:
    """One long well-formed line that occurs once on its page and normalized-nowhere else."""
    other_normalized = " ".join(other_text.split())
    candidates = []
    for line in page_text.splitlines():
        stripped = line.strip()
        normalized = " ".join(stripped.split())
        if len(normalized) < 40 or stripped != normalized:
            continue
        if page_text.count(stripped) == 1 and normalized not in other_normalized:
            candidates.append(stripped)
    assert candidates, "真实PDF样本页缺少可独特性锚定行"
    return max(candidates, key=len)


def _locator(page: int, anchor: str) -> EvidenceLocator:
    return EvidenceLocator(document_role="design_document", page=page, paragraph=anchor)


_TWO_PAGES = [
    ["Cohort alpha: 42 events", "Primary analysis population confirmed"],
    ["Cohort alpha: 57 events", "Secondary exploratory cohort: 7 events"],
]


def test_capture_binds_exact_page_bytes_and_proves_unique_anchor(tmp_path: Path) -> None:
    raw = _pdf_pages(_TWO_PAGES)
    text, receipt = capture_pdf_page_text(tmp_path, raw, page=2)

    assert receipt.method == "pypdf-page-text-v1"
    assert (receipt.page, receipt.page_count) == (2, 2)
    assert "Secondary exploratory cohort: 7 events" in text
    assert "Primary analysis population confirmed" not in text
    assert receipt.text_sha256 == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert ContentAddressedStore(tmp_path).read_bytes(receipt.raw_asset) == raw

    quote = verify_pdf_page_text_derivation(
        tmp_path, receipt, text,
        locator=_locator(2, "Secondary exploratory cohort: 7 events"),
    )
    assert quote == "Secondary exploratory cohort: 7 events"


def test_anchor_from_other_page_cannot_prove_requested_page(tmp_path: Path) -> None:
    raw = _pdf_pages([
        ["Cohort alpha: 42 events"],
        ["Cohort beta: 57 events"],
    ])
    page_one, receipt_one = capture_pdf_page_text(tmp_path, raw, page=1)
    with pytest.raises(SourceDerivationError, match="所证页面"):
        verify_pdf_page_text_derivation(
            tmp_path, receipt_one, page_one, locator=_locator(1, "Cohort beta: 57 events"),
        )
    page_two, receipt_two = capture_pdf_page_text(tmp_path, raw, page=2)
    with pytest.raises(SourceDerivationError, match="所证页面"):
        verify_pdf_page_text_derivation(
            tmp_path, receipt_two, page_two, locator=_locator(2, "Cohort alpha: 42 events"),
        )


def test_duplicate_anchor_lines_on_requested_page_fail_closed(tmp_path: Path) -> None:
    raw = _pdf_pages([
        ["Cohort alpha: 42 events"],
        ["Cohort alpha: 57 events", "Cohort alpha: 63 events"],
    ])
    text, receipt = capture_pdf_page_text(tmp_path, raw, page=2)
    with pytest.raises(SourceDerivationError):
        verify_pdf_page_text_derivation(
            tmp_path, receipt, text, locator=_locator(2, "Cohort alpha"),
        )


def test_complete_multiline_clause_can_be_proved_without_deleting_qualifiers(
    tmp_path: Path,
) -> None:
    raw = _pdf_pages([["Synthetic analysis set includes all treated participants.",
                       "Only participants with an evaluable sample enter the PK subset."]])
    text, receipt = capture_pdf_page_text(tmp_path, raw, page=1)
    assert "\n" in text
    assert verify_pdf_page_text_derivation(
        tmp_path, receipt, text, locator=_locator(1, text),
    ) == text


def test_multiline_clause_repeated_on_page_remains_ambiguous(tmp_path: Path) -> None:
    lines = ["Synthetic analysis clause.", "Qualified subset only."]
    text, receipt = capture_pdf_page_text(tmp_path, _pdf_pages([lines + lines]), page=1)
    quote = "\n".join(lines)
    with pytest.raises(SourceDerivationError, match="唯一"):
        verify_pdf_page_text_derivation(tmp_path, receipt, text, locator=_locator(1, quote))


def test_cross_page_duplicate_anchor_is_disambiguated_by_page(tmp_path: Path) -> None:
    raw = _pdf_pages([
        ["Cohort alpha: 42 events", "Page one summary"],
        ["Cohort alpha: 57 events", "Page two summary"],
    ])
    page_one, receipt_one = capture_pdf_page_text(tmp_path, raw, page=1)
    page_two, receipt_two = capture_pdf_page_text(tmp_path, raw, page=2)
    assert verify_pdf_page_text_derivation(
        tmp_path, receipt_one, page_one, locator=_locator(1, "Cohort alpha"),
    ) == "Cohort alpha: 42 events"
    assert verify_pdf_page_text_derivation(
        tmp_path, receipt_two, page_two, locator=_locator(2, "Cohort alpha"),
    ) == "Cohort alpha: 57 events"


@pytest.mark.parametrize(
    "kind", ["page_and_url", "page_only", "page_and_field_path", "no_page"],
)
def test_coarse_locator_cannot_prove_page_quote(tmp_path: Path, kind: str) -> None:
    raw = _pdf_pages([["Cohort alpha: 42 events"], ["Cohort beta: 57 events"]])
    text, receipt = capture_pdf_page_text(tmp_path, raw, page=1)
    locators = {
        "page_and_url": EvidenceLocator(
            document_role="design_document", page=1, url="https://example.org/a.pdf",
        ),
        "page_only": EvidenceLocator(document_role="design_document", page=1),
        "page_and_field_path": EvidenceLocator(
            document_role="design_document", page=1, field_path="$",
        ),
        "no_page": EvidenceLocator(
            document_role="design_document", paragraph="Cohort alpha: 42 events",
        ),
    }
    with pytest.raises(SourceDerivationError):
        verify_pdf_page_text_derivation(tmp_path, receipt, text, locator=locators[kind])


def test_missing_out_of_range_and_tampered_page_fail_closed(tmp_path: Path) -> None:
    raw = _pdf_pages([["Cohort alpha: 42 events"], ["Cohort beta: 57 events"]])
    with pytest.raises(SourceDerivationError):
        capture_pdf_page_text(tmp_path, raw, page=0)
    with pytest.raises(SourceDerivationError):
        capture_pdf_page_text(tmp_path, raw, page=3)
    assert not (tmp_path / "evidence").exists()

    text, receipt = capture_pdf_page_text(tmp_path, raw, page=1)
    locator = _locator(1, "Cohort alpha: 42 events")
    for tampered in (
        receipt.model_copy(update={"page": 2}),
        receipt.model_copy(update={"page": None}),
        receipt.model_copy(update={"page_count": 3}),
        receipt.model_copy(update={"extractor_version": "0.0.0"}),
    ):
        with pytest.raises(SourceDerivationError):
            verify_pdf_page_text_derivation(tmp_path, tampered, text, locator=locator)
    with pytest.raises(SourceDerivationError):
        verify_pdf_page_text_derivation(
            tmp_path, receipt, text, locator=_locator(2, "Cohort alpha: 42 events"),
        )


def test_raw_text_and_receipt_drift_fail_closed(tmp_path: Path) -> None:
    raw = _pdf_pages([["Cohort alpha: 42 events"], ["Cohort beta: 57 events"]])
    text, receipt = capture_pdf_page_text(tmp_path, raw, page=1)
    locator = _locator(1, "Cohort alpha: 42 events")
    with pytest.raises(SourceDerivationError):
        verify_pdf_page_text_derivation(tmp_path, receipt, text + " tampered", locator=locator)
    with pytest.raises(SourceDerivationError):
        verify_pdf_page_text_derivation(
            tmp_path, receipt.model_copy(update={"text_sha256": "0" * 64}), text, locator=locator,
        )
    (tmp_path / receipt.raw_asset.relative_path).write_bytes(b"raw drift")
    with pytest.raises(SourceDerivationError):
        verify_pdf_page_text_derivation(tmp_path, receipt, text, locator=locator)


def test_page_receipt_requires_typed_pages_and_legacy_method_rejects_pages(
    tmp_path: Path,
) -> None:
    raw = _pdf_pages([["Cohort alpha: 42 events"]])
    _, receipt = capture_pdf_page_text(tmp_path, raw, page=1)
    payload = receipt.model_dump(mode="json")
    with pytest.raises(ValidationError):
        SourceTextDerivation.model_validate({k: v for k, v in payload.items() if k != "page"})
    with pytest.raises(ValidationError):
        SourceTextDerivation.model_validate({**payload, "page": 2})
    with pytest.raises(ValidationError):
        SourceTextDerivation.model_validate({**payload, "method": "pypdf-text-v1"})


def test_legacy_receipt_is_identity_stable_and_cannot_upgrade(tmp_path: Path) -> None:
    raw = _pdf_pages([["Legacy page one text"], ["Legacy page two text"]])
    collapsed, legacy = capture_source_text(tmp_path, raw, media_type="application/pdf")
    assert legacy.method == "pypdf-text-v1"
    assert "Legacy page one text" in collapsed
    assert "Legacy page two text" in collapsed
    verify_source_text_derivation(tmp_path, legacy, collapsed)
    assert set(legacy.model_dump(mode="json")) == {
        "schema_version", "raw_asset", "text_sha256", "method", "extractor_version",
    }

    page_text, page_receipt = capture_pdf_page_text(tmp_path, raw, page=1)
    with pytest.raises(SourceDerivationError):
        verify_pdf_page_text_derivation(
            tmp_path, legacy, collapsed, locator=_locator(1, "Legacy page one text"),
        )
    # The generic caller now opts into an explicitly page-scoped receipt;
    # it still cannot turn an old whole-document receipt into page proof.
    verify_source_text_derivation(tmp_path, page_receipt, page_text)


def test_legacy_derivation_json_literal_roundtrips_unchanged() -> None:
    legacy_json = {
        "schema_version": "1.0",
        "raw_asset": {
            "sha256": "a" * 64,
            "relative_path": f"evidence/raw/sha256/aa/{'a' * 64}.bin",
            "byte_size": 10,
            "media_type": "application/pdf",
        },
        "text_sha256": "b" * 64,
        "method": "pypdf-text-v1",
        "extractor_version": "6.15.0",
    }
    receipt = SourceTextDerivation.model_validate(legacy_json)
    assert receipt.model_dump(mode="json") == legacy_json


def test_page_receipt_roundtrips_through_repository(tmp_path: Path) -> None:
    raw = _pdf_pages([["Cohort alpha: 42 events"], ["Cohort beta: 57 events"]])
    text, receipt = capture_pdf_page_text(tmp_path, raw, page=2)
    database_path = tmp_path / "state/project.sqlite"
    apply_migrations(database_path)
    repository = EvidenceRepository(database_path, ContentAddressedStore(tmp_path))
    date = DateEvidence(
        state="reported", value=datetime(2026, 10, 3, tzinfo=UTC),
        locator=_locator(2, "Cohort beta: 57 events"),
    )
    source = repository.add_source_version(
        source_id="page-proof-source", content=text.encode("utf-8"), media_type="text/plain",
        acquired_at=datetime(2026, 10, 3, tzinfo=UTC),
        published_at=date, effective_at=date, first_disclosed_at=date,
        text_derivation=receipt,
    )
    assert source.text_derivation == receipt
    with open_database(database_path) as database:
        assert repository._read_source_version(database, source.source_version_id) == source


def test_image_only_page_fails_closed_without_writing_evidence(tmp_path: Path) -> None:
    raw = _pdf_pages([None, ["Cohort beta: 57 events"]])
    with pytest.raises(SourceDerivationError, match="文本层"):
        capture_pdf_page_text(tmp_path, raw, page=1)
    assert not (tmp_path / "evidence").exists()
    with pytest.raises(SourceDerivationError):
        capture_pdf_page_text(tmp_path, raw, page=3)
    assert not (tmp_path / "evidence").exists()


def test_real_mixed_pdf_proves_native_page_only(tmp_path: Path) -> None:
    raw = _real_pdf(_MIXED_PDF)
    pages = _page_texts(raw)
    assert len(pages) == 129
    assert pages[_MIXED_IMAGE_ONLY_PAGE - 1] == ""

    other_page_marker = _distinctive_line(pages[2], pages[0])
    text, receipt = capture_pdf_page_text(tmp_path, raw, page=1)
    assert receipt.page_count == 129
    assert "Page 1 of 129" in text
    assert other_page_marker not in text
    quote = verify_pdf_page_text_derivation(
        tmp_path, receipt, text, locator=_locator(1, _distinctive_line(text, pages[2])),
    )
    assert quote in text

    with pytest.raises(SourceDerivationError, match="文本层"):
        capture_pdf_page_text(tmp_path, raw, page=_MIXED_IMAGE_ONLY_PAGE)

    collapsed, legacy = capture_source_text(tmp_path, raw, media_type="application/pdf")
    assert legacy.method == "pypdf-text-v1"
    assert len(collapsed) > len(text)
    assert other_page_marker in collapsed


def test_real_native_pdf_wrong_page_claim_is_rejected(tmp_path: Path) -> None:
    raw = _real_pdf(_NATIVE_PDF)
    pages = _page_texts(raw)
    assert len(pages) == 72
    page_two_marker = _distinctive_line(pages[1], pages[0])

    page_one, receipt_one = capture_pdf_page_text(tmp_path, raw, page=1)
    with pytest.raises(SourceDerivationError, match="所证页面"):
        verify_pdf_page_text_derivation(
            tmp_path, receipt_one, page_one, locator=_locator(1, page_two_marker),
        )

    page_two, receipt_two = capture_pdf_page_text(tmp_path, raw, page=2)
    assert verify_pdf_page_text_derivation(
        tmp_path, receipt_two, page_two, locator=_locator(2, page_two_marker),
    ) == page_two_marker
