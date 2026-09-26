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
- 精确定位只承认字段、页、表、行、列、段落锚点：仅链接或仅章节不算定位，
  ``$.`` 与 ``$.resultsSection`` 一类粗 JSON 容器也不算精确字段路径；
- 任何 locator 字段都不得携带本机路径形状（绝对路径、家目录、UNC、盘符、
  ``file:``、上跳相对路径），脏字段被拒绝而同一位置对象的其他好锚点保留；
- ``located`` 必须同时具备来源版本、精确非本机锚点与（B/C 类）逐字原文；
  ``unverified`` 不得残留来源版本、定位、原文引文、冲突、历史版本或原因原文；
- 固定对照集合必须同报告类型、同锁定快照、同页面责任且行唯一；观察类型
  必须匹配冻结目录页面声明的证据抽屉配置。
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
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

# B/C 类的已定位必须同时携带逐字原文；A 调用方的页/表/段锚点继续兼容
_TRACE_VERBATIM_TEXT_KINDS: frozenset[ReportKind] = frozenset({ReportKind.B, ReportKind.C})

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


# ─── 来源定位形状：精确非本机锚点（共享实现，模型与渲染层同源） ──────────────

# 本机路径前缀：绝对路径、家目录、UNC、Windows 盘符、file:、上跳/当前相对路径
_LOCAL_PATH_PREFIX_RE = re.compile(
    r"^(?:/|~[/\\]|\\\\|//|[A-Za-z]:[\\/]|file:|\.\.?[/\\])",
    re.IGNORECASE,
)
# 形如目录 + 本机文件名的相对路径（远程 http(s)/ftp 链接先行放行）
_LOCAL_FILE_TAIL_RE = re.compile(
    r"[\\/][^\\/\s]+\.(?:json|jsonl|pdf|csv|tsv|xlsx?|xml|html?|txt|docx?|zip|png|jpe?g)$",
    re.IGNORECASE,
)
_REMOTE_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")
# 粗 JSON 容器：``$``、``$.``、``.``；单个顶层段（``$.resultsSection``）不算精确路径
_COARSE_FIELD_PATH_RE = re.compile(r"^\$?\.?$")
# 裸本机文件名（``internal.json``）不是来源字段路径
_BARE_FILENAME_RE = re.compile(
    r"^[^./\\\s]+\.(?:json|jsonl|pdf|csv|tsv|xlsx?|xml|html?|txt|docx?|zip)$",
    re.IGNORECASE,
)

# 精确定位锚点字段：链接与章节不算锚点，粗容器字段路径不算精确路径
LOCATOR_ANCHOR_FIELDS: tuple[str, ...] = ("page", "table", "row", "column", "paragraph")
_LOCATOR_STRING_FIELDS: tuple[str, ...] = (
    "field_path",
    "heading",
    "table",
    "row",
    "column",
    "paragraph",
    "url",
)
_LOCATOR_VISIBLE_FIELDS: tuple[str, ...] = ("document_role", *_LOCATOR_STRING_FIELDS, "page")


def is_local_path_shape(value: str) -> bool:
    """判断定位文本是否为本机路径形状（绝对、家目录、UNC、盘符、file:、相对）。"""
    text = value.strip()
    if not text:
        return False
    if _LOCAL_PATH_PREFIX_RE.match(text):
        return True
    if _REMOTE_SCHEME_RE.match(text):
        return False
    return _LOCAL_FILE_TAIL_RE.search(text) is not None


def field_path_is_precise(field_path: str) -> bool:
    """字段路径是否精确到具体测量/字段：粗容器与裸文件名不算精确。"""
    path = field_path.strip()
    if not path:
        return False
    if _COARSE_FIELD_PATH_RE.match(path):
        return False
    if _BARE_FILENAME_RE.match(path):
        return False
    if "[" in path:
        return True
    segments = [segment for segment in path.lstrip("$").strip(".").split(".") if segment]
    return len(segments) >= 2


def precise_locator_anchor(locator: EvidenceLocator | None) -> str | None:
    """返回第一个精确锚点字段名；仅链接/仅章节/粗容器一律返回 None。"""
    if locator is None:
        return None
    if locator.field_path is not None and field_path_is_precise(locator.field_path):
        return "field_path"
    for name in LOCATOR_ANCHOR_FIELDS:
        if getattr(locator, name) is not None:
            return name
    return None


def locator_local_path_fields(locator: EvidenceLocator) -> tuple[str, ...]:
    """列出携带本机路径形状的 locator 字段（用于拒绝或去除脏字段）。"""
    dirty: list[str] = []
    for name in _LOCATOR_STRING_FIELDS:
        value = getattr(locator, name)
        if isinstance(value, str) and is_local_path_shape(value):
            dirty.append(name)
    return tuple(dirty)


def clean_evidence_locator(candidate: object) -> EvidenceLocator | None:
    """去除本机路径字段后仍可用的定位；无任何可用锚点返回 None。

    只清除脏字段，不因某个字段携带本机路径而丢弃同一位置对象里的好锚点。
    """
    if isinstance(candidate, EvidenceLocator):
        locator = candidate
    elif isinstance(candidate, Mapping):
        try:
            locator = EvidenceLocator.model_validate(candidate)
        except (TypeError, ValueError):
            return None
    else:
        return None
    visible: dict[str, Any] = {}
    for name in _LOCATOR_VISIBLE_FIELDS:
        value = getattr(locator, name)
        if value is None:
            continue
        if isinstance(value, str) and is_local_path_shape(value):
            continue
        visible[name] = value
    visible_anchor_names = (*LOCATOR_ANCHOR_FIELDS, "field_path", "heading", "url")
    if not any(visible.get(name) is not None for name in visible_anchor_names):
        return None
    try:
        return EvidenceLocator.model_validate(visible)
    except ValueError:
        return None


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

    # 缺省待核（独立会商 R24-25）：已定位必须显式声明，不得靠默认值晋级
    source_trace_state: Literal["located", "unverified"] = "unverified"
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
        assert_evidence_trace_contract(self)
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


def assert_evidence_trace_contract(view: EvidenceView) -> None:
    """来源追溯合同的唯一实现：模型校验与 B/C 序列化边界共用同一判定。

    - ``located`` 必须同时具备来源版本、精确非本机锚点；B/C 类还必须携带
      逐字原文（``provided``）。仅链接、仅章节、粗 JSON 容器不构成精确锚点；
    - ``unverified`` 不得残留来源版本、定位、原文引文、冲突、历史版本或原因原文。
    """
    if view.source_trace_state == "located":
        if view.source_version_id is None or view.locator is None:
            raise EvidenceViewBoundaryError("已定位来源必须同时包含来源版本与精确定位")
        dirty = locator_local_path_fields(view.locator)
        if dirty:
            raise EvidenceViewBoundaryError(
                "来源定位不得包含本机路径形状：" + "、".join(dirty)
            )
        if precise_locator_anchor(view.locator) is None:
            raise EvidenceViewBoundaryError(
                "已定位来源必须包含字段、页、表、行、列或段落精确锚点，"
                "仅链接或仅章节不足以定位"
            )
        if view.report_kind in _TRACE_VERBATIM_TEXT_KINDS and (
            view.original_text is None
            or view.original_text_status is not OriginalTextStatus.PROVIDED
        ):
            raise EvidenceViewBoundaryError(
                "B/C 类已定位来源必须同时携带逐字原文且状态为已提供"
            )
        return
    leftovers: list[str] = []
    if view.source_version_id is not None:
        leftovers.append("来源版本")
    if view.locator is not None:
        leftovers.append("定位")
    if view.original_text is not None or view.original_text_status is OriginalTextStatus.PROVIDED:
        leftovers.append("原文引文")
    if view.conflicts:
        leftovers.append("冲突")
    if view.historical_versions:
        leftovers.append("历史版本")
    if view.reason_original_text is not None:
        leftovers.append("原因原文")
    if leftovers:
        raise EvidenceViewBoundaryError(
            "来源待核不得携带来源版本、定位或原文引文等残留：" + "、".join(leftovers)
        )


def assert_evidence_views_serializable(views: Sequence[EvidenceView]) -> None:
    """序列化边界复核：``model_construct`` / ``model_copy`` 也不能绕过追溯合同。

    B/C 页面的行显示名、产品/试验名与单元值来自真实来源，可能不满足完整模型
    校验（例如登记英文名），因此这里只复核来源追溯合同本身；伪造中文名换取
    全量模型校验不是本边界的职责。
    """
    for view in views:
        try:
            assert_evidence_trace_contract(view)
        except EvidenceViewBoundaryError as error:
            row_id = _text(getattr(view.row, "row_id", "") or "")
            raise EvidenceViewBoundaryError(
                f"证据视图序列化边界校验失败（{row_id or '未知行'}）：{error}"
            ) from error


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
