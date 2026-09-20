"""Task 5.4：A 类完整多页面门户的产物与内容责任合同。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ci_workflow.application.fixture_runner import run_fixture_case
from ci_workflow.domain.enums import ReportKind
from ci_workflow.qc.browser import enumerate_site_routes


@pytest.fixture(scope="module")
def a_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("a-complete")
    result = run_fixture_case(
        "a-complete",
        project_root=root,
        reports=["A"],
        outputs=["html"],
    )
    assert result.run_result.outcome == "completed"
    return root


def _site(project: Path) -> Path:
    return project / "reports/A/v-fixture-001/html"


def _text(project: Path, relative: str) -> str:
    return (_site(project) / relative).read_text(encoding="utf-8")


def _manifest(project: Path) -> dict[str, object]:
    return json.loads(
        (project / "reports/A/v-fixture-001/html.manifest.json").read_text(encoding="utf-8")
    )


def test_a_landscape_page_keeps_every_in_scope_innovative_product(a_project: Path) -> None:
    html = _text(a_project, "landscape.html")
    products = _manifest(a_project)["product_ids"]
    assert isinstance(products, list) and len(products) >= 4
    for product_id in products:
        assert f'data-product-id="{product_id}"' in html
    assert "全部创新治疗项目" in html
    assert "Top-N" not in html


def test_a_products_page_links_every_product_dossier(a_project: Path) -> None:
    html = _text(a_project, "product-overview.html")
    products = _manifest(a_project)["product_ids"]
    assert isinstance(products, list)
    for product_id in products:
        assert f'href="products/{product_id}.html"' in html


def test_a_regulatory_page_separates_china_and_global_status(a_project: Path) -> None:
    html = _text(a_project, "regulatory.html")
    assert 'data-region-track="中国"' in html
    assert 'data-region-track="境外"' in html
    assert "中国开发与监管" in html
    assert "全球开发与监管" in html


def test_a_companies_deals_page_preserves_relationship_and_transaction_evidence(
    a_project: Path,
) -> None:
    html = _text(a_project, "companies-transactions.html")
    assert "企业关系" in html
    assert "地域权益" in html
    assert "公开交易" in html
    assert "许可方" in html and "被许可方" in html


def test_a_patents_page_preserves_family_jurisdiction_and_expiry_state(
    a_project: Path,
) -> None:
    html = _text(a_project, "patents-protection.html")
    assert "专利族" in html and "法域" in html and "期限状态" in html
    assert "监管独占" in html


def test_a_history_edge_page_keeps_suspended_terminated_and_withdrawn_programs(
    a_project: Path,
) -> None:
    html = _text(a_project, "historical-edge.html")
    assert "暂停" in html and "终止" in html and "撤回" in html
    assert "历史与边缘观察" in html


def test_a_site_contains_exactly_eleven_static_pages_plus_every_product(
    a_project: Path,
) -> None:
    routes = enumerate_site_routes(_site(a_project), ReportKind.A)
    manifest = _manifest(a_project)
    products = manifest["product_ids"]
    assert isinstance(products, list)
    assert len(routes) == 11 + len(products)
    assert not any("/trials/" in route for route in routes)


def test_a_matrix_source_has_real_treatment_group_sample_sizes(a_project: Path) -> None:
    data = json.loads(
        (a_project / "evidence/library/report-data.json").read_text(encoding="utf-8")
    )
    for trial in data["trials"]:
        assert 0 < trial["treatment_sample_size"] <= trial["sample_size"]
