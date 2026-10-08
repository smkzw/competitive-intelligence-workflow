"""Manifest-bound current reports/editor; HTTP proof, never browser acceptance."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from ci_workflow.application.latest_delivery import current_bundle_sha256
from ci_workflow.application.user_fact_edit import UserFactEditService
from ci_workflow.application.user_fact_edit_server import LoopbackEditServer
from tests.integration.test_w04_user_fact_edit import (
    _command,
    _project,
    _request_http,
)


def _open(server: LoopbackEditServer) -> tuple[dict[str, str], dict[str, object]]:
    host = f"127.0.0.1:{server.port}"
    status, headers, page = _request_http(server, "GET", "/", headers={"Host": host})
    assert status == 200
    match = re.search(rb'<script id="facts" type="application/json">(.*?)</script>', page, re.S)
    assert match is not None
    envelope = json.loads(match[1])
    return {"Host": host, "Cookie": headers["set-cookie"].split(";", 1)[0]}, envelope


def test_editor_lists_existing_current_reports_and_serves_version_bound_pages(tmp_path: Path) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB", include_b_efficacy=True)
    service = UserFactEditService(root)
    before = service.read_current_delivery()
    db_hash = hashlib.sha256((root / "state/project.sqlite").read_bytes()).hexdigest()
    with LoopbackEditServer(service) as server:
        headers, envelope = _open(server)
        assert {item["report"] for item in envelope["report_links"]} == {"A", "B", "C"}
        for link in envelope["report_links"]:
            status, response_headers, page = _request_http(server, "GET", link["href"], headers=headers)
            assert status == 200
            assert response_headers["cross-origin-resource-policy"] == "same-origin"
            assert "script-src 'self' 'unsafe-inline'" in response_headers["content-security-policy"]
            marker = re.search(rb'<script id="ci-current-edit"[^>]*>(.*?)</script>', page, re.S)
            assert marker is not None
            context = json.loads(marker[1])
            assert context["revision"] == before.revision
            assert context["generation"] == current_bundle_sha256(before)
            assert context["report"] == link["report"]
            assert "csrf" not in context and "project_root" not in context
        a_link = next(link for link in envelope["report_links"] if link["report"] == "A")
        prefix = a_link["href"].rsplit("/", 1)[0]
        status, _, js = _request_http(server, "GET", prefix + "/assets/portal.js", headers=headers)
        assert status == 200
        current_a = next(item for item in before.reports if item.report == "A")
        assert js == (root / current_a.site_relative_path / "assets/portal.js").read_bytes()
    assert service.read_current_delivery() == before
    assert hashlib.sha256((root / "state/project.sqlite").read_bytes()).hexdigest() == db_hash


@pytest.mark.parametrize("tail", (
    "../../state/project.sqlite", "%2e%2e/%2e%2e/state/project.sqlite",
    "%252e%252e/state/project.sqlite", "assets%5cportal.js", "state/project.sqlite",
    "data/render-context.json", "data/consumer-receipt.json", "missing.html",
))
def test_current_report_routes_never_become_an_arbitrary_file_server(tmp_path: Path, tail: str) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    digest = current_bundle_sha256(service.read_current_delivery())
    with LoopbackEditServer(service) as server:
        headers, _ = _open(server)
        status, _, _ = _request_http(server, "GET", f"/reports/{digest}/A/{tail}", headers=headers)
        assert status == 404


def test_current_reports_reject_bad_host_missing_session_old_generation_and_tampered_asset(tmp_path: Path) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    current = service.read_current_delivery()
    digest = current_bundle_sha256(current)
    path = f"/reports/{digest}/A/overview.html"
    with LoopbackEditServer(service) as server:
        headers, _ = _open(server)
        assert _request_http(server, "GET", path, headers={"Host": "evil.example"})[0] == 403
        assert _request_http(server, "GET", path, headers={"Host": headers["Host"]})[0] == 403
        assert _request_http(server, "GET", path.replace(digest, "0" * 64), headers=headers)[0] == 409
        item = next(report for report in current.reports if report.report == "A")
        (root / item.site_relative_path / "assets/portal.js").write_bytes(b"tampered")
        assert _request_http(server, "GET", path, headers=headers)[0] == 409


def test_report_targets_reuse_explicit_b_view_identity_and_post_save_renew_links(tmp_path: Path) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB", include_b_efficacy=True)
    service = UserFactEditService(root)
    with LoopbackEditServer(service) as server:
        headers, envelope = _open(server)
        original_links = {link["report"]: link["href"] for link in envelope["report_links"]}
        status, _, page = _request_http(server, "GET", original_links["B"], headers=headers)
        assert status == 200
        match = re.search(rb'<script id="ci-current-edit"[^>]*>(.*?)</script>', page, re.S)
        assert match is not None
        context = json.loads(match[1])
        assert any(item["row_id"] == "eff-row-nct04558918-apply-treatment"
                   and item["fact_id"] == "fact-estimated-efficacy" for item in context["bindings"])
        # Read -> edit uses the existing protected save endpoint, not a second write path.
        _, get_headers, _ = _request_http(server, "GET", "/", headers={"Host": headers["Host"]})
        status, _, result = _request_http(server, "POST", "/api/save",
            body=_command().model_dump_json(exclude_unset=True).encode(),
            headers={"Host": headers["Host"], "Origin": "http://" + headers["Host"],
                     "Cookie": get_headers["set-cookie"].split(";", 1)[0],
                     "X-CSRF-Token": get_headers["x-csrf-token"], "Content-Type": "application/json"})
        assert status == 200
        reply = json.loads(result)
        assert reply["current_revision"] == 1
        assert all(link["href"] != original_links[link["report"]] for link in reply["report_links"])
        assert _request_http(server, "GET", original_links["A"], headers=headers)[0] == 409
        assert _request_http(server, "GET", reply["report_links"][0]["href"], headers=headers)[0] == 200
