"""领域模型。所有阶段之间只传这些对象；release.json 是它们的序列化。"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ArmRole = Literal["experimental", "active_comparator", "placebo", "no_intervention", "other", "unknown"]
Period = Literal["treatment", "run_in", "follow_up", "extension", "overall"]
VerifyStatus = Literal["registry", "verified", "dual_agreed", "arbitrated", "needs_review", "rejected"]
SourceKind = Literal["ctgov", "europepmc", "openfda", "cde", "nmpa", "company", "wechat"]


def stable_id(prefix: str, *parts: object) -> str:
    raw = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
    return f"{prefix}_{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(Model):
    source_id: str
    kind: SourceKind
    url: str
    title: str = ""
    publisher: str = ""
    published_at: str | None = None
    fetched_at: str
    sha256: str


class Locator(Model):
    source_id: str
    path: str = ""  # JSON 路径（结构化来源）
    quote: str = ""  # 原文片段（非结构化来源）


class Arm(Model):
    arm_id: str
    label: str
    type: str = ""  # CT.gov armGroups.type 原值
    role: ArmRole = "unknown"
    description: str = ""
    interventions: list[str] = Field(default_factory=list)
    product_ids: list[str] = Field(default_factory=list)


class PlannedOutcome(Model):
    kind: Literal["primary", "secondary", "other"]
    title: str
    timeframe: str = ""
    description: str = ""
    concept_id: str | None = None


class Design(Model):
    allocation: str = ""
    model: str = ""
    masking: str = ""
    masked_roles: list[str] = Field(default_factory=list)
    purpose: str = ""
    brief_summary: str = ""
    detailed_description: str = ""
    model_description: str = ""
    enrollment: int | None = None
    enrollment_text: str = ""
    enrollment_type: str = ""
    eligibility_text: str = ""
    min_age: str = ""
    max_age: str = ""
    sex: str = ""
    healthy_volunteers: bool | None = None
    arm_count: int = 0
    background_therapy: list[str] = Field(default_factory=list)


class TrialDates(Model):
    start: str | None = None
    primary_completion: str | None = None
    completion: str | None = None
    first_posted: str | None = None
    results_first_posted: str | None = None
    last_update: str | None = None


class Trial(Model):
    trial_id: str
    registry: Literal["ctgov", "cde"]
    ids: dict[str, str] = Field(default_factory=dict)
    acronym: str = ""
    title: str = ""
    official_title: str = ""
    phase: str = ""  # 规范化后的显示期别，例如 "III"、"II/III"
    phase_rank: int = 0  # 排序用：0 未知/NA … 5 IV
    status: str = ""
    dates: TrialDates = Field(default_factory=TrialDates)
    sponsor: str = ""
    sponsor_class: str = ""
    collaborators: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    china: bool = False
    conditions: list[str] = Field(default_factory=list)
    design: Design = Field(default_factory=Design)
    arms: list[Arm] = Field(default_factory=list)
    outcomes_planned: list[PlannedOutcome] = Field(default_factory=list)
    product_ids: list[str] = Field(default_factory=list)
    has_results: bool = False
    relevance: Literal["core", "background"] = "core"
    relevance_reason: str = ""
    url: str = ""
    locator: Locator
    registrations: list[Trial] = Field(default_factory=list)


class Product(Model):
    product_id: str
    name_en: str
    name_zh: str = ""
    codes: list[str] = Field(default_factory=list)
    brand: str = ""
    target: str = ""
    mechanism: str = ""
    modality: str = ""
    route: str = ""
    company: str = ""
    china_partner: str = ""
    innovative: bool | None = True
    is_own: bool = False
    inclusion_reason: str = ""
    attribute_status: VerifyStatus | Literal["config"] = "config"
    attribute_locators: dict[str, Locator] = Field(default_factory=dict)
    trial_ids: list[str] = Field(default_factory=list)


class TimePoint(Model):
    raw: str
    label: str  # 中文显示，例如 “第24周”
    key: str  # 分组键，例如 “W24”、“W49-52”、“D169”
    weeks: float | None = None


class GroupValue(Model):
    group_id: str
    title: str
    arm_id: str | None = None
    role: ArmRole = "unknown"
    period: Period = "treatment"
    product_id: str | None = None
    n: int | None = None  # 该组该指标的分析人数
    value: float | None = None
    value_raw: str = ""
    spread: float | None = None
    lower: float | None = None
    upper: float | None = None
    path: str = ""


class Analysis(Model):
    group_ids: list[str]
    param_type: str = ""
    value: float | None = None
    value_raw: str = ""
    ci_pct: float | None = None
    ci_lower: float | None = None
    ci_upper: float | None = None
    p_value: str = ""
    method: str = ""
    test_type: str = ""
    path: str = ""
    minuend_group_id: str | None = None  # 来源明确差值方向，不从舍入后的均值反推
    subtrahend_group_id: str | None = None
    direction_evidence: str = ""  # 同段原文的有序组别与均值差表达，不由舍入均值相减推断


class OutcomeResult(Model):
    result_id: str
    trial_id: str
    outcome_index: int
    type: str  # PRIMARY / SECONDARY / OTHER_PRE_SPECIFIED / POST_HOC
    title: str
    description: str = ""
    timeframe: str = ""
    time: TimePoint | None = None
    class_title: str = ""  # 多 class（常为时间点或亚组）的原始标题
    category_title: str = ""
    subgroup: str = ""  # 亚组限定原文（标题中的 subgroup/in participants with…，或非时间含义的 class 标题）
    concept_id: str | None = None
    domain: Literal["efficacy", "safety", "pk", "pd", "immunogenicity", "other"] = "other"
    measure_kind: str  # mean / ls_mean / median / proportion / count / geometric_mean / other
    param_type: str = ""
    dispersion_type: str = ""
    unit: str = ""
    population: str = ""
    groups: list[GroupValue] = Field(default_factory=list)
    analyses: list[Analysis] = Field(default_factory=list)
    status: VerifyStatus = "registry"
    kind: Literal["registry", "publication"] = "registry"
    source_url: str = ""
    locator: Locator


class CountN(Model):
    n: int | None = None
    N: int | None = None


class SafetyGroup(Model):
    group_id: str
    title: str
    arm_id: str | None = None
    role: ArmRole = "unknown"
    period: Period = "treatment"
    product_id: str | None = None
    serious: CountN = Field(default_factory=CountN)
    other: CountN = Field(default_factory=CountN)
    deaths: CountN = Field(default_factory=CountN)


class AETermStat(Model):
    group_id: str
    n: int | None = None
    N: int | None = None
    events: int | None = None


class AETerm(Model):
    term: str
    organ_system: str = ""
    serious: bool
    stats: list[AETermStat] = Field(default_factory=list)


class Discontinuation(Model):
    """参与者流程中因不良事件退出（participantFlowModule.dropWithdraws, type=Adverse Event）。"""

    group_id: str
    title: str
    role: ArmRole = "unknown"
    product_id: str | None = None
    n: int | None = None
    N: int | None = None  # 首个时期 STARTED


class SafetySummary(Model):
    trial_id: str
    timeframe: str = ""
    description: str = ""
    other_threshold: float | None = None
    groups: list[SafetyGroup] = Field(default_factory=list)
    terms: list[AETerm] = Field(default_factory=list)
    discontinuations: list[Discontinuation] = Field(default_factory=list)
    status: VerifyStatus = "registry"
    locator: Locator


class Event(Model):
    """非结构化来源里的里程碑事件（获批、递交、topline、开始入组、授权许可）。"""

    event_id: str
    product_id: str | None
    product_mention: str
    event_type: Literal["approval", "filing", "topline", "phase_start", "licensing", "other"]
    region: str = ""
    date: str | None = None
    indication: str = ""
    detail: str = ""
    quote: str = ""
    status: VerifyStatus
    source_id: str


class Verification(Model):
    fact_key: str
    status: VerifyStatus
    calls: list[dict[str, Any]] = Field(default_factory=list)
    note: str = ""
