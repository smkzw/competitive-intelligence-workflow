"""Production repository XML proof must replay the node, not search whole bytes."""

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
from ci_workflow.storage.source_derivation import capture_source_text, extract_locator_quote

RAW = (
    b"<article><body><p>Estimate <italic>82.3%</italic>.</p>"
    b"<table-wrap><table><tbody><tr><td>60</td><td>7</td></tr></tbody></table>"
    b"</table-wrap></body></article>"
)
P = "/article/body[1]/p[1]"
SECOND_CELL = "/article/body[1]/table-wrap[1]/table[1]/tbody[1]/tr[1]/td[2]"
ACQUIRED = datetime(2026, 10, 7, tzinfo=UTC)


def repo(root: Path, media: str):
    db = root / "state/project.sqlite"
    apply_migrations(db)
    text, derivation = capture_source_text(root, RAW, media_type=media)
    storage = EvidenceRepository(db, ContentAddressedStore(root))
    unknown = DateEvidence(
        state="not_publicly_disclosed",
        value=None,
        locator=EvidenceLocator(
            document_role="original_linked_publication", url="https://example.invalid/native.xml"
        ),
    )
    version = storage.add_source_version(
        source_id="native-example",
        content=text.encode(),
        media_type=media,
        acquired_at=ACQUIRED,
        published_at=unknown,
        effective_at=unknown,
        first_disclosed_at=unknown,
        text_derivation=derivation,
    )
    return storage, version, text


@pytest.mark.parametrize("media", ["application/xml", "text/xml"])
def test_native_fragment_reopens_normalized_inline_source(tmp_path: Path, media: str) -> None:
    storage, version, text = repo(tmp_path, media)
    locator = EvidenceLocator(document_role="original_linked_publication", field_path=P)
    quote = extract_locator_quote(text, media_type=media, locator=locator)
    assert quote == "Estimate 82.3%." and quote not in text
    fragment = storage.add_fragment(
        source_version_id=version.source_version_id,
        locator=locator,
        original_text=quote,
        created_at=ACQUIRED,
    )
    assert (
        storage.verify_reopened_fragment_record(
            fragment, reopened_original_text=quote, source_version_id=version.source_version_id
        )
        == version
    )


@pytest.mark.parametrize("media", ["application/xml", "text/xml"])
@pytest.mark.parametrize("path", [SECOND_CELL, "/article/body[1]/p[99]", "/article/body[1]"])
def test_present_elsewhere_cannot_substantiate_wrong_or_coarse_locator(
    tmp_path: Path, media: str, path: str
) -> None:
    storage, version, text = repo(tmp_path, media)
    assert "60" in text
    fragment = storage.add_fragment(
        source_version_id=version.source_version_id,
        locator=EvidenceLocator(document_role="original_linked_publication", field_path=path),
        original_text="60",
        created_at=ACQUIRED,
    )
    with pytest.raises(ContentIntegrityError):
        storage.verify_reopened_fragment_record(
            fragment, reopened_original_text="60", source_version_id=version.source_version_id
        )
