"""Task 7.5: build the complete static C-class design comparison portal.

The renderer is an adapter over Task 7.1–7.4 design observations. It projects
immutable design facts into offline chart groups, complete tables, and evidence
views. The browser only filters, restores URL state, and opens the data-basis
panel; it does not recompute scientific facts or design recommendations.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections.abc import Mapping, Sequence
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any, Self

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState, ReportKind
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.qc.browser import route_to_site_path
from ci_workflow.renderers.portal.active_fact_projection import (
    ActiveFactBinding,
    ActiveFactRevision,
    PortalConsumerNode,
    canonical_sha256,
    canonical_source_pointer,
    user_edit_disclosure,
    validate_active_fact_binding,
    write_render_receipt,
)
from ci_workflow.renderers.portal.builder import (
    resolve_echarts_bundle,
    resolve_logo_src,
    resolve_portal_asset,
)
from ci_workflow.renderers.portal.evidence_drawer import (
    render_evidence_drawer_embed,
    render_evidence_drawer_host,
)
from ci_workflow.renderers.portal.report_a import ProductRow, TrialRow
from ci_workflow.reports.c import (
    DesignFieldFamily,
    DesignGateDecision,
    DesignObservation,
    evaluate_design_gate,
)
from ci_workflow.reports.common.evidence_view import (
    EvidenceField,
    EvidenceFieldState,
    EvidenceObservationKind,
    EvidenceView,
    OriginalTextStatus,
    UserEditDisclosure,
)
from ci_workflow.reports.common.numeric_projection import NumericMeasureKind, project_numeric
from ci_workflow.reports.common.page_registry import PageRegistry, ReportCatalog, StaticPage
from ci_workflow.reports.common.view_state import ReportRow

from .report_a import _native_endpoint_zh, _native_timepoint_zh

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates" / "c"
_ASSET_DIR = Path(__file__).resolve().parent / "assets"

_FIELD_LABELS_ZH: dict[str, str] = {
    "trial_identity": "试验标识",
    "target_population": "目标人群",
    "inclusion_criterion": "入选标准",
    "exclusion_criterion": "排除标准",
    "arm_randomization_blinding": "随机与盲法",
    "experimental_arm": "试验组干预",
    "control_arm": "对照干预",
    "dosing_regimen": "给药方案",
    "primary_endpoint_definition": "主要终点定义",
    "primary_endpoint_timepoint": "主要终点时间点",
    "secondary_endpoint_definition": "次要终点定义",
    "secondary_endpoint_timepoint": "次要终点时间点",
    "analysis_sets": "分析集",
    "statistical_comparisons": "主要比较与统计模型",
    "multiplicity_adjustment": "多重性校正",
    "missing_data_handling": "缺失数据处理",
    "visit_schedule": "访视与随访",
    "planned_or_actual_sample_size": "计划或实际样本量",
    "analysis_population": "分析人群",
    "comparison_logic": "比较方法",
    "statistical_model": "统计模型",
    "effect_size": "效应量",
    "multiplicity": "多重性控制",
}

_PAGE_FIELDS: dict[str, frozenset[str] | None] = {
    # 首页与设计图谱是横向研究矩阵入口：保留该页范围内的全部设计观察，
    # 不再压缩总览字段。其他页面继续按页面责任展示专题字段。
    "overview": None,
    "design-map": None,
    "trial-profile": None,
    "population-disease-definition": frozenset({"target_population"}),
    "inclusion-criteria": frozenset({"inclusion_criterion"}),
    "exclusion-criteria": frozenset({"exclusion_criterion"}),
    "treatment-arms": frozenset(
        {
            "arm_randomization_blinding",
            "experimental_arm",
            "control_arm",
            "dosing_regimen",
        }
    ),
    "endpoint-timepoint-matrix": frozenset(
        {
            "primary_endpoint_definition",
            "primary_endpoint_timepoint",
            "secondary_endpoint_definition",
            "secondary_endpoint_timepoint",
        }
    ),
    "visit-duration-followup": frozenset({"visit_schedule", "dosing_regimen"}),
    "sample-analysis-statistics": frozenset(
        {
            "planned_or_actual_sample_size",
            "analysis_population",
            "analysis_sets",
            "statistical_comparisons",
            "multiplicity_adjustment",
            "missing_data_handling",
        }
    ),
    "design-patterns": frozenset(
        {
            "primary_endpoint_definition",
            "primary_endpoint_timepoint",
            "arm_randomization_blinding",
            "target_population",
        }
    ),
}

_PAGE_CHART_TYPE: dict[str, str] = {
    "overview": "status_matrix",
    "design-map": "status_matrix",
    "trial-profile": "status_matrix",
    "population-disease-definition": "status_matrix",
    "inclusion-criteria": "status_matrix",
    "exclusion-criteria": "status_matrix",
    "treatment-arms": "status_matrix",
    "endpoint-timepoint-matrix": "status_matrix",
    "visit-duration-followup": "timeline",
    "sample-analysis-statistics": "bubble",
    "design-patterns": "status_matrix",
}

_FILTER_DIMENSION_LABELS = {
    "product": "产品",
    "target": "靶点/机制",
    "trial": "试验",
    "element": "设计要素",
    "field_family_zh": "设计领域",
    "scale": "量表",
    "timepoint": "时间点",
    "disclosure_state": "披露状态",
}

_FAMILY_LABELS_ZH = {
    DesignFieldFamily.POPULATION: "人群与标准",
    DesignFieldFamily.GROUPING: "分组设计",
    DesignFieldFamily.INTERVENTION: "干预与对照",
    DesignFieldFamily.DOSE_SCHEDULE: "给药与疗程",
    DesignFieldFamily.ENDPOINT: "终点定义",
    DesignFieldFamily.TIMEPOINT: "评估时间点",
    DesignFieldFamily.OPERATIONAL: "访视与随访",
    DesignFieldFamily.SAMPLE_SIZE: "样本量",
    DesignFieldFamily.STATISTICAL: "统计分析",
    DesignFieldFamily.TRIAL_IDENTITY: "试验身份",
}

_STATE_LABELS = {
    FactDisclosureState.REPORTED_VALUE: "已报告值",
    FactDisclosureState.REPORTED_ZERO: "已报告零值",
    FactDisclosureState.NOT_PUBLICLY_DISCLOSED: "未公开",
    FactDisclosureState.NOT_REPORTED: "未报告",
    FactDisclosureState.NOT_APPLICABLE: "不适用",
    FactDisclosureState.BELOW_REPORTING_THRESHOLD: "低于报告阈值",
    FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE: "路径未解析",
    FactDisclosureState.CONFLICTING: "来源冲突",
    FactDisclosureState.USER_CLEARED: "用户清除，待重新核实",
}


class ReportCPortalError(ValueError):
    """C 类门户输入、设计门槛或物理站点构建失败。"""


class ReportCPortalData(BaseModel):
    """C 类门户输入：产品、试验与已校验设计观察。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = Field(min_length=1)
    report_version: str = Field(min_length=1)
    indication_id: str = Field(min_length=1)
    indication: str = Field(min_length=1)
    data_cutoff: datetime
    report_snapshot_id: str | None = None
    products: tuple[ProductRow, ...] = Field(min_length=1)
    trials: tuple[TrialRow, ...] = Field(min_length=1)
    observations: tuple[DesignObservation, ...] = Field(min_length=1)
    user_edits: dict[str, UserEditDisclosure] = Field(default_factory=dict)
    # 独立复核 C r19：包内设计路径综合（patterns + candidate_paths）随门户数据下发，
    # design-patterns 页不再空转为核心事实表
    design_paths: Mapping[str, Any] | None = None

    @field_validator("report_snapshot_id")
    @classmethod
    def _snapshot_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("C 类报告锁定快照标识不得为空")
        return value

    @model_validator(mode="after")
    def _products_and_trials_align(self) -> Self:
        product_ids = {item.id for item in self.products}
        trial_ids = [item.id for item in self.trials]
        if len(trial_ids) != len(set(trial_ids)):
            raise ValueError("试验标识不得重复")
        for trial in self.trials:
            if trial.product_id not in product_ids:
                raise ValueError(f"试验 {trial.id} 引用了未知产品 {trial.product_id}")
        for observation in self.observations:
            if observation.product_id not in product_ids:
                raise ValueError(
                    f"观察 {observation.row_id} 引用了未知产品 {observation.product_id}"
                )
            if observation.trial_id not in set(trial_ids):
                raise ValueError(f"观察 {observation.row_id} 引用了未知试验 {observation.trial_id}")
        return self

    @property
    def product_ids(self) -> tuple[str, ...]:
        return tuple(item.id for item in self.products)

    @property
    def trial_ids(self) -> tuple[str, ...]:
        return tuple(item.id for item in self.trials)


def load_report_c_data(path: Path) -> ReportCPortalData:
    """读取并校验 C 类门户数据包。"""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReportCPortalError(f"无法读取 C 类报告数据：{path}") from exc
    try:
        return ReportCPortalData.model_validate(payload)
    except ValueError as exc:
        raise ReportCPortalError(f"C 类报告数据不符合合同：{exc}") from exc


def _json(value: Any) -> str:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def _canonical_json(value: Any) -> bytes:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"{payload}\n".encode()


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if hasattr(value, "value") and not isinstance(value, (str, bytes, int, float, bool)):
        value = getattr(value, "value", value)
    result = " ".join(str(value).split())
    return result or default


_REGISTRY_TAG_PATTERN = re.compile(r"<\s*/?\s*[A-Za-z][^>]*>", re.I)
_MINIMUM_AGE_PATTERN = re.compile(
    r"\bminimum\s*age\s*=\s*(?P<age>\d+(?:\.\d+)?)\s*(?:years?|年)\b",
    re.I,
)
_AGE_PATTERNS = (
    re.compile(
        r"\b(?:age|aged|ages?)\b[^.;；]{0,80}?"
        r"(?P<age>\d+(?:\.\d+)?)\s*(?:years?|年)\b",
        re.I,
    ),
    re.compile(r"(?:>=|≥)\s*(?P<age>\d+(?:\.\d+)?)\s*(?:years?|年)\b", re.I),
    re.compile(
        r"\b(?P<age>\d+(?:\.\d+)?)\s*(?:years?|年)\s*"
        r"(?:and|or)\s+(?:older|above|以上)\b",
        re.I,
    ),
)


def _registry_display_text(value: Any) -> str:
    """Make registry excerpts safe and readable without changing source evidence."""
    text = _text(value)
    text = _REGISTRY_TAG_PATTERN.sub(" ", text)
    text = unescape(text)
    text = _REGISTRY_TAG_PATTERN.sub(" ", text)
    for escaped, normalized in (
        (r"\>=", "≥"),
        (r"\<=", "≤"),
        (r"\<", "<"),
        (r"\>", ">"),
        (">=", "≥"),
        ("<=", "≤"),
    ):
        text = text.replace(escaped, normalized)
    text = re.sub(r"(?:^|[；;])\s*[•*]\s*", " ", text)
    return _text(text).strip(" ;；:")


def _registry_minimum_age(text: str) -> str | None:
    match = _MINIMUM_AGE_PATTERN.search(text)
    if match:
        return match.group("age")
    for pattern in _AGE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group("age")
    return None


def _target_population_text(text: str) -> str:
    minimum_age = _registry_minimum_age(text)
    if minimum_age:
        return f"登记最低年龄：{minimum_age}岁"
    folded = text.casefold()
    if "at least 3 years" in folded and re.search(r"\batopic dermatitis\b|\bad\b", folded):
        return "特应性皮炎病程至少3年"
    if "adult" in folded and "adolescent" in folded:
        return "成人及青少年受试者"
    if re.search(r"\bchildren?\b|\bpediatric\b", folded):
        return "儿童受试者"
    if text:
        return "登记目标人群已记录（原文见来源）"
    raise ReportCPortalError("目标人群原文为空，不能生成报告")


def _is_multi_criterion_source(text: str) -> bool:
    return bool(
        re.search(
            r"<\s*(?:p|li|ul|ol)\b|(?:inclusion|exclusion)\s+criteria\s*:"
            r"|participants are excluded",
            text,
            re.I,
        )
    )


def _eligibility_source_text(field: str, text: str) -> str:
    if not text:
        raise ReportCPortalError("入排标准原文为空，不能生成报告")
    value = _registry_display_text(text)
    value = re.sub(r"^Inclusion Criteria\s*:\s*", "", value, flags=re.I)
    value = re.sub(
        r"^Participants are excluded from the study if any of the following criteria apply\s*:\s*",
        "",
        value,
        flags=re.I,
    )
    label = "登记入选标准" if field == "inclusion_criterion" else "登记排除标准"
    folded = value.casefold()
    phrase_map = (
        (
            "participants must be 12 years",
            "年龄≥12岁；特应性皮炎病程≥1年；"
            "既往生物制剂或口服JAK抑制剂疗效不足；"
            "基线vIGA-AD 3或4分；EASI≥16分；"
            "BSA受累≥10%；峰值瘙痒NRS≥4分；"
            "体重≥25 kg；能够配合访视及研究操作",
        ),
        (
            "known history of or suspected significant current immunosuppression",
            "影响特应性皮炎评估的皮肤合并症；当前或疑似显著免疫抑制；恶性肿瘤史（已切除且治愈超过5年的非黑色素瘤皮肤癌除外）；实体器官或干细胞移植史；基线前4周内需系统治疗的活动性或慢性感染；筛选期HIV、乙肝或丙肝阳性；活动性、潜伏性或未充分治疗的结核，疑似肺外结核或结核高风险；规定时间窗内使用禁用治疗；筛选期有临床意义的实验室异常；对研究药物或辅料过敏",
        ),
        (
            "inadequate response is defined",
            "中高效外用糖皮质激素每日治疗至少28天（或说明书允许的最长疗程，以较短者为准），仍未达到并维持缓解或低疾病活动状态",
        ),
        (
            "moderate to severe atopic dermatitis for at least 12 months",
            "中重度特应性皮炎病程≥12个月",
        ),
        (
            "diagnosed with atopic dermatitis 6 months duration",
            "特应性皮炎病程≥6个月（儿童≥3个月），且筛选前4周病情稳定、无显著加重",
        ),
        ("iga score of 2 to 3 at the screening and baseline", "筛选期及基线IGA为2–3分"),
        (
            "investigator's global assessment (iga) score of 2 to 3",
            "筛选期及基线IGA为2–3分；第8周长期安全性期IGA为0–4分",
        ),
        ("v-iga-ad of 3 or 4", "基线vIGA-AD为3或4分"),
        ("ad involvement of 10%", "筛选期及基线SCORAD评估的BSA受累≥10%"),
        ("atopic dermatitis covering ≥5% and ≤ 35%", "特应性皮炎BSA受累5%–35%"),
        ("ad involvement ≥5% to ≤40%", "可治疗BSA受累5%–40%（不含头皮）"),
        ("body weight of ≥ 40 kg", "12–17岁受试者基线体重≥40 kg"),
        ("concurrent enrolment in another clinical trial", "同时参加另一项使用试验用药的临床试验"),
        ("tcss are medically inadvisable", "研究者认为不宜使用外用糖皮质激素"),
        ("prior exposure to any janus kinase", "既往使用过JAK抑制剂"),
        (
            "other concomitant skin conditions",
            "存在可能干扰评估的其他皮肤病，或需频繁住院/静脉治疗的红皮病、难治性或不稳定皮肤病",
        ),
        ("unstable course of ad", "基线前4周特应性皮炎病情不稳定（自行改善或快速恶化）"),
        ("serious medical condition", "存在妨碍参研或显著增加风险的严重疾病或有临床意义异常"),
        ("pregnant or breastfeeding", "妊娠、哺乳，或计划在研究期间及末次给药后90天内妊娠"),
        (
            "biological product within 12 weeks or 5 half-lives",
            "首次给药前12周或5个半衰期内使用过生物制剂（取较长者）",
        ),
        ("skin co-morbidity", "存在影响特应性皮炎评估的皮肤合并症"),
        ("immunocompromised at screening", "筛选期存在免疫功能受损"),
    )
    native = next((zh for phrase, zh in phrase_map if phrase in folded), "")
    if not native:
        return f"{label}原文：{value}"
    return f"{label}：{native}"


def _state_label(state: FactDisclosureState | str) -> str:
    if isinstance(state, FactDisclosureState):
        return _STATE_LABELS.get(state, "未报告")
    try:
        return _STATE_LABELS.get(FactDisclosureState(state), "未报告")
    except ValueError:
        return "未报告"


def _field_label(field: str) -> str:
    return _FIELD_LABELS_ZH.get(field, field)


def _family_label(family: DesignFieldFamily | str) -> str:
    if isinstance(family, DesignFieldFamily):
        return _FAMILY_LABELS_ZH.get(family, "设计事实")
    try:
        return _FAMILY_LABELS_ZH.get(DesignFieldFamily(family), "设计事实")
    except ValueError:
        return "设计事实"


def _assert_design_gate(data: ReportCPortalData) -> None:
    result = evaluate_design_gate(
        data.observations,
        core_trial_ids=data.trial_ids,
    )
    if result.decision is DesignGateDecision.PASSED:
        return
    notes = "；".join(failure.user_note_zh for failure in result.failures if failure.user_note_zh)
    detail = notes or "关键设计证据不足"
    raise ReportCPortalError(f"关键设计证据阻断：{detail}")


def _reset_site_root(site_root: Path) -> None:
    if site_root.exists() and not site_root.is_dir():
        raise ReportCPortalError(f"站点目标不是目录：{site_root}")
    if site_root.exists():
        for child in site_root.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    site_root.mkdir(parents=True, exist_ok=True)


def _copy_assets(site_root: Path) -> None:
    assets = site_root / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(resolve_logo_src(), assets / "logo.svg")
    for name in (
        "portal.css",
        "portal.js",
        "evidence-drawer.css",
        "evidence-drawer.js",
    ):
        shutil.copy2(resolve_portal_asset(name), assets / name)
    shutil.copy2(_ASSET_DIR / "report-c.css", assets / "report-c.css")
    shutil.copy2(_ASSET_DIR / "report-c.js", assets / "report-c.js")
    shutil.copy2(resolve_echarts_bundle(), assets / "echarts.min.js")


def _nav_groups(
    catalog: ReportCatalog,
    *,
    prefix: str,
    current: str,
) -> tuple[dict[str, Any], ...]:
    groups: list[dict[str, Any]] = []
    by_group: dict[str, dict[str, Any]] = {}
    for page in catalog.pages:
        group = by_group.get(page.navigation_group_zh)
        if group is None:
            group = {"label": page.navigation_group_zh, "pages": []}
            by_group[page.navigation_group_zh] = group
            groups.append(group)
        group["pages"].append(
            {
                "id": page.id,
                "title": page.title_zh,
                "href": f"{prefix}{page.id}.html",
                "active": page.id == current,
            }
        )
    return tuple(groups)


def _product_name(data: ReportCPortalData, product_id: str) -> str:
    native_name = {
        "lebrikizumab": "来布利珠单抗（Lebrikizumab）",
        "tapinarof": "他匹那罗夫（Tapinarof）",
        "difamilast": "迪法米司特（Difamilast）",
        "rocatinlimab": "罗卡替单抗（Rocatinlimab）",
        "amlitelimab": "阿姆特利单抗（Amlitelimab）",
    }.get(product_id)
    if native_name:
        return native_name
    for product in data.products:
        if product.id == product_id:
            return product.name
    return "未列示产品"


def _trial_name(data: ReportCPortalData, trial_id: str) -> str:
    for trial in data.trials:
        if trial.id == trial_id:
            if len(re.findall(r"[A-Za-z]{3,}", trial.name)) >= 5:
                product = _product_name(data, trial.product_id).split("（", 1)[0]
                return f"{product} {trial.phase}临床研究"
            return trial.name
    return "未列示试验"


_COUNTRY_NAMES_ZH = {
    "Argentina": "阿根廷",
    "Australia": "澳大利亚",
    "Austria": "奥地利",
    "Belgium": "比利时",
    "Bosnia and Herzegovina": "波斯尼亚和黑塞哥维那",
    "Brazil": "巴西",
    "Bulgaria": "保加利亚",
    "Canada": "加拿大",
    "China": "中国",
    "Czechia": "捷克",
    "Denmark": "丹麦",
    "Estonia": "爱沙尼亚",
    "France": "法国",
    "Germany": "德国",
    "Hungary": "匈牙利",
    "Japan": "日本",
    "Mexico": "墨西哥",
    "Spain": "西班牙",
    "United States": "美国",
}


def _region_zh(value: str) -> str:
    parts = (part.strip() for part in value.split("、"))
    return "、".join(_COUNTRY_NAMES_ZH.get(part, part) for part in parts)


def _trial_display(data: ReportCPortalData, trial_id: str) -> str:
    for trial in data.trials:
        if trial.id == trial_id:
            return trial.display_id
    return trial_id


def _product_target(data: ReportCPortalData, product_id: str) -> str:
    for product in data.products:
        if product.id == product_id:
            return product.target
    return "靶点未列示"


def _group_label_zh(group_id: str | None) -> str:
    value = _text(group_id)
    if value.endswith("-experimental"):
        return "试验组"
    if value.endswith("-control"):
        return "对照组"
    if not value or value.endswith("-all"):
        return "未按组别拆分"
    return "已定义组别"


def _cohort_label_zh(cohort_id: str | None) -> str:
    value = _text(cohort_id)
    if not value or value.endswith("-all"):
        return "总体入组人群"
    return "已定义分析队列"


def _observation_cohort_zh(observation: DesignObservation) -> str:
    """队列名优先还原登记标签（观察原文恰为 Cohort N 时 → 第N组）。

    仅在原文整体就是队列标签时替换，避免句中偶含 cohort 字样被误判。
    """
    m = re.fullmatch(r"[Cc]ohort\s+(\d+)", " ".join(_text(observation.source_text).split()))
    if m:
        return f"第{m.group(1)}组"
    return _cohort_label_zh(observation.cohort_id)


def _page_observations(
    data: ReportCPortalData,
    page_id: str,
    *,
    trial_id: str | None = None,
) -> tuple[DesignObservation, ...]:
    selected = data.observations
    if trial_id is not None:
        selected = tuple(item for item in selected if item.trial_id == trial_id)
    fields = _PAGE_FIELDS.get(page_id)
    if fields is None:
        return selected
    return tuple(item for item in selected if item.field in fields)


def _numeric_for(observation: DesignObservation) -> float | None:
    if observation.field == "planned_or_actual_sample_size":
        raw = observation.threshold_value or observation.source_text
        try:
            return float(str(raw).replace(",", "").strip())
        except (TypeError, ValueError):
            return None
    return None


def _operator_zh(value: str | None) -> str:
    return {
        ">=": "≥",
        "=>": "≥",
        "<=": "≤",
        "=<": "≤",
    }.get(_text(value), _text(value))


_DOSE_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:mg|milligrams?)\s*(?:/\s*(?:kg|kilogram)\b|/\s*m2|m²)?",
    re.I,
)


def _segment_doses(segment: str) -> list[str]:
    """剂量抽取：保留 /kg 体重口径（独立复核 C r19：0.57mg/kg 不得丢失分母）。"""
    doses: list[str] = []
    for match in _DOSE_PATTERN.findall(segment):
        dose = re.sub(r"\s*milligrams?", " mg", match, flags=re.I)
        dose = re.sub(r"\s+", " ", dose).strip()
        if dose not in doses:
            doses.append(dose)
    return doses


def _segment_frequency(segment: str) -> str:
    if re.search(r"\bq2w\b|every two weeks|every 2 weeks", segment, re.I):
        return "每2周1次"
    if re.search(r"once a week|once per week", segment, re.I):
        return "每周1次"
    if re.search(r"\bq4w\b|every four weeks|every 4 weeks", segment, re.I):
        return "每4周1次"
    if re.search(r"\bqw\b|once weekly|every week", segment, re.I):
        return "每周1次"
    if re.search(r"\bbid\b|twice daily", segment, re.I):
        return "每日2次"
    if re.search(r"\btid\b|three times (?:a )?day", segment, re.I):
        return "每日3次"
    if re.search(r"once a day|\bqd\b|daily", segment, re.I):
        return "每日1次"
    return ""


def _compact_regimen_zh(data: ReportCPortalData, observation: DesignObservation) -> str:
    """给药方案压缩：负荷期/维持期分开标注（独立复核 C r19）。"""
    source = _text(observation.source_text)
    product = _product_name(data, observation.product_id).split("（", 1)[0]
    timepoint = _text(observation.assessment_timepoint)

    # 按给药阶段切分：负荷/初始 vs 之后/维持
    segments = [
        s for s in re.split(r"\bthen\b|\bfollowed by\b|;|\.\s+", source, flags=re.I)
        if s.strip()
    ]
    load_seg = next((s for s in segments if re.search(r"loading|initially|first", s, re.I)), None)
    dose_segments = [s for s in segments if _segment_doses(s)]
    if load_seg is None and len(dose_segments) >= 2:
        # 无显式 loading 关键词但存在先后两个剂量段
        # （"receive 600 mg once a week …, and then 900 mg every 2 weeks"）
        load_seg = dose_segments[0]
        later_segs = dose_segments[1:]
    else:
        later_segs = [s for s in segments if s is not load_seg and _segment_doses(s)]

    parts = [product]
    if load_seg and later_segs:
        load_doses = _segment_doses(load_seg)
        load_freq = _segment_frequency(load_seg) or _segment_frequency(source)
        parts.append("负荷期" + ("、".join(load_doses) if load_doses else "剂量见登记原文")
                     + ((f"（{load_freq}）") if load_freq else ""))
        maint = later_segs[0]
        maint_doses = _segment_doses(maint)
        maint_freq = _segment_frequency(maint) or _segment_frequency(source)
        parts.append("维持期" + ("、".join(maint_doses) if maint_doses else "剂量见登记原文")
                     + ((f"（{maint_freq}）") if maint_freq else ""))
    elif load_seg:
        load_doses = _segment_doses(load_seg) or _segment_doses(source)
        parts.append("负荷剂量" + ("、".join(load_doses) if load_doses else "见登记原文"))
        if re.search(r"titrat|adjust", source, re.I):
            parts.append("维持期按临床反应滴定")
    else:
        doses = _segment_doses(source)
        frequency = _segment_frequency(source)
        if doses:
            parts.append("剂量" + "、".join(doses))
        if frequency:
            parts.append(frequency)
    timepoint = _text(observation.assessment_timepoint)
    if timepoint:
        parts.append(timepoint)
    body = "；".join(dict.fromkeys(p for p in parts if p))
    # 独立复核 C r20（veto 第3项）：无剂量句时提取给药途径，
    # 不得只剩产品名与"试验组干预"列重复
    if not _segment_doses(source):
        route = ""
        if re.search(r"IV infusion|intravenous", source, re.I):
            route = "静脉输注"
        elif re.search(r"subcutaneous", source, re.I):
            route = "皮下注射"
        elif re.search(r"oral", source, re.I):
            route = "口服"
        elif re.search(r"topical", source, re.I):
            route = "外用"
        if route:
            body = (body + "；" + route) if body else route
    return body


def _compact_arm_zh(data: ReportCPortalData, observation: DesignObservation) -> str:
    """把登记平台的长句干预描述压缩为医学经理可扫读的中文方案。"""
    source = _text(observation.source_text)
    folded = source.casefold()
    product = _product_name(data, observation.product_id).split("（", 1)[0]
    product_map = {
        "dupilumab": "度普利尤单抗",
        "nemolizumab": "奈莫利珠单抗",
        "lebrikizumab": "来布利珠单抗",
        "rocatinlimab": "罗卡替单抗",
        "difamilast": "迪法米司特",
        "tapinarof": "他匹那罗夫",
        "amlitelimab": "阿姆特利单抗",
    }
    matched_product = next((label for key, label in product_map.items() if key in folded), "")
    # 独立复核 C r21（issue-2）：组合限定（+ C5 Inhibitor 等）是登记事实，
    # 折叠为裸产品名会丢失关键干预语义
    combo_suffix = ""
    combo_match = re.search(r"\+\s*(C5 inhibitor|C3 inhibitor|background therapy)", folded)
    if combo_match:
        combo_suffix = (
            f"（+{combo_match.group(1)}抑制剂）"
            if "inhibitor" in combo_match.group(1) else "（+背景治疗）"
        )
    if "escape" in folded or "rescue" in folded:
        product = "补救治疗"
    elif "vehicle" in folded:
        product = "赋形剂对照"
    elif "placebo" in folded:
        product = f"{matched_product}匹配安慰剂" if matched_product else "安慰剂"
    else:
        product = (matched_product or product) + combo_suffix

    doses: list[str] = []
    for match in re.findall(r"\b\d+(?:\.\d+)?\s*(?:mg|milligrams?)\b", source, re.I):
        dose = re.sub(r"\s*milligrams?", " mg", match, flags=re.I)
        dose = re.sub(r"\s+", " ", dose).strip()
        if dose not in doses:
            doses.append(dose)
    frequency = ""
    if re.search(r"\bq2w\b|every two weeks|every 2 weeks", source, re.I):
        frequency = "每2周1次"
    elif re.search(r"\bq4w\b|every four weeks|every 4 weeks", source, re.I):
        frequency = "每4周1次"
    elif re.search(r"\bq?w\b|once weekly|every week", source, re.I):
        frequency = "每周1次"
    elif re.search(r"\bbid\b|twice daily", source, re.I):
        frequency = "每日2次"
    route = ""
    if "subcutaneous" in folded:
        route = "皮下注射"
    elif "topical" in folded or "cream" in folded or "ointment" in folded:
        route = "外用"
    week_range = ""
    week_match = re.search(r"weeks?\s+(\d+)\s*(?:through|to|-)\s*(\d+)", source, re.I)
    if week_match:
        week_range = f"第{week_match.group(1)}–{week_match.group(2)}周"
    elif observation.assessment_timepoint:
        week_range = _text(observation.assessment_timepoint)

    parts = [product]
    if doses:
        parts.append("剂量" + "、".join(doses))
    if route:
        parts.append(route)
    if frequency:
        parts.append(frequency)
    if week_range:
        parts.append(week_range)
    return "；".join(part for part in parts if part) or "方案详见登记信息"


_REGISTRY_ENDPOINT_TERM_ZH = {
    # 顺序关键：长词/特定词先于其子串（clone→hemoglobin、avoidance→transfusion）
    "pnh clone size": "PNH 克隆大小",
    "clone size": "克隆大小",
    "pnh clone": "PNH 克隆",
    "transfusion avoidance": "输血规避",
    "breakthrough hemolysis": "突破性溶血发生比例",
    "haptoglobin": "触珠蛋白",
    "facit": "FACIT 量表",
    "quality of life questionnaire": "生活质量问卷",
    "free hemoglobin": "游离血红蛋白",
    "free hgb": "游离血红蛋白",
    "hemoglobin": "血红蛋白",
    "hgb": "血红蛋白",
    "ldh": "LDH",
    "lactate dehydrogenase": "LDH",
    "transfusion": "输血",
    "facit-fatigue": "FACIT 疲乏评分",
    "chc": "慢性溶血标志物",
}


def _registry_endpoint_term_zh(text: str) -> str | None:
    """登记终点指标术语的确定性中文映射；未登记术语返回原文。"""
    folded = text.casefold()
    for needle, label in _REGISTRY_ENDPOINT_TERM_ZH.items():
        if needle in folded:
            return label
    return None


def _registry_timeframe_zh(text: str) -> str | None:
    """登记评估时间窗的确定性中文短语；未匹配返回 None（保留原文）。"""
    value = " ".join(str(text or "").split())
    if not value:
        return None
    m = re.fullmatch(r"[Bb]aseline(?:,| to)? [Ww]eek (\d+)", value)
    if m:
        return f"基线至第{m.group(1)}周"
    m = re.fullmatch(r"[Bb]aseline(?:,| to)? [Dd]ay (\d+)", value)
    if m:
        return f"基线至第{m.group(1)}天"
    m = re.fullmatch(r"[Dd]ay (\d+) [Aa][Nn][Dd] [Dd]ay (\d+)", value)
    if m:
        return f"第{m.group(1)}天与第{m.group(2)}天"
    m = re.fullmatch(r"[Bb]aseline, [Dd]ay (\d+)[^(]*\(.*\) [Aa][Nn][Dd] [Dd]ay (\d+).*", value)
    if m:
        return f"第{m.group(1)}天与第{m.group(2)}天（多队列）"
    m = re.fullmatch(r"[Dd]ays (\d+), (\d+), [Aa][Nn][Dd] [Dd]ay (\d+)", value)
    if m:
        return f"第{m.group(1)}、{m.group(2)}与{m.group(3)}天"
    return None


def _registry_endpoint_zh(text: str) -> str | None:
    """把 CT.gov 常见主要终点措辞确定性转写为中文；未匹配返回 None。

    只改写演示措辞，不改写事实：来源原文保留在观察的 source_text。
    """
    value = " ".join(str(text or "").split())
    if not value:
        return None
    term = _registry_endpoint_term_zh(value)
    if term is None:
        return None
    m = re.fullmatch(
        r"[Pp]ercentage [Cc]hange [Ff]rom [Bb]aseline in (.+?) at (.+)", value
    ) or re.fullmatch(
        r"[Pp]ercent [Cc]hange [Ii]n (.+?) [Ff]rom [Bb]aseline [Tt]o (.+)", value
    )
    if m:
        window = (
            _registry_timeframe_zh(m.group(2)) or _native_timepoint_zh(m.group(2))
            or m.group(2)
        )
        return f"{term}较基线百分比变化（{window}）"
    m = re.fullmatch(
        r"[Cc]hange [Ff]rom [Bb]aseline in (.+?) at (.+)", value
    )
    if m:
        window = (
            _registry_timeframe_zh(m.group(2)) or _native_timepoint_zh(m.group(2))
            or m.group(2)
        )
        return f"{term}较基线变化（{window}）"
    m = re.fullmatch(
        r"[Mm]easurement of [Rr]atio of (.+?) to the [Uu]pper [Ll]imit of [Nn]ormal(.*)",
        value,
    )
    if m:
        window = (
            _registry_timeframe_zh(m.group(2).strip(" (),"))
            if m.group(2).strip(" (),") else None
        )
        return f"{term}/正常上限比值" + (f"（{window}）" if window else "")
    # 独立复核 C r32/r37：术语命中但句式未匹配时，至少返回术语本身
    # （如"突破性溶血发生比例"），不再返回 None 导致英文直出
    return term


def _value_text(data: ReportCPortalData, observation: DesignObservation) -> str:
    def _tp_disp(tp: str | None) -> str:
        if not tp:
            return ""
        return _registry_timeframe_zh(tp) or _native_timepoint_zh(tp) or tp

    numeric = _numeric_for(observation)
    if numeric is not None:
        if numeric.is_integer():
            return str(int(numeric))
        return str(numeric)
    source_text = _text(observation.display_text or observation.source_text)
    text = _registry_display_text(source_text)
    operator = _operator_zh(observation.operator)
    threshold = _text(observation.threshold_value)
    unit = _text(observation.threshold_unit)
    timepoint = _text(observation.assessment_timepoint)
    scale = _text(observation.scale)

    if observation.field == "trial_identity":
        return _trial_name(data, observation.trial_id)
    if observation.field == "target_population":
        # 独立复核 C r20（veto 第8项）：结构化最低年龄优先，
        # 同列口径统一为可比事实，不再自指"已记录（原文见来源）"
        structured_age = _text(observation.threshold_value)
        if structured_age:
            unit = _text(observation.threshold_unit, "岁")
            return f"登记最低年龄：{structured_age}{unit}"
        return _target_population_text(text)
    if observation.field in {"inclusion_criterion", "exclusion_criterion"}:
        if not source_text:
            raise ReportCPortalError(f"{observation.trial_id} 的入排标准原文为空，不能生成报告")
        if _is_multi_criterion_source(source_text):
            value = _eligibility_source_text(observation.field, source_text)
            return value + (f"（{timepoint}）" if timepoint else "")
        if threshold:
            label = scale or ("体重" if "weight" in text.casefold() else "指标")
            return f"{label} {operator}{threshold}{unit}" + (
                f"（{timepoint}）" if timepoint else ""
            )
        phrase_map = {
            "chronic ad that had been present for at least 3 years": "特应性皮炎病程至少3年",
            "participation in a prior dupilumab clinical trial": "既往参加过度普利尤单抗临床试验",
            "prior treatment with dupilumab or tralokinumab": (
                "既往接受过度普利尤单抗或曲罗芦单抗治疗"
            ),
            "treatment with tcs within 1 week before the baseline visit": (
                "基线前1周内使用过外用糖皮质激素"
            ),
        }
        folded = text.casefold().rstrip(".;")
        value = next((label for phrase, label in phrase_map.items() if phrase in folded), "")
        if not value:
            value = _eligibility_source_text(observation.field, source_text)
        return value + (f"（{timepoint}）" if timepoint else "")
    if observation.field in {"experimental_arm", "control_arm"}:
        return _compact_arm_zh(data, observation)
    if observation.field == "dosing_regimen":
        return _compact_regimen_zh(data, observation)
    if observation.field == "primary_endpoint_definition":
        folded = text.casefold()
        is_iga = scale.upper() == "IGA" or "investigator's global assessment" in folded
        if is_iga and threshold:
            return f"IGA达到0或1分，且较基线降低{operator}{threshold}{unit}" + (
                f"（{_tp_disp(timepoint)}）" if _tp_disp(timepoint) else ""
            )
        if (scale.upper() == "EASI" or "easi" in text.casefold()) and threshold:
            endpoint_unit = unit.replace("改善", "")
            return f"EASI较基线改善{operator}{threshold}{endpoint_unit}" + (
                f"（{_tp_disp(timepoint)}）" if _tp_disp(timepoint) else ""
            )
        if is_iga or " iga " in f" {folded} ":
            return "IGA 0/1应答率" + ((f"（{_tp_disp(timepoint)}）") if _tp_disp(timepoint) else "")
        if "easi" in text.casefold():
            return "EASI应答" + ((f"（{_tp_disp(timepoint)}）") if _tp_disp(timepoint) else "")
        registry_zh = _registry_endpoint_zh(text)
        if registry_zh:
            return registry_zh
    if observation.field == "primary_endpoint_timepoint":
        translated = _registry_timeframe_zh(timepoint) if timepoint else None
        return translated or timepoint or "主要终点评估时间未公开"
    # 独立复核 C r20（veto 第1项）：次要终点定义/时间点走同一确定性转写，
    # 不得直出登记英文原句
    if observation.field == "primary_endpoint_definition":
        ep_zh = _registry_endpoint_zh(source_text)
        if ep_zh:
            disp = _tp_disp(timepoint)
            return ep_zh + (f"（{disp}）" if disp else "")
        label = _native_endpoint_zh(source_text)
        if len(re.findall(r"[A-Za-z]{3,}", label)) >= 2:
            return "主要终点（原文见证据抽屉）"
        _d = _tp_disp(timepoint)
        return label + (f"（{_d}）" if _d else "")
    if observation.field == "secondary_endpoint_definition":
        ep_zh = _registry_endpoint_zh(source_text)
        if ep_zh:
            disp = _tp_disp(timepoint)
            return ep_zh + (f"（{disp}）" if disp else "")
        label = _native_endpoint_zh(source_text)
        if len(re.findall(r"[A-Za-z]{3,}", label)) >= 2:
            # 独立复核 C r21（issue-1）：不同次要终点的兜底标签必须可区分，
            # 以观察序号命名，原文保留在证据抽屉"简短原文"
            m_sec = re.search(r"sec(\d+)$", observation.observation_id)
            ordinal = m_sec.group(1) if m_sec else "0"
            return f"次要终点{ordinal}（原文见证据抽屉）"
        _d = _tp_disp(timepoint)
        return label + (f"（{_d}）" if _d else "")
    if observation.field == "secondary_endpoint_timepoint":
        translated = _registry_timeframe_zh(timepoint) if timepoint else None
        return translated or _native_timepoint_zh(timepoint or "") or timepoint or "未公开"
    if observation.field == "visit_schedule":
        return f"主要评估与随访：{timepoint}" if timepoint else "访视安排未公开"
    if (
        observation.field == "analysis_population"
        and "does not separately report" in text.casefold()
    ):
        return "未公开"
    if observation.field == "arm_randomization_blinding":
        design_labels = {
            "allocation=RANDOMIZED": "随机分配",
            "allocation=NON_RANDOMIZED": "非随机分配",
            "interventionModel=PARALLEL": "平行分组",
            "interventionModel=CROSSOVER": "交叉设计",
            "interventionModel=SEQUENTIAL": "序贯设计",
            "interventionModel=SINGLE_GROUP": "单组设计",
            "masking=NONE": "开放标签",
            "masking=SINGLE": "单盲",
            "masking=DOUBLE": "双盲",
            "masking=TRIPLE": "三盲",
            "masking=QUADRUPLE": "四盲",
        }
        design_parts = [
            design_labels.get(part.strip(), part.strip())
            for part in text.split(";")
            if part.strip()
        ]
        text = "；".join(design_parts)
    if text:
        return text
    parts = [
        _text(observation.operator),
        _text(observation.threshold_value),
        _text(observation.threshold_unit),
        _text(observation.assessment_timepoint),
        _text(observation.scale),
    ]
    joined = " ".join(part for part in parts if part)
    return joined or _state_label(observation.disclosure_state)


_NO_TIMEPOINT_FIELDS = frozenset(
    {
        "trial_identity",
        "target_population",
        "inclusion_criterion",
        "exclusion_criterion",
        "arm_randomization_blinding",
        "experimental_arm",
        "control_arm",
        "dosing_regimen",
        "planned_or_actual_sample_size",
        "analysis_population",
        "analysis_sets",
        "statistical_comparisons",
        "multiplicity_adjustment",
        "missing_data_handling",
        "design_kind",
        "study_design_type",
    }
)


def _chart_row(
    data: ReportCPortalData,
    observation: DesignObservation,
    *,
    chart_type: str,
) -> dict[str, Any]:
    numeric = _numeric_for(observation)
    reported = observation.disclosure_state in {
        FactDisclosureState.REPORTED_VALUE,
        FactDisclosureState.REPORTED_ZERO,
    }
    value_text = _value_text(data, observation)
    row: dict[str, Any] = {
        "row_id": observation.row_id,
        "product_id": observation.product_id,
        "trial_id": observation.trial_id,
        "group_id": observation.group_id,
        "cohort_id": observation.cohort_id,
        "group_zh": _group_label_zh(observation.group_id),
        "cohort_zh": _observation_cohort_zh(observation),
        "product_zh": _product_name(data, observation.product_id),
        "trial_zh": _trial_name(data, observation.trial_id),
        "trial_display_id": _trial_display(data, observation.trial_id),
        "target": _product_target(data, observation.product_id),
        "display_label_zh": _field_label(observation.field),
        "element": observation.field,
        "element_zh": _field_label(observation.field),
        "field_family_zh": _family_label(observation.field_family),
        "arm": (
            _observation_cohort_zh(observation)
            if re.search(r"\bcohort\s+\d+", _text(observation.source_text), re.I)
            else "组别未细分"
        ),
        "group": (
            _observation_cohort_zh(observation)
            if re.search(r"\bcohort\s+\d+", _text(observation.source_text), re.I)
            else "组别未细分"
        ),
        "category": "设计事实",
        # 独立复核 C r29（issue-3）：结构上无时间点的字段缺省"不适用"，
        # 与"已报告值"披露状态不再矛盾；有时间点却缺失的才标"未公开"
        "time": (
            _registry_timeframe_zh(_text(observation.assessment_timepoint))
            or _native_timepoint_zh(_text(observation.assessment_timepoint))
            or _text(observation.assessment_timepoint)
            or (
                "不适用"
                if observation.field in _NO_TIMEPOINT_FIELDS
                else "未公开"
            )
        ),
        "unit": _text(observation.threshold_unit),
        "disclosure_state": observation.disclosure_state.value,
        "disclosure_state_zh": _state_label(observation.disclosure_state),
        "status": value_text if reported else _state_label(observation.disclosure_state),
        "value": value_text if reported else None,
        "renderable": reported,
        "_chart_type": chart_type,
        "source_text": _text(observation.source_text),
        "source_field_name": _text(observation.source_field_name, "未列示"),
        "source_location_zh": f"ClinicalTrials.gov · {_field_label(observation.field)}",
        "review_state": observation.review_state.value,
        "scale": (
            lambda s: s + "（登记原文，未译）"
            if (
                s and len(re.findall(r"[A-Za-z]{3,}", s)) >= 2
                and not re.search(r"[\u4e00-\u9fff]", s)
            )
            else s
        )(_text(observation.scale)),
    }
    if numeric is not None and reported:
        projection = project_numeric(
            value=numeric, unit=_text(observation.threshold_unit),
            kind=(NumericMeasureKind.SAMPLE_SIZE
                  if observation.field == "planned_or_actual_sample_size"
                  else NumericMeasureKind.PARTICIPANT_COUNT),
            window=_text(observation.assessment_timepoint), estimand=observation.field,
            size_value=numeric if chart_type == "bubble" else None,
            size_basis="登记计划或实际样本量" if chart_type == "bubble" else None,
        )
        row["numeric_projection"] = projection.as_dict()
        row["numeric_value"] = projection.plot_value
        row["unit"] = projection.plot_unit
        row["value"] = int(numeric) if numeric.is_integer() else numeric
        row["renderable"] = True
        if chart_type == "bubble":
            row["x_value"] = projection.plot_value
            row["y_value"] = 1
            row["size"] = max(numeric, 1.0)
            row["size_basis"] = projection.size_basis
    return row


def _chart_groups(
    data: ReportCPortalData,
    observations: Sequence[DesignObservation],
    *,
    page_id: str,
    title: str,
) -> tuple[dict[str, Any], ...]:
    if not observations:
        return ()
    chart_type = _PAGE_CHART_TYPE.get(page_id, "status_matrix")
    if page_id in {"inclusion-criteria", "exclusion-criteria"}:
        label = "公开入选标准条目" if page_id == "inclusion-criteria" else "公开排除标准条目"
        rows = []
        for observation in observations:
            row = _chart_row(data, observation, chart_type="status_matrix")
            # 人工拆分的登记原文段数不是临床事实的数值，也不能代替原条款。
            row.pop("numeric_value", None)
            row.pop("numeric_projection", None)
            row.update(
                {
                    "display_label_zh": label,
                    "element_zh": label,
                    "_chart_type": "status_matrix",
                }
            )
            rows.append(row)
        return (
            {
                "title_zh": f"各试验{label}",
                "rows": rows,
                "_chart_type": "status_matrix",
            },
        )
    if page_id == "sample-analysis-statistics":
        sample_rows = [
            item for item in observations if item.field == "planned_or_actual_sample_size"
        ]
        analysis_rows = [item for item in observations if item.field == "analysis_population"]
        groups: list[dict[str, Any]] = []
        if sample_rows:
            groups.append(
                {
                    "title_zh": "计划或实际样本量",
                    "rows": [_chart_row(data, item, chart_type="bubble") for item in sample_rows],
                    "_chart_type": "bubble",
                    "size_label_zh": "气泡大小表示样本量",
                }
            )
        if analysis_rows:
            groups.append(
                {
                    "title_zh": "分析人群",
                    "rows": [
                        _chart_row(data, item, chart_type="status_matrix") for item in analysis_rows
                    ],
                    "_chart_type": "status_matrix",
                }
            )
        return tuple(groups)
    return (
        {
            "title_zh": title,
            "rows": [_chart_row(data, item, chart_type=chart_type) for item in observations],
            "_chart_type": chart_type,
        },
    )


def _evidence_field(value: Any, state: str | None = None) -> EvidenceField:
    if value is not None and _text(value):
        return EvidenceField(value=_text(value))
    state_map = {
        "not_applicable": EvidenceFieldState.NOT_APPLICABLE,
        "not_reported": EvidenceFieldState.SOURCE_NOT_LISTED,
        "not_publicly_disclosed": EvidenceFieldState.NOT_YET_DISCLOSED,
        "below_reporting_threshold": EvidenceFieldState.NOT_YET_DISCLOSED,
        "unresolved_due_to_route": EvidenceFieldState.TECHNICALLY_UNAVAILABLE,
        "conflicting": EvidenceFieldState.TECHNICALLY_UNAVAILABLE,
        "user_cleared": EvidenceFieldState.USER_CLEARED,
    }
    return EvidenceField(state=state_map.get(state or "", EvidenceFieldState.SOURCE_NOT_LISTED))


def _safe_locator(observation: DesignObservation) -> EvidenceLocator:
    locator = observation.source_locator
    document_role_map = {
        "clinical-trial-registry": "registry",
    }
    heading_map = {
        "Identification": "研究基本信息",
        "Eligibility Criteria": "入选与排除标准",
        "Inclusion Criteria": "入选标准",
        "Exclusion Criteria": "排除标准",
        "Study Design": "研究设计",
        "Key Inclusion Criteria": "主要入选标准",
        "Key Exclusion Criteria": "主要排除标准",
        "Arms and Interventions": "分组与干预",
        "Outcome Measures": "结局指标",
    }
    url = locator.url
    nct_match = re.search(r"/api/v2/studies/(NCT\d+)", url or "", re.I)
    if nct_match:
        url = f"https://clinicaltrials.gov/study/{nct_match.group(1).upper()}"
    # 独立复核 C r29（issue-5）：定位链接必须能回到具体登记记录；
    # 观察行自带试验标识（NCTxxxx）时按行构造深链，不再落回 CT.gov 首页
    if re.fullmatch(r"NCT\d{8}", (observation.trial_id or "").upper() or ""):
        url = f"https://clinicaltrials.gov/study/{observation.trial_id.upper()}"
    visible = {
        "document_role": document_role_map.get(
            locator.document_role, locator.document_role
        ),
        "heading": heading_map.get(locator.heading or "", locator.heading or "登记结果"),
        "page": locator.page,
        "table": locator.table,
        "column": locator.column,
        "paragraph": locator.paragraph,
        "url": url,
    }
    return EvidenceLocator.model_validate(visible)


def _evidence_view(
    data: ReportCPortalData,
    observation: DesignObservation,
    *,
    page_id: str,
) -> EvidenceView:
    state = observation.disclosure_state.value
    snapshot = _text(
        data.report_snapshot_id,
        f"c-{data.report_version}",
    )
    label = _field_label(observation.field)
    report_row = ReportRow.model_construct(
        row_id=observation.row_id,
        fact_id=observation.source_row_id,
        claim_id=None,
        product_id=observation.product_id,
        trial_id=observation.trial_id,
        group_id=observation.group_id,
        endpoint_id=None,
        event_id=None,
        timepoint_id=None,
        display_label_zh=label,
        page_responsibility_id=page_id,
        report_snapshot_id=snapshot,
        disclosure_state=observation.disclosure_state,
    )
    value_text = _value_text(data, observation)
    return EvidenceView.model_construct(
        None,
        report_kind=ReportKind.C,
        observation_kind=EvidenceObservationKind.GENERAL,
        row=report_row,
        product_zh=_product_name(data, observation.product_id),
        trial_zh=_trial_name(data, observation.trial_id),
        group_zh=_evidence_field(_group_label_zh(observation.group_id), state),
        element_zh=label,
        scale=_evidence_field(observation.scale, state),
        timepoint=_evidence_field(observation.assessment_timepoint, state),
        value=_evidence_field(value_text, state),
        threshold=_evidence_field(observation.threshold_value, state),
        unit=_evidence_field(observation.threshold_unit, state),
        numerator=_evidence_field(None, "not_applicable"),
        denominator=_evidence_field(None, "not_applicable"),
        source_version_id=observation.source_version_id,
        source_version_label_zh="ClinicalTrials.gov",
        locator=_safe_locator(observation),
        explanation=_evidence_field(
            "本条信息摘自临床试验登记页，"
            f"适用于{_observation_cohort_zh(observation)}；"
            "已核对来源版本和原文位置，"
            f"当前公开情况为{_state_label(observation.disclosure_state)}。"
        ),
        original_text=_text(observation.source_text) or None,
        original_text_status=(
            OriginalTextStatus.PROVIDED
            if _text(observation.source_text)
            else OriginalTextStatus.NOT_PROVIDED
        ),
        user_edit=data.user_edits.get(observation.row_id),
        conflicts=(),
        historical_versions=(),
        source_field_name=_evidence_field(_field_label(observation.field), state),
        source_field_definition=_evidence_field("临床试验登记页对应设计要素", state),
    )


def _filter_dimensions_for_rows(
    data: ReportCPortalData,
    observations: Sequence[DesignObservation],
) -> tuple[list[dict[str, str]], dict[str, dict[str, str]]]:
    filter_rows: list[dict[str, str]] = []
    dimensions: dict[str, dict[str, str]] = {}
    for observation in observations:
        row = {
            "id": observation.row_id,
            "product": observation.product_id,
            "target": _product_target(data, observation.product_id),
            "trial": observation.trial_id,
            "element": observation.field,
            "field_family_zh": _family_label(observation.field_family),
            "scale": _text(observation.scale, "未列示"),
            "timepoint": _text(observation.assessment_timepoint, "未列示"),
            "disclosure_state": observation.disclosure_state.value,
        }
        filter_rows.append(row)
        dimensions[observation.row_id] = {key: value for key, value in row.items() if key != "id"}
    return filter_rows, dimensions


def _filter_groups(
    data: ReportCPortalData,
    filter_rows: Sequence[Mapping[str, str]],
) -> tuple[dict[str, Any], ...]:
    groups: list[dict[str, Any]] = []
    for dimension, label in _FILTER_DIMENSION_LABELS.items():
        values: list[str] = []
        seen: set[str] = set()
        for row in filter_rows:
            value = _text(row.get(dimension))
            if value and value not in seen:
                seen.add(value)
                values.append(value)
        if not values:
            continue
        options: list[dict[str, str]] = []
        for value in values:
            if dimension == "product":
                option_label = _product_name(data, value)
            elif dimension == "trial":
                option_label = f"{_trial_display(data, value)} · {_trial_name(data, value)}"
            elif dimension == "element":
                option_label = _field_label(value)
            elif dimension == "disclosure_state":
                option_label = _state_label(value)
            elif dimension in {"time", "timepoint"}:
                # 独立视觉复核（v59 copy_zh）+ 独立复核 C r20/r26：
                # 时间点筛选标签与行单元格同源转写，不再直出登记英文原文
                option_label = (
                    _registry_timeframe_zh(value)
                    or _native_timepoint_zh(value)
                    or value
                )
            elif dimension == "scale":
                option_label = _native_endpoint_zh(value) or value
            else:
                option_label = value
            options.append({"value": value, "label": option_label})
        groups.append(
            {
                "dimension": dimension,
                "label": label,
                "options": tuple(options),
                "scope": "page" if dimension in {"product", "target", "trial"} else "module",
            }
        )
    return tuple(groups)


def _candidate_design_paths(
    data: ReportCPortalData,
) -> tuple[dict[str, Any], ...]:
    payload_paths = (data.design_paths or {})
    candidates = payload_paths.get("candidate_paths") or ()
    patterns = payload_paths.get("patterns") or ()
    if candidates or patterns:
        converted: list[dict[str, Any]] = []
        for item in candidates:
            entry = dict(item)
            entry["trial_labels"] = [
                f"{_trial_display(data, trial_id)}（{_trial_name(data, trial_id)}）"
                for trial_id in entry.get("trial_ids", ())
            ]
            converted.append(entry)
        for index, item in enumerate(patterns, start=1):
            converted.append({
                "path_id": _text(item.get("item_id"), f"pattern-{index}"),
                "family": _text(item.get("item_id"), f"pattern-{index}"),
                "summary_zh": _text(item.get("statement_zh"), ""),
                "assumptions_zh": "该模式的前提是各试验共同公开的登记设计安排。",
                "tradeoffs_zh": "与未覆盖该模式的路径相比，可比较性与证据成熟度以登记原文为准。",
                "trial_ids": list(item.get("trial_ids", ())),
                "observation_ids": list(item.get("observation_ids", ())),
                "trial_labels": [
                    f"{_trial_display(data, trial_id)}（{_trial_name(data, trial_id)}）"
                    for trial_id in item.get("trial_ids", ())
                ],
            })
        return tuple(converted)
    buckets: dict[str, dict[str, Any]] = {}
    for observation in data.observations:
        if observation.field != "primary_endpoint_definition":
            continue
        source = f"{observation.source_field_name} {observation.source_text}".casefold()
        if "easi" in source:
            family = "EASI"
            summary = "以 EASI 改善作为主要终点路径"
            assumptions = "登记披露了 EASI 相关主要终点定义与评估时间。"
            tradeoffs = "强调皮损面积与严重度综合改善，可能与仅看总体评估的路径不同。"
        elif "iga" in source:
            family = "IGA"
            summary = "以 IGA 达到清除或几乎清除作为主要终点路径"
            assumptions = "登记披露了 IGA 相关主要终点定义与评估时间。"
            tradeoffs = "强调总体评估阈值达标，可能与面积严重度综合评分路径不同。"
        else:
            continue
        path_id = f"path-{family.lower()}"
        bucket = buckets.get(path_id)
        if bucket is None:
            bucket = {
                "path_id": path_id,
                "family": family,
                "summary_zh": summary,
                "assumptions_zh": assumptions,
                "tradeoffs_zh": tradeoffs,
                "trial_ids": [],
                "observation_ids": [],
            }
            buckets[path_id] = bucket
        if observation.trial_id not in bucket["trial_ids"]:
            bucket["trial_ids"].append(observation.trial_id)
        if observation.observation_id not in bucket["observation_ids"]:
            bucket["observation_ids"].append(observation.observation_id)
    ordered = sorted(buckets.values(), key=lambda item: item["path_id"])
    for item in ordered:
        item["trial_labels"] = [
            f"{_trial_display(data, trial_id)}（{_trial_name(data, trial_id)}）"
            for trial_id in item["trial_ids"]
        ]
    return tuple(ordered)


def _table_columns(page_id: str) -> tuple[tuple[str, str], ...]:
    if page_id == "trial-detail":
        return (
            ("display_label_zh", "设计要素"),
            ("value", "内容"),
            ("time", "时间点"),
            ("scale", "量表"),
            ("group_zh", "组别"),
            ("cohort_zh", "队列"),
            ("source_location_zh", "来源位置"),
            ("disclosure_state_zh", "披露状态"),
        )
    if page_id == "sample-analysis-statistics":
        return (
            ("product_zh", "产品"),
            ("trial_display_id", "试验编号"),
            ("trial_zh", "试验"),
            ("display_label_zh", "设计要素"),
            ("value", "数值/内容"),
            ("unit", "单位"),
            ("disclosure_state_zh", "披露状态"),
        )
    return (
        ("trial_display_id", "试验编号"),
        ("display_label_zh", "设计要素"),
        ("value", "内容"),
        ("time", "时间点"),
        ("disclosure_state_zh", "披露状态"),
    )


def _table_rows(
    data: ReportCPortalData,
    observations: Sequence[DesignObservation],
    *,
    page_id: str,
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for observation in observations:
        chart = _chart_row(
            data,
            observation,
            chart_type=_PAGE_CHART_TYPE.get(page_id, "status_matrix"),
        )
        chart["source_version"] = observation.source_version_id
        if chart.get("value") is None:
            chart["value"] = _state_label(observation.disclosure_state)
        # 独立复核 C r42（issue-4）/C r46（issue-1）：值列残留英文
        # （含部分转写后中英混排，如 During 残片）一律按惯例标注
        _v = chart.get("value")
        if observation.review_state is FactReviewState.USER_MODIFIED:
            chart["value"] = f"{_v}（用户修订，未独立复核）"
        elif (
            isinstance(_v, str)
            and re.findall(r"[A-Za-z]{3,}", _v)
            and not _v.endswith("（登记原文，未译）")
        ):
            chart["value"] = _v + "（登记原文，未译）"
        if chart.get("scale") in {None, ""}:
            chart["scale"] = "不适用"
        if chart.get("group_id") in {None, ""}:
            chart["group_id"] = "未细分"
        if chart.get("cohort_id") in {None, ""}:
            chart["cohort_id"] = "未细分"
        if observation.field in {"inclusion_criterion", "exclusion_criterion"}:
            parts = _criterion_parts(observation.source_text)
            if len(parts) > 1:
                timepoint = _text(observation.assessment_timepoint)
                for index, part in enumerate(parts, start=1):
                    item = dict(chart)
                    item["table_item_id"] = f"{observation.row_id}-criterion-{index}"
                    item["value"] = _eligibility_source_text(observation.field, part) + (
                        f"（{timepoint}）" if timepoint else ""
                    )
                    rows.append(item)
                continue
        chart["table_item_id"] = observation.row_id
        rows.append(chart)
    # 独立复核 C r28/r29/r40（同名行消歧）：同试验+同设计要素+同时间点的
    # 重复可见标签追加登记定义序号，行级可归属（原文保留在证据抽屉）。
    # 独立复核 C r40（issue-2）：键不含数值——同名终点不同测定
    # （如 Hgb 较基线升高 vs 正常化）也必须获得序号区分
    seen_keys: dict[tuple[str, str, str], int] = {}
    for row in rows:
        key = (
            str(row.get("trial_id")),
            str(row.get("display_label_zh") or row.get("element_zh") or ""),
            str(row.get("time") or ""),
        )
        seen_keys[key] = seen_keys.get(key, 0) + 1
    dup_keys = {k for k, v in seen_keys.items() if v > 1}
    if dup_keys:
        counters: dict[tuple[str, str, str], int] = {}
        for row in rows:
            k = (
                str(row.get("trial_id")),
                str(row.get("display_label_zh") or row.get("element_zh") or ""),
                str(row.get("time") or ""),
            )
            if k in dup_keys:
                counters[k] = counters.get(k, 0) + 1
                row["table_item_id"] = f"{row.get('table_item_id')}-d{counters[k]}"
                row["value"] = f"{row['value']}（登记定义{counters[k]}）"
    return tuple(rows)


def _matrix_field_order(observations: Sequence[DesignObservation]) -> tuple[str, ...]:
    """按合同字段顺序返回当前页面实际提取到的全部设计字段。"""
    observed = {item.field for item in observations}
    declared = tuple(field for field in _FIELD_LABELS_ZH if field in observed)
    additional = tuple(sorted(observed.difference(_FIELD_LABELS_ZH)))
    return declared + additional


def _matrix_field_label(
    field: str,
    observations: Sequence[DesignObservation],
) -> str:
    if field in _FIELD_LABELS_ZH:
        return _field_label(field)
    source_name = next(
        (_text(item.source_field_name) for item in observations if item.field == field),
        "",
    )
    return source_name or "其他设计要素"


def _criterion_parts(source_text: str) -> tuple[str, ...]:
    """把同一登记字段里的多条入排原文拆成可单独阅读的条目。"""
    raw = str(source_text or "").strip()
    raw = re.sub(r"</(?:li|p|div)>", "\n", raw, flags=re.I)
    raw = _REGISTRY_TAG_PATTERN.sub(" ", raw)
    raw = unescape(raw)
    raw = re.sub(
        r"^(?:Inclusion Criteria|Key Inclusion Criteria|Key Exclusion Criteria)"
        r"\s*:\s*",
        "",
        raw,
        flags=re.I,
    )
    raw = re.sub(
        r"^Participants are excluded from the study if any of the following criteria apply"
        r"\s*:\s*",
        "",
        raw,
        flags=re.I,
    )
    raw = re.sub(r"(?:\r?\n\s*)+(?=(?:\d+\.|[*•])\s+)", "\n", raw)
    parts = []
    for part in re.split(r"(?:;|；|\r?\n)", raw):
        cleaned = _registry_display_text(part).strip(" ;；:•*")
        cleaned = re.sub(r"^\d+\.\s*", "", cleaned)
        if cleaned:
            parts.append(cleaned)
    return tuple(parts)


def _matrix_item_summaries(
    data: ReportCPortalData,
    observation: DesignObservation,
) -> tuple[str, ...]:
    """为矩阵首层生成逐条中文入排摘要；原文仍由抽屉完整展示。"""
    if observation.field not in {"inclusion_criterion", "exclusion_criterion"}:
        return (_value_text(data, observation),)
    parts = _criterion_parts(observation.source_text)
    if len(parts) <= 1:
        return (_value_text(data, observation),)
    timepoint = _text(observation.assessment_timepoint)
    summaries = []
    for part in parts:
        summary = _eligibility_source_text(observation.field, part)
        if timepoint:
            summary += f"（{timepoint}）"
        summaries.append(summary)
    return tuple(summaries)


def _matrix_trial_context(
    data: ReportCPortalData,
    observations: Sequence[DesignObservation],
) -> tuple[dict[str, Any], ...]:
    """研究列的稳定身份：产品、登记号、阶段、状态与地区均保留。"""
    trial_ids = {item.trial_id for item in observations}
    return tuple(
        {
            "id": trial.id,
            "display_id": trial.display_id,
            "name": _trial_name(data, trial.id),
            "product_id": trial.product_id,
            "product_zh": _product_name(data, trial.product_id),
            "phase": _text(trial.phase, "阶段未列示"),
            "status": _text(trial.status, "状态未列示"),
            "region": _region_zh(_text(trial.region, "地区未列示")),
            "role": _text(trial.role, "研究角色未列示"),
        }
        for trial in data.trials
        if trial.id in trial_ids
    )


def _design_matrix(
    data: ReportCPortalData,
    observations: Sequence[DesignObservation],
) -> tuple[
    tuple[dict[str, Any], ...],
    tuple[dict[str, Any], ...],
    tuple[dict[str, Any], ...],
]:
    trials = _matrix_trial_context(data, observations)
    grouped: dict[tuple[str, str], list[DesignObservation]] = {}
    for observation in observations:
        grouped.setdefault((observation.field, observation.trial_id), []).append(observation)

    rows: list[dict[str, Any]] = []
    for field in _matrix_field_order(observations):
        field_observations = tuple(item for item in observations if item.field == field)
        first = field_observations[0]
        cells: list[dict[str, Any]] = []
        for trial in trials:
            cell_observations = tuple(grouped.get((field, trial["id"]), ()))
            items = tuple(
                {
                    "row_id": item.row_id,
                    "summary": summary,
                    "source_text": _text(item.source_text),
                    "disclosure_state": item.disclosure_state.value,
                    "scale": _text(item.scale, "未列示"),
                    "timepoint": _text(item.assessment_timepoint, "未列示"),
                }
                for item in cell_observations
                for summary in _matrix_item_summaries(data, item)
            )
            cells.append(
                {
                    "trial_id": trial["id"],
                    "product_id": trial["product_id"],
                    "trial_label": f"{trial['display_id']} · {trial['name']}",
                    "row_ids": tuple(item["row_id"] for item in items),
                    "items": items,
                    "summary": "；".join(item["summary"] for item in items) or "未提取",
                    "empty": not items,
                    "scale_values": tuple(dict.fromkeys(item["scale"] for item in items)),
                    "timepoint_values": tuple(dict.fromkeys(item["timepoint"] for item in items)),
                }
            )
        rows.append(
            {
                "field": field,
                "label": _matrix_field_label(field, field_observations),
                "family_id": first.field_family.value,
                "family_label": _family_label(first.field_family),
                "cells": tuple(cells),
                "observation_count": len(field_observations),
            }
        )

    family_rows: dict[str, list[dict[str, Any]]] = {}
    family_order: list[str] = []
    for row in rows:
        family_id = row["family_id"]
        if family_id not in family_rows:
            family_rows[family_id] = []
            family_order.append(family_id)
        family_rows[family_id].append(row)
    matrix_groups = tuple(
        {
            "id": family_id,
            "label": _family_label(family_id),
            "rows": tuple(family_rows[family_id]),
        }
        for family_id in family_order
    )
    return tuple(rows), matrix_groups, trials


def _external_source_entries(
    data: ReportCPortalData,
    observations: Sequence[DesignObservation],
) -> tuple[dict[str, str], ...]:
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for observation in observations:
        # 独立复核修复：外链按试验落到具体登记号页面（含 NCT 编号），
        # 同试验多字段合并为一条，不再折疊成单条首页链接。
        nct = observation.trial_id.upper()
        url = f"https://clinicaltrials.gov/study/{nct}"
        label = f"{_trial_name(data, observation.trial_id)} · {nct}"
        if label in seen:
            continue
        seen.add(label)
        entries.append({"label": label, "url": url})
    return tuple(entries)


def _render_page_context(
    data: ReportCPortalData,
    *,
    page: StaticPage,
    catalog: ReportCatalog,
    prefix: str = "",
    current: str | None = None,
    trial: TrialRow | None = None,
    publication_limitation_zh: str | None = None,
) -> dict[str, Any]:
    page_id = page.id if trial is None else "trial-detail"
    catalog_page_id = page.id
    if trial is not None:
        observations = tuple(item for item in data.observations if item.trial_id == trial.id)
        title = f"{trial.display_id} 试验档案"
        section_title = "本试验设计事实"
        chart_title = f"{trial.display_id}设计事实"
    else:
        observations = _page_observations(data, catalog_page_id)
        title = page.title_zh
        section_title = page.title_zh
        chart_title = page.title_zh

    groups = _chart_groups(
        data,
        observations,
        page_id="trial-profile" if trial is not None else catalog_page_id,
        title=chart_title,
    )
    views = tuple(
        _evidence_view(
            data,
            observation,
            page_id=catalog_page_id if trial is None else "trial-profile",
        )
        for observation in observations
    )
    filter_rows, dimensions = _filter_dimensions_for_rows(data, observations)
    filter_groups = _filter_groups(data, filter_rows)
    page_filter_groups = tuple(group for group in filter_groups if group["scope"] == "page")
    evidence_limitations = None
    visit_insufficient = False
    if catalog_page_id == "visit-duration-followup" and trial is None:
        visit_obs = [o for o in observations if o.field in {"visit_schedule", "dosing_regimen"}]
        _tp_ok = [
            o for o in visit_obs
            if _registry_timeframe_zh(_text(o.assessment_timepoint))
            or _native_timepoint_zh(_text(o.assessment_timepoint)) != "登记时间窗（详见登记来源）"
            and _text(o.assessment_timepoint)
        ]
        _tp_ok = [o for o in _tp_ok if _text(o.assessment_timepoint)]
        if visit_obs and not _tp_ok:
            visit_insufficient = True
            # 证据不足收口：不再渲染无信息量的空轴图
            groups = ()
    if catalog_page_id == "evidence-limitations" and trial is None:
        nct_routes = sorted(
            {
                f"https://clinicaltrials.gov/study/{o.trial_id.upper()}"
                for o in data.observations
                if re.fullmatch(r"nct\d{8}", o.trial_id, re.I)
            }
        )
        evidence_limitations = {
            "data_cutoff": _text(data.data_cutoff)[:10],
            "source_count": len(
                {o.source_version_id for o in data.observations if o.source_version_id}
            ),
            "trial_count": len(data.trials),
            "product_count": len(data.products),
            "fact_count": len(data.observations),
            "registry_links": tuple(nct_routes),
            "notes": (
                "本报告的设计事实仅来自 ClinicalTrials.gov 当前记录检索报文"
                "（数据截止见上），未接入监管、专利与文献层来源；"
                "中国境内登记路线访问受阻，已按合同如实记档；"
                "样本量未披露的试验未纳入试验明细；"
                "统计与分析维度登记未公开处以显式声明呈现，不推断。"
            ),
        }
    # 核心比较页省略首屏快速筛选，但折叠面板仍保留试验/产品选择。
    # 清空 page_filter_groups 会令研究列不可选，也使 URL 恢复失去入口。
    show_quick_filter = (
        catalog_page_id not in {"design-map", "endpoint-timepoint-matrix", "overview"}
        or trial is not None
    )
    module_filter_groups = tuple(group for group in filter_groups if group["scope"] == "module")
    paths = _candidate_design_paths(data) if catalog_page_id == "design-patterns" else ()
    table_rows = _table_rows(
        data,
        observations,
        page_id=catalog_page_id if trial is None else "trial-detail",
    )
    show_design_matrix = catalog_page_id in {"overview", "design-map", "trial-profile"}
    if show_design_matrix:
        design_matrix_rows, design_matrix_groups, design_matrix_trials = _design_matrix(
            data,
            observations,
        )
    else:
        design_matrix_rows, design_matrix_groups, design_matrix_trials = (), (), ()
    overview_conclusions = None
    if catalog_page_id == "overview" and trial is None:
        n_trials = len({obs.trial_id for obs in observations if obs.trial_id})
        overview_conclusions = [
            {"label": "比较范围", "text": (
                f"围绕 {n_trials} 项注册试验，从试验设计、人群定义、入选标准、"
                "终点与随访时间窗等维度并列呈现登记事实。")},
            {"label": "设计证据", "text": (
                "全部设计事实来自登记来源并绑定观察定位；模式与权衡并列展示，不作排名。")},
            {"label": "阅读边界", "text": (
                "设计要素差异反映各试验的科学问题不同，不构成优劣判断；"
                "入排与人群定义以登记原文为准。")},
        ]
    return {
        "report": data,
        "evidence_limitations": evidence_limitations,
        "visit_insufficient": visit_insufficient,
        "report_title": f"{data.indication}临床试验设计比较",
        "page_title": title,
        "overview_conclusions": overview_conclusions,
        "page_id": page_id if trial is None else f"trial-{trial.id}",
        "catalog_page_id": catalog_page_id,
        "page": page,
        "site_prefix": prefix,
        "nav_groups": _nav_groups(
            catalog,
            prefix=prefix,
            current=current or catalog_page_id,
        ),
        "home_href": f"{prefix}{catalog.pages[0].id}.html",
        "data_prefix": f"{prefix}data",
        "asset_prefix": f"{prefix}assets",
        "snapshot_id": _text(data.report_snapshot_id, f"c-{data.report_version}"),
        "row_set_digest": hashlib.sha256(
            _canonical_json([item.row_id for item in observations])
        ).hexdigest(),
        "lead": (
            "在有来源的设计事实之上并列呈现模式、权衡与可选路径，不作排名。"
            if catalog_page_id == "design-patterns"
            else page.responsibility_zh
        ),
        "section_title": section_title,
        "visuals": page.visuals,
        "chart_groups_json": _json(groups),
        "table_columns": _table_columns(catalog_page_id if trial is None else "trial-detail"),
        "table_rows": table_rows,
        "external_sources": _external_source_entries(data, observations),
        "filter_rows_json": _json(filter_rows),
        "row_dimensions_json": _json(dimensions),
        "filter_dimensions_json": _json(tuple(_FILTER_DIMENSION_LABELS)),
        "page_filter_groups": page_filter_groups,
        "show_quick_filter": show_quick_filter,
        "module_filter_groups": module_filter_groups,
        "essential_filter_dimensions": ("product", "trial", "target"),
        "evidence_embed": render_evidence_drawer_embed(views),
        "evidence_host": render_evidence_drawer_host(),
        "show_design_matrix": show_design_matrix,
        "design_matrix_rows": design_matrix_rows,
        "design_matrix_groups": design_matrix_groups,
        "design_matrix_trials": design_matrix_trials,
        "design_matrix_column_count": len(design_matrix_trials) + 1,
        "filter_products": tuple(
            {"id": p.id, "name": _product_name(data, p.id)} for p in data.products
        ),
        "filter_trials": tuple(
            {
                "id": t.id,
                "name": t.name,
                "display_id": t.display_id,
            }
            for t in data.trials
        ),
        "detail_trial": (
            trial.model_copy(
                update={"name": _trial_name(data, trial.id), "region": _region_zh(trial.region)}
            )
            if trial is not None
            else None
        ),
        "candidate_paths": paths,
        "show_trial_index": catalog_page_id == "trial-profile" and trial is None,
        "cutoff_text": data.data_cutoff.strftime("%Y-%m-%d"),
        "publication_limitation_zh": publication_limitation_zh,
    }


def render_report_c_site(
    data: ReportCPortalData,
    site_root: Path,
    *,
    publication_limitation_zh: str | None = None,
    active_revision: ActiveFactRevision | None = None,
) -> tuple[Path, ...]:
    """Render all C catalog pages plus every trial dossier page."""
    site_root = Path(site_root)
    consumers: list[PortalConsumerNode] = []
    if active_revision is not None:
        observations = list(data.observations)
        user_edits = dict(data.user_edits)
        for fact, binding in active_revision.bindings_for("C"):
            if binding.collection != "observations":
                raise ReportCPortalError("C renderer只接受observations领域绑定")
            matches = [
                index for index, row in enumerate(observations) if row.row_id == binding.row_id
            ]
            if len(matches) != 1:
                raise ReportCPortalError(
                    f"C active fact绑定必须命中唯一设计观察：{binding.row_id}"
                )
            index = matches[0]
            try:
                verified_binding = validate_active_fact_binding(
                    fact,
                    binding,
                    active_fact_binding_for_c(data, binding.row_id),
                )
            except ValueError as error:
                raise ReportCPortalError(str(error)) from error
            if (fact.model_extra or {}).get("review_state") != "user_modified":
                continue
            row_payload = observations[index].model_dump(mode="python")
            original_value = (
                f"{row_payload.get('operator') or ''}"
                f"{row_payload.get('threshold_value') or ''} "
                f"{row_payload.get('threshold_unit') or ''}"
            ).strip()
            fact_extra = fact.model_extra or {}
            operator = fact_extra.get("threshold_operator")
            threshold = fact_extra.get("threshold_value")
            unit = fact_extra.get("threshold_unit") or fact_extra.get("unit")
            endpoint = (
                fact_extra.get("endpoint_definition")
                or row_payload["source_field_name"]
            )
            cleared = fact.disclosure_state == "user_cleared"
            display_numeric = threshold if threshold is not None else fact.normalized_value
            narrative = (
                f"{endpoint}：用户清除，待重新核实。"
                if cleared else (
                    f"{endpoint}："
                    f"{operator or ''}{display_numeric} "
                    f"{unit or ''}。"
                ).replace("  ", " ")
            )
            row_payload.update(
                {
                    "operator": operator,
                    "threshold_value": None if threshold is None else str(threshold),
                    "threshold_unit": unit,
                    "display_text": narrative,
                    "review_state": "user_modified",
                    "disclosure_state": (
                        FactDisclosureState.USER_CLEARED
                        if cleared else row_payload["disclosure_state"]
                    ),
                }
            )
            observations[index] = DesignObservation.model_validate(row_payload)
            current_value = None
            if threshold is not None:
                current_value = f"{operator or ''}{float(threshold):g} {unit or ''}".strip()
            user_edits[binding.row_id] = user_edit_disclosure(
                fact,
                active_revision,
                original_value=original_value,
                current_value=current_value,
            )
            specific_pages = [
                page_id
                for page_id, fields in _PAGE_FIELDS.items()
                if fields is not None and observations[index].field in fields
            ]
            if not specific_pages:
                raise ReportCPortalError(
                    f"C设计观察没有既有专题消费者：{observations[index].field}"
                )
            consumer_page = f"{specific_pages[0]}.html"
            consumers.append(
                PortalConsumerNode(
                    report="C",
                    fact_id=fact.fact_id,
                    fact_version_id=fact.fact_version_id,
                    collection="observations",
                    row_id=binding.row_id,
                    binding_identity=verified_binding,
                    original_row_sha256=verified_binding.original_row_sha256,
                    page_relative_path=consumer_page,
                    chart_consumer=f"__CHART_GROUPS__.rows[row_id={binding.row_id}].threshold_value",
                    table_consumer=f"{consumer_page}#table-row:{binding.row_id}",
                    narrative_consumer=f"evidence-view:{binding.row_id}.user_edit.current_value",
                    index_consumer=f"data/search-index.js#observation:{binding.row_id}",
                    source_binding_consumer=f"evidence-view:{binding.row_id}.source_locator",
                )
            )
        data = data.model_copy(
            update={"observations": tuple(observations), "user_edits": user_edits}
        )
    _assert_design_gate(data)
    _reset_site_root(site_root)
    _copy_assets(site_root)
    (site_root / "data").mkdir(parents=True, exist_ok=True)

    registry = PageRegistry.load()
    catalog = registry.catalog(ReportKind.C)

    report_payload = data.model_dump(mode="json")
    (site_root / "data" / "report.js").write_text(
        "window.REPORT_C=" + _json(report_payload) + ";\n",
        encoding="utf-8",
    )

    env = Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    page_template = env.get_template("page.html.j2")
    trial_template = env.get_template("trial_detail.html.j2")
    generated: list[Path] = []

    for page in catalog.pages:
        context = _render_page_context(
            data,
            page=page,
            catalog=catalog,
            publication_limitation_zh=publication_limitation_zh,
        )
        output = site_root / f"{page.id}.html"
        output.write_text(page_template.render(**context), encoding="utf-8")
        generated.append(output)

    trials_dir = site_root / "trials"
    trials_dir.mkdir(exist_ok=True)
    profile_page = next(page for page in catalog.pages if page.id == "trial-profile")
    for trial in data.trials:
        context = _render_page_context(
            data,
            page=profile_page,
            catalog=catalog,
            prefix="../",
            current=profile_page.id,
            trial=trial,
            publication_limitation_zh=publication_limitation_zh,
        )
        output = trials_dir / f"{trial.id}.html"
        output.write_text(trial_template.render(**context), encoding="utf-8")
        generated.append(output)

    expected_routes = registry.sitemap(ReportKind.C, trial_ids=data.trial_ids)
    routes = [
        {"route": route, "path": route_to_site_path(route).as_posix()} for route in expected_routes
    ]
    sitemap_payload = {
        "report": "C",
        "catalog_version": catalog.contract_version,
        "routes": routes,
        "digest": hashlib.sha256(_canonical_json(routes)).hexdigest(),
    }
    (site_root / "data" / "sitemap.json").write_bytes(_canonical_json(sitemap_payload))

    search: list[dict[str, Any]] = []

    def add_search_entry(title: str, slug: str, *keywords: Any) -> None:
        values: list[str] = []
        seen: set[str] = set()
        for candidate in (title, *keywords):
            items = (
                candidate
                if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes))
                else (candidate,)
            )
            for item in items:
                text = _text(item)
                if text and text not in seen:
                    seen.add(text)
                    values.append(text)
        search.append({"title": title, "slug": slug, "keywords": values})

    for page in catalog.pages:
        add_search_entry(
            page.title_zh,
            page.id,
            page.navigation_group_zh,
            page.responsibility_zh,
        )
    for product in data.products:
        display_name = _product_name(data, product.id)
        add_search_entry(
            f"{display_name}产品",
            "trial-profile",
            "产品",
            display_name,
            product.target,
            product.modality,
        )
    for trial in data.trials:
        add_search_entry(
            f"{trial.display_id}试验档案",
            f"trials/{trial.id}",
            "试验档案",
            trial.name,
            trial.display_id,
            trial.phase,
            _region_zh(trial.region),
            trial.role,
            _product_name(data, trial.product_id),
        )
    for observation in data.observations:
        add_search_entry(
            f"{_field_label(observation.field)} · {_trial_display(data, observation.trial_id)}",
            "overview",
            _field_label(observation.field),
            _family_label(observation.field_family),
            observation.source_text,
            _trial_name(data, observation.trial_id),
            _product_name(data, observation.product_id),
        )

    (site_root / "data" / "search-index.js").write_text(
        "window.__SEARCH_INDEX__=" + _json(search) + ";\n",
        encoding="utf-8",
    )
    if active_revision is not None:
        write_render_receipt(
            site_root,
            report="C",
            active_revision=active_revision,
            consumers=tuple(consumers),
        )
    return tuple(generated)


def validate_active_fact_revision_c(
    data: ReportCPortalData,
    active_revision: ActiveFactRevision,
) -> None:
    """Validate every C binding before a render transaction can begin."""
    for fact, binding in active_revision.bindings_for("C"):
        if binding.collection != "observations":
            raise ReportCPortalError("C renderer只接受observations领域绑定")
        try:
            validate_active_fact_binding(
                fact,
                binding,
                active_fact_binding_for_c(data, binding.row_id),
            )
        except ValueError as error:
            raise ReportCPortalError(str(error)) from error


def active_fact_binding_for_c(
    data: ReportCPortalData,
    row_id: str,
) -> ActiveFactBinding:
    """Resolve the immutable identity of one original C design observation."""
    matches = [row for row in data.observations if row.row_id == row_id]
    if len(matches) != 1:
        raise ReportCPortalError(f"C active fact绑定必须命中唯一设计观察：{row_id}")
    row = matches[0]
    products = {item.id: item for item in data.products}
    trials = {item.id: item for item in data.trials}
    statistical_form = "threshold" if row.threshold_value is not None else "design_text"
    measure_object = (
        "participants" if row.field_family is DesignFieldFamily.POPULATION else "design"
    )
    unit = row.threshold_unit or "text"
    return ActiveFactBinding(
        report="C",
        collection="observations",
        row_id=row.row_id,
        product_id=row.product_id,
        drug_name=products[row.product_id].name,
        trial_id=row.trial_id,
        registry_id=trials[row.trial_id].display_id,
        group_id=row.group_id,
        arm=None,
        cohort_id=row.cohort_id,
        period=row.period,
        endpoint_definition=row.field,
        event_definition=None,
        statistical_form=statistical_form,
        measure_object=measure_object,
        unit=unit,
        normalized_unit=unit,
        source_version_id=row.source_version_id,
        source_pointer=canonical_source_pointer(row.source_locator.model_dump(mode="json")),
        original_row_sha256=canonical_sha256(row.model_dump(mode="json")),
    )
