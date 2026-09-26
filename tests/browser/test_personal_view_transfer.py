"""Browser round trip for the shared A/B/C personal view control."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from zipfile import ZipFile

import pytest
from playwright.sync_api import sync_playwright

from ci_workflow.application.fixture_runner import run_fixture_case
from ci_workflow.application.latest_delivery import read_current_delivery
from ci_workflow.application.share_export import ShareViewSelection, _validate_view_selection
from ci_workflow.application.user_fact_edit import FactEdit, UserFactEditService
from ci_workflow.cli import main as cli_main
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
from ci_workflow.renderers.portal.report_c import ReportCPortalData, render_report_c_site
from tests.integration.test_w04_user_fact_edit import _command, _project

ROOT = Path(__file__).resolve().parents[2]
PORTAL = ROOT / "src/ci_workflow/renderers/portal/assets/portal.js"


def _page(path: Path, report: str, selected: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    asset = "assets/portal.js"
    body_attrs = (
        'data-report-version="site-identity" data-page-id="overview"'
        if report == "A"
        else ""
    )
    body_attrs += ' data-current-revision="2"'
    snapshot = "" if report == "A" else '<script>window.__SNAPSHOT_ID__="site-identity";</script>'
    pressed = "true" if selected else "false"
    path.write_text(
        f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<body class="kz-{report.lower()}-site" {body_attrs}>
<header><a class="site-header__logo" href="overview.html">首页</a></header>
<main id="main"><div data-filter-dimension="product">
<button data-filter-value="product-one" aria-pressed="{pressed}">产品一</button>
</div><div data-filter-dimension="trial">
<button data-filter-value="trial-one" aria-pressed="false">试验一</button>
</div></main>{snapshot}<script src="{asset}"></script></body></html>''',
        encoding="utf-8",
    )


@pytest.mark.parametrize("report", ["A", "B", "C"])
def test_personal_view_export_import_cross_page_and_reject_bad_file(
    tmp_path: Path, report: str
) -> None:
    site = tmp_path / report
    assets = site / "assets"
    assets.mkdir(parents=True)
    shutil.copyfile(PORTAL, assets / "portal.js")
    _page(site / "overview.html", report, selected=report == "A")
    _page(site / "efficacy.html", report)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        url = (site / "overview.html").as_uri()
        if report != "A":
            url += "?product=product-one"
        page.goto(url)
        with page.expect_download() as downloaded:
            page.get_by_role("button", name="导出配置").click()
        saved = tmp_path / f"{report}.json"
        downloaded.value.save_as(saved)
        bundle = json.loads(saved.read_text(encoding="utf-8"))
        assert bundle == {"schema_version": "1.0", "selections": [{
            "report": report,
            "revision": 2,
            "entry_page": "overview.html",
            "query": {"product": ["product-one"]},
        }]}
        selection = ShareViewSelection.model_validate(bundle["selections"][0])
        _validate_view_selection(selection, (site / "overview.html").read_bytes())
        assert str(tmp_path) not in saved.read_text(encoding="utf-8")
        assert "site-identity" not in saved.read_text(encoding="utf-8")

        fresh = browser.new_context()
        target = fresh.new_page()
        target.goto((site / "overview.html").as_uri())
        target.locator('input[aria-label="选择个人视图 JSON 文件"]').set_input_files(saved)
        target.wait_for_url("**/overview.html?product=product-one")
        target.goto((site / "efficacy.html").as_uri())
        assert "product=product-one" in target.url

        selection_json = bundle["selections"][0]
        for suffix, change in (
            ("revision", {**selection_json, "revision": 1}),
            ("string-revision", {**selection_json, "revision": "2"}),
            ("extra", {**selection_json, "script": "alert(1)"}),
            ("page", {**selection_json, "entry_page": "efficacy.html"}),
            ("report", {**selection_json, "report": "B" if report != "B" else "A"}),
            (
                "html",
                {
                    **selection_json,
                    "query": {"product": ["<img onerror=alert(1)>"]},
                },
            ),
            (
                "unknown",
                {**selection_json, "query": {"product": ["absent"]}},
            ),
            (
                "path",
                {**selection_json, "query": {"product": ["/Users/person/private.json"]}},
            ),
            (
                "credential",
                {**selection_json, "query": {"product": ["token=private"]}},
            ),
            (
                "function",
                {
                    **selection_json,
                    "query": {"product": ["function(){alert(1)}"]},
                },
            ),
        ):
            bad = tmp_path / f"bad-{report}-{suffix}.json"
            bad.write_text(
                json.dumps({"schema_version": "1.0", "selections": [change]}),
                encoding="utf-8",
            )
            target.goto((site / "overview.html").as_uri() + "?trial=trial-one")
            target.locator('input[aria-label="选择个人视图 JSON 文件"]').set_input_files(bad)
            target.get_by_role("status").wait_for()
            assert "trial=trial-one" in target.url
            assert "配置" in target.get_by_role("status").inner_text()
        fresh.close()
        context.close()
        browser.close()


def test_rendered_b_portal_uses_exported_filter_on_another_page(tmp_path: Path) -> None:
    payload = json.loads(
        (ROOT / "fixtures/positive/b-pnh/inputs/report-data.json").read_text(encoding="utf-8")
    )
    site = tmp_path / "rendered-b"
    render_report_b_site(ReportBPortalData.model_validate(payload), site)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(accept_downloads=True)
        page.goto((site / "overview.html").as_uri())
        filter_button = page.locator(
            'button[data-filter-dimension="product"][data-filter-value]'
        ).first
        assert filter_button.count() == 1
        value = filter_button.get_attribute("data-filter-value")
        assert value
        filter_button.click()
        assert value in page.url
        with page.expect_download() as downloaded:
            page.get_by_role("button", name="导出配置").click()
        saved = tmp_path / "rendered-b-view.json"
        downloaded.value.save_as(saved)
        exported = json.loads(saved.read_text(encoding="utf-8"))
        assert exported["selections"][0]["query"]["product"] == [value]
        assert exported["selections"][0]["revision"] == 0
        _validate_view_selection(
            ShareViewSelection.model_validate(exported["selections"][0]),
            (site / "overview.html").read_bytes(),
        )
        other = browser.new_context().new_page()
        other.goto((site / "overview.html").as_uri())
        other.locator('input[aria-label="选择个人视图 JSON 文件"]').set_input_files(saved)
        other.wait_for_url("**/overview.html?product=*")
        other.goto((site / "efficacy.html").as_uri())
        assert value in other.url
        assert other.locator(
            'button[data-filter-dimension="product"]'
            '[data-filter-value][aria-pressed="true"]'
        ).count() >= 1
        browser.close()


@pytest.mark.parametrize("report", ["A", "C"])
def test_rendered_a_c_pages_export_cli_view_config(tmp_path: Path, report: str) -> None:
    if report == "A":
        project = tmp_path / "a-project"
        result = run_fixture_case(
            "a-complete", project_root=project, reports=["A"], outputs=["html"]
        )
        assert result.run_result.outcome == "completed"
        site = project / "reports/A/v-fixture-001/html"
        second_page = "efficacy.html"
    else:
        data = ReportCPortalData.model_validate(json.loads(
            (ROOT / "fixtures/positive/c-atopic-dermatitis/inputs/report-data.json").read_text(
                encoding="utf-8"
            )
        ))
        site = tmp_path / "c-site"
        render_report_c_site(data, site)
        second_page = "inclusion-criteria.html"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(accept_downloads=True)
        page.goto((site / "overview.html").as_uri())
        assert page.locator("body").get_attribute("data-current-revision") == "0"
        with page.expect_download() as downloaded:
            page.get_by_role("button", name="导出配置").click()
        saved = tmp_path / f"rendered-{report}.json"
        downloaded.value.save_as(saved)
        config = json.loads(saved.read_text(encoding="utf-8"))
        assert set(config) == {"schema_version", "selections"}
        assert config["selections"][0]["revision"] == 0
        assert config["selections"][0]["entry_page"] == "overview.html"
        _validate_view_selection(
            ShareViewSelection.model_validate(config["selections"][0]),
            (site / "overview.html").read_bytes(),
        )
        page.goto((site / second_page).as_uri())
        assert page.locator("body").get_attribute("data-current-revision") == "0"
        assert page.get_by_role("button", name="导出配置").count() == 1
        browser.close()


@pytest.mark.parametrize("expected_revision", [0, 1])
def test_browser_download_is_direct_cli_input_for_committed_b_current(
    tmp_path: Path, expected_revision: int
) -> None:
    root, _ = _project(
        tmp_path, cross_report_binding="legal_AB" if expected_revision else None
    )
    if expected_revision:
        UserFactEditService(root).save(_command(
            request_id="browser-share-current-b",
            edits=FactEdit(numerator=24, denominator=62),
        ))
    current = read_current_delivery(root)
    assert current is not None and current.revision == expected_revision
    b_delivery = next(item for item in current.reports if item.report == "B")
    site = root / b_delivery.site_relative_path
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(accept_downloads=True)
        page.goto((site / "overview.html").as_uri())
        assert page.locator("body").get_attribute("data-current-revision") == str(expected_revision)
        button = page.locator(
            'button[data-filter-dimension="product"][data-filter-value]'
        ).first
        assert button.count() == 1
        button.click()
        with page.expect_download() as downloaded:
            page.get_by_role("button", name="导出配置").click()
        config = tmp_path / "downloaded-view.json"
        downloaded.value.save_as(config)
        browser.close()
    exported = json.loads(config.read_text(encoding="utf-8"))
    assert exported["selections"][0]["revision"] == expected_revision
    output = tmp_path / "from-browser.zip"
    assert cli_main([
        "project", "share", "--root", str(root), "--output", str(output),
        "--reports", "B", "--view-config", str(config),
    ]) == 0
    with ZipFile(output) as archive:
        manifest = json.loads(archive.read("share-manifest.json"))
        assert manifest["current_revision"] == expected_revision
        assert manifest["reports"]["B"]["entry_href"].startswith("B/overview.html?product=")


def test_unchanged_c_page_config_remains_shareable_in_newer_current(
    tmp_path: Path,
) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    UserFactEditService(root).save(_command(
        request_id="browser-share-current-c-unchanged",
        edits=FactEdit(numerator=24, denominator=62),
    ))
    current = read_current_delivery(root)
    assert current is not None and current.revision == 1
    c_delivery = next(item for item in current.reports if item.report == "C")
    assert c_delivery.revision == 0
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(accept_downloads=True)
        page.goto((root / c_delivery.site_relative_path / "overview.html").as_uri())
        assert page.locator("body").get_attribute("data-current-revision") == "0"
        with page.expect_download() as downloaded:
            page.get_by_role("button", name="导出配置").click()
        config = tmp_path / "unchanged-c.json"
        downloaded.value.save_as(config)
        browser.close()
    assert json.loads(config.read_text(encoding="utf-8"))["selections"][0]["revision"] == 0
    output = tmp_path / "unchanged-c.zip"
    assert cli_main([
        "project", "share", "--root", str(root), "--output", str(output),
        "--reports", "C", "--view-config", str(config),
    ]) == 0
    with ZipFile(output) as archive:
        manifest = json.loads(archive.read("share-manifest.json"))
        assert manifest["current_revision"] == 1
        assert manifest["reports"]["C"]["report_revision"] == 0
    stale = json.loads(config.read_text(encoding="utf-8"))
    stale["selections"][0]["revision"] = 1
    config.write_text(json.dumps(stale), encoding="utf-8")
    rejected = tmp_path / "wrong-c-revision.zip"
    assert cli_main([
        "project", "share", "--root", str(root), "--output", str(rejected),
        "--reports", "C", "--view-config", str(config),
    ]) == 2
    assert not rejected.exists()
