"""A-only/B-only/A+B offline share of the committed R24-46 current generation.

The exporter must package the committed current revision only, preserve the
hypothetical 90.1 user state next to the original 92.2 source quote, contain no
local absolute paths, credentials, or remote runtime dependencies, and keep
working after the ZIP is extracted into a renamed directory. The share input is
the pinned committed project, not a regeneration: working-tree asset edits must
never change which generation the share certifies.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile

import pytest

from ci_workflow.application.latest_delivery import (
    current_bundle_sha256,
    read_current_delivery,
)
from ci_workflow.application.share_export import (
    _PRIVATE_DATA,
    ShareViewSelection,
    _validate_static_resources,
    export_current_html_share,
)

ROW_ID = "eff-9f54cd0202c1f000619a"
SOURCE_VERSION_ID = "source-version_73c373185062ea7054e135c8"
PINNED_GENERATION_SHA256 = "528a27ad7aee6ec02b5ee1857eafa9f5ff10c00562d702a5781777bf5cb7f5b7"
ORIGINAL_VALUE = "92.2 Percentage of responders"
REMOTE_RUNTIME_PATTERN = re.compile(
    r"<(?:script|img|source)\b[^>]*?\bsrc=[\"\'](?:https?:)?//"
    r"|<link\b[^>]*?\bhref=[\"\'](?:https?:)?//"
    r"|url\(\s*[\"\']?(?:https?:)?//",
    re.IGNORECASE,
)
NETWORK_CALL_PATTERNS = ("fetch(", "XMLHttpRequest", "import(", "sendBeacon", "new WebSocket")
# 资产注释合法地写着 "works from file://."，因此资产只匹配带三个斜杠的真实文件协议。
ASSET_ABSOLUTE_PATH = re.compile(rb"/Users/|/home/|file:///|[A-Za-z]:\\Users\\|BEGIN .*PRIVATE KEY")


@pytest.fixture(scope="module")
def pinned_share_root() -> Path:
    """The committed R24-46 current-source project; the only authorized share input."""
    repo = Path(__file__).resolve().parents[2]
    root = repo / (
        ".artifacts/r24-46-browser-rerun-20260926/"
        "test_current_capture_has_legit0/current-source-ab-development"
    )
    if not (root / "project.yaml").is_file():
        pytest.skip("pinned R24-46 current-source development project unavailable")
    current = read_current_delivery(root)
    assert current is not None and current.revision == 1
    assert current.request_id == "r24-46-current-cas-ab-hypothetical-edit"
    assert current_bundle_sha256(current) == PINNED_GENERATION_SHA256
    return root


def _projection(member: bytes) -> dict:
    return json.loads(member.decode("utf-8").split("=", 1)[1].rstrip(" ;\n"))


def _check_projection_identity(archive: ZipFile, report: str) -> None:
    projection = _projection(archive.read(f"{report}/data/report.js"))
    row = next(item for item in projection["efficacy"] if item["row_id"] == ROW_ID)
    assert row["value"] == 90.1
    assert row["source_text"] == "92.2"
    assert row["source_version_id"] == SOURCE_VERSION_ID
    assert projection["user_edits"][ROW_ID]["original_value"] == ORIGINAL_VALUE


def test_share_variants_carry_committed_current_identity_and_source_quote(
    tmp_path: Path, pinned_share_root: Path,
) -> None:
    current = read_current_delivery(pinned_share_root)
    assert current is not None
    variants = {
        "a-only.zip": (ShareViewSelection(report="A", revision=1, entry_page="overview.html"),),
        "b-only.zip": (ShareViewSelection(report="B", revision=1, entry_page="efficacy.html"),),
        "a-plus-b.zip": (
            ShareViewSelection(report="A", revision=1, entry_page="overview.html"),
            ShareViewSelection(report="B", revision=1, entry_page="efficacy.html"),
        ),
    }
    with pytest.raises(ValueError, match="revision"):
        export_current_html_share(
            pinned_share_root, tmp_path / "stale.zip",
            selections=(ShareViewSelection(report="A", revision=0,
                                           entry_page="overview.html"),),
        )
    assert not (tmp_path / "stale.zip").exists()
    for variant, selections in variants.items():
        receipt = export_current_html_share(
            pinned_share_root, tmp_path / variant, selections=selections,
        )
        reports = tuple(item.report for item in selections)
        assert (receipt.current_revision, receipt.reports) == (current.revision, reports)
        with ZipFile(tmp_path / variant) as archive:
            members = archive.namelist()
            manifest = json.loads(archive.read("share-manifest.json"))
            assert manifest["current_revision"] == current.revision
            assert manifest["current_generation_sha256"] == PINNED_GENERATION_SHA256
            assert manifest["fact_revision_digest"] == current.fact_revision_digest
            assert manifest["status"] == "user_current_not_scientific_release_acceptance"
            assert manifest["external_sources_require_network"] is True
            assert set(manifest["reports"]) == set(reports)
            prefixes = tuple(f"{report}/" for report in reports)
            assert all(
                member in {"打开报告.html", "share-manifest.json"}
                or member.startswith(prefixes) for member in members
            )
            assert all(".." not in member.split("/") for member in members)
            landing = archive.read("打开报告.html").decode("utf-8")
            assert f"当前事实版本 {current.revision}" in landing
            for report in reports:
                delivery = next(item for item in current.reports if item.report == report)
                exported = manifest["reports"][report]
                assert exported["report_revision"] == delivery.revision
                assert exported["view_config"]["revision"] == delivery.revision
                assert set(exported["file_sha256"]) == (
                    set(delivery.file_hashes) - {"data/consumer-receipt.json"}
                )
                assert exported["source_site_file_sha256"] == delivery.file_hashes
                for relative, digest in exported["file_sha256"].items():
                    member = f"{report}/{relative}"
                    assert hashlib.sha256(archive.read(member)).hexdigest() == digest
                    if relative.endswith((".html", ".json")) or relative.startswith("data/"):
                        assert _PRIVATE_DATA.search(archive.read(member)) is None, member
                    else:
                        assert ASSET_ABSOLUTE_PATH.search(archive.read(member)) is None, member
                    if member.endswith((".html", ".css")):
                        text = archive.read(member).decode("utf-8")
                        assert REMOTE_RUNTIME_PATTERN.search(text) is None, member
                    elif member.endswith(".js"):
                        script = archive.read(member).decode("utf-8", "replace")
                        assert not [pattern for pattern in NETWORK_CALL_PATTERNS
                                    if pattern in script], member
                assert f'href="{report}/' in landing
                _check_projection_identity(archive, report)
                if report == "B":
                    page = archive.read("B/efficacy.html").decode("utf-8")
                    evidence = json.loads(
                        page.split("window.__EVIDENCE_VIEWS__ = ", 1)[1].split(";\n", 1)[0])
                    view = evidence[0]
                    assert view["original_text"] == "92.2"
                    assert view["user_edit"]["original_value"] == ORIGINAL_VALUE
                    assert view["user_edit"]["basis"] == "开发演练假设值，非医学订正"
                    assert view["source_version_id"] == SOURCE_VERSION_ID
                    assert "Day 126 and Day 168" in view["timepoint"]["value"]


def test_share_zip_stays_self_contained_after_moving(
    tmp_path: Path, pinned_share_root: Path,
) -> None:
    output = tmp_path / "a-plus-b.zip"
    receipt = export_current_html_share(
        pinned_share_root, output,
        selections=(
            ShareViewSelection(report="A", revision=1, entry_page="overview.html"),
            ShareViewSelection(report="B", revision=1, entry_page="efficacy.html"),
        ),
    )
    assert receipt.reports == ("A", "B")
    renamed = tmp_path / "收件人目录" / "重命名后"
    renamed.mkdir(parents=True)
    with ZipFile(output) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
        archive.extractall(renamed)
    extracted = {
        path.relative_to(renamed).as_posix(): path.read_bytes()
        for path in sorted(renamed.rglob("*")) if path.is_file()
    }
    assert extracted == members
    _validate_static_resources(extracted)
    landing = extracted["打开报告.html"].decode("utf-8")
    for report, entry in (("A", "overview.html"), ("B", "efficacy.html")):
        assert (renamed / report / entry).is_file()
        assert f'href="{report}/{entry}"' in landing
    deeper = tmp_path / "再次移动" / "share"
    deeper.parent.mkdir()
    renamed.rename(deeper)
    for report, entry in (("A", "overview.html"), ("B", "efficacy.html")):
        page = (deeper / report / entry).read_text(encoding="utf-8")
        marker = ('<script src="data/report.js"' if report == "A"
                  else "window.__EVIDENCE_VIEWS__")
        assert marker in page
        assert (deeper / report / "data/report.js").is_file()
    assert (deeper / "B/data/report.js").read_bytes() == members["B/data/report.js"]
