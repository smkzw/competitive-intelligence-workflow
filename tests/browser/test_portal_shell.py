"""Task 4.2 Portal shell browser tests.

Exercises the generated portal across Chromium/WebKit at 1280/1440/1920
desktop widths plus one <=1024 responsive case, for both ``file://`` and a
local static HTTP server. Screenshots land in pytest tmp paths only.

Assertions deliberately close false-green paths: pairwise header collision,
text clipping, logo natural dimensions, inline/external search-index parity,
remote requests, console errors, and wheel-packaged asset loading.
"""

from __future__ import annotations

import hashlib
import http.server
import json
import re
import socket
import subprocess
import sys
import threading
from pathlib import Path
from posixpath import normpath
from typing import Any, cast

import pytest
from playwright.sync_api import Browser, Page, Playwright, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
PORTAL_SPEC: dict[str, Any] = {
    "title": "特应性皮炎竞品全景",
    "pages": [
        {
            "slug": "overview",
            "title": "竞品全景",
            "nav_label": "竞品全景",
            "nav_group": "竞品全景",
            "sections": ["靶点分布", "开发阶段", "地域状态"],
            "body_text": "本页面展示特应性皮炎领域全部创新药竞品的靶点结构与开发阶段分布。",
        },
        {
            "slug": "efficacy",
            "title": "疗效比较",
            "nav_label": "疗效比较",
            "nav_group": "疗效比较",
            "sections": ["主要终点", "次要终点", "亚组分析"],
            "body_text": "按锚定核心试验比较常用疗效终点及对照组效应。",
        },
        {
            "slug": "safety",
            "title": "安全性比较",
            "nav_label": "安全性比较",
            "nav_group": "安全性比较",
            "sections": ["常见不良事件", "严重不良事件", "特别关注事件"],
            "body_text": "安全性数据按发生率维度分层展示，不做简单排名。",
        },
    ],
    "nav": [
        {"label": "竞品全景", "slug": "overview", "group": "竞品全景"},
        {"label": "疗效比较", "slug": "efficacy", "group": "疗效比较"},
        {"label": "安全性比较", "slug": "safety", "group": "安全性比较"},
    ],
    "footer_text": "仅供产品中心医学部内部研判使用。",
}

# Canonical B report page catalog (21 pages / 5 navigation groups).
B_CATALOG_PAGES: list[dict[str, Any]] = [
    {
        "slug": "overview",
        "title": "首页",
        "nav_label": "首页",
        "nav_group": "总览",
        "sections": ["主要终点总览", "关键安全性", "疗效与安全性矩阵"],
        "body_text": "集中呈现特应性皮炎试验的疗效、安全性与人群结构。",
    },
    {
        "slug": "efficacy",
        "title": "疗效",
        "nav_label": "疗效",
        "nav_group": "疗效与安全性",
        "sections": ["主要终点", "次要终点", "对照组并列"],
        "body_text": "本页按终点组织疗效比较结构，治疗组与对照组保持并列阅读。",
    },
    {
        "slug": "longitudinal-results",
        "title": "纵向结果",
        "nav_label": "纵向结果",
        "nav_group": "疗效与安全性",
        "sections": ["时间序列", "产品分层", "终点分层"],
        "body_text": "本页组织纵向结果的阅读路径，不预先给出可比性评分。",
    },
    {
        "slug": "safety",
        "title": "安全性",
        "nav_label": "安全性",
        "nav_group": "疗效与安全性",
        "sections": ["严重不良事件", "特别关注事件", "常见事件"],
        "body_text": "本页按安全性维度组织比较，避免简单排名表述。",
    },
    {
        "slug": "baseline-overview",
        "title": "基线与人群总览",
        "nav_label": "基线与人群总览",
        "nav_group": "基线与人群",
        "sections": ["人口学概览", "疾病语境", "严重程度"],
        "body_text": "本页汇总基线与人群比较，便于查看具体变量。",
    },
    {
        "slug": "baseline-demographics",
        "title": "人口学",
        "nav_label": "人口学",
        "nav_group": "基线与人群",
        "sections": ["年龄与性别", "地区与种族", "体重相关"],
        "body_text": "本页比较人口学相关基线指标。",
    },
    {
        "slug": "baseline-disease-context",
        "title": "疾病语境",
        "nav_label": "疾病语境",
        "nav_group": "基线与人群",
        "sections": ["病程", "既往治疗", "合并症"],
        "body_text": "本页比较疾病语境相关基线指标。",
    },
    {
        "slug": "baseline-severity",
        "title": "基线疾病严重程度",
        "nav_label": "基线疾病严重程度",
        "nav_group": "基线与人群",
        "sections": ["量表版本", "统计形式", "时间点"],
        "body_text": "本页比较基线疾病严重程度相关指标。",
    },
    {
        "slug": "disposition-overview",
        "title": "试验完成情况总览",
        "nav_label": "试验完成情况总览",
        "nav_group": "试验完成情况",
        "sections": ["筛选与随机", "完成与退出", "披露状态"],
        "body_text": "本页总览试验完成情况。",
    },
    {
        "slug": "participant-flow",
        "title": "受试者流转",
        "nav_label": "受试者流转",
        "nav_group": "试验完成情况",
        "sections": ["筛选", "随机与治疗", "完成与失访"],
        "body_text": "本页比较受试者流转相关指标。",
    },
    {
        "slug": "adherence",
        "title": "依从性",
        "nav_label": "依从性",
        "nav_group": "试验完成情况",
        "sections": ["依从性定义", "报告口径", "披露状态"],
        "body_text": "本页比较依从性相关指标。",
    },
    {
        "slug": "loss-exit",
        "title": "失访与退出",
        "nav_label": "失访与退出",
        "nav_group": "试验完成情况",
        "sections": ["失访", "停止治疗", "退出研究"],
        "body_text": "本页比较失访与退出相关指标。",
    },
    {
        "slug": "screen-failure",
        "title": "筛败与原因",
        "nav_label": "筛败与原因",
        "nav_group": "试验完成情况",
        "sections": ["筛败比例", "主要原因", "披露状态"],
        "body_text": "本页比较筛败与原因相关指标。",
    },
    {
        "slug": "rescue-treatment",
        "title": "补救治疗",
        "nav_label": "补救治疗",
        "nav_group": "试验完成情况",
        "sections": ["使用人数", "时间窗", "披露状态"],
        "body_text": "本页比较补救治疗相关指标。",
    },
    {
        "slug": "prohibited-medication",
        "title": "禁用药使用",
        "nav_label": "禁用药使用",
        "nav_group": "试验完成情况",
        "sections": ["使用人数", "定义口径", "时间窗"],
        "body_text": "本页比较禁用药使用相关指标。",
    },
    {
        "slug": "plan-deviation",
        "title": "方案偏离",
        "nav_label": "方案偏离",
        "nav_group": "试验完成情况",
        "sections": ["受试者数", "事件数", "重大偏离"],
        "body_text": "本页比较方案偏离相关指标。",
    },
    {
        "slug": "trial-exposure-context",
        "title": "试验与暴露语境",
        "nav_label": "试验与暴露语境",
        "nav_group": "试验与证据",
        "sections": ["试验角色", "治疗窗口", "暴露差异"],
        "body_text": "本页说明试验与暴露语境。",
    },
    {
        "slug": "subgroups-supporting-evidence",
        "title": "亚组与支持证据",
        "nav_label": "亚组与支持证据",
        "nav_group": "试验与证据",
        "sections": ["亚组", "延伸研究", "真实世界证据"],
        "body_text": "本页汇总亚组与支持证据。",
    },
    {
        "slug": "product-trial-profiles",
        "title": "产品与试验档案",
        "nav_label": "产品与试验档案",
        "nav_group": "试验与证据",
        "sections": ["产品档案", "试验档案", "结果覆盖"],
        "body_text": "本页汇总产品与试验档案。",
    },
    {
        "slug": "efficacy-safety-matrix",
        "title": "疗效与安全性矩阵",
        "nav_label": "疗效与安全性矩阵",
        "nav_group": "试验与证据",
        "sections": ["疗效维度", "安全性维度", "样本量位置"],
        "body_text": "本页展示疗效与安全性矩阵。",
    },
    {
        "slug": "evidence-limitations",
        "title": "研究依据与局限",
        "nav_label": "研究依据与局限",
        "nav_group": "试验与证据",
        "sections": ["来源成熟度", "可比性差异", "解释边界"],
        "body_text": "本页说明研究依据与局限。",
    },
]

B_EXPECTED_GROUPS = ["总览", "疗效与安全性", "基线与人群", "试验完成情况", "试验与证据"]

DESKTOP_WIDTHS = [1280, 1440, 1920]
MOBILE_WIDTH = 1024
BROWSERS = ["chromium", "webkit"]
PAGE_SLUGS = ["overview", "efficacy", "safety"]
DESKTOP_PARAMS = [(browser, width) for browser in BROWSERS for width in DESKTOP_WIDTHS]
OFFICIAL_LOGO_SHA256 = "8d16d3ae8353dd31f46a50d401e66f9e62af40be6cc42cdf5050866a4e6e1cae"

FORBIDDEN_VOCAB = re.compile(
    r"(?:gate|signal|accepted|pending|not_run|AI evidence synthesis"
    r"|prompt|diagnostic|retry|evidence threshold|coverage calculation"
    r"|backend|workflow state|status telemetry|version chatter"
    r"|report-class|report class definition"
    r"|A version|B version|C version"
    r"|gate\s*spec|GateSpec|registry-only"
    r"|工作流|提示词|日志|后端|验收节点|证据门槛|状态机|控制图"
    r"|检索过程|技术诊断|程序状态|版本噪声|覆盖计算)",
    re.IGNORECASE,
)

PLACEHOLDER_VOCAB = re.compile(r"预留|待数据|待补齐|稍后填入|结构入口|程序|占位")


def _build_portal(tmp_path: Path) -> Path:
    from ci_workflow.renderers.portal.builder import (
        NavEntry,
        PageSpec,
        PortalSpec,
        build_portal,
    )

    spec = PortalSpec(
        title=PORTAL_SPEC["title"],
        pages=[PageSpec(**page) for page in PORTAL_SPEC["pages"]],
        nav=[NavEntry(**item) for item in PORTAL_SPEC["nav"]],
        footer_text=PORTAL_SPEC["footer_text"],
    )
    out = tmp_path / "portal"
    build_portal(spec, out)
    return out


def _build_b_catalog_portal(tmp_path: Path) -> Path:
    from ci_workflow.renderers.portal.builder import PageSpec, PortalSpec, build_portal

    spec = PortalSpec(
        title="特应性皮炎试验结果比较",
        pages=[PageSpec(**page) for page in B_CATALOG_PAGES],
        footer_text="仅供产品中心医学部内部研判使用。",
    )
    out = tmp_path / "b-portal"
    build_portal(spec, out)
    return out


def _launch(playwright: Playwright, browser_name: str) -> Browser:
    browser_type = getattr(playwright, browser_name)
    return cast(Browser, browser_type.launch())


def _open_compact_header(page: Page) -> bool:
    """展开当前宽度下的折叠顶栏；常规桌面顶栏保持原状。"""
    toggle = page.locator("#menu-toggle")
    nav = page.locator(".site-header__nav")
    if not toggle.is_visible():
        return False
    if not nav.is_visible():
        toggle.click()
        page.wait_for_timeout(100)
    assert nav.is_visible()
    assert page.locator(".site-header__search").is_visible()
    return True


def _rects_overlap(a: dict[str, float], b: dict[str, float], *, tol: float = 1.0) -> bool:
    return (
        a["x"] + a["width"] - tol > b["x"]
        and b["x"] + b["width"] - tol > a["x"]
        and a["y"] + a["height"] - tol > b["y"]
        and b["y"] + b["height"] - tol > a["y"]
    )


def _attach_error_collectors(page: Page) -> tuple[list[str], list[str], list[str]]:
    page_errors: list[str] = []
    console_errors: list[str] = []
    remote_requests: list[str] = []

    page.on("pageerror", lambda err: page_errors.append(str(err)))
    page.on(
        "console",
        lambda message: (
            console_errors.append(f"{message.type}:{message.text}")
            if message.type in {"error", "warning"}
            else None
        ),
    )
    page.on(
        "request",
        lambda request: (
            remote_requests.append(request.url)
            if request.url.startswith(("http://", "https://"))
            and not request.url.startswith(("http://127.0.0.1:", "http://localhost:"))
            else None
        ),
    )
    return page_errors, console_errors, remote_requests


def _assert_no_text_clipping(page: Page) -> None:
    clipped = page.evaluate(
        """() => {
          const selectors = [
            '.site-header__title',
            '.site-header__nav-item',
            '.site-nav-group__trigger',
            '.site-nav-group__link',
            '.portal-page-title',
            '.portal-lead',
            '.portal-path-card__title',
            '.portal-reading-path__lead',
            '.site-footer__inner'
          ];
          const hits = [];
          for (const selector of selectors) {
            for (const el of document.querySelectorAll(selector)) {
              const style = getComputedStyle(el);
              if (style.display === 'none' || style.visibility === 'hidden') continue;
              if (style.overflow === 'hidden' || style.textOverflow === 'ellipsis') {
                hits.push({
                  selector,
                  reason: 'overflow-mask',
                  overflow: style.overflow,
                  textOverflow: style.textOverflow,
                  text: (el.innerText || '').slice(0, 40),
                });
              }
              if (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1) {
                hits.push({
                  selector,
                  text: (el.innerText || '').slice(0, 40),
                  scrollWidth: el.scrollWidth,
                  clientWidth: el.clientWidth,
                  scrollHeight: el.scrollHeight,
                  clientHeight: el.clientHeight,
                });
              }
            }
          }
          return hits;
        }"""
    )
    assert clipped == [], f"Text clipping detected: {clipped}"


def _visible_text(page: Page) -> str:
    return str(
        page.evaluate(
            """() => {
              const body = document.body.cloneNode(true);
              body.querySelectorAll('script,style,noscript').forEach(el => el.remove());
              return body.innerText;
            }"""
        )
    )


def _load_external_search_index(portal_dir: Path) -> list[dict[str, object]]:
    text = (portal_dir / "assets" / "search-index.js").read_text(encoding="utf-8")
    match = re.search(r"window\.__SEARCH_INDEX__\s*=\s*(\[.*\]);?\s*$", text, re.S)
    assert match, "search-index.js missing window.__SEARCH_INDEX__ assignment"
    value = json.loads(match.group(1))
    assert isinstance(value, list)
    return value


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(
        self,
        request: object,
        client_address: object,
        server: object,
        directory: str | None = None,
    ) -> None:
        super().__init__(
            cast(Any, request),
            cast(Any, client_address),
            cast(Any, server),
            directory=directory,
        )

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_server(directory: Path) -> tuple[http.server.HTTPServer, int]:
    port = _free_port()

    def handler_factory(request: object, client_address: object, server: object) -> _QuietHandler:
        return _QuietHandler(request, client_address, server, directory=str(directory))

    server = http.server.HTTPServer(("127.0.0.1", port), cast(Any, handler_factory))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port


class TestPortalShell:
    """Portal shell acceptance matrix."""

    def test_packaged_assets_match_repo_and_official_logo(self) -> None:
        module_assets = ROOT / "src" / "ci_workflow" / "renderers" / "portal" / "assets"
        repo_css = ROOT / "assets" / "portal" / "portal.css"
        repo_js = ROOT / "assets" / "portal" / "portal.js"
        module_css = module_assets / "portal.css"
        module_js = module_assets / "portal.js"
        module_logo = module_assets / "cms-logo.svg"
        brand_logo = ROOT / "assets" / "brand" / "cms-logo.svg"

        assert module_css.read_bytes() == repo_css.read_bytes()
        assert module_js.read_bytes() == repo_js.read_bytes()
        assert module_logo.read_bytes() == brand_logo.read_bytes()
        assert hashlib.sha256(module_logo.read_bytes()).hexdigest() == OFFICIAL_LOGO_SHA256

        manifest = json.loads(
            (ROOT / "assets" / "portal" / "manifest.json").read_text(encoding="utf-8")
        )
        assert (
            hashlib.sha256(repo_css.read_bytes()).hexdigest()
            == manifest["files"]["portal.css"]["sha256"]
        )
        assert (
            hashlib.sha256(repo_js.read_bytes()).hexdigest()
            == manifest["files"]["portal.js"]["sha256"]
        )

    def test_all_shared_portal_assets_match_repo_and_manifest(self) -> None:
        """F8：全部共享资产双副本字节相等，manifest 摘要按模块内发货副本校验。"""
        module_assets = ROOT / "src" / "ci_workflow" / "renderers" / "portal" / "assets"
        repo_portal = ROOT / "assets" / "portal"
        manifest = json.loads((repo_portal / "manifest.json").read_text(encoding="utf-8"))

        shared = ("charts.js", "portal.css", "portal.js",
                  "evidence-drawer.css", "evidence-drawer.js")
        for name in shared:
            repo_copy = repo_portal / name
            module_copy = module_assets / name
            assert module_copy.read_bytes() == repo_copy.read_bytes(), name
            entry = manifest["files"].get(name)
            assert entry is not None, f"manifest 缺少共享资产：{name}"
            # 运行期消费的是模块内副本；摘要必须绑定发货字节本身。
            assert hashlib.sha256(module_copy.read_bytes()).hexdigest() == entry["sha256"], name

    def test_wheel_install_can_build_portal(self, tmp_path: Path) -> None:
        dist_dir = tmp_path / "dist"
        venv_dir = tmp_path / "wheel-venv"
        site_dir = tmp_path / "wheel-site"
        dist_dir.mkdir()
        build = subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(dist_dir)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert build.returncode == 0, build.stderr or build.stdout
        wheels = list(dist_dir.glob("*.whl"))
        assert len(wheels) == 1, wheels

        create = subprocess.run(
            ["uv", "venv", str(venv_dir), "--python", "3.13"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert create.returncode == 0, create.stderr or create.stdout
        install = subprocess.run(
            ["uv", "pip", "install", "--python", str(venv_dir / "bin" / "python"), str(wheels[0])],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert install.returncode == 0, install.stderr or install.stdout

        probe = subprocess.run(
            [
                str(venv_dir / "bin" / "python"),
                "-c",
                (
                    "from pathlib import Path\n"
                    "from ci_workflow.renderers.portal import ("
                    "NavEntry, PageSpec, PortalSpec, build_portal, resolve_logo_src, "
                    "resolve_portal_asset)\n"
                    f"out = Path({str(site_dir)!r})\n"
                    "spec = PortalSpec(\n"
                    "  title='特应性皮炎竞品全景',\n"
                    "  pages=[\n"
                    "    PageSpec(slug='overview', title='竞品全景', nav_label='竞品全景',"
                    " sections=['靶点分布'], body_text='展示竞品格局要点。'),\n"
                    "    PageSpec(slug='efficacy', title='疗效比较', nav_label='疗效比较',"
                    " sections=['主要终点'], body_text='终点比较展示。'),\n"
                    "    PageSpec(slug='safety', title='安全性比较', nav_label='安全性比较',"
                    " sections=['常见不良事件'], body_text='安全性分层展示。'),\n"
                    "  ],\n"
                    "  nav=[\n"
                    "    NavEntry(label='竞品全景', slug='overview'),\n"
                    "    NavEntry(label='疗效比较', slug='efficacy'),\n"
                    "    NavEntry(label='安全性比较', slug='safety'),\n"
                    "  ],\n"
                    ")\n"
                    "paths = build_portal(spec, out)\n"
                    "logo = resolve_logo_src()\n"
                    "css = resolve_portal_asset('portal.css')\n"
                    "print('PAGES', len(paths))\n"
                    "print('LOGO', logo.exists(), logo.name)\n"
                    "print('CSS', css.exists())\n"
                    "print('OUT_LOGO', (out / 'assets' / 'logo.svg').exists())\n"
                    "print('OUT_CSS', (out / 'assets' / 'portal.css').exists())\n"
                    "print('OUT_JS', (out / 'assets' / 'portal.js').exists())\n"
                ),
            ],
            cwd=tmp_path,
            check=False,
            capture_output=True,
            text=True,
        )
        assert probe.returncode == 0, probe.stderr or probe.stdout
        assert "PAGES 3" in probe.stdout
        assert "OUT_LOGO True" in probe.stdout
        assert "OUT_CSS True" in probe.stdout
        assert "OUT_JS True" in probe.stdout
        assert (site_dir / "overview.html").exists()
        assert (site_dir / "assets" / "logo.svg").exists()

    @pytest.mark.parametrize("browser_name", BROWSERS)
    def test_logo_visible_upper_left_with_real_dimensions(
        self, browser_name: str, tmp_path: Path
    ) -> None:
        portal_dir = _build_portal(tmp_path)
        url = (portal_dir / "overview.html").as_uri()
        with sync_playwright() as playwright:
            browser = _launch(playwright, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page_errors, console_errors, remote_requests = _attach_error_collectors(page)
            page.goto(url)
            page.wait_for_load_state("domcontentloaded")
            page.evaluate("() => document.fonts.ready")

            logo = page.locator(".site-header__logo img")
            assert logo.count() == 1
            assert logo.is_visible()
            metrics = page.evaluate(
                """() => {
                  const img = document.querySelector('.site-header__logo img');
                  const header = document.querySelector('.site-header');
                  const box = img.getBoundingClientRect();
                  return {
                    complete: img.complete,
                    naturalWidth: img.naturalWidth,
                    naturalHeight: img.naturalHeight,
                    width: box.width,
                    height: box.height,
                    x: box.x,
                    y: box.y,
                    headerTop: header.getBoundingClientRect().top,
                    bodyPadTop: getComputedStyle(document.body).paddingTop,
                  };
                }"""
            )
            assert metrics["complete"] is True
            assert metrics["naturalWidth"] > 0
            assert metrics["naturalHeight"] > 0
            assert abs(metrics["width"] - 121) <= 1
            assert abs(metrics["height"] - 25) <= 1
            assert metrics["x"] < 40
            assert metrics["y"] < 40
            assert metrics["headerTop"] <= 1
            assert metrics["bodyPadTop"] in {"0px", ""}
            assert "logo.svg" in (logo.get_attribute("src") or "")
            assert (logo.get_attribute("alt") or "").strip()
            assert page_errors == []
            assert console_errors == []
            assert remote_requests == []
            browser.close()

    @pytest.mark.parametrize("browser_name,width", DESKTOP_PARAMS)
    def test_no_overlap_title_nav_search_and_no_clipping(
        self, browser_name: str, width: int, tmp_path: Path
    ) -> None:
        portal_dir = _build_portal(tmp_path)
        url = (portal_dir / "overview.html").as_uri()
        with sync_playwright() as playwright:
            browser = _launch(playwright, browser_name)
            page = browser.new_page(viewport={"width": width, "height": 800})
            page.goto(url)
            page.wait_for_load_state("domcontentloaded")
            compact = _open_compact_header(page)

            boxes = {
                "logo": page.locator(".site-header__logo").bounding_box(),
                "title": page.locator(".site-header__title").bounding_box(),
                "nav": page.locator(".site-header__nav").bounding_box(),
                "search": page.locator(".site-header__search").bounding_box(),
            }
            assert all(boxes.values()), boxes
            logo = cast(dict[str, float], boxes["logo"])
            title = cast(dict[str, float], boxes["title"])
            nav = cast(dict[str, float], boxes["nav"])
            search = cast(dict[str, float], boxes["search"])
            pairs = [
                (logo, title),
                (title, nav),
                (nav, search),
                (logo, nav),
            ]
            for left, right in pairs:
                assert not _rects_overlap(left, right), f"header collision at {width}: {boxes}"
            assert title["x"] >= logo["x"] + logo["width"] - 1
            if compact:
                assert nav["y"] >= logo["y"] + logo["height"] - 1
                assert search["y"] >= nav["y"] + nav["height"] - 1
            else:
                assert nav["x"] >= title["x"] + title["width"] - 1
                assert search["x"] >= nav["x"] + nav["width"] - 1
            rightmost = search["x"] + search["width"]
            assert rightmost <= width + 1

            _assert_no_text_clipping(page)
            screenshot = tmp_path / f"header_{browser_name}_{width}.png"
            page.screenshot(path=str(screenshot))
            assert screenshot.exists()
            browser.close()

    @pytest.mark.parametrize("browser_name", BROWSERS)
    def test_current_page_and_single_footer(self, browser_name: str, tmp_path: Path) -> None:
        portal_dir = _build_portal(tmp_path)
        with sync_playwright() as playwright:
            browser = _launch(playwright, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            for slug in PAGE_SLUGS:
                page.goto((portal_dir / f"{slug}.html").as_uri())
                page.wait_for_load_state("domcontentloaded")
                active = page.locator(".site-header__nav-item--active")
                assert active.count() == 1
                assert active.get_attribute("aria-current") == "page"
                assert slug in (active.get_attribute("href") or "")
                assert page.locator(".site-footer").count() == 1
                assert "产品中心医学部" in page.locator(".site-footer").inner_text()
                assert "内部研判" in page.locator(".site-footer").inner_text()
            browser.close()

    @pytest.mark.parametrize("browser_name", BROWSERS)
    def test_content_shell_lead_before_reading_path(
        self, browser_name: str, tmp_path: Path
    ) -> None:
        portal_dir = _build_portal(tmp_path)
        with sync_playwright() as playwright:
            browser = _launch(playwright, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto((portal_dir / "overview.html").as_uri())
            page.wait_for_load_state("domcontentloaded")

            order = page.evaluate(
                """() => {
                  const title = document.querySelector('.portal-page-title');
                  const lead = document.querySelector('.portal-lead');
                  const path = document.querySelector('.portal-reading-path');
                  const cards = Array.from(document.querySelectorAll('.portal-path-card__title'))
                    .map(el => el.textContent.trim());
                  const titleTop = title.getBoundingClientRect().top;
                  const leadTop = lead.getBoundingClientRect().top;
                  const pathTop = path.getBoundingClientRect().top;
                  const mainBottom = document.querySelector('.portal-main')
                    .getBoundingClientRect().bottom;
                  return {
                    titleTop, leadTop, pathTop, cards, mainBottom,
                    leadText: lead.textContent.trim(),
                    shellNoteCount: document.querySelectorAll('.portal-shell-note').length,
                    hintCount: document.querySelectorAll('.portal-path-card__hint').length,
                  };
                }"""
            )
            assert order["leadTop"] > order["titleTop"]
            assert order["pathTop"] > order["leadTop"]
            assert order["cards"] == ["靶点分布", "开发阶段", "地域状态"]
            assert "靶点结构" in order["leadText"]
            assert page.locator(".portal-reading-path__title").inner_text() == "重点模块"
            assert page.locator(".portal-page-kicker").count() == 0
            assert order["shellNoteCount"] == 0
            assert order["hintCount"] == 0
            assert order["mainBottom"] > 420
            assert page.locator(".portal-path-card").count() == 3
            visible = _visible_text(page)
            assert not re.search(r"\b\d+(\.\d+)?%\b", visible)
            assert PLACEHOLDER_VOCAB.search(visible) is None
            assert "仅供参考，不构成任何医学建议" not in visible
            page.screenshot(path=str(tmp_path / f"shell_{browser_name}_1280.png"), full_page=True)
            browser.close()

    @pytest.mark.parametrize("browser_name", BROWSERS)
    def test_no_audience_placeholder_vocabulary(
        self, browser_name: str, tmp_path: Path
    ) -> None:
        for builder in (_build_portal, _build_b_catalog_portal):
            portal_dir = builder(tmp_path / builder.__name__)
            with sync_playwright() as playwright:
                browser = _launch(playwright, browser_name)
                page = browser.new_page(viewport={"width": 1280, "height": 800})
                for html in sorted(portal_dir.glob("*.html")):
                    page.goto(html.as_uri())
                    page.wait_for_load_state("domcontentloaded")
                    hits = PLACEHOLDER_VOCAB.findall(_visible_text(page))
                    assert hits == [], f"{html.name}: {hits}"
                browser.close()

    @pytest.mark.parametrize("browser_name", BROWSERS)
    def test_group_trigger_shows_chevron_and_expanded_state(
        self, browser_name: str, tmp_path: Path
    ) -> None:
        portal_dir = _build_b_catalog_portal(tmp_path)
        with sync_playwright() as playwright:
            browser = _launch(playwright, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto((portal_dir / "overview.html").as_uri())
            page.wait_for_load_state("domcontentloaded")
            _open_compact_header(page)
            trigger = page.locator(".site-nav-group__trigger", has_text="疗效与安全性")
            chevron = trigger.locator(".site-nav-group__chevron")
            assert chevron.count() == 1
            assert chevron.is_visible()
            assert trigger.get_attribute("aria-expanded") == "false"
            trigger.click()
            page.wait_for_timeout(100)
            assert trigger.get_attribute("aria-expanded") == "true"
            rotated = page.evaluate(
                """(el) => {
                  const chevron = el.querySelector('.site-nav-group__chevron');
                  return getComputedStyle(chevron).transform;
                }""",
                trigger.element_handle(),
            )
            assert rotated not in {"none", "matrix(1, 0, 0, 1, 0, 0)"}
            browser.close()

    def test_explicit_nav_order_overrides_page_order(self, tmp_path: Path) -> None:
        from ci_workflow.renderers.portal.builder import (
            NavEntry,
            PageSpec,
            PortalBuildError,
            PortalSpec,
            build_portal,
        )
        from ci_workflow.renderers.portal.page_shell import _build_nav_groups

        pages = [
            PageSpec(
                slug="overview",
                title="首页",
                nav_label="首页",
                nav_group="总览",
                sections=["主要终点总览"],
                body_text="本页给出试验比较总览。",
            ),
            PageSpec(
                slug="efficacy",
                title="疗效",
                nav_label="疗效",
                nav_group="疗效与安全性",
                sections=["主要终点"],
                body_text="本页比较疗效终点。",
            ),
            PageSpec(
                slug="safety",
                title="安全性",
                nav_label="安全性",
                nav_group="疗效与安全性",
                sections=["严重不良事件"],
                body_text="本页比较安全性指标。",
            ),
        ]
        # Explicit nav deliberately reverses page order and regroups labels.
        nav = [
            NavEntry(label="安全性", slug="safety", group="疗效与安全性"),
            NavEntry(label="疗效", slug="efficacy", group="疗效与安全性"),
            NavEntry(label="首页", slug="overview", group="总览"),
        ]
        spec = PortalSpec(
            title="特应性皮炎试验结果比较",
            pages=pages,
            nav=nav,
            footer_text="仅供产品中心医学部内部研判使用。",
        )
        groups = _build_nav_groups(spec)
        assert [label for label, _ in groups] == ["疗效与安全性", "总览"]
        assert [page["slug"] for page in groups[0][1]] == ["safety", "efficacy"]
        assert [page["slug"] for page in groups[1][1]] == ["overview"]

        out_dir = tmp_path / "nav-order"
        build_portal(spec, out_dir)
        html = (out_dir / "overview.html").read_text(encoding="utf-8")
        safety_pos = html.find('href="safety.html"')
        efficacy_pos = html.find('href="efficacy.html"')
        overview_link = html.find('href="overview.html" class="site-header__nav-item')
        assert 0 <= safety_pos < efficacy_pos
        assert overview_link > efficacy_pos

        with pytest.raises(PortalBuildError):
            build_portal(
                PortalSpec(
                    title="特应性皮炎试验结果比较",
                    pages=pages,
                    nav=[
                        NavEntry(label="首页", slug="overview", group="总览"),
                        NavEntry(label="疗效", slug="efficacy", group="疗效与安全性"),
                    ],
                ),
                tmp_path / "nav-missing",
            )

        with pytest.raises(PortalBuildError):
            build_portal(
                PortalSpec(
                    title="特应性皮炎试验结果比较",
                    pages=pages,
                    nav=[
                        NavEntry(label="首页", slug="overview", group="总览"),
                        NavEntry(label="疗效", slug="efficacy", group="疗效与安全性"),
                        NavEntry(label="安全性", slug="safety", group="疗效与安全性"),
                        NavEntry(label="重复", slug="overview", group="总览"),
                    ],
                ),
                tmp_path / "nav-dup",
            )

    @pytest.mark.parametrize("browser_name,width", DESKTOP_PARAMS)
    def test_b_catalog_grouped_nav_scale(
        self, browser_name: str, width: int, tmp_path: Path
    ) -> None:
        portal_dir = _build_b_catalog_portal(tmp_path)
        assert len(list(portal_dir.glob("*.html"))) == 21
        with sync_playwright() as playwright:
            browser = _launch(playwright, browser_name)
            page = browser.new_page(viewport={"width": width, "height": 900})
            page_errors, console_errors, remote_requests = _attach_error_collectors(page)
            page.goto((portal_dir / "overview.html").as_uri())
            page.wait_for_load_state("domcontentloaded")

            compact = page.locator("#menu-toggle").is_visible()

            group_labels = page.evaluate(
                """() => Array.from(document.querySelectorAll(
                  '.site-header__nav-item, .site-nav-group__trigger'
                )).map(el => el.textContent.trim())"""
            )
            assert group_labels == B_EXPECTED_GROUPS

            # Shallow header: only groups visible at top, not all 21 page labels.
            assert page.locator(".site-nav-group").count() == 5
            assert page.locator(".site-nav-group__link").count() >= 16

            header_box = page.locator(".site-header").bounding_box()
            assert header_box is not None
            assert header_box["height"] <= 88
            if compact:
                _open_compact_header(page)
            boxes = {
                "logo": page.locator(".site-header__logo").bounding_box(),
                "title": page.locator(".site-header__title").bounding_box(),
                "nav": page.locator(".site-header__nav").bounding_box(),
                "search": page.locator(".site-header__search").bounding_box(),
            }
            assert all(boxes.values()), boxes
            logo = cast(dict[str, float], boxes["logo"])
            title = cast(dict[str, float], boxes["title"])
            nav = cast(dict[str, float], boxes["nav"])
            search = cast(dict[str, float], boxes["search"])
            for left, right in [(logo, title), (title, nav), (nav, search)]:
                assert not _rects_overlap(left, right), boxes
            assert search["x"] + search["width"] <= width + 1
            _assert_no_text_clipping(page)

            # Open a multi-page group and navigate by keyboard-accessible link.
            trigger = page.locator(".site-nav-group__trigger", has_text="疗效与安全性")
            trigger.click()
            assert trigger.get_attribute("aria-expanded") == "true"
            link = page.locator(".site-nav-group__link", has_text="纵向结果")
            assert link.is_visible()
            link.click()
            page.wait_for_load_state("domcontentloaded")
            assert "longitudinal-results" in page.url
            assert page.locator(".site-nav-group__link--active").inner_text() == "纵向结果"
            assert page.locator(".site-nav-group__trigger--current").inner_text() == "疗效与安全性"

            # Every physical page exists and is reachable from nav markup.
            hrefs = page.evaluate(
                """() => Array.from(document.querySelectorAll(
                  '.site-header__nav a[href$=".html"]'
                )).map(a => a.getAttribute('href'))"""
            )
            assert len(set(hrefs)) == 21
            for href in hrefs:
                assert (portal_dir / normpath(href)).exists(), href

            page.screenshot(path=str(tmp_path / f"b_nav_{browser_name}_{width}.png"))
            assert page_errors == []
            assert console_errors == []
            assert remote_requests == []
            browser.close()

    @pytest.mark.parametrize("browser_name", BROWSERS)
    def test_b_catalog_mobile_grouped_nav(self, browser_name: str, tmp_path: Path) -> None:
        portal_dir = _build_b_catalog_portal(tmp_path)
        with sync_playwright() as playwright:
            browser = _launch(playwright, browser_name)
            page = browser.new_page(viewport={"width": MOBILE_WIDTH, "height": 900})
            page.goto((portal_dir / "overview.html").as_uri())
            page.wait_for_load_state("domcontentloaded")
            toggle = page.locator("#menu-toggle")
            nav = page.locator(".site-header__nav")
            assert not nav.is_visible()
            toggle.click()
            page.wait_for_timeout(200)
            assert nav.is_visible()
            page.locator(".site-nav-group__trigger", has_text="试验完成情况").click()
            assert page.locator(".site-nav-group__link", has_text="筛败与原因").is_visible()
            page.screenshot(path=str(tmp_path / f"b_mobile_{browser_name}.png"))
            browser.close()

    @pytest.mark.parametrize("browser_name", BROWSERS)
    def test_three_linked_pages_no_dead_links(self, browser_name: str, tmp_path: Path) -> None:
        portal_dir = _build_portal(tmp_path)
        with sync_playwright() as playwright:
            browser = _launch(playwright, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page_errors, console_errors, remote_requests = _attach_error_collectors(page)
            page.goto((portal_dir / "overview.html").as_uri())
            page.wait_for_load_state("domcontentloaded")

            nav_links = page.locator(".site-header__nav-item")
            assert nav_links.count() >= 3
            for index in range(nav_links.count()):
                href = nav_links.nth(index).get_attribute("href") or ""
                target = portal_dir / normpath(href)
                assert target.exists(), f"Dead nav link: {href} -> {target}"

            for slug in PAGE_SLUGS:
                page.goto((portal_dir / f"{slug}.html").as_uri())
                page.wait_for_load_state("domcontentloaded")
                for index in range(page.locator("a[href]").count()):
                    href = page.locator("a[href]").nth(index).get_attribute("href") or ""
                    if href.startswith(("#", "javascript:")):
                        continue
                    target = portal_dir / normpath(href)
                    assert target.exists(), f"Dead link on {slug}: {href}"

            _open_compact_header(page)
            page.locator('.site-header__nav-item[href*="efficacy"]').first.click()
            page.wait_for_load_state("domcontentloaded")
            assert "efficacy" in page.url
            assert page_errors == []
            assert console_errors == []
            assert remote_requests == []
            browser.close()

    @pytest.mark.parametrize("browser_name", BROWSERS)
    def test_inline_and_external_search_index_consistency(
        self, browser_name: str, tmp_path: Path
    ) -> None:
        portal_dir = _build_portal(tmp_path)
        external = _load_external_search_index(portal_dir)
        with sync_playwright() as playwright:
            browser = _launch(playwright, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto((portal_dir / "overview.html").as_uri())
            page.wait_for_load_state("domcontentloaded")
            inline = page.evaluate("window.__SEARCH_INDEX__")
            assert inline == external
            assert {item["slug"] for item in inline} == set(PAGE_SLUGS)
            scripts = page.evaluate(
                """() => Array.from(document.scripts).map(s => s.getAttribute('src'))"""
            )
            assert any(src and "search-index.js" in src for src in scripts)
            assert any(src and "portal.js" in src for src in scripts)
            browser.close()

    @pytest.mark.parametrize("browser_name", BROWSERS)
    def test_global_search_keyboard_highlight_and_navigation(
        self, browser_name: str, tmp_path: Path
    ) -> None:
        portal_dir = _build_portal(tmp_path)
        with sync_playwright() as playwright:
            browser = _launch(playwright, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto((portal_dir / "overview.html").as_uri())
            page.wait_for_load_state("domcontentloaded")
            _open_compact_header(page)

            search = page.locator("#global-search-input")
            search.fill("疗效")
            page.wait_for_timeout(150)
            results = page.locator("#global-search-results")
            assert results.get_attribute("hidden") is None
            assert page.locator(".site-header__search-result").count() > 0
            assert "疗效" in page.locator(".site-header__search-result").first.inner_text()
            assert page.locator(".site-header__search-result-mark").count() > 0

            search.press("ArrowDown")
            assert page.locator(".site-header__search-result--focused").count() == 1
            search.press("Enter")
            page.wait_for_load_state("domcontentloaded")
            assert "efficacy" in page.url

            _open_compact_header(page)
            search = page.locator("#global-search-input")
            search.fill("安全性")
            page.wait_for_timeout(150)
            marks = page.locator(".site-header__search-result-mark")
            assert marks.count() > 0
            assert "安全性" in marks.first.inner_text()
            page.screenshot(path=str(tmp_path / f"search_{browser_name}.png"))
            browser.close()

    @pytest.mark.parametrize("browser_name", BROWSERS)
    def test_mobile_toggle_reduced_motion_and_focus(
        self, browser_name: str, tmp_path: Path
    ) -> None:
        portal_dir = _build_portal(tmp_path)
        url = (portal_dir / "overview.html").as_uri()
        with sync_playwright() as playwright:
            browser = _launch(playwright, browser_name)
            page = browser.new_page(viewport={"width": MOBILE_WIDTH, "height": 800})
            page.goto(url)
            page.wait_for_load_state("domcontentloaded")
            nav = page.locator(".site-header__nav")
            toggle = page.locator("#menu-toggle")
            assert not nav.is_visible()
            assert toggle.is_visible()
            toggle.click()
            page.wait_for_timeout(200)
            assert nav.is_visible()
            assert toggle.get_attribute("aria-expanded") == "true"
            toggle.click()
            page.wait_for_timeout(200)
            assert not nav.is_visible()
            page.screenshot(path=str(tmp_path / f"mobile_{browser_name}.png"))
            page.close()

            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                reduced_motion="reduce",
            )
            page = context.new_page()
            page.goto(url)
            page.wait_for_load_state("domcontentloaded")
            _open_compact_header(page)
            duration = page.evaluate(
                """() => {
                  const el = document.querySelector('.site-header__nav-item');
                  return getComputedStyle(el).transitionDuration;
                }"""
            )
            assert (
                duration in {"0s", "0.01ms", "0.00001s", "1e-05s"}
                or float(duration.replace("ms", "").replace("s", "")) <= 0.001
            )
            assert page.locator(".portal-page-title").is_visible()
            assert page.locator(".site-footer").is_visible()
            _assert_no_text_clipping(page)
            # Chromium tabs through links; macOS WebKit defaults to form controls only.
            page.locator("#menu-toggle").focus()
            page.keyboard.press("Shift+Tab")
            focus_state = page.evaluate(
                """() => {
                  const focused = document.activeElement;
                  if (!focused) return { ok: false, reason: 'none' };
                  const style = getComputedStyle(focused);
                  const outlineVisible =
                    style.outlineStyle !== 'none' && style.outlineWidth !== '0px';
                  const borderAccent = style.borderColor.includes('255, 153, 0')
                    || style.borderColor.toLowerCase().includes('#ff9900');
                  return {
                    ok: focused.matches(':focus-visible') && (outlineVisible || borderAccent),
                    tag: focused.tagName,
                    className: focused.className,
                    outlineStyle: style.outlineStyle,
                    borderColor: style.borderColor,
                  };
                }"""
            )
            if not focus_state["ok"] and browser_name == "webkit":
                page.focus("#global-search-input")
                page.keyboard.press("Shift+Tab")
                page.keyboard.press("Tab")
                focus_state = page.evaluate(
                    """() => {
                      const focused = document.activeElement;
                      if (!focused) return { ok: false };
                      const style = getComputedStyle(focused);
                      const outlineVisible =
                        style.outlineStyle !== 'none' && style.outlineWidth !== '0px';
                      const borderAccent = style.borderColor.includes('255, 153, 0');
                      return {
                        ok: focused.id === 'global-search-input'
                          && focused.matches(':focus-visible')
                          && (outlineVisible || borderAccent),
                        tag: focused.tagName,
                        className: focused.className,
                        outlineStyle: style.outlineStyle,
                        borderColor: style.borderColor,
                      };
                    }"""
                )
            assert focus_state["ok"], focus_state
            # Links remain keyboard-activatable even when WebKit skips them in Tab order.
            activatable = page.evaluate(
                """() => {
                  const link = document.querySelector('.site-header__nav-item');
                  link.focus();
                  return document.activeElement === link && !!link.getAttribute('href');
                }"""
            )
            assert activatable
            context.close()
            browser.close()

    @pytest.mark.parametrize("browser_name", BROWSERS)
    def test_forbidden_vocab_tokens_fonts_and_contrast_floor(
        self, browser_name: str, tmp_path: Path
    ) -> None:
        portal_dir = _build_portal(tmp_path)
        with sync_playwright() as playwright:
            browser = _launch(playwright, browser_name)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            for slug in PAGE_SLUGS:
                page.goto((portal_dir / f"{slug}.html").as_uri())
                page.wait_for_load_state("domcontentloaded")
                visible = page.evaluate(
                    """() => {
                      const body = document.body.cloneNode(true);
                      body.querySelectorAll('script,style,noscript').forEach(el => el.remove());
                      return body.innerText;
                    }"""
                )
                assert FORBIDDEN_VOCAB.findall(visible) == []
            metrics = page.evaluate(
                """() => {
                  const body = getComputedStyle(document.body);
                  const active = getComputedStyle(
                    document.querySelector('.site-header__nav-item--active')
                  );
                  const btn = getComputedStyle(
                    document.querySelector('.site-header__menu-toggle')
                  );
                  const htmlBg = getComputedStyle(document.documentElement).backgroundColor;
                  const orange = getComputedStyle(document.documentElement)
                    .getPropertyValue('--kz-orange').trim();
                  return {
                    bodyFont: parseFloat(body.fontSize),
                    navFont: parseFloat(active.fontSize),
                    searchFont: parseFloat(
                      getComputedStyle(document.querySelector('#global-search-input')).fontSize
                    ),
                    activeColor: active.color,
                    htmlBg,
                    orange,
                    fontFamily: body.fontFamily,
                    tabular: body.fontVariantNumeric,
                    menuDisplay: btn.display,
                  };
                }"""
            )
            assert metrics["bodyFont"] >= 16
            assert metrics["navFont"] >= 16
            assert metrics["searchFont"] >= 16
            assert metrics["orange"] == "#FF9900"
            assert "255" in metrics["activeColor"]
            assert "255" in metrics["htmlBg"] or "248" in metrics["htmlBg"]
            assert any(
                token in metrics["fontFamily"]
                for token in ("YaHei", "PingFang", "Noto Sans SC", "Arial")
            )
            assert "tabular" in metrics["tabular"].lower()
            browser.close()

    def test_static_server_and_file_protocol(self, tmp_path: Path) -> None:
        portal_dir = _build_portal(tmp_path)
        server, port = _start_server(portal_dir)
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={"width": 1280, "height": 800})
                page_errors, console_errors, remote_requests = _attach_error_collectors(page)
                for slug in PAGE_SLUGS:
                    page.goto(f"http://127.0.0.1:{port}/{slug}.html")
                    page.wait_for_load_state("domcontentloaded")
                    assert page.locator(".portal-page-title").is_visible()
                    _assert_no_text_clipping(page)
                assert page_errors == []
                assert console_errors == []
                # Local static server requests are expected; remote CDN/host must stay empty.
                assert remote_requests == []
                page.close()

                for slug in PAGE_SLUGS:
                    page = browser.new_page(viewport={"width": 1280, "height": 800})
                    page_errors, console_errors, remote_requests = _attach_error_collectors(page)
                    page.goto((portal_dir / f"{slug}.html").as_uri())
                    page.wait_for_load_state("domcontentloaded")
                    assert page.locator(".portal-page-title").is_visible()
                    assert page_errors == []
                    assert console_errors == []
                    assert remote_requests == []
                    page.close()
                browser.close()
        finally:
            server.shutdown()

    @pytest.mark.parametrize("browser_name,width", DESKTOP_PARAMS)
    def test_screenshot_matrix(self, browser_name: str, width: int, tmp_path: Path) -> None:
        portal_dir = _build_portal(tmp_path)
        with sync_playwright() as playwright:
            browser = _launch(playwright, browser_name)
            page = browser.new_page(viewport={"width": width, "height": 800})
            for slug in PAGE_SLUGS:
                page.goto((portal_dir / f"{slug}.html").as_uri())
                page.wait_for_load_state("domcontentloaded")
                path = tmp_path / f"{slug}_{browser_name}_{width}.png"
                page.screenshot(path=str(path), full_page=True)
                assert path.exists()
            browser.close()


def test_builder_rejects_unknown_nav_slug(tmp_path: Path) -> None:
    from ci_workflow.renderers.portal.builder import (
        NavEntry,
        PageSpec,
        PortalBuildError,
        PortalSpec,
        build_portal,
    )

    spec = PortalSpec(
        title="特应性皮炎竞品全景",
        pages=[
            PageSpec(
                slug="overview",
                title="竞品全景",
                nav_label="竞品全景",
                sections=["靶点分布"],
            )
        ],
        nav=[NavEntry(label="缺失页", slug="missing")],
    )
    with pytest.raises(PortalBuildError):
        build_portal(spec, tmp_path / "bad")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
