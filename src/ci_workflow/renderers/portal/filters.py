# mypy: disable-error-code="operator"
"""Task 4.3 分层筛选与确定性 URL 状态：不可变类型化契约。

公开类型：
* ``FilterDimension`` — 单个筛选维度（ID 身份、中文标签、值列表、适用性）
* ``FilterValue`` — 维度内的一个可选值
* ``PageFilterScope`` — 页面级筛选状态
* ``ModuleFilterState`` — 模块级筛选状态
* ``SortState`` — 排序状态
* ``AnchorTrialState`` — 锚定试验
* ``EvidenceSelection`` — 选中证据片段
* ``PaginationState`` — 当前页码
* ``FilterState`` — 顶层不可变筛选状态
* ``FilterVersion`` — URL 状态版本
* ``PortalFilterError`` — 筛选边界拒绝

设计约束（§15.4 / §15.7）：
- 页面级维度（适应症/产品/靶点机制/试验）影响页面全部模块
- 模块级维度（终点/时间点/效应形式/分析人群/AE/设计要素/量表等）只影响相关模块
- B 基线与完成情况扩展：队列/组别/人群/变量域/统计形式/原因/分母角色/
  计量对象/时间窗/披露状态
- 页面重置只清页面筛选；模块重置只清指定模块；排序/锚定/证据/分页不跨作用域
- 状态版本化；未知/重复/非法字段失败关闭；中文错误
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

if TYPE_CHECKING:
    from ci_workflow.reports.common.chart_specs import FilteredRowSet
    from ci_workflow.reports.common.view_state import ReportViewModel

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")

# 页面级维度（§15.4）：稳定 ID；中文标签仅展示。
PAGE_DIMENSION_IDS: tuple[str, ...] = (
    "indication",
    "product",
    "target_or_mechanism",
    "trial",
)

# 模块级维度（§15.4），含 B 基线与完成情况扩展。
MODULE_DIMENSION_IDS: tuple[str, ...] = (
    "endpoint",
    "timepoint",
    "effect_measure",
    "analysis_population",
    "ae_term",
    "ae_grade",
    "design_element",
    "scale",
    # B 基线 / 处置扩展
    "cohort_or_arm",
    "baseline_or_disposition_population",
    "variable_domain",
    "statistic_form",
    "reason",
    "denominator_role",
    "measure_object",
    "time_window",
    "disclosure_state",
)

PAGE_DIMENSION_LABELS_ZH: dict[str, str] = {
    "indication": "适应症",
    "product": "产品",
    "target_or_mechanism": "靶点或机制",
    "trial": "试验",
}

MODULE_DIMENSION_LABELS_ZH: dict[str, str] = {
    "endpoint": "终点",
    "timepoint": "时间点",
    "effect_measure": "效应形式",
    "analysis_population": "分析人群",
    "ae_term": "不良事件术语",
    "ae_grade": "不良事件等级",
    "design_element": "设计要素",
    "scale": "量表",
    "cohort_or_arm": "队列或组别",
    "baseline_or_disposition_population": "基线或处置人群",
    "variable_domain": "变量域或字段族",
    "statistic_form": "统计形式",
    "reason": "原因",
    "denominator_role": "分母角色",
    "measure_object": "计量对象",
    "time_window": "时间窗",
    "disclosure_state": "披露状态",
}

# ReportRow 科学身份字段 ↔ 筛选维度（仅既有行；不创造身份）
_ROW_FIELD_BY_DIMENSION: dict[str, str] = {
    "product": "product_id",
    "trial": "trial_id",
    "endpoint": "endpoint_id",
    "timepoint": "timepoint_id",
    "ae_term": "event_id",
}

INAPPLICABLE_REASON_ZH = "当前页面或模块不适用此条件"

_STATIC_ROUTES: frozenset[str] | None = None
_DYNAMIC_ROUTE_PATTERNS: tuple[re.Pattern[str], ...] | None = None
_KNOWN_FILTER_PROFILES: frozenset[str] | None = None
_SLUG_SEGMENT_RE = re.compile(r"[a-z0-9][a-z0-9-]*")


def _ensure_catalog_authority() -> tuple[
    frozenset[str], tuple[re.Pattern[str], ...], frozenset[str]
]:
    """加载冻结 A/B/C 静态路由、动态详情模板与 filter_profiles。"""
    global _STATIC_ROUTES, _DYNAMIC_ROUTE_PATTERNS, _KNOWN_FILTER_PROFILES
    if (
        _STATIC_ROUTES is not None
        and _DYNAMIC_ROUTE_PATTERNS is not None
        and _KNOWN_FILTER_PROFILES is not None
    ):
        return _STATIC_ROUTES, _DYNAMIC_ROUTE_PATTERNS, _KNOWN_FILTER_PROFILES

    from ci_workflow.reports.common.page_registry import PageRegistry

    registry = PageRegistry.load()
    static: set[str] = set()
    patterns: list[re.Pattern[str]] = []
    profiles: set[str] = set()
    for catalog in registry.catalogs:
        for page in catalog.pages:
            static.add(page.route)
            profiles.update(page.filter_profiles)
        for spec in catalog.dynamic_routes:
            # ``/b/products/{product_id}`` → ``^/b/products/[a-z0-9][a-z0-9-]*$``
            escaped = re.escape(spec.route_template)
            regex = re.sub(
                r"\\\{[a-z0-9_]+\\\}",
                _SLUG_SEGMENT_RE.pattern,
                escaped,
            )
            patterns.append(re.compile(f"^{regex}$"))

    _STATIC_ROUTES = frozenset(static)
    _DYNAMIC_ROUTE_PATTERNS = tuple(patterns)
    _KNOWN_FILTER_PROFILES = frozenset(profiles)
    return _STATIC_ROUTES, _DYNAMIC_ROUTE_PATTERNS, _KNOWN_FILTER_PROFILES


def assert_known_page_route(page_id: str) -> str:
    """页面路由必须是冻结静态路由或合法动态产品/试验详情路由。"""
    static, patterns, _ = _ensure_catalog_authority()
    if page_id in static:
        return page_id
    for pattern in patterns:
        if pattern.fullmatch(page_id):
            return page_id
    raise PortalFilterError(f"页面不在冻结目录中：{page_id}")


def assert_known_filter_profile(module_id: str) -> str:
    """模块 ID 必须来自冻结目录 ``filter_profiles``。"""
    _, _, profiles = _ensure_catalog_authority()
    if module_id not in profiles:
        raise PortalFilterError(f"模块不在冻结目录中：{module_id}")
    return module_id


class PortalFilterError(ValueError):
    """筛选边界拒绝：未知页面、重复值、非法状态。"""


class FilterVersion(StrEnum):
    """URL 状态版本——便于未来迁移。"""

    V1 = "v1"


class FilterValue(BaseModel):
    """维度内的一个可选值：稳定 ID + 中文展示标签。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    label_zh: str

    @field_validator("id")
    @classmethod
    def _id_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("筛选值 ID 不能为空")
        return normalized

    @field_validator("label_zh")
    @classmethod
    def _label_must_have_chinese(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("中文标签不能为空")
        if not _CJK_RE.search(normalized):
            raise ValueError(f"中文标签必须包含中文字符：{normalized}")
        return normalized


class FilterDimension(BaseModel):
    """一个筛选维度：稳定 ID、中文标签、值列表、按页面/模块适用性。

    ID 是身份，中文标签仅展示。适用性声明决定维度在哪些页面/模块可见或
    禁用；不适用的维度应隐藏或显示禁用原因，不得标注为"数据缺失"。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    label_zh: str
    values: tuple[FilterValue, ...]
    page_applicability: dict[str, bool]
    module_applicability: dict[str, bool]
    disabled_reason_zh: str | None = None

    @field_validator("id")
    @classmethod
    def _id_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("筛选维度 ID 不能为空")
        return normalized

    @field_validator("label_zh")
    @classmethod
    def _label_must_have_chinese(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not _CJK_RE.search(normalized):
            raise ValueError(f"维度中文标签必须包含中文：{normalized}")
        return normalized

    def is_applicable_to_page(self, page_id: str) -> bool:
        return self.page_applicability.get(page_id, False)

    def is_applicable_to_module(self, module_id: str) -> bool:
        return self.module_applicability.get(module_id, False)


class PageFilterScope(BaseModel):
    """页面级筛选：独立键空间，只影响当前页面全部模块。

    ``page_id`` 使用冻结目录的确定性路由（如 ``/b/overview``）。
    ``selected`` 映射维度 ID → 选中值 ID 列表；值 ID 必须在维度值列表中。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    page_id: str
    dimensions: tuple[FilterDimension, ...]
    selected: dict[str, tuple[str, ...]]

    @field_validator("page_id")
    @classmethod
    def _page_id_format(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("页面 ID 不能为空")
        if not normalized.startswith("/"):
            raise PortalFilterError(
                f"页面 ID 格式无效：{normalized}（必须以 / 开头）"
            )
        return assert_known_page_route(normalized)

    @field_validator("selected", mode="before")
    @classmethod
    def _check_duplicates_and_normalize(
        cls, value: dict[str, list[str]]
    ) -> dict[str, tuple[str, ...]]:
        normalized: dict[str, tuple[str, ...]] = {}
        for key, vals in value.items():
            sorted_vals = sorted(vals)
            # Check for duplicates before collapsing
            if len(sorted_vals) != len(set(sorted_vals)):
                seen: set[str] = set()
                for v in sorted_vals:
                    if v in seen:
                        raise PortalFilterError(
                            f"筛选值「{v}」在维度「{key}」中重复"
                        )
                    seen.add(v)
            normalized[key] = tuple(sorted_vals)
        return normalized

    @model_validator(mode="after")
    def _validate_selected_values(self) -> PageFilterScope:
        allowed = set(PAGE_DIMENSION_IDS)
        dim_ids = {d.id for d in self.dimensions} if self.dimensions else allowed
        dim_values: dict[str, set[str]] | None = None
        if self.dimensions:
            dim_values = {d.id: {v.id for v in d.values} for d in self.dimensions}
        for dim_id, selected_vals in self.selected.items():
            if dim_id not in allowed:
                raise PortalFilterError(f"未知页面筛选维度：{dim_id}")
            if self.dimensions and dim_id not in dim_ids:
                raise PortalFilterError(
                    f"筛选维度「{dim_id}」不适用于当前页面"
                )
            if dim_values is not None:
                for val_id in selected_vals:
                    if val_id not in dim_values.get(dim_id, set()):
                        raise PortalFilterError(
                            f"筛选值「{val_id}」不在维度「{dim_id}」的可选值中"
                        )
        return self

    def validate_values(self) -> None:
        """显式校验选中值存在于维度（可在外部调用）。"""
        self._validate_selected_values()


class ModuleFilterState(BaseModel):
    """模块级筛选：独立键空间，只影响相关模块。

    ``module_id`` 对应报告目录中定义的筛选 profile ID（如 ``b-efficacy``）。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    module_id: str
    dimensions: tuple[FilterDimension, ...]
    selected: dict[str, tuple[str, ...]]

    @field_validator("module_id")
    @classmethod
    def _module_id_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("模块 ID 不能为空")
        return assert_known_filter_profile(normalized)

    @field_validator("selected", mode="before")
    @classmethod
    def _check_duplicates_and_normalize(
        cls, value: dict[str, list[str]]
    ) -> dict[str, tuple[str, ...]]:
        normalized: dict[str, tuple[str, ...]] = {}
        for key, vals in value.items():
            sorted_vals = sorted(vals)
            if len(sorted_vals) != len(set(sorted_vals)):
                seen: set[str] = set()
                for v in sorted_vals:
                    if v in seen:
                        raise PortalFilterError(
                            f"模块筛选值「{v}」在维度「{key}」中重复"
                        )
                    seen.add(v)
            normalized[key] = tuple(sorted_vals)
        return normalized

    @model_validator(mode="after")
    def _validate_selected_values(self) -> ModuleFilterState:
        allowed = set(MODULE_DIMENSION_IDS)
        dim_ids = {d.id for d in self.dimensions} if self.dimensions else allowed
        dim_values: dict[str, set[str]] | None = None
        if self.dimensions:
            dim_values = {d.id: {v.id for v in d.values} for d in self.dimensions}
        for dim_id, selected_vals in self.selected.items():
            if dim_id not in allowed:
                raise PortalFilterError(f"未知模块筛选维度：{dim_id}")
            if self.dimensions and dim_id not in dim_ids:
                raise PortalFilterError(f"模块筛选维度「{dim_id}」不存在")
            if dim_values is not None:
                for val_id in selected_vals:
                    if val_id not in dim_values.get(dim_id, set()):
                        raise PortalFilterError(
                            f"模块筛选值「{val_id}」不在维度「{dim_id}」的可选值中"
                        )
        return self


class SortState(BaseModel):
    """排序状态：字段 + 方向；默认无排序（field=None）。

    方向只允许 ``asc`` 或 ``desc``。排序是可逆视图状态，不影响行身份。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str | None = None
    direction: Literal["asc", "desc"] = "asc"


class AnchorTrialState(BaseModel):
    """锚定试验选择：默认无锚定（trial_id=None）。

    锚定规则（§15.7）：按注册角色 → 阶段 → 披露成熟度 → 稳定试验 ID。
    不使用疗效数值或安全性发生率偏好。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    trial_id: str | None = None


class EvidenceSelection(BaseModel):
    """当前打开的数据依据与已固定条目；默认均无。

    ``open_id`` 为当前打开行；``selected_ids`` 为固定对照行（排序去重）。
    打开行可以同时被固定。未知/过期标识由网址层失败关闭并规范化，
    不在本模型放宽。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    selected_ids: tuple[str, ...] = ()
    open_id: str | None = None

    @field_validator("selected_ids")
    @classmethod
    def _no_duplicate_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise PortalFilterError("证据标识重复")
        return tuple(sorted(value))

    @field_validator("open_id")
    @classmethod
    def _open_id_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise PortalFilterError("打开的数据依据标识不能为空")
        return stripped


class PaginationState(BaseModel):
    """当前页码；默认第 1 页，从 1 开始。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    current_page: int = 1

    @field_validator("current_page")
    @classmethod
    def _page_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("页码必须 ≥ 1")
        return value


class FilterState(BaseModel):
    """顶层不可变筛选状态：页面级 + 模块级 + 全局状态。

    版本化（v1）确保 URL 可迁移。重置操作返回新实例，不修改原状态。
    - ``reset_page()``：仅清空页面级 selected，模块/排序/锚定/证据/分页不变
    - ``reset_module(module_id)``：仅清空指定模块 selected；未知模块中文拒绝
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: FilterVersion = FilterVersion.V1
    page: PageFilterScope
    modules: tuple[ModuleFilterState, ...] = ()
    sort: SortState = SortState()
    anchor: AnchorTrialState = AnchorTrialState()
    evidence: EvidenceSelection = EvidenceSelection()
    pagination: PaginationState = PaginationState()

    @model_validator(mode="after")
    def _unique_module_ids(self) -> FilterState:
        ids = [m.module_id for m in self.modules]
        if len(ids) != len(set(ids)):
            raise PortalFilterError("模块标识重复")
        return self

    def reset_page(self) -> FilterState:
        """重置页面级筛选：仅清空页面 selected，其他所有状态不变。"""
        return FilterState(
            version=self.version,
            page=PageFilterScope(
                page_id=self.page.page_id,
                dimensions=self.page.dimensions,
                selected={},
            ),
            modules=self.modules,
            sort=self.sort,
            anchor=self.anchor,
            evidence=self.evidence,
            pagination=self.pagination,
        )

    def reset_module(self, module_id: str) -> FilterState:
        """重置指定模块筛选：仅清空该模块 selected；未知模块失败关闭。"""
        new_modules = []
        found = False
        for mod in self.modules:
            if mod.module_id == module_id:
                found = True
                new_modules.append(
                    ModuleFilterState(
                        module_id=mod.module_id,
                        dimensions=mod.dimensions,
                        selected={},
                    )
                )
            else:
                new_modules.append(mod)
        if not found:
            raise PortalFilterError(f"未知模块：{module_id}")
        return FilterState(
            version=self.version,
            page=self.page,
            modules=tuple(new_modules),
            sort=self.sort,
            anchor=self.anchor,
            evidence=self.evidence,
            pagination=self.pagination,
        )


def dimension_applicability_reason(
    dimension: FilterDimension,
    *,
    page_id: str | None = None,
    module_id: str | None = None,
) -> str | None:
    """若不适用，返回中文禁用原因；适用则返回 None。从不使用「数据缺失」。"""
    if page_id is not None and not dimension.is_applicable_to_page(page_id):
        return dimension.disabled_reason_zh or INAPPLICABLE_REASON_ZH
    if module_id is not None and not dimension.is_applicable_to_module(module_id):
        return dimension.disabled_reason_zh or INAPPLICABLE_REASON_ZH
    return None


def select_view_rows(
    view: ReportViewModel,
    state: FilterState,
    *,
    module_id: str | None = None,
) -> FilteredRowSet:
    """按筛选状态从既有 ``ReportViewModel`` 行中选取子集。

    - 只返回视图内已有稳定行，不创建、不替换行身份
    - 不改变快照或页面责任
    - 空结果保持为空，不扩围
    - 同维度多选为 OR，跨维度为 AND
    - 无法投影到行身份字段的已选维度失败关闭（不得静默忽略）
    """
    from ci_workflow.reports.common.chart_specs import FilteredRowSet

    criteria: dict[str, tuple[str, ...]] = {
        k: v for k, v in state.page.selected.items() if v
    }
    if module_id is not None:
        for mod in state.modules:
            if mod.module_id == module_id:
                for k, v in mod.selected.items():
                    if v:
                        criteria[k] = v
                break
        else:
            raise PortalFilterError(f"未知模块：{module_id}")

    for dim_id in criteria:
        if dim_id not in _ROW_FIELD_BY_DIMENSION:
            raise PortalFilterError(
                f"筛选维度「{dim_id}」无法映射到报告行身份字段，不能投影"
            )

    selected_rows = []
    for row in view.rows:
        matched = True
        for dim_id, value_ids in criteria.items():
            field = _ROW_FIELD_BY_DIMENSION[dim_id]
            row_val = getattr(row, field, None)
            # OR within dimension
            if row_val is None or row_val not in value_ids:
                matched = False
                break
        if matched:
            selected_rows.append(row)

    return FilteredRowSet(view=view, rows=tuple(selected_rows))
