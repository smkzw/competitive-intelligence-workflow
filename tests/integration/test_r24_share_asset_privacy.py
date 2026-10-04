"""Sharing must inspect assets as well as the visible report/data files."""

import pytest

from ci_workflow.application.share_export import _validate_static_resources


@pytest.mark.parametrize("relative", ["assets/local.js", "assets/local.css", "assets/icon.svg"])
@pytest.mark.parametrize(
    "private",
    [
        b"/Users/private-example/source.txt",
        b"file:///private-example/source.txt",
        b"ghp_" + b"SYNTHETICTESTNOTREALTOKEN" * 2,
        b'"session_token": "synthetic-test-only"',
    ],
)
def test_share_rejects_private_content_in_non_data_assets(relative: str, private: bytes) -> None:
    with pytest.raises(ValueError, match="绝对路径|凭据"):
        _validate_static_resources({
            "overview.html": b"<!doctype html><title>report</title>",
            relative: private,
        })


def test_share_keeps_bare_protocol_comment_and_external_source_links() -> None:
    _validate_static_resources({
        "overview.html": (
            b'<a href="https://clinicaltrials.gov/">original source</a>'
            b'<script src="assets/local.js"></script>'
        ),
        "assets/local.js": b"// Works from file://.\nwindow.ready = true;",
    })
