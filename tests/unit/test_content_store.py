from __future__ import annotations

from pathlib import Path

import pytest

from ci_workflow.storage.content_store import (
    ContentAddressedStore,
    ContentIntegrityError,
)


def test_same_content_deduplicates_and_different_versions_coexist(tmp_path: Path) -> None:
    store = ContentAddressedStore(tmp_path)

    first = store.put_bytes(b"protocol version one", media_type="application/pdf")
    duplicate = store.put_bytes(b"protocol version one", media_type="application/pdf")
    changed = store.put_bytes(b"protocol version two", media_type="application/pdf")

    assert duplicate == first
    assert changed.sha256 != first.sha256
    assert changed.relative_path != first.relative_path
    assert first.relative_path.startswith("evidence/raw/sha256/")
    assert not Path(first.relative_path).is_absolute()
    assert store.read_bytes(first) == b"protocol version one"
    assert store.read_bytes(changed) == b"protocol version two"


def test_content_store_rejects_path_escape_and_digest_drift(tmp_path: Path) -> None:
    store = ContentAddressedStore(tmp_path)
    with pytest.raises(ValueError, match="原文"):
        store.put_bytes(b"", media_type="application/pdf")
    blob = store.put_bytes(b"primary publication", media_type="application/pdf")
    absolute = tmp_path / blob.relative_path
    absolute.write_bytes(b"tampered")

    with pytest.raises(ContentIntegrityError, match="摘要"):
        store.read_bytes(blob)

    with pytest.raises(ContentIntegrityError, match="项目目录"):
        store.resolve_relative("../outside.pdf")
