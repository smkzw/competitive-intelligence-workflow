from datetime import datetime

import pytest
from pydantic import ValidationError

from ci_workflow.application.source_research_service import SourceCapture
from ci_workflow.domain.evidence import source_version_identity


def _payload() -> dict[str, object]:
    return {
        "source_id": "source", "route_id": "ctgov", "source_type": "registry",
        "title": "Record", "url": "https://clinicaltrials.gov/study/NCT00000001",
        "query_or_identifier": "NCT00000001", "language": "en", "access_method": "api",
        "content_text": "record", "acquired_at": "2026-09-06T12:00:00Z",
        "published_at": "2026-07-01T00:00:00Z", "effective_at": None,
        "first_disclosed_at": "2026-07-01T00:00:00Z",
        "locator": {"document_role": "registry", "field_path": "lastUpdatePostDateStruct"},
    }


def test_capture_preserves_explicit_calendar_day() -> None:
    capture = SourceCapture.model_validate({
        **_payload(), "date_precisions": {"published_at": "calendar_day",
                                          "first_disclosed_at": "calendar_day"},
    })
    assert capture.date_evidence("published_at").precision == "calendar_day"
    assert capture.date_evidence("first_disclosed_at").precision == "calendar_day"


def test_legacy_capture_bytes_do_not_gain_implicit_precision_fields() -> None:
    capture = SourceCapture.model_validate(_payload())
    assert "date_precisions" not in capture.model_dump(mode="json")
    assert capture.date_evidence("published_at").precision == "instant"


@pytest.mark.parametrize("field,value", [
    ("published_at", "2026-07-01T12:00:00Z"), ("published_at", None),
])
def test_invalid_day_precision_is_rejected(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        SourceCapture.model_validate({
            **_payload(), field: value, "date_precisions": {field: "calendar_day"},
        })


def test_precision_correction_creates_distinct_source_version() -> None:
    instant = SourceCapture.model_validate(_payload())
    day = SourceCapture.model_validate({
        **_payload(), "date_precisions": {"published_at": "calendar_day"},
    })
    identities = [source_version_identity(
        capture.source_id, "a" * 64,
        published_at=capture.date_evidence("published_at"),
        effective_at=capture.date_evidence("effective_at"),
        first_disclosed_at=capture.date_evidence("first_disclosed_at"),
    ) for capture in (instant, day)]
    assert identities[0] != identities[1]


def test_day_disclosure_is_not_known_at_noon_but_is_known_after_day_end() -> None:
    capture = SourceCapture.model_validate({
        **_payload(), "date_precisions": {"first_disclosed_at": "calendar_day"},
    })
    disclosed = capture.date_evidence("first_disclosed_at")
    assert not disclosed.is_known_by(datetime.fromisoformat("2026-07-01T12:00:00Z"))
    assert disclosed.is_known_by(datetime.fromisoformat("2026-07-01T23:59:59.999999Z"))
