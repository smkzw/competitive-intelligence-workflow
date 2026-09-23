"""Task 4.1 共用报告视图模型：稳定行身份与单快照/单页面责任绑定。

行 ID 由科学身份字段（事实/声明/产品/试验/组别/终点/事件/时间点）的
**字段名 + 规范化值** 确定性推导，与中文显示标签、排序、筛选和输出格式
无关；身份不足与重复身份失败关闭。生产验证器包装 Pydantic 校验，把模型
层错误统一为 ``ViewStateBoundaryError``。

取值查找边界（最小视图合同）：行只携带不可变科学身份与绑定，不重复存放
临床数值；消费方只能经 ``report_snapshot_id`` 标识的锁定快照解析取值。
该边界由以下机械绑定强制执行：(1) 行/视图/模块绑定恰好一个锁定快照与
一个页面责任；(2) 筛选行必须是规范视图行本体（模型级全等，见
``chart_specs``），任何层都不能替换行内容或换取其他快照；(3) 页面责任
必须属于匹配报告类型的冻结目录（生产验证器自动加载 PageRegistry，
不接受调用方注入注册表）。
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from pydantic import (
    ValidationError as PydanticValidationError,
)

from ci_workflow.domain.enums import FactDisclosureState, ReportKind
from ci_workflow.domain.ids import stable_id
from ci_workflow.reports.common.page_registry import PageRegistry

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")

# 行身份字段的规范顺序：推导 ID 时按此顺序拼接，顺序本身是身份的一部分。
_ROW_IDENTITY_FIELDS: tuple[str, ...] = (
    "fact_id",
    "claim_id",
    "product_id",
    "trial_id",
    "group_id",
    "endpoint_id",
    "event_id",
    "timepoint_id",
)


class ViewStateBoundaryError(ValueError):
    """视图模型边界拒绝：身份不足、重复身份或跨快照/跨页面混用。"""


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("文本不能为空")
    return normalized


def _has_chinese(value: str) -> bool:
    return _CJK_RE.search(value) is not None


def derive_row_id(
    *,
    fact_id: str | None = None,
    claim_id: str | None = None,
    product_id: str | None = None,
    trial_id: str | None = None,
    group_id: str | None = None,
    endpoint_id: str | None = None,
    event_id: str | None = None,
    timepoint_id: str | None = None,
) -> str:
    """由科学身份字段（字段名 + 规范化值）确定性推导行 ID；身份不足时失败关闭。

    字段名参与身份材料，避免 ``fact_id="x"`` 与 ``claim_id="x"`` 等跨身份
    字段同值碰撞；字段按 ``_ROW_IDENTITY_FIELDS`` 规范顺序拼接，关键字
    传入顺序不改变身份。排序、筛选、中文标签与格式变化不改变身份。
    """
    values = {
        "fact_id": fact_id,
        "claim_id": claim_id,
        "product_id": product_id,
        "trial_id": trial_id,
        "group_id": group_id,
        "endpoint_id": endpoint_id,
        "event_id": event_id,
        "timepoint_id": timepoint_id,
    }
    pairs: list[tuple[str, str]] = []
    for field in _ROW_IDENTITY_FIELDS:
        value = values[field]
        if value is None:
            continue
        try:
            normalized = _text(value)
        except ValueError as error:
            raise ViewStateBoundaryError("科学身份字段不能为空") from error
        pairs.append((field, normalized))
    if not pairs:
        raise ViewStateBoundaryError("报告行缺少科学身份字段，身份不足必须失败关闭")
    material = json.dumps(pairs, ensure_ascii=False, separators=(",", ":"))
    return stable_id("report-row", material)


class ReportRow(BaseModel):
    """一个视图行：科学身份字段 + 中文显示标签 + 单快照/单页面责任绑定。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    row_id: str
    fact_id: str | None = None
    claim_id: str | None = None
    product_id: str | None = None
    trial_id: str | None = None
    group_id: str | None = None
    endpoint_id: str | None = None
    event_id: str | None = None
    timepoint_id: str | None = None
    display_label_zh: str
    page_responsibility_id: str
    report_snapshot_id: str
    disclosure_state: FactDisclosureState

    @field_validator(
        "row_id", "page_responsibility_id", "report_snapshot_id"
    )
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator(
        "fact_id", "claim_id", "product_id", "trial_id",
        "group_id", "endpoint_id", "event_id", "timepoint_id",
    )
    @classmethod
    def _identity_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _text(value)

    @field_validator("display_label_zh")
    @classmethod
    def _label_has_chinese(cls, value: str) -> str:
        normalized = _text(value)
        if not _has_chinese(normalized):
            raise ValueError("中文显示标签必须包含中文")
        return normalized

    @model_validator(mode="after")
    def _identity_sufficient_and_id_consistent(self) -> ReportRow:
        identity = {
            field: getattr(self, field)
            for field in _ROW_IDENTITY_FIELDS
            if getattr(self, field) is not None
        }
        if not identity:
            raise ValueError("报告行缺少科学身份字段，身份不足必须失败关闭")
        if self.row_id != derive_row_id(**identity):
            raise ValueError(
                f"报告行身份与科学身份字段不一致：{self.row_id}（自由替换被拒绝）"
            )
        return self


class ReportViewModel(BaseModel):
    """一个页面责任下的不可变行视图：全部行绑定同一锁定快照与页面。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    report_kind: ReportKind
    page_responsibility_id: str
    report_snapshot_id: str
    report_version: str
    rows: tuple[ReportRow, ...]

    @field_validator(
        "page_responsibility_id", "report_snapshot_id", "report_version"
    )
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _text(value)

    @model_validator(mode="after")
    def _rows_unique_and_bound(self) -> ReportViewModel:
        row_ids = [row.row_id for row in self.rows]
        if len(set(row_ids)) != len(row_ids):
            raise ValueError("报告视图包含重复科学身份行，必须失败关闭")
        for row in self.rows:
            if row.report_snapshot_id != self.report_snapshot_id:
                raise ValueError("报告视图混用多个锁定快照，必须失败关闭")
            if row.page_responsibility_id != self.page_responsibility_id:
                raise ValueError("报告视图混用多个页面责任，必须失败关闭")
        return self


class WorkspaceMembership(BaseModel):
    """All relevant rows retained in the workspace before faceting or plotting."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    row_ids: tuple[str, ...]

    @field_validator("row_ids")
    @classmethod
    def _unique_rows(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("工作区成员不能包含重复行")
        return values

    @classmethod
    def from_view(cls, view: ReportViewModel) -> WorkspaceMembership:
        return cls(row_ids=tuple(row.row_id for row in view.rows))


class FacetAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    row_id: str
    facet_id: str

    @field_validator("row_id", "facet_id")
    @classmethod
    def _nonblank(cls, value: str) -> str:
        return _text(value)


class FacetPlan(BaseModel):
    """Display grouping only; it never changes workspace membership."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    membership_row_ids: tuple[str, ...]
    assignments: tuple[FacetAssignment, ...]

    @model_validator(mode="after")
    def _covers_membership_once(self) -> Self:
        assigned = tuple(item.row_id for item in self.assignments)
        if len(assigned) != len(set(assigned)):
            raise ValueError("分面计划不能重复分配同一行")
        if set(assigned) != set(self.membership_row_ids):
            raise ValueError("分面计划必须完整覆盖工作区成员且不得增删成员")
        return self


class NumericFrameEligibility(BaseModel):
    """Plot eligibility is a partition of membership, not a membership filter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    membership_row_ids: tuple[str, ...]
    drawable_row_ids: tuple[str, ...]
    undrawable_reasons: dict[str, str]

    @model_validator(mode="after")
    def _partitions_membership(self) -> Self:
        drawable = set(self.drawable_row_ids)
        undrawable = set(self.undrawable_reasons)
        membership = set(self.membership_row_ids)
        if len(drawable) != len(self.drawable_row_ids):
            raise ValueError("可绘集合不能包含重复行")
        if drawable & undrawable:
            raise ValueError("可绘与不可绘集合必须不相交")
        if drawable | undrawable != membership:
            raise ValueError("数值资格必须完整划分工作区成员")
        if any(not _text(reason) for reason in self.undrawable_reasons.values()):
            raise ValueError("不可绘原因不能为空")
        return self


class ReportQuery(BaseModel):
    """Closed, typed scientific query; ``None`` means no criterion, ``()`` means zero."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    row_ids: tuple[str, ...] | None = None
    fact_ids: tuple[str, ...] | None = None
    claim_ids: tuple[str, ...] | None = None
    product_ids: tuple[str, ...] | None = None
    trial_ids: tuple[str, ...] | None = None
    group_ids: tuple[str, ...] | None = None
    endpoint_ids: tuple[str, ...] | None = None
    event_ids: tuple[str, ...] | None = None
    timepoint_ids: tuple[str, ...] | None = None

    @field_validator(
        "row_ids", "fact_ids", "claim_ids", "product_ids", "trial_ids",
        "group_ids", "endpoint_ids", "event_ids", "timepoint_ids",
    )
    @classmethod
    def _unique_values(cls, values: tuple[str, ...] | None) -> tuple[str, ...] | None:
        if values is not None and len(values) != len(set(values)):
            raise ValueError("查询条件不能包含重复值")
        return values


_QUERY_TO_ROW_FIELD = {
    "fact_ids": "fact_id",
    "claim_ids": "claim_id",
    "product_ids": "product_id",
    "trial_ids": "trial_id",
    "group_ids": "group_id",
    "endpoint_ids": "endpoint_id",
    "event_ids": "event_id",
    "timepoint_ids": "timepoint_id",
}


class VisualState(BaseModel):
    """Non-scientific presentation state; changing it cannot alter ``ReportQuery``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    hidden_series: tuple[str, ...] = ()
    zoom: tuple[float, float] = (0.0, 100.0)

    @model_validator(mode="after")
    def _valid_zoom(self) -> Self:
        start, end = self.zoom
        if not 0.0 <= start <= end <= 100.0:
            raise ValueError("缩放范围必须位于 0 到 100 且起点不晚于终点")
        return self


class ReportViewState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    report_kind: ReportKind
    report_snapshot_id: str
    page_responsibility_id: str
    query: ReportQuery
    selected_fact_id: str | None = None
    drilldown_fact_id: str | None = None
    visual: VisualState = Field(default_factory=VisualState)

    def with_visual(
        self,
        *,
        hidden_series: tuple[str, ...],
        zoom: tuple[float, float],
    ) -> ReportViewState:
        return self.model_copy(
            update={"visual": VisualState(hidden_series=hidden_series, zoom=zoom)}
        )


class BoundViewState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    chart_fact_ids: tuple[str, ...]
    table_fact_ids: tuple[str, ...]
    selected_fact_id: str | None
    drilldown_fact_id: str | None


class ReportQueryResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    report_kind: ReportKind
    report_snapshot_id: str
    page_responsibility_id: str
    query_row_ids: tuple[str, ...]
    drawable_row_ids: tuple[str, ...]
    undrawable_row_ids: tuple[str, ...]
    query_fact_ids: tuple[str, ...]
    drawable_fact_ids: tuple[str, ...]

    @model_validator(mode="after")
    def _conserves_query(self) -> Self:
        query = set(self.query_row_ids)
        drawable = set(self.drawable_row_ids)
        undrawable = set(self.undrawable_row_ids)
        if drawable & undrawable or drawable | undrawable != query:
            raise ValueError("查询守恒失败：Q 必须等于可绘 P 与不可绘 U 的不相交并集")
        return self

    def bind_view_state(self, state: ReportViewState) -> BoundViewState:
        if (
            state.report_kind != self.report_kind
            or state.report_snapshot_id != self.report_snapshot_id
            or state.page_responsibility_id != self.page_responsibility_id
        ):
            raise ViewStateBoundaryError("ViewState 与查询结果的报告、快照或页面不一致")
        facts = set(self.query_fact_ids)
        for value in (state.selected_fact_id, state.drilldown_fact_id):
            if value is not None and value not in facts:
                raise ViewStateBoundaryError("选中或下钻事实不属于当前科学查询")
        return BoundViewState(
            chart_fact_ids=self.drawable_fact_ids,
            table_fact_ids=self.query_fact_ids,
            selected_fact_id=state.selected_fact_id,
            drilldown_fact_id=state.drilldown_fact_id,
        )


def query_workspace_membership(
    view: ReportViewModel,
    query: ReportQuery,
) -> tuple[ReportRow, ...]:
    """Apply only scientific membership criteria; empty matches remain empty."""
    selected: list[ReportRow] = []
    for row in view.rows:
        if query.row_ids is not None and row.row_id not in query.row_ids:
            continue
        if any(
            values is not None and getattr(row, field) not in values
            for query_field, field in _QUERY_TO_ROW_FIELD.items()
            if (values := getattr(query, query_field)) is not None
        ):
            continue
        selected.append(row)
    return tuple(selected)


def execute_report_query(
    view: ReportViewModel,
    query: ReportQuery,
    *,
    membership: WorkspaceMembership,
    facets: FacetPlan,
    eligibility: NumericFrameEligibility,
) -> ReportQueryResult:
    """Execute one closed scientific query without visual-state or zero-hit fallback."""
    canonical_ids = tuple(row.row_id for row in view.rows)
    if set(membership.row_ids) != set(canonical_ids):
        raise ViewStateBoundaryError("工作区成员必须与报告视图完整一致")
    if set(facets.membership_row_ids) != set(membership.row_ids):
        raise ViewStateBoundaryError("分面计划与工作区成员不一致")
    if set(eligibility.membership_row_ids) != set(membership.row_ids):
        raise ViewStateBoundaryError("数值资格与工作区成员不一致")

    selected = query_workspace_membership(view, query)
    query_ids = tuple(row.row_id for row in selected)
    drawable_set = set(eligibility.drawable_row_ids)
    drawable_ids = tuple(row_id for row_id in query_ids if row_id in drawable_set)
    undrawable_ids = tuple(row_id for row_id in query_ids if row_id not in drawable_set)
    query_fact_ids = tuple(dict.fromkeys(row.fact_id for row in selected if row.fact_id))
    drawable_fact_ids = tuple(
        dict.fromkeys(
            row.fact_id for row in selected
            if row.row_id in drawable_set and row.fact_id
        )
    )
    return ReportQueryResult(
        report_kind=view.report_kind,
        report_snapshot_id=view.report_snapshot_id,
        page_responsibility_id=view.page_responsibility_id,
        query_row_ids=query_ids,
        drawable_row_ids=drawable_ids,
        undrawable_row_ids=undrawable_ids,
        query_fact_ids=query_fact_ids,
        drawable_fact_ids=drawable_fact_ids,
    )


def validate_report_row_payload(
    raw: dict[str, Any],
    *,
    report_kind: ReportKind,
) -> ReportRow:
    """生产行验证器：Pydantic 模型 + 身份一致性 + 冻结目录页面责任权威。

    独立行必须携带报告上下文：页面责任必须属于该报告类型的冻结目录或
    动态详情责任（PageRegistry 自动加载，不接受调用方注入注册表）。
    省略报告上下文或使用目录外页面责任均失败关闭。
    """
    try:
        row = ReportRow.model_validate(raw)
    except PydanticValidationError as error:
        raise ViewStateBoundaryError(f"报告行模型校验失败：{error}") from error
    registry = PageRegistry.load()
    known = registry.page_responsibility_ids(report_kind)
    if row.page_responsibility_id not in known:
        raise ViewStateBoundaryError(
            f"页面责任不在冻结目录中：{row.page_responsibility_id}"
            f"（{report_kind.value} 目录外，未知责任必须失败关闭）"
        )
    return row


def _assert_page_in_catalog(model: ReportViewModel, registry: PageRegistry) -> None:
    """页面责任必须属于匹配报告类型的冻结目录或动态详情责任。"""
    known = registry.page_responsibility_ids(model.report_kind)
    if model.page_responsibility_id not in known:
        raise ViewStateBoundaryError(
            f"页面责任不在冻结目录中：{model.page_responsibility_id}"
            f"（{model.report_kind.value} 目录外，未知责任必须失败关闭）"
        )


def _validate_report_view_model_payload_with_registry(
    raw: dict[str, Any],
    registry: PageRegistry,
) -> ReportViewModel:
    """内部/测试专用：以给定注册表校验视图模型；公开边界必须使用冻结注册表。"""
    try:
        model = ReportViewModel.model_validate(raw)
    except PydanticValidationError as error:
        raise ViewStateBoundaryError(f"报告视图模型校验失败：{error}") from error
    _assert_page_in_catalog(model, registry)
    return model


def validate_report_view_model_payload(raw: dict[str, Any]) -> ReportViewModel:
    """生产视图验证器：单快照/单页面绑定、重复身份与目录外页面责任失败关闭。

    页面责任权威：始终加载冻结 PageRegistry（源码树或包内数据布局），
    不接受调用方注入注册表；自定义注册表只允许内部/测试专用路径。
    """
    return _validate_report_view_model_payload_with_registry(
        raw, PageRegistry.load()
    )
