"""1007V1：C2 科学呈现否决的单一根因家族（ci-1007-c2-report-presentation-veto-v1 / worker_01）。

真实 C2 复核（veto，3 阻断 + 1 非阻断）指向同一呈现根：报告把"已核实的事实"
呈现为更弱或错误的科学断言。本文件只用生产投影 → 报告渲染 → 证据视图/页面
产物做只读结构核对：

- 实际入组限定（``enrollmentInfo.type=ACTUAL``）必须与原始计数、例单位一起
  可见于读图/完整表/横比/数据依据；数值同轴仍为数值；不得由计数、数组顺序
  或分组分母推断类型，用户修订/清除也不得把原始计数当作当前值。
- 未结构化提取（量表/阈值等类型化字段缺失）不得宣称为"来源未列示"；来源缺失、
  不适用与用户清除仍保持各自状态；逐字原文与精确 locator 保留。
- 统计页与局限页必须如实披露未结构化/未审阅的统计扩展范围、Protocol/SAP 正文
  未纳入与出版分支未闭合，且不得把"未提取"写成"来源未公开"。
- 中文译述不得标作"登记原文，未译"；真正未译的登记英文仍须标注且可达。

本文件不是医学、浏览器或发布验收；真实 C2 产物与最终 C3 复核仍由 owner 负责。
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState, ReportKind
from ci_workflow.gates.models import SourceRole
from ci_workflow.renderers.portal import report_c
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    _evidence_view,
    _render_page_context,
    design_comparison_workspace,
    render_report_c_site,
)
from ci_workflow.reports.c import DesignFieldFamily
from ci_workflow.reports.common.evidence_view import (
    EVIDENCE_FIELD_STATE_LABELS_ZH,
    EvidenceFieldState,
)
from ci_workflow.reports.common.page_registry import PageRegistry
from tests.integration.test_r24_c_candidate_materialization import _raw
from tests.integration.test_r24_ctgov_c_design_projection import _CAS_ROOT, _full_bindings
from tools.materialize_ctgov_c_candidate import materialize, render_review_preview

_OBSERVED = datetime(2026, 10, 3, tzinfo=UTC)
_STATISTICS_PAGE = "sample-analysis-statistics"
_ABSENT_CLAIM = "来源未列示"
_TRANSLATED_MARK = "中文译述"


@pytest.fixture(scope="module")
def pnh_report(tmp_path_factory) -> ReportCPortalData:
    """真实 CT.gov 捕获 → 生产原子投影 → 门户数据（ACTUAL 入组类型来自登记来源）。"""
    output = tmp_path_factory.mktemp("c2-veto-root") / "candidate"
    materialize(
        source_root=_CAS_ROOT, raw_asset=_raw(), output=output,
        bindings=_full_bindings(), indication_id="pnh",
        indication="阵发性睡眠性血红蛋白尿症", cutoff="2026-09-26",
        observed_at=_OBSERVED,
    )
    render_review_preview(output, rendered_at=_OBSERVED)
    return ReportCPortalData.model_validate_json(
        (output / "review-portal-data.json").read_bytes()
    )


def _sample_sizes(report: ReportCPortalData):
    return tuple(item for item in report.observations
                 if item.field == "planned_or_actual_sample_size")


def _endpoint_definition(report: ReportCPortalData):
    return next(item for item in report.observations
                if item.field == "primary_endpoint_definition")


@pytest.mark.parametrize("has_dosing", [True, False])
def test_unprojected_timeline_never_claims_registry_absence(
    pnh_report: ReportCPortalData, tmp_path: Path, has_dosing: bool,
) -> None:
    observations = tuple(
        item.model_copy(update={"assessment_timepoint": None})
        if item.field == "dosing_regimen" else item
        for item in pnh_report.observations
        if item.field != "visit_schedule" and (has_dosing or item.field != "dosing_regimen")
    )
    data = pnh_report.model_copy(update={"observations": observations})
    catalog = PageRegistry.load().catalog(ReportKind.C)
    page = next(item for item in catalog.pages if item.id == "visit-duration-followup")
    context = _render_page_context(data, page=page, catalog=catalog)
    assert context["visit_insufficient"] is True
    assert context["chart_groups_json"] == "[]"  # no invented time axis
    site = tmp_path / "timeline"
    render_report_c_site(data, site, review_candidate=True)
    html = (site / "visit-duration-followup.html").read_text(encoding="utf-8")
    assert "尚未完成结构化提取或复核" in html
    assert "未结构化提取不等于来源未公开" in html
    assert "绑定登记来源未公开本组试验" not in html
    assert 'href="treatment-arms.html"' in html
    assert 'href="endpoint-timepoint-matrix.html"' in html
    # Raw treatment/endpoint windows stay in their own existing evidence surfaces.
    if has_dosing:
        dose = next(item for item in observations if item.field == "dosing_regimen")
        assert dose.source_text[:60] in (site / "treatment-arms.html").read_text()


# ─── 根 1：实际入组限定与原始计数/例单位一起可见 ─────────────────────────────


def test_verified_actual_enrollment_type_is_not_dropped_from_any_reader_surface(
    pnh_report: ReportCPortalData,
) -> None:
    samples = _sample_sizes(pnh_report)
    assert samples, "生产投影未产生样本量观察"
    for observation in samples:
        # 前提：限定文本由已核实登记类型投影而来，不是本测试构造的字符串。
        assert "ACTUAL" in (observation.display_text or "")
        assert observation.threshold_unit == "例"

        chart = report_c._chart_row(pnh_report, observation, chart_type="bubble")
        # 数值同轴仍是数值：限定文本不得替换数值投影。
        assert chart["numeric_value"] == float(observation.threshold_value)
        assert chart["numeric_projection"]["plot_value"] == float(observation.threshold_value)
        assert chart["unit"] == "例"
        assert "实际入组" in str(chart["value"])
        assert str(observation.threshold_value) in str(chart["value"])
        assert "计划入组" not in str(chart["value"])

        table = report_c._table_rows(
            pnh_report, (observation,), page_id=_STATISTICS_PAGE
        )[0]
        assert "实际入组" in str(table["value"])
        assert table["unit"] == "例"
        # 计数来源是数值事实：不得被标成条款翻译（"中文译述"只用于文字原文）。
        assert "（中文译述" not in str(table["value"])

        workspace = design_comparison_workspace(pnh_report, (observation,))
        summaries = [
            item["summary"]
            for column in workspace["columns"] for cell in column["cells"]
            for item in cell["items"] if item["row_id"] == observation.row_id
        ]
        assert summaries and all("实际入组" in summary for summary in summaries)

        view = _evidence_view(pnh_report, observation, page_id=_STATISTICS_PAGE)
        assert "实际入组" in str(view.value.value)
        assert view.unit.value == "例"
        assert view.original_text == observation.source_text
        assert view.source_trace_state == "located"


def test_enrollment_qualifier_is_never_inferred_from_count_order_or_denominator(
    pnh_report: ReportCPortalData,
) -> None:
    observation = _sample_sizes(pnh_report)[0]
    unqualified = observation.model_copy(update={"display_text": None})
    chart = report_c._chart_row(pnh_report, unqualified, chart_type="status_matrix")
    # 来源没有给出类型限定：只呈现可核实计数，不凭计数或位置补出"实际/计划"。
    assert chart["value"] == int(float(observation.threshold_value))
    assert "入组" not in str(chart["value"])

    estimated = observation.model_copy(update={
        "display_text": "计划入组：9例（登记类型 ESTIMATED）",
    })
    estimated_chart = report_c._chart_row(pnh_report, estimated, chart_type="status_matrix")
    # 透传来源限定：不把已核实类型硬编码成 ACTUAL。
    assert "计划入组" in str(estimated_chart["value"])
    assert "实际入组" not in str(estimated_chart["value"])
    assert estimated_chart["numeric_value"] == float(observation.threshold_value)


def test_cleared_or_edited_sample_size_never_shows_the_original_count_as_current(
    pnh_report: ReportCPortalData,
) -> None:
    observation = _sample_sizes(pnh_report)[0]
    cleared = observation.model_copy(update={
        "disclosure_state": FactDisclosureState.USER_CLEARED,
        "review_state": FactReviewState.USER_MODIFIED,
        "display_text": "用户清除：原登记样本量待重新核实",
    })
    chart = report_c._chart_row(pnh_report, cleared, chart_type="bubble")
    assert chart["value"] is None
    assert "实际入组" not in str(chart["status"])
    assert chart["source_text"] == observation.source_text  # 原始来源不被擦除
    view = _evidence_view(pnh_report, cleared, page_id=_STATISTICS_PAGE)
    assert "实际入组" not in str(view.value.value)
    assert view.original_text == observation.source_text
    assert view.source_trace_state == "located"


# ─── 根 2：未结构化提取 ≠ 来源缺失 ─────────────────────────────────────────


def test_missing_typed_scale_and_threshold_do_not_claim_source_absence(
    pnh_report: ReportCPortalData,
) -> None:
    observation = _endpoint_definition(pnh_report)
    assert observation.disclosure_state is FactDisclosureState.REPORTED_VALUE
    assert observation.scale is None and observation.threshold_value is None
    assert observation.source_text.strip()

    view = _evidence_view(pnh_report, observation, page_id=_STATISTICS_PAGE)
    for field in (view.scale, view.threshold, view.unit):
        assert field.value is None
        assert field.state is EvidenceFieldState.NOT_EXTRACTED
    # 原文、定位与来源追溯仍逐字保留，读者可自行核对量表和阈值。
    assert view.original_text == observation.source_text
    assert view.source_trace_state == "located"
    assert "结构化" in str(view.explanation.value)
    # 共同模型/共用抽屉标签必须显式说"未结构化提取"，不得读成技术故障或来源缺失。
    assert EVIDENCE_FIELD_STATE_LABELS_ZH[EvidenceFieldState.NOT_EXTRACTED] == "未结构化提取"
    assert (
        EVIDENCE_FIELD_STATE_LABELS_ZH[EvidenceFieldState.NOT_EXTRACTED]
        != EVIDENCE_FIELD_STATE_LABELS_ZH[EvidenceFieldState.TECHNICALLY_UNAVAILABLE]
    )
    assert EVIDENCE_FIELD_STATE_LABELS_ZH[EvidenceFieldState.NOT_EXTRACTED] != _ABSENT_CLAIM


def test_extraction_gap_labels_reach_table_and_workspace_without_absence_claim(
    pnh_report: ReportCPortalData,
) -> None:
    """生产反例：提取缺口在表格与设计横比呈现层同样不得冒充"不适用/未列示"。"""
    observation = _endpoint_definition(pnh_report)
    table = report_c._table_rows(pnh_report, (observation,), page_id="trial-detail")[0]
    assert table["scale"] == "未结构化提取"
    workspace_item = next(
        item for column in design_comparison_workspace(pnh_report, (observation,))["columns"]
        for cell in column["cells"] for item in cell["items"]
        if item["row_id"] == observation.row_id
    )
    assert workspace_item["scale"] == "未结构化提取"
    # 计数等无量表对象的字段仍按"不适用"，不回退成提取缺口。
    sample = _sample_sizes(pnh_report)[0]
    assert report_c._table_rows(
        pnh_report, (sample,), page_id="trial-detail"
    )[0]["scale"] == "不适用"


@pytest.mark.parametrize(("state", "expected"), [
    (FactDisclosureState.NOT_REPORTED, EvidenceFieldState.SOURCE_NOT_LISTED),
    (FactDisclosureState.NOT_APPLICABLE, EvidenceFieldState.NOT_APPLICABLE),
    (FactDisclosureState.USER_CLEARED, EvidenceFieldState.USER_CLEARED),
])
def test_genuine_absence_not_applicable_and_user_cleared_states_are_preserved(
    pnh_report: ReportCPortalData, state: FactDisclosureState,
    expected: EvidenceFieldState,
) -> None:
    observation = _endpoint_definition(pnh_report).model_copy(
        update={"disclosure_state": state}
    )
    view = _evidence_view(pnh_report, observation, page_id=_STATISTICS_PAGE)
    assert view.scale.state is expected


# ─── 根 3：统计扩展范围与文档闭合如实披露 ───────────────────────────────────


def _statistics_page():
    catalog = PageRegistry.load().catalog(ReportKind.C)
    return catalog, next(page for page in catalog.pages if page.id == _STATISTICS_PAGE)


def _statistical_clone(seed, field: str, *, state: FactDisclosureState):
    return seed.model_copy(update={
        "row_id": f"c2-root-{field}",
        "observation_id": f"c2-root-{field}",
        "source_row_id": f"c2-root-{field}",
        "field": field,
        "field_family": DesignFieldFamily.STATISTICAL,
        "source_field_name": field,
        "source_text": "各主要终点按预先规定的比较方法分析。",
        "display_text": None,
        "threshold_value": None,
        "threshold_unit": None,
        "scale": None,
        "disclosure_state": state,
    })


def test_statistics_scope_distinguishes_current_data_placeholder_and_unextracted(
    pnh_report: ReportCPortalData,
) -> None:
    catalog, page = _statistics_page()
    declared = report_c._PAGE_FIELDS[_STATISTICS_PAGE]
    context = _render_page_context(pnh_report, page=page, catalog=catalog)
    scope = context["statistics_scope"]
    assert set(scope["declared_fields"]) == set(declared)
    # 生产数据中样本量是唯一有当前可核实数据的统计字段，且两试验都有值。
    assert set(scope["extracted_fields"]) == {"planned_or_actual_sample_size"}
    assert scope["per_trial_gap_zh"] == ()
    assert "分析集" in scope["unextracted_field_labels"]
    assert "效应量" in scope["unextracted_field_labels"]

    # 生产反例：只有占位状态（未报告）的字段不算已提取覆盖。
    sample = _sample_sizes(pnh_report)[0]
    placeholder = _statistical_clone(
        sample, "analysis_sets", state=FactDisclosureState.NOT_REPORTED,
    )
    with_placeholder = pnh_report.model_copy(
        update={"observations": (*pnh_report.observations, placeholder)}
    )
    placeholder_scope = _render_page_context(
        with_placeholder, page=page, catalog=catalog
    )["statistics_scope"]
    assert "analysis_sets" in placeholder_scope["placeholder_fields"]
    assert "analysis_sets" not in placeholder_scope["extracted_fields"]
    assert "analysis_sets" not in placeholder_scope["unextracted_fields"]
    assert "分析集" in placeholder_scope["placeholder_field_labels"]

    # 数据驱动而非硬编码：补上一条已报告统计观察后，它进入已提取并退出未提取。
    statistical = _statistical_clone(
        sample, "comparison_logic", state=FactDisclosureState.REPORTED_VALUE,
    )
    extended = pnh_report.model_copy(
        update={"observations": (*pnh_report.observations, statistical)}
    )
    extended_scope = _render_page_context(extended, page=page, catalog=catalog)["statistics_scope"]
    assert "comparison_logic" in extended_scope["extracted_fields"]
    assert "comparison_logic" not in extended_scope["unextracted_fields"]

    # 逐研究缺口只在材料性存在时列出：只剩一项试验有时，另一项被如实列出。
    other = next(
        item for item in _sample_sizes(pnh_report)
        if item.row_id != sample.row_id
    )
    single_trial = pnh_report.model_copy(update={"observations": tuple(
        item for item in pnh_report.observations if item.row_id != other.row_id
    )})
    gap_scope = _render_page_context(single_trial, page=page, catalog=catalog)["statistics_scope"]
    assert gap_scope["per_trial_gap_zh"]
    assert "样本量" in gap_scope["per_trial_gap_zh"][0]
    assert other.trial_id.upper() in gap_scope["per_trial_gap_zh"][0]


def test_statistics_document_closure_is_computed_from_bound_source_roles(
    pnh_report: ReportCPortalData,
) -> None:
    catalog, page = _statistics_page()
    scope = _render_page_context(pnh_report, page=page, catalog=catalog)["statistics_scope"]
    # 只绑定登记来源：不得声称已纳入 Protocol/SAP 正文，也不得声称出版分支闭合。
    assert "未绑定研究方案与统计分析计划" in scope["protocol_closure_zh"]
    assert "未绑定出版或会议披露来源" in scope["publication_closure_zh"]

    # 生产反例：绑定条款级 Protocol/SAP 事实后按事实计数声明，而不是硬编码结论。
    seed = _sample_sizes(pnh_report)[0]
    protocol = seed.model_copy(update={
        "row_id": "c2-root-protocol-clause",
        "observation_id": "c2-root-protocol-clause",
        "source_row_id": "c2-root-protocol-clause",
        "source_role": SourceRole.PROTOCOL_SAP,
    })
    bound = pnh_report.model_copy(
        update={"observations": (*pnh_report.observations, protocol)}
    )
    bound_scope = _render_page_context(bound, page=page, catalog=catalog)["statistics_scope"]
    assert "条款级事实 1 条" in bound_scope["protocol_closure_zh"]
    assert "不能证明全文是否已纳入" in bound_scope["protocol_closure_zh"]

    publication = seed.model_copy(update={
        "row_id": "c2-root-primary-report",
        "observation_id": "c2-root-primary-report",
        "source_row_id": "c2-root-primary-report",
        "source_role": SourceRole.PRIMARY_TRIAL_REPORT,
    })
    published = pnh_report.model_copy(
        update={"observations": (*pnh_report.observations, publication)}
    )
    published_scope = _render_page_context(
        published, page=page, catalog=catalog
    )["statistics_scope"]
    # 主要试验报告不等于出版检索闭合：只作有界计数声明。
    assert "条款级事实 1 条" in published_scope["publication_closure_zh"]
    assert "不构成完整出版检索" in published_scope["publication_closure_zh"]


def test_statistics_and_limitations_pages_disclose_review_and_document_closure(
    pnh_report: ReportCPortalData, tmp_path: Path,
) -> None:
    site = tmp_path / "c2-root"
    render_report_c_site(pnh_report, site, review_candidate=True)
    statistics = (site / f"{_STATISTICS_PAGE}.html").read_text(encoding="utf-8")
    limitations = (site / "evidence-limitations.html").read_text(encoding="utf-8")
    for html in (statistics, limitations):
        assert "尚未结构化提取" in html
        assert "不等于完整" in html or "不构成完整" in html
        assert "Protocol/SAP" in html
        assert "未结构化提取不等于来源未公开" in html
        # 不得把未提取写成来源未公开，也不得输出内部 gate 诊断词。
        assert "extension_missing" not in html
        assert "core_satisfied" not in html
    assert "出版" in limitations
    # 登记统计语境必须真的可达：统计页指向承载终点定义说明的既有页面。
    assert "（登记原文，未译）" not in statistics
    assert re.search(r'href="[^"]*endpoint-timepoint-matrix\.html"', statistics)
    assert (site / "endpoint-timepoint-matrix.html").exists()


def test_endpoint_definition_prose_containing_statistical_context_stays_reachable(
    pnh_report: ReportCPortalData, tmp_path: Path,
) -> None:
    """生产反例：统计页不能只说"见下表"——承载统计语境的终点说明另有其页。"""
    site = tmp_path / "c2-root-prose"
    render_report_c_site(pnh_report, site, review_candidate=True)
    description_rows = [
        observation for observation in pnh_report.observations
        if observation.field.endswith("_endpoint_description")
    ]
    assert description_rows, "生产投影未产生终点说明观察"
    endpoint_page = (site / "endpoint-timepoint-matrix.html").read_text(encoding="utf-8")
    statistics_page = (site / f"{_STATISTICS_PAGE}.html").read_text(encoding="utf-8")
    # 终点说明的逐字原文与来源定位留在其页面/数据依据中；统计页只做入口，不复制卡片。
    sample = description_rows[0]
    assert sample.source_text[:60] in endpoint_page
    assert sample.source_text[:60] not in statistics_page
    assert "终点、定义与时间点" in statistics_page


def test_stale_or_edited_display_text_never_becomes_the_current_qualified_read(
    pnh_report: ReportCPortalData,
) -> None:
    """生产反例：过期的限定文本不得冒充当前计数，当前值仍来自可核实计数。"""
    observation = _sample_sizes(pnh_report)[0]
    assert observation.display_text and "实际入组" in observation.display_text
    stale = observation.model_copy(update={"threshold_value": "160", "source_text": "160"})
    chart = report_c._chart_row(pnh_report, stale, chart_type="bubble")
    assert chart["numeric_value"] == 160.0
    assert chart["value"] == 160
    assert "151" not in str(chart["value"])
    assert chart["source_text"] == "160"
    view = _evidence_view(pnh_report, stale, page_id=_STATISTICS_PAGE)
    assert view.original_text == "160"
    # 计数分隔符容差：1,234 例仍与当前计数一致，限定保留。
    comma = observation.model_copy(update={
        "threshold_value": "1234",
        "source_text": "1234",
        "display_text": "实际入组：1,234例（登记类型 ACTUAL）",
    })
    assert "实际入组" in str(
        report_c._chart_row(pnh_report, comma, chart_type="status_matrix")["value"]
    )
    assert report_c._chart_row(pnh_report, comma, chart_type="status_matrix")["value"] == (
        "实际入组：1,234例（登记类型 ACTUAL）"
    )


# ─── 根 4：中文译述与登记英文原文的来源标注 ─────────────────────────────────


def test_chinese_translation_is_not_labeled_as_untranslated_source(
    pnh_report: ReportCPortalData,
) -> None:
    observation = _endpoint_definition(pnh_report)
    translated = observation.model_copy(update={
        "display_text": "在基线至第24周期间，最严重瘙痒数字评价量表（WI-NRS）"
                        "评分改善幅度达到4分或以上的受试者比例",
    })
    row = report_c._table_rows(pnh_report, (translated,), page_id="overview")[0]
    assert "未译" not in str(row["value"])
    assert _TRANSLATED_MARK in str(row["value"])
    assert "完整定义原文" not in str(row["value"])
    # 英文登记原文仍在数据依据中可达，且定位未改写。
    view = _evidence_view(pnh_report, translated, page_id="overview")
    assert view.original_text == observation.source_text
    assert view.source_trace_state == "located"


def test_genuinely_untranslated_english_still_reaches_readers_with_its_marker(
    pnh_report: ReportCPortalData,
) -> None:
    observation = _endpoint_definition(pnh_report).model_copy(update={"display_text": None})
    row = report_c._table_rows(pnh_report, (observation,), page_id="overview")[0]
    assert "（登记原文，未译）" in str(row["value"])
    assert observation.source_text in str(row["value"])


def test_english_display_projection_is_not_labeled_as_the_registry_original(
    pnh_report: ReportCPortalData,
) -> None:
    """生产反例：英文展示文本与登记原文不同，不得冒充"登记原文，未译"。"""
    observation = _endpoint_definition(pnh_report)
    projected = observation.model_copy(update={
        "display_text": "Proportion of participants with a documented improvement of at "
                        "least two points at the primary timepoint",
    })
    assert projected.display_text != observation.source_text
    row = report_c._table_rows(pnh_report, (projected,), page_id="overview")[0]
    assert "（登记原文，未译）" not in str(row["value"])
    assert "非登记原文" in str(row["value"])
    assert "登记原文见数据依据" in str(row["value"])
    # 逐字登记英文原文仍完整保留在数据依据中，且定位未改写。
    view = _evidence_view(pnh_report, projected, page_id="overview")
    assert view.original_text == observation.source_text
    assert view.source_trace_state == "located"


def test_endpoint_definition_description_label_stops_claiming_registry_original(
    pnh_report: ReportCPortalData,
) -> None:
    assert "原文" not in report_c._field_label("primary_endpoint_description")
    assert "原文" not in report_c._field_label("secondary_endpoint_description")


def test_evidence_drawer_labels_keep_one_explicit_state_per_missing_field(
    pnh_report: ReportCPortalData,
) -> None:
    observation = _endpoint_definition(pnh_report)
    view = _evidence_view(pnh_report, observation, page_id=_STATISTICS_PAGE)
    for field in (view.scale, view.threshold, view.unit, view.value):
        assert (field.value is None) != (field.state is None)
    workspace = design_comparison_workspace(pnh_report, (observation,))
    item = next(
        item for column in workspace["columns"] for cell in column["cells"]
        for item in cell["items"] if item["row_id"] == observation.row_id
    )
    # 呈现层如实标注提取缺口；原始观察不被改写。
    assert item["scale"] == "未结构化提取"
    assert observation.scale is None
    assert item["threshold_value"] is None and item["threshold_unit"] is None


def test_shared_extraction_state_is_a_missing_field_not_an_a_consumer_crash() -> None:
    from ci_workflow.reports.a.analysis import _missing_state_reason
    from ci_workflow.reports.common.evidence_view import EvidenceField

    reason = _missing_state_reason("靶点", EvidenceField(state=EvidenceFieldState.NOT_EXTRACTED))
    assert "未结构化提取" in reason
    assert "完整证据" in reason


def test_all_placeholder_statistics_do_not_claim_all_extensions_are_extracted(
    pnh_report: ReportCPortalData, tmp_path: Path,
) -> None:
    sample = _sample_sizes(pnh_report)[0]
    fields = report_c._PAGE_FIELDS[_STATISTICS_PAGE] or ()
    placeholder_report = pnh_report.model_copy(update={"observations": (
        *(item for item in pnh_report.observations if item.field not in fields),
        *(_statistical_clone(sample, field, state=FactDisclosureState.NOT_REPORTED)
          for field in sorted(fields)),
    )})
    site = tmp_path / "all-placeholder"
    render_report_c_site(placeholder_report, site, review_candidate=True)
    limitations = (site / "evidence-limitations.html").read_text(encoding="utf-8")
    assert "仅有占位状态" in limitations
    assert "统计扩展字段均已结构化提取" not in limitations
