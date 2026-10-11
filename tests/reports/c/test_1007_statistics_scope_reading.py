"""1007V1：C 统计页覆盖率摘要 + 原生展开的完整字段与缺口。

ci-1007-c-statistics-reading-v1 / worker_01 有界执行 RED 家族：

- 统计页首屏只保留一行紧凑的"统计字段覆盖与复核边界"摘要：从既有
  ``statistics_scope`` 数组派生已提取/仅占位/未提取字段计数与逐研究缺口提示，
  并保留现有 Protocol/SAP 与出版分支的逐字闭合说明。
- 完整的字段标签、逐研究缺口字符串与未结构化提取的解释进入同一个原生
  ``<details>`` 展开块（键盘可达），文字不丢失、不断言来源闭合。
- 证据版本与局限页保留原样完整细则，不加折叠。
- 本文件只用生产渲染产物做只读结构核对；不是医学、浏览器或发布验收，
  也不代替 owner 的四宽度浏览器验收。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ci_workflow.domain.enums import (
    FactDisclosureState,
    FactReviewState,
)
from ci_workflow.renderers.portal import report_c
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    _render_page_context,
    render_report_c_site,
)
from tests.reports.c.test_1007_c2_presentation_veto_root import (
    _statistical_clone,
    _statistics_page,
)

ROOT = Path(__file__).resolve().parents[3]
REPORT_DATA = ROOT / "fixtures/positive/c-atopic-dermatitis/inputs/report-data.json"
STATISTICS_PAGE = "sample-analysis-statistics"
LIMITATIONS_PAGE = "evidence-limitations"

SUMMARY_MARKER = '<summary class="kz-c-statistics-scope__summary"'
DETAILS_MARKER = '<details class="kz-c-statistics-scope">'
FULLY_EXTRACTED_STATEMENT = "统计字段已提取。"


@pytest.fixture(scope="module")
def report() -> ReportCPortalData:
    return ReportCPortalData.model_validate_json(REPORT_DATA.read_bytes())


def _render_pages(data: ReportCPortalData, tmp_path: Path) -> dict[str, str]:
    site = tmp_path / "site"
    render_report_c_site(data, site, review_candidate=True)
    return {
        name: (site / f"{name}.html").read_text(encoding="utf-8")
        for name in (STATISTICS_PAGE, LIMITATIONS_PAGE)
    }


def _main(html: str) -> str:
    match = re.search(r"<main\b[^>]*>([\s\S]*)</main>", html)
    assert match is not None, "页面缺少 main 主体"
    return match.group(1)


def _section(html: str, aria_label: str) -> str:
    start = html.find(f'aria-label="{aria_label}"')
    assert start != -1, f"未找到区块：{aria_label}"
    end = html.find("</section>", start)
    assert end != -1, f"区块未闭合：{aria_label}"
    return html[start:end]


def _scope_section(html: str) -> str:
    return _section(_main(html), "统计资料")


def _scope_details(html: str) -> str:
    section = _scope_section(html)
    start = section.find(DETAILS_MARKER)
    assert start != -1, "统计覆盖边界缺少原生展开块"
    end = section.find("</details>", start)
    assert end != -1, "展开块未闭合"
    return section[start:end]


def _stats_scope(data: ReportCPortalData) -> dict:
    catalog, page = _statistics_page()
    return _render_page_context(data, page=page, catalog=catalog)["statistics_scope"]


def test_limitations_summary_does_not_reuse_nested_drawer_field_grid(
    report: ReportCPortalData, tmp_path: Path,
) -> None:
    html = _render_pages(report, tmp_path)[LIMITATIONS_PAGE]
    section = _section(_main(html), "来源资料")
    # A field grid is a label/value row, never the collection containing rows.
    assert '<dl class="kz-evidence-field">' not in section
    assert '<dl class="kz-c-evidence-summary">' in section
    for label in ("数据截止", "证据来源", "覆盖范围"):
        assert f"<dt>{label}</dt>" in section
    assert section.count('<div class="kz-evidence-field">') == 3


# ─── 紧凑首屏摘要 ───────────────────────────────────────────────────────────


def test_statistics_page_leads_with_compact_visible_coverage_summary(
    report: ReportCPortalData, tmp_path: Path,
) -> None:
    html = _render_pages(report, tmp_path)[STATISTICS_PAGE]
    section = _scope_section(html)
    summary_index = section.find(SUMMARY_MARKER)
    assert summary_index != -1
    assert summary_index > section.find(DETAILS_MARKER)
    assert section.find("<h3") == -1  # 紧凑区块不再插入子标题
    summary = section[summary_index:section.find("</summary>", summary_index)]

    scope = _stats_scope(report)
    extracted = len(scope["extracted_fields"])
    placeholder = len(scope["placeholder_fields"])
    unextracted = len(scope["unextracted_fields"])
    assert (extracted, placeholder, unextracted) == (1, 1, 12)
    extracted_count = "1 个有当前值"
    placeholder_count = "暂无当前值"
    unextracted_count = "12 个待提取"
    assert extracted_count in summary
    assert placeholder_count in _scope_details(html)
    assert unextracted_count in summary
    assert "不等于" not in summary
    assert "字段与来源" in summary


def test_visible_summary_keeps_exact_closure_strings_and_full_lists_stay_reachable_in_details(
    report: ReportCPortalData, tmp_path: Path,
) -> None:
    html = _render_pages(report, tmp_path)[STATISTICS_PAGE]
    section = _scope_section(html)
    details = _scope_details(html)
    visible = section[:section.find(DETAILS_MARKER)]
    scope = _stats_scope(report)

    # 逐字闭合说明仍在首屏可见（只出现一次，不在展开块里重复）。
    assert scope["protocol_closure_zh"] in details
    assert scope["publication_closure_zh"] in details
    assert "不等于完整统计分析复核" not in section
    for closure in (scope["protocol_closure_zh"], scope["publication_closure_zh"]):
        assert closure not in visible

    # 完整字段标签与缺口字符串只保留在展开块中，且逐条可达。
    for label in scope["extracted_field_labels"]:
        assert label in details
        assert label not in visible
    for label in scope["placeholder_field_labels"]:
        assert label in details
    for label in scope["unextracted_field_labels"]:
        assert label in details
    assert scope["unextracted_field_labels"][0] in details
    assert "终点、定义与时间点" in details
    assert 'data-scope-field-list="unextracted"' in details
    # details 内容完整承载缺口项，字段清单非空。
    for inner in re.findall(
        r'data-scope-field-list="(?:placeholder|unextracted)">([^<]*)<', details
    ):
        assert inner.strip()


def test_statistics_page_first_screen_facts_and_source_links_stay_reachable(
    report: ReportCPortalData, tmp_path: Path,
) -> None:
    pages = _render_pages(report, tmp_path)
    html = pages[STATISTICS_PAGE]
    # 首屏摘要不遮挡数据事实与来源入口：完整表、筛选与页末外链仍在。
    assert 'id="kz-chart-module"' in html
    assert 'id="external-sources"' in html
    assert "终点、定义与时间点" in html
    # 完整表仍承载样本量数据事实。
    assert "740" in html


# ─── 占位与用户清除不得计入已提取 ───────────────────────────────────────────


def test_missing_and_user_cleared_fields_are_never_counted_as_extracted(
    report: ReportCPortalData, tmp_path: Path,
) -> None:
    def cleared(item):
        return item.model_copy(update={
            "threshold_value": None,
            "disclosure_state": FactDisclosureState.USER_CLEARED,
            "review_state": FactReviewState.USER_MODIFIED,
            "display_text": "用户清除：原登记样本量待重新核实",
        })

    data = report.model_copy(update={"observations": tuple(
        cleared(item) if item.field == "planned_or_actual_sample_size" else item
        for item in report.observations
    )})
    scope = _stats_scope(data)
    assert scope["extracted_fields"] == ()
    assert "planned_or_actual_sample_size" in scope["placeholder_fields"]

    html = _render_pages(data, tmp_path)[STATISTICS_PAGE]
    summary = _scope_section(html)
    assert "0 个有当前值" in summary
    details = _scope_details(html)
    assert "暂无当前值" in details
    assert "用户清除" not in "\n".join(
        line for line in details.splitlines() if "已结构化提取且当前有可核实数据" in line
    )


# ─── 空/满覆盖边界 ──────────────────────────────────────────────────────────


def test_full_coverage_states_extraction_without_dropping_expandable_completeness(
    report: ReportCPortalData, tmp_path: Path,
) -> None:
    declared = report_c._PAGE_FIELDS[STATISTICS_PAGE] or ()
    seed = next(
        item for item in report.observations
        if item.field == "planned_or_actual_sample_size"
    )
    full = report.model_copy(update={"observations": (
        *(item for item in report.observations if item.field not in declared),
        *(
            _statistical_clone(seed, field, state=FactDisclosureState.REPORTED_VALUE)
            for field in sorted(declared)
        ),
    )})
    scope = _stats_scope(full)
    assert set(scope["extracted_fields"]) == set(declared)
    assert scope["placeholder_fields"] == ()
    assert scope["unextracted_fields"] == ()
    assert scope["per_trial_gap_zh"]

    html = _render_pages(full, tmp_path)[STATISTICS_PAGE]
    section = _scope_section(html)
    summary_head = section[: section.find(DETAILS_MARKER)]
    assert "0 个待提取" in section
    assert "尚未结构化提取或尚未审阅" not in summary_head
    details = _scope_details(html)
    assert FULLY_EXTRACTED_STATEMENT in details
    assert "计划或实际样本量" in details


def test_per_study_gaps_stay_truthfully_expandable(
    report: ReportCPortalData, tmp_path: Path,
) -> None:
    seed = next(
        item for item in report.observations
        if item.field == "planned_or_actual_sample_size"
    )
    other = next(
        item for item in report.observations
        if item.field == "planned_or_actual_sample_size" and item.row_id != seed.row_id
    )
    single = report.model_copy(update={"observations": tuple(
        item for item in report.observations if item.row_id != other.row_id
    )})
    scope = _stats_scope(single)
    assert scope["per_trial_gap_zh"]
    gap = scope["per_trial_gap_zh"][0]
    assert other.trial_id.upper() in gap

    html = _render_pages(single, tmp_path)[STATISTICS_PAGE]
    details = _scope_details(html)
    assert "逐研究缺口" in details
    assert f"逐研究缺口（下列已提取字段在该试验暂无当前可核实数据）：{gap}" in details


# ─── 证据版本与局限页保留完整细则 ───────────────────────────────────────────


def test_evidence_limitations_page_keeps_complete_scope_detail_inline(
    report: ReportCPortalData, tmp_path: Path,
) -> None:
    html = _render_pages(report, tmp_path)[LIMITATIONS_PAGE]
    scope = _stats_scope(report)
    for label in (
        *scope["extracted_field_labels"],
        *scope["placeholder_field_labels"],
        *scope["unextracted_field_labels"],
    ):
        assert label in html
    assert DETAILS_MARKER not in html  # 局限页保持原样，不引入折叠
    assert scope["protocol_closure_zh"] in html
    assert scope["publication_closure_zh"] in html


def test_full_statistical_explanation_is_reachable_without_preceding_the_data(
    report: ReportCPortalData, tmp_path: Path,
) -> None:
    section = _scope_section(_render_pages(report, tmp_path)[STATISTICS_PAGE])
    visible = section[:section.find(DETAILS_MARKER)]
    details = _scope_details(_render_pages(report, tmp_path / "second")[STATISTICS_PAGE])
    explanation = "分析集、比较方法、效应量、估计目标与伴发事件策略、缺失数据与敏感性"
    assert explanation not in visible, "完整方法词表不应挤在比较数据前面"
    assert explanation not in details
    assert "不等于完整" not in section
    assert "Protocol/SAP" in details


def test_each_complete_field_list_has_one_owner_not_duplicate_paragraph_and_list(
    report: ReportCPortalData, tmp_path: Path,
) -> None:
    details = _scope_details(_render_pages(report, tmp_path)[STATISTICS_PAGE])
    scope = _stats_scope(report)
    for key in ("extracted_field_labels", "placeholder_field_labels", "unextracted_field_labels"):
        joined = "、".join(scope[key])
        assert joined
        assert details.count(joined) == 1, f"{key}完整清单不得机械重复"


def test_native_statistics_summary_retains_visible_disclosure_marker() -> None:
    css = (ROOT / "src/ci_workflow/renderers/portal/assets/report-c.css").read_text()
    selector = ".kz-c-statistics-scope > .kz-c-statistics-scope__summary {"
    declaration = css.split(selector, 1)[1].split("}", 1)[0]
    assert "display: list-item" in declaration, "原生summary箭头不应被flex移除"
