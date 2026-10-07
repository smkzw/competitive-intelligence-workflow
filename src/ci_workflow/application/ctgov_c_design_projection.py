"""C 类固定 CT.gov 协议原子到既有设计观察的有界生产投影。

本模块把 ``ctgov_design_atoms`` 从固定登记来源提取的来源原子，在身份可证明的
前提下映射为既有 ``reports.c`` ``DesignObservation``：

- 试验身份由原子自身证明（登记号与已验证 ``SourceCapture`` 一致）；产品与 arm
  组别只接受调用方显式绑定，未绑定的产品/组别原子记入 ``unresolved_atoms``，
  不猜测产品、组别或 arm 关系；
- 不在既有 C 报告字段词汇内的原子记入 ``unsupported_atoms`` 并给出原因，
  不创建新 schema、本体或字段语义；
- 缺失或为空的协议路径记录为 ``gaps``，不生成零值或占位观察；
- 输出观察一律 ``review_state=candidate``：本层不签发 accepted，也不切换
  current；``source_version_id`` 原样保留已验证 ``SourceCapture`` 的来源标识
  （现行 C 研究包按来源实例识别观察）；
- 逐原子保留来源 JSON 字段路径、原文引文与来源 URL，并在本层边界重新按
  locator 从采集文本重提引文，防止转发过程中字节漂移；
- 资格全文原子在映射为 ``target_population``（父级，完整原文）之外，再按确定性
  标题分段规则派生既有 C 人群字段 ``inclusion_criterion`` / ``exclusion_criterion``：
  段落文本是父级标量的精确连续子串（仅去除首尾空白），来源标识、标量 JSON 定位
  与来源事实 ID 与父级一致——定位仍指向完整资格标量，不是更窄的段落定位；
  ``compatibility_rule`` 记录该派生规则。标题缺失、重复或段落为空时保持显式
  未决（``eligibility_sections``），不猜测分段、不重写引文、不扁平化条款。
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.application.ctgov_design_atoms import (
    CtgovProtocolDesignAtoms,
    extract_ctgov_protocol_design_atoms,
)
from ci_workflow.application.source_research_service import ResearchFact, SourceCapture
from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.gates.models import (
    ConflictDisposition,
    DisclosureMaturity,
    SourceRole,
)
from ci_workflow.reports.c.contracts import DesignFieldFamily, DesignObservation
from ci_workflow.reports.c.eligibility_source import EXCLUSION_HEADING, INCLUSION_HEADING
from ci_workflow.storage.source_derivation import extract_locator_quote

_COMPATIBILITY_RULE = "ctgov-c-protocol-atoms-v1"
# 派生段落的确定性规则标识：段落取自父级资格标量的标题边界连续子串；
# 标量 JSON 定位保持为父级定位，不冒充更窄的引文定位。
ELIGIBILITY_SECTION_COMPATIBILITY_RULE = "ctgov-c-protocol-atoms-v1+eligibility-section-split-v2"
_REGISTRY_DOCUMENT_ROLE = "clinical_trial_registry"
_PROTOCOL_PREFIX = "$.protocolSection"
_TRIAL_COHORT_TEMPLATE = "cohort-{trial}-all"
_TRIAL_GROUP_TEMPLATE = "group-{trial}-all"
_ARM_RELATION_REASON = "调用方显式绑定的组别标识与登记 arm 标签一致"
_UNCLASSIFIED_FAMILY = "unclassified"

# Use the existing C heading vocabulary; mentions inside clauses are not headings.

_YEAR_SCALAR = re.compile(r"^(?P<years>\d+(?:\.\d+)?)\s+years?$", re.IGNORECASE)
# Conservative mapping, not a dose parser: durations and extension population
# prose alone cannot prove a regimen. Other descriptions remain explicit gaps.
_DOSE_QUANTITY = re.compile(
    r"(?<!\w)\d+(?:\.\d+)?\s*(?:mg|mcg|[uµμ]g|g|units?|iu)\b", re.IGNORECASE
)
_ARM_INDEX = re.compile(r"armGroups\[(?P<index>\d+)\]")
_ARM_NAME_INDEX = re.compile(r"interventionNames\[(?P<index>\d+)\]")
_OUTCOME_INDEX = re.compile(r"(?P<collection>primaryOutcomes|secondaryOutcomes)\[(?P<index>\d+)\]")
_LAST_FIELD_NAME = re.compile(r"\.(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?:\[\d+\])?$")

_ATOM_FAMILIES: tuple[tuple[str, str], ...] = (
    ("ctgov.protocol.eligibility.", "eligibility"),
    ("ctgov.protocol.design.", "trial-design"),
    ("ctgov.protocol.arm.", "arms"),
    ("ctgov.protocol.intervention.", "interventions"),
    ("ctgov.protocol.primary_outcome.", "primary-endpoints"),
    ("ctgov.protocol.secondary_outcome.", "secondary-endpoints"),
)

_GROUPING_TOKENS: Mapping[str, str] = {
    "ctgov.protocol.design.allocation": "allocation",
    "ctgov.protocol.design.intervention_model": "interventionModel",
    "ctgov.protocol.design.masking": "masking",
}

_OUTCOME_ROLES: Mapping[str, tuple[str, str]] = {
    "ctgov.protocol.primary_outcome.measure": ("primary", "pri"),
    "ctgov.protocol.primary_outcome.description": ("primary", "pri"),
    "ctgov.protocol.primary_outcome.time_frame": ("primary", "pri"),
    "ctgov.protocol.secondary_outcome.measure": ("secondary", "sec"),
    "ctgov.protocol.secondary_outcome.description": ("secondary", "sec"),
    "ctgov.protocol.secondary_outcome.time_frame": ("secondary", "sec"),
}

_SUPPORTED_FIELD_IDS = frozenset(
    {
        "ctgov.protocol.eligibility.criteria",
        "ctgov.protocol.eligibility.minimum_age",
        "ctgov.protocol.design.phase",
        "ctgov.protocol.design.study_type",
        "ctgov.protocol.design.allocation",
        "ctgov.protocol.design.intervention_model",
        "ctgov.protocol.design.masking",
        "ctgov.protocol.design.enrollment_count",
        "ctgov.protocol.arm.label",
        "ctgov.protocol.arm.description",
        "ctgov.protocol.arm.intervention_name",
        "ctgov.protocol.primary_outcome.measure",
        "ctgov.protocol.primary_outcome.description",
        "ctgov.protocol.primary_outcome.time_frame",
        "ctgov.protocol.secondary_outcome.measure",
        "ctgov.protocol.secondary_outcome.description",
        "ctgov.protocol.secondary_outcome.time_frame",
    }
)


class CtgovCDesignProjectionError(ValueError):
    """协议原子投影的输入、身份或来源证据不满足合同。"""


class CtgovCUnresolvedReason(StrEnum):
    """需要调用方补充决策的原子原因；不得以猜测代替。"""

    MISSING_TRIAL_BINDING = "missing_trial_binding"
    MISSING_ARM_BINDING = "missing_arm_binding"
    UNPARSABLE_SCALAR_FOR_FIELD = "unparsable_scalar_for_field"
    ARM_DESCRIPTION_WITHOUT_DOSE = "arm_description_without_explicit_dose"
    MISSING_OUTCOME_TIMEFRAME = "missing_outcome_timeframe"


class CtgovCUnsupportedReason(StrEnum):
    """无既有 C 报告字段承载的原子原因；不新建字段语义。"""

    NO_EXISTING_DESIGN_FIELD = "no_existing_design_field"
    RELATION_ATOM_ONLY = "relation_atom_only"
    INTERVENTIONS_MODULE_NOT_PROJECTED = "interventions_module_not_projected"


class CtgovCEligibilitySectionKind(StrEnum):
    """资格全文中的两个显式段落方向。"""

    INCLUSION = "inclusion"
    EXCLUSION = "exclusion"


class CtgovCEligibilitySectionReason(StrEnum):
    """段落派生未决原因；标题缺失、重复或段落为空时不得猜测分段。"""

    INCLUSION_HEADING_MISSING = "inclusion_heading_missing"
    INCLUSION_HEADING_REPEATED = "inclusion_heading_repeated"
    INCLUSION_BOUNDARY_UNRESOLVED = "inclusion_boundary_unresolved"
    INCLUSION_TEXT_EMPTY = "inclusion_text_empty"
    EXCLUSION_HEADING_MISSING = "exclusion_heading_missing"
    EXCLUSION_HEADING_REPEATED = "exclusion_heading_repeated"
    EXCLUSION_BOUNDARY_UNRESOLVED = "exclusion_boundary_unresolved"
    EXCLUSION_TEXT_EMPTY = "exclusion_text_empty"


_UNSUPPORTED_REASON_BY_FIELD: Mapping[str, CtgovCUnsupportedReason] = {
    "ctgov.protocol.intervention.arm_group_label": CtgovCUnsupportedReason.RELATION_ATOM_ONLY,
    "ctgov.protocol.intervention.type": (
        CtgovCUnsupportedReason.INTERVENTIONS_MODULE_NOT_PROJECTED
    ),
    "ctgov.protocol.intervention.name": (
        CtgovCUnsupportedReason.INTERVENTIONS_MODULE_NOT_PROJECTED
    ),
    "ctgov.protocol.intervention.description": (
        CtgovCUnsupportedReason.INTERVENTIONS_MODULE_NOT_PROJECTED
    ),
    "ctgov.protocol.intervention.other_name": (
        CtgovCUnsupportedReason.INTERVENTIONS_MODULE_NOT_PROJECTED
    ),
}

_ARM_FIELD_IDS = (
    "ctgov.protocol.arm.label",
    "ctgov.protocol.arm.description",
    "ctgov.protocol.arm.intervention_name",
)
_OUTCOME_TIMEFRAME_FIELD_IDS = (
    "ctgov.protocol.primary_outcome.time_frame",
    "ctgov.protocol.secondary_outcome.time_frame",
)
_ELIGIBILITY_SECTION_FIELDS: Mapping[CtgovCEligibilitySectionKind, str] = {
    CtgovCEligibilitySectionKind.INCLUSION: "inclusion_criterion",
    CtgovCEligibilitySectionKind.EXCLUSION: "exclusion_criterion",
}


def _anchor_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}不能为空")
    return value


def _optional_anchor_text(value: str | None, label: str) -> str | None:
    return None if value is None else _anchor_text(value, label)


class CtgovCArmBinding(BaseModel):
    """调用方显式提供的组别绑定：登记 arm 标签 → 报告组别身份与角色字段。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str
    group_id: str
    role: Literal["experimental_arm", "control_arm"]
    cohort_id: str | None = None

    @field_validator("label", "group_id")
    @classmethod
    def _required(cls, value: str) -> str:
        return _anchor_text(value, "组别绑定文本")

    @field_validator("cohort_id")
    @classmethod
    def _optional_cohort(cls, value: str | None) -> str | None:
        return _optional_anchor_text(value, "组别绑定队列标识")


class CtgovCTrialBinding(BaseModel):
    """调用方显式提供的试验绑定：报告试验身份、产品身份与组别绑定集合。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trial_id: str
    product_id: str | None
    cohort_id: str | None = None
    group_id: str | None = None
    arms: tuple[CtgovCArmBinding, ...] = ()

    @field_validator("trial_id")
    @classmethod
    def _required(cls, value: str) -> str:
        return _anchor_text(value, "试验绑定文本")

    @field_validator("product_id")
    @classmethod
    def _explicit_product(cls, value: str | None) -> str | None:
        return _optional_anchor_text(value, "试验绑定产品身份")

    @field_validator("cohort_id", "group_id")
    @classmethod
    def _optional_identity(cls, value: str | None) -> str | None:
        return _optional_anchor_text(value, "试验绑定身份")


class CtgovCUnresolvedAtom(BaseModel):
    """需要调用方决策的原子：保留原子身份、来源路径与未决原因。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    atom_id: str
    trial_id: str
    field_id: str
    path: str | None
    reason: CtgovCUnresolvedReason

    @field_validator("atom_id", "trial_id", "field_id")
    @classmethod
    def _required(cls, value: str) -> str:
        return _anchor_text(value, "未决原子文本")

    @field_validator("path")
    @classmethod
    def _optional_path(cls, value: str | None) -> str | None:
        return _optional_anchor_text(value, "未决原子来源路径")


class CtgovCUnsupportedAtom(BaseModel):
    """无既有 C 报告字段承载的原子：暴露标识与原因，不伪造观察。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    atom_id: str
    trial_id: str
    field_id: str
    path: str | None
    reason: CtgovCUnsupportedReason

    @field_validator("atom_id", "trial_id", "field_id")
    @classmethod
    def _required(cls, value: str) -> str:
        return _anchor_text(value, "未支持原子文本")

    @field_validator("path")
    @classmethod
    def _optional_path(cls, value: str | None) -> str | None:
        return _optional_anchor_text(value, "未支持原子来源路径")


class CtgovCProtocolGap(BaseModel):
    """协议缺失或空列表缺口；只记录路径，不生成占位观察。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trial_id: str
    source_id: str
    path: str
    reason: Literal["absent_or_empty_protocol_path"] = "absent_or_empty_protocol_path"

    @field_validator("trial_id", "source_id", "path")
    @classmethod
    def _required(cls, value: str) -> str:
        return _anchor_text(value, "协议缺口文本")


class CtgovCEligibilitySectionOutcome(BaseModel):
    """资格段落派生的显式结果：已派生观察标识，或未决原因，二者恰有其一。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trial_id: str
    source_id: str
    atom_id: str
    parent_path: str
    section: CtgovCEligibilitySectionKind
    observation_id: str | None = None
    reason: CtgovCEligibilitySectionReason | None = None

    @field_validator("trial_id", "source_id", "atom_id", "parent_path")
    @classmethod
    def _required(cls, value: str) -> str:
        return _anchor_text(value, "资格段落结果文本")

    @field_validator("observation_id")
    @classmethod
    def _optional_observation(cls, value: str | None) -> str | None:
        return _optional_anchor_text(value, "资格段落观察标识")

    @model_validator(mode="after")
    def _derived_xor_unresolved(self) -> Self:
        if (self.observation_id is None) == (self.reason is None):
            raise ValueError("资格段落结果必须恰为已派生观察或未决原因之一")
        return self


class CtgovCAtomFamilyCoverage(BaseModel):
    """单个原子族的映射完整性：原子数 = 已映射 + 未支持 + 未决。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    family: str
    atom_count: int = Field(ge=0)
    mapped_count: int = Field(ge=0)
    unsupported_count: int = Field(ge=0)
    unresolved_count: int = Field(ge=0)
    unsupported_field_ids: tuple[str, ...] = ()

    @field_validator("family")
    @classmethod
    def _required(cls, value: str) -> str:
        return _anchor_text(value, "原子族名称")


class CtgovCDesignProjection(BaseModel):
    """有界投影结果：既有设计观察、缺口、未决/未支持原子与族完整性。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    indication_id: str
    observations: tuple[DesignObservation, ...]
    eligibility_sections: tuple[CtgovCEligibilitySectionOutcome, ...]
    gaps: tuple[CtgovCProtocolGap, ...]
    unresolved_atoms: tuple[CtgovCUnresolvedAtom, ...]
    unsupported_atoms: tuple[CtgovCUnsupportedAtom, ...]
    atom_families: tuple[CtgovCAtomFamilyCoverage, ...]

    @field_validator("indication_id")
    @classmethod
    def _required(cls, value: str) -> str:
        return _anchor_text(value, "适应症标识")


@dataclass(frozen=True)
class _StudyContext:
    report_trial_id: str
    atoms: CtgovProtocolDesignAtoms
    capture: SourceCapture
    binding: CtgovCTrialBinding | None
    arm_label_by_index: Mapping[int, str]
    arm_bindings: Mapping[str, CtgovCArmBinding]
    outcome_timeframe: Mapping[tuple[str, int], str]

    @property
    def cohort_id(self) -> str:
        if self.binding is not None and self.binding.cohort_id is not None:
            return self.binding.cohort_id
        return _TRIAL_COHORT_TEMPLATE.format(trial=self.report_trial_id)

    @property
    def group_id(self) -> str:
        if self.binding is not None and self.binding.group_id is not None:
            return self.binding.group_id
        return _TRIAL_GROUP_TEMPLATE.format(trial=self.report_trial_id)


@dataclass(frozen=True)
class _SectionDerivation:
    """单段派生的两种互斥结果：连续子串文本，或显式未决原因。"""

    text: str | None
    reason: CtgovCEligibilitySectionReason | None


@dataclass(frozen=True)
class _FactProjection:
    """单条原子的投影结果：观察、未决原因与资格段落派生结果。"""

    observations: tuple[DesignObservation, ...]
    unresolved_reason: CtgovCUnresolvedReason | None = None
    eligibility_sections: tuple[CtgovCEligibilitySectionOutcome, ...] = ()


def _fact_quote(fact: ResearchFact) -> str:
    quote = fact.raw_value
    if quote is None or not quote.strip():
        raise CtgovCDesignProjectionError(f"原子 {fact.fact_id} 缺少原文引文")
    return quote


def _atom_family(field_id: str) -> str:
    for prefix, family in _ATOM_FAMILIES:
        if field_id.startswith(prefix):
            return family
    return _UNCLASSIFIED_FAMILY


def _source_field_name(path: str) -> str:
    match = _LAST_FIELD_NAME.search(path)
    if match is None:
        raise CtgovCDesignProjectionError(f"无法从来源路径确定字段名：{path}")
    return match.group("name")


def _stripped_section(
    text: str, empty_reason: CtgovCEligibilitySectionReason
) -> _SectionDerivation:
    """段落只去首尾空白，保持为父级标量的精确连续子串；空段保持未决。"""

    stripped = text.strip()
    if not stripped:
        return _SectionDerivation(text=None, reason=empty_reason)
    return _SectionDerivation(text=stripped, reason=None)


def _derive_eligibility_sections(
    quote: str,
) -> Mapping[CtgovCEligibilitySectionKind, _SectionDerivation]:
    """按确定性标题分段规则从父级资格全文派生入选段与排除段。

    规则（标题语义与既有 C 分段器一致；仅在无歧义时派生）：

    - 排除标题在父级全文中恰出现一次、入选标题在排除标题之前不超过一次时：
      入选段取入选标题之后到排除标题之前的原文，排除段取排除标题之后的原文；
      两段仅去除首尾空白，始终是父级标量的精确连续子串，标题本身不计入段落，
      也不改写任何条款、布尔逻辑或嵌套项目符号；
    - 排除标题缺失或重复时，入选段缺少确定结束边界、排除段缺少唯一标题，
      两者保持显式未决；
    - 入选标题缺失或重复时，仅入选段保持显式未决，排除段仍可派生；
    - 段落去空白后为空时保持显式未决；未决段落不生成观察。

    本层不解析条目、不扁平化条件、不推断等价或阈值；父级 ``target_population``
    观察始终保留完整原文与标量定位。
    """

    exclusion_matches = tuple(EXCLUSION_HEADING.finditer(quote))
    inclusion_scope_end = exclusion_matches[0].start() if exclusion_matches else len(quote)
    all_inclusion_matches = tuple(INCLUSION_HEADING.finditer(quote))
    inclusion_matches = tuple(item for item in all_inclusion_matches
                              if item.start() < inclusion_scope_end)

    if exclusion_matches and any(
        item.start() > exclusion_matches[0].start() for item in all_inclusion_matches
    ):
        # Reversed or interleaved headings cannot be swallowed into 'exclusion'.
        return {
            CtgovCEligibilitySectionKind.INCLUSION: _SectionDerivation(
                text=None, reason=CtgovCEligibilitySectionReason.INCLUSION_BOUNDARY_UNRESOLVED,
            ),
            CtgovCEligibilitySectionKind.EXCLUSION: _SectionDerivation(
                text=None, reason=CtgovCEligibilitySectionReason.EXCLUSION_BOUNDARY_UNRESOLVED,
            ),
        }

    if not exclusion_matches:
        inclusion = _SectionDerivation(
            text=None,
            reason=CtgovCEligibilitySectionReason.INCLUSION_BOUNDARY_UNRESOLVED,
        )
        exclusion = _SectionDerivation(
            text=None,
            reason=CtgovCEligibilitySectionReason.EXCLUSION_HEADING_MISSING,
        )
    elif len(exclusion_matches) > 1:
        inclusion = _SectionDerivation(
            text=None,
            reason=CtgovCEligibilitySectionReason.INCLUSION_BOUNDARY_UNRESOLVED,
        )
        exclusion = _SectionDerivation(
            text=None,
            reason=CtgovCEligibilitySectionReason.EXCLUSION_HEADING_REPEATED,
        )
    else:
        exclusion_heading = exclusion_matches[0]
        exclusion = _stripped_section(
            quote[exclusion_heading.end() :],
            CtgovCEligibilitySectionReason.EXCLUSION_TEXT_EMPTY,
        )
        if not inclusion_matches:
            inclusion = _SectionDerivation(
                text=None,
                reason=CtgovCEligibilitySectionReason.INCLUSION_HEADING_MISSING,
            )
        elif len(inclusion_matches) > 1:
            inclusion = _SectionDerivation(
                text=None,
                reason=CtgovCEligibilitySectionReason.INCLUSION_HEADING_REPEATED,
            )
        else:
            inclusion = _stripped_section(
                quote[inclusion_matches[0].end() : exclusion_heading.start()],
                CtgovCEligibilitySectionReason.INCLUSION_TEXT_EMPTY,
            )

    return {
        CtgovCEligibilitySectionKind.INCLUSION: inclusion,
        CtgovCEligibilitySectionKind.EXCLUSION: exclusion,
    }


def _verify_capture(study: CtgovProtocolDesignAtoms, capture: SourceCapture) -> None:
    if capture.source_id != study.source_id:
        raise CtgovCDesignProjectionError(f"采集来源标识与原子不一致：{study.source_id}")
    if capture.source_type != "clinical_trial_registry" or capture.media_type != "application/json":
        raise CtgovCDesignProjectionError(f"原子来源不是 JSON 登记采集：{study.source_id}")
    if capture.query_or_identifier.casefold() != study.trial_id.casefold():
        raise CtgovCDesignProjectionError(f"采集登记号与原子试验身份不一致：{study.trial_id}")
    # Verify source content, not merely two caller-supplied identity strings.
    # Reuse the existing extractor so field/path semantics and completeness have
    # one owner; transport order cannot create or remove protocol facts/gaps.
    try:
        replayed = extract_ctgov_protocol_design_atoms(capture)
    except ValueError as error:
        raise CtgovCDesignProjectionError("原始登记内容不能证明协议身份与完整原子集合") from error
    expected = {fact.fact_id: fact for fact in replayed.facts}
    supplied = {fact.fact_id: fact for fact in study.facts}
    if (
        replayed.trial_id.casefold() != study.trial_id.casefold()
        or len(supplied) != len(study.facts)
        or supplied != expected
        or set(study.absent_paths) != set(replayed.absent_paths)
    ):
        raise CtgovCDesignProjectionError("协议原子、语义或缺口与原始来源重提取结果不一致")


def replay_ctgov_eligibility_section(parent_text: str, field: str) -> str:
    """Replay an exact section; the public locator still identifies its full scalar."""
    kinds = {value: key for key, value in _ELIGIBILITY_SECTION_FIELDS.items()}
    kind = kinds.get(field)
    if kind is None:
        raise CtgovCDesignProjectionError("非入排字段不能使用资格分段规则")
    section = _derive_eligibility_sections(parent_text)[kind]
    if section.text is None:
        raise CtgovCDesignProjectionError("登记资格原文没有可证明的完整段落边界")
    return section.text


def _verify_fact_source(ctx: _StudyContext, fact: ResearchFact) -> str:
    """校验原子定位属于已验证采集，并按路径重提原文，防止字节漂移。"""

    locator = fact.locator
    if locator.document_role != _REGISTRY_DOCUMENT_ROLE:
        raise CtgovCDesignProjectionError(f"原子 {fact.fact_id} 的来源角色不是登记来源")
    path = locator.field_path
    if path is None or not path.startswith(f"{_PROTOCOL_PREFIX}."):
        raise CtgovCDesignProjectionError(f"原子 {fact.fact_id} 缺少精确协议 JSON 路径")
    if locator.url != ctx.capture.url:
        raise CtgovCDesignProjectionError(f"原子 {fact.fact_id} 的来源链接与已验证采集不一致")
    if fact.source_id != ctx.atoms.source_id:
        raise CtgovCDesignProjectionError(f"原子 {fact.fact_id} 的来源标识与所属研究不一致")
    quote = _fact_quote(fact)
    replayed = extract_locator_quote(
        ctx.capture.content_text, media_type=ctx.capture.media_type, locator=locator
    )
    if replayed != quote:
        raise CtgovCDesignProjectionError(f"原子 {fact.fact_id} 的原文引文与采集文本不一致")
    return path


def _build_context(
    study: CtgovProtocolDesignAtoms,
    capture: SourceCapture,
    binding: CtgovCTrialBinding | None,
) -> _StudyContext:
    # Registry spellings are preserved in source atoms; report identifiers must
    # share the case-insensitive identity used by the declared study universe.
    report_trial_id = (binding.trial_id if binding is not None else study.trial_id).casefold()
    arm_label_by_index: dict[int, str] = {}
    outcome_timeframe: dict[tuple[str, int], str] = {}
    for fact in study.facts:
        path = fact.locator.field_path or ""
        if fact.field_id == "ctgov.protocol.arm.label":
            match = _ARM_INDEX.search(path)
            if match is None:
                raise CtgovCDesignProjectionError(f"组别标签缺少 armGroups 索引：{path}")
            index = int(match.group("index"))
            if index in arm_label_by_index:
                raise CtgovCDesignProjectionError(f"组别标签索引重复：{path}")
            arm_label_by_index[index] = _fact_quote(fact)
        elif fact.field_id in _OUTCOME_TIMEFRAME_FIELD_IDS:
            match = _OUTCOME_INDEX.search(path)
            role = _OUTCOME_ROLES[fact.field_id][0]
            collection = "primaryOutcomes" if role == "primary" else "secondaryOutcomes"
            if match is None or match.group("collection") != collection:
                raise CtgovCDesignProjectionError(f"终点时间窗缺少结局索引：{path}")
            key = (role, int(match.group("index")))
            if key in outcome_timeframe:
                raise CtgovCDesignProjectionError(f"终点时间窗实例重复：{path}")
            outcome_timeframe[key] = _fact_quote(fact)

    arm_bindings: dict[str, CtgovCArmBinding] = {}
    if binding is not None:
        labels = [arm.label for arm in binding.arms]
        groups = [arm.group_id for arm in binding.arms]
        if len(set(labels)) != len(labels):
            raise CtgovCDesignProjectionError(f"组别绑定标签被复用：{binding.trial_id}")
        if len(set(groups)) != len(groups):
            raise CtgovCDesignProjectionError(f"组别绑定组别标识被复用：{binding.trial_id}")
        known_labels = set(arm_label_by_index.values())
        for arm in binding.arms:
            if arm.label not in known_labels:
                raise CtgovCDesignProjectionError(
                    f"组别绑定无法在固定原子中证明：{binding.trial_id} / {arm.label}"
                )
            arm_bindings[arm.label] = arm

    return _StudyContext(
        report_trial_id=report_trial_id,
        atoms=study,
        capture=capture,
        binding=binding,
        arm_label_by_index=arm_label_by_index,
        arm_bindings=arm_bindings,
        outcome_timeframe=outcome_timeframe,
    )


def _observation(
    ctx: _StudyContext,
    binding: CtgovCTrialBinding,
    fact: ResearchFact,
    path: str,
    *,
    family: DesignFieldFamily,
    field: str,
    suffix: str,
    group_id: str | None = None,
    cohort_id: str | None = None,
    display_text: str | None = None,
    operator: str | None = None,
    threshold_value: str | None = None,
    threshold_unit: str | None = None,
    assessment_timepoint: str | None = None,
    stage: str | None = None,
    outcome_id: str | None = None,
    endpoint_key: str | None = None,
    relationship_status: Literal["bound"] | None = None,
    source_text: str | None = None,
    compatibility_rule: str | None = None,
) -> DesignObservation:
    return DesignObservation(
        row_id=f"c-{ctx.report_trial_id}-{suffix}",
        source_row_id=fact.fact_id,
        observation_id=f"obs-{ctx.report_trial_id}-{suffix}",
        product_id=binding.product_id,
        trial_id=ctx.report_trial_id,
        cohort_id=cohort_id or ctx.cohort_id,
        group_id=group_id or ctx.group_id,
        field_family=family,
        field=field,
        outcome_id=outcome_id,
        endpoint_key=endpoint_key,
        source_field_name=_source_field_name(path),
        source_field_definition=path.removeprefix("$."),
        source_text=_fact_quote(fact) if source_text is None else source_text,
        display_text=display_text,
        operator=operator,
        threshold_value=threshold_value,
        threshold_unit=threshold_unit,
        assessment_timepoint=assessment_timepoint,
        stage=stage,
        source_version_id=ctx.capture.source_id,
        source_locator=fact.locator,
        source_role=SourceRole.CLINICAL_TRIAL_REGISTRY,
        disclosure_maturity=DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT,
        review_state=FactReviewState.CANDIDATE,
        disclosure_state=FactDisclosureState(fact.disclosure_state),
        conflict_disposition=ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT,
        compatibility_rule=compatibility_rule or _COMPATIBILITY_RULE,
        relationship_status=relationship_status,
        relationship_reason=_ARM_RELATION_REASON if relationship_status is not None else None,
    )


def _project_arm_fact(
    ctx: _StudyContext,
    binding: CtgovCTrialBinding,
    fact: ResearchFact,
    path: str,
) -> tuple[tuple[DesignObservation, ...], CtgovCUnresolvedReason | None]:
    match = _ARM_INDEX.search(path)
    if match is None:
        raise CtgovCDesignProjectionError(f"组别原子缺少 armGroups 索引：{path}")
    index = int(match.group("index"))
    label = ctx.arm_label_by_index.get(index)
    if label is None:
        raise CtgovCDesignProjectionError(f"协议切片缺少组别标签原子：{path}")
    arm = ctx.arm_bindings.get(label)
    if arm is None:
        return (), CtgovCUnresolvedReason.MISSING_ARM_BINDING
    cohort_id = arm.cohort_id or ctx.cohort_id
    if fact.field_id == "ctgov.protocol.arm.label":
        return (
            _observation(
                ctx,
                binding,
                fact,
                path,
                family=DesignFieldFamily.INTERVENTION,
                field=arm.role,
                suffix=f"arm-{index}-label",
                group_id=arm.group_id,
                cohort_id=cohort_id,
                relationship_status="bound",
            ),
        ), None
    if fact.field_id == "ctgov.protocol.arm.description":
        if _DOSE_QUANTITY.search(_fact_quote(fact)) is None:
            return (), CtgovCUnresolvedReason.ARM_DESCRIPTION_WITHOUT_DOSE
        return (
            _observation(
                ctx,
                binding,
                fact,
                path,
                family=DesignFieldFamily.DOSE_SCHEDULE,
                field="dosing_regimen",
                suffix=f"arm-{index}-dosing",
                group_id=arm.group_id,
                cohort_id=cohort_id,
                relationship_status="bound",
            ),
        ), None
    name_match = _ARM_NAME_INDEX.search(path)
    if name_match is None:
        raise CtgovCDesignProjectionError(f"组别干预名称缺少索引：{path}")
    return (
        _observation(
            ctx,
            binding,
            fact,
            path,
            family=DesignFieldFamily.INTERVENTION,
            field=arm.role,
            suffix=f"arm-{index}-intervention-{name_match.group('index')}",
            group_id=arm.group_id,
            cohort_id=cohort_id,
            relationship_status="bound",
        ),
    ), None


def _project_outcome_fact(
    ctx: _StudyContext,
    binding: CtgovCTrialBinding,
    fact: ResearchFact,
    path: str,
) -> tuple[tuple[DesignObservation, ...], CtgovCUnresolvedReason | None]:
    match = _OUTCOME_INDEX.search(path)
    role, short = _OUTCOME_ROLES[fact.field_id]
    collection = "primaryOutcomes" if role == "primary" else "secondaryOutcomes"
    if match is None or match.group("collection") != collection:
        raise CtgovCDesignProjectionError(f"终点原子缺少结局索引：{path}")
    index = int(match.group("index"))
    outcome_id = f"outcome-{ctx.report_trial_id}-{short}-{index}"
    if fact.field_id.endswith((".measure", ".description")):
        timeframe = ctx.outcome_timeframe.get((role, index))
        if timeframe is None:
            return (), CtgovCUnresolvedReason.MISSING_OUTCOME_TIMEFRAME
        is_description = fact.field_id.endswith(".description")
        endpoint_field = "description" if is_description else "definition"
        return (
            _observation(
                ctx,
                binding,
                fact,
                path,
                family=DesignFieldFamily.ENDPOINT,
                field=f"{role}_endpoint_{endpoint_field}",
                suffix=f"{short}{index}-{endpoint_field}",
                outcome_id=outcome_id,
                endpoint_key=f"{role}_endpoint",
                assessment_timepoint=timeframe,
            ),
        ), None
    return (
        _observation(
            ctx,
            binding,
            fact,
            path,
            family=DesignFieldFamily.TIMEPOINT,
            field=f"{role}_endpoint_timepoint",
            suffix=f"{short}{index}-timepoint",
            outcome_id=outcome_id,
            assessment_timepoint=_fact_quote(fact),
        ),
    ), None


def _project_eligibility_criteria(
    ctx: _StudyContext,
    binding: CtgovCTrialBinding,
    fact: ResearchFact,
    path: str,
) -> _FactProjection:
    """父级资格全文 + 确定性派生段落的同源观察。

    父级 ``target_population`` 保留完整原文；派生段落的 ``source_text`` 是按
    标题边界从同一父级标量截取的连续子串，来源事实 ID、来源实例与标量 JSON
    定位与父级一致，``compatibility_rule`` 记录派生规则。段落未决时只记录
    ``eligibility_sections``，不生成观察，父级观察仍可用。
    """

    quote = _fact_quote(fact)
    observations = [
        _observation(
            ctx,
            binding,
            fact,
            path,
            family=DesignFieldFamily.POPULATION,
            field="target_population",
            suffix="population",
        )
    ]
    sections: list[CtgovCEligibilitySectionOutcome] = []
    for kind, derivation in _derive_eligibility_sections(quote).items():
        if derivation.text is None:
            sections.append(
                CtgovCEligibilitySectionOutcome(
                    trial_id=ctx.atoms.trial_id,
                    source_id=ctx.atoms.source_id,
                    atom_id=fact.fact_id,
                    parent_path=path,
                    section=kind,
                    reason=derivation.reason,
                )
            )
            continue
        observation = _observation(
            ctx,
            binding,
            fact,
            path,
            family=DesignFieldFamily.POPULATION,
            field=_ELIGIBILITY_SECTION_FIELDS[kind],
            suffix=kind.value,
            source_text=derivation.text,
            compatibility_rule=ELIGIBILITY_SECTION_COMPATIBILITY_RULE,
        )
        observations.append(observation)
        sections.append(
            CtgovCEligibilitySectionOutcome(
                trial_id=ctx.atoms.trial_id,
                source_id=ctx.atoms.source_id,
                atom_id=fact.fact_id,
                parent_path=path,
                section=kind,
                observation_id=observation.observation_id,
            )
        )
    return _FactProjection(
        observations=tuple(observations),
        eligibility_sections=tuple(sections),
    )


def _project_fact(
    ctx: _StudyContext,
    binding: CtgovCTrialBinding,
    fact: ResearchFact,
    path: str,
) -> _FactProjection:
    field_id = fact.field_id
    if field_id in {"ctgov.protocol.design.phase", "ctgov.protocol.design.study_type"}:
        quote = _fact_quote(fact)
        is_phase = field_id.endswith(".phase")
        if is_phase:
            match = re.fullmatch(r"\$\.protocolSection\.designModule\.phases\[(\d+)\]", path)
            if match is None:
                raise CtgovCDesignProjectionError("登记阶段缺少精确数组实例定位")
            suffix = f"phase-{match.group(1)}"
            label = {"EARLY_PHASE1": "早期I期", "PHASE1": "I期", "PHASE2": "II期",
                     "PHASE3": "III期", "PHASE4": "IV期", "NA": "不适用"}.get(quote, quote)
            display = f"登记阶段：{label}"
        else:
            suffix = "study-type"
            label = {"INTERVENTIONAL": "干预性研究", "OBSERVATIONAL": "观察性研究"}.get(
                quote, quote,
            )
            display = f"登记研究类型：{label}"
        return _FactProjection(observations=(
            _observation(ctx, binding, fact, path, family=DesignFieldFamily.TRIAL_IDENTITY,
                         field="trial_identity", suffix=suffix, display_text=display,
                         stage=quote if is_phase else None),
        ))
    if field_id == "ctgov.protocol.eligibility.criteria":
        return _project_eligibility_criteria(ctx, binding, fact, path)
    if field_id == "ctgov.protocol.eligibility.minimum_age":
        years = _YEAR_SCALAR.match(_fact_quote(fact))
        if years is None:
            return _FactProjection(
                observations=(),
                unresolved_reason=CtgovCUnresolvedReason.UNPARSABLE_SCALAR_FOR_FIELD,
            )
        return _FactProjection(
            observations=(
                _observation(
                    ctx,
                    binding,
                    fact,
                    path,
                    family=DesignFieldFamily.POPULATION,
                    field="target_population",
                    suffix="min-age",
                    operator="≥",
                    threshold_value=years.group("years"),
                    threshold_unit="岁",
                ),
            )
        )
    if field_id in _GROUPING_TOKENS:
        token = _GROUPING_TOKENS[field_id]
        return _FactProjection(
            observations=(
                _observation(
                    ctx,
                    binding,
                    fact,
                    path,
                    family=DesignFieldFamily.GROUPING,
                    field="arm_randomization_blinding",
                    suffix=token.replace("_", "-"),
                    display_text=f"{token}={_fact_quote(fact)}",
                ),
            )
        )
    if field_id == "ctgov.protocol.design.enrollment_count":
        enrollment_type = next(
            (_fact_quote(item) for item in ctx.atoms.facts
             if item.field_id == "ctgov.protocol.design.enrollment_type"), None
        )
        label = {"ACTUAL": "实际入组", "ESTIMATED": "计划入组"}.get(
            enrollment_type or "", "入组类型未明"
        )
        display = f"{label}：{_fact_quote(fact)}例"
        if enrollment_type is not None:
            display += f"（登记类型 {enrollment_type}）"
        return _FactProjection(
            observations=(
                _observation(
                    ctx,
                    binding,
                    fact,
                    path,
                    family=DesignFieldFamily.SAMPLE_SIZE,
                    field="planned_or_actual_sample_size",
                    suffix="sample-size",
                    threshold_value=_fact_quote(fact),
                    threshold_unit="例",
                    display_text=display,
                ),
            )
        )
    if field_id in _ARM_FIELD_IDS:
        observations, unresolved_reason = _project_arm_fact(ctx, binding, fact, path)
        return _FactProjection(observations=observations, unresolved_reason=unresolved_reason)
    if field_id in _OUTCOME_ROLES:
        observations, unresolved_reason = _project_outcome_fact(ctx, binding, fact, path)
        return _FactProjection(observations=observations, unresolved_reason=unresolved_reason)
    raise AssertionError(f"支持的原子字段缺少投影处理器：{field_id}")


def _family_coverage(
    counters: Mapping[str, list[int]],
    unsupported_ids: Mapping[str, set[str]],
) -> tuple[CtgovCAtomFamilyCoverage, ...]:
    """固定报告全部原子族：无原子的族也以 0 计数出现，形状稳定。"""

    ordered = [family for _, family in _ATOM_FAMILIES]
    ordered.extend(sorted(set(counters) - set(ordered)))
    reports = []
    for family in ordered:
        atom_count, mapped, unsupported, unresolved = counters.get(family, [0, 0, 0, 0])
        reports.append(
            CtgovCAtomFamilyCoverage(
                family=family,
                atom_count=atom_count,
                mapped_count=mapped,
                unsupported_count=unsupported,
                unresolved_count=unresolved,
                unsupported_field_ids=tuple(sorted(unsupported_ids.get(family, set()))),
            )
        )
    return tuple(reports)


def project_ctgov_c_design_observations(
    atoms: Sequence[CtgovProtocolDesignAtoms],
    *,
    captures: Mapping[str, SourceCapture],
    bindings: Sequence[CtgovCTrialBinding],
    indication_id: str,
) -> CtgovCDesignProjection:
    """把固定登记协议原子投影为既有 C 设计观察（不签发 accepted）。

    - 每个原子在边界按 locator 重新从采集文本重提原文，任何身份、路径、链接
      或引文不一致立即失败关闭；
    - 试验身份由原子证明；调用方的试验/组别绑定必须能在原子中证明，否则失败；
      被投影研究的 arm 原子未绑定时保持未决，不猜测组别；
    - 未在既有 C 字段词汇内的原子只暴露标识与原因；缺失/空路径只记录缺口；
    - 资格全文原子额外派生入选/排除段观察：段落是父级标量的精确连续子串，
      标题缺失、重复或段落为空时只记录 ``eligibility_sections`` 未决，
      不生成观察、不改写父级原文。
    """

    indication = _anchor_text(indication_id, "适应症标识")
    studies = tuple(atoms)
    if not studies:
        raise CtgovCDesignProjectionError("协议原子输入不能为空")

    binding_by_trial: dict[str, CtgovCTrialBinding] = {}
    for binding in bindings:
        key = binding.trial_id.casefold()
        if key in binding_by_trial:
            raise CtgovCDesignProjectionError(f"试验绑定身份被复用：{binding.trial_id}")
        binding_by_trial[key] = binding

    contexts: list[_StudyContext] = []
    seen_trials: set[str] = set()
    seen_sources: set[str] = set()
    for study in studies:
        trial_key = study.trial_id.casefold()
        if trial_key in seen_trials:
            raise CtgovCDesignProjectionError(f"研究身份被复用：{study.trial_id}")
        if study.source_id in seen_sources:
            raise CtgovCDesignProjectionError(f"来源身份被复用：{study.source_id}")
        seen_trials.add(trial_key)
        seen_sources.add(study.source_id)
        capture = captures.get(study.source_id)
        if capture is None:
            raise CtgovCDesignProjectionError(f"缺少已验证的来源采集：{study.source_id}")
        _verify_capture(study, capture)
        contexts.append(_build_context(study, capture, binding_by_trial.get(trial_key)))

    observations: list[DesignObservation] = []
    eligibility_sections: list[CtgovCEligibilitySectionOutcome] = []
    gaps: list[CtgovCProtocolGap] = []
    unresolved: list[CtgovCUnresolvedAtom] = []
    unsupported: list[CtgovCUnsupportedAtom] = []
    counters: dict[str, list[int]] = {}
    unsupported_ids: dict[str, set[str]] = {}

    for ctx in contexts:
        for fact in ctx.atoms.facts:
            path = _verify_fact_source(ctx, fact)
            family = _atom_family(fact.field_id)
            counters.setdefault(family, [0, 0, 0, 0])[0] += 1
            if fact.field_id not in _SUPPORTED_FIELD_IDS:
                unsupported_reason = _UNSUPPORTED_REASON_BY_FIELD.get(
                    fact.field_id, CtgovCUnsupportedReason.NO_EXISTING_DESIGN_FIELD
                )
                unsupported.append(
                    CtgovCUnsupportedAtom(
                        atom_id=fact.fact_id,
                        trial_id=ctx.atoms.trial_id,
                        field_id=fact.field_id,
                        path=path,
                        reason=unsupported_reason,
                    )
                )
                counters[family][2] += 1
                unsupported_ids.setdefault(family, set()).add(fact.field_id)
                continue
            if ctx.binding is None:
                unresolved.append(
                    CtgovCUnresolvedAtom(
                        atom_id=fact.fact_id,
                        trial_id=ctx.atoms.trial_id,
                        field_id=fact.field_id,
                        path=path,
                        reason=CtgovCUnresolvedReason.MISSING_TRIAL_BINDING,
                    )
                )
                counters[family][3] += 1
                continue
            produced = _project_fact(ctx, ctx.binding, fact, path)
            if produced.unresolved_reason is not None:
                unresolved.append(
                    CtgovCUnresolvedAtom(
                        atom_id=fact.fact_id,
                        trial_id=ctx.atoms.trial_id,
                        field_id=fact.field_id,
                        path=path,
                        reason=produced.unresolved_reason,
                    )
                )
                counters[family][3] += 1
                continue
            observations.extend(produced.observations)
            eligibility_sections.extend(produced.eligibility_sections)
            counters[family][1] += 1
        for absent_path in ctx.atoms.absent_paths:
            gaps.append(
                CtgovCProtocolGap(
                    trial_id=ctx.atoms.trial_id,
                    source_id=ctx.atoms.source_id,
                    path=absent_path,
                )
            )

    observation_ids = [item.observation_id for item in observations]
    if len(set(observation_ids)) != len(observation_ids):
        raise CtgovCDesignProjectionError("投影观察身份发生碰撞")

    return CtgovCDesignProjection(
        indication_id=indication,
        observations=tuple(observations),
        eligibility_sections=tuple(eligibility_sections),
        gaps=tuple(gaps),
        unresolved_atoms=tuple(unresolved),
        unsupported_atoms=tuple(unsupported),
        atom_families=_family_coverage(counters, unsupported_ids),
    )


__all__ = [
    "ELIGIBILITY_SECTION_COMPATIBILITY_RULE",
    "CtgovCArmBinding",
    "CtgovCAtomFamilyCoverage",
    "CtgovCDesignProjection",
    "CtgovCDesignProjectionError",
    "CtgovCEligibilitySectionKind",
    "CtgovCEligibilitySectionOutcome",
    "CtgovCEligibilitySectionReason",
    "CtgovCProtocolGap",
    "CtgovCTrialBinding",
    "CtgovCUnresolvedAtom",
    "CtgovCUnresolvedReason",
    "CtgovCUnsupportedAtom",
    "CtgovCUnsupportedReason",
    "project_ctgov_c_design_observations",
]
