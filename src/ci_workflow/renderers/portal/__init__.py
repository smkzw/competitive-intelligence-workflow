"""Task 4.2 康哲门户壳层：builder + page_shell + global_search。

公开 API：

* ``build_portal`` — 从 ``PortalSpec`` 生成确定性物理 HTML 页面。
* ``PageSpec``, ``NavEntry``, ``PortalSpec``, ``SearchIndexEntry`` — 类型化输入。
* ``resolve_logo_src`` / ``resolve_portal_asset`` — 轮分发安全的资产解析。
"""

from ci_workflow.renderers.portal.builder import (
    NavEntry,
    PageSpec,
    PortalBuildError,
    PortalSpec,
    build_portal,
    resolve_logo_src,
    resolve_portal_asset,
)
from ci_workflow.renderers.portal.global_search import SearchIndexEntry, build_search_index
from ci_workflow.renderers.portal.page_shell import (
    render_page_html,
    render_search_index_json,
)

__all__ = [
    "NavEntry",
    "PageSpec",
    "PortalBuildError",
    "PortalSpec",
    "SearchIndexEntry",
    "build_portal",
    "build_search_index",
    "render_page_html",
    "render_search_index_json",
    "resolve_logo_src",
    "resolve_portal_asset",
]
