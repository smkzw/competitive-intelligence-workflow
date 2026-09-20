"""B 报告科学视图层：裁决、分组与视图集合的唯一权威来源。

渲染器（renderers/portal/report_b.py）只消费本包产出的分区、视图
和提案，不另行做跨试验可比性裁决。
"""

from ci_workflow.reports.b.contracts import (
    EndpointCompatibilityPolicy,
    EndpointCompatibilityResult,
    EndpointObservation,
    TimepointCompatibilityPolicy,
    match_endpoint_compatibility,
)
from ci_workflow.reports.b.efficacy import (
    EfficacyFactRow,
    EfficacyViewError,
    EfficacyViewSet,
    build_efficacy_views,
)
from ci_workflow.reports.b.portal_science import efficacy_science_partition

__all__ = [
    "EndpointCompatibilityPolicy",
    "EndpointCompatibilityResult",
    "EndpointObservation",
    "TimepointCompatibilityPolicy",
    "match_endpoint_compatibility",
    "EfficacyFactRow",
    "EfficacyViewError",
    "EfficacyViewSet",
    "build_efficacy_views",
    "efficacy_science_partition",
]
