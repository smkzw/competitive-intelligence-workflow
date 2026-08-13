"""图表/表格输入联动、类型化图表注册、可比性分组与稳定小多图拆分。

Task 4.1 合同：一个模块只能接收一个不可变筛选行集，并确定性导出完全
相同的图表行 ID 与完整表行 ID 集合；调用方不能分别注入图表行或表格行。
空筛选保持为空，不扩宽作用域；行集摘要是格式覆盖投影中"图表等价"例外
证据的锚点。

Task 4.4 合同：九类图形类型化注册、可比性维度分组、稳定小多图拆分。
行只携带稳定科学身份，消费方只能经 ``report_snapshot_id`` 的锁定快照
取值，且任何层都无法替换行内容。披露缺失状态（not_reported 等）以非数值
状态保留，不得转 0。治疗/对照角色与分母为组内展示语境，不触发拆图。
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import OrderedDict
from enum import StrEnum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    model_validator,
)
from pydantic import (
    ValidationError as PydanticValidationError,
)

from ci_workflow.domain.enums import FactDisclosureState
from ci_workflow.reports.common.page_registry import PageRegistry
from ci_workflow.reports.common.view_state import (
    ReportRow,
    ReportViewModel,
    ViewStateBoundaryError,
    _assert_page_in_catalog,
)


class ChartTableBoundaryError(ValueError):
    """图表/表格行集边界拒绝：作用域扩宽、重复行或分别注入图表/表行。"""


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _sha256_hex(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


class FilteredRowSet(BaseModel):
    """不可变筛选行集：行必须属于绑定视图（不扩宽作用域），允许为空。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    view: ReportViewModel
    rows: tuple[ReportRow, ...]

    @property
    def row_set_digest(self) -> str:
        """按行 ID 排序的完整规范行模型摘要。

        行集摘要是"图表等价"例外证据的锚点，必须覆盖完整规范行内容：
        中文标签、披露状态、页面责任、锁定快照或任何身份字段变化都改变
        摘要，不能只哈希行 ID（行 ID 只由科学身份决定，会放过内容漂移）。
        行序不参与摘要；行必须是规范视图行本体（模型级全等，见模型校验）。
        """
        rows = sorted(self.rows, key=lambda row: row.row_id)
        payload = [row.model_dump(mode="json") for row in rows]
        return _sha256_hex({"kind": "row-set", "rows": payload})

    @model_validator(mode="after")
    def _rows_canonical_unique_within_view(self) -> FilteredRowSet:
        row_ids = [row.row_id for row in self.rows]
        if len(set(row_ids)) != len(row_ids):
            raise ValueError("筛选行集包含重复行，必须失败关闭")
        canonical = {row.row_id: row for row in self.view.rows}
        for row in self.rows:
            if row.row_id not in canonical:
                raise ValueError(f"筛选行集引用视图外行，不得扩宽作用域：{row.row_id}")
            if row != canonical[row.row_id]:
                raise ValueError(
                    "筛选行必须与规范视图行模型级全等（披露状态/中文标签/"
                    f"快照/页面漂移被拒绝）：{row.row_id}"
                )
        return self


class ChartTableModule(BaseModel):
    """一个模块 = 一个筛选行集；图表行与完整表行 ID 由同一行集确定性导出。

    模型只接受唯一 ``row_set`` 字段，调用方无法分别注入图表行或表格行；
    两个行 ID 集合按构造恒等，且都保留披露缺失行与空筛选。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    row_set: FilteredRowSet

    @property
    def chart_row_ids(self) -> tuple[str, ...]:
        return tuple(sorted(row.row_id for row in self.row_set.rows))

    @property
    def table_row_ids(self) -> tuple[str, ...]:
        return tuple(sorted(row.row_id for row in self.row_set.rows))


def _assert_catalog_authority(view: ReportViewModel) -> None:
    """行集边界内的目录权威检查：页面责任必须属于冻结目录。"""
    try:
        _assert_page_in_catalog(view, PageRegistry.load())
    except ViewStateBoundaryError as error:
        raise ChartTableBoundaryError(str(error)) from error


def validate_filtered_row_set_payload(raw: dict[str, Any]) -> FilteredRowSet:
    """生产行集验证器：作用域闭合、规范行全等、重复行与目录外页面责任失败关闭。"""
    try:
        model = FilteredRowSet.model_validate(raw)
    except PydanticValidationError as error:
        raise ChartTableBoundaryError(f"筛选行集模型校验失败：{error}") from error
    _assert_catalog_authority(model.view)
    return model


def validate_chart_table_module_payload(raw: dict[str, Any]) -> ChartTableModule:
    """生产模块验证器：只接受唯一行集，分别注入图表/表行被拒绝。"""
    try:
        model = ChartTableModule.model_validate(raw)
    except PydanticValidationError as error:
        raise ChartTableBoundaryError(f"图表表格模块模型校验失败：{error}") from error
    _assert_catalog_authority(model.row_set.view)
    return model


# ══════════════════════════════════════════════════════════════════════════════
# Task 4.4：类型化图表注册、可比性分组与稳定小多图拆分
# ══════════════════════════════════════════════════════════════════════════════

_KNOWN_DISCLOSURE_STATES: frozenset[str] = frozenset(state.value for state in FactDisclosureState)
_MISSING_DISCLOSURE_STATES: frozenset[str] = frozenset(
    {
        FactDisclosureState.NOT_REPORTED.value,
        FactDisclosureState.NOT_PUBLICLY_DISCLOSED.value,
        FactDisclosureState.NOT_APPLICABLE.value,
        FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE.value,
        FactDisclosureState.BELOW_REPORTING_THRESHOLD.value,
    }
)
_RENDERABLE_DISCLOSURE_STATES: frozenset[str] = frozenset(
    {
        FactDisclosureState.REPORTED_VALUE.value,
        FactDisclosureState.REPORTED_ZERO.value,
    }
)
_CHART_ANNOTATION_KEYS: frozenset[str] = frozenset({"_chart_type", "renderable"})


class ChartType(StrEnum):
    """九类临床数据图形类型。"""

    BAR = "bar"
    LINE = "line"
    FOREST = "forest"
    HEATMAP = "heatmap"
    BUBBLE = "bubble"
    SCATTER_INTERVAL = "scatter_interval"
    TIMELINE = "timeline"
    RADAR = "radar"
    STATUS_MATRIX = "status_matrix"


class ChartSpec(BaseModel):
    """单个图形类型的注册规格：必填字段与中文显示合同。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chart_type: str
    required_fields: tuple[str, ...]
    display_contract_zh: str

    @model_validator(mode="after")
    def _validate_chart_type(self) -> ChartSpec:
        try:
            ChartType(self.chart_type)
        except ValueError as err:
            raise ValueError(f"未知图形类型，不在注册范围：{self.chart_type}") from err
        return self

    @property
    def resolved_chart_type(self) -> ChartType:
        return ChartType(self.chart_type)

    @classmethod
    def for_type(cls, chart_type: ChartType) -> ChartSpec:
        if chart_type not in _CHART_REGISTRY:
            raise KeyError(f"未注册图形类型：{chart_type.value}")
        return _CHART_REGISTRY[chart_type]


_CHART_REGISTRY: OrderedDict[ChartType, ChartSpec] = OrderedDict()


def _register_defaults() -> None:
    specs = [
        ChartSpec(
            chart_type="bar",
            required_fields=("category", "value"),
            display_contract_zh="柱状图",
        ),
        ChartSpec(
            chart_type="line",
            required_fields=("time", "value"),
            display_contract_zh="折线图",
        ),
        ChartSpec(
            chart_type="forest",
            required_fields=("effect", "ci_lower", "ci_upper"),
            display_contract_zh="森林图",
        ),
        ChartSpec(
            chart_type="heatmap",
            required_fields=("event", "value_matrix"),
            display_contract_zh="热图",
        ),
        ChartSpec(
            chart_type="bubble",
            required_fields=("x_value", "y_value", "size"),
            display_contract_zh="气泡图",
        ),
        ChartSpec(
            chart_type="scatter_interval",
            required_fields=("center", "ci_lower"),
            display_contract_zh="点图/区间图",
        ),
        ChartSpec(
            chart_type="timeline",
            required_fields=("time", "status"),
            display_contract_zh="时间线",
        ),
        ChartSpec(
            chart_type="radar",
            required_fields=("dimensions", "scores"),
            display_contract_zh="雷达图",
        ),
        ChartSpec(
            chart_type="status_matrix",
            required_fields=("status", "coverage"),
            display_contract_zh="状态矩阵",
        ),
    ]
    for spec in specs:
        _CHART_REGISTRY[ChartType(spec.chart_type)] = spec


_register_defaults()


# 拆图维度：共轴可比性。control_role / denominator 仅为组内展示语境。
COMPARABILITY_DIMS: tuple[str, ...] = (
    "unit",
    "scale",
    "statistical_form",
    "direction",
    "time_window",
    "analysis_population",
)

DISPLAY_CONTEXT_DIMS: tuple[str, ...] = (
    "control_role",
    "denominator",
)

_DIM_LABELS_ZH: dict[str, str] = {
    "unit": "单位",
    "scale": "量表",
    "statistical_form": "统计形式",
    "direction": "方向",
    "time_window": "时间窗",
    "analysis_population": "分析人群",
    "control_role": "对照角色",
    "denominator": "分母",
}

# 标题展示映射：分组仍用内部键；title_zh 不得回显英枚举/snake_case。
_DIRECTION_TITLE_ZH: dict[str, str] = {
    "higher_better": "越高越有利",
    "lower_better": "越低越有利",
}
_ANALYSIS_POPULATION_TITLE_ZH: dict[str, str] = {
    "intention_to_treat": "意向治疗人群",
    "modified_intention_to_treat": "改良意向治疗人群",
    "per_protocol": "符合方案人群",
    # 常见缩写已是稳定展示标签（非 snake_case 内部键）
    "ITT": "ITT",
    "mITT": "mITT",
    "PP": "PP",
}
_DIM_VALUE_TITLE_ZH: dict[str, dict[str, str]] = {
    "direction": _DIRECTION_TITLE_ZH,
    "analysis_population": _ANALYSIS_POPULATION_TITLE_ZH,
}
_SNAKE_CASE_TOKEN = re.compile(r"(?<![A-Za-z0-9_])[a-z]+(?:_[a-z0-9]+)+(?![A-Za-z0-9_])")


class SmallMultipleGroup(BaseModel):
    """一个可比性小多图组：共享拆图维度的一组行。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    title_zh: str
    split_dims: tuple[str, ...]
    rows: tuple[dict[str, Any], ...]


def register_chart_type(type_name: str, spec: ChartSpec) -> None:
    """注册图形类型；只接受 ChartType 枚举内的值。"""
    try:
        chart_type = ChartType(type_name)
    except ValueError as err:
        raise ValueError(f"未知图形类型，不在注册范围：{type_name}") from err
    if ChartType(spec.chart_type) != chart_type:
        raise ValueError(
            f"注册规格与类型名不一致：type_name={type_name}，spec.chart_type={spec.chart_type}"
        )
    _CHART_REGISTRY[chart_type] = spec


def validate_chart_input_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """统一锁定快照入口：row_id 唯一非空、快照一致、披露状态已知。

    返回浅拷贝列表；不把任意前端字典升格为科学真源——仅执行入口闭合校验。
    Task 4.1 ``FilteredRowSet`` 的不扩围语义仍由视图模型强制。
    """
    if not rows:
        return []

    seen_ids: set[str] = set()
    snapshot_id: str | None = None
    validated: list[dict[str, Any]] = []

    for index, row in enumerate(rows):
        raw_id = row.get("row_id")
        if raw_id is None or not str(raw_id).strip():
            raise ValueError(f"row_id 缺失或为空（索引 {index}）")
        row_id = str(raw_id).strip()
        if row_id in seen_ids:
            raise ValueError(f"重复 row_id：{row_id}")
        seen_ids.add(row_id)

        raw_snapshot = row.get("report_snapshot_id")
        if raw_snapshot is None or not str(raw_snapshot).strip():
            raise ValueError(f"report_snapshot_id 缺失或为空（row_id={row_id}）")
        snapshot = str(raw_snapshot).strip()
        if snapshot_id is None:
            snapshot_id = snapshot
        elif snapshot != snapshot_id:
            raise ValueError(
                f"混合快照：report_snapshot_id 不一致（期望 {snapshot_id}，"
                f"实际 {snapshot}，row_id={row_id}）"
            )

        disclosure = row.get("disclosure_state")
        if disclosure not in _KNOWN_DISCLOSURE_STATES:
            raise ValueError(
                f"未知 disclosure_state（披露状态不在已知集合）：{disclosure!r}（row_id={row_id}）"
            )

        validated.append(dict(row))

    return validated


def _field_missing(row: dict[str, Any], field: str) -> bool:
    if field not in row:
        return True
    value = row[field]
    return value is None or value == ""


def _as_number(value: Any, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} 必须为数值")
    return float(value)


def _validate_renderable_fields(row: dict[str, Any], chart_type: ChartType) -> None:
    """已披露行：必需字段存在 + 最小类型/范围校验。"""
    spec = ChartSpec.for_type(chart_type)
    missing = [f for f in spec.required_fields if _field_missing(row, f)]
    if missing:
        raise ValueError(f"缺少必需字段（{chart_type.value}）：{', '.join(missing)}")

    if chart_type is ChartType.FOREST:
        lower = _as_number(row["ci_lower"], label="ci_lower")
        upper = _as_number(row["ci_upper"], label="ci_upper")
        if lower > upper:
            raise ValueError("森林图置信区间上下限次序错误：ci_lower 不得大于 ci_upper")

    if chart_type is ChartType.BUBBLE:
        size = _as_number(row["size"], label="气泡图 size")
        if size <= 0:
            raise ValueError("气泡图 size 必须 > 0")

    if chart_type is ChartType.RADAR:
        dimensions = row["dimensions"]
        scores = row["scores"]
        if not isinstance(dimensions, (list, tuple)) or not isinstance(scores, (list, tuple)):
            raise ValueError("雷达图 dimensions 与 scores 必须为序列")
        if len(dimensions) != len(scores):
            raise ValueError("雷达图 dimensions 与 scores 长度不一致")


def resolve_chart_type(
    rows: list[dict[str, Any]],
    chart_type: ChartType | str,
) -> list[dict[str, Any]]:
    """解析图形类型并标注可渲染性；缺失状态不得转 0。

    - 先经 ``validate_chart_input_rows`` 锁定快照入口。
    - 已披露行缺必需字段或范围非法 → 失败关闭。
    - 缺失/未公开行保留，``renderable=False``，不生成数值点。
    """
    if isinstance(chart_type, str):
        try:
            chart_type = ChartType(chart_type)
        except ValueError as err:
            raise KeyError(f"未知图形类型，未注册：{chart_type}") from err
    if chart_type not in _CHART_REGISTRY:
        raise KeyError(f"未注册图形类型：{chart_type.value}")

    validated = validate_chart_input_rows(rows)
    result: list[dict[str, Any]] = []
    for row in validated:
        annotated = dict(row)
        annotated["_chart_type"] = chart_type.value
        disclosure = str(annotated.get("disclosure_state", ""))

        if disclosure in _MISSING_DISCLOSURE_STATES:
            for key in ("value", "display_value", "numeric_value"):
                if key in annotated:
                    annotated[key] = None
            annotated["renderable"] = False
        elif disclosure in _RENDERABLE_DISCLOSURE_STATES:
            _validate_renderable_fields(annotated, chart_type)
            annotated["renderable"] = True
        else:
            annotated["renderable"] = False

        result.append(annotated)
    return result


def _normalize_dim_value(dim: str, value: Any) -> str:
    """规范化可比性维度取值；时间窗进入无空白规范化桶。"""
    text = "" if value is None else str(value).strip()
    if dim == "time_window":
        return "".join(text.split())
    return text


def _display_dim_value(dim: str, normalized: str) -> str:
    """将拆图维度取值映射为用户可见中文；未知 snake_case 失败关闭。"""
    mapping = _DIM_VALUE_TITLE_ZH.get(dim, {})
    if normalized in mapping:
        return mapping[normalized]
    if _SNAKE_CASE_TOKEN.search(normalized):
        label = _DIM_LABELS_ZH.get(dim, dim)
        raise ValueError(f"未知/未映射的{label}值，失败关闭（不得写入标题）：{normalized}")
    return normalized


def _assert_comparability_values_displayable(row: dict[str, Any]) -> None:
    """拆分前校验：可比维度取值均可安全进入中文标题。"""
    for dim in COMPARABILITY_DIMS:
        _display_dim_value(dim, _normalize_dim_value(dim, row.get(dim)))


def _group_key(row: dict[str, Any]) -> tuple[str, ...]:
    return tuple(_normalize_dim_value(dim, row.get(dim)) for dim in COMPARABILITY_DIMS)


def _stable_rows(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    """组内按 row_id 稳定排序；保留原始 dict 引用，不改写内容。"""
    return tuple(sorted(rows, key=lambda row: str(row.get("row_id", ""))))


def _title_for_group(
    varying_dim_indices: tuple[int, ...],
    key: tuple[str, ...],
) -> str:
    if not varying_dim_indices:
        return "全部指标"
    parts: list[str] = []
    for i in varying_dim_indices:
        dim = COMPARABILITY_DIMS[i]
        label = _DIM_LABELS_ZH.get(dim, dim)
        display = _display_dim_value(dim, key[i])
        parts.append(f"{label}：{display}")
    return "；".join(parts)


def split_compatible_groups(
    rows: list[dict[str, Any]],
) -> list[SmallMultipleGroup]:
    """按拆图维度拆分为小多图；展示语境维度不参与拆分。"""
    if not rows:
        return []

    validated = validate_chart_input_rows(rows)
    for row in validated:
        _assert_comparability_values_displayable(row)

    groups_map: OrderedDict[tuple[str, ...], list[dict[str, Any]]] = OrderedDict()
    for row in validated:
        key = _group_key(row)
        groups_map.setdefault(key, []).append(row)

    if len(groups_map) == 1:
        key = next(iter(groups_map))
        return [
            SmallMultipleGroup(
                title_zh="全部指标",
                split_dims=(),
                rows=_stable_rows(groups_map[key]),
            )
        ]

    all_keys = list(groups_map.keys())
    varying_dims = [
        i for i, _dim in enumerate(COMPARABILITY_DIMS) if len({k[i] for k in all_keys}) > 1
    ]
    varying_indices = tuple(varying_dims)
    split_dims = tuple(COMPARABILITY_DIMS[i] for i in varying_indices)

    result: list[SmallMultipleGroup] = []
    for key in sorted(groups_map.keys()):
        result.append(
            SmallMultipleGroup(
                title_zh=_title_for_group(varying_indices, key),
                split_dims=split_dims,
                rows=_stable_rows(groups_map[key]),
            )
        )
    return result


def _scientific_row_digest(row: dict[str, Any]) -> str:
    """科学行规范摘要：排除图形注解字段。"""
    payload = {key: value for key, value in row.items() if key not in _CHART_ANNOTATION_KEYS}
    return _sha256_hex(payload)


def validate_all_rows_covered(
    original_rows: list[dict[str, Any]],
    groups: list[SmallMultipleGroup],
) -> None:
    """验证拆分覆盖：原始 row_id 唯一、恰好一次、内容未被改写。"""
    original_ids = [row.get("row_id") for row in original_rows]
    if len(original_ids) != len(set(original_ids)):
        raise ValueError("原始行存在重复 row_id，覆盖校验失败关闭")

    original_by_id: dict[Any, dict[str, Any]] = {row.get("row_id"): row for row in original_rows}

    group_ids: list[Any] = []
    for group in groups:
        for row in group.rows:
            rid = row.get("row_id")
            group_ids.append(rid)
            if rid not in original_by_id:
                raise ValueError(f"行覆盖不一致：拆分结果含未知 row_id={rid}")
            if _scientific_row_digest(row) != _scientific_row_digest(original_by_id[rid]):
                raise ValueError(f"组内内容改写被拒绝：row_id={rid} 与原始行规范摘要/全等不一致")

    if len(group_ids) != len(original_ids):
        raise ValueError(
            f"行覆盖不一致：原始 {len(original_ids)} 行，拆分后 {len(group_ids)} 行（丢失或重复）"
        )

    if set(group_ids) != set(original_ids):
        lost = set(original_ids) - set(group_ids)
        extra = set(group_ids) - set(original_ids)
        parts: list[str] = []
        if lost:
            parts.append(f"丢失：{lost}")
        if extra:
            parts.append(f"重复：{extra}")
        raise ValueError(f"行覆盖不一致：{'; '.join(parts)}")

    if len(group_ids) != len(set(group_ids)):
        raise ValueError("行覆盖不一致：拆分结果存在重复 row_id")
