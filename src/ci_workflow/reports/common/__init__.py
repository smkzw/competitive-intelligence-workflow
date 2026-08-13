"""Task 4.1 共用报告视图与覆盖合同包。

对外公开：规范覆盖集合/格式投影（``coverage``）、稳定行视图
（``view_state``）、冻结页面注册表与站点地图（``page_registry``）、
单行集图表/表格联动合同（``chart_specs``）。
"""

from ci_workflow.reports.common.chart_specs import (
    ChartTableBoundaryError,
    ChartTableModule,
    FilteredRowSet,
    validate_chart_table_module_payload,
    validate_filtered_row_set_payload,
)
from ci_workflow.reports.common.coverage import (
    CoverageBoundaryError,
    CoverageException,
    CoverageExceptionKind,
    CoverageItem,
    CoverageItemKind,
    CoverageProjection,
    CoverageSet,
    EquivalenceEvidence,
    compute_coverage_projection_content_digest,
    compute_coverage_set_content_digest,
    derive_coverage_exception_id,
    derive_coverage_item_id,
    derive_coverage_projection_id,
    derive_coverage_set_id,
    validate_coverage_projection_payload,
    validate_coverage_set_payload,
)
from ci_workflow.reports.common.page_registry import (
    DynamicRouteSpec,
    PageRegistry,
    PageRegistryError,
    ReportCatalog,
    StaticPage,
)
from ci_workflow.reports.common.view_state import (
    ReportRow,
    ReportViewModel,
    ViewStateBoundaryError,
    derive_row_id,
    validate_report_row_payload,
    validate_report_view_model_payload,
)

__all__ = [
    "ChartTableBoundaryError",
    "ChartTableModule",
    "CoverageBoundaryError",
    "CoverageException",
    "CoverageExceptionKind",
    "CoverageItem",
    "CoverageItemKind",
    "CoverageProjection",
    "CoverageSet",
    "DynamicRouteSpec",
    "EquivalenceEvidence",
    "FilteredRowSet",
    "PageRegistry",
    "PageRegistryError",
    "ReportCatalog",
    "ReportRow",
    "ReportViewModel",
    "StaticPage",
    "ViewStateBoundaryError",
    "compute_coverage_projection_content_digest",
    "compute_coverage_set_content_digest",
    "derive_coverage_exception_id",
    "derive_coverage_item_id",
    "derive_coverage_projection_id",
    "derive_coverage_set_id",
    "derive_row_id",
    "validate_chart_table_module_payload",
    "validate_coverage_projection_payload",
    "validate_coverage_set_payload",
    "validate_filtered_row_set_payload",
    "validate_report_row_payload",
    "validate_report_view_model_payload",
]
