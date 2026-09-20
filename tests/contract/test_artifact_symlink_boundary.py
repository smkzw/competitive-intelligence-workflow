"""Artifact digests must not follow substituted external or local files."""

from pathlib import Path

import pytest

from ci_workflow.storage.manifest_store import (
    ArtifactManifest,
    ManifestIntegrityError,
    ManifestStore,
)
from tests.contract.test_artifact_manifest import _manifest


def test_artifact_entry_symlink_is_rejected_before_resolving(tmp_path: Path) -> None:
    payload = _manifest()
    entry = tmp_path / "reports/B/v1/html/index.html"
    entry.parent.mkdir(parents=True)
    target = tmp_path / "target.html"
    target.write_bytes(b"candidate")
    entry.symlink_to(target)
    with pytest.raises(ManifestIntegrityError, match="符号链接"):
        ManifestStore(tmp_path)._artifact_path(ArtifactManifest.model_validate(payload))


@pytest.mark.parametrize("directory_link", [False, True])
def test_directory_digest_rejects_all_symlinks(tmp_path: Path, directory_link: bool) -> None:
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_bytes(b"candidate")
    target = tmp_path / "target"
    if directory_link:
        target.mkdir()
        (target / "data.json").write_bytes(b"external")
    else:
        target.write_bytes(b"external")
    (site / "substituted").symlink_to(target, target_is_directory=directory_link)
    with pytest.raises(ManifestIntegrityError, match="符号链接"):
        ManifestStore._directory_digest(site)
