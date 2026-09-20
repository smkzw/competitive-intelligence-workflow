"""Task 4.6 全站浏览器验收：站点地图一一对应枚举合同（worker_01 sitemap 节点）。

RED→GREEN 顺序：本文件 sitemap 节点先于 ``src/ci_workflow/qc/browser.py``
的站点地图合同实现而失败（模块缺失即 RED），实现后全部通过（GREEN）。

站点地图合同 = 页面注册表全部静态责任页 + 锁定快照**每一个**产品/试验
动态详情页，集合一一对应。缺页、多页（重复）、Top-N 截断与额外 slug
均失败关闭；验收器只报告与否决，绝不修改被验收站点。

worker_02（只读缺陷检测）与 worker_03（CLI/多浏览器/截图/trace）在本
文件追加各自节点，不得重写本文件的 sitemap 合同。

worker_02 节点：死链、控制台/页面错误、非本地请求、页脚唯一性、横向
溢出与固定元素遮挡的观察模型、纯函数判定与真实壳层静态扫描验收；先
以缺失符号记录 RED，再实现 GREEN。

worker_03 节点：Chromium/WebKit 在 1280/1440/1920 的运行时失败测试
（``collect_page_runtime_observations`` 收集控制台/页面错误/溢出/遮挡，
``merge_page_observations`` 合并静态扫描与运行时观察）与
``tools/verify_portal.py`` CLI 的黑盒验收（中文缺失/非法输入说明、双
浏览器 × 三视口 × 全部路由遍历、原分辨率截图、带 run/site digest 的
交互 trace、失败关闭与只读站点保证）；先以缺失符号/缺失工具记录 RED，
再实现 GREEN。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from playwright.sync_api import Browser, Playwright, sync_playwright

from ci_workflow.domain.enums import ReportKind
from ci_workflow.domain.ids import stable_id
from ci_workflow.qc.browser import (
    DEFAULT_VIEWPORTS,
    ConsoleObservation,
    DefectViolationCode,
    LayoutObservation,
    LinkObservation,
    OcclusionObservation,
    PageErrorObservation,
    PageInspection,
    ReachabilityViolationCode,
    Rect,
    RequestObservation,
    SitemapBoundaryError,
    SitemapContract,
    SitemapKind,
    SitemapViolationCode,
    collect_page_runtime_observations,
    derive_sitemap_contract,
    enumerate_site_routes,
    merge_page_observations,
    resolve_local_link,
    route_to_site_path,
    scan_page_html,
    site_directory_digest,
    site_path_to_route,
    verify_page_defects,
    verify_portal_defects,
    verify_route_reachability,
    verify_sitemap_one_to_one,
)
from ci_workflow.renderers.portal import PageSpec, PortalSpec, build_portal
from ci_workflow.renderers.portal.global_search import build_search_index
from ci_workflow.renderers.portal.page_shell import render_page_html
from ci_workflow.reports.common.page_registry import PageRegistry
from ci_workflow.storage.manifest_store import ArtifactManifest
from ci_workflow.storage.snapshot_store import ReportSnapshotManifest

PRODUCT_IDS = ("product-01", "product-02", "product-03")
TRIAL_IDS = ("trial-01", "trial-02")


def _contract(report: ReportKind) -> SitemapContract:
    return derive_sitemap_contract(
        PageRegistry.load(),
        report,
        product_ids=PRODUCT_IDS,
        trial_ids=TRIAL_IDS,
    )


def _static_ids(report: ReportKind) -> tuple[str, ...]:
    catalog = PageRegistry.load().catalog(report)
    return tuple(sorted(page.id for page in catalog.pages))


# ─── 期望站点地图：静态责任页 + 快照每一个产品/试验详情页 ───────────────


@pytest.mark.parametrize("report", [ReportKind.A, ReportKind.B, ReportKind.C])
def test_expected_sitemap_covers_every_static_and_every_detail_page(
    report: ReportKind,
) -> None:
    """期望 sitemap = 全部静态责任页 + 快照每一个产品/试验详情页（无 Top-N）。"""
    registry = PageRegistry.load()
    contract = _contract(report)
    catalog = registry.catalog(report)

    static_routes = {page.route for page in catalog.pages}
    assert contract.static_routes == static_routes
    assert len(contract.static_routes) == len(catalog.pages)

    for spec in catalog.dynamic_routes:
        if spec.identity_field == "product_id":
            expected = {spec.route_template.format(product_id=slug) for slug in PRODUCT_IDS}
            assert contract.product_routes == expected
        else:
            expected = {spec.route_template.format(trial_id=slug) for slug in TRIAL_IDS}
            assert contract.trial_routes == expected

    # 一一对应：提供的每一个身份都生成路由，绝不 Top-N 或固定示例。
    assert len(contract.routes) == len(set(contract.routes)), "期望站点地图不允许重复路由"
    assert len(contract.routes) == (
        len(catalog.pages) + len(contract.product_routes) + len(contract.trial_routes)
    )


def test_expected_sitemap_kind_classification() -> None:
    """静态/产品详情/试验详情三类路由的归属与页面责任一一对应。"""
    contract = _contract(ReportKind.A)

    by_route = {entry.route: entry for entry in contract.entries}
    overview = by_route["/a/overview"]
    assert overview.kind is SitemapKind.STATIC
    assert overview.page_responsibility_id == "overview"
    assert overview.identity is None

    product = by_route["/a/products/product-01"]
    assert product.kind is SitemapKind.PRODUCT_DETAIL
    assert product.page_responsibility_id == "product-overview"
    assert product.identity == "product-01"

    assert not contract.trial_routes

    # C 只有试验详情动态责任：提供的产品不产生任何产品路由。
    c_contract = _contract(ReportKind.C)
    assert c_contract.product_routes == frozenset()
    assert "/c/products/product-01" not in c_contract.routes
    assert "/c/trials/trial-01" in c_contract.routes


def test_expected_sitemap_is_deterministic_and_ordered() -> None:
    """同一输入两次展开结果一致；排序遵循注册表合同（静态责任页在前）。"""
    first = _contract(ReportKind.B)
    second = _contract(ReportKind.B)
    assert first == second
    assert first.routes == second.routes
    static = first.static_routes
    dynamic = [r for r in first.routes if r not in static]
    assert list(first.routes)[: len(static)] == sorted(static)
    assert dynamic == sorted(dynamic)


# ─── 一一对应验收：缺页、多页、Top-N、额外 slug 失败关闭 ─────────────────


def test_sitemap_verification_passes_when_sets_match_exactly() -> None:
    """期望与实际完全一致时验收通过，无任何违例。"""
    contract = _contract(ReportKind.A)
    result = verify_sitemap_one_to_one(contract, contract.routes)
    assert result.ok
    assert result.violations == ()
    assert "通过" in result.message_zh


def test_sitemap_fails_closed_when_static_page_missing() -> None:
    """缺少任一静态责任页必须失败关闭。"""
    contract = _contract(ReportKind.A)
    missing_route = "/a/regulatory"
    actual = tuple(r for r in contract.routes if r != missing_route)
    result = verify_sitemap_one_to_one(contract, actual)
    assert not result.ok
    codes = {v.code for v in result.violations}
    assert SitemapViolationCode.MISSING_STATIC_PAGE in codes
    assert any(v.route == missing_route for v in result.violations)
    assert "缺少静态责任页" in result.message_zh


def test_sitemap_fails_closed_when_product_detail_missing() -> None:
    """缺少任一产品详情页必须失败关闭。"""
    contract = _contract(ReportKind.B)
    missing_route = "/b/products/product-02"
    actual = tuple(r for r in contract.routes if r != missing_route)
    result = verify_sitemap_one_to_one(contract, actual)
    assert not result.ok
    codes = {v.code for v in result.violations}
    assert SitemapViolationCode.MISSING_PRODUCT_DETAIL in codes
    assert any(v.route == missing_route for v in result.violations)


def test_sitemap_fails_closed_when_trial_detail_missing() -> None:
    """缺少任一试验详情页必须失败关闭。"""
    contract = _contract(ReportKind.C)
    missing_route = "/c/trials/trial-02"
    actual = tuple(r for r in contract.routes if r != missing_route)
    result = verify_sitemap_one_to_one(contract, actual)
    assert not result.ok
    codes = {v.code for v in result.violations}
    assert SitemapViolationCode.MISSING_TRIAL_DETAIL in codes
    assert any(v.route == missing_route for v in result.violations)


def test_sitemap_fails_closed_on_top_n_truncation() -> None:
    """只保留前 N 个详情页（Top-N 截断）必须失败关闭，不得静默放行。"""
    contract = _contract(ReportKind.A)
    static = tuple(r for r in contract.routes if "/products/" not in r and "/trials/" not in r)
    truncated = (*static, "/a/products/product-01")
    result = verify_sitemap_one_to_one(contract, truncated)
    assert not result.ok
    codes = {v.code for v in result.violations}
    assert SitemapViolationCode.MISSING_PRODUCT_DETAIL in codes
    assert len([v for v in result.violations if v.route.startswith("/a/products/")]) == 2


def test_sitemap_fails_closed_on_extra_slug_and_page() -> None:
    """额外 slug（详情页）与站点地图之外的页面都必须失败关闭。"""
    contract = _contract(ReportKind.A)
    extra = (*contract.routes, "/a/products/ghost-slug", "/a/unknown-page")
    result = verify_sitemap_one_to_one(contract, extra)
    assert not result.ok
    codes = {v.code for v in result.violations}
    assert SitemapViolationCode.EXTRA_ROUTE in codes
    extra_routes = {
        v.route for v in result.violations if v.code is SitemapViolationCode.EXTRA_ROUTE
    }
    assert extra_routes == {"/a/products/ghost-slug", "/a/unknown-page"}
    assert "站点地图之外" in result.message_zh


def test_sitemap_fails_closed_on_duplicate_actual_route() -> None:
    """同一路由在实际产物中重复出现（多页）必须失败关闭。"""
    contract = _contract(ReportKind.A)
    duplicated = (*contract.routes, "/a/overview")
    result = verify_sitemap_one_to_one(contract, duplicated)
    assert not result.ok
    codes = {v.code for v in result.violations}
    assert SitemapViolationCode.DUPLICATE_ACTUAL_ROUTE in codes
    assert any(v.route == "/a/overview" for v in result.violations)


def test_sitemap_derivation_fails_closed_on_invalid_identity() -> None:
    """非法身份（路径穿越、中文、空白、重复）在合同推导时必须失败关闭。"""
    registry = PageRegistry.load()
    for bad in ("product/../01", "带中文", "", "a b", "-lead-dash", "with_underscore"):
        with pytest.raises(SitemapBoundaryError):
            derive_sitemap_contract(registry, ReportKind.A, product_ids=(bad,))
    with pytest.raises(SitemapBoundaryError, match="重复"):
        derive_sitemap_contract(registry, ReportKind.A, product_ids=("product-01", "product-01"))
    with pytest.raises(SitemapBoundaryError):
        derive_sitemap_contract(registry, ReportKind.B, trial_ids=("trial/../x",))


# ─── 物理产物站点枚举：路由 ↔ 站点文件一一对应 ──────────────────────────


def _write_site(site_root: Path, routes: tuple[str, ...]) -> None:
    for route in routes:
        path = site_root / route_to_site_path(route)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "<!doctype html><html lang='zh-CN'><head><title>页</title></head>"
            "<body><h1>责任页</h1></body></html>",
            encoding="utf-8",
        )


def test_route_to_site_path_maps_static_and_detail_layout() -> None:
    """路由到站点物理文件的确定性布局：静态平铺、动态按类目目录。"""
    assert route_to_site_path("/a/overview") == Path("overview.html")
    assert route_to_site_path("/a/products/product-01") == Path("products/product-01.html")
    assert route_to_site_path("/c/trials/trial-01") == Path("trials/trial-01.html")


def test_site_route_enumeration_and_full_acceptance(tmp_path: Path) -> None:
    """按布局写入的产物站点可枚举出完整路由并通过一一对应验收。

    篡改（缺页或额外页）后必须失败关闭。
    """
    site_root = tmp_path / "site"
    contract = _contract(ReportKind.A)
    _write_site(site_root, contract.routes)

    enumerated = enumerate_site_routes(site_root, ReportKind.A)
    assert set(enumerated) == set(contract.routes)
    result = verify_sitemap_one_to_one(contract, enumerated)
    assert result.ok

    # 缺页：删除一个静态责任页与一个产品详情页。
    (site_root / "regulatory.html").unlink()
    (site_root / "products" / "product-02.html").unlink()
    result = verify_sitemap_one_to_one(contract, enumerate_site_routes(site_root, ReportKind.A))
    assert not result.ok
    codes = {v.code for v in result.violations}
    assert SitemapViolationCode.MISSING_STATIC_PAGE in codes
    assert SitemapViolationCode.MISSING_PRODUCT_DETAIL in codes

    # 额外页：补回缺失页后加入幽灵详情页与未知静态页。
    _write_site(site_root, ("/a/regulatory", "/a/products/product-02"))
    _write_site(site_root, ("/a/products/ghost-slug", "/a/unknown-page"))
    result = verify_sitemap_one_to_one(contract, enumerate_site_routes(site_root, ReportKind.A))
    assert not result.ok
    codes = {v.code for v in result.violations}
    assert SitemapViolationCode.EXTRA_ROUTE in codes


# ─── 路由可达性：从站点入口沿本地锚点遍历（P1 修复） ────────────────────


def _reachability_contract() -> SitemapContract:
    """可达性测试合同：A 报告 + 1 产品（11 个静态页 + 1 个详情页）。"""
    return derive_sitemap_contract(
        PageRegistry.load(),
        ReportKind.A,
        product_ids=("product-01",),
        trial_ids=("trial-01",),
    )


def _scan_graph_contract(
    pages: dict[str, tuple[tuple[str, str], ...]],
) -> tuple[SitemapContract, tuple[PageInspection, ...]]:
    """把 {路由: ((href, 可见文本), ...)} 图转为合同与逐页静态扫描观察。

    站点内相对 href 按路由物理布局生成（平铺页直链详情子目录），与
    死链判定共用同一链接解析规则，不另设一套更弱的 URL 规则。
    """
    contract = _reachability_contract()
    inspections: list[PageInspection] = []
    for route in contract.routes:
        links = pages.get(route, ())
        html = (
            "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'></head>"
            "<body>"
            + "".join(f'<a href="{href}">{text}</a>' for href, text in links)
            + "</body></html>"
        )
        inspections.append(scan_page_html(html, route))
    return contract, tuple(inspections)


def _flat_href(route: str) -> str:
    """从平铺静态页到目标路由的相对 href（复用站点物理布局）。"""
    return route_to_site_path(route).as_posix()


def _reachable_routes() -> tuple[str, ...]:
    """全部可达目标路由：除入口外的全部静态责任页 + 1 个产品详情页。"""
    contract = _reachability_contract()
    return tuple(
        entry.route
        for entry in contract.entries
        if entry.kind is SitemapKind.STATIC and entry.route != "/a/overview"
    ) + ("/a/products/product-01",)


def test_site_path_route_round_trip() -> None:
    """站点物理文件与路由互转一一对应；非 HTML 文件不产生路由。"""
    for route in _contract(ReportKind.A).routes:
        assert site_path_to_route(route_to_site_path(route), ReportKind.A) == route
    assert site_path_to_route(Path("assets/portal.css"), ReportKind.A) is None


def test_reachability_all_expected_routes_reachable() -> None:
    """首页/总览直接或间接链接全部期望路由时，可达性验收通过。"""
    contract, inspections = _scan_graph_contract(
        {
            "/a/overview": tuple((_flat_href(target), target) for target in _reachable_routes()),
        }
    )
    result = verify_route_reachability(contract, inspections)
    assert result.ok, result.message_zh
    assert result.start_route == "/a/overview"
    assert result.unreachable_routes == ()
    assert set(result.reachable_routes) == set(contract.routes)
    assert "通过" in result.message_zh


def test_reachability_orphan_dynamic_page_fails_closed() -> None:
    """详情页文件存在但门户内没有任何入口（孤儿页）必须失败关闭。"""
    contract, inspections = _scan_graph_contract(
        {
            "/a/overview": tuple(
                (_flat_href(target), target)
                for target in _reachable_routes()
                if target != "/a/products/product-01"
            ),
        }
    )
    result = verify_route_reachability(contract, inspections)
    assert not result.ok
    assert result.unreachable_routes == ("/a/products/product-01",)
    codes = {v.code for v in result.violations}
    assert codes == {ReachabilityViolationCode.UNREACHABLE_ROUTE}
    assert "/a/products/product-01" in result.message_zh


def test_reachability_multi_hop_route_stays_reachable() -> None:
    """多跳可达（首页→产品总览→产品详情）通过。"""
    contract, inspections = _scan_graph_contract(
        {
            "/a/overview": tuple(
                (_flat_href(route), route)
                for route in _reachable_routes()
                if route != "/a/products/product-01"
            ),
            "/a/product-overview": ((_flat_href("/a/products/product-01"), "环柏单抗"),),
        }
    )
    # 详情页只能经中间静态页两跳到达：首页→产品总览→产品详情。
    result = verify_route_reachability(contract, inspections)
    assert result.ok, result.message_zh
    assert "/a/products/product-01" in result.reachable_routes


def test_reachability_external_fragment_mail_links_do_not_count() -> None:
    """站外、页内锚点与邮件链接不构成站点入口，也不能掩盖孤儿页。"""
    contract, inspections = _scan_graph_contract(
        {
            "/a/overview": (
                ("https://example.com/products/product-01.html", "站外详情"),
                ("#product-01", "页内锚点"),
                ("mailto:research@example.com", "联系医学部"),
            ),
        }
    )
    orphan_result = verify_route_reachability(contract, inspections)
    assert not orphan_result.ok
    assert "/a/products/product-01" in orphan_result.unreachable_routes

    # 补上有效本地入口后，同一页面可达；站外/锚点/邮件链接不破坏其余可达性。
    contract, inspections = _scan_graph_contract(
        {
            "/a/overview": tuple((_flat_href(route), route) for route in _reachable_routes())
            + (
                ("https://example.com/x.html", "站外"),
                ("#fragment", "锚点"),
                ("mailto:research@example.com", "邮件"),
            ),
        }
    )
    result = verify_route_reachability(contract, inspections)
    assert result.ok, result.message_zh
    assert "/a/products/product-01" in result.reachable_routes


def test_reachability_never_modifies_site_files(tmp_path: Path) -> None:
    """可达性验收只读：验收前后站点文件字节一致。"""
    site_root = tmp_path / "site"
    site_root.mkdir()
    (site_root / "overview.html").write_text(
        '<a href="product-overview.html">产品总览</a>', encoding="utf-8"
    )
    (site_root / "product-overview.html").write_text(
        '<a href="products/product-01.html">环柏单抗</a>', encoding="utf-8"
    )
    (site_root / "products").mkdir()
    (site_root / "products" / "product-01.html").write_text(
        '<a href="../overview.html">首页</a>', encoding="utf-8"
    )
    contract = derive_sitemap_contract(
        PageRegistry.load(),
        ReportKind.A,
        product_ids=("product-01",),
        trial_ids=(),
    )
    before = {
        path.relative_to(site_root): path.read_bytes()
        for path in site_root.rglob("*")
        if path.is_file()
    }
    inspections = tuple(
        scan_page_html(
            (site_root / route_to_site_path(route)).read_text(encoding="utf-8"),
            route,
        )
        for route in contract.routes
        if (site_root / route_to_site_path(route)).is_file()
    )
    result = verify_route_reachability(contract, inspections)
    assert "/a/products/product-01" in result.reachable_routes
    after = {
        path.relative_to(site_root): path.read_bytes()
        for path in site_root.rglob("*")
        if path.is_file()
    }
    assert before == after


# ─── 只读缺陷观察模型：封闭集合与边界校验（worker_02） ───────────────────


def test_observation_models_reject_invalid_input() -> None:
    """观察模型的非法输入（倒置矩形、未知类型、负页脚数）失败关闭。"""
    with pytest.raises(ValueError):
        Rect(top=10.0, left=0.0, right=100.0, bottom=5.0)
    with pytest.raises(ValueError):
        Rect(top=0.0, left=100.0, right=50.0, bottom=10.0)
    with pytest.raises(ValueError):
        ConsoleObservation(message_type="verbose", text="x")
    with pytest.raises(ValueError):
        RequestObservation(url="x", resource_type="websocket")
    with pytest.raises(ValueError):
        LayoutObservation(viewport_width=0.0, document_scroll_width=10.0)
    with pytest.raises(ValueError):
        PageInspection(route="/a/overview", footer_count=-1)
    with pytest.raises(ValueError):
        PageInspection(route=" ", links=())


def test_resolve_local_link_maps_page_relative_targets() -> None:
    """死链判定前的链接解析：相对目录、上级目录、站内绝对路径与回环地址。"""
    assert resolve_local_link("/a/products/product-01", "product-02.html") == Path(
        "products/product-02.html"
    )
    assert resolve_local_link("/a/products/product-01", "../overview.html") == Path("overview.html")
    assert resolve_local_link("/a/overview", "products/product-01.html") == Path(
        "products/product-01.html"
    )
    assert resolve_local_link("/a/overview", "/overview.html") == Path("overview.html")
    assert resolve_local_link("/a/overview", "http://127.0.0.1:8000/overview.html") == Path(
        "overview.html"
    )
    # 非页面链接：页内锚点、邮件、站外、脚本占位与未知协议不进入死链判定。
    assert resolve_local_link("/a/overview", "#section-2") is None
    assert resolve_local_link("/a/overview", "mailto:med@example.com") is None
    assert resolve_local_link("/a/overview", "https://pubmed.ncbi.nlm.nih.gov/") is None
    assert resolve_local_link("/a/overview", "javascript:void(0)") is None
    assert resolve_local_link("/a/overview", "ftp://example.com/file") is None


# ─── 死链：本地链接必须指向站点内真实页面（worker_02） ───────────────────


def test_dead_link_fails_closed_when_target_page_missing() -> None:
    """链接指向站点内不存在的页面必须失败关闭。"""
    valid = (Path("overview.html"), Path("products/product-01.html"))
    inspection = PageInspection(
        route="/a/overview",
        links=(LinkObservation(href="ghost.html", text="不存在页"),),
    )
    result = verify_page_defects(inspection, valid)
    assert not result.ok
    codes = {v.code for v in result.violations}
    assert DefectViolationCode.DEAD_LINK in codes
    assert "ghost.html" in result.message_zh
    assert "不存在页" in result.message_zh


def test_local_links_resolve_within_site_and_pass() -> None:
    """指向站点内真实页面的相对链接（同目录/上级/子目录）验收通过。"""
    valid = (
        Path("overview.html"),
        Path("products/product-01.html"),
        Path("products/product-02.html"),
    )
    from_detail = PageInspection(
        route="/a/products/product-01",
        links=(
            LinkObservation(href="../overview.html", text="首页"),
            LinkObservation(href="product-02.html", text="产品二"),
        ),
    )
    assert verify_page_defects(from_detail, valid).ok
    from_home = PageInspection(
        route="/a/overview",
        links=(LinkObservation(href="products/product-02.html", text="产品二"),),
    )
    assert verify_page_defects(from_home, valid).ok


def test_dead_link_fails_closed_when_escaping_site_root() -> None:
    """相对链接用 .. 逃出站点根目录必须失败关闭。"""
    inspection = PageInspection(
        route="/a/products/product-01",
        links=(LinkObservation(href="../../outside.html", text="外部页"),),
    )
    result = verify_page_defects(inspection, (Path("overview.html"),))
    assert not result.ok
    assert any(v.code is DefectViolationCode.DEAD_LINK for v in result.violations)


def test_fragment_mailto_and_external_links_are_not_dead() -> None:
    """页内锚点、邮件链接、站外链接与脚本占位不属于死链。"""
    inspection = PageInspection(
        route="/a/overview",
        links=(
            LinkObservation(href="#section-1", text="锚点"),
            LinkObservation(href="mailto:med@example.com", text="邮件"),
            LinkObservation(href="https://pubmed.ncbi.nlm.nih.gov/", text="文献库"),
            LinkObservation(href="javascript:void(0)", text="占位"),
        ),
    )
    assert verify_page_defects(inspection, (Path("overview.html"),)).ok


# ─── 控制台与页面错误：任何 error 即失败关闭（worker_02） ─────────────────


def test_console_error_fails_closed_but_warnings_do_not() -> None:
    """console.error 失败关闭；warning/log/info 不否决。"""
    inspection = PageInspection(
        route="/a/overview",
        console_messages=(
            ConsoleObservation(message_type="error", text="TypeError: x 不是函数"),
            ConsoleObservation(message_type="warning", text="已废弃 API"),
            ConsoleObservation(message_type="log", text="渲染完成"),
        ),
    )
    result = verify_page_defects(inspection, ())
    assert not result.ok
    assert [v.code for v in result.violations] == [DefectViolationCode.CONSOLE_ERROR]
    assert "TypeError" in result.message_zh


def test_page_error_fails_closed() -> None:
    """未捕获页面异常（页面错误）必须失败关闭。"""
    inspection = PageInspection(
        route="/a/overview",
        page_errors=(PageErrorObservation(text="ReferenceError: data 未定义"),),
    )
    result = verify_page_defects(inspection, ())
    assert not result.ok
    assert [v.code for v in result.violations] == [DefectViolationCode.PAGE_ERROR]
    assert "ReferenceError" in result.message_zh


# ─── 非本地请求：远程字体/脚本/图片与跨源请求失败关闭（worker_02） ───────


def test_remote_request_fails_closed_but_local_requests_pass() -> None:
    """远程字体/脚本/图片请求一律否决；相对、内联与回环请求通过。"""
    inspection = PageInspection(
        route="/a/overview",
        requests=(
            RequestObservation(url="assets/portal.css", resource_type="stylesheet"),
            RequestObservation(url="data:image/svg+xml,%3Csvg/%3E", resource_type="image"),
            RequestObservation(url="http://localhost:8000/portal.js", resource_type="script"),
            RequestObservation(
                url="https://fonts.googleapis.com/css2?family=Noto",
                resource_type="stylesheet",
            ),
            RequestObservation(
                url="https://cdn.example.com/echarts.min.js",
                resource_type="script",
            ),
        ),
    )
    result = verify_page_defects(inspection, ())
    assert not result.ok
    remote = [v for v in result.violations if v.code is DefectViolationCode.REMOTE_REQUEST]
    assert len(remote) == 2
    assert "fonts.googleapis.com" in result.message_zh


# ─── 页脚唯一性：每页恰好一个全局页脚（worker_02） ───────────────────────


def test_duplicate_footer_fails_closed() -> None:
    """同一页面出现多个全局页脚（重复 footer）必须失败关闭。"""
    inspection = PageInspection(route="/a/overview", footer_count=2)
    result = verify_page_defects(inspection, ())
    assert not result.ok
    assert [v.code for v in result.violations] == [DefectViolationCode.DUPLICATE_FOOTER]
    assert "2" in result.message_zh


def test_missing_footer_fails_closed() -> None:
    """页面缺少唯一全局页脚必须失败关闭。"""
    inspection = PageInspection(route="/a/overview", footer_count=0)
    result = verify_page_defects(inspection, ())
    assert not result.ok
    assert [v.code for v in result.violations] == [DefectViolationCode.MISSING_FOOTER]


def test_single_footer_passes() -> None:
    """每页恰好一个全局页脚时通过。"""
    inspection = PageInspection(route="/a/overview", footer_count=1)
    assert verify_page_defects(inspection, ()).ok


# ─── 横向溢出与固定元素遮挡（worker_02） ─────────────────────────────────


def test_horizontal_overflow_fails_closed() -> None:
    """文档横向溢出（scrollWidth > 视口宽度）必须失败关闭。"""
    inspection = PageInspection(
        route="/a/overview",
        layout=LayoutObservation(viewport_width=1280.0, document_scroll_width=1400.0),
    )
    result = verify_page_defects(inspection, ())
    assert not result.ok
    assert [v.code for v in result.violations] == [DefectViolationCode.HORIZONTAL_OVERFLOW]
    assert "120" in result.message_zh


def test_subpixel_overflow_within_tolerance_passes() -> None:
    """1px 内的亚像素溢出按现有浏览器测试约定放行。"""
    inspection = PageInspection(
        route="/a/overview",
        layout=LayoutObservation(viewport_width=1280.0, document_scroll_width=1281.0),
    )
    assert verify_page_defects(inspection, ()).ok


def test_content_occlusion_fails_closed() -> None:
    """固定页眉/面板矩形与内容矩形相交（遮挡）必须失败关闭。"""
    inspection = PageInspection(
        route="/a/overview",
        occlusions=(
            OcclusionObservation(
                fixed_label="粘性站点页眉",
                fixed_rect=Rect(top=0.0, left=0.0, right=1280.0, bottom=72.0),
                covered_label="页面主标题",
                covered_rect=Rect(top=40.0, left=24.0, right=800.0, bottom=120.0),
            ),
        ),
    )
    result = verify_page_defects(inspection, ())
    assert not result.ok
    assert [v.code for v in result.violations] == [DefectViolationCode.CONTENT_OCCLUSION]
    assert "粘性站点页眉" in result.message_zh
    assert "页面主标题" in result.message_zh


def test_non_overlapping_fixed_element_passes() -> None:
    """固定元素与内容不相交时不否决。"""
    inspection = PageInspection(
        route="/a/overview",
        occlusions=(
            OcclusionObservation(
                fixed_label="粘性站点页眉",
                fixed_rect=Rect(top=0.0, left=0.0, right=1280.0, bottom=72.0),
                covered_label="页面主标题",
                covered_rect=Rect(top=96.0, left=24.0, right=800.0, bottom=176.0),
            ),
        ),
    )
    assert verify_page_defects(inspection, ()).ok


# ─── 全站聚合与只读性（worker_02） ───────────────────────────────────────


def test_portal_defect_verification_aggregates_every_page() -> None:
    """任一页面缺陷即全站否决；全部干净才通过。"""
    clean = PageInspection(route="/a/overview", footer_count=1)
    broken = PageInspection(
        route="/a/products/product-01",
        footer_count=1,
        console_messages=(ConsoleObservation(message_type="error", text="渲染异常"),),
    )
    result = verify_portal_defects((clean, broken), ())
    assert not result.ok
    assert len(result.pages) == 2
    assert result.pages[0].ok
    assert not result.pages[1].ok
    assert "验收失败" in result.message_zh

    all_clean = verify_portal_defects((clean,), ())
    assert all_clean.ok
    assert "通过" in all_clean.message_zh


# ─── 静态扫描：真实壳层 HTML 的确定性验收（worker_02） ───────────────────


def _portal_spec() -> PortalSpec:
    return PortalSpec(
        title="系统性红斑狼疮竞品研究",
        pages=[
            PageSpec(
                slug="overview",
                title="首页",
                nav_label="首页",
                nav_group="总览",
                sections=["主要终点总览"],
                body_text="集中呈现疗效、安全性与人群结构。",
            ),
            PageSpec(
                slug="efficacy",
                title="疗效",
                nav_label="疗效",
                nav_group="疗效与安全性",
                sections=["主要终点"],
                body_text="按终点组织疗效比较结构。",
            ),
        ],
        footer_text="仅供产品中心医学部内部研判使用。",
    )


def _valid_site_files(site_root: Path) -> tuple[Path, ...]:
    valid = {route_to_site_path(route) for route in enumerate_site_routes(site_root, ReportKind.A)}
    for asset in site_root.rglob("assets/*"):
        valid.add(asset.relative_to(site_root))
    return tuple(sorted(valid))


def _scan_site_pages(site_root: Path) -> list[PageInspection]:
    inspections: list[PageInspection] = []
    for route in sorted(enumerate_site_routes(site_root, ReportKind.A)):
        html = (site_root / route_to_site_path(route)).read_text(encoding="utf-8")
        inspections.append(scan_page_html(html, route))
    return inspections


def test_static_scan_of_rendered_portal_passes_end_to_end(tmp_path: Path) -> None:
    """真实门户壳层的静态扫描 + 全站只读验收通过；篡改后失败关闭。"""
    site_root = tmp_path / "site"
    build_portal(_portal_spec(), site_root)
    valid = _valid_site_files(site_root)

    result = verify_portal_defects(_scan_site_pages(site_root), valid)
    assert result.ok, result.message_zh
    for page in result.pages:
        assert page.ok, page.message_zh

    # 篡改：每页追加第二个全局页脚 → 重复页脚失败关闭。
    for route in sorted(enumerate_site_routes(site_root, ReportKind.A)):
        path = site_root / route_to_site_path(route)
        html = path.read_text(encoding="utf-8")
        path.write_text(
            html.replace("</footer>", '</footer><footer class="site-footer">重复页脚</footer>'),
            encoding="utf-8",
        )
    result = verify_portal_defects(_scan_site_pages(site_root), valid)
    assert not result.ok
    assert any(
        v.code is DefectViolationCode.DUPLICATE_FOOTER
        for page in result.pages
        for v in page.violations
    )


def test_verification_never_modifies_site_files(tmp_path: Path) -> None:
    """只读验收器绝不修改被验收站点：验收前后站点文件字节一致。"""
    site_root = tmp_path / "site"
    build_portal(_portal_spec(), site_root)
    valid = _valid_site_files(site_root)
    before = {
        path.relative_to(site_root): path.read_bytes()
        for path in site_root.rglob("*")
        if path.is_file()
    }

    result = verify_portal_defects(_scan_site_pages(site_root), valid)
    assert result.ok, result.message_zh

    after = {
        path.relative_to(site_root): path.read_bytes()
        for path in site_root.rglob("*")
        if path.is_file()
    }
    assert before == after


# ─── CLI 输入校验：中文、可操作的缺失/非法输入说明（worker_03） ─────────────

TOOLS_DIR = Path(__file__).resolve().parents[2] / "tools"
CLI_VERIFY_PORTAL = TOOLS_DIR / "verify_portal.py"


def _load_verify_portal_module() -> object:
    spec = importlib.util.spec_from_file_location("task46_verify_portal", CLI_VERIFY_PORTAL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_cli(*argv: str, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI_VERIFY_PORTAL), *argv],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _default_cli_argv(project_root: Path) -> tuple[str, ...]:
    return (
        "--report",
        "A",
        "--project",
        str(project_root),
        "--version",
        _FIXTURE_VERSION,
        "--browser",
        "chromium",
        "--browser",
        "webkit",
        "--all-routes",
    )


def test_cli_rejects_missing_required_arguments_in_chinese() -> None:
    """CLI 缺少必填参数（--report/--project/--version）时给出中文可操作说明。"""
    result = _run_cli(timeout=60)
    assert result.returncode == 2
    assert "参数错误" in result.stderr
    assert "缺少必填参数" in result.stderr
    assert "--report" in result.stderr


def test_cli_rejects_unknown_report_browser_and_bad_viewport_in_chinese() -> None:
    """非法报告类型、浏览器与视口格式均以中文拒绝并退出 2。"""
    cases = (
        ("--report", "D", "--project", "p", "--version", "v"),
        ("--report", "A", "--project", "p", "--version", "v", "--browser", "firefox"),
        ("--report", "A", "--project", "p", "--version", "v", "--viewport", "1280"),
        ("--report", "A", "--project", "p", "--version", "v", "--viewport", "12x0"),
    )
    for argv in cases:
        result = _run_cli(*argv, timeout=60)
        assert result.returncode == 2, argv
        assert "参数错误" in result.stderr, argv


def test_cli_rejects_removed_identity_arguments_in_chinese() -> None:
    """CLI 已移除 --product/--trial：仍传入时以中文拒绝并退出 2。"""
    result = _run_cli(
        "--report",
        "A",
        "--project",
        "p",
        "--version",
        "v",
        "--product",
        "product-01",
        timeout=60,
    )
    assert result.returncode == 2
    assert "参数错误" in result.stderr
    assert "--product" in result.stderr


def test_cli_rejects_version_and_latest_together_in_chinese() -> None:
    """显式版本与自动选择互斥，避免调用方以为锁定了另一份产物。"""
    result = _run_cli(
        "--report",
        "A",
        "--project",
        "p",
        "--version",
        "v-one",
        "--latest",
        timeout=60,
    )
    assert result.returncode == 2
    assert "参数错误" in result.stderr


def test_latest_selects_most_recent_valid_manifest_and_ignores_broken_one(
    tmp_path: Path,
) -> None:
    """--latest 只在可解析清单中按生成时刻选最新版本。"""
    report_root = tmp_path / "reports" / "A"
    manifests = {
        "v-old": "2026-08-17T08:00:00+08:00",
        "v-new": "2026-08-18T08:00:00+08:00",
    }
    for version, generated_at in manifests.items():
        path = report_root / version / "html.manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"generated_at": generated_at}), encoding="utf-8")
    broken = report_root / "v-broken" / "html.manifest.json"
    broken.parent.mkdir(parents=True, exist_ok=True)
    broken.write_text("不是合法清单", encoding="utf-8")

    module = _load_verify_portal_module()
    assert module._resolve_version(tmp_path, "A", None) == "v-new"  # type: ignore[attr-defined]


def test_cli_fails_closed_when_site_directory_missing() -> None:
    """报告站点目录缺失时给出中文且可操作（含期望路径）的说明。"""
    result = _run_cli(
        "--report",
        "A",
        "--project",
        "不存在的项目目录",
        "--version",
        "v-fixture-001",
        timeout=60,
    )
    assert result.returncode == 2
    assert "参数错误" in result.stderr
    assert "不存在" in result.stderr
    assert "reports" in result.stderr and "html" in result.stderr


# ─── Task 4.6 合成夹具：A 报告站点式门户 + 锁定快照与产物清单（worker_03） ───

_FIXTURE_VERSION = "v-fixture-001"
_FIXTURE_PROJECT_ID = "fixture-task46-project"
_FIXTURE_SOURCE_COMMIT = "0123456789abcdef0123456789abcdef01234567"
_FIXTURE_PACKAGE_DIGEST = "ab" * 32
_DATA_CUTOFF = datetime(2026, 7, 31, 23, 59, tzinfo=UTC)
_CREATED_AT = datetime(2026, 8, 1, 7, 0, tzinfo=UTC)
_GENERATED_AT = datetime(2026, 8, 1, 8, 0, tzinfo=UTC)
_MODIFIED_AT = datetime(2026, 8, 1, 8, 5, tzinfo=UTC)
_VERIFIED_AT = datetime(2026, 8, 1, 8, 10, tzinfo=UTC)


def _canonical_json(value: object) -> bytes:
    """与 SnapshotStore/ManifestStore 同一规范 JSON：排序、紧凑、中文不转义。"""
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


_DETAIL_HREF_RE = re.compile(r'href="(?![.#/])([a-z0-9-]+\.html)"')

# 合成夹具的用户可见中文名称：内部路由 slug 保持稳定，对外只显示中文名。
# 链接、搜索索引与详情页标题均使用本映射；slug 只作为文件与路由身份。
_PRODUCT_DISPLAY_NAMES: dict[str, str] = {
    "product-01": "环柏单抗",
    "product-02": "洛普利单抗",
    "product-03": "贝妥昔单抗",
}
_TRIAL_DISPLAY_NAMES: dict[str, str] = {
    "trial-01": "关键注册研究",
    "trial-02": "长期扩展研究",
}


def _render_detail_page(
    spec: PortalSpec,
    site_root: Path,
    kind_dir: str,
    slug: str,
    label_zh: str,
    kind_label: str,
) -> None:
    """渲染产品/试验详情页：位于子目录，站点链接与资源路径加 ../ 前缀。

    页面标题与正文使用原生中文名称（label_zh），不把 slug 写进用户可见
    文案；slug 仅作为稳定路由身份与物理文件名。
    """
    page = PageSpec(
        slug=slug,
        title=label_zh,
        nav_label=label_zh,
        nav_group=kind_label,
        sections=[label_zh],
        body_text=(
            f"本页汇总{label_zh}的作用机制、开发阶段、关键研究结果与安全性概况。"
            if kind_dir == "products"
            else f"本页呈现{label_zh}的试验设计、目标人群、主要终点与结果披露状态。"
        ),
    )
    html = render_page_html(page=page, spec=spec, assets_rel="../assets")
    html = _DETAIL_HREF_RE.sub(r'href="../\1"', html)
    target = site_root / kind_dir / f"{slug}.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")


def _inject_detail_entries(
    site_root: Path,
    *,
    products: tuple[str, ...],
    trials: tuple[str, ...],
) -> None:
    """给产品总览与临床开发组合页添加可见、可点击的详情入口。

    链接文本必须是用户可见中文名称，不得显示内部路由 slug；这些入口
    也是可达性验收沿本地锚点遍历时进入详情页的边。
    """
    product_items = "\n".join(
        '          <li class="portal-detail-index__item">'
        f'<a href="products/{slug}.html">{_PRODUCT_DISPLAY_NAMES[slug]}</a></li>'
        for slug in products
    )
    trial_items = "\n".join(
        '          <li class="portal-detail-index__item">'
        f'<a href="trials/{slug}.html">{_TRIAL_DISPLAY_NAMES[slug]}</a></li>'
        for slug in trials
    )
    for filename, heading, items in (
        ("product-overview.html", "产品档案", product_items),
        ("clinical-portfolio.html", "试验档案", trial_items),
    ):
        path = site_root / filename
        if not path.is_file() or not items:
            continue
        html = path.read_text(encoding="utf-8")
        section = (
            f'    <section class="portal-detail-index" aria-label="{heading}">\n'
            f'      <h2 class="portal-detail-index__title">{heading}</h2>\n'
            f'      <ul class="portal-detail-index__list">\n{items}\n'
            "      </ul>\n"
            "    </section>\n"
        )
        html = html.replace("  </main>", section + "  </main>", 1)
        path.write_text(html, encoding="utf-8")


def _expand_search_index(
    site_root: Path,
    spec: PortalSpec,
    *,
    products: tuple[str, ...],
    trials: tuple[str, ...],
) -> None:
    """把产品/试验详情页并入全局搜索索引，并按页面深度生成正确链接。

    静态页位于站点根目录，产品/试验详情页各深一层；同一条搜索结果在
    三种位置需要不同相对路径。夹具分别生成根目录、产品目录和试验目录
    三份索引，避免搜索结果看似存在却跳到不存在文件的假功能。
    """
    detail_pages: list[PageSpec] = []
    for slug in products:
        name = _PRODUCT_DISPLAY_NAMES[slug]
        detail_pages.append(
            PageSpec(
                slug=slug,
                title=name,
                nav_label=name,
                nav_group="产品详情",
                sections=[name],
            )
        )
    for slug in trials:
        name = _TRIAL_DISPLAY_NAMES[slug]
        detail_pages.append(
            PageSpec(
                slug=slug,
                title=name,
                nav_label=name,
                nav_group="试验详情",
                sections=[name],
            )
        )
    entries = build_search_index([*spec.pages, *detail_pages])
    static_slugs = {page.slug for page in spec.pages}
    product_slugs = set(products)

    def literal_for(scope: str) -> str:
        rows: list[dict[str, object]] = []
        for entry in entries:
            if entry.slug in static_slugs:
                relative_slug = entry.slug if scope == "root" else f"../{entry.slug}"
            elif entry.slug in product_slugs:
                relative_slug = (
                    f"products/{entry.slug}"
                    if scope == "root"
                    else entry.slug
                    if scope == "products"
                    else f"../products/{entry.slug}"
                )
            else:
                relative_slug = (
                    f"trials/{entry.slug}"
                    if scope == "root"
                    else entry.slug
                    if scope == "trials"
                    else f"../trials/{entry.slug}"
                )
            rows.append({"slug": relative_slug, "title": entry.title, "keywords": entry.keywords})
        return json.dumps(rows, ensure_ascii=False, separators=(",", ":"))

    inline = re.compile(r"window\.__SEARCH_INDEX__ = [^<]*</script>")
    for html_path in sorted(site_root.rglob("*.html")):
        scope = html_path.parent.name if html_path.parent != site_root else "root"
        literal = literal_for(scope)
        html = html_path.read_text(encoding="utf-8")
        if scope in {"products", "trials"}:
            html = html.replace('src="../assets/search-index.js"', 'src="search-index.js"', 1)
        html_path.write_text(
            inline.sub(
                f"window.__SEARCH_INDEX__ = {literal};\n</script>",
                html,
                count=1,
            ),
            encoding="utf-8",
        )
    (site_root / "assets" / "search-index.js").write_text(
        f"window.__SEARCH_INDEX__ = {literal_for('root')};\n",
        encoding="utf-8",
    )
    for scope in ("products", "trials"):
        if (site_root / scope).is_dir():
            (site_root / scope / "search-index.js").write_text(
                f"window.__SEARCH_INDEX__ = {literal_for(scope)};\n",
                encoding="utf-8",
            )


def _write_locked_report_artifacts(
    project_root: Path,
    site_root: Path,
    *,
    products: tuple[str, ...],
    trials: tuple[str, ...],
) -> None:
    """真实写入锁定报告快照与完整 html.manifest.json，与生产加载器同一合同。

    快照按 SnapshotStore 规范 JSON（排序、紧凑、中文不转义、末尾换行）
    内容寻址写入，报告快照身份 = ``stable_id("report-snapshot", 报告, 摘要)``；
    产物清单用真实 ``ArtifactManifest`` 模型校验后写入（校验失败即夹具
    损坏），站点目录摘要/字节数由 ``site_directory_digest`` 计算。不用
    任何 mock 绕过。
    """
    site_digest, site_bytes = site_directory_digest(site_root)
    claim_ids = ("claim_primary_001", "claim_safety_001")
    snapshot_payload = {
        "schema_version": "1.0",
        "project_id": _FIXTURE_PROJECT_ID,
        "contract_version": 1,
        "report": "A",
        "report_version": _FIXTURE_VERSION,
        "data_cutoff": _DATA_CUTOFF.isoformat(),
        "evidence_snapshot_id": stable_id("evidence-snapshot", "fixture-evidence"),
        "claim_snapshot_id": stable_id("claim-snapshot", "fixture-claims"),
        "coverage_set_id": stable_id("coverage-set", "fixture-coverage"),
        "claim_ids": list(claim_ids),
        "created_at": _CREATED_AT.isoformat(),
    }
    validated_snapshot = ReportSnapshotManifest.model_validate(snapshot_payload)
    encoded = _canonical_json(validated_snapshot.model_dump(mode="json"))
    snapshot_id = stable_id("report-snapshot", "A", hashlib.sha256(encoded).hexdigest())
    snapshot_path = project_root / "snapshots" / "reports" / "A" / f"{snapshot_id}.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_bytes(encoded)

    catalog = PageRegistry.load().catalog(ReportKind.A)
    manifest_payload = {
        "schema_version": "1.0",
        "manifest_id": stable_id("artifact-manifest", "A", _FIXTURE_VERSION, "fixture-run"),
        "project_id": _FIXTURE_PROJECT_ID,
        "contract_version": 1,
        "report": "A",
        "report_version": _FIXTURE_VERSION,
        "data_cutoff": _DATA_CUTOFF.isoformat(),
        "producer_run_id": "run-fixture-task46",
        "source_commit": _FIXTURE_SOURCE_COMMIT,
        "package_digest": _FIXTURE_PACKAGE_DIGEST,
        "evidence_snapshot_id": validated_snapshot.evidence_snapshot_id,
        "claim_snapshot_id": validated_snapshot.claim_snapshot_id,
        "report_snapshot_id": snapshot_id,
        "coverage_set_id": validated_snapshot.coverage_set_id,
        "coverage_projection_id": stable_id("coverage-projection", "A", _FIXTURE_VERSION),
        "structured_exceptions": [],
        "pages_or_sections": [page.id for page in catalog.pages],
        "product_ids": list(products),
        "trial_ids": list(trials),
        "claim_ids": list(claim_ids),
        "chart_ids": [],
        "table_ids": [],
        "evidence_reference_ids": ["evidence-ref-001"],
        "design_contract": {
            "roles": ["report-portal"],
            "digest": _FIXTURE_PACKAGE_DIGEST,
            "applicable_sections": ["15.1", "15.6"],
        },
        "renderer": {"name": "portal", "version": "1.0"},
        "filter_state": {},
        "generated_at": _GENERATED_AT.isoformat(),
        "deterministic_checks": [
            {
                "check_id": "portal-shell",
                "status": "passed",
                "receipt": "fixture-receipt",
            }
        ],
        "render_verdict": {
            "verdict_id": "verdict-task46-fixture",
            "status": "accepted",
            "verified_at": _VERIFIED_AT.isoformat(),
            "anchor_ids": ["anchor-task46-fixture"],
        },
        "accepted_by": "fixture-acceptance",
        "artifact": {
            "relative_path": f"reports/A/{_FIXTURE_VERSION}/html",
            "sha256": site_digest,
            "byte_size": site_bytes,
            "modified_at": _MODIFIED_AT.isoformat(),
            "media_type": "directory",
        },
        "status": "accepted",
        "supersedes_manifest_id": None,
    }
    manifest = ArtifactManifest.model_validate(manifest_payload)
    manifest_path = project_root / "reports" / "A" / _FIXTURE_VERSION / "html.manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(_canonical_json(manifest.model_dump(mode="json")))


def _build_task46_project(
    project_root: Path,
    *,
    products: tuple[str, ...] = PRODUCT_IDS,
    trials: tuple[str, ...] = TRIAL_IDS,
) -> tuple[Path, tuple[str, ...]]:
    """Task 4.6 合成夹具：A 报告门户 + 真实锁定报告快照与完整产物清单。

    返回 (site_root, 期望路由)。静态页来自冻结目录与真实门户壳层构建，
    详情页复用同一壳层（链接/资源相对路径加 ``../``）；随后真实写入
    锁定报告快照与 html.manifest.json 绑定当前站点目录摘要。
    """
    registry = PageRegistry.load()
    catalog = registry.catalog(ReportKind.A)
    site_root = project_root / "reports" / "A" / _FIXTURE_VERSION / "html"
    spec = PortalSpec(
        title="系统性红斑狼疮竞品全景",
        pages=[
            PageSpec(
                slug=page.id,
                title=page.title_zh,
                nav_label=page.title_zh,
                nav_group=page.navigation_group_zh,
                sections=list(page.visuals),
                body_text=page.responsibility_zh,
            )
            for page in sorted(catalog.pages, key=lambda item: item.id)
        ],
        footer_text="仅供产品中心医学部内部研判使用。",
    )
    build_portal(spec, site_root)
    for product in products:
        _render_detail_page(
            spec, site_root, "products", product, _PRODUCT_DISPLAY_NAMES[product], "产品详情"
        )
    _inject_detail_entries(site_root, products=products, trials=())
    _expand_search_index(site_root, spec, products=products, trials=())
    _write_locked_report_artifacts(project_root, site_root, products=products, trials=trials)
    contract = derive_sitemap_contract(
        registry,
        ReportKind.A,
        product_ids=products,
        trial_ids=trials,
    )
    return site_root, contract.routes


def _launch_browser(playwright: Playwright, browser_name: str) -> Browser:
    return cast(Browser, getattr(playwright, browser_name).launch())


def _png_size(path: Path) -> tuple[int, int]:
    """从 PNG 头读取像素尺寸（不依赖图像库）。"""
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"不是 PNG 文件：{path}"
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


# ─── 运行时收集：Chromium/WebKit 1280/1440/1920 失败关闭（worker_03） ───────

_DEFECT_PAGE_HTML = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>缺陷页</title>
<style>body{margin:0}</style>
</head><body>
<div style="position:fixed;top:0;left:0;width:100%;height:120px;
background:#fff;z-index:9999">固定覆盖层</div>
<h1>页面主标题</h1>
<div style="width:1500px;height:1px"></div>
<script>console.error("TypeError: x 不是函数")</script>
<script>throw new Error("ReferenceError: data 未定义")</script>
</body></html>
"""


@pytest.mark.parametrize("browser_name", ["chromium", "webkit"])
@pytest.mark.parametrize("viewport", DEFAULT_VIEWPORTS)
def test_runtime_collection_detects_errors_overflow_and_occlusion_fail_closed(
    browser_name: str,
    viewport: tuple[int, int],
    tmp_path: Path,
) -> None:
    """真实浏览器运行时收集在 Chromium/WebKit 三个视口对缺陷失败关闭。"""
    defect_page = tmp_path / "defect.html"
    defect_page.write_text(_DEFECT_PAGE_HTML, encoding="utf-8")
    with sync_playwright() as playwright:
        browser = _launch_browser(playwright, browser_name)
        page = browser.new_page(
            viewport={"width": viewport[0], "height": viewport[1]},
            device_scale_factor=1,
        )
        inspection = collect_page_runtime_observations(page, "/a/overview", defect_page.as_uri())
        browser.close()

    result = verify_page_defects(inspection, ())
    assert not result.ok
    codes = {v.code for v in result.violations}
    assert DefectViolationCode.CONSOLE_ERROR in codes
    assert DefectViolationCode.PAGE_ERROR in codes
    assert DefectViolationCode.CONTENT_OCCLUSION in codes
    if viewport[0] < 1500:
        assert DefectViolationCode.HORIZONTAL_OVERFLOW in codes
    else:
        assert DefectViolationCode.HORIZONTAL_OVERFLOW not in codes
    assert "TypeError" in result.message_zh


def test_runtime_collection_of_clean_shell_passes(tmp_path: Path) -> None:
    """真实门户壳层在运行时收集 + 静态扫描合并后全部通过。"""
    site_root, _ = _build_task46_project(tmp_path)
    route = "/a/overview"
    html = (site_root / route_to_site_path(route)).read_text(encoding="utf-8")
    with sync_playwright() as playwright:
        browser = _launch_browser(playwright, "chromium")
        page = browser.new_page(
            viewport={"width": 1280, "height": 800},
            device_scale_factor=1,
        )
        runtime = collect_page_runtime_observations(
            page, route, (site_root / route_to_site_path(route)).as_uri()
        )
        browser.close()

    merged = merge_page_observations(scan_page_html(html, route), runtime)
    result = verify_page_defects(merged, _valid_site_files(site_root))
    assert result.ok, result.message_zh


def test_runtime_collection_does_not_treat_sticky_table_header_as_occlusion(
    tmp_path: Path,
) -> None:
    """粘性表头位于所属表格容器内时属于正常阅读辅助，不得误报为遮挡。"""
    page_path = tmp_path / "sticky-table.html"
    page_path.write_text(
        """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<style>th{position:sticky;top:0;background:white}</style></head><body>
<main><section><h1>疗效比较</h1><table><thead><tr><th>产品</th></tr></thead>
<tbody><tr><td>示例产品</td></tr></tbody></table></section></main>
<footer class="site-footer">页脚</footer></body></html>""",
        encoding="utf-8",
    )
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        inspection = collect_page_runtime_observations(
            page, "/a/efficacy", page_path.as_uri()
        )
        browser.close()
    assert inspection.occlusions == ()


def test_merge_observations_combines_static_and_runtime_deduplicating_requests() -> None:
    """静态扫描与运行时观察合并为同一 PageInspection，重复请求去重。"""
    static = scan_page_html(
        '<link rel="stylesheet" href="assets/portal.css">'
        '<script src="assets/portal.js"></script>'
        '<footer class="site-footer">唯一页脚</footer>',
        "/a/overview",
    )
    runtime = PageInspection(
        route="/a/overview",
        console_messages=(ConsoleObservation(message_type="warning", text="已废弃 API"),),
        requests=(RequestObservation(url="assets/portal.css", resource_type="stylesheet"),),
    )
    merged = merge_page_observations(static, runtime)
    assert merged.footer_count == 1
    assert merged.layout is None
    assert merged.console_messages == (
        ConsoleObservation(message_type="warning", text="已废弃 API"),
    )
    assert len(merged.requests) == 2
    assert verify_page_defects(merged, (Path("assets/portal.css"),)).ok


# ─── CLI 全站验收：双浏览器、多视口、原分辨率截图与交互 trace（worker_03） ───


def _project_files(project_root: Path) -> dict[str, bytes]:
    """项目内全部文件字节（排除验收输出目录），验证只读保证。"""
    return {
        str(path.relative_to(project_root).as_posix()): path.read_bytes()
        for path in sorted(project_root.rglob("*"))
        if path.is_file() and "verification" not in path.parts
    }


def test_fixture_search_reaches_products_from_root_and_product_depth(
    tmp_path: Path,
) -> None:
    """全局搜索从根页面和产品详情页都能进入正确的中文详情页。"""
    project_root = tmp_path / "project"
    site_root, _routes = _build_task46_project(project_root)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto((site_root / "product-overview.html").as_uri())
        page.locator("#menu-toggle").click()
        page.locator("#global-search-input").fill("环柏单抗")
        product_result = page.locator('#global-search-results a[href="products/product-01.html"]')
        assert product_result.is_visible()
        product_result.click()
        assert page.locator("h1").inner_text() == "环柏单抗"

        page.locator("#menu-toggle").click()
        page.locator("#global-search-input").fill("洛普利单抗")
        second_product = page.locator('#global-search-results a[href="product-02.html"]')
        assert second_product.is_visible()
        second_product.click()
        assert page.locator("h1").inner_text() == "洛普利单抗"
        browser.close()


def test_cli_full_site_acceptance_passes_with_screenshots_traces_and_read_only_site(
    tmp_path: Path,
) -> None:
    """CLI 全站验收通过：双浏览器 × 三视口 × 全部路由；原分辨率截图、带摘要
    交互 trace 与只读保证（站点、清单与锁定快照字节均不变）。"""
    project_root = tmp_path / "project"
    _site_root, routes = _build_task46_project(project_root)
    before = _project_files(project_root)

    result = _run_cli(*_default_cli_argv(project_root))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "全站验收通过" in result.stdout
    assert f"A_PORTAL_OK routes={len(routes)} browsers=2" in result.stdout

    output_dir = project_root / "verification" / "A" / _FIXTURE_VERSION
    report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert report["routes"] == list(routes)
    assert report["browsers"] == ["chromium", "webkit"]
    assert report["viewports"] == [list(vp) for vp in DEFAULT_VIEWPORTS]
    assert len(report["manifest_id"]) > 0
    assert len(report["report_snapshot_id"]) > 0

    # 原分辨率截图：每路由 × 每浏览器 × 每视口，像素尺寸与视口一致。
    screenshots = output_dir / "screenshots"
    expected_shots = 0
    for route in routes:
        slug = route.lstrip("/").replace("/", "_")
        for browser_name in ("chromium", "webkit"):
            for width, height in DEFAULT_VIEWPORTS:
                shot = screenshots / f"{slug}__{browser_name}__{width}x{height}.png"
                assert shot.is_file(), shot
                assert _png_size(shot) == (width, height), shot
                expected_shots += 1
    assert report["screenshots"]["count"] == expected_shots

    # 交互 trace：每浏览器一个 zip，携带 run/site digest。
    run_digest = report["run_digest"]
    site_digest = report["site_digest"]
    assert len(run_digest) == 64 and len(site_digest) == 64
    traces = {entry["browser"]: entry for entry in report["traces"]}
    assert set(traces) == {"chromium", "webkit"}
    for _browser_name, entry in traces.items():
        assert entry["run_digest"] == run_digest
        assert entry["site_digest"] == site_digest
        trace_path = output_dir / entry["path"]
        assert trace_path.is_file(), trace_path
        with zipfile.ZipFile(trace_path) as archive:
            names = archive.namelist()
            assert "trace.trace" in names
            assert "trace.network" in names
            text = "".join(archive.read(name).decode("utf-8", errors="replace") for name in names)
            assert run_digest in text
            assert site_digest in text

    # 只读保证：被验收站点、产物清单与锁定快照字节均不变。
    after = _project_files(project_root)
    assert before == after


def test_cli_fails_closed_on_runtime_defect_with_chinese_actionable_message(
    tmp_path: Path,
) -> None:
    """运行时缺陷（控制台错误 + 固定遮挡）使 CLI 失败关闭并给出中文可操作说明。"""
    project_root = tmp_path / "project"
    site_root, routes = _build_task46_project(project_root)
    tampered = site_root / route_to_site_path("/a/products/product-01")
    html = tampered.read_text(encoding="utf-8")
    tampered.write_text(
        html.replace(
            "</body>",
            '<script>console.error("TypeError: x 不是函数")</script>'
            '<div style="position:fixed;top:0;left:0;width:100%;height:120px;'
            'background:#fff;z-index:99999">固定覆盖层</div>'
            "</body>",
        ),
        encoding="utf-8",
    )
    # 篡改后重新绑定清单（模拟站点以当前内容重新生成），让运行时缺陷单独被验收。
    _write_locked_report_artifacts(project_root, site_root, products=PRODUCT_IDS, trials=TRIAL_IDS)

    result = _run_cli(*_default_cli_argv(project_root))
    assert result.returncode == 1, result.stdout + result.stderr
    assert "全站验收失败" in result.stdout
    assert "/a/products/product-01" in result.stdout
    assert "控制台错误" in result.stdout
    assert f"A_PORTAL_FAIL routes={len(routes)} browsers=2" in result.stdout

    output_dir = project_root / "verification" / "A" / _FIXTURE_VERSION
    report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
    assert report["ok"] is False
    product = next(
        page for page in report["pages"] if page["route"] == "/a/products/product-01"
    )
    assert product["ok"] is False
    codes = {
        check["violations"][0]["code"]
        for page in report["pages"]
        if not page["ok"]
        for check in page["checks"]
        if check["violations"]
    }
    assert "console_error" in codes


def test_cli_sitemap_gate_fails_closed_before_browsers_launch(tmp_path: Path) -> None:
    """缺页在站点地图核对即失败关闭，不启动浏览器、不产出截图。"""
    project_root = tmp_path / "project"
    site_root, routes = _build_task46_project(project_root)
    (site_root / route_to_site_path("/a/products/product-02")).unlink()
    # 缺页后重新绑定清单（模拟该版本站点确实缺少此详情页），让站点地图
    # 一一对应核对单独失败。
    _write_locked_report_artifacts(project_root, site_root, products=PRODUCT_IDS, trials=TRIAL_IDS)

    result = _run_cli(*_default_cli_argv(project_root))
    assert result.returncode == 1
    assert "站点地图" in result.stdout
    assert "缺少产品详情页" in result.stdout
    assert "/a/products/product-02" in result.stdout
    output_dir = project_root / "verification" / "A" / _FIXTURE_VERSION
    assert not (output_dir / "screenshots").exists()


def test_cli_orphan_detail_page_fails_reachability_before_browsers(
    tmp_path: Path,
) -> None:
    """详情页文件存在但门户内没有任何可见入口时，可达性验收失败关闭。

    失败发生在启动浏览器之前：退出 1、stdout 指明不可达路由、不产出截图、
    不写 report.json（browsers=0）。
    """
    project_root = tmp_path / "project"
    site_root, _routes = _build_task46_project(project_root)
    # 移除产品总览页中 product-02 的可见入口；文件保留，成为孤儿详情页。
    overview = site_root / "product-overview.html"
    overview.write_text(
        re.sub(
            r'<a href="products/product-02\.html">[^<]*</a>',
            "",
            overview.read_text(encoding="utf-8"),
        ),
        encoding="utf-8",
    )
    _write_locked_report_artifacts(project_root, site_root, products=PRODUCT_IDS, trials=TRIAL_IDS)

    result = _run_cli(*_default_cli_argv(project_root))
    assert result.returncode == 1, result.stdout + result.stderr
    assert "可达性" in result.stdout
    assert "/a/products/product-02" in result.stdout
    assert "browsers=0" in result.stdout
    output_dir = project_root / "verification" / "A" / _FIXTURE_VERSION
    assert not (output_dir / "screenshots").exists()
    assert not (output_dir / "report.json").exists()


# ─── 锁定站点地图来源：清单/快照/站点摘要失败关闭（worker_03 修订） ────────


def test_cli_plan_command_succeeds_without_identity_arguments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """实施计划原始命令可用相对项目路径，并从清单读取全部实体。"""
    project_root = tmp_path / "project"
    _site_root, routes = _build_task46_project(project_root)
    monkeypatch.chdir(tmp_path)
    result = _run_cli(
        "--report",
        "A",
        "--project",
        "project",
        "--version",
        _FIXTURE_VERSION,
        "--browser",
        "chromium",
        "--all-routes",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "全站验收通过" in result.stdout
    assert f"A_PORTAL_OK routes={len(routes)} browsers=1" in result.stdout


def test_cli_fails_closed_when_html_manifest_missing(tmp_path: Path) -> None:
    """缺少 html.manifest.json 时失败关闭并给出中文可操作说明。"""
    project_root = tmp_path / "project"
    _build_task46_project(project_root)
    manifest_path = project_root / "reports" / "A" / _FIXTURE_VERSION / "html.manifest.json"
    manifest_path.unlink()

    result = _run_cli(*_default_cli_argv(project_root))
    assert result.returncode == 2
    assert "参数错误" in result.stderr
    assert "清单" in result.stderr and "不存在" in result.stderr
    assert "reports" in result.stderr and "html" in result.stderr


def test_cli_fails_closed_when_report_snapshot_missing(tmp_path: Path) -> None:
    """清单引用的报告快照缺失时失败关闭并给出中文可操作说明。"""
    project_root = tmp_path / "project"
    _build_task46_project(project_root)
    for path in (project_root / "snapshots" / "reports" / "A").glob("*.json"):
        path.unlink()

    result = _run_cli(*_default_cli_argv(project_root))
    assert result.returncode == 2
    assert "参数错误" in result.stderr
    assert "报告快照" in result.stderr and "不存在" in result.stderr


def test_cli_fails_closed_on_snapshot_binding_mismatch(tmp_path: Path) -> None:
    """报告快照内容与清单绑定不一致（篡改后身份重算不符）时失败关闭。"""
    project_root = tmp_path / "project"
    _build_task46_project(project_root)
    snapshot_path = next((project_root / "snapshots" / "reports" / "A").glob("*.json"))
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    payload["report_version"] = "v-other-999"
    snapshot_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = _run_cli(*_default_cli_argv(project_root))
    assert result.returncode == 2
    assert "参数错误" in result.stderr
    assert "报告快照" in result.stderr and "不一致" in result.stderr


def test_cli_fails_closed_on_stale_site_digest(tmp_path: Path) -> None:
    """站点目录摘要与清单不一致（站点被改写）时在启动浏览器前失败关闭。"""
    project_root = tmp_path / "project"
    _build_task46_project(project_root)
    site_root = project_root / "reports" / "A" / _FIXTURE_VERSION / "html"
    overview = site_root / "overview.html"
    overview.write_text(overview.read_text(encoding="utf-8") + "<!-- 被改写 -->", encoding="utf-8")

    result = _run_cli(*_default_cli_argv(project_root))
    assert result.returncode == 2
    assert "参数错误" in result.stderr
    assert "摘要" in result.stderr and "不一致" in result.stderr
    output_dir = project_root / "verification" / "A" / _FIXTURE_VERSION
    assert not (output_dir / "screenshots").exists()


def test_cli_sitemap_rejects_extra_route_when_manifest_omits_entity(
    tmp_path: Path,
) -> None:
    """清单漏掉已有实体时，站点地图核对拒绝该额外路由（失败关闭）。"""
    project_root = tmp_path / "project"
    site_root, _ = _build_task46_project(project_root)
    # 站点仍含 product-02 详情页，但清单省略该实体。
    _write_locked_report_artifacts(
        project_root,
        site_root,
        products=("product-01", "product-03"),
        trials=TRIAL_IDS,
    )

    result = _run_cli(*_default_cli_argv(project_root))
    assert result.returncode == 1, result.stdout + result.stderr
    assert "站点地图" in result.stdout
    assert "站点地图之外" in result.stdout
    assert "/a/products/product-02" in result.stdout
