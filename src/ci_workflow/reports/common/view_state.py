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
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
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
