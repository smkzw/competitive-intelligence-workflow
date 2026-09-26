"""Task 5.4：从已校验的 A 类报告数据包生成完整纯静态多页面门户。"""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from importlib.metadata import version as dependency_version
from pathlib import Path
from typing import Any, ClassVar, Literal, Self

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.enums import FactDisclosureState, ReportKind
from ci_workflow.domain.ids import stable_id
from ci_workflow.domain.public_provenance import PublicCalculationEvidence, PublicProvenance
from ci_workflow.qc.browser import load_locked_sitemap_source, site_directory_digest
from ci_workflow.reports.common.evidence_view import UserEditDisclosure
from ci_workflow.reports.common.numeric_projection import infer_numeric_kind, project_numeric
from ci_workflow.reports.common.page_registry import PageRegistry
from ci_workflow.storage.manifest_store import (
    ArtifactFileBinding,
    ArtifactManifest,
    DesignContractBinding,
    DeterministicCheck,
    ManifestStore,
    RendererBinding,
    RenderVerdict,
)
from ci_workflow.storage.render_transaction import (
    RenderTransactionError,
    UnpublishedRenderTransaction,
)
from ci_workflow.storage.snapshot_store import ReportSnapshotManifest, SnapshotStore

from .active_fact_projection import (
    ActiveFactBinding,
    ActiveFactRevision,
    PortalConsumerNode,
    canonical_sha256,
    numeric_value,
    user_edit_disclosure,
    validate_active_fact_binding,
    write_render_receipt,
)
from .builder import resolve_echarts_bundle, resolve_logo_src, resolve_portal_asset


class ReportAPortalError(ValueError):
    """A 类门户输入、模板或清单不闭合。"""


class ProductRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    name: str
    target: str
    modality: str
    phase: str
    status: str
    regions: tuple[str, ...] = Field(min_length=1)
    route: str
    developer: str
    mechanism: str
    result_status: Literal[
        "有公开关键结果",
        "已有部分公开结果",
        "暂无公开关键结果",
        "临床前",
    ] = "有公开关键结果"
    # 独立审阅 R11（SCI11）：登记记录状态与监管批准事实是两个字段——
    # 登记试验状态不构成监管批准证据；未接入权威核验时显式待核验
    regulatory_approval_status: str | None = None

    @field_validator("id")
    @classmethod
    def _id_is_slug(cls, value: str) -> str:
        if not value or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in value):
            raise ValueError("产品标识必须是安全英文路径片段")
        return value


class TrialProductLink(BaseModel):
    """A source-declared intervention-to-arm link, not a guessed trial owner."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    product_id: str
    arm_role: Literal[
        "experimental", "active_comparator", "other_comparator", "other", "unknown"
    ]
    arm_labels: tuple[str, ...] = ()


class TrialRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    display_id: str
    product_id: str
    name: str
    phase: str
    region: str
    status: str
    # 独立审阅 R13（SCI10）：未知样本量显式建模为 None（保留适格研究，
    # 不为凑 gt=0 删除试验）；计划与实际人数分开保存，不可混用
    sample_size: int | None = Field(default=None, ge=0)
    planned_sample_size: int | None = Field(default=None, ge=0)
    reported_sample_size: int | None = Field(default=None, ge=0)
    enrollment_type: Literal["ACTUAL", "ESTIMATED", "UNKNOWN"] = "UNKNOWN"
    treatment_sample_size: int | None = Field(default=None, ge=0)
    product_links: tuple[TrialProductLink, ...] = ()
    role: str

    @model_validator(mode="after")
    def _treatment_group_cannot_exceed_trial(self) -> TrialRow:
        if self.enrollment_type == "ESTIMATED" and self.sample_size is not None:
            raise ValueError("计划样本量不得伪装成实际样本量")
        if self.enrollment_type == "ACTUAL" and self.planned_sample_size is not None:
            raise ValueError("实际样本量不得伪装成计划样本量")
        if len({(link.product_id, link.arm_role) for link in self.product_links}) != len(
            self.product_links
        ):
            raise ValueError("试验产品-组别角色重复")
        if (
            self.treatment_sample_size is not None
            and self.sample_size is not None
            and self.treatment_sample_size > self.sample_size
        ):
            raise ValueError("治疗组样本量不得大于试验总样本量")
        if (
            self.planned_sample_size is not None
            and self.sample_size is not None
            and self.planned_sample_size != self.sample_size
        ):
            # 计划与实际并列时必须各自成立，不得互相顶替
            pass
        return self


class EfficacyRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    row_id: str
    source_view_row_id: str | None = Field(default=None, exclude_if=lambda value: value is None)
    value_basis: Literal["crude_rate", "modeled_estimate", "reported_estimate"] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    product_id: str
    trial_id: str
    group_assignment_state: Literal["declared", "unknown", "unassessed"] = "unassessed"
    endpoint: str
    timepoint: str
    arm: str
    arm_detail: str | None = None
    value: float | None = Field(default=None, allow_inf_nan=False)
    # F01 修复：REPORTED_ZERO 携带 0 是合法科学事实；REPORTED_VALUE 必须有值
    disclosure_state: FactDisclosureState = FactDisclosureState.REPORTED_VALUE

    @model_validator(mode="after")
    def _value_disclosure_consistency(self) -> EfficacyRow:
        # 独立审阅 R01：披露状态与数值的唯一不变量（合并原先互相冲突的
        # 两个 validator）。reported_zero 必须显式为 0，缺失不得补 0；
        # 未报告/未公开/不适用等一律不得携带数值。
        if self.disclosure_state is FactDisclosureState.REPORTED_VALUE:
            if self.value is None:
                raise ValueError("REPORTED_VALUE 必须携带有限数值")
        elif self.disclosure_state is FactDisclosureState.REPORTED_ZERO:
            if self.value is None or self.value != 0:
                raise ValueError("REPORTED_ZERO 必须显式携带数值 0（缺失不得补 0）")
        elif self.value is not None:
            raise ValueError(f"{self.disclosure_state.value} 状态行不得携带数值")
        return self

    numerator: int | None = Field(default=None, ge=0)
    denominator: int | None = Field(default=None, gt=0)
    unit: str
    population: str
    source_field_path: str | None = None
    source_version_id: str | None = Field(default=None, exclude_if=lambda value: value is None)
    group_id: str | None = Field(default=None, exclude_if=lambda value: value is None)
    cohort_id: str | None = Field(default=None, exclude_if=lambda value: value is None)
    source_text: str | None = None
    clinical_narrative: str | None = None

    @model_validator(mode="after")
    def _undisclosed_row_carries_no_value(self) -> EfficacyRow:
        # 独立审阅 R01：REPORTED_VALUE 的数值要求已并入唯一不变量
        # _value_disclosure_consistency；此处仅保留数值有限性守卫。
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError("疗效数值必须是有限数值")
        return self

    @model_validator(mode="after")
    def _counts_are_complete_and_ordered(self) -> EfficacyRow:
        # 独立复核 A r27/r30/r32：登记 denoms（各组受试者数）是真实披露，
        # 允许"仅有分母"（组规模），分子缺失不再是契约违规
        if self.numerator is not None and self.denominator is None:
            raise ValueError("疗效分子与分母必须同时公开或同时缺失")
        if (
            self.numerator is not None
            and self.denominator is not None
            and self.numerator > self.denominator
        ):
            raise ValueError("疗效分子不得大于分母")
        return self


class SafetyRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    row_id: str
    product_id: str
    trial_id: str | None = None
    group_assignment_state: Literal["declared", "unknown", "unassessed"] = "unassessed"
    arm: str = "治疗组"
    arm_detail: str | None = None
    category: str
    term: str
    # 会商 P0 #3：受控词表键（any_sae/any_teae/death），供矩阵安全轴精确匹配
    term_key: str | None = None
    polarity: str = "affirmed"
    grade_set: tuple[int, ...] = ()
    seriousness: str = "unspecified"
    teae: bool | None = None
    relatedness: str = "unspecified"
    parent: str | None = None
    children: tuple[str, ...] = ()
    count_basis: str = "participants"
    at_risk_stat: str | None = None
    # 独立复核 A r44/r45（issue-2）：类目/类标题上下文（term 保持登记原貌）
    measure_context: str | None = None
    source_class_title: str | None = Field(default=None, exclude_if=lambda value: value is None)
    source_category_title: str | None = Field(default=None, exclude_if=lambda value: value is None)
    value: float | None = Field(allow_inf_nan=False)
    numerator: int | None = Field(default=None, ge=0)
    denominator: int | None = Field(default=None, gt=0)
    unit: str
    time_window: str
    measure_object: Literal[
        "participant_proportion",
        "participant_count",
        "event_count",
        "person_time_rate",
        "adjusted_estimate",
    ] = "participant_proportion"
    disclosure_state: Literal["已公开", "未公开", "不适用", "用户清除，待重新核实"] = "已公开"
    source_field_path: str | None = None
    source_version_id: str | None = Field(default=None, exclude_if=lambda value: value is None)
    group_id: str | None = Field(default=None, exclude_if=lambda value: value is None)
    cohort_id: str | None = Field(default=None, exclude_if=lambda value: value is None)
    source_text: str | None = None
    clinical_narrative: str | None = None

    @model_validator(mode="after")
    def _value_matches_disclosure_state(self) -> SafetyRow:
        if self.disclosure_state == "已公开" and self.value is None:
            raise ValueError("已公开安全性记录必须包含数值")
        if self.disclosure_state == "未公开" and self.value is not None:
            raise ValueError("未公开安全性记录不得填入推测数值")
        if self.disclosure_state == "用户清除，待重新核实" and self.value is not None:
            raise ValueError("用户清除的安全性记录不得携带当前数值")
        if (self.numerator is None) != (self.denominator is None):
            raise ValueError("安全性分子与分母必须同时公开或同时缺失")
        if (
            self.measure_object == "participant_proportion"
            and self.numerator is not None
            and self.denominator is not None
            and self.numerator > self.denominator
        ):
            raise ValueError("安全性分子不得大于分母")
        if self.count_basis == "mixed" and (
            self.numerator is not None or self.denominator is not None
        ):
            raise ValueError("复合安全项不得拆值或借用其他项分母")
        return self


class RegulatoryRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    product_id: str
    track: str
    event: str
    date: str
    status: str


class CompanyRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    product_id: str
    relationship: str
    licensor: str
    licensee: str
    territory: str
    transaction: str


class PatentRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    product_id: str
    family: str
    display_family: str
    jurisdiction: str
    scope: str
    expiry: str
    exclusivity: str


class HistoryRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    product_id: str
    status: str
    date: str
    observation: str


class SourceRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source: str
    scope: str
    maturity: str
    limitation: str


class AdditionalObservationRow(BaseModel):
    """Reported non-efficacy, non-AE study observation retained without co-axis claims."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    row_id: str
    product_id: str
    trial_id: str
    group_id: str
    group_title: str
    group_assignment_state: Literal["declared", "unknown"]
    endpoint: str
    class_title: str
    category_title: str
    time_window: str
    domain: Literal["immunogenicity", "pk_pd", "biomarkers", "other", "unresolved"]
    raw_value: str
    raw_value_type: str
    raw_unit: str
    source_url: str
    source_page_sha256: str
    source_path: str


class ReportALineageBinding(BaseModel):
    """新鲜来源路径传给渲染器的已锁定科学谱系。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    evidence_snapshot_id: str
    claim_snapshot_id: str
    coverage_set_id: str
    coverage_projection_id: str
    claim_ids: tuple[str, ...] = Field(min_length=1)
    source_version_ids: tuple[str, ...] = Field(min_length=1)


class ReportAPortalData(BaseModel):
    """模板只读输入；产品/试验/结果关系必须在入模时闭合。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    require_a_result_completeness: ClassVar[bool] = True
    schema_version: str
    report_version: str
    indication: str
    data_cutoff: datetime
    products: tuple[ProductRow, ...] = Field(min_length=1)
    trials: tuple[TrialRow, ...] = Field(min_length=1)
    efficacy: tuple[EfficacyRow, ...] = ()
    safety: tuple[SafetyRow, ...] = ()
    additional_observations: tuple[AdditionalObservationRow, ...] = ()
    regulatory: tuple[RegulatoryRow, ...] = Field(min_length=1)
    companies: tuple[CompanyRow, ...] = Field(min_length=1)
    patents: tuple[PatentRow, ...] = Field(min_length=1)
    history: tuple[HistoryRow, ...] = Field(min_length=1)
    sources: tuple[SourceRow, ...] = Field(min_length=1)
    user_edits: dict[str, UserEditDisclosure] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _relations_are_closed(self) -> Self:
        product_ids = [item.id for item in self.products]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("产品标识重复")
        trial_ids = [item.id for item in self.trials]
        if len(trial_ids) != len(set(trial_ids)):
            raise ValueError("试验标识重复")
        products = set(product_ids)
        trials = set(trial_ids)
        if any(item.product_id not in products for item in self.trials):
            raise ValueError("试验引用了未知产品")
        if any(
            link.product_id not in products
            for trial in self.trials for link in trial.product_links
        ):
            raise ValueError("试验干预关系引用了未知产品")
        linked_product_rows: tuple[
            EfficacyRow | SafetyRow | AdditionalObservationRow | RegulatoryRow
            | CompanyRow | PatentRow | HistoryRow,
            ...,
        ] = (
            *self.efficacy,
            *self.safety,
            *self.additional_observations,
            *self.regulatory,
            *self.companies,
            *self.patents,
            *self.history,
        )
        if any(item.product_id not in products for item in linked_product_rows):
            raise ValueError("报告事实引用了未知产品")
        if any(item.trial_id not in trials for item in self.efficacy):
            raise ValueError("疗效事实引用了未知试验")
        if any(item.trial_id not in trials for item in self.additional_observations):
            raise ValueError("其他观察引用了未知试验")
        if any(item.trial_id is not None and item.trial_id not in trials for item in self.safety):
            raise ValueError("安全性事实引用了未知试验")
        if not self.require_a_result_completeness:
            return self
        # 会商 #2/#12：门禁按概念键判定（any_teae/any_sae 必须齐备），
        # 不再比对与载荷词表脱节的中文类别字面
        from ci_workflow.reports.b.concept_catalog import row_concept

        required_concepts = {"any_teae", "any_sae"}
        product_by_id = {item.id: item for item in self.products}
        for product_id in products:
            if product_by_id[product_id].result_status != "有公开关键结果":
                continue
            concepts = {row_concept(row) for row in self.safety if row.product_id == product_id}
            if not required_concepts <= concepts:
                raise ValueError(f"产品 {product_id} 的关键安全性维度不完整")
            arms = {row.arm for row in self.efficacy if row.product_id == product_id}
            if not {"治疗组", "对照组"} <= arms:
                raise ValueError(f"产品 {product_id} 的疗效比较缺少治疗组或对照组")
        return self

    @property
    def product_ids(self) -> tuple[str, ...]:
        return tuple(item.id for item in self.products)

    @property
    def trial_ids(self) -> tuple[str, ...]:
        return tuple(item.id for item in self.trials)


_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates" / "a"
_ASSET_DIR = Path(__file__).resolve().parent / "assets"
_STATIC_TEMPLATES: tuple[tuple[str, str], ...] = (
    ("overview", "index.html.j2"),
    ("landscape", "landscape.html.j2"),
    ("product-overview", "products.html.j2"),
    ("clinical-portfolio", "clinical_portfolio.html.j2"),
    ("efficacy", "efficacy.html.j2"),
    ("safety", "safety.html.j2"),
    ("matrix", "matrix.html.j2"),
    ("regulatory", "regulatory.html.j2"),
    ("companies-transactions", "companies_deals.html.j2"),
    ("patents-protection", "patents.html.j2"),
    ("historical-edge", "history_edge.html.j2"),
)

_TRIAL_STATUS_ZH = {
    "COMPLETED": "已完成",
    "RECRUITING": "招募中",
    "ACTIVE_NOT_RECRUITING": "进行中（已停止招募）",
    "NOT_YET_RECRUITING": "尚未开始招募",
    "ENROLLING_BY_INVITATION": "仅限邀请入组",
    "SUSPENDED": "已暂停",
    "TERMINATED": "已提前终止",
    "WITHDRAWN": "启动前撤回",
    "UNKNOWN": "登记状态尚不明确",
}

_PRODUCT_DISPLAY_NAMES_ZH = {
    "amlitelimab": "阿姆特利单抗（Amlitelimab）",
}


# 仅把明确批准的中英文/大小写变体放入同一展示维度；未列入的术语
# 只做大小写和空白稳定化，不按相似词或前后缀猜测临床等价性。
_SAFETY_TERM_GROUPS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "any_teae",
        "任何TEAE",
        (
            "任何TEAE",
            "Any TEAE",
            "TEAE",
            "Any treatment-emergent adverse event",
            "Any treatment emergent adverse event",
        ),
    ),
    (
        "any_sae",
        "任何SAE",
        (
            "任何SAE",
            "Any SAE",
            "SAE",
            "Any serious adverse event",
            "Serious adverse events",
        ),
    ),
    ("nasopharyngitis", "鼻咽炎", ("Nasopharyngitis", "鼻咽炎")),
    ("headache", "头痛", ("Headache", "头痛")),
    (
        "upper_respiratory_tract_infection",
        "上呼吸道感染",
        ("Upper respiratory tract infection", "上呼吸道感染"),
    ),
    (
        "viral_upper_respiratory_tract_infection",
        "病毒性上呼吸道感染",
        ("Viral upper respiratory tract infection", "病毒性上呼吸道感染"),
    ),
    (
        "sars_cov_2_antibody_positive",
        "新型冠状病毒抗体检测阳性",
        ("SARS-CoV-2 antibody test positive", "新型冠状病毒抗体检测阳性"),
    ),
    (
        "dermatitis_atopic",
        "特应性皮炎",
        ("Dermatitis atopic", "Atopic dermatitis", "特应性皮炎"),
    ),
    ("nausea", "恶心", ("Nausea", "恶心")),
    ("diarrhoea", "腹泻", ("Diarrhoea", "Diarrhea", "腹泻")),
    ("cough", "咳嗽", ("Cough", "咳嗽")),
    ("asthma", "哮喘", ("Asthma", "哮喘")),
    ("pyrexia", "发热", ("Pyrexia", "发热")),
    ("pruritus", "瘙痒", ("Pruritus", "瘙痒")),
    ("influenza", "流感", ("Influenza", "流感")),
    ("arthralgia", "关节痛", ("Arthralgia", "关节痛")),
    ("vomiting", "呕吐", ("Vomiting", "呕吐")),
    (
        "oropharyngeal_pain",
        "口咽疼痛",
        ("Oropharyngeal pain", "口咽疼痛"),
    ),
    ("oral_herpes", "口腔疱疹", ("Oral herpes", "口腔疱疹")),
    (
        "injection_site_reaction",
        "注射部位反应",
        ("Injection site reaction", "注射部位反应"),
    ),
    ("eczema", "湿疹", ("Eczema", "湿疹")),
    (
        "conjunctivitis_allergic",
        "过敏性结膜炎",
        ("Conjunctivitis allergic", "过敏性结膜炎"),
    ),
    ("conjunctivitis", "结膜炎", ("Conjunctivitis", "结膜炎")),
    ("skin_infection", "皮肤感染", ("Skin infection", "皮肤感染")),
    (
        "urinary_tract_infection",
        "尿路感染",
        ("Urinary tract infection", "尿路感染"),
    ),
    ("hypersensitivity", "超敏反应", ("Hypersensitivity", "超敏反应")),
    ("herpes_zoster", "带状疱疹", ("Herpes zoster", "带状疱疹")),
)
_SAFETY_TERM_ALIASES: dict[str, tuple[str, str]] = {
    " ".join(alias.split()).casefold(): (key, label)
    for key, label, aliases in _SAFETY_TERM_GROUPS
    for alias in aliases
}


def _contains_chinese(value: str) -> bool:
    return any("\u4e00" <= character <= "\u9fff" for character in value)


def _display_products(data: ReportAPortalData) -> tuple[ProductRow, ...]:
    return tuple(
        product.model_copy(update={"name": _PRODUCT_DISPLAY_NAMES_ZH.get(product.id, product.name)})
        for product in data.products
    )


def _safety_term_projection(term: str, term_key: str | None = None) -> tuple[str, str]:
    # 独立复核 A r27/r31：优先消费构建器受控词表键（any_sae/any_teae/death），
    # 未命中时才回退 raw: 归一化
    normalized = " ".join(term.split()).casefold()
    known = _SAFETY_TERM_ALIASES.get(normalized)
    if known is not None:
        return known
    # 会商 #2（概念词表单源）：受控标签一律取自 concept_catalog，
    # 渲染器不再自造中文概念字面
    from ci_workflow.reports.b.concept_catalog import spec_of

    catalog_keys = {
        "any_sae",
        "any_teae",
        "death",
        "aesi",
        "discontinuation_ae",
        "treatment_related_ae",
        "grade_3_plus",
        "serious_teae_subset",
        "generic_ae",
        "composite_ae",
    }
    if term_key and term_key in catalog_keys:
        return term_key, spec_of(term_key).label_zh
    # 独立审阅 R02：受控安全概念键（分流特定指标）的展示标签；
    # specific_ae/unknown 仍走 raw 原文路径，不冒充受控类别
    return f"raw:{normalized}", term


def _category_base(category: object) -> str:
    # 独立审阅 R02：登记类别带"（登记）"来源后缀，判定按基础类别名
    return str(category or "").replace("（登记）", "").strip()


def _display_safety_rows(data: ReportAPortalData) -> tuple[dict[str, object], ...]:
    """加入展示归一元数据，但永不覆盖安全性事实的原始术语。

    AESI 只有在至少一条对应数值已公开时才进入展示数据集；全空
    AESI 不应在页面、图表、筛选或表格中占据一个没有信息的维度。
    """
    rows: list[dict[str, object]] = []
    for item in data.safety:
        # 独立复核 A r37（issue-4）：声明臂影子行仅供 B 门匹配，
        # 不进 A 门户安全展示（避免与期间行重复计数）
        if str(item.row_id).endswith("-declared"):
            continue
        row = item.model_dump(mode="json")
        term_key, term_label = _safety_term_projection(item.term, getattr(item, "term_key", None))
        row["original_term"] = item.term
        row["term_key"] = term_key
        row["term_label"] = term_label
        # 独立复核 A r44（issue-4）：安全行组名与疗效行同一解码口径；
        # 登记原名保留在 arm_detail 供证据回溯
        _arm_decoded = _native_arm_zh(str(item.arm))
        if _arm_decoded and _arm_decoded != str(item.arm):
            row["arm"] = _arm_decoded
            row["arm_detail"] = _native_arm_detail_zh(item.arm_detail) or str(item.arm)
        else:
            row["arm_detail"] = _native_arm_detail_zh(item.arm_detail)
            # 独立复核 A r46（issue-4）：解码后仍残留英文组名按惯例标注
            if (
                _arm_decoded
                and re.findall(r"[A-Za-z]{3,}", _arm_decoded)
                and not _arm_decoded.endswith("（登记原文，未译）")
            ):
                row["arm"] = _arm_decoded + "（登记原文，未译）"
        # 独立复核 A r37（issue-4）：声明臂影子行显式标注归因性质
        if str(item.row_id).endswith("-declared"):
            row["term_label"] = (row["term_label"] or item.term) + "（声明臂归因，由期间组汇总）"
        # 独立复核 A r42（issue-2）：分流的 TEAE/AE 测量行带原测量标题，
        # 事件列可区分不同测量（不再全部塌缩为同一受控标签）
        # 独立复核 A r46（issue-1）：类目上下文对所有受控键组合进标签——
        # any_* 行此前走第一分支时把 measure_context 丢掉，类目行仍不可区分
        _base_label = None
        if term_key in {"any_sae", "any_teae", "death"} and "组别汇总计数" not in item.term:
            if re.findall(r"[A-Za-z]{3,}", item.term) and not item.term.endswith(
                "（登记原文，未译）"
            ):
                _base_label = item.term + "（登记原文，未译）"
            else:
                _base_label = item.term
        _ctx = getattr(item, "measure_context", None)
        if _base_label and _ctx:
            row["measure_label"] = f"{_base_label}｜{str(_ctx).strip()}"
        elif _base_label:
            row["measure_label"] = _base_label
        elif _ctx:
            row["measure_label"] = str(_ctx)
        else:
            row["measure_label"] = None
        # 独立复核 A r36（issue-3）：安全行观察窗按登记 timeFrame 逐试验转写；
        # 独立复核 A r42（issue-4）/B r56（issue-1）：转写后仍残留英文的
        # （含部分转写、含构建器已标注的）统一保留标注，不重复追加
        _tw = _native_timepoint_zh(item.time_window)
        if re.findall(r"[A-Za-z]{3,}", _tw) and not _tw.endswith("（登记原文，未译）"):
            _tw = _tw + "（登记原文，未译）"
        row["time_window"] = _tw
        projection = project_numeric(
            value=item.value,
            unit=item.unit,
            kind=infer_numeric_kind(
                measure_object=item.measure_object, unit=item.unit, domain="safety"
            ),
            numerator=item.numerator,
            denominator=item.denominator,
            window=item.time_window,
            estimand="安全性登记测量",
        )
        row["numeric_projection"] = projection.as_dict()
        if item.group_assignment_state == "unknown":
            row["numeric_projection"]["renderable"] = False
            row["unrendered_reason"] = "group_product_relationship_unresolved"
        else:
            row["unrendered_reason"] = None
        row["plot_value"] = projection.plot_value
        row["plot_unit"] = projection.plot_unit
        row["renderable"] = row["numeric_projection"]["renderable"]
        row["semantic_filter_key"] = "|".join(
            (
                str(item.term_key or "unknown"),
                item.polarity,
                item.seriousness,
                "teae"
                if item.teae is True
                else "non_teae"
                if item.teae is False
                else "teae_unknown",
                item.relatedness,
                ",".join(str(value) for value in item.grade_set),
                item.count_basis,
            )
        )
        rows.append(row)
    if not any(
        _category_base(row["category"]) == "特别关注不良事件" and row["value"] is not None
        for row in rows
    ):
        rows = [row for row in rows if _category_base(row["category"]) != "特别关注不良事件"]
    return tuple(rows)


def _safety_event_filters(
    rows: tuple[dict[str, object], ...],
) -> tuple[dict[str, str], ...]:
    """把受控同义项折叠成唯一筛选项，保留各行原始术语供明细查看。"""
    seen: dict[str, dict[str, str]] = {}
    for row in rows:
        key = str(row["term_key"])
        if key not in seen:
            seen[key] = {"key": key, "label": str(row["term_label"])}
    return tuple(seen.values())


def _safety_semantic_filters(rows: tuple[dict[str, object], ...]) -> tuple[dict[str, str], ...]:
    seen: dict[str, dict[str, str]] = {}
    for row in rows:
        key = str(row["semantic_filter_key"])
        if key not in seen:
            raw_grades = row.get("grade_set", ())
            grades = (
                "/".join(str(value) for value in raw_grades)
                if isinstance(raw_grades, (tuple, list))
                else ""
            )
            grades = grades or "无等级"
            seen[key] = {
                "key": key,
                "label": "｜".join(
                    (
                        str(row.get("term_label") or row.get("term_key")),
                        str(row.get("polarity")),
                        grades,
                        str(row.get("seriousness")),
                        str(row.get("relatedness")),
                        str(row.get("count_basis")),
                    )
                ),
            }
    return tuple(seen.values())


def _display_trials(data: ReportAPortalData) -> tuple[dict[str, object], ...]:
    """把登记平台字段投影成面向医学用户的中文展示，不改写证据原文。"""
    product_names = {item.id: item.name for item in _display_products(data)}
    rows: list[dict[str, object]] = []
    # 独立复核 A r31（issue-1）：同名试验折叠修复——组合名重复时全部
    # 追加登记号区分（NCT04820530 与 NCT05630001 不再同名）
    name_counts: dict[str, int] = {}
    for trial in data.trials:
        row = trial.model_dump(mode="json")
        row["original_name"] = trial.name
        if not _contains_chinese(trial.name):
            row["name"] = f"{product_names[trial.product_id]} {trial.phase}临床研究"
        name_counts[row["name"]] = name_counts.get(row["name"], 0) + 1
    dup_names = {n for n, c in name_counts.items() if c > 1}
    for trial in data.trials:
        row = trial.model_dump(mode="json")
        row["original_name"] = trial.name
        if not _contains_chinese(trial.name):
            row["name"] = f"{product_names[trial.product_id]} {trial.phase}临床研究"
        if row["name"] in dup_names:
            row["name"] = f"{row['name']}（{trial.display_id}）"
        row["status"] = _TRIAL_STATUS_ZH.get(trial.status, trial.status)
        rows.append(row)
    return tuple(rows)


def _display_regulatory(data: ReportAPortalData) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for item in data.regulatory:
        row = item.model_dump(mode="json")
        if item.track == "境外":
            parts = [
                part.strip()
                for part in item.status.split("；")
                if part.strip() and "中国" not in part
            ]
            row["status"] = "；".join(parts) or "境外状态未核实"
        rows.append(row)
    return tuple(rows)


def load_report_a_data(path: Path) -> ReportAPortalData:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReportAPortalError(f"无法读取 A 类报告数据：{path}") from exc
    try:
        return ReportAPortalData.model_validate(payload)
    except ValueError as exc:
        raise ReportAPortalError(f"A 类报告数据不符合合同：{exc}") from exc


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _git_commit() -> str:
    try:
        value = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[4],
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "0" * 40
    return value if len(value) in (40, 64) else "0" * 40


def _copy_assets(site_root: Path) -> None:
    assets = site_root / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(resolve_logo_src(), assets / "logo.svg")
    for name in ("portal.css", "portal.js", "report-a.js", "report-a.css"):
        source = _ASSET_DIR / name if name.startswith("report-a.") else resolve_portal_asset(name)
        shutil.copy2(source, assets / name)
    shutil.copy2(resolve_echarts_bundle(), assets / "echarts.min.js")


def _navigation() -> tuple[dict[str, str], ...]:
    catalog = PageRegistry.load().catalog(ReportKind.A)
    return tuple(
        {"id": page.id, "title": page.title_zh, "group": page.navigation_group_zh}
        for page in catalog.pages
    )


_TIMEPOINT_PHRASES: tuple[tuple[str, str | Callable[[re.Match[str]], str]], ...] = (
    # 结构化长短语先行：整句式登记时间窗
    (r"final study visit", "末次研究访视"),
    (r"primary treatment period", "主要治疗期"),
    (r"\bprimary\b", "主要"),
    (r"\blte\b", "长期扩展期"),
    (
        r"within (\d+) weeks? prior to first dose and during (\d+)[- ]week treatment period",
        r"首次给药前\1周内及\2周治疗期内",
    ),
    (r"within (\d+) weeks? prior to first dose", r"首次给药前\1周内"),
    (r"during (\d+)[- ]week treatment period", r"\1周治疗期内"),
    (r"period (\d+)", r"第\1周期"),
    (r"on entry and every 3 months thereafter[^,;.]*", "入组时及此后每3个月"),
    (
        r"from (?:first|single) dose of study drug up to (\d+) days? "
        r"after (?:the )?last dose(?: of study (?:drug|medication))?",
        r"自首次给药至末次给药后\1天",
    ),
    (
        r"from (?:first|single) dose of study drug \(days? (\d+)\) "
        r"up to (\d+) days?(?: after the last dose(?: of study (?:drug|medication))?)?",
        r"首次给药（第\1天）后至\2天",
    ),
    (
        r"after the first dose of study medication \(days? (\d+)\) "
        r"through (\d+) days? after the last dose(?: of study (?:drug|medication))?",
        r"首次给药后（第\1天）至末次给药后\2天",
    ),
    (r"from days? (\d+) to (\d+) days? after the last dose", r"自第\1天至末次给药后\2天"),
    (r"post (\d+) weeks? of treatment", r"治疗开始后\1周"),
    (r"within (\d+) weeks? prior to first dose", r"首次给药前\1周内"),
    (r"prior to initiation of treatment", "治疗开始前"),
    (r"post initiation of treatment", "治疗开始后"),
    (r"prior to first dose", "首次给药前"),
    (r"from first dose of study drug", "自首次给药起"),
    (r"first dose of study drug", "首次给药"),
    (
        r"last available rolling average before the first dose of study drug",
        "首次给药前最后一次可用滚动均值",
    ),
    (
        r"between (day|week|month)s? (\d+) and (?:day|week|month)s? (\d+)",
        lambda m: (
            f"第{m.group(2)}至第{m.group(3)}"
            f"{dict(d='天', w='周', m='个月')[m.group(1)[0].casefold()]}"
        ),
    ),
    (r"between days? (\d+) and (\d+)", r"第\1至\2天"),
    (r"between weeks? (\d+) and (\d+)", r"第\1至\2周"),
    (r"blood samples for ada assessments were taken\s*", "ADA检测采样："),
    (r"mean of visits", "访视均值"),
    (r"through days? (\d+)", r"至第\1天"),
    (r"through weeks? (\d+)", r"至第\1周"),
    (r"long[- ]term extension", "长期扩展期"),
    (r"extension period", "扩展期"),
    (r"extension study", "扩展研究"),
    (r"\bextension\b", "扩展期"),
    (r"to completion|\bcompletion\b", "研究结束"),
    (r"\bprior to\b", "之前"),
    (r"\bprior\b", "之前"),
    (r"\bminutes?\b", "分钟"),
    (r"\bperiod\b", "期间"),
    (r"up to end of study", "至研究结束"),
    (r"up to weeks? (\d+)", r"至第\1周"),
    (r"up to days? (\d+)", r"至第\1天"),
    (r"up to months? (\d+)", r"至第\1个月"),
    (r"up to ([\d.]+) years?", r"至\1年"),
    (r"up to (\d+) months?", r"至\1个月"),
    (r"up to (\d+) weeks?", r"至\1周"),
    (r"up to (\d+) days?", r"至\1天"),
    (r"up to (\d+) hours?", r"至\1小时"),
    (r"weeks? (\d+)\s*[-–]\s*weeks? (\d+)", r"第\1–\2周"),
    (r"days? (\d+)\s*[-–]\s*days? (\d+)", r"第\1–\2天"),
    (r"maximum exposure\s*[:：]?\s*", "最长暴露"),
    (r"end of follow-?up", "随访结束"),
    (r"end of (?:the )?study", "研究结束"),
    (r"end of treatment|\beot\b", "治疗结束"),
    (r"end of infusion", "输注结束"),
    (r"(\d+)\s*[-–]\s*(\d+)\s*hrs?", r"\1–\2小时"),
    (r"every (\d+) months?", r"每\1个月"),
    (r"every (\d+) weeks?", r"每\1周"),
    (r"(\d+(?:\.\d+)?)\s*weeks?", r"\1周"),
    (r"(\d+(?:\.\d+)?)\s*months?", r"\1个月"),
    (r"(\d+(?:\.\d+)?)\s*years?", r"\1年"),
    (r"post ?transplant", "移植后"),
    (r"\bolep\b", "开放扩展期"),
    (r"\boltp\b", "开放治疗期"),
    (r"part ([abc])\s*:", lambda m: f"{m.group(1).upper()}部分："),
    (r"part ([abc])\b", lambda m: f"{m.group(1).upper()}部分"),
    (r"cohorts? ([\d\-]+)\s*:", r"第\1组："),
    (r"cohorts? (\d+)\s+to\s+(\d+)", r"第\1–\2组"),
    (r"cohort (\d+)", r"第\1组"),
    (r"weekly/monthly/biweekly/monthly cohorts", "混合给药频率组"),
    (r"\((?:weekly|biweekly)[^)]*\)", "（分组给药）"),
    (r"dosing cohorts", "给药组"),
    (r"symptom scales? at", ""),
    # 症状与体征名词（症状量表行的时间窗自带症状名）
    (r"abdominal pain", "腹痛"),
    (r"chest pain", "胸痛"),
    (r"erectile dysfunction", "勃起功能障碍"),
    (r"\bdyspnea\b|\bdyspnoea\b", "呼吸困难"),
    (r"\bdysphagia\b", "吞咽困难"),
    (r"\bfatigue\b", "疲乏"),
    (r"\bdiarrhea\b", "腹泻"),
    (r"\bnausea\b", "恶心"),
    (r"\bheadache\b", "头痛"),
    (r"\bpruritus\b", "瘙痒"),
    (r"\bhemoglobin\b|\bhaemoglobin\b", "血红蛋白"),
    (r"absence of (?:red blood cell|rbc) transfusions?", "无红细胞输血"),
    (r"absence of transfusions?", "无输血"),
    (r"\bplatelets?\b", "血小板"),
    (r"\breticulocytes?\b", "网织红细胞"),
    (r"lactate dehydrogenase|\bldh\b", "乳酸脱氢酶"),
    (r"\btransfusions?\b", "输血"),
    # 登记月份/周/日枚举与裸时间
    (
        r"months?\s+((?:\d+)(?:,\s*\d+)*(?:,?\s*and\s*\d+)?)",
        lambda m: "第" + re.sub(r",\s*|\s*and\s*", "、", m.group(1), flags=re.I) + "个月",
    ),
    (r"\bmonth\s*(\d+)", r"第\1个月"),
    (
        r"\bweeks?\s+(\d+)(?:\s*(?:,|and)\s*(\d+))+\b",
        lambda m: "、".join(f"第{x}周" for x in re.findall(r"\d+", m.group(0))),
    ),
    (r"\bweeks?\s*(\d+)e?\b", r"第\1周"),
    (r"\bdays?\s*(\d+)e?\b", r"第\1天"),
    (r"\bbaseline\b", "基线"),
    (r"\bscreening\b", "筛选期"),
    (r"\bsingle dose\b", "单次给药"),
    (r"after (?:the )?last dose", "末次给药后"),
    (r"\bafter eot\b", "治疗结束后"),
    (r"\bafter dosing\b|\bpost-dose\b", "给药后"),
    (r"immediately postdose", "给药后即时"),
    (r"\bapproximately\b", "约"),
    (r"\buntil the\b|\buntil\b", "至"),
    (r"\bthrough\b", "至"),
    (r"^from\s+", "自"),
    (r"\bhrs?\b", "小时"),
    (r"\bhours?\b", "小时"),
    (r"\byears?\b", "年"),
    (r"\bweekly\b", "每周"),
    (r"\bbiweekly\b", "每2周1次"),
    (r"\bmonthly\b", "每月1次"),
    (r"\bdosing\b", "给药"),
    (r"\bthereafter\b", "此后"),
    (r"\bsubsequent\b", "后续"),
    (r"\bduring the study\b|for the duration of the study", "研究期内"),
    (r"\bon entry\b|\bat entry\b", "入组时"),
    (r"\bvisit\b", "访视"),
    # 通用词收敛放最后：仅在结构化短语消费完毕后兜底
    (r"\bresponders?\b", "应答者"),
    (r"\bunbound\b", "游离型"),
    (r"\btotal\b", "总"),
    (r"\bpre dose\b|\bpredose\b|\bpre-dose\b", "给药前"),
    (r"\bed\b", "勃起功能障碍"),
    (r"\bnone\b", "无"),
    (r"\bmild\b", "轻度"),
    (r"\bmoderate\b", "中度"),
    (r"\bsevere\b", "重度"),
    (r"\bchange\b", "较基线变化"),
    (r"\beculizumab\b", "依库珠单抗"),
    (r"\bravulizumab\b", "雷夫利珠单抗"),
    (r"\bcrovalimab\b", "可伐利单抗"),
    (r"\biptacopan\b", "伊普可泮"),
    (r"\bpegcetacoplan\b", "培戈赛他泮"),
    (r"\btreatment\b|\bdose\b", "给药"),
    (r"\bfrom\b", "自"),
    (r"\bon\s+", ""),
    (r"\bstudy\b", "研究"),
    (r"(\d+)\s*days?", r"\1天"),
    (r"parent study", "母研究"),
    (r"\bpre-?treatment\b", "治疗前"),
    (r"\bpost-?treatment\b", "治疗后"),
    (r"\bmissing severity\b", "严重程度缺失"),
    (r"\bpre-?infusion\b", "输注前"),
    (r"\bpost-?infusion\b", "输注后"),
    (r"\bpost\b", "给药后"),
    (r"\bsince\b", "自"),
    (r"\b\btid\b\b|\btid\b", "每日3次"),
    (r"\bbid\b", "每日2次"),
    (r"\bqd\b", "每日1次"),
    (r"\bminutes?\b", "分钟"),
    (r"\bafter\b", "后"),
    (r"\btrough\b", "谷浓度"),
    (r"\bpostdose\b", "给药后"),
    (r"\bolep\b", "开放扩展期"),
    (r"\bdiarrhoea\b", "腹泻"),
    (r"direct bilirubin", "直接胆红素"),
    (r"indirect bilirubin", "间接胆红素"),
    (r"\boverall\b", "总体"),
    (r"\bprestudy\b|\bpre-study\b", "研究前"),
    (r"\babsolute\b", "绝对值"),
    (r"\bvalues?\b", "值"),
    (r"\bin the\b|\bthe\b|\bin\b", ""),
    (r"\bof\b", ""),
)


def _native_timepoint_zh(value: str) -> str:
    """登记时间窗的确定性中文转写；结构性短语优先，裸枚举次之，通用词兜底。

    残余裸英文 ≥2 词视为未转写成功，回退为显式声明式标签（原文保留证据层）。
    """
    text = " ".join(str(value or "").split())
    if not text:
        return text
    if _contains_chinese(text) and len(re.findall(r"[A-Za-z]{2,}", text)) == 0:
        return text
    out = text
    for pattern, rep in _TIMEPOINT_PHRASES:
        out = re.sub(pattern, rep, out, flags=re.I)
    out = re.sub(r"\s*(?:and|&)\s*", "、", out, flags=re.I)
    out = re.sub(r"\s*\bat\s+", "", out, flags=re.I)
    out = re.sub(r"\s*\bto\b\s*", "至", out, flags=re.I)
    out = re.sub(r"\s*\bof the\b\s*|\s*\bof\b\s*", "", out, flags=re.I)
    out = re.sub(r",\s*", "、", out)
    out = re.sub(r";\s*", "；", out)
    out = re.sub(r"\[\s*", "（", out)
    out = re.sub(r"\s*\]", "）", out)
    out = re.sub(r"\(\s*", "（", out)
    out = re.sub(r"\s*\)", "）", out)
    out = re.sub(r"、、+", "、", out)
    out = re.sub(r"至至+", "至", out)
    out = re.sub(r"([\u4e00-\u9fff]{2,}) \1", r"\1", out)
    out = re.sub(r"研究 研究结束", "研究结束", out)
    out = re.sub(r"\s{2,}", " ", out).strip(" 、；")
    # 残余裸英文 ≥2 词 → 未转写成功，显式声明
    if len(re.findall(r"[A-Za-z]{2,}", out)) >= 2:
        # 独立复核 A r32：已披露但难以转写的叙事型时间窗保留登记原句
        # （可核对优先于占位串）
        return " ".join(str(value or "").split())
    return out


def _native_endpoint_zh(value: str) -> str:
    """把登记结果长标题收敛成中文临床终点名；原文仍保存在证据层。"""
    # 中文原生（独立复核 r22）：只有"零非缩写英文词"的中西混合文本才直通。
    # 此前 <3 词即放行，导致 "Absolute 较基线变化： Hemoglobin" 类规则半替换
    # 的混合文本原样漏出（429 行）。全大写缩写（LDH/EASI/ULN 等）不算残留。
    if _contains_chinese(value):
        residual = [w for w in re.findall(r"[A-Za-z]{3,}", value) if not w.isupper()]
        if not residual:
            return value
    folded = value.casefold()
    if re.search(
        r"(?:≥|>=)\s*(50|75|90)\s*%\s+improvement\s+in\s+"
        r"eczema area and severity index",
        value,
        re.I,
    ):
        match = re.search(r"(?:≥|>=)\s*(50|75|90)\s*%", value)
        measure = f"EASI-{match.group(1)}" if match else "EASI"
    elif re.search(r"(?:viga|isga|\biga\b)", value, re.I) and re.search(
        r"0\s*(?:or|and|/|或)\s*1|clear\s+or\s+almost\s+clear",
        value,
        re.I,
    ):
        measure = "IGA 0/1"
    else:
        measure = ""

    scale_patterns: tuple[tuple[str, Callable[[re.Match[str]], str]], ...] = (
        (r"easi[- ]?(50|75|90)", lambda m: f"EASI-{m.group(1)}"),
        (r"eczema area and severity index|\beasi\b", lambda _m: "EASI"),
        (r"investigator'?s global assessment|\bviga\b|\biga\b", lambda _m: "IGA"),
        (r"scoring atopic dermatitis|\bscorad\b", lambda _m: "SCORAD"),
        (r"pruritus.*(?:numeric|numerical) rating scale|pruritus nrs", lambda _m: "瘙痒NRS"),
        (r"dermatology life quality index|\bdlqi\b", lambda _m: "皮肤病生活质量指数（DLQI）"),
        (r"patient oriented eczema measure|\bpoem\b", lambda _m: "患者自评湿疹量表（POEM）"),
        (r"hospital anxiety and depression scale|\bhads\b", lambda _m: "医院焦虑抑郁量表（HADS）"),
        (r"euroquality of life|eq-5d", lambda _m: "欧洲五维健康量表（EQ-5D）"),
        (r"body surface area|\bbsa\b", lambda _m: "受累体表面积（BSA）"),
        (r"trough.*concentration|plasma concentration|serum concentration", lambda _m: "药物浓度"),
        # 跨适应症通用生物医学终点（独立视觉复核：通用族标签不得顶替终点身份）
        # 肾脏科终点（IgAN 泛化测试：不得落入通用占位标签）
        (
            r"urine protein[- ]?to[- ]?creatinine ratio|\bupcr\b|protein[- ]?creatinine ratio",
            lambda _m: "尿蛋白/肌酐比值（UPCR）",
        ),
        (
            r"urine albumin[- ]?to[- ]?creatinine ratio|\buacr\b",
            lambda _m: "尿白蛋白/肌酐比值（UACR）",
        ),
        (r"estimated glomerular filtration rate|\begfr\b", lambda _m: "估算肾小球滤过率（eGFR）"),
        (r"proteinuria|urine protein|urinary protein", lambda _m: "蛋白尿"),
        (r"albuminuria|urine albumin(?!/)", lambda _m: "白蛋白尿"),
        (r"haematuria|hematuria", lambda _m: "血尿"),
        (r"serum creatinine|\bscr\b(?!at)", lambda _m: "血肌酐"),
        (r"creatinine clearance|\bcrc[l]\b", lambda _m: "肌酐清除率"),
        # 肺科终点（IPF round-3 泛化测试：不得落入通用占位标签）
        (r"forced vital capacity|\bfvc\b", lambda _m: "用力肺活量（FVC）"),
        (
            r"six[- ]minute walk distance|\b6mwd\b|6[- ]minute walk",
            lambda _m: "6分钟步行距离（6MWD）",
        ),
        (
            r"diffusing (?:capacity|ability).*(?:carbon monoxide|co)|\bdlco\b",
            lambda _m: "一氧化碳弥散量（DLCO）",
        ),
        (
            r"acute exacerbation|worsening(?: of)? ipf|disease progression",
            lambda _m: "急性加重/疾病进展",
        ),
        (r"high[- ]resolution computed tomography|\bhrct\b", lambda _m: "高分辨CT（HRCT）"),
        (r"forced expiratory volume|\bfev1\b", lambda _m: "第一秒用力呼气量（FEV1）"),
        (r"oxygen saturation|spo2|\bpao2\b", lambda _m: "血氧饱和度"),
        # 消化科终点（UC 泛化测试）
        (
            r"endoscopic(?:\s+\w+)*\s*(?:remission|improvement|response)|endoscopy",
            lambda _m: "内镜改善",
        ),
        (r"mucosal healing", lambda _m: "黏膜愈合"),
        (
            r"histologic(?:al)?(?:\s+\w+)*\s*(?:remission|improvement|response)",
            lambda _m: "组织学改善",
        ),
        (r"rectal bleeding|bowel bleeding", lambda _m: "直肠出血"),
        (r"stool frequency", lambda _m: "排便次数"),
        (r"bowel urgency|urgency", lambda _m: "便急"),
        (r"inflammatory bowel disease questionnaire|\bibdq\b", lambda _m: "IBD 问卷（IBDQ）"),
        (r"steroid[- ]free", lambda _m: "无激素缓解"),
        (r"clinical remission|complete remission(?!.*iga)", lambda _m: "临床缓解"),
        (r"clinical (?:response|remission)", lambda _m: "临床应答"),
        # 跨适应症通用生物医学终点
        # PNH 特异症状/克隆/溶血终点必须先于 hemoglobin 等子串匹配
        # （独立复核 r21：89 条症状/克隆观察被误标为血红蛋白）
        (r"hemoglobinuria|haemoglobinuria", lambda _m: "血红蛋白尿"),
        (r"\bpnh clone|clone (?:size|count)|clonal (?:population|fraction)", lambda _m: "PNH 克隆"),
        (r"clinical pnh symptoms?|pnh symptoms?", lambda _m: "PNH 症状"),
        (r"intravascular hemolysis|\bhemolysis\b|\bhaemolysis\b", lambda _m: "血管内溶血"),
        (r"\bldh\b|lactate dehydrogenase", lambda _m: "乳酸脱氢酶（LDH）"),
        (r"hemoglobin|\bhgb\b", lambda _m: "血红蛋白"),
        (r"platelet", lambda _m: "血小板"),
        (r"absolute neutrophil|\banc\b", lambda _m: "中性粒细胞"),
        (r"reticulocyte", lambda _m: "网织红细胞"),
        (r"transfusion", lambda _m: "输血"),
        (r"\bfatigue\b", lambda _m: "疲乏"),
        (r"abdominal pain", lambda _m: "腹痛"),
        (r"dyspnea|dyspnoea", lambda _m: "呼吸困难"),
        (r"dysphagia", lambda _m: "吞咽困难"),
        (r"chest pain", lambda _m: "胸痛"),
        (r"erectile", lambda _m: "勃起功能"),
        (r"calprotectin", lambda _m: "粪便钙卫蛋白"),
        (r"mayo", lambda _m: "Mayo 评分"),
        (r"adverse event", lambda _m: "不良事件"),
    )
    # 独立复核 C r42（issue-1/2）：安全域与免疫原性终点不得落入
    # "疗效评价/其他临床疗效指标"——医学读者须能看出终点评价的是安全性
    if re.search(r"anti[- ]?drug antibod|antidrug antibod|immunogenicit|\badas?\b", value, re.I):
        return "免疫原性评价"
    # 独立复核 C r44（issue-3）：血清浓度终点保留测量身份，不再泛化
    if re.search(
        r"serum concentration|serum trough concentration|plasma concentration", value, re.I
    ):
        return "血清药物浓度评价"
    # 独立复核 C r46（issue-1）：During 等介词残留按惯例标注，不冒充门户文案
    if re.search(r"\bduring\b", value, re.I) and not value.endswith("（登记原文，未译）"):
        pass
    if re.search(
        r"adverse event|\bteaes?\b|\bsaes?\b|treatment[- ]emergent|"
        r"\baes\b of special|infection|\bdeath?s?\b",
        value,
        re.I,
    ):
        return "安全性评价"
    if not measure:
        measure = "其他临床疗效指标"
        for pattern, label in scale_patterns:
            match = re.search(pattern, value, re.I)
            if match:
                measure = label(match)
                break

    # 中文原生（独立复核 r22）：endpoint_rules 半替换留下的中文形式词
    # 也要参与 form 识别，避免退化成通用"疗效评价"
    zh_form = ""
    if "较基线百分比变化" in value:
        zh_form = "较基线百分比变化"
    elif "较基线变化" in value:
        zh_form = "较基线变化"
    elif "达到以下标准的受试者比例" in value:
        zh_form = "应答率"
    if "time to" in folded:
        form = "达到应答所需时间"
    elif re.search(r"percent(?:age)? of (?:participants|subjects)", folded) or re.search(
        r"(?:participants|subjects) achieving", folded
    ):
        form = "应答率"
    elif "number of participants" in folded:
        form = "应答人数"
    elif "percentage change" in folded or "percent change" in folded:
        form = "较基线百分比变化"
    elif "change from baseline" in folded or "change in" in folded:
        form = "较基线变化"
    elif "concentration" in folded:
        form = "浓度"
    elif "incidence" in folded:
        form = "发生率"
    else:
        form = "疗效评价"

    qualifiers: list[str] = []
    if "adolescent" in folded:
        qualifiers.append("青少年")
    elif "children" in folded or "pediatric" in folded:
        qualifiers.append("儿童")
    if match := re.search(r"(?:≥|>=)\s*(\d+(?:\.\d+)?)\s*(?:point|分)", value, re.I):
        qualifiers.append(f"改善≥{match.group(1)}分")
    if match := re.search(r"\bWeek\s*(\d+)\b", value, re.I):
        qualifiers.append(f"第{match.group(1)}周")
    if match := re.search(r"\bPart\s*([AB12])\b", value, re.I):
        qualifiers.append(f"第{match.group(1)}部分")
    if zh_form and form == "疗效评价":
        form = zh_form
    suffix = "；" + "；".join(qualifiers) if qualifiers else ""
    # 会商 #5 残留：measure 已含 form 语义时不再叠加（"药物浓度浓度"→"药物浓度"）
    body = measure + form if not measure.endswith(form) else measure
    return f"{body}{suffix}"


def _native_arm_detail_zh(value: str | None) -> str | None:
    if value is None:
        return None
    text = value
    replacements = (
        (r"Maintenance Blinded Treatment\s*-\s*", "维持期盲法治疗："),
        (r"Maintenance\s+", "维持期："),
        (r"Lebrikizumab Responder/", "Lebrikizumab应答者/"),
        (r"\bEscape\b", "补救治疗"),
        (r"\bPart\s*([AB])", r"\1部分"),
        (r"\(Part\s*([12])\)", r"（第\1部分）"),
        (r"\bPart\s*([12])\b", r"第\1部分"),
        (r"\bFrom the\b", "源自"),
        (r"\bThen\b", "后转为"),
        (r"\band\b", "；"),
        (r"\bTopical\b", "外用"),
        (r"\bOintment\b", "软膏"),
        (r"\bVehicle Controlled\b", "基质对照"),
        (r"\bVehicle\b", "基质"),
        (r"\bPercent\s*\(%\)", "%"),
        (r"\bAdolescents\s*:", "青少年："),
        (r"\bPlacebo\b", "安慰剂"),
        (r"up to Week\s*(\d+)", r"至第\1周"),
        (r"Week\s*(\d+)\s*to\s*(\d+)", r"第\1–\2周"),
        (r"\bSwitchers\b", "转换治疗者"),
        (r"\bRe-randomized\b", "再随机"),
        (r"\bContinued From\b", "延续自"),
        (r"\bQ2W\b", "每2周1次"),
        (r"\bQ4W\b", "每4周1次"),
        (r"\bQ8W\b", "每8周1次"),
        (r"\bQW\b", "每周1次"),
        (r"\bQD\b", "每日1次"),
        (r"\bSC\b", "皮下注射"),
        (r"\bno LD\b", "无负荷剂量"),
        (r"\bLD\b", "负荷剂量"),
        (r"\bArm\b", "组"),
        (r"\bLTS Period\b", "长期安全性期"),
        (r"\bInitial Treatment Period\b", "初始治疗期"),
        (r"\bVehicle Cream\b", "基质乳膏"),
        (r"\bRuxolitinib\b", "鲁索替尼"),
        (r"\bCream\b", "乳膏"),
        (r"\bBID\b", "每日2次"),
        (r"\bPredose\b", "给药前"),
        (r"\bBaseline\b", "基线"),
        (r"\(Week\s*(\d+)\s*-\s*(\d+)\)", r"（第\1–\2周）"),
        (r"\bWeek\s*(\d+)\b", r"第\1周"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.I)
    return " ".join(text.split())


_POPULATION_TOKENS: tuple[tuple[str, str | Callable[[re.Match[str]], str]], ...] = (
    # 登记类标题残留英文的确定性转写（先于通用回退；全大写缩写保留）
    (r"not applicable", "不适用"),
    (r"prior to first eculizumab dose", "首次依库珠单抗给药前"),
    (r"from first dose of eculizumab through last dose", "自首次依库珠单抗给药至末次给药"),
    (r"\beculizumab\b", "依库珠单抗"),
    (r"creatin(e)? kinase", "肌酸激酶"),
    (r"gamma glutamyl transpeptidase", "γ-谷氨酰转移酶"),
    (r"entire study", "整个研究期"),
    (r"post[- ]baseline", "基线后"),
    (r"\bmean\b", "均值"),
    (r"haemoglobin", "血红蛋白"),
    (r"antibody positive at/?before baseline", "抗体基线时/前阳性"),
    (r"antibody positive anytime", "抗体任何时候阳性"),
    (r"\bbinding\b", "结合"),
    (r"\bneutralizing\b", "中和"),
    (r"\btransfusions?\b", "输血"),
    (r"\bpostdose\b", "给药后"),
    (r"\bconcentration\b", "浓度"),
    (r"negative", "阴性"),
    (r"\btrace\b", "痕量"),
    (r"\bsmall\b", "少量"),
    (r"\blarge\b", "大量"),
    (r"\bpositive\b", "阳性"),
    (r"standard of care|\bsoc\b", "标准治疗"),
    (r"inadequate responder|inadequate response", "应答不佳"),
    (r"\btreatment[- ]na(\u00ef|ï)ve\b", "初治"),
    (r"\bna(\u00ef|ï|ai)ve\b", "初治"),
    (r"\brollover\b", "延续入组"),
    (r"\bswitch\b", "换用"),
    (r"\bgroup\b", "组"),
    (r"\bcohort\b", "队列"),
    (r"\bpeak\b", "峰浓度"),
    (r"\bblood\b", "血液"),
    (r"\bthrombos[ée]?s?\b", "血栓"),
    (r"\bhematology\b", "血液学"),
    (r"\bchemistry\b", "生化"),
    (r"\burinalysis\b", "尿液分析"),
    (r"\bsince\b", "自"),
    (r"\blnp023\b", "伊普可泮"),
    (r"\bquality\b", "质量"),
    (r"\banytime\b", "任何时候"),
    (r"at/?before baseline", "基线时/前"),
    (r"definitely related", "肯定相关"),
    (r"global satisfaction", "总体满意度"),
    (r"peak concentration", "峰浓度"),
    (r"alanine aminotransferase", "丙氨酸氨基转移酶"),
    (r"aspartate aminotransferase", "天冬氨酸氨基转移酶"),
    (r"neutrophil count", "中性粒细胞计数"),
    (r"prior to starting trial", "试验开始前"),
    (r"transfusion dependent", "输血依赖"),
    (r"treatment emergent adverse event|treatment-emergent adverse event", "治疗中出现的不良事件"),
    (r"treatment[- ]emergent", "治疗中新出现的"),
    (r"\beoi\b", "感兴趣事件"),
    (r"infusion reaction", "输注反应"),
    (r"serious infection", "严重感染"),
    (r"blood transfusions?", "输血"),
    (r"binding antibody", "结合抗体"),
    (r"neutralizing antibody", "中和抗体"),
    (r"antibody positive anytime", "抗体任何时候阳性"),
    (r"antibody positive at/?before baseline", "抗体基线时/前阳性"),
    (r"antibody positive", "抗体阳性"),
    (r"boosted", "强化"),
    (r"within (\d+) weeks? prior to first dose", r"首次给药前\1周内"),
    (r"during (\d+)[- ]week treatment period", r"\1周治疗期内"),
    (r"predose \(trough\)|predose", "给药前"),
    (r"trough", "谷浓度"),
    (r"financial difficulties", "经济困难"),
    (r"missing severity", "严重程度缺失"),
    (r"life[- ]threatening", "危及生命"),
    (r"treatment[- ]boosted response", "治疗强化应答"),
    (r"treatment[- ]emergent response", "治疗中新出现的应答"),
    (r"increase in hb", "血红蛋白升高"),
    (r"\bhb\b|hemoglobin", "血红蛋白"),
    (r"irrespective of", "不论"),
    (r"rbc transfusions?", "红细胞输血"),
    (r"direct bilirubin", "直接胆红素"),
    (r"indirect bilirubin", "间接胆红素"),
    (r"bilirubin", "胆红素"),
    (r"\baes?\b", "不良事件"),
    (r"study medication", "研究药物"),
    (r"\bincrease\b|\bincreased\b", "升高"),
    (r"\bdecrease\b|\bdecreased\b", "下降"),
    (r"\bevents?\b", "事件"),
    (r"at least (\d+)", r"至少\1次"),
    (r"serious adverse events?", "严重不良事件"),
    (r"adverse events?", "不良事件"),
    (r"leading to discontinuation", "导致停药"),
    (r"leading to death", "导致死亡"),
    (r"leading to", "导致"),
    (r"discontinuation|discontinued", "停药"),
    (r"possibly related", "可能相关"),
    (r"probably related", "很可能相关"),
    (r"related to study drug|related to", "相关"),
    (r"study drug|study treatment", "研究药物"),
    (r"maximum severity", "最重严重程度"),
    (r"global health status", "整体健康状态"),
    (r"quality of life|\bqol\b", "生活质量"),
    (r"functional scales", "功能量表"),
    (r"physical functioning", "躯体功能"),
    (r"role functioning", "角色功能"),
    (r"emotional functioning", "情绪功能"),
    (r"cognitive functioning", "认知功能"),
    (r"social functioning", "社会功能"),
    (r"\bfatigue\b", "疲乏"),
    (r"\bnausea\b", "恶心"),
    (r"\bvomiting\b", "呕吐"),
    (r"\bconstipation\b", "便秘"),
    (r"\bdiarrhea\b", "腹泻"),
    (r"\bappetite loss\b", "食欲减退"),
    (r"\binsomnia\b", "失眠"),
    (r"\bdyspnea\b|\bdyspnoea\b", "呼吸困难"),
    (r"non\s*responders?", "非应答者"),
    (r"responders?", "应答者"),
    (r"overall", "总体"),
    (r"up to", "至"),
    (r"\bthrough\b", "至"),
    (r"\bduring\b", "期间"),
    (r"\bonset\b", "发生"),
    (r"non\s*-?\s*clinically\s+significant|not\s+clinically\s+significant", "无临床意义"),
    (r"clinically\s+significant", "有临床意义"),
    (r"treatment[- ]emergent adverse events?|teaes?", "治疗中出现的不良事件"),
    (r"\bgrade\s*(\d+)", r"\1级"),
    (r"\bserious\b", "严重"),
    (r"\bmoderate\b", "中度"),
    (r"\bmild\b", "轻度"),
    (r"\bsevere\b", "重度"),
    (r"\bhigh\b", "升高"),
    (r"\blow\b", "降低"),
    (r"\bpre\b", "给药前"),
    (r"\bpost\b", "给药后"),
    (r"infusion", "输注"),
    (r"\bdose\b|\bdosing\b", "给药"),
    (r"\bchange\b", "变化"),
    (r"symptoms?", "症状"),
    (r"\btotal\b", "总"),
    (r"functioning", "功能"),
    (r"\bany\b", "任意"),
    (r"\bwith\b", "伴"),
    (r"\bfrom\b", "自"),
    (r"\bday\s*(\d+)", r"第\1天"),
    (r"\bperiod\s*(\d+)", r"第\1周期"),
    (r"\bweek\s*(\d+)", r"第\1周"),
    (r"participants?", "受试者"),
    (r"\btreatment\b", "治疗"),
    (r"\bend\b", "末次"),
    (r"\bunbound\b", "游离型"),
    (r"\bscales?\b", "量表"),
    (r"\bscores?\b", "评分"),
    (r"\bworst\b", "最重"),
    (r"\bpains?\b", "疼痛"),
    (r"\bworsening\b|\bworsened\b", "恶化"),
    (r"\bimproved?ment?\b", "改善"),
    (r"\bbaseline\b", "基线"),
    (r"\bsource\b", "来源"),
    (r"\blead[- ]?in\b", "导入期"),
    (r"\bwithdrawn\b", "提前停药者"),
    (r"\bcompleters?\b", "完成者"),
    (r"\bper\s+protocol\b", "符合方案"),
    (r"\binterim efficacy analysis\b", "期中疗效分析"),
    (r"\bfull analysis\b", "全分析集"),
    (r"\bmale\b", "男性"),
    (r"\bfemale\b", "女性"),
    (r"\bat least\b", "至少"),
    (r"\bminutes?\b", "分钟"),
    (r"\bolep\b", "开放扩展期"),
    (r"\ball\b", "全部"),
    (r"\band\b", "、"),
    (r"\bto\b", ""),
    (r"\bof\b", ""),
    (r"\bin\b", ""),
    (r"\bat\b", ""),
)


def _native_population_zh(value: str) -> str:
    """将登记平台分析人群长句压缩为可比较的中文定义。"""
    folded = value.casefold()
    if re.search(r"pk (?:evaluable )?population|pharmacokinetic", value, re.I):
        return "药代动力学分析集：至少接受1次研究药物且相应时间点样本可分析者"
    if "safety population" in folded or "safety analysis set" in folded:
        return "安全性分析集：至少接受1次研究药物且有基线后评估者"
    if "per-protocol analysis set" in folded:
        return "符合方案分析集：接受研究治疗且无重大方案违背的随机受试者"
    if "severe pruritus population" in folded:
        return "重度瘙痒人群：基线峰值瘙痒NRS≥7分的随机受试者"
    if "maintenance analysis set" in folded:
        response = "IGA 0/1" if "iga 0/1" in folded else "EASI-75"
        return f"维持期分析集：第16周达到{response}且未使用补救治疗者"
    if "re-randomized" in folded or "randomly reassigned" in folded:
        if "lebrikizumab" in folded:
            return "维持期分析集：基线接受Lebrikizumab、第16周再随机且至少接受1次维持期治疗者"
        if "week 24" in folded:
            response = (
                "IGA 0/1"
                if "iga response" in folded
                else "EASI-50"
                if "easi 50" in folded
                else "EASI-75"
                if "easi 75" in folded
                else "相应疗效"
            )
            return f"维持期再随机分析集：第24周达到{response}并完成再随机者"
    if "part 1" in folded and ("full analysis set" in folded or "ky1005" in folded):
        return "第1部分全分析集：随机后至少接受1次研究药物且相应时间点有可用数据者"
    if "part 2" in folded and ("full analysis set" in folded or "ky1005" in folded):
        return "第2部分全分析集：再随机后至少接受1次研究药物且相应时间点有可用数据者"
    if "lts evaluable population" in folded:
        age = (
            "；年龄<16岁"
            if "age \\< 16" in folded
            else "；年龄≥16岁"
            if "age \\>= 16" in folded
            else ""
        )
        return f"长期安全性可评价人群：长期研究期内至少使用1次研究药物且相应时间点有可用数据者{age}"
    if "intent-to-treat" in folded or "itt population" in folded:
        scope = (
            "青少年"
            if "adolescent" in folded
            else "主研究"
            if "main study" in folded
            else "全部随机"
        )
        method = (
            "；采用重复测量混合效应模型"
            if "mixed-effect" in folded or "mmrm" in folded
            else "；缺失数据按方案预设方法处理"
            if "imputation" in folded
            else ""
        )
        return f"意向治疗人群：{scope}受试者{method}"
    if re.search(
        r"\bfas\b|full analysis set|all randomized|all participants randomized", value, re.I
    ):
        method = (
            "；采用重复测量混合效应模型"
            if "mmrm" in folded
            else "；缺失数据按方案预设方法处理"
            if "imput" in folded
            else ""
        )
        return f"全分析集：所有随机受试者；按相应时间点可用数据统计{method}"
    if "analysis set included all randomized" in folded:
        return "分析集：至少接受1次研究药物且相应时间点有可用数据的随机受试者"
    if "participants who" in folded or "subjects who" in folded:
        return "预设分析人群：达到相应应答或基线条件并有可用数据者"
    # 登记类标题残留英文：确定性转写；全大写缩写（EORTC/QLQ/FACIT 等）保留；
    # 转写后仍剩 ≥2 个非缩写英文词才回退通用声明
    out = " ".join(str(value or "").split())
    for pattern, rep in _POPULATION_TOKENS:
        out = re.sub(pattern, rep, out, flags=re.I)
    out = re.sub(r"、\s*、", "、", out)
    out = re.sub(r"\(\s*", "（", out)
    out = re.sub(r"\s*\)", "）", out)
    out = re.sub(r"(?<=[\u4e00-\u9fff]) (?=[\u4e00-\u9fff])", "", out)
    out = re.sub(r"\s{2,}", " ", out).strip(" 、（")
    residual = [w for w in re.findall(r"[A-Za-z]{3,}", out) if not w.isupper()]
    if len(residual) >= 2:
        return "预设分析人群：按登记平台分析集定义及相应时间点可用数据纳入"
    return out


_UNIT_LITERAL_ZH = {
    "participants": "例",
    "events": "例",
    "number of events": "例数",
    "number of participants": "例",
    "score on a scale": "分",
    "scores on a scale": "分",
    "score on a scale (change from baseline)": "分（较基线变化）",
    "units on a scale": "分",
    "points on a scale": "分",
    "percentage of participants": "受试者百分比",
    "percentage of subjects": "受试者百分比",
    "percentage of responders": "应答者百分比",
    "percent change": "百分比变化",
    "percentage reduction": "百分比降幅",
    "percentage of activity": "活性百分比",
    "percentage of hemolysis": "溶血百分比",
    "percentage of pnh rbc": "PNH红细胞百分比",
    "percentage of pnh red blood cells": "PNH红细胞百分比",
    "percentage of type iii erythrocytes": "Ⅲ型红细胞百分比",
    "percentage of the total cell population": "总细胞群百分比",
    "percentage of carboxyhemoglobin": "碳氧血红蛋白百分比",
    "percent of lln for all ch50 values": "CH50占正常下限百分比",
    "percent lysis of sheep erythrocytes": "绵羊红细胞溶血百分比",
    "% c3 fragment deposition on pnh rbc": "PNH红细胞C3片段沉积率",
    "%change in hb value compare to screening": "较筛选期血红蛋白百分比变化",
    "percent change in ldh levels": "LDH水平百分比变化",
    "transfusion instances": "输血次数",
    "rbc units": "红细胞单位",
    "seconds": "秒",
    "hours": "小时",
    "weeks": "周",
    "days": "天",
    "months": "个月",
    "years": "年",
    "ratio": "比值",
    "events per patient-year": "每患者年事件数",
    "mg fibrinogen-equivalent unit (feu)/l": "mg FEU/L",
}


def _native_unit_zh(unit: str) -> str:
    """登记单位中文化：SI 符号化规则（可泛化）+ 字面映射 + 显式回退。"""
    text = " ".join(str(unit or "").split())
    if not text:
        return text
    low = text.casefold()
    m = re.fullmatch(
        r"(?:kilo|milli|micro|nano)?\s*(?:gram|mole|equivalent)s?\s*\(([^)]+)\)\s*/?\s*"
        r"per\s*(?:deci|milli|micro|nano)?\s*lit(?:er|re)(?:\s*\(([^)]+)\))?",
        low,
    )
    if m:
        sym = (m.group(2) or m.group(1) or "").replace(" ", "")
        sym = re.sub(r"ug", "μg", sym)
        sym = re.sub(r"umol", "μmol", sym)
        return sym
    m = re.fullmatch(
        r"(?:kilo|milli|micro|nano)?(gram|mole)s? per (?:deci|milli|micro|nano)?lit(?:er|re)",
        low,
    )
    if m:
        stem = "g" if m.group(1).startswith("gram") else "mol"
        prefix = "μ" if "micro" in low else "n" if "nano" in low else "k" if "kilo" in low else ""
        return f"{prefix}{stem}/L"
    # 指数计数单位写法归一（独立复核 r21：同一量级多种写法并存）
    m = re.fullmatch(
        r"(?:cells?\s*)?[x×*]\s*10\s*\^?\s*(\d+)(?:\s*cells?)?\s*/?\s*l(?:\s*\([^)]*\))?",
        low,
    )
    if m:
        exp = m.group(1)
        return {("9",): "×10⁹/L", ("12",): "×10¹²/L", ("6",): "×10⁶/L"}.get((exp,), f"×10{exp}/L")
    m = re.fullmatch(r"cells?\s*[x×]\s*10\s*\^?\s*(\d+)\s*/\s*l", low)
    if m:
        exp = m.group(1)
        return {("9",): "×10⁹/L", ("12",): "×10¹²/L", ("6",): "×10⁶/L"}.get((exp,), f"×10{exp}/L")
    # 值列拼接单位的来源（独立复核 A r22：'2.56hour (h)' 类）
    m = re.fullmatch(r"hours?\s*\(h\)", low)
    if m:
        return "小时"
    if low in {"g/liter (l)", "g/liter(l)", "g/l"}:
        return "g/L"
    if low == "units":
        return "U"
    if low == "ln(ratio)":
        return "ln(比值)"
    # 符号规范化（A r34 修订）：仅对"符号形"单位（含 / 且 ≤14 字符）做
    # 拼写统一；不得对多词英文单位做整串空格剥离（A r35 回归：单位被
    # 压成 percentageofresponders 之类的无空格串）
    canonical = re.sub(r"[\s]", "", low)
    if "/" in canonical and len(canonical) <= 16:
        c2 = canonical
        c2 = re.sub(r"\bmicromol", "μmol", c2)
        c2 = c2.replace("ug/", "μg/").replace("mcg/", "μg/")
        c2 = c2.replace("umol", "μmol").replace("μmol/l", "μmol/L")
        c2 = c2.replace("/ml", "/mL").replace("/l", "/L")
        c2 = c2.replace("μmoles", "μmol")
        if c2 != canonical:
            return c2
    # 拼写式单位第二形状：前缀词直接连在 gram/mole 上、符号在括注里
    # （A r24：'micrograms per litre (ug/L)' 类 500+ 行被占位串误吞）
    m = re.fullmatch(
        r"(kilo|milli|micro|nano)?(gram|mole)s?\s*(?:\([^)]*\))?\s*per\s*"
        r"(deci|milli|micro|nano|kilo)?\s*lit(?:er|re)\s*(?:\(([^)]+)\))?",
        low,
    )
    if m:
        # 注意分组：3=分母词前缀（deci/milli/...），4=括注符号
        num_prefix = {"kilo": "k", "milli": "m", "micro": "μ", "nano": "n"}.get(
            m.group(1) or "", ""
        )
        den_prefix = {"deci": "d", "milli": "m", "micro": "μ", "nano": "n", "kilo": "k"}.get(
            m.group(3) or "", ""
        )
        stem = "g" if (m.group(2) or "").startswith("gram") else "mol"
        return f"{num_prefix}{stem}/{den_prefix}L"
    m = re.fullmatch(
        r"(?:international\s*)?units?\s*(?:\([^)]*\))?\s*(?:per\s*(?:lit(?:er|re)|ml)|/\s*lit(?:er|re)|/\s*ml|/l)"
        r"(?:\s*\(([^)]+)\))?",
        low,
    )
    if m:
        paren_sym = (m.group(1) or "").replace(" ", "")
        return paren_sym if paren_sym else ("IU/L" if "international" in low else "U/L")
    # 括注符号直取（"micromoles (μmol)/liter" → μmol/L）
    m = re.search(r"\(([^)]*/[^)]+)\)", text)
    if m and re.fullmatch(
        r"[kμµMmGgdUIn]?[A-Za-zμμ]{0,5}/[kμµMmGdn]?[A-Za-zμL]{1,5}", m.group(1).strip()
    ):
        sym = m.group(1).strip().replace("µ", "μ")
        return sym
    # 常见派生形状
    _DERIVED_UNIT_ZH = {
        "% of pnh-rbc within total rbc population": "PNH红细胞占比",
        "prbc units": "红细胞单位",
        "prbc transfusions": "红细胞输注",
        "units/liter": "U/L",
        "grams/liter": "g/L",
        "millimole(s)/litre": "mmol/L",
        "micromoles/liter": "μmol/L",
        "percentage of survival probability": "生存概率百分比",
        "bth events/year": "突破性溶血事件/年",
        "mave events/year": "重要血管事件/年",
        "ratio of ldh:uln (250 u/l)": "LDH:ULN 比值",
        "% change from baseline in serum ldh": "较基线血清LDH百分比变化",
        "transfusions per person-year": "每人年输血次数",
        "score on scale": "分",
        "percentage of change": "百分比变化",
        "units of prbcs": "红细胞单位数",
        "units/liter (u/l)": "U/L",
        "percent change from baseline": "较基线百分比变化",
        "events per person-years of treatment": "每治疗人年事件数",
        "percent reduction": "百分比降幅",
        "hour (hr)*nanograms/milliliter (ng/ml)": "ng/mL·h",
        "facit-f scale (change from baseline)": "FACIT-f 分（较基线变化）",
        "mg per deciliter (mg/dl)": "mg/dL",
        "number of blood transfusions": "输血次数",
        "packed rbc units per month": "红细胞单位/月",
        "proportion of participants": "受试者比例",
        "percentage change": "百分比变化",
        "number of events per 100 patient-years": "每100患者年事件数",
        "hour*microgram/milliliter (h*μg/ml)": "μg/mL·h",
        "international units per ml (iu/ml)": "IU/mL",
        "units * days per liter (u*day/l)": "U·天/L",
        "percentage of days": "天数百分比",
        "infusions per participant year": "每受试者年输注次数",
        "number of units of transfusions of rbc": "红细胞输注单位数",
        "percentage of patients with bth events": "突破性溶血事件患者百分比",
        "percentage of patients with maves": "重要血管事件患者百分比",
        "mean percentage of participants": "受试者百分比均值",
        "rbc transfusion instances": "红细胞输注次数",
        "transfusion per person-year of treatment": "每治疗人年输血次数",
        "days since first dose": "自首次给药起天数",
        "grams/deciliter": "g/dL",
        "scores on a scale (change from baseline)": "分（较基线变化）",
        "milligram per litre (mg)/l": "mg/L",
        "milligram per liter (mg)/l": "mg/L",
        "micromoles (μmol)/liter": "μmol/L",
        "micromole (μmol)/l": "μmol/L",
        "percent change from baseline in ldh": "较基线LDH百分比变化",
        "u*day/l/week": "U·天/周",
        "microgram per milliliter (ug/ml)": "μg/mL",
    }
    if low in _DERIVED_UNIT_ZH:
        return _DERIVED_UNIT_ZH[low]
    # 指数计数单位：空格无关的容差匹配（round-3 IPF：'10^9 cells/ liter (L)' 类变体）
    compact = re.sub(r"\s+", "", low)
    m = re.fullmatch(
        r"10\^?(\d+)(?:cells?|reticulocytes\(cells\))?(?:/|per)(microlit(?:er|re)|nanolit(?:er|re)|lit(?:er|re)|ml|l)(?:\(siunits\)|\(l\)|\(μl\)|\(ul\))?",
        compact,
    )
    if m:
        exp = m.group(1)
        denom = m.group(2)
        denom_zh = {
            "microliter": "μL",
            "microlitre": "μL",
            "nanoliter": "nL",
            "nanolitre": "nL",
            "liter": "L",
            "litre": "L",
            "ml": "mL",
            "l": "L",
        }.get(denom, denom)
        sup = {"6": "⁶", "9": "⁹", "12": "¹²"}.get(exp, f"^{exp}")
        return f"×10{sup}/{denom_zh}"
    if compact in {"arc/nanoliter", "arc/nl"}:
        return "ARC/nL"
    if compact in {"gramperliter(g/l)", "g/l"}:
        return "g/L"
    if low in {"10^12 cells/l", "10^12 cells/l (si units)", "10^12 reticulocytes (cells)/l"}:
        return "×10¹²/L"
    if low in {"10^9 cells/l", "10^9 cells/liter (l)", "10^9/l"}:
        return "×10⁹/L"
    if low in _UNIT_LITERAL_ZH:
        return _UNIT_LITERAL_ZH[low]
    if text in _UNIT_LITERAL_ZH:
        return _UNIT_LITERAL_ZH[text]
    # 回退：残余多词英文 → 显式声明；短符号（g/L、U/L、μmol/L 等）保留
    if len(re.findall(r"[A-Za-z]{3,}", text)) >= 2:
        return "登记报告单位（详见登记来源）"
    return text


def _disambiguate_endpoint_labels(rows: list[dict[str, Any]]) -> None:
    """同试验内不同登记测量被收敛为同一中文终点标签时，以序号显式区分。

    独立复核：同名标签不同数值无法归属到登记终点 → 标签必须一一对应测量定义。
    """
    by_trial_label: dict[tuple[str, str], dict[str, int]] = {}
    for row in rows:
        key = (str(row.get("trial_id")), str(row.get("endpoint")))
        src = str(row.get("endpoint_source") or "")
        by_trial_label.setdefault(key, {}).setdefault(src, 0)
    for sources in by_trial_label.values():
        if len(sources) >= 2:
            ordered = sorted(sources)
            for idx, src in enumerate(ordered, start=1):
                sources[src] = idx
    for row in rows:
        key = (str(row.get("trial_id")), str(row.get("endpoint")))
        source_ordinals = by_trial_label.get(key)
        if source_ordinals and len(source_ordinals) >= 2:
            src = str(row.get("endpoint_source") or "")
            n = source_ordinals.get(src)
            if n:
                row["endpoint"] = f"{row['endpoint']}（登记终点定义{n}）"


_HISTORY_PHRASING: tuple[tuple[str, str], ...] = (
    (r"条因未披露样本量未入试验表", "项试验因登记未披露样本量，未纳入试验明细"),
    (
        r"条无独立药物干预未产出实体（明细见派生记录）",
        "条记录经登记适用性筛查未纳入试验明细（A 门户当前不含证据与局限页，规则说明随证据包交付）",
    ),
    (r"无独立药物干预未产出实体", "经登记适用性筛查未纳入明细"),
    (r"联合治疗关系受载荷单产品字段限制", "联合用药信息按各产品分别记录"),
    (r"监管/专利来源待接入", "监管与专利来源将在后续版本接入"),
    (r"中国路线\s*访问受阻已如实记档", "中国境内登记路线访问受阻，已按合同记档并声明"),
    (r"访问受阻已如实记档", "访问受阻，已按合同记档"),
)


def _native_history_zh(text: str) -> str:
    """历史时间线面向用户改写：内部派生口径不得直出（独立复核 r21）。"""
    out = str(text or "")
    for pattern, rep in _HISTORY_PHRASING:
        out = re.sub(pattern, rep, out)
    return out


# 研发代号 → 已确立中文名（构成式转写的药名层；仅收录可核实条目）
_ARM_CODE_ZH = {
    "LNP023": "伊普可泮",
    "RVA576": "Coversin",
    "ALXN2050": "Danicopan",
    "ACH-0144471": "Danicopan",
    "ALN-CC5": "ALN-CC5",
}


def _native_arm_zh(value: str) -> str:
    """登记组别名的确定性中文转写；残余多词英文回退显式声明。"""
    out = " ".join(str(value or "").split())
    if not out:
        return out
    for pattern, rep in _POPULATION_TOKENS:
        out = re.sub(pattern, rep, out, flags=re.I)
    out = re.sub(r"、、+", "、", out)
    out = re.sub(r"\(\s*", "（", out)
    out = re.sub(r"\s*\)", "）", out)
    out = re.sub(r"(?<=[\u4e00-\u9fff]) (?=[\u4e00-\u9fff])", "", out)
    out = re.sub(r"\s{2,}", " ", out).strip(" 、（")
    if len([w for w in re.findall(r"[A-Za-z]{3,}", out) if not w.isupper()]) >= 2:
        # 构成式转写：研发代号→中文名，剂量/频次词保留
        for code, zhname in _ARM_CODE_ZH.items():
            if re.search(code, out, re.I):
                out = re.sub(code, zhname, out, flags=re.I)
        out = re.sub(r"\bBid\b|\bBID\b|\bb\.i\.d\.?\b", "每日2次", out, flags=re.I)
        out = re.sub(r"\bQD\b|\bqd\b", "每日1次", out, flags=re.I)
        out = re.sub(r"\bQ4W\b", "每4周1次", out, flags=re.I)
        out = re.sub(r"\bQ2W\b", "每2周1次", out, flags=re.I)
        out = re.sub(r"\bmg\b", "毫克", out, flags=re.I)
        out = re.sub(r"\bSoC\b|\bsoc\b", "标准治疗", out, flags=re.I)
        out = re.sub(r"(?<=[\u4e00-\u9fff]) (?=[\u4e00-\u9fff])", "", out)
        out = re.sub(r"\s{2,}", " ", out).strip()
        if len([w for w in re.findall(r"[A-Za-z]{3,}", out) if not w.isupper()]) < 2:
            return out
        # 独立复核 A r29/r30：臂区分度优先于外观——残余英文保留原臂名
        return " ".join(str(value or "").split())
    return out


def _display_efficacy_rows(data: ReportAPortalData) -> tuple[dict[str, Any], ...]:
    """仅转换面向用户的疗效文字；保留原始数值及证据数据。"""
    rows: list[dict[str, Any]] = []
    for item in data.efficacy:
        row = item.model_dump(mode="json")
        endpoint = str(row["endpoint"])
        endpoint = re.sub(
            r"Time to Achievement EASI\s*(50|75|90)",
            r"达到EASI \1应答所需时间",
            endpoint,
            flags=re.I,
        )
        endpoint = re.sub(
            r"Change from Baseline in SCORAD.*", "SCORAD较基线变化", endpoint, flags=re.I
        )
        endpoint = re.sub(
            r"Change from Baseline in Pruritus NRS.*", "瘙痒NRS较基线变化", endpoint, flags=re.I
        )
        endpoint = re.sub(
            r"Serum Trough Concentration.*", "Tezepelumab血清谷浓度", endpoint, flags=re.I
        )
        endpoint = re.sub(r"Participants.*IGA.*", "IGA 0/1应答率", endpoint, flags=re.I)
        endpoint_rules = (
            (r"Mean Percentage Change From Baseline in", "较基线平均百分比变化："),
            (r"Percentage Change From Baseline in", "较基线百分比变化："),
            (r"Percent Change From Baseline in", "较基线百分比变化："),
            (r"Absolute Change in", "绝对变化："),
            (r"Change From Baseline in", "较基线变化："),
            (r"Percentage of Participants With", "达到以下标准的受试者比例："),
            (r"Participants With", "达到以下标准的受试者："),
            (r"Improvement \(Reduction\) of", "改善（降低）："),
            (r"Achievement of", "达到"),
            (r"Incidence of Adverse Events", "不良事件发生率"),
            (r"Eczema Area and Severity Index", "湿疹面积及严重程度指数"),
            (r"Investigator'?s Global Assessment", "研究者总体评估"),
            (r"Dermatology Life Quality Index", "皮肤病生活质量指数"),
            (r"Pruritus Numerical Rating Scale", "瘙痒数字评分量表"),
            (r"Pruritus NRS", "瘙痒NRS"),
            (r"at Each Time Point", "（各时间点）"),
            (r"at Week\s*(\d+)", r"（第\1周）"),
            (r"Part\s*([AB])\s*Only", r"\1部分"),
            (r"Part\s*([12])", r"第\1部分"),
        )
        for pattern, replacement in endpoint_rules:
            endpoint = re.sub(pattern, replacement, endpoint, flags=re.I)
        row["endpoint"] = _native_endpoint_zh(endpoint)

        # 独立复核 A r42（issue-4）：转写后仍残留英文的时间点（含部分转写），
        # 按惯例标注"（登记原文，未译）"，不让半翻译串冒充已译口径
        _tp = _native_timepoint_zh(str(row["timepoint"]))
        if re.findall(r"[A-Za-z]{3,}", _tp) and not _tp.endswith("（登记原文，未译）"):
            _tp = _tp + "（登记原文，未译）"
        row["timepoint"] = _tp

        arm = str(row["arm"])
        arm = re.sub(r"\bPart\s*A\b", "A部分", arm, flags=re.I)
        arm = re.sub(r"\bPlacebo\b", "安慰剂", arm, flags=re.I)
        arm = re.sub(r"\bQ2W\b", "每2周1次", arm, flags=re.I)
        arm = re.sub(r"\bQ4W\b", "每4周1次", arm, flags=re.I)
        row["arm"] = _native_arm_zh(arm)
        row["arm_detail"] = _native_arm_detail_zh(row.get("arm_detail"))

        row["population"] = _native_population_zh(str(row["population"]))
        row["unit"] = _native_unit_zh(str(row["unit"]))
        projection = project_numeric(
            value=item.value,
            unit=item.unit,
            kind=infer_numeric_kind(unit=item.unit, domain="efficacy"),
            numerator=item.numerator,
            denominator=item.denominator,
            window=item.timepoint,
            estimand=item.endpoint,
        )
        displayed_projection = projection.as_dict()
        displayed_projection["plot_unit"] = _native_unit_zh(projection.plot_unit)
        row["numeric_unrendered_reason_zh"] = (
            "来源未注明比例刻度（0–1 或 0–100）"
            if projection.unrenderable_reason
            == "participant_proportion_requires_percent_or_n_over_N"
            else "当前数值或统计单位不足以安全绘图"
            if projection.unrenderable_reason is not None else None
        )
        if item.group_assignment_state == "unknown":
            displayed_projection["renderable"] = False
            row["unrendered_reason"] = "group_product_relationship_unresolved"
        else:
            row["unrendered_reason"] = None
        row["numeric_projection"] = displayed_projection
        row["plot_value"] = projection.plot_value
        row["plot_unit"] = displayed_projection["plot_unit"]
        row["renderable"] = displayed_projection["renderable"]
        # 登记结果测量原文（独立复核：门户必须保留可回溯的终点原文）
        row["endpoint_source"] = str(item.endpoint)
        rows.append(row)
    _disambiguate_endpoint_labels(rows)
    return tuple(rows)


def _view_context(
    data: ReportAPortalData,
    *,
    current: str,
    depth: int = 0,
    publication_limitation_zh: str | None = None,
    public_provenance: PublicProvenance | None = None,
) -> dict[str, Any]:
    display_products = _display_products(data)
    product_names = {item.id: item.name for item in display_products}
    display_trials = _display_trials(data)
    display_efficacy = _display_efficacy_rows(data)
    display_safety = _display_safety_rows(data)
    trial_names = {str(item["id"]): str(item["name"]) for item in display_trials}
    trial_original_names = {str(item["id"]): str(item["original_name"]) for item in display_trials}
    return {
        "report": data,
        "products": display_products,
        "trials": display_trials,
        "efficacy": display_efficacy,
        "unassigned_efficacy_count": sum(
            item["group_assignment_state"] == "unknown" for item in display_efficacy
        ),
        "additional_observations": tuple(
            {
                **item.model_dump(mode="json"),
                "domain_label": {
                    "immunogenicity": "免疫原性",
                    "pk_pd": "药代/药效学",
                    "biomarkers": "生物标志物",
                    "other": "其他研究观察",
                    "unresolved": "领域待核",
                }[item.domain],
            }
            for item in data.additional_observations
        ),
        "safety": display_safety,
        "unassigned_safety_count": sum(
            item["group_assignment_state"] == "unknown" for item in display_safety
        ),
        "safety_public_categories": tuple(
            category
            for category in ("严重不良事件", "治疗期间不良事件", "常见不良事件", "特别关注不良事件")
            if any(
                _category_base(row["category"]) == category and row["value"] is not None
                for row in display_safety
            )
        ),
        "regulatory": _display_regulatory(data),
        "safety_event_filters": _safety_event_filters(display_safety),
        "safety_semantic_filters": _safety_semantic_filters(display_safety),
        "sources": data.sources,
        "user_edits": data.user_edits,
        "external_sources": public_provenance.sources if public_provenance else (),
        "companies": data.companies,
        "patents": data.patents,
        "history": tuple(
            row.model_copy(update={"observation": _native_history_zh(row.observation)})
            for row in data.history
        ),
        "product_names": product_names,
        "trial_names": trial_names,
        "trial_original_names": trial_original_names,
        "navigation": _navigation(),
        "current": current,
        "root_prefix": "../" * depth,
        "asset_prefix": "../" * depth + "assets",
        "data_prefix": "../" * depth + "data",
        "publication_limitation_zh": publication_limitation_zh,
    }


def _project_active_facts_a(
    data: ReportAPortalData,
    active_revision: ActiveFactRevision,
) -> tuple[ReportAPortalData, tuple[PortalConsumerNode, ...]]:
    safety = list(data.safety)
    efficacy = list(data.efficacy)
    user_edits = dict(data.user_edits)
    consumers: list[PortalConsumerNode] = []
    for fact, binding in active_revision.bindings_for("A"):
        page: str
        if binding.collection == "safety":
            matches = [
                index
                for index, candidate in enumerate(safety)
                if candidate.row_id == binding.row_id
            ]
            page = "safety.html"
        elif binding.collection == "efficacy":
            matches = [
                index
                for index, candidate in enumerate(efficacy)
                if candidate.row_id == binding.row_id
            ]
            page = "efficacy.html"
        else:
            raise ReportAPortalError("A renderer只接受safety/efficacy领域绑定")
        if len(matches) != 1:
            raise ReportAPortalError(
                f"A active fact绑定必须命中唯一领域行：{binding.collection}/{binding.row_id}"
            )
        index = matches[0]
        row: SafetyRow | EfficacyRow = (
            safety[index] if binding.collection == "safety" else efficacy[index]
        )
        fact_extra = fact.model_extra or {}
        try:
            verified_binding = validate_active_fact_binding(
                fact,
                binding,
                active_fact_binding_for_a(data, binding.collection, binding.row_id),
            )
        except ValueError as error:
            raise ReportAPortalError(str(error)) from error
        if fact_extra.get("review_state") != "user_modified":
            continue
        unit = str(fact_extra.get("normalized_unit") or fact_extra.get("unit") or row.unit)
        endpoint = (
            fact_extra.get("endpoint_definition")
            or getattr(row, "term", None)
            or getattr(row, "endpoint", "")
        )
        cleared = fact.disclosure_state == "user_cleared"
        narrative = (
            f"{endpoint}：用户清除，待重新核实。"
            if cleared else f"{endpoint}：{fact.raw_value or fact.normalized_value}。"
        )
        updates: dict[str, Any] = {
            "value": None if cleared else numeric_value(fact),
            "unit": unit,
            "clinical_narrative": narrative,
        }
        if cleared:
            updates.update(numerator=None, denominator=None)
            updates["disclosure_state"] = (
                "用户清除，待重新核实" if isinstance(row, SafetyRow)
                else FactDisclosureState.USER_CLEARED
            )
        for field in ("numerator", "denominator"):
            value = fact_extra.get(field)
            if isinstance(value, int):
                updates[field] = value
        if isinstance(row, SafetyRow):
            if fact_extra.get("time_window"):
                updates["time_window"] = str(fact_extra["time_window"])
            if (
                fact_extra.get("statistical_form") == "crude_rate"
                and fact_extra.get("measure_object") == "participants"
            ):
                updates["measure_object"] = "participant_proportion"
                updates["count_basis"] = "participants"
            safety[index] = SafetyRow.model_validate(row.model_copy(update=updates))
        else:
            if fact_extra.get("timepoint"):
                updates["timepoint"] = str(fact_extra["timepoint"])
            if fact_extra.get("population"):
                updates["population"] = str(fact_extra["population"])
            efficacy[index] = EfficacyRow.model_validate(row.model_copy(update=updates))
        original_value = "未公开" if row.value is None else f"{row.value:g}{row.unit}"
        user_edits[binding.row_id] = user_edit_disclosure(
            fact,
            active_revision,
            original_value=original_value,
        )
        consumers.append(
            PortalConsumerNode(
                report="A",
                fact_id=fact.fact_id,
                fact_version_id=fact.fact_version_id,
                collection=binding.collection,
                row_id=binding.row_id,
                binding_identity=verified_binding,
                original_row_sha256=verified_binding.original_row_sha256,
                page_relative_path=page,
                chart_consumer=f"REPORT_A.{binding.collection}[row_id={binding.row_id}].value",
                table_consumer=f"{page}#table-row:{binding.row_id}",
                narrative_consumer=f"{page}#clinical-narrative:{binding.row_id}",
                index_consumer=f"data/search-index.js#{binding.collection}:{binding.row_id}",
                source_binding_consumer=(
                    f"REPORT_A.{binding.collection}[row_id={binding.row_id}].source_field_path"
                ),
            )
        )
    return (
        data.model_copy(
            update={
                "safety": tuple(safety),
                "efficacy": tuple(efficacy),
                "user_edits": user_edits,
            }
        ),
        tuple(consumers),
    )


def validate_active_fact_revision_a(
    data: ReportAPortalData,
    active_revision: ActiveFactRevision,
) -> None:
    """Validate every A binding without creating or modifying a staging tree."""
    for fact, binding in active_revision.bindings_for("A"):
        if binding.collection not in {"safety", "efficacy"}:
            raise ReportAPortalError("A renderer只接受safety/efficacy领域绑定")
        try:
            validate_active_fact_binding(
                fact,
                binding,
                active_fact_binding_for_a(data, binding.collection, binding.row_id),
            )
        except ValueError as error:
            raise ReportAPortalError(str(error)) from error


def _a_statistical_identity(row: SafetyRow | EfficacyRow) -> tuple[str, str]:
    if isinstance(row, EfficacyRow):
        form = "crude_rate" if row.unit == "%" and row.numerator is not None else "estimate"
        return form, "participants" if row.numerator is not None else "estimate"
    forms = {
        "participant_proportion": ("crude_rate", "participants"),
        "participant_count": ("count", "participants"),
        "event_count": ("count", "events"),
        "person_time_rate": ("person_time_rate", "person_time"),
        "adjusted_estimate": ("adjusted_rate", "estimate"),
    }
    return forms[row.measure_object]


def active_fact_binding_for_a(
    data: ReportAPortalData,
    collection: Literal["safety", "efficacy"],
    row_id: str,
) -> ActiveFactBinding:
    """Resolve the immutable identity of an original A builder row."""
    if collection == "safety":
        candidates: tuple[SafetyRow | EfficacyRow, ...] = data.safety
    elif collection == "efficacy":
        candidates = data.efficacy
    else:
        raise ReportAPortalError("A renderer只接受safety/efficacy领域绑定")
    matches = [row for row in candidates if row.row_id == row_id]
    if len(matches) != 1:
        raise ReportAPortalError(f"A active fact绑定必须命中唯一领域行：{collection}/{row_id}")
    row = matches[0]
    if row.trial_id is None:
        raise ReportAPortalError("A active fact目标原行缺少试验身份")
    products = {item.id: item for item in data.products}
    trials = {item.id: item for item in data.trials}
    product = products[row.product_id]
    trial = trials[row.trial_id]
    row_payload = row.model_dump(mode="json")
    row_digest = canonical_sha256(row_payload)
    source_pointer = row.source_field_path or f"REPORT_A.{collection}[row_id={row.row_id}]"
    source_version = row.source_version_id or f"report-a-row:{row_digest}"
    statistical_form, measure_object = _a_statistical_identity(row)
    return ActiveFactBinding(
        report="A",
        collection=collection,
        row_id=row.row_id,
        product_id=row.product_id,
        drug_name=product.name,
        trial_id=row.trial_id,
        registry_id=trial.display_id,
        group_id=row.group_id,
        arm=row.arm,
        cohort_id=row.cohort_id,
        period=row.time_window if isinstance(row, SafetyRow) else row.timepoint,
        endpoint_definition=row.endpoint if isinstance(row, EfficacyRow) else None,
        event_definition=row.term if isinstance(row, SafetyRow) else None,
        statistical_form=statistical_form,
        measure_object=measure_object,
        unit=row.unit,
        normalized_unit=row.unit,
        source_version_id=source_version,
        source_pointer=source_pointer,
        original_row_sha256=row_digest,
    )


def render_report_a_site(
    data: ReportAPortalData,
    site_root: Path,
    *,
    publication_limitation_zh: str | None = None,
    public_provenance: PublicProvenance | None = None,
    calculation_evidence: tuple[PublicCalculationEvidence, ...] = (),
    active_revision: ActiveFactRevision | None = None,
) -> tuple[Path, ...]:
    """生成 11 个静态责任页及全部产品详情页。"""
    consumers: tuple[PortalConsumerNode, ...] = ()
    if active_revision is not None:
        data, consumers = _project_active_facts_a(data, active_revision)
    if public_provenance is not None:
        public_provenance = PublicProvenance.model_validate(
            public_provenance.model_dump(mode="json")
        )
        if (
            public_provenance.report_data_digest
            != hashlib.sha256(data.model_dump_json().encode("utf-8")).hexdigest()
        ):
            raise ReportAPortalError("公共来源与报告内容不一致")
    env = Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    site_root.mkdir(parents=True, exist_ok=True)
    _copy_assets(site_root)
    data_dir = site_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    # One immutable report revision has one presentation projection. Rebuilding
    # thousands of translated rows for every product page is both wasteful and
    # capable of making a large real report appear to hang.
    base_context = _view_context(
        data,
        current="overview",
        public_provenance=public_provenance,
        publication_limitation_zh=publication_limitation_zh,
    )
    display_payload = data.model_dump(mode="json")
    display_payload["calculation_evidence"] = [
        item.model_dump(mode="json") for item in calculation_evidence
    ]
    display_payload["public_sources"] = (
        [item.model_dump(mode="json") for item in public_provenance.sources]
        if public_provenance is not None
        else []
    )
    display_payload["products"] = [
        item.model_dump(mode="json") for item in base_context["products"]
    ]
    display_payload["trials"] = list(base_context["trials"])
    display_payload["efficacy"] = list(base_context["efficacy"])
    display_payload["safety"] = list(base_context["safety"])
    display_payload["regulatory"] = list(base_context["regulatory"])
    literal = json.dumps(display_payload, ensure_ascii=False, separators=(",", ":"))
    (data_dir / "report.js").write_text(f"window.REPORT_A={literal};\n", encoding="utf-8")

    generated: list[Path] = []
    for page_id, template_name in _STATIC_TEMPLATES:
        output = site_root / f"{page_id}.html"
        output.write_text(
            env.get_template(template_name).render(
                **{**base_context, "current": page_id}
            ),
            encoding="utf-8",
        )
        generated.append(output)

    product_dir = site_root / "products"
    product_dir.mkdir(parents=True, exist_ok=True)
    product_template = env.get_template("product.html.j2")
    display_products = {item.id: item for item in base_context["products"]}
    for product in data.products:
        output = product_dir / f"{product.id}.html"
        context = {
            **base_context,
            "current": "product-overview",
            "root_prefix": "../",
            "asset_prefix": "../assets",
            "data_prefix": "../data",
        }
        context["product"] = display_products[product.id]
        context["product_trials"] = tuple(
            row for row in context["trials"]
            if row["product_id"] == product.id
            or any(link["product_id"] == product.id for link in row["product_links"])
        )
        context["product_efficacy"] = tuple(
            row for row in context["efficacy"]
            if row["product_id"] == product.id
            and row["group_assignment_state"] != "unknown"
        )
        context["product_safety"] = tuple(
            row for row in context["safety"]
            if row["product_id"] == product.id
            and row["group_assignment_state"] != "unknown"
        )
        context["product_regulatory"] = tuple(
            row for row in context["regulatory"] if row["product_id"] == product.id
        )
        context["product_companies"] = tuple(
            row for row in data.companies if row.product_id == product.id
        )
        context["product_patents"] = tuple(
            row for row in data.patents if row.product_id == product.id
        )
        output.write_text(product_template.render(**context), encoding="utf-8")
        generated.append(output)

    routes = [
        {"route": f"/a/{page_id}", "path": f"{page_id}.html"} for page_id, _ in _STATIC_TEMPLATES
    ] + [
        {"route": f"/a/products/{product.id}", "path": f"products/{product.id}.html"}
        for product in data.products
    ]
    (data_dir / "sitemap.json").write_bytes(_canonical_json({"routes": routes}))
    search = (
        [
            {"title": item["title"], "slug": item["id"], "keywords": [item["group"]]}
            for item in _navigation()
        ]
        + [
            {
                "title": display_products[product.id].name,
                "slug": f"products/{product.id}",
                "keywords": [product.target, product.modality],
            }
            for product in data.products
        ]
        + [
            {
                "title": (
                    f"{row.term} · 产品归属待核"
                    if row.group_assignment_state == "unknown"
                    else row.clinical_narrative
                    or f"{row.term} · {display_products[row.product_id].name}"
                ),
                "slug": "safety",
                "keywords": [
                    row.row_id,
                    row.term,
                    row.value,
                    row.unit,
                    row.numerator,
                    row.denominator,
                    row.source_text,
                    row.source_field_path,
                ],
            }
            for row in data.safety
        ]
        + [
            {
                "title": (
                    f"{row.endpoint} · 产品归属待核"
                    if row.group_assignment_state == "unknown"
                    else row.clinical_narrative
                    or f"{row.endpoint} · {display_products[row.product_id].name}"
                ),
                "slug": "efficacy",
                "keywords": [
                    row.row_id,
                    row.endpoint,
                    row.value,
                    row.unit,
                    row.numerator,
                    row.denominator,
                    row.source_text,
                    row.source_field_path,
                ],
            }
            for row in data.efficacy
        ]
        + [
            {
                "title": (
                    f"{row.endpoint} · 产品归属待核"
                    if row.group_assignment_state == "unknown"
                    else f"{row.endpoint} · {display_products[row.product_id].name}"
                ),
                "slug": "efficacy",
                "keywords": [
                    row.row_id, row.trial_id, row.group_title,
                    row.time_window, row.domain, row.raw_value, row.raw_unit,
                ],
            }
            for row in data.additional_observations
        ]
    )
    (data_dir / "search-index.js").write_text(
        "window.__SEARCH_INDEX__="
        + json.dumps(search, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    if active_revision is not None:
        write_render_receipt(
            site_root,
            report="A",
            active_revision=active_revision,
            consumers=consumers,
        )
    return tuple(generated)


def _render_recovery_digest(
    data: ReportAPortalData,
    project_id: str,
    contract_version: int,
    lineage: ReportALineageBinding | None,
    public_provenance: PublicProvenance | None,
    calculation_evidence: tuple[PublicCalculationEvidence, ...],
    limitation: str | None,
) -> str:
    """Bind exact inputs and installed renderer resources, never infer old bindings."""
    root = Path(__file__).resolve().parents[4]
    digest = hashlib.sha256(
        _canonical_json(
            {
                "data": data.model_dump(mode="json"),
                "project_id": project_id,
                "contract_version": contract_version,
                "lineage": lineage.model_dump(mode="json") if lineage else None,
                "public_provenance": (
                    public_provenance.model_dump(mode="json") if public_provenance else None
                ),
                "calculation_evidence": [
                    item.model_dump(mode="json") for item in calculation_evidence
                ],
                "publication_limitation": limitation,
                "runtime_versions": {
                    name: dependency_version(name) for name in ("Jinja2", "pydantic")
                },
            }
        )
    )
    files = [
        path
        for path in (root / "src/ci_workflow").rglob("*")
        if path.is_file() and path.suffix in {".py", ".js", ".css", ".j2", ".json", ".yaml"}
    ]
    files.extend(root / name for name in ("package-manifest.json", "uv.lock"))
    files.extend(
        path
        for path in (root / "contracts").rglob("*")
        if path.is_file() and path.suffix in {".json", ".yaml"}
    )
    for path in sorted(files):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0" + path.read_bytes())
    for path in (
        resolve_logo_src(),
        resolve_echarts_bundle(),
        resolve_portal_asset("portal.css"),
        resolve_portal_asset("portal.js"),
    ):
        digest.update(path.name.encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def build_report_a_artifact(
    *,
    project_root: Path,
    data_path: Path,
    project_id: str,
    contract_version: int,
    run_id: str,
    lineage: ReportALineageBinding | None = None,
    public_provenance: PublicProvenance | None = None,
    calculation_evidence: tuple[PublicCalculationEvidence, ...] = (),
    publication_limitation_zh: str | None = None,
    recover_committed: bool = False,
) -> tuple[Path, Path]:
    """生成站点、锁定报告快照并写入 generated 清单。

    站点先写入未发布事务的 staging 目录；只有清单原子写入成功后，最终
    ``html/`` 目录才出现。中断只留下可证明未发布的残留，重跑自动恢复；
    任何已有清单或完成绑定一律拒绝覆盖。
    """
    data = load_report_a_data(data_path)
    if public_provenance is not None and (
        lineage is None
        or public_provenance.evidence_snapshot_id != lineage.evidence_snapshot_id
        or sorted(item.source_version_id for item in public_provenance.sources)
        != sorted(lineage.source_version_ids)
    ):
        raise ReportAPortalError("公共来源与报告谱系不一致")
    source_ids = (
        {item.source_version_id for item in public_provenance.sources}
        if public_provenance is not None else set()
    )
    safety_rows = {row.row_id: row for row in data.safety}
    if len({item.row_id for item in calculation_evidence}) != len(calculation_evidence):
        raise ReportAPortalError("公开计算依据存在重复报告行")
    for item in calculation_evidence:
        row = safety_rows.get(item.row_id)
        if (
            lineage is None or row is None or item.source_version_id not in source_ids
            or row.source_version_id != item.source_version_id
            or row.source_field_path != item.numerator_field_path
            or row.source_text != item.numerator_quote
            or row.numerator != item.numerator or row.denominator != item.denominator
            or row.value != item.value or row.unit != item.unit
        ):
            raise ReportAPortalError("公开计算依据与已锁定报告行不一致")
    started_at = datetime.now(UTC)
    transaction = UnpublishedRenderTransaction(
        project_root,
        report="A",
        report_version=data.report_version,
        run_id=run_id,
    )
    recovery_digest = _render_recovery_digest(
        data,
        project_id,
        contract_version,
        lineage,
        public_provenance,
        calculation_evidence,
        publication_limitation_zh,
    )
    if recover_committed and transaction.manifest_path.exists():
        for path in (transaction.manifest_path, transaction.version_root, transaction.site_root):
            if path.is_symlink():
                raise ReportAPortalError("已提交渲染恢复路径不得是链接")
        existing = ArtifactManifest.model_validate_json(transaction.manifest_path.read_bytes())
        bindings = [
            item.receipt
            for item in existing.deterministic_checks
            if item.check_id == "committed-render-input-v1" and item.status == "passed"
        ]
        if (
            existing.project_id != project_id
            or existing.contract_version != contract_version
            or existing.status != "generated"
            or bindings != [recovery_digest]
        ):
            raise ReportAPortalError("已提交渲染缺少一致的输入/源码绑定，拒绝覆盖或猜测复用")
        ManifestStore(project_root).verify_artifact(existing)
        load_locked_sitemap_source(project_root, ReportKind.A, data.report_version)
        return transaction.site_root, transaction.manifest_path
    try:
        staging_root = transaction.begin()
    except RenderTransactionError as error:
        raise ReportAPortalError(str(error)) from error
    render_report_a_site(
        data,
        staging_root,
        public_provenance=public_provenance,
        calculation_evidence=calculation_evidence,
        publication_limitation_zh=publication_limitation_zh,
    )

    result_rows: tuple[EfficacyRow | SafetyRow, ...] = (*data.efficacy, *data.safety)
    data_digest = hashlib.sha256(_canonical_json(data.model_dump(mode="json"))).hexdigest()
    if lineage is None:
        claim_ids = tuple(stable_id("claim", row.row_id) for row in result_rows)
        evidence_snapshot_id = stable_id("evidence-snapshot", project_id, data_digest)
        claim_snapshot_id = stable_id("claim-snapshot", project_id, data_digest)
        coverage_set_id = stable_id("coverage-set", project_id, "A", data_digest)
        coverage_projection_id = stable_id(
            "coverage-projection", project_id, "A", data.report_version
        )
        evidence_reference_ids = tuple(stable_id("source", row.source) for row in data.sources)
    else:
        claim_ids = lineage.claim_ids
        evidence_snapshot_id = lineage.evidence_snapshot_id
        claim_snapshot_id = lineage.claim_snapshot_id
        coverage_set_id = lineage.coverage_set_id
        coverage_projection_id = lineage.coverage_projection_id
        evidence_reference_ids = lineage.source_version_ids
    snapshot_payload = ReportSnapshotManifest(
        schema_version="1.0",
        project_id=project_id,
        contract_version=contract_version,
        report="A",
        report_version=data.report_version,
        data_cutoff=data.data_cutoff,
        evidence_snapshot_id=evidence_snapshot_id,
        claim_snapshot_id=claim_snapshot_id,
        coverage_set_id=coverage_set_id,
        claim_ids=claim_ids,
        created_at=started_at,
    )
    locked = SnapshotStore(project_root).lock_report_snapshot(
        report="A", manifest=snapshot_payload.model_dump(mode="json")
    )
    site_digest, site_bytes = site_directory_digest(staging_root)
    modified_at = datetime.fromtimestamp(
        max(path.stat().st_mtime for path in staging_root.rglob("*") if path.is_file()),
        tz=UTC,
    )
    package_digest = hashlib.sha256(
        (Path(__file__).resolve().parents[4] / "package-manifest.json").read_bytes()
    ).hexdigest()
    catalog = PageRegistry.load().catalog(ReportKind.A)
    manifest = ArtifactManifest(
        schema_version="1.0",
        manifest_id=stable_id("artifact-manifest", project_id, run_id, "A", data.report_version),
        project_id=project_id,
        contract_version=contract_version,
        report="A",
        report_version=data.report_version,
        data_cutoff=data.data_cutoff,
        producer_run_id=run_id,
        source_commit=_git_commit(),
        package_digest=package_digest,
        evidence_snapshot_id=evidence_snapshot_id,
        claim_snapshot_id=claim_snapshot_id,
        report_snapshot_id=locked.snapshot_id,
        coverage_set_id=coverage_set_id,
        coverage_projection_id=coverage_projection_id,
        structured_exceptions=(),
        pages_or_sections=tuple(page.id for page in catalog.pages),
        product_ids=data.product_ids,
        trial_ids=data.trial_ids,
        claim_ids=claim_ids,
        chart_ids=("landscape-summary", "efficacy-summary", "safety-summary", "matrix-summary"),
        table_ids=(
            "products",
            "trials",
            "efficacy",
            "safety",
            "regulatory",
            "companies",
            "patents",
            "history",
        ),
        evidence_reference_ids=evidence_reference_ids,
        design_contract=DesignContractBinding(
            roles=("report-portal",),
            digest=package_digest,
            applicable_sections=("项目设计合同", "站点式门户"),
        ),
        renderer=RendererBinding(name="report-a-portal", version="1.0"),
        filter_state={},
        generated_at=started_at,
        deterministic_checks=(
            DeterministicCheck(
                check_id="committed-render-input-v1",
                status="passed",
                receipt=recovery_digest,
            ),
            DeterministicCheck(
                check_id="eleven-static-plus-products",
                status="passed",
                receipt=data_digest,
            ),
        ),
        render_verdict=RenderVerdict(
            verdict_id=stable_id("render-verdict", run_id, "awaiting-independent-review"),
            status="rejected",
            verified_at=modified_at,
            anchor_ids=("尚待独立浏览器验收",),
        ),
        accepted_by=None,
        artifact=ArtifactFileBinding(
            relative_path=f"reports/A/{data.report_version}/html",
            sha256=site_digest,
            byte_size=site_bytes,
            modified_at=modified_at,
            media_type="directory",
        ),
        status="generated",
        supersedes_manifest_id=None,
    )
    try:
        site_root, manifest_path = transaction.commit(
            _canonical_json(manifest.model_dump(mode="json"))
        )
    except RenderTransactionError as error:
        raise ReportAPortalError(str(error)) from error
    return site_root, manifest_path
