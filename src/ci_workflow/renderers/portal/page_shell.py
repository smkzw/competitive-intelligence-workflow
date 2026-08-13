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
from typing import Protocol

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
{reading_path}  </main>

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
