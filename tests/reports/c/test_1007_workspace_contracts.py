"""1007V1：C 设计横比工作区接入共享成员/分面/数值资格合同。

有界执行 RED 家族（ci-1007-c-matched-workspace / worker_01）：
- ``WorkspaceMembership`` 保留每条观察恰好一次；``FacetPlan`` 是呈现归类，
  从不声明临床等价；``NumericFrameEligibility`` 只决定数值图权限，
  文本/未知/清除行保留明确原因并保持可查询成员身份。
- 生产 ``_design_matrix`` 消费同一编译结果：多研究共享设计维度的每个单元格
  保留各自原文、来源版本、产品/试验/组别、量表/算子/时间与缺失状态；
  同格多观察不首条胜出；重排不改变身份。
- 真实候选只做只读结构核对。本文件不是医学、浏览器或发布验收。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState, ReportKind
from ci_workflow.renderers.portal import report_c
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    design_comparison_workspace,
)
from ci_workflow.reports.common.page_registry import PageRegistry
from ci_workflow.reports.common.view_state import (
    FacetPlan,
    NumericFrameEligibility,
    ReportQuery,
    ReportRow,
    ReportViewModel,
    WorkspaceMembership,
    execute_report_query,
)

ROOT = Path(__file__).resolve().parents[3]
REPORT_DATA = ROOT / "fixtures/positive/c-atopic-dermatitis/inputs/report-data.json"
CANDIDATE = ROOT / (
    ".artifacts/1007-pn-joint-abc-source-v1/source-values-v2/working/project/"
    "evidence/library/c-candidate/source-context-v3-portal-data.json"
)


def _facet_id(field: str) -> str:
    return f"design-field::{field}"


def _columns_by_facet(workspace: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {column["facet_id"]: column for column in workspace["columns"]}


def _canonical_columns(workspace: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    """重排不变的身份投影：列/单元格/条目按稳定键排序后比较。"""
    canonical: list[dict[str, Any]] = []
    for column in workspace["columns"]:
        cells = []
        for cell in sorted(column["cells"], key=lambda item: item["trial_id"]):
            cells.append({**cell, "items": sorted(
                cell["items"], key=lambda item: (item["row_id"], item["summary"]),
            )})
        canonical.append({**column, "cells": cells})
    return tuple(sorted(canonical, key=lambda column: column["facet_id"]))


@pytest.fixture(scope="module")
def report() -> ReportCPortalData:
    return ReportCPortalData.model_validate_json(REPORT_DATA.read_bytes())


def test_workspace_membership_and_facets_cover_every_observation_once(
    report: ReportCPortalData,
) -> None:
    workspace = design_comparison_workspace(report, report.observations)
    membership = workspace["membership"]
    facets = workspace["facets"]
    eligibility = workspace["numeric_eligibility"]
    assert isinstance(membership, WorkspaceMembership)
    assert isinstance(facets, FacetPlan)
    assert isinstance(eligibility, NumericFrameEligibility)
    expected_ids = [observation.row_id for observation in report.observations]
    assert sorted(membership.row_ids) == sorted(expected_ids)
    assert len(membership.row_ids) == len(expected_ids)
    by_row = {assignment.row_id: assignment.facet_id for assignment in facets.assignments}
    assert set(by_row) == set(expected_ids)
    for observation in report.observations:
        assert by_row[observation.row_id] == _facet_id(observation.field)
    # 数值资格划分成员而非过滤成员
    assert set(eligibility.drawable_row_ids) | set(eligibility.undrawable_reasons) == (
        set(expected_ids)
    )
    assert not set(eligibility.drawable_row_ids) & set(eligibility.undrawable_reasons)
    assert all(reason.strip() for reason in eligibility.undrawable_reasons.values())


def test_shared_design_column_keeps_each_study_identity_and_heterogeneity(
    report: ReportCPortalData,
) -> None:
    workspace = design_comparison_workspace(report, report.observations)
    column = _columns_by_facet(workspace)[_facet_id("primary_endpoint_definition")]
    assert column["cross_study"] is True
    assert column["presentation_only"] is True
    assert "临床等价" in column["facet_note_zh"]
    assert set(column["trial_ids"]) == {trial.id for trial in report.trials}
    cells = {cell["trial_id"]: cell for cell in column["cells"]}
    endpoint_rows = [
        observation for observation in report.observations
        if observation.field == "primary_endpoint_definition"
    ]
    assert len(endpoint_rows) >= 2
    assert len({observation.scale for observation in endpoint_rows if observation.scale}) >= 2
    for observation in endpoint_rows:
        cell = cells[observation.trial_id]
        item = next(item for item in cell["items"] if item["row_id"] == observation.row_id)
        assert item["source_text"] == observation.source_text
        assert item["display_text"] == observation.display_text
        assert item["observation_id"] == observation.observation_id
        assert item["source_row_id"] == observation.source_row_id
        assert item["outcome_id"] == observation.outcome_id
        assert item["endpoint_key"] == observation.endpoint_key
        assert item["product_id"] == observation.product_id
        assert item["trial_id"] == observation.trial_id
        assert item["group_id"] == observation.group_id
        assert item["cohort_id"] == observation.cohort_id
        assert item["source_version_id"].strip()
        assert item["disclosure_state"] == observation.disclosure_state.value
        assert item["scale"] == observation.scale
        assert item["operator"] == observation.operator
        assert item["threshold_value"] == observation.threshold_value
        assert item["threshold_unit"] == observation.threshold_unit
        assert item["assessment_timepoint"] == observation.assessment_timepoint
    # 异质量表/时间窗按研究逐格保留，不合并为同一列取值
    scale_sets = {
        trial_id: frozenset(item["scale"] for item in cell["items"])
        for trial_id, cell in cells.items()
    }
    assert len(set(scale_sets.values())) >= 2


def test_numeric_eligibility_partitions_membership_and_is_independent_of_it(
    report: ReportCPortalData,
) -> None:
    workspace = design_comparison_workspace(report, report.observations)
    membership = workspace["membership"]
    eligibility = workspace["numeric_eligibility"]
    numeric_ids = {
        observation.row_id for observation in report.observations
        if observation.field == "planned_or_actual_sample_size"
    }
    assert set(eligibility.drawable_row_ids) == numeric_ids
    assert set(eligibility.undrawable_reasons) == set(membership.row_ids) - numeric_ids
    # 文本终点行：不可绘但始终是成员
    text_row = next(
        observation for observation in report.observations
        if observation.field == "primary_endpoint_definition"
    )
    assert text_row.row_id in eligibility.undrawable_reasons
    assert text_row.row_id in membership.row_ids


def test_text_unknown_and_cleared_rows_stay_members_with_explicit_reasons(
    report: ReportCPortalData,
) -> None:
    sample_sizes = [
        observation for observation in report.observations
        if observation.field == "planned_or_actual_sample_size"
    ]
    cleared = sample_sizes[0].model_copy(update={
        "disclosure_state": FactDisclosureState.USER_CLEARED,
        "review_state": FactReviewState.USER_MODIFIED,
    })
    unknown = sample_sizes[1].model_copy(update={
        "disclosure_state": FactDisclosureState.NOT_REPORTED,
    })
    data = report.model_copy(update={"observations": tuple(
        cleared if observation.row_id == sample_sizes[0].row_id
        else unknown if observation.row_id == sample_sizes[1].row_id
        else observation
        for observation in report.observations
    )})
    workspace = design_comparison_workspace(data, data.observations)
    membership = workspace["membership"]
    eligibility = workspace["numeric_eligibility"]
    assert cleared.row_id in membership.row_ids
    assert unknown.row_id in membership.row_ids
    assert cleared.row_id not in eligibility.drawable_row_ids
    assert "用户清除" in eligibility.undrawable_reasons[cleared.row_id]
    assert eligibility.undrawable_reasons[unknown.row_id].strip()
    by_row = {
        assignment.row_id: assignment.facet_id
        for assignment in workspace["facets"].assignments
    }
    assert by_row[cleared.row_id] == _facet_id("planned_or_actual_sample_size")
    assert by_row[unknown.row_id] == _facet_id("planned_or_actual_sample_size")
    # 可查询性：typed 查询在编译出的三层合同上执行，清除行仍可检索
    snapshot = data.report_snapshot_id or f"c-{data.report_version}"
    rows = tuple(
        ReportRow.model_construct(
            row_id=observation.row_id,
            fact_id=observation.source_row_id,
            product_id=observation.product_id,
            trial_id=observation.trial_id,
            group_id=observation.group_id,
            display_label_zh=report_c._field_label(observation.field),
            page_responsibility_id="overview",
            report_snapshot_id=snapshot,
            disclosure_state=observation.disclosure_state,
        )
        for observation in data.observations
    )
    view = ReportViewModel.model_construct(
        report_kind=ReportKind.C,
        page_responsibility_id="overview",
        report_snapshot_id=snapshot,
        report_version=data.report_version,
        rows=rows,
    )
    result = execute_report_query(
        view,
        ReportQuery(),
        membership=membership,
        facets=workspace["facets"],
        eligibility=eligibility,
    )
    assert set(result.query_row_ids) == set(membership.row_ids)
    assert cleared.row_id in result.undrawable_row_ids
    focused = execute_report_query(
        view,
        ReportQuery(row_ids=(cleared.row_id,)),
        membership=membership,
        facets=workspace["facets"],
        eligibility=eligibility,
    )
    assert focused.query_row_ids == (cleared.row_id,)
    assert focused.undrawable_row_ids == (cleared.row_id,)
    assert cleared.source_row_id in focused.query_fact_ids


def test_production_design_matrix_consumes_workspace_without_first_wins_loss(
    report: ReportCPortalData,
) -> None:
    base = next(
        observation for observation in report.observations
        if observation.field == "planned_or_actual_sample_size"
    )
    extra = base.model_copy(update={
        "row_id": base.row_id + "-second",
        "observation_id": base.observation_id + "-second",
        "source_row_id": base.source_row_id + "-second",
        "threshold_value": "500",
    })
    data = report.model_copy(update={"observations": report.observations + (extra,)})
    rows, _groups, _trials = report_c._design_matrix(data, data.observations)
    row = next(item for item in rows if item["field"] == "planned_or_actual_sample_size")
    assert row["facet_id"] == _facet_id("planned_or_actual_sample_size")
    assert row["presentation_only"] is True
    cell = next(item for item in row["cells"] if item["trial_id"] == base.trial_id)
    item_row_ids = {item["row_id"] for item in cell["items"]}
    assert {base.row_id, extra.row_id} <= item_row_ids
    assert cell["row_ids"] == (base.row_id, extra.row_id)
    assert set(row["numeric_eligible_row_ids"]) >= {base.row_id, extra.row_id}
    workspace = design_comparison_workspace(data, data.observations)
    assert extra.row_id in workspace["membership"].row_ids


def test_missing_cell_stays_explicit_while_trial_stays_member(
    report: ReportCPortalData,
) -> None:
    dropped_trial = report.trials[-1]
    dropped = next(
        observation for observation in report.observations
        if observation.field == "target_population"
        and observation.trial_id == dropped_trial.id
    )
    data = report.model_copy(update={"observations": tuple(
        observation for observation in report.observations
        if observation.row_id != dropped.row_id
    )})
    rows, _groups, _trials = report_c._design_matrix(data, data.observations)
    row = next(item for item in rows if item["field"] == "target_population")
    cell = next(item for item in row["cells"] if item["trial_id"] == dropped_trial.id)
    assert cell["empty"] is True
    assert cell["row_ids"] == ()
    workspace = design_comparison_workspace(data, data.observations)
    column = _columns_by_facet(workspace)[_facet_id("target_population")]
    compiled_cell = next(
        item for item in column["cells"] if item["trial_id"] == dropped_trial.id
    )
    assert compiled_cell["missing"] is True
    assert compiled_cell["row_ids"] == ()
    assert column["cross_study"] is True
    # 该研究仍通过其他观察保留在成员与分面中
    assert any(
        observation.row_id in workspace["membership"].row_ids
        for observation in data.observations
        if observation.trial_id == dropped_trial.id
    )


def test_reordering_observations_preserves_workspace_identity(
    report: ReportCPortalData,
) -> None:
    first = design_comparison_workspace(report, report.observations)
    reordered = tuple(sorted(report.observations, key=lambda item: item.row_id, reverse=True))
    second = design_comparison_workspace(report, reordered)
    assert sorted(first["membership"].row_ids) == sorted(second["membership"].row_ids)
    assert {
        (assignment.row_id, assignment.facet_id)
        for assignment in first["facets"].assignments
    } == {
        (assignment.row_id, assignment.facet_id)
        for assignment in second["facets"].assignments
    }
    assert sorted(first["numeric_eligibility"].drawable_row_ids) == sorted(
        second["numeric_eligibility"].drawable_row_ids
    )
    assert (
        first["numeric_eligibility"].undrawable_reasons
        == second["numeric_eligibility"].undrawable_reasons
    )
    assert _canonical_columns(first) == _canonical_columns(second)


def test_duplicate_observation_row_fails_closed(report: ReportCPortalData) -> None:
    duplicated = report.model_copy(update={
        "observations": report.observations + (report.observations[0],),
    })
    with pytest.raises(ValueError, match="重复"):
        design_comparison_workspace(duplicated, duplicated.observations)


@pytest.mark.parametrize("raw", ["NaN", "Infinity", "-1", "25.5", "not available"])
def test_invalid_sample_size_stays_member_without_numeric_permission(report, raw):
    original = next(o for o in report.observations
                    if o.field == "planned_or_actual_sample_size")
    invalid = original.model_copy(update={"threshold_value": raw, "source_text": raw})
    observations = tuple(invalid if o.row_id == original.row_id else o
                         for o in report.observations)
    workspace = design_comparison_workspace(report, observations)
    assert invalid.row_id in workspace["membership"].row_ids
    assert invalid.row_id not in workspace["numeric_eligibility"].drawable_row_ids
    reason = workspace["numeric_eligibility"].undrawable_reasons[invalid.row_id]
    assert "非负整数" in reason and "原文文本" not in reason


def test_serialized_workspace_binds_real_page_snapshot_and_row_query(report):
    catalog = PageRegistry.load().catalog(ReportKind.C)
    page = next(p for p in catalog.pages if p.id == "overview")
    context = report_c._render_page_context(report, page=page, catalog=catalog)
    import json
    payload = json.loads(context["design_workspace_json"])
    assert payload["snapshot_id"] == context["snapshot_id"]
    assert payload["row_set_digest"] == context["row_set_digest"]
    assert set(payload["membership"]["row_ids"]) == {o.row_id for o in report.observations}
    assert payload["columns"]
    for column in payload["columns"]:
        for cell in column["cells"]:
            for item in cell["items"]:
                assert item["source_locator"] and item["source_role"]


@pytest.mark.parametrize("field", ["field_path", "heading", "table", "row", "column",
                                    "paragraph", "url"])
def test_workspace_locator_consumes_existing_safe_public_projection(report, field):
    from ci_workflow.reports.common.evidence_view import is_local_path_shape

    original = report.observations[0]
    locator = original.source_locator.model_copy(update={field: "/Users/private/source.pdf",
                                                        "page": 3})
    row = original.model_copy(update={"source_locator": locator})
    changed = report.model_copy(update={"observations": (row,) + report.observations[1:]})
    workspace = design_comparison_workspace(changed, changed.observations)
    item = next(item for col in workspace["columns"] for cell in col["cells"]
                for item in cell["items"] if item["row_id"] == row.row_id)
    assert item["source_locator"]["page"] == 3
    assert all(not is_local_path_shape(value) for value in item["source_locator"].values()
               if isinstance(value, str))
    assert row.source_locator == locator  # raw source never rewritten


@pytest.mark.parametrize("kind", ["report", "evidence", "candidate"])
def test_serialized_query_explicitly_labels_report_versus_source_snapshot(report, kind):
    import json

    changed = report.model_copy(update={
        "report_snapshot_id": "actual-report-id" if kind == "report" else None,
        "source_evidence_snapshot_id": "actual-evidence-id" if kind == "evidence" else None,
    })
    catalog = PageRegistry.load().catalog(ReportKind.C)
    page = next(p for p in catalog.pages if p.id == "overview")
    context = report_c._render_page_context(changed, page=page, catalog=catalog)
    payload = json.loads(context["design_workspace_json"])
    assert payload["snapshot_kind"] == kind
    assert payload["report_snapshot_id"] == changed.report_snapshot_id
    assert payload["source_evidence_snapshot_id"] == changed.source_evidence_snapshot_id


def test_overview_page_context_binds_the_design_workspace(
    report: ReportCPortalData,
) -> None:
    registry = PageRegistry.load()
    catalog = registry.catalog(ReportKind.C)
    page = next(item for item in catalog.pages if item.id == "overview")
    context = report_c._render_page_context(report, page=page, catalog=catalog)
    assert context["show_design_matrix"] is True
    matrix_rows = context["design_matrix_rows"]
    assert matrix_rows
    for row in matrix_rows:
        assert row["facet_id"] == _facet_id(row["field"])
        assert row["presentation_only"] is True
        assert row["facet_note_zh"].strip()
    sample_row = next(
        item for item in matrix_rows
        if item["field"] == "planned_or_actual_sample_size"
    )
    assert len(sample_row["numeric_eligible_row_ids"]) == 4
    endpoint_row = next(
        item for item in matrix_rows
        if item["field"] == "primary_endpoint_definition"
    )
    assert endpoint_row["numeric_eligible_row_ids"] == ()
    assert len(endpoint_row["undrawable_reasons"]) == 4


@pytest.mark.skipif(not CANDIDATE.exists(), reason="只读真实候选不在当前工作区")
def test_real_candidate_workspace_structure_is_complete_and_identity_preserving() -> None:
    data = ReportCPortalData.model_validate_json(CANDIDATE.read_bytes())
    assert data.source_evidence_snapshot_id
    workspace = design_comparison_workspace(data, data.observations)
    membership = workspace["membership"]
    assert len(membership.row_ids) == len(data.observations)
    assert len(set(membership.row_ids)) == len(data.observations)
    by_row = {
        assignment.row_id: assignment.facet_id
        for assignment in workspace["facets"].assignments
    }
    assert set(by_row) == set(membership.row_ids)
    eligibility = workspace["numeric_eligibility"]
    numeric_ids = {
        observation.row_id for observation in data.observations
        if observation.field == "planned_or_actual_sample_size"
    }
    assert set(eligibility.drawable_row_ids) == numeric_ids
    grouped: dict[tuple[str, str], list[str]] = {}
    for observation in data.observations:
        grouped.setdefault((observation.field, observation.trial_id), []).append(
            observation.row_id
        )
    multi_cells = {key: value for key, value in grouped.items() if len(value) > 1}
    assert len(multi_cells) >= 40
    columns = _columns_by_facet(workspace)
    for (field, trial_id), row_ids in multi_cells.items():
        cell = next(
            item for item in columns[_facet_id(field)]["cells"] if item["trial_id"] == trial_id
        )
        assert set(row_ids) <= set(cell["row_ids"])
    public_versions = set(data.source_version_by_source_id.values())
    assert public_versions
    for column in workspace["columns"]:
        for cell in column["cells"]:
            for item in cell["items"]:
                assert item["source_version_id"] in public_versions
