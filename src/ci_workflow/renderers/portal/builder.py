"""Portal builder: typed page specs → deterministic physical HTML files.

Produces a complete static portal directory with:
  - Shared assets (CSS, JS, SVG logo)
  - One ``<slug>.html`` per ``PageSpec``
  - ``search-index.js`` for global search

Assets resolve from the packaged module tree first (wheel-safe), then from
the repository ``assets/`` tree in editable source checkouts.  The builder
never fetches remote resources.  Output is ``file://``-safe.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, Field, field_validator, model_validator

from ci_workflow.renderers.portal.global_search import SearchIndexEntry, build_search_index
from ci_workflow.renderers.portal.page_shell import render_page_html, render_search_index_json

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

_MAX_REPORT_TITLE_CHARS = 24


class NavEntry(BaseModel):
    """One leaf navigation link (used when flat nav is explicitly supplied)."""

    label: str = Field(..., description="Chinese navigation label, e.g. 首页")
    slug: str = Field(
        ...,
        description="Target page slug (matches PageSpec.slug)",
        pattern=r"^[a-z0-9][a-z0-9-]*$",
    )
    group: str = Field(
        default="",
        description="Optional Chinese navigation group label",
    )


class PageSpec(BaseModel):
    """Typed specification for a single physical portal page."""

    slug: str = Field(
        ...,
        description="Page slug used as filename: <slug>.html",
        pattern=r"^[a-z0-9][a-z0-9-]*$",
    )
    title: str = Field(..., description="Page title shown in <title> and h1")
    nav_label: str = Field(..., description="Label in header navigation")
    nav_group: str = Field(
        default="",
        description="Chinese navigation group, e.g. 基线与人群",
    )
    sections: list[str] = Field(
        default_factory=list,
        description="Section headings rendered as reading-path cards",
    )
    body_text: str = Field(
        default="",
        description="Page summary shown immediately under the title",
    )


class PortalSpec(BaseModel):
    """Complete portal specification: pages, navigation, metadata."""

    title: str = Field(..., description="Report title shown in header")
    pages: list[PageSpec] = Field(..., min_length=1)
    nav: list[NavEntry] = Field(default_factory=list)
    footer_text: str = Field(
        default="仅供产品中心医学部内部研判使用。",
        description="Quiet footer disclaimer for medical readers",
    )

    @field_validator("title")
    @classmethod
    def _title_must_be_concise(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("报告标题不能为空")
        if len(normalized) > _MAX_REPORT_TITLE_CHARS:
            raise ValueError(
                f"报告标题过长（{len(normalized)}字），请缩短为"
                f"不超过{_MAX_REPORT_TITLE_CHARS}个字的简洁中文标题"
            )
        return normalized

    @model_validator(mode="after")
    def _default_nav_from_pages(self) -> PortalSpec:
        if not self.nav:
            self.nav = [
                NavEntry(
                    label=page.nav_label,
                    slug=page.slug,
                    group=page.nav_group or page.nav_label,
                )
                for page in self.pages
            ]
        return self


class PortalBuildError(RuntimeError):
    """Raised when the builder encounters an invalid spec or I/O failure."""


# ---------------------------------------------------------------------------
# Asset resolution (wheel-safe)
# ---------------------------------------------------------------------------

_MODULE_DIR = Path(__file__).resolve().parent
_MODULE_ASSETS_DIR = _MODULE_DIR / "assets"
_OFFICIAL_LOGO_SHA256 = "8d16d3ae8353dd31f46a50d401e66f9e62af40be6cc42cdf5050866a4e6e1cae"
_ECHARTS_BUNDLE_SHA256 = "b66b25aeb4df84e33199dc21694014d336d222cbd9deb0e5a7c14bd6aa0d0fd0"
_ECHARTS_BUNDLE_NAME = "echarts.min.js"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_assets_root() -> Path | None:
    """Best-effort repository ``assets/`` root for editable checkouts."""
    candidate = _MODULE_DIR.parents[3] / "assets"
    if candidate.is_dir():
        return candidate
    for parent in _MODULE_DIR.parents:
        assets = parent / "assets"
        if (assets / "portal").is_dir() and (assets / "brand").is_dir():
            return assets
    return None


def resolve_portal_asset(name: str) -> Path:
    """Resolve a portal static asset for copy into a generated site."""
    module_candidate = _MODULE_ASSETS_DIR / name
    if module_candidate.is_file():
        return module_candidate

    repo_assets = _repo_assets_root()
    if repo_assets is not None:
        if name in {"portal.css", "portal.js", "charts.js"}:
            repo_candidate = repo_assets / "portal" / name
            if repo_candidate.is_file():
                return repo_candidate
        if name in {"cms-logo.svg", "logo.svg"}:
            brand = repo_assets / "brand" / "cms-logo.svg"
            if brand.is_file():
                return brand

    raise PortalBuildError(
        f"Portal asset '{name}' not found in packaged module assets "
        f"({_MODULE_ASSETS_DIR}) or repository assets tree"
    )


def resolve_echarts_bundle() -> Path:
    """Resolve offline ECharts 6.1.0 bundle (wheel-safe; no silent repo fallback).

    Fail-closed if the packaged module asset is missing or digest mismatches.
    Repository ``assets/third-party/echarts/`` is never used as a silent runtime path.
    """
    candidate = _MODULE_ASSETS_DIR / _ECHARTS_BUNDLE_NAME
    if not candidate.is_file():
        raise PortalBuildError(
            "包内缺少 ECharts 离线包（失败关闭）："
            f"{candidate}。请将 assets/third-party/echarts/echarts.min.js "
            "以可测试资源合同复制到 src/ci_workflow/renderers/portal/assets/"
        )
    digest = _sha256(candidate)
    if digest != _ECHARTS_BUNDLE_SHA256:
        raise PortalBuildError(f"ECharts 包摘要不匹配：{digest} != {_ECHARTS_BUNDLE_SHA256}")
    return candidate


def resolve_logo_src() -> Path:
    """Return the official CMS logo path and verify its digest."""
    for name in ("cms-logo.svg", "logo.svg"):
        try:
            logo = resolve_portal_asset(name)
        except PortalBuildError:
            continue
        digest = _sha256(logo)
        if digest != _OFFICIAL_LOGO_SHA256:
            raise PortalBuildError(
                f"Logo digest mismatch for {logo}: {digest} != {_OFFICIAL_LOGO_SHA256}"
            )
        return logo
    raise PortalBuildError("Official CMS logo asset not found")


def _copy_asset(src: Path, dest_dir: Path, name: str) -> Path:
    dest = dest_dir / name
    shutil.copy2(src, dest)
    return dest


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_portal(spec: PortalSpec, output_dir: Path) -> list[Path]:
    """Build the complete portal into *output_dir*.

    Returns the list of generated HTML file paths in page order.
    """
    page_slugs = {page.slug for page in spec.pages}
    if len(page_slugs) != len(spec.pages):
        raise PortalBuildError("Page slugs must be unique")
    nav_slugs = [nav.slug for nav in spec.nav]
    if len(nav_slugs) != len(set(nav_slugs)):
        raise PortalBuildError("导航项存在重复页面")
    if set(nav_slugs) != page_slugs:
        raise PortalBuildError("导航必须覆盖全部页面且不得引用未知页面")
    for nav in spec.nav:
        if nav.slug not in page_slugs:
            raise PortalBuildError(
                f"Nav entry '{nav.label}' references slug '{nav.slug}' "
                f"which is not in the page list"
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    logo_src = resolve_logo_src()
    _copy_asset(logo_src, assets_dir, "logo.svg")
    _copy_asset(resolve_portal_asset("portal.css"), assets_dir, "portal.css")
    _copy_asset(resolve_portal_asset("portal.js"), assets_dir, "portal.js")
    _copy_asset(resolve_portal_asset("charts.js"), assets_dir, "charts.js")
    _copy_asset(resolve_echarts_bundle(), assets_dir, _ECHARTS_BUNDLE_NAME)

    search_entries: list[SearchIndexEntry] = build_search_index(spec.pages)
    search_index_js = render_search_index_json(search_entries)
    (assets_dir / "search-index.js").write_text(search_index_js, encoding="utf-8")

    generated: list[Path] = []
    for page in spec.pages:
        html = render_page_html(
            page=page,
            spec=cast(Any, spec),
            assets_rel="assets",
        )
        html_path = output_dir / f"{page.slug}.html"
        html_path.write_text(html, encoding="utf-8")
        generated.append(html_path)

    return generated
