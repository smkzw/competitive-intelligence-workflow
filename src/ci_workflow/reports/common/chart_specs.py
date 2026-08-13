"""Task 4.1 图表/表格输入联动与稳定行集合同。

本模块只声明 Task 4.1 所需的最小合同：一个模块只能接收一个不可变筛选
行集，并确定性导出完全相同的图表行 ID 与完整表行 ID 集合；调用方不能
分别注入图表行或表格行。图表类型兼容与拆分逻辑属于 Task 4.4，不在本
模块实现。空筛选保持为空，不扩宽作用域；行集摘要是格式覆盖投影中
"图表等价"例外证据的锚点。

行集必须是规范视图行的本体：筛选行只允许是视图行的子集/重排/空，任何
与规范行不一致的重建（披露状态、中文标签、快照或页面漂移）都被拒绝。
这机械绑定取值查找边界——行只携带稳定科学身份，消费方只能经
``report_snapshot_id`` 的锁定快照取值，且任何层都无法替换行内容。
生产验证器还强制嵌入视图的页面责任属于冻结目录。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    model_validator,
)
from pydantic import (
    ValidationError as PydanticValidationError,
)

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
            value, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
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
