"""Task 4.5 规范证据视图：绑定稳定 row_id、单一锁定快照、来源版本与
精确 locator 的不可变证据投影。

边界（与 ``view_state`` / ``chart_specs`` 同源的最小证据合同）：

- 每条证据视图嵌入 ``ReportRow`` 本体：稳定 ``row_id``、单一锁定快照与
  页面责任由行身份保证，任何层都不能替换行内容或换取其他快照；
- 产品、试验、组别、终点/事件/设计要素与全部观察值都由本模型携带，
  展示层只能渲染本模型字段，禁止从展示层拼出临床事实；
- 观察字段（量表/时间点/值/阈值/单位/分子/分母与基线/完成情况扩展字段）
  只允许"确定值 XOR 互斥状态"：不适用、尚未公开、来源未列示、技术暂不可用。
  状态互斥且由本模块提供中文标签，不得空白，也不得把缺失当作 0（真零由
  ``REPORTED_ZERO`` 显式表达）；
- 披露状态与值严格一致：未报告/未公开/不适用不得携带确定值，已报告必须
  携带确定值，已报告零值必须是数值零；
- 简短原文与原因原文仅在输入已有且允许时携带，逐字保留，与规范化说明/
  规范原因分离存储，原文不被规范化文本覆盖；
- 冲突与历史版本各自绑定来源版本与精确 locator；来源定位未知时不生成
  伪链接或伪定位（``EvidenceLocator`` 至少一个锚点，否则失败关闭）；
- 固定对照集合必须同报告类型、同锁定快照、同页面责任且行唯一；观察类型
  必须匹配冻结目录页面声明的证据抽屉配置。
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any, Literal, Self

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
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.reports.common.page_registry import PageRegistry
from ci_workflow.reports.common.view_state import ReportRow

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


class EvidenceFieldState(StrEnum):
    """观察字段的互斥缺失状态：不得空白，也不得把缺失当作 0。"""

    NOT_APPLICABLE = "not_applicable"
    NOT_YET_DISCLOSED = "not_yet_disclosed"
    SOURCE_NOT_LISTED = "source_not_listed"
    TECHNICALLY_UNAVAILABLE = "technically_unavailable"
    USER_CLEARED = "user_cleared"


EVIDENCE_FIELD_STATE_LABELS_ZH: dict[EvidenceFieldState, str] = {
    EvidenceFieldState.NOT_APPLICABLE: "不适用",
    EvidenceFieldState.NOT_YET_DISCLOSED: "尚未公开",
    EvidenceFieldState.SOURCE_NOT_LISTED: "来源未列示",
    EvidenceFieldState.TECHNICALLY_UNAVAILABLE: "技术暂不可用",
    EvidenceFieldState.USER_CLEARED: "用户清除，待重新核实",
}


class EvidenceObservationKind(StrEnum):
    """观察类型：通用临床事实或 §15.5 的基线/完成情况扩展观察。"""

    GENERAL = "general"
    BASELINE_OBSERVATION = "baseline_observation"
    TRIAL_DISPOSITION_OBSERVATION = "trial_disposition_observation"


class OriginalTextStatus(StrEnum):
    """简短原文/原因原文的携带状态：仅在输入已有且允许时提供。"""

    PROVIDED = "provided"
    NOT_PROVIDED = "not_provided"
    NOT_PERMITTED = "not_permitted"


MUTUAL_EXCLUSION_MARKS_ZH: frozenset[str] = frozenset({"互斥且穷尽", "互斥但未穷尽", "非互斥"})

_EXTENSION_KINDS: frozenset[EvidenceObservationKind] = frozenset(
    {
        EvidenceObservationKind.BASELINE_OBSERVATION,
        EvidenceObservationKind.TRIAL_DISPOSITION_OBSERVATION,
    }
)

# 冻结目录页面抽屉配置 → 观察类型：静态页面必须一致，未知配置失败关闭。
_PROFILE_KINDS: dict[str, EvidenceObservationKind] = {
    "common-clinical": EvidenceObservationKind.GENERAL,
    "common-regulatory": EvidenceObservationKind.GENERAL,
    "common-corporate": EvidenceObservationKind.GENERAL,
    "common-patent": EvidenceObservationKind.GENERAL,
    "design-fact": EvidenceObservationKind.GENERAL,
    "baseline-observation": EvidenceObservationKind.BASELINE_OBSERVATION,
    "trial-disposition": EvidenceObservationKind.TRIAL_DISPOSITION_OBSERVATION,
}

# 基线/完成情况扩展字段族：扩展观察全部必填，通用观察必须全部为空。
_EXTENSION_FIELDS: tuple[str, ...] = (
    "canonical_variable_family",
    "source_field_name",
    "source_field_definition",
    "statistical_form_or_measurement_object",
    "scale_version_direction",
    "denominator_role",
    "time_window_or_baseline_definition",
    "canonical_reason",
    "mutual_exclusion_exhaustiveness",
    "compatibility_rule",
    "difference_label",
)

# 不得携带确定值的披露状态：缺失永远不能表现为数值（更不能表现为 0）。
_NON_CONCRETE_VALUE_STATES: frozenset[FactDisclosureState] = frozenset(
    {
        FactDisclosureState.NOT_REPORTED,
        FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
        FactDisclosureState.NOT_APPLICABLE,
        FactDisclosureState.USER_CLEARED,
    }
)


class EvidenceViewBoundaryError(ValueError):
    """证据视图边界拒绝：跨快照/跨页面、身份漂移、非法状态或目录外页面。"""


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("文本不能为空")
    return normalized


def _has_chinese(value: str) -> bool:
    return _CJK_RE.search(value) is not None


class EvidenceField(BaseModel):
    """观察字段：确定值或互斥状态恰好其一；不得空白或当作 0。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    value: str | None = None
    state: EvidenceFieldState | None = None

    @field_validator("value")
    @classmethod
    def _value_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _text(value)

    @model_validator(mode="after")
    def _value_or_state_exactly_one(self) -> Self:
        if (self.value is None) == (self.state is None):
            raise ValueError("观察字段必须恰好是确定值或互斥状态之一，不得空白")
        return self


class EvidenceConflict(BaseModel):
    """一条来源可定位的冲突：绑定冲突方来源版本、冲突取值与精确定位。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    conflicting_source_version_id: str
    conflicting_value_zh: str
    conflict_note_zh: str
    locator: EvidenceLocator

    @field_validator("conflicting_source_version_id", "conflicting_value_zh")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("conflict_note_zh")
    @classmethod
    def _note_is_chinese(cls, value: str) -> str:
        normalized = _text(value)
        if not _has_chinese(normalized):
            raise ValueError("冲突说明必须为原生中文")
        return normalized


class EvidenceHistoricalVersion(BaseModel):
    """一个被取代的历史版本：旧值/旧状态与取代说明，仅保留不覆盖。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_version_id: str
    previous_value: EvidenceField
    supersession_note_zh: str
    locator: EvidenceLocator

    @field_validator("source_version_id")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("supersession_note_zh")
    @classmethod
    def _note_is_chinese(cls, value: str) -> str:
        normalized = _text(value)
        if not _has_chinese(normalized):
            raise ValueError("取代说明必须为原生中文")
        return normalized


class UserEditDisclosure(BaseModel):
    """User-authored current value kept separate from immutable source evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    review_state: Literal["user_modified"] = "user_modified"
    status_label_zh: Literal["用户修订，未独立复核", "用户清除，待重新核实"] = (
        "用户修订，未独立复核"
    )
    fact_id: str
    fact_version_id: str
    request_id: str
    revision: int
    primary_fragment_id: str
    source_version_id: str
    source_locator: dict[str, Any]
    current_value: str
    original_value: str
    basis: str
    saved_by: str
    saved_at: str
    operation: Literal["save", "undo"]

    @field_validator(
        "fact_id",
        "fact_version_id",
        "request_id",
        "primary_fragment_id",
        "source_version_id",
        "current_value",
        "original_value",
        "basis",
        "saved_by",
        "saved_at",
    )
    @classmethod
    def _required_user_edit_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("用户修订披露字段不得为空")
        return value

    @model_validator(mode="after")
    def _locator_is_structured(self) -> Self:
        if not self.source_locator:
            raise ValueError("用户修订必须保留结构化原来源定位")
        return self


class EvidenceView(BaseModel):
    """一条规范证据：稳定 row_id、单一快照、可核验来源或显式待核状态。

    临床事实由本模型携带并与披露状态交叉校验；基线/完成情况观察必须携带
    完整扩展字段族，通用观察不得携带扩展字段。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    report_kind: ReportKind
    observation_kind: EvidenceObservationKind
    row: ReportRow

    product_zh: str
    trial_zh: str
    group_zh: EvidenceField
    element_zh: str

    scale: EvidenceField
    timepoint: EvidenceField
    value: EvidenceField
    threshold: EvidenceField
    unit: EvidenceField
    numerator: EvidenceField
    denominator: EvidenceField

    source_trace_state: Literal["located", "unverified"] = "located"
    source_version_id: str | None
    source_version_label_zh: str
    locator: EvidenceLocator | None

    explanation: EvidenceField
    original_text: str | None = None
    original_text_status: OriginalTextStatus = OriginalTextStatus.NOT_PROVIDED
    user_edit: UserEditDisclosure | None = None

    conflicts: tuple[EvidenceConflict, ...] = ()
    historical_versions: tuple[EvidenceHistoricalVersion, ...] = ()

    canonical_variable_family: EvidenceField | None = None
    source_field_name: EvidenceField | None = None
    source_field_definition: EvidenceField | None = None
    statistical_form_or_measurement_object: EvidenceField | None = None
    scale_version_direction: EvidenceField | None = None
    denominator_role: EvidenceField | None = None
    time_window_or_baseline_definition: EvidenceField | None = None
    reason_original_text: str | None = None
    canonical_reason: EvidenceField | None = None
    mutual_exclusion_exhaustiveness: EvidenceField | None = None
    compatibility_rule: EvidenceField | None = None
    difference_label: EvidenceField | None = None

    @field_validator("source_version_id")
    @classmethod
    def _source_id_not_blank_when_present(cls, value: str | None) -> str | None:
        return None if value is None else _text(value)

    @field_validator("product_zh", "trial_zh", "element_zh", "source_version_label_zh")
    @classmethod
    def _display_name_is_chinese(cls, value: str) -> str:
        normalized = _text(value)
        if not _has_chinese(normalized):
            raise ValueError("用户可见显示名必须为原生中文")
        return normalized

    @field_validator("original_text", "reason_original_text")
    @classmethod
    def _original_text_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("原文不得空白")
        return value  # 原文逐字保留，不做空白折叠

    @model_validator(mode="after")
    def _extension_and_disclosure_integrity(self) -> Self:
        if self.source_trace_state == "located":
            if self.source_version_id is None or self.locator is None:
                raise ValueError("已定位来源必须同时包含来源版本与精确定位")
        elif (
            self.source_version_id is not None
            or self.locator is not None
            or self.original_text is not None
            or self.original_text_status is OriginalTextStatus.PROVIDED
        ):
            raise ValueError("来源待核不得携带来源版本、定位或原文引文")
        is_extension = self.observation_kind in _EXTENSION_KINDS
        present = [name for name in _EXTENSION_FIELDS if getattr(self, name) is not None]
        if is_extension:
            missing = [name for name in _EXTENSION_FIELDS if getattr(self, name) is None]
            if missing:
                raise ValueError("基线/完成情况观察必须携带完整扩展字段族：" + "、".join(missing))
        elif present:
            raise ValueError("通用观察不得携带基线/完成情况扩展字段：" + "、".join(present))

        disclosure = self.row.disclosure_state
        if disclosure is FactDisclosureState.REPORTED_VALUE:
            if self.value.value is None:
                raise ValueError("已报告值的证据视图必须携带确定值")
        elif disclosure is FactDisclosureState.REPORTED_ZERO:
            if self.value.value is None:
                raise ValueError("已报告零值的证据视图必须携带确定值")
            try:
                numeric = float(self.value.value)
            except ValueError:
                raise ValueError("已报告零值的规范数值必须为零") from None
            if numeric != 0:
                raise ValueError("已报告零值的规范数值必须为零")
        if disclosure in _NON_CONCRETE_VALUE_STATES and self.value.value is not None:
            raise ValueError("未报告、未公开或不适用状态不得携带确定值，更不能把缺失当作 0")

        if self.original_text_status is OriginalTextStatus.PROVIDED:
            if self.original_text is None:
                raise ValueError("原文状态为已提供时必须携带原文")
        elif self.original_text is not None:
            raise ValueError("原文仅在输入已有且允许时携带，不得附带原文")

        if self.group_zh.value is not None and not _has_chinese(self.group_zh.value):
            raise ValueError("组别显示名必须为原生中文")
        for name in ("explanation", "canonical_reason"):
            field = getattr(self, name)
            if field is not None and field.value is not None and not _has_chinese(field.value):
                raise ValueError(f"{name} 必须为原生中文")
        mark = self.mutual_exclusion_exhaustiveness
        if (
            mark is not None
            and mark.value is not None
            and mark.value not in MUTUAL_EXCLUSION_MARKS_ZH
        ):
            raise ValueError("互斥穷尽标记必须是已知中文标记或互斥状态")
        return self


class EvidenceViewSet(BaseModel):
    """同页固定对照集合：全部证据视图绑定同一锁定快照与页面责任，行唯一。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    report_kind: ReportKind
    report_snapshot_id: str
    page_responsibility_id: str
    views: tuple[EvidenceView, ...]

    @field_validator("report_snapshot_id", "page_responsibility_id")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _text(value)

    @model_validator(mode="after")
    def _views_bound_and_unique(self) -> Self:
        row_ids = [view.row.row_id for view in self.views]
        if len(set(row_ids)) != len(row_ids):
            raise ValueError("固定对照集合包含重复行，必须失败关闭")
        for view in self.views:
            if view.report_kind is not self.report_kind:
                raise ValueError("固定对照集合混用报告类型，必须失败关闭")
            if view.row.report_snapshot_id != self.report_snapshot_id:
                raise ValueError("固定对照集合混用多个锁定快照，必须失败关闭")
            if view.row.page_responsibility_id != self.page_responsibility_id:
                raise ValueError("固定对照集合混用多个页面责任，必须失败关闭")
        return self


def _assert_catalog_authority(view: EvidenceView, registry: PageRegistry) -> None:
    """页面责任必须属于冻结目录；静态页的观察类型必须匹配抽屉配置。"""
    known = registry.page_responsibility_ids(view.report_kind)
    if view.row.page_responsibility_id not in known:
        raise EvidenceViewBoundaryError(
            f"页面责任不在冻结目录中：{view.row.page_responsibility_id}"
            f"（{view.report_kind.value} 目录外，未知责任必须失败关闭）"
        )
    catalog = registry.catalog(view.report_kind)
    for page in catalog.pages:
        if page.id == view.row.page_responsibility_id:
            expected = _PROFILE_KINDS.get(page.evidence_drawer_profile)
            if expected is None:
                raise EvidenceViewBoundaryError(
                    f"页面证据抽屉配置未知：{page.evidence_drawer_profile}"
                    f"（{page.id}，未知配置必须失败关闭）"
                )
            if view.observation_kind is not expected:
                raise EvidenceViewBoundaryError(
                    f"观察类型与页面证据抽屉配置不符：{view.observation_kind.value}"
                    f"（页面 {page.id} 声明 {page.evidence_drawer_profile}，"
                    "必须失败关闭）"
                )
            return


def validate_evidence_view_payload(raw: dict[str, Any]) -> EvidenceView:
    """生产证据视图验证器：模型校验 + 冻结目录页面责任 + 抽屉配置一致。

    页面责任权威：始终加载冻结 PageRegistry（源码树或包内数据布局），
    不接受调用方注入注册表。
    """
    try:
        view = EvidenceView.model_validate(raw)
    except PydanticValidationError as error:
        raise EvidenceViewBoundaryError(f"证据视图模型校验失败：{error}") from error
    _assert_catalog_authority(view, PageRegistry.load())
    return view


def validate_evidence_view_set_payload(raw: dict[str, Any]) -> EvidenceViewSet:
    """生产固定对照集合验证器：同快照、同页面、行唯一 + 冻结目录权威。"""
    try:
        view_set = EvidenceViewSet.model_validate(raw)
    except PydanticValidationError as error:
        raise EvidenceViewBoundaryError(f"固定对照集合模型校验失败：{error}") from error
    registry = PageRegistry.load()
    for view in view_set.views:
        _assert_catalog_authority(view, registry)
    return view_set
