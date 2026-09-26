"""Task 6.9：B 类完整门户的静态路由、事实绑定与清单 RED 合同。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.domain.enums import ReportKind
from ci_workflow.qc.browser import enumerate_site_routes, route_to_site_path
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
from ci_workflow.reports.common.page_registry import PageRegistry

ROOT = Path(__file__).resolve().parents[3]
SYNTHETIC_REPORT_DATA = ROOT / "fixtures/synthetic/a-complete/inputs/report-data.json"

B_CORE_FACT_PAGES = (
    "overview",
    "efficacy",
    "longitudinal-results",
    "safety",
    "baseline-overview",
    "disposition-overview",
    "efficacy-safety-matrix",
)


def _load_portal_payload() -> dict[str, Any]:
    """Use a small deterministic fixture while retaining explicit zero/missing states."""
    payload = json.loads(SYNTHETIC_REPORT_DATA.read_text(encoding="utf-8"))
    safety = [dict(row) for row in payload["safety"]]
    safety[0].update(value=0, disclosure_state="已公开")
    safety[1].update(value=None, disclosure_state="未公开")
    payload["safety"] = safety
    return payload


@pytest.fixture(scope="module")
def b_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("b-report-portal") / "html"
    data = ReportBPortalData.model_validate(_load_portal_payload())
    render_report_b_site(data, root)
    return root


@pytest.fixture(scope="module")
def b_payload() -> dict[str, Any]:
    return _load_portal_payload()


def _text(site: Path, relative: str) -> str:
    return (site / relative).read_text(encoding="utf-8")


def _json_assignment(html: str, name: str) -> Any:
    match = re.search(
        rf"window\.{re.escape(name)}\s*=\s*(\[.*?\]);",
        html,
        flags=re.S,
    )
    assert match is not None, name
    return json.loads(match.group(1))




def _sitemap(site: Path) -> dict[str, Any]:
    return json.loads((site / "data/sitemap.json").read_text(encoding="utf-8"))


def _report_literal(site: Path) -> dict[str, Any]:
    source = (site / "data/report.js").read_text(encoding="utf-8")
    marker = "window.REPORT_B="
    assert marker in source
    raw = source.split(marker, 1)[1].lstrip()
    value, _ = json.JSONDecoder().raw_decode(raw)
    assert isinstance(value, dict)
    return value


def _page_json_assignment(site: Path, relative: str, name: str) -> Any:
    return _json_assignment(_text(site, relative), name)


def test_partial_precise_view_keeps_all_related_rows_in_physical_b_pages(
    tmp_path: Path,
) -> None:
    payload = _load_portal_payload()
    payload["efficacy_views"] = {
        "coverage_mode": "partial",
        "facts": [{
            **payload["efficacy"][0], "source_version_id": "verified-efficacy",
            "source_text": "68.4",
            "source_locator": {
                "document_role": "registry", "field_path": "$.results.efficacy[0].value",
                "url": "https://example.org/study/1",
            },
        }],
    }
    payload["safety_views"] = {
        "coverage_mode": "partial",
        "facts": [{
            **payload["safety"][0], "source_version_id": "verified-safety",
            "source_text": "0",
            "source_locator": {
                "document_role": "registry", "field_path": "$.results.safety[0].value",
                "url": "https://example.org/study/1",
            },
        }],
    }
    payload["efficacy"][1].update({
        "source_version_id": "verified-field-only",
        "source_field_path": "$.results.efficacy[1].value",
        "source_text": "31.2",
    })
    site = tmp_path / "b-partial"
    render_report_b_site(ReportBPortalData.model_validate(payload), site)

    efficacy = _page_json_assignment(site, "efficacy.html", "__EVIDENCE_VIEWS__")
    safety = _page_json_assignment(site, "safety.html", "__EVIDENCE_VIEWS__")
    assert {view["row"]["row_id"] for view in efficacy} == {
        row["row_id"] for row in payload["efficacy"]
    }
    assert {view["row"]["row_id"] for view in safety} == {
        row["row_id"] for row in payload["safety"]
    }
    assert any(
        view["source_version_id"] == "verified-efficacy" for view in efficacy
    )
    precise_id = payload["efficacy"][0]["row_id"]
    field_only_id = payload["efficacy"][1]["row_id"]
    pending_id = payload["efficacy"][2]["row_id"]
    precise = next(view for view in efficacy if view["row"]["row_id"] == precise_id)
    field_only = next(view for view in efficacy if view["row"]["row_id"] == field_only_id)
    pending = next(view for view in efficacy if view["row"]["row_id"] == pending_id)
    assert precise["source_trace_state"] == "located"
    assert precise["original_text"] == "68.4"
    assert precise["locator"]["field_path"] == "$.results.efficacy[0].value"
    assert field_only["source_trace_state"] == "located"
    assert field_only["locator"]["field_path"] == "$.results.efficacy[1].value"
    assert field_only["locator"]["url"] is None
    assert field_only["locator"]["document_role"] == "source_record"
    assert pending["source_trace_state"] == "unverified"
    assert pending["source_version_id"] is None
    assert pending["locator"] is None
    assert pending["original_text"] is None
    assert pending["source_version_label_zh"] == "逐事实来源待核"
    assert pending["row"]["disclosure_state"] == "reported_value"


def test_b_sitemap_expands_every_static_product_and_trial_route(
    b_site: Path, b_payload: dict[str, Any]
) -> None:
    """B 目录全量展开：21 个静态页 + 每个产品和每个试验详情页。"""
    products = tuple(row["id"] for row in b_payload["products"])
    trials = tuple(row["id"] for row in b_payload["trials"])
    registry = PageRegistry.load()
    catalog = registry.catalog(ReportKind.B)
    expected = registry.sitemap(
        ReportKind.B,
        product_ids=products,
        trial_ids=trials,
    )

    sitemap = _sitemap(b_site)
    entries = sitemap["routes"]
    assert isinstance(entries, list)
    listed = tuple(item["route"] for item in entries)
    assert set(listed) == set(expected)
    assert len(listed) == len(catalog.pages) + len(products) + len(trials)
    assert len(set(listed)) == len(listed)

    physical = tuple(enumerate_site_routes(b_site, ReportKind.B))
    assert set(physical) == set(expected)
    for route in expected:
        assert (b_site / route_to_site_path(route)).is_file(), route


def test_b_profile_index_links_every_product_and_trial_dossier(
    b_site: Path, b_payload: dict[str, Any]
) -> None:
    html = _text(b_site, "product-trial-profiles.html")
    for product in b_payload["products"]:
        assert f'href="products/{product["id"]}.html"' in html
    for trial in b_payload["trials"]:
        assert f'href="trials/{trial["id"]}.html"' in html

    for product in b_payload["products"]:
        dossier = _text(b_site, f'products/{product["id"]}.html')
        assert f'data-product-id="{product["id"]}"' in dossier
        assert "产品档案" in dossier
        assert "疗效" in dossier and "安全性" in dossier
    for trial in b_payload["trials"]:
        dossier = _text(b_site, f'trials/{trial["id"]}.html')
        assert f'data-trial-id="{trial["id"]}"' in dossier
        assert "试验档案" in dossier
        assert "疗效" in dossier and "安全性" in dossier


def test_b_core_pages_install_chart_data_before_complete_table_shell(b_site: Path) -> None:
    """图表输入、完整表格壳和证据抽屉必须由同一稳定行集驱动。"""
    for page_id in B_CORE_FACT_PAGES:
        relative = f"{page_id}.html"
        html = _text(b_site, relative)
        chart_shell = re.search(
            r'(?:id="kz-chart-module"|class="[^"]*kz-chart[^"]*"|data-chart-id=)',
            html,
        )
        assert chart_shell is not None, page_id
        assert "window.__CHART_GROUPS__" in html, page_id
        assert "window.__EVIDENCE_VIEWS__" in html, page_id
        # 完整表格由离线脚本在此壳中生成；浏览器合同核验实际 DOM 顺序。

        groups = _page_json_assignment(b_site, relative, "__CHART_GROUPS__")
        evidence = _page_json_assignment(b_site, relative, "__EVIDENCE_VIEWS__")
        chart_row_ids = {
            row["row_id"]
            for group in groups
            for row in group.get("rows", [])
            if isinstance(row, dict) and row.get("row_id")
        }
        evidence_row_ids = {
            view["row"]["row_id"]
            for view in evidence
            if isinstance(view, dict)
            and isinstance(view.get("row"), dict)
            and view["row"].get("row_id")
        }
        assert chart_row_ids, page_id
        assert chart_row_ids <= evidence_row_ids, page_id


def test_b_report_payload_preserves_stable_rows_evidence_and_zero_missing_states(
    b_site: Path,
) -> None:
    report = _report_literal(b_site)
    safety = report["safety"]
    by_id = {row["row_id"]: row for row in safety}

    assert by_id["safe-fixture-teae"]["value"] == 0
    assert by_id["safe-fixture-teae"]["disclosure_state"] in {"已公开", "reported_zero"}
    assert by_id["safe-fixture-sae"]["value"] is None
    assert by_id["safe-fixture-sae"]["disclosure_state"] in {
        "未公开",
        "not_publicly_disclosed",
        "not_reported",
    }

    for page_id in B_CORE_FACT_PAGES:
        relative = f"{page_id}.html"
        groups = _page_json_assignment(b_site, relative, "__CHART_GROUPS__")
        evidence = _page_json_assignment(b_site, relative, "__EVIDENCE_VIEWS__")
        ids = {
            row["row_id"]
            for group in groups
            for row in group.get("rows", [])
            if isinstance(row, dict) and row.get("row_id")
        }
        evidence_ids = {
            view["row"]["row_id"]
            for view in evidence
            if isinstance(view, dict)
            and isinstance(view.get("row"), dict)
            and view["row"].get("row_id")
        }
        assert ids, page_id
        assert ids <= evidence_ids, page_id


def test_b_pages_use_local_assets_and_native_chinese_audience_copy(b_site: Path) -> None:
    for html_path in sorted(b_site.rglob("*.html")):
        html = html_path.read_text(encoding="utf-8")
        assert 'lang="zh-CN"' in html
        assert "康哲药业" in html
        for src in re.findall(r'(?:src|href)="([^"]+)"', html):
            assert not src.startswith(("http:", "https:", "//")), (html_path, src)
        visible = re.sub(r"<script\b.*?</script>", "", html, flags=re.S | re.I)
        visible = re.sub(r"<style\b.*?</style>", "", visible, flags=re.S | re.I)
        visible = re.sub(r"<[^>]+>", "", visible)
        assert not re.search(
            r"(?:pipeline|backend|prompt|schema|debug|trace|gate|pending|工作流|提示词|后端|日志|占位)",
            visible,
            flags=re.I,
        ), html_path
