"""Task 4.2/4.3 康哲门户壳层：builder + page_shell + global_search + filters。

公开 API：

* ``build_portal`` — 从 ``PortalSpec`` 生成确定性物理 HTML 页面。
* ``PageSpec``, ``NavEntry``, ``PortalSpec``, ``SearchIndexEntry`` — 类型化输入。
* ``resolve_logo_src`` / ``resolve_portal_asset`` / ``resolve_echarts_bundle``
  — 轮分发安全的资产解析。
* ``render_page_html`` — 支持 filter_groups / synthetic_rows 参数。
"""

from ci_workflow.renderers.portal.builder import (
    NavEntry,
    PageSpec,
    PortalBuildError,
    PortalSpec,
    build_portal,
    resolve_echarts_bundle,
    resolve_logo_src,
    resolve_portal_asset,
)
from ci_workflow.renderers.portal.filters import (
    MODULE_DIMENSION_IDS,
    MODULE_DIMENSION_LABELS_ZH,
    PAGE_DIMENSION_IDS,
    PAGE_DIMENSION_LABELS_ZH,
    AnchorTrialState,
    EvidenceSelection,
    FilterDimension,
    FilterState,
    FilterValue,
    FilterVersion,
    ModuleFilterState,
    PageFilterScope,
    PaginationState,
    PortalFilterError,
    SortState,
    assert_known_filter_profile,
    assert_known_page_route,
    dimension_applicability_reason,
    select_view_rows,
)
from ci_workflow.renderers.portal.global_search import SearchIndexEntry, build_search_index
from ci_workflow.renderers.portal.page_shell import (
    render_page_html,
    render_search_index_json,
)
from ci_workflow.renderers.portal.url_state import (
    SAVE_LOCAL_VIEW_HINT_ZH,
    URL_SIZE_LIMIT,
    UrlSerializeOutcome,
    UrlStateError,
    decode_filter_state,
    encode_filter_state,
    serialize_filter_state,
)

__all__ = [
    "MODULE_DIMENSION_IDS",
    "MODULE_DIMENSION_LABELS_ZH",
    "PAGE_DIMENSION_IDS",
    "PAGE_DIMENSION_LABELS_ZH",
    "SAVE_LOCAL_VIEW_HINT_ZH",
    "AnchorTrialState",
    "EvidenceSelection",
    "FilterDimension",
    "FilterState",
    "FilterValue",
    "FilterVersion",
    "ModuleFilterState",
    "NavEntry",
    "PageFilterScope",
    "PageSpec",
    "PaginationState",
    "PortalBuildError",
    "PortalFilterError",
    "PortalSpec",
    "SearchIndexEntry",
    "SortState",
    "URL_SIZE_LIMIT",
    "UrlSerializeOutcome",
    "UrlStateError",
    "assert_known_filter_profile",
    "assert_known_page_route",
    "build_portal",
    "build_search_index",
    "decode_filter_state",
    "dimension_applicability_reason",
    "encode_filter_state",
    "render_page_html",
    "render_search_index_json",
    "resolve_echarts_bundle",
    "resolve_logo_src",
    "resolve_portal_asset",
    "select_view_rows",
    "serialize_filter_state",
]
