"""JSON fragment proof uses the exact field, not serialized-text substring."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ci_workflow.domain.evidence import DateEvidence, EvidenceLocator
from ci_workflow.storage.content_store import (
    ContentAddressedStore,
    ContentIntegrityError,
    EvidenceRepository,
)
from ci_workflow.storage.migrations import apply_migrations


def _verify(
    root: Path, raw: bytes, path: str | None, quote: str, *, media: str = "application/json",
) -> None:
    db = root / "state/project.sqlite"
    apply_migrations(db)
    repository = EvidenceRepository(db, ContentAddressedStore(root))
    locator = EvidenceLocator(document_role="synthetic registry field", field_path=path,
                              paragraph="synthetic" if path is None else None)
    unknown = DateEvidence(state="not_publicly_disclosed", value=None, locator=locator)
    source = repository.add_source_version(
        source_id="synthetic-json", content=raw, media_type=media,
        acquired_at=datetime(2026, 10, 3, tzinfo=UTC), published_at=unknown,
        effective_at=unknown, first_disclosed_at=unknown,
    )
    fragment = repository.add_fragment(source_version_id=source.source_version_id,
                                       locator=locator, original_text=quote)
    reopened = repository.verify_reopened_fragment_record(
        fragment, reopened_original_text=quote, source_version_id=source.source_version_id,
    )
    assert reopened == source


@pytest.mark.parametrize("quote,ascii_encoding", [
    ("Inclusion Criteria:\n* 诊断PNH\n* eculizumab \\\u003e3 months", False),
    ('A quoted "endpoint" and a \\ literal', False),
    ("免疫与肾功能要求", True),
])
def test_json_escaped_scalar_reopens_exact_field(
    tmp_path: Path, quote: str, ascii_encoding: bool,
) -> None:
    raw = json.dumps({"eligibility": {"criteria": quote}}, ensure_ascii=ascii_encoding).encode()
    assert quote not in raw.decode()
    _verify(tmp_path, raw, "$.eligibility.criteria", quote)


@pytest.mark.parametrize("value,quote", [(0, "0"), (False, "false"),
                                        ({"b": 1, "a": 2}, '{"a":2,"b":1}')])
def test_json_native_values_reopen_without_reinterpreting_zero_or_boolean(
    tmp_path: Path, value: object, quote: str,
) -> None:
    _verify(tmp_path, json.dumps({"result": value}).encode(), "$.result", quote)


@pytest.mark.parametrize("raw,path,quote", [
    (b'{"selected":"wrong","other":"synthetic"}', "$.selected", "synthetic"),
    (b'{"other":"synthetic"}', "$.missing", "synthetic"),
    (b'{"other":"synthetic"}', "$", "synthetic"),
    (b'{"other":"synthetic"}', None, "synthetic"),
    (b'{"selected":"synthetic","selected":"conflict"}', "$.selected", "synthetic"),
    (b'{"selected":"synthetic","count":NaN}', "$.selected", "synthetic"),
    (b'{"selected":"synthetic"', "$.selected", "synthetic"),
])
def test_json_literal_elsewhere_or_ambiguous_source_cannot_prove_fragment(
    tmp_path: Path, raw: bytes, path: str | None, quote: str,
) -> None:
    with pytest.raises(ContentIntegrityError):
        _verify(tmp_path, raw, path, quote)


def test_non_json_text_keeps_existing_exact_literal_proof(tmp_path: Path) -> None:
    _verify(tmp_path, b"original synthetic text", None, "synthetic", media="text/plain")
