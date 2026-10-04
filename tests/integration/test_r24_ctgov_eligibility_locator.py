"""Native eligibility is a string, not an invented .text child or an accepted scope."""

import json

import pytest

from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.storage.source_derivation import extract_locator_quote
from tests.integration.test_r24_ctgov_source_inventory import _study
from tools.build_ctgov_source_inventory import _study_inventory_row


def _row(value: object, *, present: bool = True) -> dict:
    study = _study("NCT00000011", interventions=[])
    study["protocolSection"]["eligibilityModule"] = (
        {"eligibilityCriteria": value} if present else {}
    )
    return {"study": study, "page_number": 1, "study_index": 0,
            "page_sha256": "a" * 64, "page_relative_path": "pinned-page.bin"}


def test_exact_criteria_scalar_locator_reopens_complete_native_text() -> None:
    text = "Inclusion Criteria:\nCRSwNP.\n\nExclusion Criteria:\nWithout nasal polyps."
    row = _row(text)
    projected = _study_inventory_row(row, include_eligibility=True)
    clause = projected["eligibility_criteria"]
    assert clause["status"] == "reported_value"
    assert clause["value"] == text
    assert clause["path"] == "$.studies[0].protocolSection.eligibilityModule.eligibilityCriteria"
    assert extract_locator_quote(
        json.dumps({"studies": [row["study"]]}), media_type="application/json",
        locator=EvidenceLocator(document_role="clinical_trial_registry", field_path=clause["path"]),
    ) == text


@pytest.mark.parametrize("value,present,status", [
    (None, False, "source_field_missing"),
    (None, True, "source_value_null"),
    ({"text": "invented nested field"}, True, "parse_error"),
    ("", True, "source_text_empty"),
])
def test_source_missing_null_empty_and_parse_error_do_not_become_zero_or_equal(
    value: object, present: bool, status: str,
) -> None:
    projected = _study_inventory_row(_row(value, present=present), include_eligibility=True)
    clause = projected["eligibility_criteria"]
    assert clause["status"] == status
    assert clause["value"] == value


def test_default_legacy_inventory_does_not_gain_new_bytes() -> None:
    row = _row("Complete criteria")
    assert _study_inventory_row(row) == _study_inventory_row(row, include_eligibility=False)
    assert "eligibility_criteria" not in _study_inventory_row(row)
