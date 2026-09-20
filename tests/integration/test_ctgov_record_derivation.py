"""A registry record is a proved extraction from the exact API response."""

import json
from pathlib import Path

import pytest

from ci_workflow.domain.evidence import CtgovRecordSelector
from ci_workflow.storage.content_store import ContentAddressedStore
from ci_workflow.storage.source_derivation import (
    SourceDerivationError,
    capture_source_text,
    verify_source_text_derivation,
)
from tests.integration.sources.test_ctgov_fetch import _study


def test_record_extraction_preserves_page_bytes_and_reopens_selector(tmp_path: Path) -> None:
    raw = json.dumps({"studies": [_study(1), _study(2)]}, indent=2).encode()
    selector = CtgovRecordSelector(study_index=1, nct_id="NCT00000002")
    text, receipt = capture_source_text(
        tmp_path, raw, media_type="application/json", record_selector=selector,
    )
    assert receipt.method == "ctgov-study-json-v1"
    assert json.loads(text) == _study(2)
    assert ContentAddressedStore(tmp_path).read_bytes(receipt.raw_asset) == raw
    verify_source_text_derivation(tmp_path, receipt, text)
    with pytest.raises(SourceDerivationError):
        verify_source_text_derivation(tmp_path, receipt.model_copy(update={
            "record_selector": CtgovRecordSelector(study_index=0, nct_id="NCT00000001"),
        }), text)


@pytest.mark.parametrize("failure", ["index", "identity", "mime", "duplicate_key", "nan"])
def test_invalid_record_extraction_is_not_persisted(tmp_path: Path, failure: str) -> None:
    raw = json.dumps({"studies": [_study(1)]}).encode()
    selector = CtgovRecordSelector(
        study_index=2 if failure == "index" else 0,
        nct_id="NCT00000002" if failure == "identity" else "NCT00000001",
    )
    if failure == "duplicate_key":
        raw = b'{"studies": [], "studies": ' + json.dumps([_study(1)]).encode() + b'}'
    if failure == "nan":
        raw = raw.replace(b'"Synthetic"', b'NaN')
    with pytest.raises(SourceDerivationError):
        capture_source_text(
            tmp_path, raw, media_type="text/plain" if failure == "mime" else "application/json",
            record_selector=selector,
        )
    assert not (tmp_path / "evidence").exists()


def test_plain_text_receipts_keep_legacy_serialized_shape(tmp_path: Path) -> None:
    _, receipt = capture_source_text(tmp_path, b"text", media_type="text/plain")
    assert "record_selector" not in receipt.model_dump(mode="json")


def test_record_slice_preserves_numeric_tokens_and_schema_contract(tmp_path: Path) -> None:
    from jsonschema import Draft202012Validator

    token = "0.12345678901234567890123456789"
    raw = json.dumps({"before": {"studies": "decoy"}, "studies": [_study(1)]}).replace(
        '"Synthetic"', f'"Synthetic", "numeric": {token}',
    ).encode()
    text, receipt = capture_source_text(
        tmp_path, raw, media_type="application/json",
        record_selector=CtgovRecordSelector(study_index=0, nct_id="NCT00000001"),
    )
    assert token in text
    root = Path(__file__).resolve().parents[2]
    for name in ("source-version", "research-package"):
        schema = json.loads((root / f"schemas/{name}.schema.json").read_text())
        validator = Draft202012Validator(schema["$defs"]["source_text_derivation"])
        valid = receipt.model_dump(mode="json")
        assert not list(validator.iter_errors(valid))
        invalid = dict(valid)
        invalid.pop("record_selector")
        assert list(validator.iter_errors(invalid))
