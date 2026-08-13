"""Page shell: generates HTML for each portal page.

Produces a complete HTML document with:
  - Shallow sticky header (logo, concise title, grouped nav, search)
  - Meaningful content shell (lead under title + reading-path cards)
  - Single quiet footer
  - Shared CSS/JS plus inline and external search indexes
  - ``file://``-safe relative asset paths
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from html import escape
from typing import Any, Protocol

from ci_workflow.renderers.portal.global_search import SearchIndexEntry, build_search_index


class _PageLike(Protocol):
    slug: str
    title: str
    nav_label: str
    sections: list[str]
    body_text: str


class _NavLike(Protocol):
    label: str
    slug: str


class _PortalLike(Protocol):
    title: str
    pages: Sequence[_PageLike]
    nav: Sequence[_NavLike]
    footer_text: str


class PortalShellError(ValueError):
    """Raised when navigation grouping cannot be resolved safely."""


def _e(text: str) -> str:
    """HTML-escape text."""
    return escape(text, quote=True)


def _page_group(page: _PageLike) -> str:
    group = str(getattr(page, "nav_group", "") or "").strip()
    return group or page.nav_label


def _nav_group(item: _NavLike, page: _PageLike) -> str:
    group = str(getattr(item, "group", "") or "").strip()
    return group or _page_group(page)


def _dom_id(prefix: str, label: str, index: int) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", label).strip("-").lower()
    if not slug:
        slug = "group"
    return f"{prefix}-{index}-{slug}"


def _build_nav_groups(spec: _PortalLike) -> list[tuple[str, list[dict[str, str]]]]:
    """Build ordered navigation groups.

    Prefer explicit ``PortalSpec.nav`` order/labels/groups when supplied.
    Fall back to page order only when nav is empty.
    """
    page_by_slug = {page.slug: page for page in spec.pages}
    groups: list[tuple[str, list[dict[str, str]]]] = []
    index: dict[str, list[dict[str, str]]] = {}

    if spec.nav:
        nav_slugs = [item.slug for item in spec.nav]
        if len(nav_slugs) != len(set(nav_slugs)):
            raise PortalShellError("导航项存在重复页面")
        missing = set(page_by_slug) - set(nav_slugs)
        unknown = set(nav_slugs) - set(page_by_slug)
        if missing or unknown:
            raise PortalShellError("导航必须覆盖全部页面且不得引用未知页面")
        source = [
            (
                item.slug,
                item.label,
                _nav_group(item, page_by_slug[item.slug]),
            )
            for item in spec.nav
        ]
    else:
        source = [
            (page.slug, page.nav_label, _page_group(page)) for page in spec.pages
        ]

    for slug, label, group_label in source:
        bucket = index.get(group_label)
        if bucket is None:
            bucket = []
            index[group_label] = bucket
            groups.append((group_label, bucket))
        bucket.append({"slug": slug, "label": label})
    return groups


def _render_grouped_nav(
    groups: list[tuple[str, list[dict[str, str]]]], current_slug: str
) -> str:
    """Render shallow grouped navigation: group triggers + page panels."""
    parts: list[str] = []
    for group_index, (label, pages) in enumerate(groups, start=1):
        current_in_group = any(page["slug"] == current_slug for page in pages)
        group_cls = "site-nav-group"
        if current_in_group:
            group_cls += " site-nav-group--current"

        if len(pages) == 1:
            page = pages[0]
            link_cls = "site-header__nav-item"
            if page["slug"] == current_slug:
                link_cls += " site-header__nav-item--active"
            aria = "page" if page["slug"] == current_slug else "false"
            parts.append(
                f'<div class="{group_cls}">'
                f'<a href="{_e(page["slug"])}.html" class="{link_cls}" '
                f'aria-current="{aria}">{_e(label)}</a>'
                f"</div>"
            )
            continue

        trigger_cls = "site-nav-group__trigger"
        if current_in_group:
            trigger_cls += " site-nav-group__trigger--current"
        panel_id = _dom_id("nav-group", label, group_index)
        links = []
        for page in pages:
            link_cls = "site-nav-group__link"
            if page["slug"] == current_slug:
                link_cls += " site-nav-group__link--active"
            aria = "page" if page["slug"] == current_slug else "false"
            links.append(
                f'<a href="{_e(page["slug"])}.html" class="{link_cls}" '
                f'aria-current="{aria}">{_e(page["label"])}</a>'
            )
        links_html = "\n            ".join(links)
        parts.append(
            f'<div class="{group_cls}">\n'
            f'          <button type="button" class="{trigger_cls}" '
            f'aria-expanded="false" aria-haspopup="true" '
            f'aria-controls="{panel_id}">'
            f'<span class="site-nav-group__label">{_e(label)}</span>'
            f'<span class="site-nav-group__chevron" aria-hidden="true"></span>'
            f"</button>\n"
            f'          <div class="site-nav-group__panel" id="{panel_id}" hidden>\n'
            f"            {links_html}\n"
            f"          </div>\n"
            f"        </div>"
        )
    return "\n        ".join(parts)


def _search_index_literal(entries: list[SearchIndexEntry]) -> str:
    data = [{"slug": e.slug, "title": e.title, "keywords": e.keywords} for e in entries]
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def render_search_index_json(entries: list[SearchIndexEntry]) -> str:
    """Render the search index as a JS global assignment."""
    return f"window.__SEARCH_INDEX__ = {_search_index_literal(entries)};\n"


def _render_filter_panel(
    filter_groups: list[dict[str, Any]] | None = None,
    synthetic_rows: list[dict[str, str]] | None = None,
    page_id: str = "",
) -> str:
    """Render filter panel HTML for page-level and module-level filters.

    Expected group keys:
    - title: Chinese dimension label
    - scope: ``page`` | ``module``
    - module_id: required when scope is module
    - advanced: optional bool — collapsed under「更多条件」
    - disabled / disabled_reason: hide-or-disable with Chinese reason
    - items: [{id, label, dim}]
    """
    if not filter_groups:
        return ""

    page_groups: list[str] = []
    module_groups: dict[str, list[str]] = {}
    advanced_groups: dict[str, list[str]] = {}
    module_labels: dict[str, str] = {}
    active_module_id = ""

    for group in filter_groups:
        group_title = _e(str(group.get("title", "")))
        group_items = group.get("items", [])
        scope = str(group.get("scope", "page"))
        module_id = str(group.get("module_id", ""))
        module_label = str(group.get("module_label", "") or "").strip()
        is_advanced = bool(group.get("advanced", False))
        disabled = bool(group.get("disabled", False))
        disabled_reason = _e(str(group.get("disabled_reason", "") or ""))
        if scope == "module" and module_id and not active_module_id:
            active_module_id = module_id
        if scope == "module" and module_id:
            if not module_label:
                if "efficacy" in module_id:
                    module_label = "疗效数据"
                elif "safety" in module_id:
                    module_label = "安全性数据"
                else:
                    module_label = "当前数据"
            module_labels[module_id] = module_label

        items_html_parts: list[str] = []
        for item in group_items:
            item_id = _e(str(item.get("id", "")))
            item_label = _e(str(item.get("label", "")))
            dim_id = _e(str(item.get("dim", "")))
            item_disabled = disabled or bool(item.get("disabled", False))
            item_test_only = bool(item.get("test_only", False))
            item_reason = _e(
                str(
                    item.get("disabled_reason")
                    or disabled_reason
                    or "当前页面或模块不适用此条件"
                )
            )
            disabled_attrs = ""
            disabled_class = ""
            if item_disabled:
                disabled_attrs = (
                    f' aria-disabled="true" disabled title="{item_reason}"'
                )
                disabled_class = " kz-filter-item--disabled"
            test_only_attrs = ' hidden data-test-only="true"' if item_test_only else ""
            items_html_parts.append(
                f'          <button type="button" class="kz-filter-item'
                f'{disabled_class}" '
                f'data-dim="{dim_id}" data-val="{item_id}" '
                f'data-scope="{_e(scope)}" '
                f'data-module-id="{_e(module_id)}" '
                f'role="checkbox" aria-checked="false" tabindex="0"'
                f"{disabled_attrs}{test_only_attrs}>"
                f'<span class="kz-filter-item__check" aria-hidden="true"></span>'
                f"{item_label}</button>"
            )
        items_html = "\n".join(items_html_parts)
        block = (
            f'      <div class="kz-filter-group" data-scope="{_e(scope)}" '
            f'data-module-id="{_e(module_id)}">\n'
            f'        <h4 class="kz-filter-group__title">{group_title}</h4>\n'
            f'        <div class="kz-filter-group__items">\n'
            f"{items_html}\n"
            f"        </div>\n"
            f"      </div>"
        )
        if scope == "module" and is_advanced:
            advanced_groups.setdefault(module_id, []).append(block)
        elif scope == "module":
            module_groups.setdefault(module_id, []).append(block)
        else:
            page_groups.append(block)

    page_html = "\n".join(page_groups)
    module_sections: list[str] = []
    module_ids = list(dict.fromkeys([*module_groups, *advanced_groups]))
    for module_index, module_id in enumerate(module_ids):
        module_html = "\n".join(module_groups.get(module_id, []))
        advanced_html = ""
        module_advanced = advanced_groups.get(module_id, [])
        if module_advanced:
            advanced_html = (
                '      <details class="kz-filter-advanced">\n'
                '        <summary class="kz-filter-advanced__summary">'
                '<span aria-hidden="true">›</span> 更多条件</summary>\n'
                + "\n".join(module_advanced)
                + "\n      </details>"
            )
        label = module_labels[module_id]
        reset_label = label.removesuffix("数据")
        reset_id = (
            "kz-filter-reset-module"
            if module_index == 0
            else f"kz-filter-reset-module-{module_index + 1}"
        )
        module_sections.append(
            f"""      <section class="kz-filter-scope" data-scope="module"
               data-module-id="{_e(module_id)}" data-module-label="{_e(label)}"
               aria-label="{_e(label)}">
        <h3 class="kz-filter-scope__title">{_e(label)}</h3>
{module_html}
{advanced_html}
        <button type="button" class="kz-filter-reset-btn kz-filter-reset-module"
                id="{_e(reset_id)}" data-module-id="{_e(module_id)}">
          清除{_e(reset_label)}条件
        </button>
      </section>"""
        )
    module_section = "\n".join(module_sections)

    empty_module_buttons = "\n".join(
        f'''        <button type="button" class="kz-filter-reset-btn kz-filter-empty-reset-module"
                data-module-id="{_e(module_id)}">
          清除{_e(module_labels[module_id].removesuffix("数据"))}条件
        </button>'''
        for module_id in module_ids
    )

    rows_literal = json.dumps(
        synthetic_rows or [], ensure_ascii=False, separators=(",", ":")
    )

    return f"""    <div class="kz-filter-bar">
      <button type="button" class="kz-filter-entry" id="kz-filter-entry"
              aria-expanded="false" aria-controls="kz-filter-panel">
        筛选条件
        <span class="kz-filter-entry__count" style="display:none">0</span>
      </button>
      <div class="kz-filter-chips" id="kz-filter-chips" aria-label="已选筛选条件"></div>
      <span class="kz-filter-summary" id="kz-filter-summary">无筛选条件</span>
      <p class="kz-filter-local-hint" id="kz-filter-local-hint" hidden
         role="status">当前选择过多，请保存为本地视图</p>
      <p class="kz-filter-restore-error" id="kz-filter-restore-error" hidden
         role="alert">无法恢复此筛选网址</p>
    </div>

    <details class="kz-filter-panel" id="kz-filter-panel"
             data-page-id="{_e(page_id)}" data-module-id="{_e(active_module_id)}">
      <summary class="kz-filter-panel__native-summary">筛选条件</summary>
      <div class="kz-filter-panel__header">
        <h2 class="kz-filter-panel__title">筛选条件</h2>
        <button type="button" class="kz-filter-panel__close" id="kz-filter-close"
                aria-label="关闭筛选面板">×</button>
      </div>
      <section class="kz-filter-scope" data-scope="page" aria-label="整份报告条件">
        <h3 class="kz-filter-scope__title">整份报告条件</h3>
{page_html}
        <button type="button" class="kz-filter-reset-btn" id="kz-filter-reset-page">
          清除整份报告条件
        </button>
      </section>
{module_section}
    </details>

    <p class="kz-filter-row-count" id="kz-filter-row-count"></p>
    <div class="kz-filter-empty" id="kz-filter-empty" style="display:none">
      <p class="kz-filter-empty__title">当前选择下暂无可比较数据</p>
      <div class="kz-filter-empty__restrictions" id="kz-filter-empty-restrictions"></div>
      <div class="kz-filter-empty__actions">
        <button type="button" class="kz-filter-reset-btn" id="kz-filter-empty-reset-page">
          清除整份报告条件
        </button>
{empty_module_buttons}
      </div>
    </div>

    <script>window.__FILTER_ROWS__ = {rows_literal};</script>
"""


def _render_reading_path(sections: list[str]) -> str:
    if not sections:
        return (
            '    <section class="portal-reading-path" aria-label="重点模块">\n'
            '      <h2 class="portal-reading-path__title">重点模块</h2>\n'
            "    </section>\n"
        )
    cards: list[str] = []
    for index, section in enumerate(sections, start=1):
        cards.append(
            '        <li class="portal-path-card">\n'
            f'          <span class="portal-path-card__index">{index:02d}</span>\n'
            f'          <h3 class="portal-path-card__title">{_e(section)}</h3>\n'
            "        </li>"
        )
    cards_html = "\n".join(cards)
    return (
        '    <section class="portal-reading-path" aria-label="重点模块">\n'
        '      <div class="portal-reading-path__head">\n'
        '        <h2 class="portal-reading-path__title">重点模块</h2>\n'
        "      </div>\n"
        f'      <ol class="portal-path-grid">\n{cards_html}\n      </ol>\n'
        "    </section>\n"
    )


def render_page_html(
    *,
    page: _PageLike,
    spec: _PortalLike,
    assets_rel: str = "assets",
    filter_groups: list[dict[str, Any]] | None = None,
    synthetic_rows: list[dict[str, str]] | None = None,
) -> str:
    """Render a complete HTML page from typed portal specs."""
    slug = page.slug
    title = page.title
    sections = list(page.sections)
    body_text = page.body_text
    report_title = spec.title
    footer_text = spec.footer_text

    groups = _build_nav_groups(spec)
    if not groups:
        raise PortalShellError("Portal must declare at least one navigation entry")
    home_slug = groups[0][1][0]["slug"]

    search_entries = build_search_index(spec.pages)
    search_json = _search_index_literal(search_entries)

    lead_html = ""
    if body_text:
        lead_html = f'      <p class="portal-lead">{_e(body_text)}</p>\n'

    filter_html = _render_filter_panel(
        filter_groups=filter_groups,
        synthetic_rows=synthetic_rows,
        page_id=slug if slug.startswith("/") else f"/{slug}",
    )
    reading_path = _render_reading_path(sections)
    kicker_html = ""
    page_group = _page_group(page)
    if title != "首页" and page_group != title:
        kicker_html = f'      <p class="portal-page-kicker">{_e(page_group)}</p>\n'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="only light">
  <link rel="icon" href="data:,">
  <title>{_e(title)} - {_e(report_title)}</title>
  <link rel="stylesheet" href="{assets_rel}/portal.css">
</head>
<body>
  <header class="site-header" role="banner">
    <div class="site-header__inner">
      <a href="{_e(home_slug)}.html" class="site-header__logo" aria-label="康哲药业">
        <img src="{assets_rel}/logo.svg" alt="康哲药业" width="121" height="25"
             decoding="async">
      </a>
      <span class="site-header__title">{_e(report_title)}</span>
      <nav class="site-header__nav" id="site-primary-nav" aria-label="主导航">
        {_render_grouped_nav(groups, slug)}
      </nav>
      <div class="site-header__search">
        <label class="visually-hidden" for="global-search-input">全局搜索</label>
        <input type="search"
               id="global-search-input"
               class="site-header__search-input"
               placeholder="搜索页面或关键词…"
               aria-label="全局搜索"
               autocomplete="off">
        <div id="global-search-results"
             class="site-header__search-results"
             role="listbox"
             hidden></div>
      </div>
      <button type="button"
              class="site-header__menu-toggle"
              id="menu-toggle"
              aria-label="打开导航菜单"
              aria-expanded="false"
              aria-controls="site-primary-nav">
        菜单
      </button>
    </div>
    <div class="site-header__brand-line" aria-hidden="true"></div>
  </header>

  <main class="portal-main" id="main" role="main">
    <header class="portal-page-head">
{kicker_html}      
      <h1 class="portal-page-title">{_e(title)}</h1>
{lead_html}    </header>
{filter_html}{reading_path}  </main>

  <footer class="site-footer" role="contentinfo">
    <div class="site-footer__inner">
      <span>{_e(footer_text)}</span>
    </div>
  </footer>

  <script>window.__SEARCH_INDEX__ = {search_json};</script>
  <script src="{assets_rel}/search-index.js"></script>
  <script src="{assets_rel}/portal.js"></script>
</body>
</html>
"""
