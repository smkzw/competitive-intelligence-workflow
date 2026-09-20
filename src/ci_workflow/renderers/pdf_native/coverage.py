"""PDF coverage projection for Task 8.2 PDF09.

Projects searchable PDF text + outline bookmarks onto the frozen PageRegistry
page-responsibility catalog for reports A/B/C, then diffs against the locked
``coverage-set-expected.json`` counts. This module only reports gaps; it never
rewrites report content to force a green result.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ci_workflow.domain.enums import ReportKind
from ci_workflow.reports.common.page_registry import PageRegistry

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_EXPECTED = (
    ROOT / "fixtures/synthetic/three-report-complete/inputs/coverage-set-expected.json"
)

# Bookmark keys / alternate titles emitted by current A/B/C PDF projections
# mapped onto PageRegistry page_responsibility_id values.
_BOOKMARK_ALIASES: dict[str, dict[str, str]] = {
    "A": {
        "cover": "overview",
        "封面": "overview",
        "封面与摘要": "overview",
        "toc": "overview",
        "目录": "overview",
        "summary": "overview",
        "首页摘要": "overview",
        "landscape": "landscape",
        "竞争格局": "landscape",
        "product-overview": "product-overview",
        "产品总览": "product-overview",
        "clinical-portfolio": "clinical-portfolio",
        "临床开发组合": "clinical-portfolio",
        "efficacy": "efficacy",
        "疗效": "efficacy",
        "safety": "safety",
        "安全性": "safety",
        "matrix": "matrix",
        "疗效与安全性矩阵": "matrix",
        "regulatory": "regulatory",
        "中国与全球监管": "regulatory",
        "companies-transactions": "companies-transactions",
        "企业与交易": "companies-transactions",
        "patents-protection": "patents-protection",
        "专利与保护": "patents-protection",
        "historical-edge": "historical-edge",
        "历史与边缘观察": "historical-edge",
        "evidence-limitations": "evidence-limitations",
        "研究依据与局限": "evidence-limitations",
    },
    "B": {
        "cover": "overview",
        "封面": "overview",
        "封面与摘要": "overview",
        "toc": "overview",
        "目录": "overview",
        "summary": "overview",
        "首页摘要": "overview",
        "efficacy": "efficacy",
        "疗效": "efficacy",
        "longitudinal-results": "longitudinal-results",
        "纵向结果": "longitudinal-results",
        "safety": "safety",
        "安全性": "safety",
        "efficacy-safety-matrix": "efficacy-safety-matrix",
        "疗效与安全性矩阵": "efficacy-safety-matrix",
        "baseline-overview": "baseline-overview",
        "基线与人群总览": "baseline-overview",
        "baseline-demographics": "baseline-demographics",
        "人口学": "baseline-demographics",
        "baseline-disease-context": "baseline-disease-context",
        "疾病语境": "baseline-disease-context",
        "baseline-severity": "baseline-severity",
        "基线疾病严重程度": "baseline-severity",
        "disposition-overview": "disposition-overview",
        "试验完成情况": "disposition-overview",
        "试验完成情况总览": "disposition-overview",
        "participant-flow": "participant-flow",
        "受试者流转": "participant-flow",
        "adherence": "adherence",
        "依从性": "adherence",
        "loss-exit": "loss-exit",
        "失访与退出": "loss-exit",
        "screen-failure": "screen-failure",
        "筛败与原因": "screen-failure",
        "rescue-treatment": "rescue-treatment",
        "补救治疗": "rescue-treatment",
        "prohibited-medication": "prohibited-medication",
        "禁用药使用": "prohibited-medication",
        "plan-deviation": "plan-deviation",
        "方案偏离": "plan-deviation",
        "trial-exposure-context": "trial-exposure-context",
        "试验与暴露语境": "trial-exposure-context",
        "subgroups-supporting-evidence": "subgroups-supporting-evidence",
        "亚组与支持证据": "subgroups-supporting-evidence",
        "product-trial-profiles": "product-trial-profiles",
        "产品与试验档案": "product-trial-profiles",
        "evidence-limitations": "evidence-limitations",
        "研究依据与局限": "evidence-limitations",
    },
    "C": {
        "cover": "overview",
        "封面": "overview",
        "封面与摘要": "overview",
        "toc": "overview",
        "目录": "overview",
        "summary": "overview",
        "首页摘要": "overview",
        "design-map": "design-map",
        "设计图谱": "design-map",
        "population": "population-disease-definition",
        "人群与疾病定义": "population-disease-definition",
        "inclusion": "inclusion-criteria",
        "入选标准": "inclusion-criteria",
        "exclusion": "exclusion-criteria",
        "排除标准": "exclusion-criteria",
        "intervention": "treatment-arms",
        "分组、干预与对照": "treatment-arms",
        "endpoints": "endpoint-timepoint-matrix",
        "终点、定义与时间点": "endpoint-timepoint-matrix",
        "visits": "visit-duration-followup",
        "访视、疗程与随访": "visit-duration-followup",
        "statistics": "sample-analysis-statistics",
        "样本量、分析集与统计设计": "sample-analysis-statistics",
        "trial-dossiers": "trial-profile",
        "逐试验详情": "trial-profile",
        "patterns-paths": "design-patterns",
        "设计模式、权衡与可选路径": "design-patterns",
        "evidence-limits": "evidence-versions-limitations",
        "资料版本与局限": "evidence-versions-limitations",
    },
}

# Extra searchable needles that prove a page responsibility is present even when
# the bookmark key differs from the registry id.
_TEXT_NEEDLES: dict[str, dict[str, tuple[str, ...]]] = {
    "A": {
        "overview": ("封面", "目录", "首页摘要", "摘要", "特应性皮炎"),
        "landscape": ("竞争格局",),
        "product-overview": ("产品总览",),
        "clinical-portfolio": ("临床开发组合",),
        "efficacy": ("疗效", "疗效比较图", "疗效完整数据表"),
        "safety": ("安全性", "安全性热图", "安全性完整数据表"),
        "matrix": ("疗效与安全性矩阵", "疗效与安全性气泡图"),
        "regulatory": ("中国与全球监管",),
        "companies-transactions": ("企业与交易",),
        "patents-protection": ("专利与保护",),
        "historical-edge": ("历史与边缘观察", "历史与边缘"),
        "evidence-limitations": ("研究依据与局限", "证据局限"),
    },
    "B": {
        "overview": ("封面", "目录", "首页摘要", "摘要", "特应性皮炎"),
        "efficacy": ("疗效", "疗效比较柱状图", "疗效完整数据表"),
        "longitudinal-results": ("纵向结果", "纵向结果折线图"),
        "safety": ("安全性", "安全性热图"),
        "efficacy-safety-matrix": ("疗效与安全性矩阵", "疗效与安全性气泡图"),
        "baseline-overview": ("基线与人群总览",),
        "baseline-demographics": ("人口学",),
        "baseline-disease-context": ("疾病语境",),
        "baseline-severity": ("基线疾病严重程度", "严重程度"),
        "disposition-overview": ("试验完成情况",),
        "participant-flow": ("受试者流转",),
        "adherence": ("依从性",),
        "loss-exit": ("失访与退出",),
        "screen-failure": ("筛败与原因", "筛败"),
        "rescue-treatment": ("补救治疗",),
        "prohibited-medication": ("禁用药使用", "禁用药"),
        "plan-deviation": ("方案偏离",),
        "trial-exposure-context": ("试验与暴露语境", "暴露语境"),
        "subgroups-supporting-evidence": ("亚组与支持证据", "亚组"),
        "product-trial-profiles": ("产品与试验档案",),
        "evidence-limitations": ("研究依据与局限", "证据局限"),
    },
    "C": {
        "overview": ("封面", "目录", "首页摘要", "关键已披露结果一览", "特应性皮炎"),
        "design-map": ("设计图谱",),
        "trial-profile": ("逐试验详情", "试验档案"),
        "population-disease-definition": ("人群与疾病定义",),
        "inclusion-criteria": ("入选标准",),
        "exclusion-criteria": ("排除标准",),
        "treatment-arms": ("分组、干预与对照",),
        "endpoint-timepoint-matrix": ("终点、定义与时间点",),
        "visit-duration-followup": ("访视、疗程与随访",),
        "sample-analysis-statistics": ("样本量、分析集与统计设计",),
        "design-patterns": ("设计模式", "可选路径", "路径"),
        "evidence-versions-limitations": ("资料版本与局限",),
    },
}

_FORBIDDEN_AUDIENCE_MARKERS = (
    "snapshot-",
    "gate-spec",
    "prompt",
    "workflow",
    "RENDERER_",
    "fixture run",
    "v-fixture-001",
    "html.manifest",
    "chromium",
    "playwright",
)


@dataclass
class PageCoverageStatus:
    page_responsibility_id: str
    title_zh: str
    covered: bool
    evidence: list[str] = field(default_factory=list)
    missing_reasons: list[str] = field(default_factory=list)


@dataclass
class PdfCoverageProjection:
    report: str
    expected_page_count: int
    registry_page_count: int
    covered_page_ids: list[str]
    missing_page_ids: list[str]
    unexpected_bookmark_titles: list[str]
    pages: list[PageCoverageStatus]
    forbidden_markers_found: list[str]
    has_continued_table_marker: bool
    differences_approved: bool = False

    @property
    def ok(self) -> bool:
        return (
            not self.missing_page_ids
            and self.registry_page_count == self.expected_page_count
            and not self.forbidden_markers_found
            and self.has_continued_table_marker
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ok"] = self.ok
        return payload


def load_expected_page_counts(path: Path | None = None) -> dict[str, int]:
    payload = json.loads((path or DEFAULT_EXPECTED).read_text(encoding="utf-8"))
    reports = payload.get("reports") or {}
    return {
        str(kind): int((meta or {}).get("page_responsibility_count") or 0)
        for kind, meta in reports.items()
    }


def _catalog_pages(report: str) -> list[tuple[str, str]]:
    registry = PageRegistry.load()
    kind = ReportKind(report)
    for catalog in registry.catalogs:
        if catalog.report != kind:
            continue
        return [(page.id, page.title_zh) for page in catalog.pages]
    raise KeyError(f"PageRegistry missing catalog for report {report}")


def project_pdf_coverage(
    *,
    report: str,
    text: str,
    bookmark_titles: list[str],
    expected_counts: dict[str, int] | None = None,
) -> PdfCoverageProjection:
    """Project PDF text/bookmarks onto PageRegistry responsibilities and diff."""
    report = report.upper()
    if report not in {"A", "B", "C"}:
        raise ValueError(f"unsupported report kind: {report}")

    counts = expected_counts or load_expected_page_counts()
    expected = int(counts.get(report) or 0)
    catalog = _catalog_pages(report)
    registry_ids = [page_id for page_id, _ in catalog]
    aliases = _BOOKMARK_ALIASES[report]
    bookmark_page_ids: set[str] = set()
    unexpected: list[str] = []
    for title in bookmark_titles:
        mapped = aliases.get(title)
        if mapped:
            bookmark_page_ids.add(mapped)
            continue
        if report == "C" and ("试验档案" in title or title.startswith("trial-")):
            bookmark_page_ids.add("trial-profile")
            continue
        unexpected.append(title)

    needles = _TEXT_NEEDLES[report]
    pages: list[PageCoverageStatus] = []
    covered: list[str] = []
    missing: list[str] = []
    for page_id, title_zh in catalog:
        evidence: list[str] = []
        reasons: list[str] = []
        page_needles = needles.get(page_id, ())
        text_hit = any(needle in text for needle in page_needles) if page_needles else False
        if page_id in bookmark_page_ids:
            evidence.append(f"bookmark:{page_id}")
        else:
            reasons.append("bookmark_not_found")
        if text_hit:
            evidence.append("text_needle")
        else:
            if page_needles:
                reasons.append("text_needle_not_found")
        is_covered = bool(evidence)
        if is_covered:
            covered.append(page_id)
        else:
            missing.append(page_id)
        pages.append(
            PageCoverageStatus(
                page_responsibility_id=page_id,
                title_zh=title_zh,
                covered=is_covered,
                evidence=evidence,
                missing_reasons=reasons,
            )
        )

    forbidden = [marker for marker in _FORBIDDEN_AUDIENCE_MARKERS if marker in text]
    return PdfCoverageProjection(
        report=report,
        expected_page_count=expected,
        registry_page_count=len(registry_ids),
        covered_page_ids=covered,
        missing_page_ids=missing,
        unexpected_bookmark_titles=unexpected,
        pages=pages,
        forbidden_markers_found=forbidden,
        has_continued_table_marker=("续表" in text),
        differences_approved=False,
    )


def coverage_defects(projection: PdfCoverageProjection) -> list[dict[str, Any]]:
    """Flatten projection gaps into verifier defect records (report-only)."""
    defects: list[dict[str, Any]] = []
    for page_id in projection.missing_page_ids:
        defects.append(
            {
                "id": f"COV-{projection.report}-MISSING-{page_id}",
                "severity": "high",
                "kind": "missing_page_responsibility",
                "message": f"PDF missing page responsibility `{page_id}`",
            }
        )
    if projection.registry_page_count != projection.expected_page_count:
        defects.append(
            {
                "id": f"COV-{projection.report}-COUNT",
                "severity": "high",
                "kind": "page_count_mismatch",
                "message": (
                    f"registry={projection.registry_page_count} "
                    f"expected={projection.expected_page_count}"
                ),
            }
        )
    if not projection.has_continued_table_marker:
        defects.append(
            {
                "id": f"COV-{projection.report}-CONTINUED",
                "severity": "medium",
                "kind": "missing_continued_table_marker",
                "message": "no searchable `续表` marker found",
            }
        )
    for marker in projection.forbidden_markers_found:
        defects.append(
            {
                "id": f"COV-{projection.report}-FORBIDDEN",
                "severity": "high",
                "kind": "forbidden_audience_marker",
                "message": f"found forbidden audience marker `{marker}`",
            }
        )
    return defects


__all__ = [
    "PageCoverageStatus",
    "PdfCoverageProjection",
    "coverage_defects",
    "load_expected_page_counts",
    "project_pdf_coverage",
]
