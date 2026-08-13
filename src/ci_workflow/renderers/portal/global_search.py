"""Global search: index building and keyword matching for portal pages.

Provides:
  - ``SearchIndexEntry``: typed data for one searchable page.
  - ``build_search_index``: build entries from page specs.
  - ``search``: fuzzy keyword search against the index.

All search is local (no fetch); works from ``file://``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol


class _PageLike(Protocol):
    """Duck-typed page spec for search indexing."""

    @property
    def slug(self) -> str: ...
    @property
    def title(self) -> str: ...
    @property
    def nav_label(self) -> str: ...
    @property
    def sections(self) -> list[str]: ...


@dataclass(frozen=True)
class SearchIndexEntry:
    """One page in the search index."""

    slug: str
    title: str
    keywords: list[str]


def build_search_index(pages: Iterable[_PageLike]) -> list[SearchIndexEntry]:
    """Build search index from a list of PageSpec-like objects."""
    entries: list[SearchIndexEntry] = []
    for p in pages:
        title = p.title
        slug = p.slug
        nav_label = p.nav_label
        sections = list(p.sections)
        nav_group = str(getattr(p, "nav_group", "") or "")
        keywords = _extract_keywords(title, nav_label, sections, nav_group)
        entries.append(SearchIndexEntry(slug=slug, title=title, keywords=keywords))
    return entries


def _extract_keywords(
    title: str, nav_label: str, sections: list[str], nav_group: str = ""
) -> list[str]:
    """Extract searchable keywords from page metadata."""
    text = f"{title} {nav_label} {nav_group} {' '.join(sections)}"
    tokens = re.split(r"[\s,，。、；：\u201c\u201d\u2018\u2019（）()《》\-/]+", text)
    seen: set[str] = set()
    result: list[str] = []
    for t in tokens:
        t = t.strip()
        if len(t) < 1:
            continue
        lower = t.lower()
        if lower not in seen:
            seen.add(lower)
            result.append(t)
    return result


def search(
    query: str,
    index: list[SearchIndexEntry],
) -> list[SearchIndexEntry]:
    """Search the index for pages matching *query*.

    Returns matching entries ordered by relevance (title match first,
    then keyword match, then nav label match).
    """
    if not query.strip():
        return list(index)

    query_lower = query.strip().lower()
    query_chars = set(query_lower)

    scored: list[tuple[int, SearchIndexEntry]] = []
    for entry in index:
        score = _score_entry(query_lower, query_chars, entry)
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: (-x[0], x[1].slug))
    return [e for _, e in scored]


def _score_entry(
    query_lower: str,
    query_chars: set[str],
    entry: SearchIndexEntry,
) -> int:
    """Score an entry against a query. 0 = no match."""
    score = 0
    title_lower = entry.title.lower()
    # Exact title match
    if query_lower in title_lower:
        score += 100
    # Title character overlap
    elif query_chars.issubset(set(title_lower)):
        score += 50

    # Keyword matches
    for kw in entry.keywords:
        kw_lower = kw.lower()
        if query_lower in kw_lower or kw_lower in query_lower:
            score += 10
        elif query_chars.issubset(set(kw_lower)):
            score += 5

    return score
