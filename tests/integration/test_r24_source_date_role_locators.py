"""Document creation, public upload and acquisition have different evidence locators."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from ci_workflow.application.source_research_service import SourceCapture
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.storage.source_derivation import capture_pdf_page_text
from tests.integration.test_r24_pdf_page_source_proof import _pdf_pages


def _capture(tmp_path: Path) -> dict[str, object]:
    text, receipt = capture_pdf_page_text(
        tmp_path, _pdf_pages([["Synthetic document version"]]), page=1,
    )
    return {
        "source_id": "synthetic-page", "route_id": "test", "source_type": "protocol_sap",
        "title": "Synthetic source only", "url": "https://example.org/test.pdf",
        "query_or_identifier": "synthetic", "language": "en", "access_method": "test",
        "media_type": "application/pdf", "content_text": text,
        "text_derivation": receipt.model_dump(mode="json"),
        "acquired_at": datetime(2026, 10, 3, tzinfo=UTC),
        "published_at": datetime(2024, 2, 7, tzinfo=UTC),
        "first_disclosed_at": datetime(2024, 2, 7, tzinfo=UTC),
        "effective_at": datetime(2020, 4, 3, tzinfo=UTC),
        "locator": EvidenceLocator(document_role="protocol_sap", page=1,
                                   paragraph="Synthetic document version").model_dump(mode="json"),
    }


def test_date_roles_preserve_distinct_locators_and_do_not_use_acquisition(tmp_path: Path) -> None:
    payload = _capture(tmp_path)
    metadata = EvidenceLocator(
        document_role="clinical_trial_registry", field_path="$.documents[0].uploadDate",
        url="https://example.org/registry",
    )
    payload["date_locators"] = {
        "published_at": metadata.model_dump(mode="json"),
        "first_disclosed_at": metadata.model_dump(mode="json"),
        "effective_at": payload["locator"],
    }
    capture = SourceCapture.model_validate(payload)
    assert capture.date_evidence("first_disclosed_at").locator == metadata
    assert capture.date_evidence("effective_at").locator == capture.locator
    assert capture.date_evidence("first_disclosed_at").value != capture.acquired_at
    assert SourceCapture.model_validate(capture.model_dump(mode="json")) == capture


def test_legacy_capture_does_not_gain_a_new_serialized_field(tmp_path: Path) -> None:
    capture = SourceCapture.model_validate(_capture(tmp_path))
    assert "date_locators" not in capture.model_dump(mode="json")
    for role in ("published_at", "effective_at", "first_disclosed_at"):
        assert capture.date_evidence(role).locator == capture.locator


def test_unknown_date_role_is_rejected_instead_of_silently_ignored(tmp_path: Path) -> None:
    payload = _capture(tmp_path)
    payload["date_locators"] = {"downloaded_at": payload["locator"]}
    with pytest.raises(ValidationError):
        SourceCapture.model_validate(payload)


def test_unknown_first_disclosure_is_retained_not_replaced_by_download_or_print_date(
    tmp_path: Path,
) -> None:
    payload = _capture(tmp_path)
    payload["first_disclosed_at"] = None
    capture = SourceCapture.model_validate(payload)
    unknown = capture.date_evidence("first_disclosed_at")
    assert unknown.state == "not_publicly_disclosed"
    assert unknown.value is None
    assert not unknown.is_known_by(datetime(2099, 1, 1, tzinfo=UTC))
    assert capture.published_at == payload["published_at"]
    assert capture.effective_at == payload["effective_at"]
    assert SourceCapture.model_validate(capture.model_dump(mode="json")) == capture
