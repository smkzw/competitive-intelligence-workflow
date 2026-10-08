"""1007V1：C 类当前读法以状态为先，清除/修订行不得回填原始来源值。

有界执行 RED 家族（ci-1007-c-cleared-reading-v1 / worker_01）：

- 用户清除（USER_CLEARED）的样本量行：``_numeric_for`` 不得再从 source_text
  回填旧数值，``_value_text``、矩阵首层条目、完整表与证据视图的当前值只能
  来自显式当前投影（display_text）或状态标签；原始 source_text 与来源定位
  仍逐字保留在来源字段与证据抽屉。
- 用户修订/清除（USER_MODIFIED）的入排标准带多段原始原文时，矩阵与完整表
  不得把原始多段文本拆成"当前"摘要；未修订的多段原文仍逐条拆分。
- 真实已报告零值、未修订样本量与未报告行保持原行为，不清除、不转状态。
- 本文件只调用生产函数做只读结构核对；不是医学、浏览器或发布验收。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.renderers.portal import report_c
from ci_workflow.renderers.portal.active_fact_projection import ActiveFact, ActiveFactRevision
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    design_comparison_workspace,
)

ROOT = Path(__file__).resolve().parents[3]
REPORT_DATA = ROOT / "fixtures/positive/c-atopic-dermatitis/inputs/report-data.json"

SAMPLE_ROW_ID = "c-nct02260986-sample-size"
CRITERION_ROW_ID = "c-nct04178967-inclusion"

MULTI_CRITERION_SOURCE = (
    "Inclusion Criteria:\n"
    "1. EASI score >=16 at the baseline visit\n"
    "2. Chronic atopic dermatitis for at least 3 years\n"
    "3. Age 18 years or older"
)
MULTI_CRITERION_PARTS = (
    "EASI score ≥16 at the baseline visit",
    "Chronic atopic dermatitis for at least 3 years",
    "Age 18 years or older",
)

CLEARED_SAMPLE_TEXT = "用户清除：原登记样本量待重新核实"
CLEARED_ZERO_TEXT = "用户清除：原登记零值待重新核实"
EDITED_CRITERION_TEXT = "入选标准：EASI 评分 ≥12（用户修订，待复核）"
CLEARED_CRITERION_TEXT = "入选标准：用户清除，待重新核实。"


@pytest.fixture(scope="module")
def report() -> ReportCPortalData:
    return ReportCPortalData.model_validate_json(REPORT_DATA.read_bytes())


def _observation(report: ReportCPortalData, row_id: str):
    return next(item for item in report.observations if item.row_id == row_id)


def _cleared_sample_size(report: ReportCPortalData):
    original = _observation(report, SAMPLE_ROW_ID)
    return original.model_copy(
        update={
            "threshold_value": None,
            "disclosure_state": FactDisclosureState.USER_CLEARED,
            "review_state": FactReviewState.USER_MODIFIED,
            "display_text": CLEARED_SAMPLE_TEXT,
        }
    )


def _matrix_items(report: ReportCPortalData, observation) -> tuple[dict[str, Any], ...]:
    workspace = design_comparison_workspace(report, (observation,))
    return tuple(
        item
        for column in workspace["columns"]
        for cell in column["cells"]
        for item in cell["items"]
        if item["row_id"] == observation.row_id
    )


def test_cleared_sample_size_does_not_revive_source_value(
    report: ReportCPortalData,
) -> None:
    cleared = _cleared_sample_size(report)
    assert cleared.source_text == "740"  # 原始来源逐字未改
    # 当前读法：清除行没有可核实的当前数值，不得从 source_text 回填 740。
    assert report_c._numeric_for(cleared) is None
    value_text = report_c._value_text(report, cleared)
    assert value_text == CLEARED_SAMPLE_TEXT
    assert "740" not in value_text
    assert report_c._matrix_item_summaries(report, cleared) == (CLEARED_SAMPLE_TEXT,)
    items = _matrix_items(report, cleared)
    assert [item["summary"] for item in items] == [CLEARED_SAMPLE_TEXT]
    assert all("740" not in item["summary"] for item in items)
    assert items[0]["source_text"] == "740"  # 来源原文保留在条目来源字段
    assert items[0]["disclosure_state"] == "user_cleared"


def test_cleared_sample_size_keeps_source_evidence_and_state_reason(
    report: ReportCPortalData,
) -> None:
    cleared = _cleared_sample_size(report)
    chart = report_c._chart_row(report, cleared, chart_type="bubble")
    assert chart["status"] == "用户清除，待重新核实"
    assert chart["value"] is None
    assert chart["renderable"] is False
    assert chart["display_label_zh"] == "计划或实际样本量"
    assert chart["source_text"] == "740"
    assert chart["source_version_id"]
    workspace = design_comparison_workspace(report, (cleared,))
    assert cleared.row_id in workspace["membership"].row_ids
    assert cleared.row_id not in workspace["numeric_eligibility"].drawable_row_ids
    reason = workspace["numeric_eligibility"].undrawable_reasons[cleared.row_id]
    assert "用户清除" in reason
    assert "非负整数" not in reason
    evidence = report_c._evidence_view(
        report, cleared, page_id="sample-analysis-statistics"
    )
    assert evidence.value.value == CLEARED_SAMPLE_TEXT
    assert evidence.original_text == "740"  # 原文与来源定位仍逐字保留
    assert evidence.source_trace_state == "located"


def test_cleared_reported_zero_does_not_revive_zero_value(
    report: ReportCPortalData,
) -> None:
    base = _observation(report, SAMPLE_ROW_ID)
    zero = base.model_copy(
        update={
            "threshold_value": "0",
            "source_text": "0",
            "reported_zero_text": "0",
            "disclosure_state": FactDisclosureState.REPORTED_ZERO,
        }
    )
    cleared = zero.model_copy(
        update={
            "threshold_value": None,
            "disclosure_state": FactDisclosureState.USER_CLEARED,
            "review_state": FactReviewState.USER_MODIFIED,
            "display_text": CLEARED_ZERO_TEXT,
        }
    )
    assert report_c._numeric_for(cleared) is None
    assert report_c._value_text(report, cleared) == CLEARED_ZERO_TEXT
    assert report_c._matrix_item_summaries(report, cleared) == (CLEARED_ZERO_TEXT,)
    chart = report_c._chart_row(report, cleared, chart_type="bubble")
    assert chart["value"] is None
    assert chart["status"] == "用户清除，待重新核实"


def test_edited_sample_size_current_threshold_still_reads_and_plots(
    report: ReportCPortalData,
) -> None:
    base = _observation(report, SAMPLE_ROW_ID)
    edited = base.model_copy(
        update={
            "threshold_value": "500",
            "review_state": FactReviewState.USER_MODIFIED,
            "display_text": "计划入组：500 例（用户修订）",
        }
    )
    # 用户修订给出了当前数值：当前读法用当前阈值，不是原始来源旧值。
    assert report_c._numeric_for(edited) == 500.0
    assert report_c._value_text(report, edited) == "500"
    chart = report_c._chart_row(report, edited, chart_type="bubble")
    assert chart["value"] == 500
    assert chart["renderable"] is True
    assert chart["source_text"] == "740"  # 原始来源仍在
    workspace = design_comparison_workspace(report, (edited,))
    assert workspace["numeric_eligibility"].drawable_row_ids == (edited.row_id,)


def test_cleared_sample_size_with_leftover_threshold_still_reads_cleared_state(
    report: ReportCPortalData,
) -> None:
    base = _observation(report, SAMPLE_ROW_ID)
    leftover = base.model_copy(
        update={
            "threshold_value": "740",
            "disclosure_state": FactDisclosureState.USER_CLEARED,
            "review_state": FactReviewState.USER_MODIFIED,
            "display_text": CLEARED_SAMPLE_TEXT,
        }
    )
    # 状态为先：用户清除优先于数值轴，不得因残留阈值复活 740。
    assert report_c._numeric_for(leftover) is None
    assert report_c._value_text(report, leftover) == CLEARED_SAMPLE_TEXT
    assert report_c._matrix_item_summaries(report, leftover) == (CLEARED_SAMPLE_TEXT,)
    workspace = design_comparison_workspace(report, (leftover,))
    assert leftover.row_id not in workspace["numeric_eligibility"].drawable_row_ids
    assert "用户清除" in workspace["numeric_eligibility"].undrawable_reasons[leftover.row_id]


def test_genuine_reported_zero_still_reads_zero_and_stays_drawable(
    report: ReportCPortalData,
) -> None:
    base = _observation(report, SAMPLE_ROW_ID)
    zero = base.model_copy(
        update={
            "threshold_value": "0",
            "source_text": "0",
            "reported_zero_text": "0",
            "disclosure_state": FactDisclosureState.REPORTED_ZERO,
        }
    )
    # 真实已报告零值不是清除：仍按 0 进入当前读法与数值同轴。
    assert report_c._numeric_for(zero) == 0.0
    assert report_c._value_text(report, zero) == "0"
    assert report_c._matrix_item_summaries(report, zero) == ("0",)
    chart = report_c._chart_row(report, zero, chart_type="bubble")
    assert chart["status"] == "0"
    assert chart["value"] == 0
    assert chart["renderable"] is True
    workspace = design_comparison_workspace(report, (zero,))
    assert workspace["numeric_eligibility"].drawable_row_ids == (zero.row_id,)


def test_unedited_sample_sizes_keep_source_derived_current_reading(
    report: ReportCPortalData,
) -> None:
    sample_sizes = [
        item for item in report.observations
        if item.field == "planned_or_actual_sample_size"
    ]
    assert len(sample_sizes) == 4
    for observation in sample_sizes:
        expected = float(observation.threshold_value or observation.source_text)
        assert report_c._numeric_for(observation) == expected
        assert report_c._value_text(report, observation) == str(int(expected))
        assert report_c._matrix_item_summaries(report, observation) == (str(int(expected)),)
    workspace = design_comparison_workspace(report, report.observations)
    assert set(workspace["numeric_eligibility"].drawable_row_ids) == {
        item.row_id for item in sample_sizes
    }


def test_edited_criterion_current_summary_does_not_split_stale_source(
    report: ReportCPortalData,
) -> None:
    original = _observation(report, CRITERION_ROW_ID)
    edited = original.model_copy(
        update={
            "source_text": MULTI_CRITERION_SOURCE,
            "display_text": EDITED_CRITERION_TEXT,
            "threshold_value": None,
            "disclosure_state": FactDisclosureState.REPORTED_VALUE,
            "review_state": FactReviewState.USER_MODIFIED,
        }
    )
    summaries = report_c._matrix_item_summaries(report, edited)
    assert summaries == (EDITED_CRITERION_TEXT,)
    assert all(
        fragment not in summary
        for summary in summaries
        for fragment in MULTI_CRITERION_PARTS
    )
    items = _matrix_items(report, edited)
    assert [item["summary"] for item in items] == [EDITED_CRITERION_TEXT]
    assert items[0]["source_text"] == MULTI_CRITERION_SOURCE  # 原文逐字保留
    rows = report_c._table_rows(report, (edited,), page_id="inclusion-criteria")
    assert len(rows) == 1
    assert EDITED_CRITERION_TEXT in rows[0]["value"]
    assert all(fragment not in rows[0]["value"] for fragment in MULTI_CRITERION_PARTS)
    assert edited.source_text == MULTI_CRITERION_SOURCE
    evidence = report_c._evidence_view(report, edited, page_id="inclusion-criteria")
    assert evidence.original_text == MULTI_CRITERION_SOURCE


def test_cleared_criterion_current_reading_uses_state_not_stale_parts(
    report: ReportCPortalData,
) -> None:
    original = _observation(report, CRITERION_ROW_ID)
    cleared = original.model_copy(
        update={
            "source_text": MULTI_CRITERION_SOURCE,
            "display_text": CLEARED_CRITERION_TEXT,
            "threshold_value": None,
            "disclosure_state": FactDisclosureState.USER_CLEARED,
            "review_state": FactReviewState.USER_MODIFIED,
        }
    )
    summaries = report_c._matrix_item_summaries(report, cleared)
    assert len(summaries) == 1
    assert "用户清除" in summaries[0]
    assert all(fragment not in summaries[0] for fragment in MULTI_CRITERION_PARTS)
    rows = report_c._table_rows(report, (cleared,), page_id="inclusion-criteria")
    assert len(rows) == 1
    assert "用户清除" in rows[0]["value"]
    assert all(fragment not in rows[0]["value"] for fragment in MULTI_CRITERION_PARTS)
    assert rows[0]["disclosure_state"] == "user_cleared"
    evidence = report_c._evidence_view(report, cleared, page_id="inclusion-criteria")
    assert evidence.original_text == MULTI_CRITERION_SOURCE
    assert all(
        fragment not in (evidence.value.value or "")
        for fragment in MULTI_CRITERION_PARTS
    )


def test_unedited_multiline_criterion_still_splits_into_source_parts(
    report: ReportCPortalData,
) -> None:
    original = _observation(report, CRITERION_ROW_ID)
    unedited = original.model_copy(
        update={
            "source_text": MULTI_CRITERION_SOURCE,
            "display_text": None,
            "threshold_value": None,
        }
    )
    summaries = report_c._matrix_item_summaries(report, unedited)
    assert len(summaries) == len(MULTI_CRITERION_PARTS)
    for fragment in MULTI_CRITERION_PARTS:
        assert any(fragment in summary for summary in summaries)
    rows = report_c._table_rows(report, (unedited,), page_id="inclusion-criteria")
    assert len(rows) == len(MULTI_CRITERION_PARTS)
    assert unedited.source_text == MULTI_CRITERION_SOURCE


def test_not_reported_row_stays_not_reported_member(
    report: ReportCPortalData,
) -> None:
    original = _observation(report, SAMPLE_ROW_ID)
    unknown = original.model_copy(
        update={"disclosure_state": FactDisclosureState.NOT_REPORTED}
    )
    chart = report_c._chart_row(report, unknown, chart_type="status_matrix")
    assert chart["status"] == "未报告"
    assert chart["disclosure_state"] == "not_reported"
    assert chart["value"] is None
    assert chart["renderable"] is False
    workspace = design_comparison_workspace(report, (unknown,))
    assert unknown.row_id in workspace["membership"].row_ids
    assert unknown.row_id not in workspace["numeric_eligibility"].drawable_row_ids
    reason = workspace["numeric_eligibility"].undrawable_reasons[unknown.row_id]
    assert "用户清除" not in reason
    assert "未报告" in reason


@pytest.mark.parametrize("state", [
    FactDisclosureState.NOT_REPORTED,
    FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
    FactDisclosureState.NOT_APPLICABLE,
    FactDisclosureState.BELOW_REPORTING_THRESHOLD,
    FactDisclosureState.CONFLICTING,
    FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE,
])
def test_nonreported_sample_current_reading_never_revives_numeric_axis(
    report: ReportCPortalData, state: FactDisclosureState,
) -> None:
    original = _observation(report, SAMPLE_ROW_ID)
    unknown = original.model_copy(update={"disclosure_state": state})
    assert unknown.source_text == "740"
    assert report_c._numeric_for(unknown) is None
    current = report_c._state_label(state)
    assert report_c._value_text(report, unknown) == current
    assert report_c._matrix_item_summaries(report, unknown) == (current,)
    items = _matrix_items(report, unknown)
    assert items[0]["summary"] == current
    assert items[0]["source_text"] == "740"
    assert items[0]["disclosure_state"] == state.value
    view = report_c._evidence_view(report, unknown, page_id="sample-analysis-statistics")
    assert view.value.value == current
    assert view.original_text == "740"
    workspace = design_comparison_workspace(report, (unknown,))
    assert unknown.row_id in workspace["membership"].row_ids
    assert unknown.row_id not in workspace["numeric_eligibility"].drawable_row_ids
    assert current in workspace["numeric_eligibility"].undrawable_reasons[unknown.row_id]


@pytest.mark.parametrize("current_number", [None, 500])
def test_native_revision_rebuild_keeps_current_and_original_sample_separate(
    report: ReportCPortalData, tmp_path: Path, current_number: int | None,
) -> None:
    """Full native render of a source-bound development edit, not a browser acceptance."""
    original = _observation(report, SAMPLE_ROW_ID)
    before = report.model_dump_json()
    binding = report_c.active_fact_binding_for_c(report, SAMPLE_ROW_ID)
    identity = binding.model_dump(exclude={
        "report", "collection", "row_id", "original_row_sha256", "source_pointer",
    })
    fact = ActiveFact(
        **identity, fact_id="development-sample", fact_version_id="development-sample-v2",
        field_id="design.sample_size", primary_fragment_id="development-source-fragment",
        raw_value=None if current_number is None else str(current_number),
        normalized_value=current_number, threshold_value=current_number,
        threshold_unit=original.threshold_unit, threshold_operator=original.operator,
        source_locator=binding.source_pointer, source_quote=original.source_text,
        consumer_bindings=(binding,), review_state="user_modified",
        disclosure_state="user_cleared" if current_number is None else "reported_value",
        user_edit={"request_id": "development-current-reading", "revision": 1,
                   "operation": "save", "basis": "开发验收用，不修改实际项目。",
                   "saved_by": "development-test", "saved_at": "2026-10-08T04:00:00Z"},
    )
    revision = ActiveFactRevision(
        revision=1, request_id="development-current-reading",
        fact_revision_digest="a" * 64, facts=(fact,),
    )
    site = tmp_path / "native-c"
    report_c.render_report_c_site(report, site, active_revision=revision)

    def assignment(relative: str, name: str):
        raw = (site / relative).read_text(encoding="utf-8")
        match = re.search(rf"window\.{re.escape(name)}\s*=\s*", raw)
        assert match is not None, (relative, name)
        return json.JSONDecoder().raw_decode(raw[match.end():].lstrip())[0]

    for relative in ("overview.html", "sample-analysis-statistics.html",
                     f"trials/{original.trial_id}.html"):
        workspace = assignment(relative, "__C_DESIGN_WORKSPACE__")
        items = [item for column in workspace["columns"] for cell in column["cells"]
                 for item in cell["items"] if item["row_id"] == SAMPLE_ROW_ID]
        assert items and all(item["source_text"] == "740" for item in items)
        summaries = [item["summary"] for item in items]
        if current_number is None:
            assert all("用户清除" in summary and "740" not in summary for summary in summaries)
        else:
            assert summaries == ["500"]
        evidence = next(view for view in assignment(relative, "__EVIDENCE_VIEWS__")
                        if view["row"]["row_id"] == SAMPLE_ROW_ID)
        assert evidence["original_text"] == "740"
        assert evidence["user_edit"]["original_value"]
        assert "740" not in str(evidence["value"]["value"])
    assert report.model_dump_json() == before
    assert not (site / "current.json").exists()
