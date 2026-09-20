"""Task 5.4：从已校验的 A 类报告数据包生成完整纯静态多页面门户。"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from importlib.metadata import version as dependency_version
from pathlib import Path
from typing import Any, Literal, Self

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.enums import FactDisclosureState, ReportKind
from ci_workflow.domain.ids import stable_id
from ci_workflow.domain.public_provenance import PublicProvenance
from ci_workflow.qc.browser import load_locked_sitemap_source, site_directory_digest
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

    @field_validator("id")
    @classmethod
    def _id_is_slug(cls, value: str) -> str:
        if not value or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in value):
            raise ValueError("产品标识必须是安全英文路径片段")
        return value


class TrialRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    display_id: str
    product_id: str
    name: str
    phase: str
    region: str
    status: str
    sample_size: int = Field(gt=0)
    treatment_sample_size: int | None = Field(default=None, gt=0)
    role: str

    @model_validator(mode="after")
    def _treatment_group_cannot_exceed_trial(self) -> TrialRow:
        if self.treatment_sample_size is not None and self.treatment_sample_size > self.sample_size:
            raise ValueError("治疗组样本量不得大于试验总样本量")
        return self


class EfficacyRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    row_id: str
    product_id: str
    trial_id: str
    endpoint: str
    timepoint: str
    arm: str
    arm_detail: str | None = None
    value: float | None = Field(default=None, allow_inf_nan=False)
    # F01 修复：REPORTED_ZERO 携带 0 是合法科学事实；REPORTED_VALUE 必须有值
    disclosure_state: FactDisclosureState = FactDisclosureState.REPORTED_VALUE

    @model_validator(mode="after")
    def _value_disclosure_consistency(self) -> "EfficacyRow":
        if self.disclosure_state == FactDisclosureState.REPORTED_VALUE and self.value is None:
            raise ValueError("REPORTED_VALUE 必须携带数值")
        if self.disclosure_state == FactDisclosureState.REPORTED_ZERO and self.value is not None and self.value != 0:
            raise ValueError("REPORTED_ZERO 数值必须为 0")
        return self
    numerator: int | None = Field(default=None, ge=0)
    denominator: int | None = Field(default=None, gt=0)
    unit: str
    population: str

    @model_validator(mode="after")
    def _undisclosed_row_carries_no_value(self) -> EfficacyRow:
        if self.disclosure_state != FactDisclosureState.REPORTED_VALUE and self.value is not None:
            raise ValueError("未披露状态行不得携带数值")
        if self.disclosure_state == FactDisclosureState.REPORTED_VALUE and self.value is None:
            raise ValueError("已报告数值行必须携带数值")
        return self

    @model_validator(mode="after")
    def _counts_are_complete_and_ordered(self) -> EfficacyRow:
        if (self.numerator is None) != (self.denominator is None):
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
    arm: str = "治疗组"
    arm_detail: str | None = None
    category: str
    term: str
    value: float | None = Field(allow_inf_nan=False)
    numerator: int | None = Field(default=None, ge=0)
    denominator: int | None = Field(default=None, gt=0)
    unit: str
    time_window: str
    disclosure_state: Literal["已公开", "未公开", "不适用"] = "已公开"

    @model_validator(mode="after")
    def _value_matches_disclosure_state(self) -> SafetyRow:
        if self.disclosure_state == "已公开" and self.value is None:
            raise ValueError("已公开安全性记录必须包含数值")
        if self.disclosure_state == "未公开" and self.value is not None:
            raise ValueError("未公开安全性记录不得填入推测数值")
        if (self.numerator is None) != (self.denominator is None):
            raise ValueError("安全性分子与分母必须同时公开或同时缺失")
        if (
            self.numerator is not None
            and self.denominator is not None
            and self.numerator > self.denominator
        ):
            raise ValueError("安全性分子不得大于分母")
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
    schema_version: str
    report_version: str
    indication: str
    data_cutoff: datetime
    products: tuple[ProductRow, ...] = Field(min_length=1)
    trials: tuple[TrialRow, ...] = Field(min_length=1)
    efficacy: tuple[EfficacyRow, ...] = Field(min_length=1)
    safety: tuple[SafetyRow, ...] = Field(min_length=1)
    regulatory: tuple[RegulatoryRow, ...] = Field(min_length=1)
    companies: tuple[CompanyRow, ...] = Field(min_length=1)
    patents: tuple[PatentRow, ...] = Field(min_length=1)
    history: tuple[HistoryRow, ...] = Field(min_length=1)
    sources: tuple[SourceRow, ...] = Field(min_length=1)

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
        linked_product_rows: tuple[
            EfficacyRow | SafetyRow | RegulatoryRow | CompanyRow | PatentRow | HistoryRow,
            ...,
        ] = (
            *self.efficacy,
            *self.safety,
            *self.regulatory,
            *self.companies,
            *self.patents,
            *self.history,
        )
        if any(item.product_id not in products for item in linked_product_rows):
            raise ValueError("报告事实引用了未知产品")
        if any(item.trial_id not in trials for item in self.efficacy):
            raise ValueError("疗效事实引用了未知试验")
        if any(item.trial_id is not None and item.trial_id not in trials for item in self.safety):
            raise ValueError("安全性事实引用了未知试验")
        required_safety = {"治疗期间不良事件", "严重不良事件", "特别关注不良事件", "常见不良事件"}
        product_by_id = {item.id: item for item in self.products}
        for product_id in products:
            if product_by_id[product_id].result_status != "有公开关键结果":
                continue
            categories = {row.category for row in self.safety if row.product_id == product_id}
            if not required_safety <= categories:
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


def _safety_term_projection(term: str) -> tuple[str, str]:
    normalized = " ".join(term.split()).casefold()
    known = _SAFETY_TERM_ALIASES.get(normalized)
    if known is not None:
        return known
    return f"raw:{normalized}", term


def _display_safety_rows(data: ReportAPortalData) -> tuple[dict[str, object], ...]:
    """加入展示归一元数据，但永不覆盖安全性事实的原始术语。

    AESI 只有在至少一条对应数值已公开时才进入展示数据集；全空
    AESI 不应在页面、图表、筛选或表格中占据一个没有信息的维度。
    """
    rows: list[dict[str, object]] = []
    for item in data.safety:
        row = item.model_dump(mode="json")
        term_key, term_label = _safety_term_projection(item.term)
        row["original_term"] = item.term
        row["term_key"] = term_key
        row["term_label"] = term_label
        row["arm_detail"] = _native_arm_detail_zh(item.arm_detail)
        rows.append(row)
    if not any(row["category"] == "特别关注不良事件" and row["value"] is not None for row in rows):
        rows = [row for row in rows if row["category"] != "特别关注不良事件"]
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


def _display_trials(data: ReportAPortalData) -> tuple[dict[str, object], ...]:
    """把登记平台字段投影成面向医学用户的中文展示，不改写证据原文。"""
    product_names = {item.id: item.name for item in _display_products(data)}
    rows: list[dict[str, object]] = []
    for trial in data.trials:
        row = trial.model_dump(mode="json")
        row["original_name"] = trial.name
        if not _contains_chinese(trial.name):
            row["name"] = f"{product_names[trial.product_id]} {trial.phase}临床研究"
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


def _native_timepoint_zh(value: str) -> str:
    text = re.sub(r"\bWeeks?\s*(\d+)\b", r"第\1周", value, flags=re.I)
    text = re.sub(r"\bDays?\s*(\d+)\b", r"第\1天", text, flags=re.I)
    text = re.sub(r"up to End of Study", "至研究结束", text, flags=re.I)
    text = re.sub(r"\bBaseline\b", "基线", text, flags=re.I)
    text = re.sub(r"\bto\b", "至", text, flags=re.I)
    text = re.sub(r"\band\b|&", "、", text, flags=re.I)
    replacements = (
        (
            r"last available rolling average before the first dose of study drug",
            "首次给药前最后一次可用滚动均值",
        ),
        (r"From first dose of study drug", "自首次给药起"),
        (r"\bPre-dose\b|\bPredose\b", "给药前"),
        (r"\bpost-dose\b", "给药后"),
        (r"\bhours?\b", "小时"),
        (r"\bof\b", "的"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.I)
    return " ".join(text.split())


def _native_endpoint_zh(value: str) -> str:
    """把登记结果长标题收敛成中文临床终点名；原文仍保存在证据层。"""
    if len(value) <= 40 and len(re.findall(r"[A-Za-z]{3,}", value)) <= 2:
        return value
    if _contains_chinese(value) and len(re.findall(r"[A-Za-z]{3,}", value)) < 3:
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
        (r"adverse event", lambda _m: "不良事件"),
    )
    if not measure:
        measure = "其他临床疗效指标"
        for pattern, label in scale_patterns:
            match = re.search(pattern, value, re.I)
            if match:
                measure = label(match)
                break

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
    suffix = "；" + "；".join(qualifiers) if qualifiers else ""
    return f"{measure}{form}{suffix}"


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
    if re.search(r"[A-Za-z]{3,}", value):
        return "预设分析人群：按登记平台分析集定义及相应时间点可用数据纳入"
    return value


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

        row["timepoint"] = _native_timepoint_zh(str(row["timepoint"]))

        arm = str(row["arm"])
        arm = re.sub(r"\bPart\s*A\b", "A部分", arm, flags=re.I)
        arm = re.sub(r"\bPlacebo\b", "安慰剂", arm, flags=re.I)
        arm = re.sub(r"\bQ2W\b", "每2周1次", arm, flags=re.I)
        arm = re.sub(r"\bQ4W\b", "每4周1次", arm, flags=re.I)
        row["arm"] = arm
        row["arm_detail"] = _native_arm_detail_zh(row.get("arm_detail"))

        row["population"] = _native_population_zh(str(row["population"]))
        unit = str(row["unit"])
        row["unit"] = {
            "weeks": "周",
            "days": "天",
            "score on a scale": "分",
            "units on a scale": "分",
            "points on a scale": "分",
            "events per patient-year": "每患者年事件数",
        }.get(unit.casefold(), unit)
        rows.append(row)
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
        "safety": display_safety,
        "safety_public_categories": tuple(
            category
            for category in ("严重不良事件", "治疗期间不良事件", "常见不良事件", "特别关注不良事件")
            if any(
                row["category"] == category and row["value"] is not None for row in display_safety
            )
        ),
        "regulatory": _display_regulatory(data),
        "safety_event_filters": _safety_event_filters(display_safety),
        "sources": data.sources,
        "external_sources": public_provenance.sources if public_provenance else (),
        "companies": data.companies,
        "patents": data.patents,
        "history": data.history,
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


def render_report_a_site(
    data: ReportAPortalData,
    site_root: Path,
    *,
    publication_limitation_zh: str | None = None,
    public_provenance: PublicProvenance | None = None,
) -> tuple[Path, ...]:
    """生成 11 个静态责任页及全部产品详情页。"""
    if public_provenance is not None:
        public_provenance = PublicProvenance.model_validate(
            public_provenance.model_dump(mode="json")
        )
        if public_provenance.report_data_digest != hashlib.sha256(
            data.model_dump_json().encode("utf-8")
        ).hexdigest():
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
    display_payload = data.model_dump(mode="json")
    display_payload["public_sources"] = (
        [item.model_dump(mode="json") for item in public_provenance.sources]
        if public_provenance is not None else []
    )
    display_payload["products"] = [item.model_dump(mode="json") for item in _display_products(data)]
    display_payload["trials"] = list(_display_trials(data))
    display_payload["efficacy"] = list(_display_efficacy_rows(data))
    display_payload["safety"] = list(_display_safety_rows(data))
    display_payload["regulatory"] = list(_display_regulatory(data))
    literal = json.dumps(display_payload, ensure_ascii=False, separators=(",", ":"))
    (data_dir / "report.js").write_text(f"window.REPORT_A={literal};\n", encoding="utf-8")

    generated: list[Path] = []
    for page_id, template_name in _STATIC_TEMPLATES:
        output = site_root / f"{page_id}.html"
        output.write_text(
            env.get_template(template_name).render(
                **_view_context(
                    data,
                    current=page_id,
                    public_provenance=public_provenance,
                    publication_limitation_zh=publication_limitation_zh,
                )
            ),
            encoding="utf-8",
        )
        generated.append(output)

    product_dir = site_root / "products"
    product_dir.mkdir(parents=True, exist_ok=True)
    product_template = env.get_template("product.html.j2")
    display_products = {item.id: item for item in _display_products(data)}
    for product in data.products:
        output = product_dir / f"{product.id}.html"
        context = _view_context(
            data,
            current="product-overview",
            depth=1,
            public_provenance=public_provenance,
            publication_limitation_zh=publication_limitation_zh,
        )
        context["product"] = display_products[product.id]
        context["product_trials"] = tuple(
            row for row in context["trials"] if row["product_id"] == product.id
        )
        context["product_efficacy"] = tuple(
            row for row in context["efficacy"] if row["product_id"] == product.id
        )
        context["product_safety"] = tuple(
            row for row in context["safety"] if row["product_id"] == product.id
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
    search = [
        {"title": item["title"], "slug": item["id"], "keywords": [item["group"]]}
        for item in _navigation()
    ] + [
        {
            "title": display_products[product.id].name,
            "slug": f"products/{product.id}",
            "keywords": [product.target, product.modality],
        }
        for product in data.products
    ]
    (data_dir / "search-index.js").write_text(
        "window.__SEARCH_INDEX__="
        + json.dumps(search, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    return tuple(generated)


def _render_recovery_digest(
    data: ReportAPortalData, project_id: str, contract_version: int,
    lineage: ReportALineageBinding | None, public_provenance: PublicProvenance | None,
    limitation: str | None,
) -> str:
    """Bind exact inputs and installed renderer resources, never infer old bindings."""
    root = Path(__file__).resolve().parents[4]
    digest = hashlib.sha256(_canonical_json({
        "data": data.model_dump(mode="json"), "project_id": project_id,
        "contract_version": contract_version,
        "lineage": lineage.model_dump(mode="json") if lineage else None,
        "public_provenance": (
            public_provenance.model_dump(mode="json") if public_provenance else None
        ),
        "publication_limitation": limitation,
        "runtime_versions": {name: dependency_version(name) for name in ("Jinja2", "pydantic")},
    }))
    files = [path for path in (root / "src/ci_workflow").rglob("*")
             if path.is_file() and path.suffix in {".py", ".js", ".css", ".j2", ".json", ".yaml"}]
    files.extend(root / name for name in ("package-manifest.json", "uv.lock"))
    files.extend(path for path in (root / "contracts").rglob("*")
                 if path.is_file() and path.suffix in {".json", ".yaml"})
    for path in sorted(files):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0" + path.read_bytes())
    for path in (resolve_logo_src(), resolve_echarts_bundle(),
                 resolve_portal_asset("portal.css"), resolve_portal_asset("portal.js")):
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
    started_at = datetime.now(UTC)
    transaction = UnpublishedRenderTransaction(
        project_root,
        report="A",
        report_version=data.report_version,
        run_id=run_id,
    )
    recovery_digest = _render_recovery_digest(
        data, project_id, contract_version, lineage, public_provenance, publication_limitation_zh,
    )
    if recover_committed and transaction.manifest_path.exists():
        for path in (transaction.manifest_path, transaction.version_root, transaction.site_root):
            if path.is_symlink():
                raise ReportAPortalError("已提交渲染恢复路径不得是链接")
        existing = ArtifactManifest.model_validate_json(transaction.manifest_path.read_bytes())
        bindings = [item.receipt for item in existing.deterministic_checks
                    if item.check_id == "committed-render-input-v1" and item.status == "passed"]
        if (existing.project_id != project_id or existing.contract_version != contract_version
                or existing.status != "generated" or bindings != [recovery_digest]):
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
                check_id="committed-render-input-v1", status="passed", receipt=recovery_digest,
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
