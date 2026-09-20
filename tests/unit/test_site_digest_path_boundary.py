from pathlib import Path

import pytest

from ci_workflow.qc.browser import LockedSitemapSourceError, site_directory_digest


@pytest.mark.parametrize("kind", ["file", "directory", "root"])
def test_site_digest_never_follows_links(tmp_path: Path, kind: str) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "data.txt").write_bytes(b"outside site")
    site = tmp_path / "site"
    if kind == "root":
        site.symlink_to(outside, target_is_directory=True)
    else:
        site.mkdir()
        (site / "index.html").write_bytes(b"site")
        (site / "link").symlink_to(outside / "data.txt" if kind == "file" else outside)
    with pytest.raises(LockedSitemapSourceError):
        site_directory_digest(site)
