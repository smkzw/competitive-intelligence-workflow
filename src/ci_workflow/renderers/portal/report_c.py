"""Task 7.5: build the complete static C-class design comparison portal.

The renderer is an adapter over Task 7.1–7.4 design observations. It projects
immutable design facts into offline chart groups, complete tables, and evidence
views. The browser only filters, restores URL state, and opens the data-basis
panel; it does not recompute scientific facts or design recommendations.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal, InvalidOperation
from html import unescape
from pathlib import Path
from typing import Any, Self
from urllib.parse import urlsplit

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState, ReportKind
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.gates.models import SourceRole
from ci_workflow.qc.browser import route_to_site_path
from ci_workflow.renderers.portal.active_fact_projection import (
    ActiveFact,
    ActiveFactBinding,
    ActiveFactRevision,
    PortalConsumerNode,
    canonical_sha256,
    canonical_source_pointer,
    source_consumer_node,
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
from ci_workflow.renderers.portal.report_a import ProductRow, StudyRow
from ci_workflow.reports.c import (
    DesignFieldFamily,
    DesignGateDecision,
    DesignObservation,
    evaluate_design_gate,
)
from ci_workflow.reports.c.endpoint_instances import _identity as endpoint_instance_identity
from ci_workflow.reports.common.evidence_view import (
    EvidenceConflict,
    EvidenceField,
    EvidenceFieldState,
    EvidenceObservationKind,
    EvidenceView,
    OriginalTextStatus,
    UserEditDisclosure,
    assert_evidence_views_serializable,
    clean_evidence_locator,
    precise_locator_anchor,
)
from ci_workflow.reports.common.identity_projection import (
    PortalIdentityContext,
    render_identity_headers,
)
from ci_workflow.reports.common.numeric_projection import NumericMeasureKind, project_numeric
from ci_workflow.reports.common.page_registry import PageRegistry, ReportCatalog, StaticPage
from ci_workflow.reports.common.view_state import (
    FacetAssignment,
    FacetPlan,
    NumericFrameEligibility,
    ReportRow,
    WorkspaceMembership,
)

from .report_a import _native_endpoint_zh, _native_timepoint_zh

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates" / "c"
_ASSET_DIR = Path(__file__).resolve().parent / "assets"

_FIELD_LABELS_ZH: dict[str, str] = {
    "trial_identity": "试验标识",
    "target_population": "目标人群",
    "inclusion_criterion": "入选标准",
    "exclusion_criterion": "排除标准",
    "arm_randomization_blinding": "随机与盲法",
    "experimental_arm": "试验组内干预",
    "control_arm": "对照组内干预",
    "dosing_regimen": "给药方案",
    "primary_endpoint_definition": "主要终点定义",
    "primary_endpoint_description": "主要终点定义说明",
    "primary_endpoint_timepoint": "主要终点时间点",
    "secondary_endpoint_definition": "次要终点定义",
    "secondary_endpoint_description": "次要终点定义说明",
    "secondary_endpoint_timepoint": "次要终点时间点",
    "analysis_sets": "分析集",
    "statistical_comparisons": "主要比较与统计模型",
    "multiplicity_adjustment": "多重性校正",
    "missing_data_handling": "缺失数据处理",
    "visit_schedule": "访视与随访",
    "planned_or_actual_sample_size": "计划或实际样本量",
    "planned_sample_size_terms": "计划样本量与计数条件",
    "analysis_population": "分析人群",
    "comparison_logic": "比较方法",
    "statistical_model": "统计模型",
    "effect_size": "效应量",
    "multiplicity": "多重性控制",
    "sample_size_assumptions": "样本量依据",
    "estimand_intercurrent": "估计目标与伴发事件策略",
    "missing_data_sensitivity": "缺失数据与敏感性处理",
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
            "primary_endpoint_description",
            "primary_endpoint_timepoint",
            "secondary_endpoint_definition",
            "secondary_endpoint_description",
            "secondary_endpoint_timepoint",
        }
    ),
    "visit-duration-followup": frozenset({"visit_schedule", "dosing_regimen"}),
    "sample-analysis-statistics": frozenset(
        {
            "planned_or_actual_sample_size",
            "planned_sample_size_terms",
            "analysis_population",
            "analysis_sets",
            "statistical_comparisons",
            "multiplicity_adjustment",
            "missing_data_handling",
            "comparison_logic",
            "statistical_model",
            "effect_size",
            "multiplicity",
            "sample_size_assumptions",
            "estimand_intercurrent",
            "missing_data_sensitivity",
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
    source_evidence_snapshot_id: str | None = Field(
        default=None, exclude_if=lambda value: value is None,
    )
    # Origin capture IDs stay in scientific observations. Public versions come
    # only from an explicit projection of the verified evidence snapshot.
    source_version_by_source_id: Mapping[str, str] = Field(
        default_factory=dict, exclude_if=lambda value: not value,
    )
    products: tuple[ProductRow, ...]
    trials: tuple[StudyRow, ...] = Field(min_length=1)
    observations: tuple[DesignObservation, ...] = Field(min_length=1)
    user_edits: dict[str, UserEditDisclosure] = Field(default_factory=dict)
    # 独立复核 C r19：包内设计路径综合（patterns + candidate_paths）随门户数据下发，
    # design-patterns 页不再空转为核心事实表
    design_paths: Mapping[str, Any] | None = None

    @field_validator("report_snapshot_id", "source_evidence_snapshot_id")
    @classmethod
    def _snapshot_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("C 类报告锁定快照标识不得为空")
        return value

    @model_validator(mode="after")
    def _products_and_trials_align(self) -> Self:
        if self.source_evidence_snapshot_id is not None or self.source_version_by_source_id:
            if self.source_evidence_snapshot_id is None:
                raise ValueError("C 类来源版本投影必须绑定明确锁定快照")
            if set(self.source_version_by_source_id) != {
                row.source_version_id for row in self.observations
            } or any(not key.strip() or not value.strip()
                     for key, value in self.source_version_by_source_id.items()):
                raise ValueError("C 类来源版本投影必须完整覆盖观察来源且不得为空")
        product_ids = {item.id for item in self.products}
        trial_ids = [item.id for item in self.trials]
        if len(trial_ids) != len(set(trial_ids)):
            raise ValueError("试验标识不得重复")
        for trial in self.trials:
            if trial.product_id is not None and trial.product_id not in product_ids:
                raise ValueError(f"试验 {trial.id} 引用了未知产品 {trial.product_id}")
        for observation in self.observations:
            if observation.product_id is not None and observation.product_id not in product_ids:
                raise ValueError(
                    f"观察 {observation.row_id} 引用了未知产品 {observation.product_id}"
                )
            if observation.trial_id not in set(trial_ids):
                raise ValueError(f"观察 {observation.row_id} 引用了未知试验 {observation.trial_id}")
            trial = next(item for item in self.trials if item.id == observation.trial_id)
            if (trial.product_id is None or observation.product_id is None) \
                    and trial.product_id != observation.product_id:
                raise ValueError(f"观察 {observation.row_id} 的研究与产品关联不一致")
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
    # A substring is not a translation or proof of the rest of a protocol clause.
    # Preserve all source qualifiers until a source-bound translation exists;
    # never substitute an indication-specific canned set of requirements.
    return f"{label}原文：{value}"


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
        "charts.js",
        "evidence-drawer.css",
        "evidence-drawer.js",
        "kangzhe-site.css",
        "kangzhe-site.js",
        "kz-motion.js",
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


def _product_name(data: ReportCPortalData, product_id: str | None) -> str:
    if product_id is None:
        return "产品关联待核"
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
                if trial.product_id is None:
                    return f"{trial.display_id} · {trial.phase}研究"
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


def _product_target(data: ReportCPortalData, product_id: str | None) -> str:
    for product in data.products:
        if product.id == product_id:
            return product.target
    return "靶点未列示"


def _group_label_zh(group_id: str | None) -> str:
    value = _text(group_id)
    if value.endswith("-source-clause"):
        return "组别适用范围见原文"
    if value.endswith("-experimental"):
        return "试验组"
    if value.endswith("-control"):
        return "对照组"
    if not value or value.endswith("-all"):
        return "未按组别拆分"
    return "已定义组别"


def _cohort_label_zh(cohort_id: str | None) -> str:
    value = _text(cohort_id)
    if value.endswith("-source-clause"):
        return "条款适用范围见原文"
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


# 终点族字段：definition/timepoint/description 三类观察共享显式实例身份。
_ENDPOINT_FIELDS = frozenset(
    {
        "primary_endpoint_definition",
        "primary_endpoint_description",
        "primary_endpoint_timepoint",
        "secondary_endpoint_definition",
        "secondary_endpoint_description",
        "secondary_endpoint_timepoint",
    }
)

_ENDPOINT_ROLE_LABELS_ZH = {
    "primary_endpoint": "主要终点",
    "secondary_endpoint": "次要终点",
}

# 未结构化提取：来源条款已给出可核实内容，但类型化字段（量表/阈值/单位等）尚未
# 进入结构化投影。它既不是"来源未列示"，也不是"不适用"；不得据此推断等价。
_UNSTRUCTURED_EXTRACTION_LABEL_ZH = "未结构化提取"

# 展示组合的九项完整性前提；实际身份复用领域所有者的十轴键，另含原始
# protocol parent。period 可缺省但参与一致性比较，不由标题推断。
_ENDPOINT_INSTANCE_IDENTITY_AXES: tuple[tuple[str, str], ...] = (
    ("trial_id", "研究标识"),
    ("outcome_id", "终点实例标识"),
    ("endpoint_key", "终点角色键"),
    ("group_id", "组别标识"),
    ("cohort_id", "队列标识"),
    ("period", "期别"),
    ("product_id", "产品标识"),
    ("source_version_id", "来源版本标识"),
    ("assessment_timepoint", "评估时间点"),
)


def _endpoint_axis_values(observation: DesignObservation) -> dict[str, str | None]:
    return {
        "trial_id": observation.trial_id,
        "outcome_id": _text(observation.outcome_id),
        "endpoint_key": _text(observation.endpoint_key),
        "group_id": observation.group_id,
        "cohort_id": observation.cohort_id,
        "period": _text(observation.period),
        "product_id": observation.product_id,
        "source_version_id": observation.source_version_id,
        "assessment_timepoint": _text(observation.assessment_timepoint),
    }


def _endpoint_instance_projection(
    observations: Sequence[DesignObservation],
) -> dict[str, dict[str, Any]]:
    """把 validated 观察的显式终点实例上下文投影为逐行载荷。

    组合只发生在同一研究内部：完整性前提满足且领域十轴身份一致的
    definition/timepoint/description 观察共享实例键；缺少必需上下文时独立
    列示。不同组、评估时间和原始父路径是不同实例，不自动标记冲突；同一
    完整身份同一字段的原文或阈值矛盾才标记待核，全部保留。不同研究之间
    绝不因序号、角色或标题相似而配对，也不聚合或选择第一条。
    """
    axis_by_row: dict[str, dict[str, str | None]] = {}
    identity_by_row: dict[str, tuple[str | None, ...]] = {}
    values_by_field: dict[tuple[tuple[str | None, ...], str], set[tuple[str, ...]]] = {}
    projection: dict[str, dict[str, Any]] = {}
    for observation in observations:
        if observation.field not in _ENDPOINT_FIELDS:
            continue
        values = _endpoint_axis_values(observation)
        axis_by_row[observation.row_id] = values
        missing = [
            label
            for axis, label in _ENDPOINT_INSTANCE_IDENTITY_AXES
            if axis != "period" and not values[axis]
            and not (axis == "product_id" and observation.product_id is None)
        ]
        if missing:
            projection[observation.row_id] = {
                "instance_id": None,
                "complete": False,
                "conflict": False,
                "reason_zh": (
                    "终点实例上下文不完整（缺少"
                    + "、".join(missing)
                    + "），保持独立列示，不参与同实例组合。"
                ),
            }
            continue
        # Reuse the scientific owner identity, including exact registry outcome
        # parent. Different groups/windows are legitimate separate instances,
        # not proof of a conflict just because outcome_id is the same.
        identity: tuple[str | None, ...] = endpoint_instance_identity(observation)
        identity_by_row[observation.row_id] = identity
        values_by_field.setdefault((identity, observation.field), set()).add((
            observation.source_text, _text(observation.operator),
            _text(observation.threshold_value), _text(observation.threshold_unit),
        ))
    for observation in observations:
        row_axes = axis_by_row.get(observation.row_id)
        if row_axes is None or observation.row_id in projection:
            continue
        identity = identity_by_row[observation.row_id]
        conflicting = any(
            len(variants) > 1
            for (context, _field), variants in values_by_field.items()
            if context == identity
        )
        payload = _canonical_json(identity)
        projection[observation.row_id] = {
            "instance_id": "epinst-" + hashlib.sha256(payload).hexdigest()[:16],
            "complete": True,
            "conflict": conflicting,
            "reason_zh": (
                "同一完整终点实例的同一字段存在不同原文或阈值，保留全部观察"
                "并标明待核冲突，不选择第一条或自动汇总。"
            )
            if conflicting
            else "",
        }
    return projection


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


def _user_current_state(observation: DesignObservation) -> bool:
    """用户清除/用户修订：当前读法以当前状态为先，不得回填原始来源。

    这两类观察的当前值来自显式当前投影（display_text）或状态标签；
    source_text 只作为原始来源证据逐字保留，不能充当"当前值"。
    """
    return (
        observation.disclosure_state is FactDisclosureState.USER_CLEARED
        or observation.review_state is FactReviewState.USER_MODIFIED
    )


def _numeric_for(observation: DesignObservation) -> float | None:
    if observation.field != "planned_or_actual_sample_size":
        return None
    if observation.disclosure_state not in _NUMERIC_DISCLOSED_STATES:
        # 非已报告状态没有当前可核实数值；原始数值只留在来源证据中。
        return None
    raw = observation.threshold_value
    if raw is None and observation.review_state is not FactReviewState.USER_MODIFIED:
        # 用户修订未给出当前数值时，同样不得用原文旧值充当当前读法。
        raw = observation.source_text
    if raw is None:
        return None
    try:
        number = float(str(raw).replace(",", "").strip())
        return number if math.isfinite(number) and number >= 0 and number.is_integer() else None
    except (TypeError, ValueError):
        return None


def _qualifier_states_current_count(display: str, numeric: float) -> bool:
    """限定文本是否与当前可核实计数一致（有序数分隔容忍，不做数值推断）。

    旧的显示文本可能来自上一次捕获或另一次修订；与当前计数不一致时它不是当前
    读法，只能作为来源证据保留。这里只做一致性守卫，绝不从文本补出数值。
    """
    if not numeric.is_integer():
        return False
    count = str(int(numeric))
    normalized = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", display)
    return re.search(rf"(?<!\d){re.escape(count)}(?!\d)", normalized) is not None


def _sample_size_qualifier_zh(observation: DesignObservation) -> str | None:
    """已核实入组限定（实际/计划入组）的来源绑定显示文本。

    只透传投影层基于同一来源版本 ``enrollmentInfo.type`` 生成的限定；不从计数、
    数组顺序或分组分母推断类型；用户修订/清除行以当前投影为先；与当前计数不一致
    的过期限定不进入当前读法（当前值仍是可核实计数）。
    """
    if observation.field != "planned_or_actual_sample_size":
        return None
    if _user_current_state(observation):
        return None
    display = _text(observation.display_text)
    if not display:
        return None
    numeric = _numeric_for(observation)
    if numeric is None or not _qualifier_states_current_count(display, numeric):
        return None
    return display


def _operator_zh(value: str | None) -> str:
    return {
        ">=": "≥",
        "=>": "≥",
        "<=": "≤",
        "=<": "≤",
    }.get(_text(value), _text(value))


def _source_design_text(observation: DesignObservation) -> str:
    """Never substitute a study product or guessed regimen for a source clause.

    Explicit display text is the caller's source-bound translation or current
    user projection. Otherwise keep every qualifier, dose, branch and negation.
    Scientific names remain in the shared identity header, not inferred here.
    """
    return (observation.display_text if observation.display_text is not None
            else observation.source_text)


def _compact_regimen_zh(data: ReportCPortalData, observation: DesignObservation) -> str:
    return _source_design_text(observation)


def _compact_arm_zh(data: ReportCPortalData, observation: DesignObservation) -> str:
    return _source_design_text(observation)


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


def _value_text(data: ReportCPortalData, observation: DesignObservation) -> str:
    def _tp_disp(tp: str | None) -> str:
        if not tp:
            return ""
        return _registry_timeframe_zh(tp) or _native_timepoint_zh(tp) or tp

    numeric = _numeric_for(observation)
    if numeric is not None:
        # 实际/计划入组限定来自同一来源的已核实类型；数值同轴仍由 numeric_value
        # 与 numeric_projection 提供，限定文本不替换数值投影。
        qualifier = _sample_size_qualifier_zh(observation)
        if qualifier is not None:
            return qualifier
        if numeric.is_integer():
            return str(int(numeric))
        return str(numeric)
    if _user_current_state(observation):
        # 用户清除/用户修订且当前没有可核实数值：当前读法只来自显式当前投影
        # 或状态标签，不再回退原始来源文本或原文分段。
        return _text(observation.display_text) or _state_label(observation.disclosure_state)
    if (
        observation.field == "planned_or_actual_sample_size"
        and observation.disclosure_state not in _NUMERIC_DISCLOSED_STATES
    ):
        return _state_label(observation.disclosure_state)
    source_text = _text(observation.display_text or observation.source_text)
    if observation.source_clause_context is not None and observation.display_text is None:
        # A source-qualified reading index is separate from its verbatim quote.
        # Do not normalize extracted line breaks or silently summarize clauses.
        return observation.source_text
    text = _registry_display_text(source_text)
    operator = _operator_zh(observation.operator)
    threshold = _text(observation.threshold_value)
    unit = _text(observation.threshold_unit)
    timepoint = _text(observation.assessment_timepoint)
    scale = _text(observation.scale)

    if observation.field == "trial_identity":
        return observation.display_text or _trial_name(data, observation.trial_id)
    if observation.field == "target_population":
        # 独立复核 C r20（veto 第8项）：结构化最低年龄优先，
        # 同列口径统一为可比事实，不再自指"已记录（原文见来源）"
        structured_age = _text(observation.threshold_value)
        if structured_age:
            unit = _text(observation.threshold_unit, "岁")
            bound = "最高" if observation.operator in {"≤", "<="} else "最低"
            return f"登记{bound}年龄：{structured_age}{unit}"
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
        value = _eligibility_source_text(observation.field, source_text)
        return value + (f"（{timepoint}）" if timepoint else "")
    if observation.field in {"primary_endpoint_description", "secondary_endpoint_description"}:
        return f"{_field_label(observation.field)}：{text}"
    if observation.field in {"experimental_arm", "control_arm"}:
        return _compact_arm_zh(data, observation)
    if observation.field == "dosing_regimen":
        return _compact_regimen_zh(data, observation)
    if observation.field in {"primary_endpoint_definition", "secondary_endpoint_definition"}:
        # A metric keyword is not proof of its threshold, denominator, estimator
        # or scale variant. Preserve the complete definition until an explicit
        # source-bound translation exists; the description remains alongside it.
        return _source_design_text(observation)
    if observation.field == "primary_endpoint_timepoint":
        translated = _registry_timeframe_zh(timepoint) if timepoint else None
        return translated or timepoint or "主要终点评估时间未公开"
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
        "planned_sample_size_terms",
        "analysis_population",
        "analysis_sets",
        "statistical_comparisons",
        "multiplicity_adjustment",
        "missing_data_handling",
        "comparison_logic",
        "statistical_model",
        "effect_size",
        "multiplicity",
        "sample_size_assumptions",
        "estimand_intercurrent",
        "missing_data_sensitivity",
        "design_kind",
        "study_design_type",
    }
)


def _chart_row(
    data: ReportCPortalData,
    observation: DesignObservation,
    *,
    chart_type: str,
    endpoint_instance: Mapping[str, Any] | None = None,
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
        "source_text": (
            observation.source_text if observation.source_clause_context is not None
            else _text(observation.source_text)
        ),
        "source_field_name": _text(observation.source_field_name, "未列示"),
        "source_location_zh": (
            f"{_source_kind_zh(observation.source_role.value)} · "
            f"{_field_label(observation.field)}"
        ),
        "review_state": observation.review_state.value,
        "scale": (
            lambda s: s + _untranslated_note(observation.source_role.value)
            if (
                s and len(re.findall(r"[A-Za-z]{3,}", s)) >= 2
                and not re.search(r"[\u4e00-\u9fff]", s)
            )
            else s
        )(_text(observation.scale)),
        # R24-146 有界执行及 R24-154 主线程修复：显式上下文逐行投影，
        # 组合判据由 _endpoint_instance_projection 给出，浏览器只读不重算。
        "source_version_id": _public_source_version(data, observation.source_version_id),
        "assessment_timepoint_raw": _text(observation.assessment_timepoint) or None,
        "outcome_id": _text(observation.outcome_id) or None,
        "endpoint_role_key": _text(observation.endpoint_key) or None,
        "period": _text(observation.period) or None,
    }
    if endpoint_instance is not None:
        row["endpoint_instance"] = dict(endpoint_instance)
    if observation.source_clause_context is not None:
        row["source_topic_zh"] = observation.source_clause_context.label_zh
        if observation.source_clause_context.continuations:
            row["source_context_note_zh"] = "跨页条款，前后文各页分别定位"
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
        # 已核实入组限定（实际/计划入组 + 计数 + 例）保留在读者面；数值同轴仍由
        # numeric_value / numeric_projection 承担，限定不替换数值。
        row["value"] = (
            value_text
            if _sample_size_qualifier_zh(observation) is not None
            else int(numeric) if numeric.is_integer() else numeric
        )
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
    endpoint_instances = _endpoint_instance_projection(observations)
    if page_id in {"inclusion-criteria", "exclusion-criteria"}:
        label = "公开入选标准条目" if page_id == "inclusion-criteria" else "公开排除标准条目"
        rows = []
        for observation in observations:
            row = _chart_row(
                data,
                observation,
                chart_type="status_matrix",
                endpoint_instance=endpoint_instances.get(observation.row_id),
            )
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
        # Source-comparison mode consumes one complete query. The former
        # sample-size/analysis-only groups hid other statistics from search and
        # its table even though they existed in a separate secondary matrix.
        return ({
            "title_zh": "样本量与统计分析原文对照",
            "rows": [_chart_row(data, item, chart_type="status_matrix")
                     for item in observations],
            "_chart_type": "status_matrix",
        },)
    return (
        {
            "title_zh": title,
            "rows": [
                _chart_row(
                    data,
                    item,
                    chart_type=chart_type,
                    endpoint_instance=endpoint_instances.get(item.row_id),
                )
                for item in observations
            ],
            "_chart_type": chart_type,
        },
    )


def _evidence_field(
    value: Any,
    state: str | None = None,
    *,
    missing_default: EvidenceFieldState | None = None,
) -> EvidenceField:
    """确定值 XOR 互斥状态；空白不得留白。

    ``missing_default`` 供类型化子字段使用：已报告事实的字段尚未结构化提取时，
    不得落到"来源未列示"（那是对来源缺失的断言），改用调用方给出的保守状态。
    """
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
    resolved = state_map.get(state or "")
    if resolved is None:
        resolved = missing_default or EvidenceFieldState.SOURCE_NOT_LISTED
    return EvidenceField(state=resolved)


_C_DOCUMENT_ROLE_ZH: dict[str, str] = {
    "registry": "临床试验登记页",
    "clinical-trial-registry": "临床试验登记页",
    "clinical_trial_registry": "临床试验登记页",
    "primary_registry": "主要登记记录",
    "registry_result": "登记结果记录",
    "primary_trial_report": "主要试验报告",
    "publication": "期刊论文",
    "supplementary_material": "补充材料",
    "protocol": "研究方案",
    "protocol_sap": "研究方案与统计分析计划",
    "company_disclosure": "企业披露",
    "conference_disclosure": "会议披露",
    "designated_industry_source": "行业指定来源",
    "source_primary": "原始来源",
    "source_record": "来源字段记录",
}
_C_DOCUMENT_ROLE_ALIASES: dict[str, str] = {
    "clinical-trial-registry": "registry",
    "clinical_trial_registry": "registry",
}
_C_HEADING_ZH: dict[str, str] = {
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


def _source_kind_zh(role: str) -> str:
    return _C_DOCUMENT_ROLE_ZH.get(role, "来源记录")


def _untranslated_note(role: str) -> str:
    kind = "登记" if role in {
        "registry", "clinical-trial-registry", "clinical_trial_registry",
    } else _source_kind_zh(role)
    return f"（{kind}原文，未译）"


def _translation_provenance_note(observation: DesignObservation, value: Any) -> str:
    """展示文本的来源语种标注：中文译述与未译登记英文互不冒充。

    判定只用既有的 display_text / source_text 关系：

    - 含中文且正是同一来源英文条款的显式译文 → 标注中文译述并指向数据依据；
      中文门户文案（无英文来源或非 display 文本）不标注，绝不写成"未译"。
    - 无中文且正是未译的登记英文原文（display_text 未覆盖 source_text）→ 标注
      "原文，未译"；英文展示文本若与登记原文不同（当前投影/压缩文本），不得冒充
      登记原文，改为显式指向数据依据中的逐字原文。
    """
    text = str(value if value is not None else "")
    if not text.strip():
        return ""
    display = _text(observation.display_text)
    source = _text(observation.source_text)
    is_display = bool(display) and display == text.strip()
    is_source = bool(source) and text.strip() in {
        source, _registry_display_text(source),
    }
    has_cjk = re.search(r"[\u4e00-\u9fff]", text) is not None
    if has_cjk:
        if (
            is_display
            and display != source
            and source
            and re.search(r"[\u4e00-\u9fff]", source) is None
            # 译述标注只针对条款级文字原文：纯数字/计数来源是数值事实，不称"译述"。
            and len(re.findall(r"[A-Za-z]{2,}", source)) >= 2
        ):
            return "（中文译述，登记原文见数据依据）"
        return ""
    if len(re.findall(r"[A-Za-z]{3,}", text)) < 2:
        return ""
    if is_display and not is_source:
        return "（非登记原文，登记原文见数据依据）"
    return _untranslated_note(observation.source_role.value)


def _safe_locator(observation: DesignObservation) -> EvidenceLocator | None:
    """保留来源自身的 URL、字段路径与文档位置，不改写、不补造。

    独立会商 R24-25 FAIL 复现：C 曾把论文/外部来源 URL 按试验标识改写成 CT.gov
    深链、丢掉 JSON 字段路径，并把无章节的行补成“登记结果”；这里只做本机路径
    字段去除与章节中文映射，其余定位逐字保留；无可用锚点返回 None。
    """
    locator = clean_evidence_locator(observation.source_locator)
    if locator is None:
        return None
    heading = _C_HEADING_ZH.get(locator.heading or "", locator.heading)
    visible = {
        "document_role": _C_DOCUMENT_ROLE_ALIASES.get(
            locator.document_role, locator.document_role
        ),
        "field_path": locator.field_path,
        "heading": heading,
        "page": locator.page,
        "table": locator.table,
        "row": locator.row,
        "column": locator.column,
        "paragraph": locator.paragraph,
        "url": locator.url,
    }
    visible = {name: value for name, value in visible.items() if value is not None}
    try:
        return EvidenceLocator.model_validate(visible)
    except ValueError:
        return None


def _public_source_version(data: ReportCPortalData, source_id: str) -> str:
    """Explicit snapshot projection, or unchanged legacy identity for reading."""
    if data.source_version_by_source_id:
        return data.source_version_by_source_id[source_id]
    return source_id


def _evidence_view(
    data: ReportCPortalData,
    observation: DesignObservation,
    *,
    page_id: str,
) -> EvidenceView:
    state = observation.disclosure_state.value
    snapshot = _text(
        data.report_snapshot_id or data.source_evidence_snapshot_id,
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
    locator = _safe_locator(observation)
    source_version_id = _public_source_version(data, observation.source_version_id)
    # 精确来源原文不得经过用户可见标签的空白归一化函数。
    source_text = (
        observation.source_text
        if observation.source_text and observation.source_text.strip() else None
    )
    # 已定位＝来源版本 + 逐字原文 + 精确非本机锚点三件套齐备（独立会商 R24-25）
    located = bool(
        source_version_id
        and source_text
        and locator is not None
        and precise_locator_anchor(locator) is not None
    )
    if located and locator is not None:
        source_kind = _source_kind_zh(locator.document_role)
        source_version_label_zh = f"{source_kind}来源版本"
    else:
        source_version_label_zh = "逐事实来源待核"
    # 已报告事实的类型化字段缺失＝未结构化提取（来源条款已给出内容），不是来源
    # 缺失，也不是技术故障；结构上无时间点的字段缺省"不适用"（与完整表口径一致）。
    field_default = (
        EvidenceFieldState.NOT_EXTRACTED
        if observation.disclosure_state in _NUMERIC_DISCLOSED_STATES
        else None
    )
    timepoint_default = (
        EvidenceFieldState.NOT_APPLICABLE
        if observation.field in _NO_TIMEPOINT_FIELDS
        else field_default
    )
    missing_typed = [
        label for label, value in (
            ("量表", observation.scale),
            ("阈值", observation.threshold_value),
        ) if value is None
    ]
    extraction_gap_note = (
        "本条为已报告事实，" + "、".join(missing_typed)
        + f"等结构化字段尚未提取（{_UNSTRUCTURED_EXTRACTION_LABEL_ZH}），"
        "不代表来源未公开，也不推断跨研究等价；请以逐字原文为准。"
        if missing_typed and _unstructured_extraction(observation) else ""
    )
    return EvidenceView.model_construct(
        None,
        report_kind=ReportKind.C,
        observation_kind=EvidenceObservationKind.GENERAL,
        row=report_row,
        product_zh=_product_name(data, observation.product_id),
        trial_zh=_trial_name(data, observation.trial_id),
        group_zh=_evidence_field(_group_label_zh(observation.group_id), state),
        element_zh=label,
        scale=_evidence_field(observation.scale, state, missing_default=field_default),
        timepoint=_evidence_field(
            observation.assessment_timepoint, state, missing_default=timepoint_default,
        ),
        value=_evidence_field(value_text, state),
        threshold=_evidence_field(
            observation.threshold_value, state, missing_default=field_default,
        ),
        unit=_evidence_field(observation.threshold_unit, state, missing_default=field_default),
        numerator=_evidence_field(None, "not_applicable"),
        denominator=_evidence_field(None, "not_applicable"),
        source_trace_state="located" if located else "unverified",
        source_version_id=source_version_id if located else None,
        source_version_label_zh=source_version_label_zh,
        locator=locator if located else None,
        explanation=_evidence_field(
            f"本条信息摘自{source_kind}，"
            f"适用于{_observation_cohort_zh(observation)}；"
            + ("本条为方案/SAP的设计或分析约定，不代表已观察的临床结果；"
               if observation.source_role is SourceRole.PROTOCOL_SAP else "")
            +
            "来源版本、逐字原文与精确位置均已定位，仍不代替医学裁决；"
            f"当前公开情况为{_state_label(observation.disclosure_state)}。"
            + extraction_gap_note
            if located
            else (
                "该观察仍可检索；逐事实来源版本、原文和精确定位待核，"
                "不能作为已验科学结论。"
            )
        ),
        original_text=source_text if located else None,
        original_text_status=(
            OriginalTextStatus.PROVIDED
            if located and source_text
            else OriginalTextStatus.NOT_PROVIDED
        ),
        user_edit=data.user_edits.get(observation.row_id),
        source_clause_context=observation.source_clause_context if located else None,
        conflicts=tuple(
            EvidenceConflict(
                conflicting_source_version_id=_public_source_version(data, ref.source_id),
                conflicting_value_zh=ref.original_text,
                conflict_note_zh=(
                    "来源表述存在待裁决差异，未自动选定优先来源或结论。"
                    + relation.description
                ),
                locator=ref.locator,
            )
            for relation in (
                observation.source_clause_context.relations
                if observation.source_clause_context is not None and located else ()
            )
            if relation.status in {
                "unresolved_internal_tension", "unresolved_version_divergence",
                "unresolved_wording_divergence", "unresolved_scope_difference",
            }
            for ref in relation.references
            if ref.reference_id != observation.source_row_id
        ),
        historical_versions=(),
    )


def _filter_dimensions_for_rows(
    data: ReportCPortalData,
    observations: Sequence[DesignObservation],
) -> tuple[list[dict[str, str | None]], dict[str, dict[str, str | None]]]:
    filter_rows: list[dict[str, str | None]] = []
    dimensions: dict[str, dict[str, str | None]] = {}
    for observation in observations:
        row = {
            "id": observation.row_id,
            "product": observation.product_id,
            "target": _product_target(data, observation.product_id),
            "trial": observation.trial_id,
            "element": observation.field,
            "field_family_zh": _family_label(observation.field_family),
            "scale": _scale_presentation_zh(observation, absent="未列示"),
            "timepoint": _text(observation.assessment_timepoint, "未列示"),
            "disclosure_state": observation.disclosure_state.value,
        }
        filter_rows.append(row)
        dimensions[observation.row_id] = {key: value for key, value in row.items() if key != "id"}
    return filter_rows, dimensions


def _filter_groups(
    data: ReportCPortalData,
    filter_rows: Sequence[Mapping[str, str | None]],
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
    endpoint_instances = _endpoint_instance_projection(observations)
    for observation in observations:
        chart = _chart_row(
            data,
            observation,
            chart_type=_PAGE_CHART_TYPE.get(page_id, "status_matrix"),
            endpoint_instance=endpoint_instances.get(observation.row_id),
        )
        chart["source_version"] = _public_source_version(data, observation.source_version_id)
        if chart.get("value") is None:
            chart["value"] = _state_label(observation.disclosure_state)
        # 独立复核 C r42（issue-4）/C r46（issue-1）：值列残留英文
        # （含部分转写后中英混排，如 During 残片）一律按惯例标注
        _v = chart.get("value")
        if observation.review_state is FactReviewState.USER_MODIFIED:
            chart["value"] = f"{_v}（用户修订，未独立复核）"
        else:
            # 中文译述不得标成"未译"；真正未译的登记英文仍须标注。
            provenance_note = _translation_provenance_note(observation, _v)
            if provenance_note and not str(_v).endswith(provenance_note):
                chart["value"] = f"{_v}{provenance_note}"
        if chart.get("scale") in {None, ""}:
            chart["scale"] = _scale_presentation_zh(observation, absent="不适用")
        if chart.get("group_id") in {None, ""}:
            chart["group_id"] = "未细分"
        if chart.get("cohort_id") in {None, ""}:
            chart["cohort_id"] = "未细分"
        if (
            observation.field in {"inclusion_criterion", "exclusion_criterion"}
            and not _user_current_state(observation)
        ):
            # 用户清除/修订行不按原始条款分段：当前值保持 _chart_row 的当前读法。
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
    if (
        observation.field not in {"inclusion_criterion", "exclusion_criterion"}
        or _user_current_state(observation)
    ):
        # 用户清除/修订行的当前读法只有一个：显式当前投影或状态标签。
        # 不得把原始多段条款拆成"当前"摘要（来源原文只在来源字段保留）。
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


_DESIGN_FIELD_FACET_PREFIX = "design-field::"

_NUMERIC_DISCLOSED_STATES = frozenset(
    {FactDisclosureState.REPORTED_VALUE, FactDisclosureState.REPORTED_ZERO}
)


def _unstructured_extraction(observation: DesignObservation) -> bool:
    """类型化字段为空时，是"未结构化提取"还是"确实不适用"。

    终点族条款（definition/description/timepoint）在登记来源中自带量表、阈值与
    时间窗限定；这类观察已报告而类型化字段为空时是提取缺口，既不是来源缺失，
    也不得写成"不适用"。约定外的字段族不在此列（如样本量计数无量表对象），
    继续按原文既有缺省表达。
    """
    return (
        observation.disclosure_state in _NUMERIC_DISCLOSED_STATES
        and observation.field in _ENDPOINT_FIELDS
        and bool(_text(observation.source_text))
    )


def _scale_presentation_zh(observation: DesignObservation, *, absent: str) -> str:
    """量表呈现：已提取值原样保留；提取缺口不得冒充"不适用/未列示"。"""
    scale = _text(observation.scale)
    if scale:
        return scale
    if _unstructured_extraction(observation):
        return _UNSTRUCTURED_EXTRACTION_LABEL_ZH
    return absent


def _numeric_frame_reason_zh(observation: DesignObservation) -> str:
    """每条不可绘行一个如实的显式原因；成员身份与可检索性不受影响。"""
    if observation.field != "planned_or_actual_sample_size":
        return "设计条款为原文文本，不进入数值同轴，仍在完整表与检索中保留"
    if observation.disclosure_state not in _NUMERIC_DISCLOSED_STATES:
        return (
            f"数值当前状态为{_state_label(observation.disclosure_state)}，"
            "不进入数值同轴，仍在完整表与检索中保留"
        )
    if _numeric_for(observation) is None:
        return "样本量不能核实为非负整数，保留原值与来源，不进入数值同轴"
    return (
        f"数值当前状态为{_state_label(observation.disclosure_state)}，"
        "不进入数值同轴，仍在完整表与检索中保留"
    )


def _workspace_cell_item(
    data: ReportCPortalData,
    observation: DesignObservation,
    summary: str,
) -> dict[str, Any]:
    """单个矩阵单元格条目：来源身份逐字段挂在观察自身，不跨研究借位。"""
    locator = _safe_locator(observation)
    return {
        "row_id": observation.row_id,
        "observation_id": observation.observation_id,
        "source_row_id": observation.source_row_id,
        "summary": summary,
        "source_text": observation.source_text,
        "display_text": observation.display_text,
        "outcome_id": _text(observation.outcome_id) or None,
        "endpoint_key": _text(observation.endpoint_key) or None,
        "product_id": observation.product_id,
        "trial_id": observation.trial_id,
        "group_id": observation.group_id,
        "cohort_id": observation.cohort_id,
        "arm_zh": _group_label_zh(observation.group_id),
        "source_version_id": _public_source_version(data, observation.source_version_id),
        "source_locator": locator.model_dump(mode="json") if locator is not None else None,
        "source_role": observation.source_role.value,
        "disclosure_state": observation.disclosure_state.value,
        "scale": _scale_presentation_zh(observation, absent="未列示"),
        "operator": observation.operator,
        "threshold_value": observation.threshold_value,
        "threshold_unit": observation.threshold_unit,
        "timepoint": _text(observation.assessment_timepoint, "未列示"),
        "assessment_timepoint": observation.assessment_timepoint,
    }


def design_comparison_workspace(
    data: ReportCPortalData,
    observations: Sequence[DesignObservation],
) -> dict[str, Any]:
    """Compile the C design comparison workspace from the shared typed contracts.

    ``WorkspaceMembership`` retains every observation exactly once; the
    ``FacetPlan`` is a presentation classification by design field and never
    declares clinical equivalence; ``NumericFrameEligibility`` only decides
    numeric chart permission, keeping text/unknown/cleared rows queryable
    members with an explicit reason. Each column cell preserves the
    observation's own clause, source version, product/trial/arm,
    scale/operator/timepoint and missing/unknown status. Different endpoint
    definitions, scales or thresholds stay distinct; nothing here merges
    them or infers semantic equality.
    """
    row_ids = tuple(observation.row_id for observation in observations)
    membership = WorkspaceMembership(row_ids=row_ids)
    facets = FacetPlan(
        membership_row_ids=row_ids,
        assignments=tuple(
            FacetAssignment(
                row_id=observation.row_id,
                facet_id=f"{_DESIGN_FIELD_FACET_PREFIX}{observation.field}",
            )
            for observation in observations
        ),
    )
    drawable: list[str] = []
    undrawable: dict[str, str] = {}
    for observation in observations:
        if (
            _numeric_for(observation) is not None
            and observation.disclosure_state in _NUMERIC_DISCLOSED_STATES
        ):
            drawable.append(observation.row_id)
        else:
            undrawable[observation.row_id] = _numeric_frame_reason_zh(observation)
    eligibility = NumericFrameEligibility(
        membership_row_ids=row_ids,
        drawable_row_ids=tuple(drawable),
        undrawable_reasons=undrawable,
    )
    eligible_ids = frozenset(drawable)
    trial_scope = tuple(
        trial for trial in data.trials
        if trial.id in {observation.trial_id for observation in observations}
    )
    grouped: dict[tuple[str, str], list[DesignObservation]] = {}
    for observation in observations:
        grouped.setdefault((observation.field, observation.trial_id), []).append(observation)
    columns: list[dict[str, Any]] = []
    field_order = list(dict.fromkeys(observation.field for observation in observations))
    for field in field_order:
        cells: list[dict[str, Any]] = []
        present_trials: list[str] = []
        for trial in trial_scope:
            cell_observations = grouped.get((field, trial.id), ())
            if cell_observations:
                present_trials.append(trial.id)
            items = tuple(
                _workspace_cell_item(data, observation, summary)
                for observation in cell_observations
                for summary in _matrix_item_summaries(data, observation)
            )
            cells.append(
                {
                    "trial_id": trial.id,
                    "product_id": trial.product_id,
                    "row_ids": tuple(dict.fromkeys(
                        observation.row_id for observation in cell_observations
                    )),
                    "items": items,
                    "missing": not cell_observations,
                    "numeric_eligible_row_ids": tuple(
                        observation.row_id for observation in cell_observations
                        if observation.row_id in eligible_ids
                    ),
                    "numeric_ineligible_row_ids": tuple(
                        observation.row_id for observation in cell_observations
                        if observation.row_id not in eligible_ids
                    ),
                }
            )
        columns.append(
            {
                "facet_id": f"{_DESIGN_FIELD_FACET_PREFIX}{field}",
                "facet_label_zh": _field_label(field),
                "facet_kind": "design_field_presentation",
                "presentation_only": True,
                "facet_note_zh": (
                    "分面标签只是呈现归类，不声明各研究临床等价；"
                    "各单元格保留登记原文、量表、阈值、时间窗与来源版本。"
                ),
                "cross_study": len(set(present_trials)) >= 2,
                "trial_ids": tuple(present_trials),
                "cells": tuple(cells),
            }
        )
    return {
        "membership": membership,
        "facets": facets,
        "numeric_eligibility": eligibility,
        "columns": tuple(columns),
    }


def _design_matrix(
    data: ReportCPortalData,
    observations: Sequence[DesignObservation],
) -> tuple[
    tuple[dict[str, Any], ...],
    tuple[dict[str, Any], ...],
    tuple[dict[str, Any], ...],
]:
    trials = _matrix_trial_context(data, observations)
    workspace = design_comparison_workspace(data, observations)
    columns_by_facet = {column["facet_id"]: column for column in workspace["columns"]}
    trials_by_id = {trial["id"]: trial for trial in trials}

    rows: list[dict[str, Any]] = []
    for field in _matrix_field_order(observations):
        column = columns_by_facet[f"{_DESIGN_FIELD_FACET_PREFIX}{field}"]
        field_observations = tuple(item for item in observations if item.field == field)
        field_row_ids = {item.row_id for item in field_observations}
        cells: list[dict[str, Any]] = []
        for compiled in column["cells"]:
            trial = trials_by_id[compiled["trial_id"]]
            items = compiled["items"]
            cells.append(
                {
                    "trial_id": compiled["trial_id"],
                    "product_id": trial["product_id"],
                    "trial_label": f"{trial['display_id']} · {trial['name']}",
                    "row_ids": compiled["row_ids"],
                    "items": items,
                    "summary": "；".join(item["summary"] for item in items) or "未提取",
                    "empty": not items,
                    "scale_values": tuple(dict.fromkeys(item["scale"] for item in items)),
                    "timepoint_values": tuple(
                        dict.fromkeys(item["timepoint"] for item in items)
                    ),
                    "numeric_eligible_row_ids": compiled["numeric_eligible_row_ids"],
                    "numeric_ineligible_row_ids": compiled["numeric_ineligible_row_ids"],
                }
            )
        rows.append(
            {
                "field": field,
                "label": _matrix_field_label(field, field_observations),
                "family_id": field_observations[0].field_family.value,
                "family_label": _family_label(field_observations[0].field_family),
                "cells": tuple(cells),
                "observation_count": len(field_observations),
                "facet_id": column["facet_id"],
                "facet_label_zh": column["facet_label_zh"],
                "presentation_only": column["presentation_only"],
                "facet_note_zh": column["facet_note_zh"],
                "numeric_eligible_row_ids": tuple(dict.fromkeys(
                    row_id
                    for cell in column["cells"]
                    for row_id in cell["numeric_eligible_row_ids"]
                )),
                "undrawable_reasons": tuple(
                    {"row_id": row_id, "reason_zh": reason}
                    for row_id, reason in workspace["numeric_eligibility"]
                    .undrawable_reasons.items()
                    if row_id in field_row_ids
                ),
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
        # A protocol/publication is not the registry page. Preserve the actual
        # source URL. Audience document links collapse identical URLs only;
        # per-observation scientific source versions and locators stay intact.
        locator = clean_evidence_locator(observation.source_locator)
        url = locator.url if locator is not None else None
        if not url:
            continue
        parsed = urlsplit(url)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            continue
        key = url
        if key in seen:
            continue
        seen.add(key)
        kind = _source_kind_zh(observation.source_role.value)
        label = (
            f"{_trial_name(data, observation.trial_id)} · "
            f"{observation.trial_id.upper()} · {kind}"
        )
        entries.append({"label": label, "url": url})
    return tuple(entries)


def _statistics_scope(data: ReportCPortalData) -> dict[str, Any]:
    """统计页声明字段的覆盖与复核边界：全部从实际观察与冻结目录声明派生。

    "存在观察"不等于"当前有可核实数据"：未报告/用户清除/未公开/路径未解析等
    占位状态单独列出，不冒充已提取覆盖；完全缺失的字段按冻结声明逐项列出。
    文档闭合只用实际绑定来源角色与事实计数，不做检索闭合或验收推断。
    """
    statistics_page = "sample-analysis-statistics"
    declared = tuple(
        field for field in _FIELD_LABELS_ZH
        if field in (_PAGE_FIELDS[statistics_page] or ())
    )
    observations = tuple(
        observation for observation in data.observations
        if observation.field in declared
    )
    extracted = tuple(
        field for field in declared
        if any(
            observation.field == field
            and observation.disclosure_state in _NUMERIC_DISCLOSED_STATES
            for observation in observations
        )
    )
    placeholder = tuple(
        field for field in declared
        if field not in extracted and any(
            observation.field == field for observation in observations
        )
    )
    unextracted = tuple(
        field for field in declared
        if field not in extracted and field not in placeholder
    )
    # 逐研究缺口只在字段已提取且确有试验缺少当前可核实数据时列出（材料性）。
    # 研究范围就是本报告自身的研究清单，不引入新的来源或检索闭合声明。
    trial_label_by_id = {trial.id: _trial_display(data, trial.id) for trial in data.trials}
    scope_trial_ids = {trial.id for trial in data.trials}
    per_trial_gaps: list[str] = []
    for field in extracted:
        covered = {
            observation.trial_id for observation in observations
            if observation.field == field
            and observation.disclosure_state in _NUMERIC_DISCLOSED_STATES
        }
        missing = sorted(scope_trial_ids - covered)
        if missing:
            refs = "、".join(trial_label_by_id.get(trial_id, trial_id) for trial_id in missing)
            per_trial_gaps.append(f"{_field_label(field)}：{refs}")
    source_kinds = "、".join(sorted({
        _source_kind_zh(observation.source_role.value) for observation in data.observations
    }))
    protocol_facts = sum(
        1 for observation in data.observations
        if observation.source_role is SourceRole.PROTOCOL_SAP
    )
    publication_facts = sum(
        1 for observation in data.observations
        if observation.source_role in {
            SourceRole.PRIMARY_TRIAL_REPORT, SourceRole.CONFERENCE_DISCLOSURE,
        }
    )
    protocol_closure = (
        f"本包已绑定研究方案与统计分析计划（Protocol/SAP）来源的条款级事实 "
        f"{protocol_facts} 条；仅凭条款级绑定不能证明全文是否已纳入，"
        "也不等于完整统计复核。"
        if protocol_facts
        else "本包未绑定研究方案与统计分析计划（Protocol/SAP）来源；"
             "本报告未纳入 Protocol/SAP 正文。"
    )
    publication_closure = (
        f"本包已绑定主要试验报告或会议披露来源的条款级事实 {publication_facts} 条；"
        "出版分支以实际绑定来源为限，不构成完整出版检索。"
        if publication_facts
        else f"本包绑定来源为{source_kinds}，未绑定出版或会议披露来源；"
             "出版与结果报告分支未纳入本报告。"
    )
    return {
        "declared_fields": declared,
        "extracted_fields": extracted,
        "placeholder_fields": placeholder,
        "unextracted_fields": unextracted,
        "extracted_field_labels": tuple(_field_label(field) for field in extracted),
        "placeholder_field_labels": tuple(_field_label(field) for field in placeholder),
        "unextracted_field_labels": tuple(_field_label(field) for field in unextracted),
        "per_trial_gap_zh": tuple(per_trial_gaps),
        "source_kinds_zh": source_kinds,
        "protocol_closure_zh": protocol_closure,
        "publication_closure_zh": publication_closure,
    }


def _render_page_context(
    data: ReportCPortalData,
    *,
    page: StaticPage,
    catalog: ReportCatalog,
    prefix: str = "",
    current: str | None = None,
    trial: StudyRow | None = None,
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
    # 序列化边界复核：本页嵌入前逐条确认来源追溯合同（model_construct 不豁免）
    assert_evidence_views_serializable(views)
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
        source_routes = sorted({entry["url"] for entry in
                                _external_source_entries(data, data.observations)})
        source_kinds = "、".join(sorted({
            _source_kind_zh(o.source_role.value) for o in data.observations
        }))
        evidence_limitations = {
            "data_cutoff": _text(data.data_cutoff)[:10],
            "source_count": len(
                {_public_source_version(data, o.source_version_id) for o in data.observations}
            ),
            "trial_count": len(data.trials),
            "product_count": len(data.products),
            "fact_count": len(data.observations),
            "source_links": tuple(source_routes),
            "notes": (
                f"本包实际绑定的来源类型为{source_kinds}（数据截止见上）。"
                "此处列示实际来源和覆盖范围，不据此宣称全球或中国竞品检索已闭合；"
                "未提取与未公开应在具体事实中区分，缺失样本量不构成删除研究的理由；"
                "统计语境按原文保留，不将缺失补成零或推断来源中没有的设计。"
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
    # Statistics now has one complete, searchable source comparison plus its
    # folded full table. Do not repeat every paragraph in a second matrix.
    show_design_matrix = catalog_page_id in {"overview", "design-map", "trial-profile"}
    if show_design_matrix:
        design_matrix_rows, design_matrix_groups, design_matrix_trials = _design_matrix(
            data,
            observations,
        )
    else:
        design_matrix_rows, design_matrix_groups, design_matrix_trials = (), (), ()
    workspace = design_comparison_workspace(data, observations)
    snapshot_id = _text(
        data.report_snapshot_id or data.source_evidence_snapshot_id, f"c-{data.report_version}"
    )
    row_set_digest = hashlib.sha256(_canonical_json([o.row_id for o in observations])).hexdigest()
    workspace_json = _json({
        "snapshot_id": snapshot_id,
        "snapshot_kind": ("report" if data.report_snapshot_id else "evidence"
                          if data.source_evidence_snapshot_id else "candidate"),
        "report_snapshot_id": data.report_snapshot_id,
        "source_evidence_snapshot_id": data.source_evidence_snapshot_id,
        "row_set_digest": row_set_digest,
        "membership": workspace["membership"].model_dump(mode="json"),
        "facets": workspace["facets"].model_dump(mode="json"),
        "numeric_eligibility": workspace["numeric_eligibility"].model_dump(mode="json"),
        "columns": workspace["columns"],
    })
    overview_conclusions = None
    if catalog_page_id == "overview" and trial is None:
        n_trials = len({obs.trial_id for obs in observations if obs.trial_id})
        overview_conclusions = [
            {"label": "比较范围", "text": (
                f"围绕 {n_trials} 项注册试验，从试验设计、人群定义、入选标准、"
                "终点与随访时间窗等维度并列呈现登记事实。")},
            {"label": "设计证据", "text": (
                "设计事实按实际绑定来源保留观察定位；模式与权衡并列展示，不作排名。")},
            {"label": "阅读边界", "text": (
                "设计要素差异反映各试验的科学问题不同，不构成优劣判断；"
                "入排与人群定义以登记原文为准。")},
        ]
    return {
        "report": data,
        "evidence_limitations": evidence_limitations,
        "statistics_scope": (
            _statistics_scope(data)
            if catalog_page_id in {"sample-analysis-statistics", "evidence-limitations"}
            else None
        ),
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
        "snapshot_id": snapshot_id,
        "row_set_digest": row_set_digest,
        "design_workspace_json": workspace_json,
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
        # FR20: homepage summary and first-level all-study comparison stay distinct.
        # The comparison entry reuses the existing source-comparison query surface.
        "comparison_href": f"{prefix}overview.html?view=comparison",
        "endpoint_definitions_href": f"{prefix}endpoint-timepoint-matrix.html",
        "show_comparison_entry": catalog_page_id == "overview" and trial is None,
    }


def render_report_c_site(
    data: ReportCPortalData,
    site_root: Path,
    *,
    publication_limitation_zh: str | None = None,
    active_revision: ActiveFactRevision | None = None,
    review_candidate: bool = False,
    identity_context: PortalIdentityContext | None = None,
) -> tuple[Path, ...]:
    """Render C pages; explicit review candidates cannot become current deliveries."""
    site_root = Path(site_root)
    if review_candidate and active_revision is not None:
        raise ReportCPortalError("待复核资料不能消费当前事实修订")
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
                verified_binding = _validate_current_c_binding(data, fact, binding)
            except ValueError as error:
                raise ReportCPortalError(str(error)) from error
            if (fact.model_extra or {}).get("review_state") != "user_modified":
                pages = [page_id for page_id, fields in _PAGE_FIELDS.items()
                         if fields is not None and observations[index].field in fields]
                # Source-only atoms remain visible in their trial detail even
                # when they have no dedicated topical page (same as search).
                source_page = pages[0] if pages else f"trials/{observations[index].trial_id}"
                consumers.append(source_consumer_node(
                    fact, verified_binding, page=f"{source_page}.html",
                ))
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
            if observations[index].field == "planned_or_actual_sample_size":
                threshold = _current_sample_number(fact)
                display_numeric = threshold
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
            consumer_page = (
                f"{specific_pages[0]}.html" if specific_pages
                else f"trials/{observations[index].trial_id}.html"
            )
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
    if not review_candidate:
        _assert_design_gate(data)
    identities = (identity_context.project(data.product_ids, cutoff=data.data_cutoff)
                  if identity_context else {})
    if identities:
        data = data.model_copy(update={"products": tuple(
            product.model_copy(update={"name": identities[product.id]["display_name"]})
            if product.id in identities else product for product in data.products
        )})
    _reset_site_root(site_root)
    _copy_assets(site_root)
    (site_root / "data").mkdir(parents=True, exist_ok=True)
    (site_root / "data/identity-projection.json").write_bytes(_canonical_json(identities))
    if identity_context is not None:
        (site_root / "data/identity-context.json").write_bytes(
            _canonical_json(identity_context.render_binding())
        )
    research_status = "unreviewed_candidate" if review_candidate else "design_gate_passed"
    (site_root / "data/research-status.json").write_bytes(_canonical_json({
        "schema_version": "1.0", "report": "C", "delivery_status": research_status,
    }))

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
        context["current_revision"] = active_revision.revision if active_revision else 0
        context["review_status"] = research_status
        context["identity_headers_html"] = render_identity_headers(identities)
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
        context["current_revision"] = active_revision.revision if active_revision else 0
        context["review_status"] = research_status
        product_ids = {trial.product_id, *(link.product_id for link in trial.product_links)}
        context["identity_headers_html"] = render_identity_headers({
            key: value for key, value in identities.items() if key in product_ids
        })
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

    def add_search_entry(
        title: str, slug: str, *keywords: Any, row_id: str | None = None,
    ) -> None:
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
        entry: dict[str, Any] = {"title": title, "slug": slug, "keywords": values}
        if row_id:
            entry["row_id"] = row_id
        search.append(entry)

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
        specific_page = next(
            (
                page_id for page_id, fields in _PAGE_FIELDS.items()
                if fields is not None and observation.field in fields
            ),
            None,
        )
        # Every trial detail holds its own observations, even if no topical page does.
        route = specific_page or f"trials/{observation.trial_id}"
        add_search_entry(
            f"{_field_label(observation.field)} · {_trial_display(data, observation.trial_id)}",
            route,
            _field_label(observation.field),
            _family_label(observation.field_family),
            observation.source_text,
            observation.display_text,
            observation.threshold_value,
            _trial_name(data, observation.trial_id),
            _product_name(data, observation.product_id),
            observation.row_id,
            row_id=observation.row_id,
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


def render_report_c_review_candidate(
    data: ReportCPortalData,
    site_root: Path,
    *,
    publication_limitation_zh: str | None = None,
    identity_context: PortalIdentityContext | None = None,
) -> tuple[Path, ...]:
    """Render the same C library for review, preserving unresolved/incomplete facts.

    This is not a fourth report, an accepted delivery, or a gate bypass for current.
    The immutable review-only marker is verified by the current publication layer.
    Existing artifacts are never overwritten by this explicit candidate entry.
    """
    site_root = Path(site_root)
    if site_root.is_symlink() or (site_root.exists() and (
        not site_root.is_dir() or any(site_root.iterdir())
    )):
        raise ReportCPortalError("待复核资料需要新的空目录，不覆盖既有证据")
    return render_report_c_site(
        data, site_root, publication_limitation_zh=publication_limitation_zh,
        review_candidate=True,
        identity_context=identity_context,
    )


def validate_active_fact_revision_c(
    data: ReportCPortalData,
    active_revision: ActiveFactRevision,
) -> None:
    """Validate every C binding before a render transaction can begin."""
    for fact, binding in active_revision.bindings_for("C"):
        if binding.collection != "observations":
            raise ReportCPortalError("C renderer只接受observations领域绑定")
        try:
            _validate_current_c_binding(data, fact, binding)
        except ValueError as error:
            raise ReportCPortalError(str(error)) from error
        if (
            binding.endpoint_definition == "planned_or_actual_sample_size"
            and (fact.model_extra or {}).get("review_state") == "user_modified"
        ):
            _current_sample_number(fact)


def _validate_current_c_binding(
    data: ReportCPortalData, fact: ActiveFact, binding: ActiveFactBinding,
) -> ActiveFactBinding:
    """Keep legacy source-row bytes across the proven candidate→accepted projection.

    Only that lifecycle field can differ. Never rewrite stored bindings or relax
    scientific fields, source text, value, disclosure or the shared identity guard.
    """
    actual = active_fact_binding_for_c(data, binding.row_id)
    if actual.original_row_sha256 != binding.original_row_sha256:
        row = next(row for row in data.observations if row.row_id == binding.row_id)
        if row.review_state is FactReviewState.ACCEPTED:
            original = row.model_dump(mode="json")
            original["review_state"] = FactReviewState.CANDIDATE.value
            if canonical_sha256(original) == binding.original_row_sha256:
                actual = actual.model_copy(update={
                    "original_row_sha256": binding.original_row_sha256,
                })
    return validate_active_fact_binding(fact, binding, actual)


def _current_sample_number(fact: ActiveFact) -> float | None:
    """Current sample scalar, not the retained source threshold or an inferred rate."""
    if fact.disclosure_state == "user_cleared":
        return None
    threshold = (fact.model_extra or {}).get("threshold_value")
    value = threshold if threshold is not None else fact.normalized_value
    try:
        number = float(str(value))
        normalized = (float(str(fact.normalized_value))
                      if fact.normalized_value is not None else number)
        exact = Decimal(str(fact.normalized_value if fact.normalized_value is not None else value))
    except (TypeError, ValueError, InvalidOperation) as error:
        raise ReportCPortalError("当前样本量必须为一致的非负整数") from error
    if (isinstance(value, bool) or isinstance(fact.normalized_value, bool)
        or not math.isfinite(number) or number < 0 or not number.is_integer()
        or number != normalized or Decimal(str(number)) != exact):
        raise ReportCPortalError("当前样本量必须为一致的非负整数")
    return number


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
        drug_name=(products[row.product_id].name if row.product_id is not None else None),
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
