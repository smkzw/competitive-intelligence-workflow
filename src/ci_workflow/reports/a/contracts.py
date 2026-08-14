"""Task 5.1 A 类项目合同与成熟度递增字段规格。

本合同只描述 A 报告的项目身份、成熟度分层与逐层必需字段；不检索来源、
不生成报告。成熟度与结果承载判定直接消费 Phase 3 已接受的
``ApplicableUniverseSnapshot`` 与 ``GateEvidenceBinding``，不允许调用方手工
降级、删除项目、填写成熟度/result-bearing 或用空值冒充。

分层语义（§12.2 证据门槛，逐层递增必需字段）：
- 所有项目：规范身份与别名、创新本体纳排、靶点/机制、模态、当前开发者/
  原研方、适应症关系、中国和境外最高阶段/状态及日期；
- 临床项目：上述字段，加适用的核心试验身份、开发角色和状态；
- 申报/上市/终止项目：上述字段，加适用的申报、批准、撤回、终止或放弃
  事件及地域；
- 已公开结果的成熟项目：上述字段，加适格锚定试验、可解释核心疗效记录与
  TEAE/SAE 数值摘要记录（含组别、对照、时间点/窗口和分母），全部由已接受
  证据绑定判定。

不适用只能显式表达（``EvidenceField`` 的互斥状态），且仅限规格声明允许的
字段；未公开、检索后未找到、技术不可用是独立状态，均视为必需字段缺失。
官方登记"已发布结果"只能由强类型只读证据（``RegistryResultsPostedEvidence``）
表达，不接受自由布尔或未知试验。
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.enums import FactReviewState
from ci_workflow.gates.models import SourceRole
from ci_workflow.reports.common.evidence_view import EvidenceField


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("A 项目合同文本字段不能为空")
    return normalized


class MaturityLevel(StrEnum):
    """A 报告成熟度分层：必需字段随分层逐层递增。"""

    ALL_PROJECTS = "all_projects"
    CLINICAL = "clinical"
    FILING_APPROVAL_TERMINATION = "filing_approval_termination"
    RESULT_BEARING = "result_bearing"


_MATURITY_RANK: dict[MaturityLevel, int] = {
    MaturityLevel.ALL_PROJECTS: 1,
    MaturityLevel.CLINICAL: 2,
    MaturityLevel.FILING_APPROVAL_TERMINATION: 3,
    MaturityLevel.RESULT_BEARING: 4,
}


class RequiredFieldKey(StrEnum):
    """A 报告必需字段封闭集合；按成熟度层归属，逐层递增。"""

    # L1 所有项目
    CANONICAL_IDENTITY_AND_ALIASES = "canonical_identity_and_aliases"
    INNOVATION_ELIGIBILITY = "innovation_eligibility"
    TARGET_MECHANISM = "target_mechanism"
    MODALITY = "modality"
    DEVELOPER_ORIGINATOR = "developer_originator"
    INDICATION_RELATION = "indication_relation"
    CHINA_STAGE_STATUS_DATE = "china_stage_status_date"
    OVERSEAS_STAGE_STATUS_DATE = "overseas_stage_status_date"
    # L2 临床项目
    CORE_TRIAL_IDENTITY = "core_trial_identity"
    CORE_TRIAL_DEVELOPMENT_ROLE = "core_trial_development_role"
    CORE_TRIAL_STATUS = "core_trial_status"
    # L3 申报/上市/终止项目
    REGULATORY_EVENT = "regulatory_event"
    REGULATORY_EVENT_JURISDICTION = "regulatory_event_jurisdiction"
    REGULATORY_EVENT_DATE = "regulatory_event_date"
    # L4 已公开结果的成熟项目
    ANCHOR_TRIAL = "anchor_trial"
    CORE_EFFICACY_RECORD = "core_efficacy_record"
    SAFETY_SUMMARY_RECORD = "safety_summary_record"


# L1 常量导出（测试与视图消费）
CANONICAL_IDENTITY_AND_ALIASES = RequiredFieldKey.CANONICAL_IDENTITY_AND_ALIASES
INNOVATION_ELIGIBILITY = RequiredFieldKey.INNOVATION_ELIGIBILITY
TARGET_MECHANISM = RequiredFieldKey.TARGET_MECHANISM
MODALITY = RequiredFieldKey.MODALITY
DEVELOPER_ORIGINATOR = RequiredFieldKey.DEVELOPER_ORIGINATOR
INDICATION_RELATION = RequiredFieldKey.INDICATION_RELATION
CHINA_STAGE_STATUS_DATE = RequiredFieldKey.CHINA_STAGE_STATUS_DATE
OVERSEAS_STAGE_STATUS_DATE = RequiredFieldKey.OVERSEAS_STAGE_STATUS_DATE
# L2 常量导出
CORE_TRIAL_IDENTITY = RequiredFieldKey.CORE_TRIAL_IDENTITY
CORE_TRIAL_DEVELOPMENT_ROLE = RequiredFieldKey.CORE_TRIAL_DEVELOPMENT_ROLE
CORE_TRIAL_STATUS = RequiredFieldKey.CORE_TRIAL_STATUS
# L3 常量导出
REGULATORY_EVENT = RequiredFieldKey.REGULATORY_EVENT
REGULATORY_EVENT_JURISDICTION = RequiredFieldKey.REGULATORY_EVENT_JURISDICTION
REGULATORY_EVENT_DATE = RequiredFieldKey.REGULATORY_EVENT_DATE
# L4 常量导出
ANCHOR_TRIAL = RequiredFieldKey.ANCHOR_TRIAL
CORE_EFFICACY_RECORD = RequiredFieldKey.CORE_EFFICACY_RECORD
SAFETY_SUMMARY_RECORD = RequiredFieldKey.SAFETY_SUMMARY_RECORD


class RequiredFieldSpec(BaseModel):
    """一个必需字段的规格：归属层、中文标签、描述与不适用许可。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    key: RequiredFieldKey
    layer: MaturityLevel
    label_zh: str
    description_zh: str
    allows_not_applicable: bool = False

    @field_validator("label_zh", "description_zh")
    @classmethod
    def _spec_text_is_not_blank(cls, value: str) -> str:
        return _text(value)


REQUIRED_FIELD_SPECS: tuple[RequiredFieldSpec, ...] = (
    # ── L1 所有项目 ─────────────────────────────────────────────────────────
    RequiredFieldSpec(
        key=CANONICAL_IDENTITY_AND_ALIASES,
        layer=MaturityLevel.ALL_PROJECTS,
        label_zh="规范身份与别名",
        description_zh="项目规范名称、别名与身份依据由已闭合宇宙绑定，构造即满足。",
    ),
    RequiredFieldSpec(
        key=INNOVATION_ELIGIBILITY,
        layer=MaturityLevel.ALL_PROJECTS,
        label_zh="创新本体纳排",
        description_zh="仅纳入已通过创新本体资格的项目；政策与规则版本由已接受判定绑定。",
    ),
    RequiredFieldSpec(
        key=TARGET_MECHANISM,
        layer=MaturityLevel.ALL_PROJECTS,
        label_zh="靶点/机制",
        description_zh="项目的明确靶点与作用机制。",
    ),
    RequiredFieldSpec(
        key=MODALITY,
        layer=MaturityLevel.ALL_PROJECTS,
        label_zh="模态",
        description_zh="项目的药物模态（创新抗体、多抗、融合蛋白、ADC、创新小分子等）。",
    ),
    RequiredFieldSpec(
        key=DEVELOPER_ORIGINATOR,
        layer=MaturityLevel.ALL_PROJECTS,
        label_zh="当前开发者/原研方",
        description_zh="当前开发者与原研方；仅暂停/终止/撤回项目可整组显式声明不适用。",
        allows_not_applicable=True,
    ),
    RequiredFieldSpec(
        key=INDICATION_RELATION,
        layer=MaturityLevel.ALL_PROJECTS,
        label_zh="适应症关系",
        description_zh="项目与目标适应症的关系（核心竞品/邻近观察）。",
    ),
    RequiredFieldSpec(
        key=CHINA_STAGE_STATUS_DATE,
        layer=MaturityLevel.ALL_PROJECTS,
        label_zh="中国最高阶段/状态及日期",
        description_zh="中国开发最高阶段、状态与日期；未在中国开发可整组显式声明不适用，"
        "但不得与同地域监管事件矛盾。",
        allows_not_applicable=True,
    ),
    RequiredFieldSpec(
        key=OVERSEAS_STAGE_STATUS_DATE,
        layer=MaturityLevel.ALL_PROJECTS,
        label_zh="境外最高阶段/状态及日期",
        description_zh="境外开发最高阶段、状态与日期；未在境外开发可整组显式声明不适用，"
        "但不得与同地域监管事件矛盾。",
        allows_not_applicable=True,
    ),
    # ── L2 临床项目 ─────────────────────────────────────────────────────────
    RequiredFieldSpec(
        key=CORE_TRIAL_IDENTITY,
        layer=MaturityLevel.CLINICAL,
        label_zh="核心试验身份",
        description_zh="临床项目适用的核心试验身份（登记号/稳定标识），必须属于本产品"
        "与已闭合宇宙快照。",
    ),
    RequiredFieldSpec(
        key=CORE_TRIAL_DEVELOPMENT_ROLE,
        layer=MaturityLevel.CLINICAL,
        label_zh="核心试验开发角色",
        description_zh="核心试验的开发角色（关键/注册、支持性、决策相关早期）。",
    ),
    RequiredFieldSpec(
        key=CORE_TRIAL_STATUS,
        layer=MaturityLevel.CLINICAL,
        label_zh="核心试验状态",
        description_zh="核心试验的开发状态。",
    ),
    # ── L3 申报/上市/终止项目 ───────────────────────────────────────────────
    RequiredFieldSpec(
        key=REGULATORY_EVENT,
        layer=MaturityLevel.FILING_APPROVAL_TERMINATION,
        label_zh="申报/批准/撤回/终止/放弃事件",
        description_zh="适用的申报、批准、撤回、终止或放弃事件。",
    ),
    RequiredFieldSpec(
        key=REGULATORY_EVENT_JURISDICTION,
        layer=MaturityLevel.FILING_APPROVAL_TERMINATION,
        label_zh="事件地域",
        description_zh="监管事件所属地域（中国/境外）；必须与事件日期由同一条事件提供。",
    ),
    RequiredFieldSpec(
        key=REGULATORY_EVENT_DATE,
        layer=MaturityLevel.FILING_APPROVAL_TERMINATION,
        label_zh="事件日期",
        description_zh="监管事件的发生日期；必须与事件地域由同一条事件提供。",
    ),
    # ── L4 已公开结果的成熟项目 ─────────────────────────────────────────────
    RequiredFieldSpec(
        key=ANCHOR_TRIAL,
        layer=MaturityLevel.RESULT_BEARING,
        label_zh="适格锚定试验",
        description_zh="承载已公开结果的目标适应症适格试验，作为 A 概览锚定；必须是本"
        "产品核心试验且证据版本可在已接受绑定或已发布结果证据中找到。",
    ),
    RequiredFieldSpec(
        key=CORE_EFFICACY_RECORD,
        layer=MaturityLevel.RESULT_BEARING,
        label_zh="核心疗效记录",
        description_zh="可解释的核心疗效终点记录，由已接受绑定判定：原始定义、方向、"
        "单位、时间点、分析人群、治疗组、适用时的对照组和分母。",
    ),
    RequiredFieldSpec(
        key=SAFETY_SUMMARY_RECORD,
        layer=MaturityLevel.RESULT_BEARING,
        label_zh="TEAE/SAE 数值摘要",
        description_zh="TEAE 或 SAE 数值摘要记录，由已接受绑定判定：事件定义、时间窗、"
        "治疗组、适用时的对照组和分母，并携带报告值/零或准确未报告/阈值状态。",
    ),
)

_SPEC_BY_KEY: dict[RequiredFieldKey, RequiredFieldSpec] = {
    spec.key: spec for spec in REQUIRED_FIELD_SPECS
}


def required_fields_for(level: MaturityLevel) -> tuple[RequiredFieldKey, ...]:
    """返回指定成熟度层适用的全部必需字段（含更低层的累计字段）。"""
    rank = _MATURITY_RANK[level]
    return tuple(spec.key for spec in REQUIRED_FIELD_SPECS if _MATURITY_RANK[spec.layer] <= rank)


def assert_ladder_monotonic() -> None:
    """校验成熟度分层逐层严格增加必需字段；违反即合同错误。"""
    previous: tuple[RequiredFieldKey, ...] = ()
    for level in MaturityLevel:
        current = required_fields_for(level)
        if not set(current) > set(previous):
            raise ValueError(f"成熟度层 {level.value} 必须严格增加必需字段")
        previous = current


class CoreTrialRole(StrEnum):
    """核心试验开发角色封闭集合。"""

    REGISTRATION_OR_PIVOTAL = "registration_or_pivotal"
    SUPPORTING = "supporting"
    EARLY_DECISION = "early_decision"


class CoreTrialRecord(BaseModel):
    """临床项目核心试验：身份、开发角色与状态齐备；试验作用域由评估闭合。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trial_id: str
    role: CoreTrialRole
    status: str

    @field_validator("trial_id", "status")
    @classmethod
    def _record_text_is_not_blank(cls, value: str) -> str:
        return _text(value)


class RegulatoryEventKind(StrEnum):
    """监管事件类型封闭集合：申报、批准、撤回、终止、放弃、暂停。"""

    SUBMISSION = "submission"
    APPROVAL = "approval"
    WITHDRAWAL = "withdrawal"
    TERMINATION = "termination"
    ABANDONMENT = "abandonment"
    PAUSE = "pause"


class RegulatoryEventRecord(BaseModel):
    """申报/上市/终止项目的一个监管事件；地域与日期必须由同一事件同时满足。

    ``event_id`` 是事件的稳定不可变身份：版本化监管记录按该 ID 精确绑定，
    禁止用「类型+地域+日期」的计数配对冒充事件身份。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    event_kind: RegulatoryEventKind
    jurisdiction: EvidenceField
    event_date: EvidenceField

    @field_validator("event_id")
    @classmethod
    def _event_id_is_not_blank(cls, value: str) -> str:
        return _text(value)


class AnchorTrialRecord(BaseModel):
    """结果承载项目的适格锚定试验；必须绑定已接受证据版本。

    证据版本必须能在本产品该试验的已接受绑定或已发布结果证据中找到；
    不允许任意片段标识冒充。试验作用域由评估闭合。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    trial_id: str
    fact_version_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("trial_id")
    @classmethod
    def _trial_id_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("fact_version_ids")
    @classmethod
    def _fact_version_ids_are_text(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_text(value) for value in values)


class SafetyEventUnitId(StrEnum):
    """安全性摘要的规则单元标识；最低记录只认 TEAE 与 SAE。"""

    TEAE = "a_safety_event_teae"
    SAE = "a_safety_event_sae"


class SafetyMeasurementUnit(StrEnum):
    """安全性结果的规范测量单位；与 TEAE/SAE 事件类别分开保存。"""

    PERCENT = "%"
    PARTICIPANT_COUNT = "例"
    EVENT_COUNT = "事件数"
    EXPOSURE_ADJUSTED_RATE = "每100患者年"


class RegistryResultsPostedEvidence(BaseModel):
    """官方登记"已发布结果"的强类型只读证据（§12.2 例外）。

    必须绑定产品、试验、不可变事实版本、精确来源定位，来源角色固定为官方
    试验登记、审查状态固定为已接受、标志固定为真；不得用自由布尔或未知
    试验。评估时校验产品—试验关系：未知试验或引用其他产品的试验失败关闭。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    trial_id: str
    fact_version_id: str
    source_location: str
    source_role: Literal[SourceRole.CLINICAL_TRIAL_REGISTRY] = SourceRole.CLINICAL_TRIAL_REGISTRY
    review_state: Literal[FactReviewState.ACCEPTED] = FactReviewState.ACCEPTED
    official_results_posted: Literal[True] = True

    @field_validator("project_id", "trial_id", "fact_version_id", "source_location")
    @classmethod
    def _registry_evidence_text_is_not_blank(cls, value: str) -> str:
        return _text(value)


class RegionDevelopment(BaseModel):
    """一个区域（中国/境外）的最高阶段、状态与日期。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    highest_stage: EvidenceField
    highest_status: EvidenceField
    date: EvidenceField


class AProjectContract(BaseModel):
    """A 报告项目合同：身份、资格与各成熟度层的契约字段载荷。

    成熟度与 result-bearing 不由合同携带：评估层从当前不可变快照与已接受
    绑定确定性推导，任何手工填写的成熟度/结果承载字段都是 extra 并被拒绝。
    合同构造即拒绝：空白文本、非纳入资格。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    canonical_name: str
    aliases: tuple[str, ...] = ()
    aliases_absence_basis: str | None = None
    identity_basis: str

    eligibility: Literal["included"]
    eligibility_policy_id: str
    eligibility_rule_id: str

    target_mechanism: EvidenceField
    modality: EvidenceField
    developer: EvidenceField
    originator: EvidenceField
    indication_relation: EvidenceField

    china: RegionDevelopment
    overseas: RegionDevelopment

    core_trials: tuple[CoreTrialRecord, ...] = ()
    regulatory_events: tuple[RegulatoryEventRecord, ...] = ()
    anchor_trials: tuple[AnchorTrialRecord, ...] = ()

    @field_validator("project_id", "canonical_name", "identity_basis")
    @classmethod
    def _identity_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("aliases")
    @classmethod
    def _aliases_are_unique_text(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(_text(item) for item in values))

    @field_validator("aliases_absence_basis")
    @classmethod
    def _optional_alias_basis_is_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _text(value)

    @model_validator(mode="after")
    def _aliases_or_explicit_absence_are_required(self) -> Self:
        if self.aliases and self.aliases_absence_basis is not None:
            raise ValueError("已有别名时不得同时声明无别名依据")
        if not self.aliases and self.aliases_absence_basis is None:
            raise ValueError("没有已识别别名时必须保存明确的无别名检索依据")
        return self

    @field_validator("eligibility_policy_id", "eligibility_rule_id")
    @classmethod
    def _eligibility_text_is_not_blank(cls, value: str) -> str:
        return _text(value)
