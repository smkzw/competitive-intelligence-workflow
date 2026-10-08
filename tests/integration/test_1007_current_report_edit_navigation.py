"""Manifest-bound current reports/editor; HTTP proof, never browser acceptance."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
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


def test_editor_lists_existing_current_reports_and_serves_version_bound_pages(
    tmp_path: Path,
) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB", include_b_efficacy=True)
    service = UserFactEditService(root)
    before = service.read_current_delivery()
    db_hash = hashlib.sha256((root / "state/project.sqlite").read_bytes()).hexdigest()
    with LoopbackEditServer(service) as server:
        headers, envelope = _open(server)
        assert {item["report"] for item in envelope["report_links"]} == {"A", "B", "C"}
        for link in envelope["report_links"]:
            status, response_headers, page = _request_http(
                server, "GET", link["href"], headers=headers
            )
            assert status == 200
            assert response_headers["cross-origin-resource-policy"] == "same-origin"
            assert (
                "script-src 'self' 'unsafe-inline'" in response_headers["content-security-policy"]
            )
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


@pytest.mark.parametrize(
    "tail",
    (
        "../../state/project.sqlite",
        "%2e%2e/%2e%2e/state/project.sqlite",
        "%252e%252e/state/project.sqlite",
        "assets%5cportal.js",
        "state/project.sqlite",
        "data/render-context.json",
        "data/consumer-receipt.json",
        "missing.html",
        "assets/../overview.html",
        "assets%2f..%2foverview.html",
        "overview.html%00",
        "/overview.html",
        "data/identity-context.json",
        "data/identity-projection.json",
    ),
)
def test_current_report_routes_never_become_an_arbitrary_file_server(
    tmp_path: Path, tail: str
) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    digest = current_bundle_sha256(service.read_current_delivery())
    with LoopbackEditServer(service) as server:
        headers, _ = _open(server)
        status, _, _ = _request_http(server, "GET", f"/reports/{digest}/A/{tail}", headers=headers)
        assert status == 404


def test_current_reports_reject_bad_host_missing_session_old_generation_and_tampered_asset(
    tmp_path: Path,
) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    current = service.read_current_delivery()
    digest = current_bundle_sha256(current)
    path = f"/reports/{digest}/A/overview.html"
    with LoopbackEditServer(service) as server:
        headers, _ = _open(server)
        assert _request_http(server, "GET", path, headers={"Host": "evil.example"})[0] == 403
        assert _request_http(server, "GET", path, headers={"Host": headers["Host"]})[0] == 403
        assert (
            _request_http(server, "GET", path.replace(digest, "0" * 64), headers=headers)[0] == 409
        )
        item = next(report for report in current.reports if report.report == "A")
        (root / item.site_relative_path / "assets/portal.js").write_bytes(b"tampered")
        assert _request_http(server, "GET", path, headers=headers)[0] == 409


def test_report_targets_reuse_explicit_b_view_identity_and_post_save_renew_links(
    tmp_path: Path,
) -> None:
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
        assert any(
            item["row_id"] == "eff-row-nct04558918-apply-treatment"
            and item["fact_id"] == "fact-b-estimated-efficacy"
            for item in context["bindings"]
        )
        # Read -> edit uses the existing protected save endpoint, not a second write path.
        _, get_headers, _ = _request_http(server, "GET", "/", headers={"Host": headers["Host"]})
        status, _, result = _request_http(
            server,
            "POST",
            "/api/save",
            body=_command().model_dump_json(exclude_unset=True).encode(),
            headers={
                "Host": headers["Host"],
                "Origin": "http://" + headers["Host"],
                "Cookie": get_headers["set-cookie"].split(";", 1)[0],
                "X-CSRF-Token": get_headers["x-csrf-token"],
                "Content-Type": "application/json",
            },
        )
        assert status == 200
        reply = json.loads(result)
        assert reply["current_revision"] == 1
        assert all(link["href"] != original_links[link["report"]] for link in reply["report_links"])
        assert _request_http(server, "GET", original_links["A"], headers=headers)[0] == 409
        old_generation = original_links["A"].split("/")[2]
        assert (
            _request_http(
                server,
                "GET",
                f"/?fact=fact-crude-rate&generation={old_generation}",
                headers=headers,
            )[0]
            == 409
        )
        for link in reply["report_links"]:
            status, _, page = _request_http(server, "GET", link["href"], headers=headers)
            assert status == 200
            marker = re.search(rb'<script id="ci-current-edit"[^>]*>(.*?)</script>', page, re.S)
            assert marker is not None
            context = json.loads(marker[1])
            assert context["revision"] == 1
            if link["report"] == "B":
                assert any(
                    item["row_id"] == "eff-row-nct04558918-apply-treatment"
                    and item["fact_id"] == "fact-b-estimated-efficacy"
                    for item in context["bindings"]
                )
            if link["report"] == "C":
                assert any(item["collection"] == "observations" for item in context["bindings"])


@pytest.mark.parametrize("declarations", (None, "legacy", ["legacy"], [{"report": "A"}]))
def test_bad_legacy_binding_returns_conflict_not_dropped_connection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    declarations: object,
) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    with LoopbackEditServer(service) as server:
        headers, envelope = _open(server)
        facts = service.current_facts()
        facts["fact-unrelated-20"]["consumer_bindings"] = declarations
        monkeypatch.setattr(service, "current_facts", lambda: facts)
        status, _, body = _request_http(
            server, "GET", envelope["report_links"][0]["href"], headers=headers
        )
        assert status == 409
        assert json.loads(body)["error"] == "当前交付未能完整核验"


def test_empty_generation_and_nonascii_csrf_fail_closed(tmp_path: Path) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    before = service.read_current_delivery()
    with LoopbackEditServer(service) as server:
        headers, _ = _open(server)
        assert _request_http(server, "GET", "/?generation=", headers=headers)[0] == 409
        status, _, _ = _request_http(
            server,
            "POST",
            "/api/save",
            body=b"{}",
            headers={
                **headers,
                "Origin": "http://" + headers["Host"],
                "X-CSRF-Token": "\xe9",
                "Content-Type": "application/json",
            },
        )
        assert status == 403
    assert service.read_current_delivery() == before


def test_current_report_rejects_symlinks_without_exposing_target(tmp_path: Path) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    current = service.read_current_delivery()
    with LoopbackEditServer(service) as server:
        headers, envelope = _open(server)
        link = next(link for link in envelope["report_links"] if link["report"] == "A")
        item = next(item for item in current.reports if item.report == "A")
        target = root / item.site_relative_path / "assets/portal.js"
        target.unlink()
        target.symlink_to(root / "state/project.sqlite")
        status, _, body = _request_http(server, "GET", link["href"], headers=headers)
        assert status == 409 and b"SQLite format" not in body


def test_production_shared_edit_links_keep_all_exact_targets_and_static_shares_readonly() -> None:
    author = Path(__file__).resolve().parents[2] / "src/ci_workflow/renderers/portal/assets"
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const text=fs.readFileSync(process.argv[1],'utf8');
const start=text.indexOf('  function appendCurrentFactEditLinks(');
const end=text.indexOf('\n  window.__CURRENT_FACT_EDIT__',start);
assert.ok(start>=0&&end>start);
let marker=null;
function node(tag){return {tagName:tag,children:[],appendChild(n){this.children.push(n);}};}
const sandbox={document:{getElementById(){return marker;},createElement:node},JSON,Array,
 Object,encodeURIComponent};
vm.runInNewContext(text.slice(start,end),sandbox);
function links(row,collection){const parent=node('div');
 sandbox.appendCurrentFactEditLinks(parent,row,collection);
 return parent.children.map(n=>n.children[0]);}
assert.equal(links('r','efficacy').length,0); // offline has no injected edit capability
marker={textContent:JSON.stringify({generation:'a'.repeat(64),bindings:[
 {row_id:'r',collection:'efficacy',fact_id:'one&</script>'},
 {row_id:'r',collection:'efficacy',fact_id:'two'},
 {row_id:'r',collection:'efficacy',fact_id:'two'},
 {row_id:'r',collection:'safety',fact_id:'three'},
 {row_id:'other',collection:'efficacy',fact_id:'four'}]})};
assert.equal(links('r','efficacy').length,2);
assert.equal(links('r').length,3);
assert.equal(links('missing').length,0);
const first=links('r','efficacy')[0];
assert.equal(first.tagName,'a');
assert.equal(first.href,'/?fact=one%26%3C%2Fscript%3E&generation='+'a'.repeat(64));
assert.equal(first.textContent,'修订当前疗效事实');
marker={textContent:'not-json'};assert.equal(links('r').length,0);
marker={textContent:JSON.stringify({generation:'bad',bindings:[]})};
assert.equal(links('r').length,0);
console.log('NODE-OK current edit links');
"""
    result = subprocess.run(
        ["node", "-e", script, str(author / "portal.js")], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert "NODE-OK current edit links" in result.stdout
    # Both real evidence adapters consume the one helper, not a parallel guessed mapping.
    assert (
        "__CURRENT_FACT_EDIT__(content, selectedRow.row_id, rowRef.collection)"
        in (author / "report-a.js").read_text()
    )
    assert (
        "__CURRENT_FACT_EDIT__(viewFields, view.row.row_id)"
        in (author / "evidence-drawer.js").read_text()
    )
