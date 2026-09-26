"""Task 6.9: build the complete static B-class comparison portal.

The renderer is deliberately an adapter.  It accepts the compact fixture contract
used by the existing portal tests and, when supplied, consumes the immutable B
view sets produced by Tasks 6.1--6.8.  It does not calculate comparisons,
proportions, denominators, or disclosure states in the browser; those values are
projected into the offline chart payload here.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar, Literal, Self, cast

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ci_workflow.domain.enums import FactDisclosureState, ReportKind
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id
from ci_workflow.qc.browser import route_to_site_path, site_directory_digest
from ci_workflow.reports.b.concept_catalog import SAFETY_CONCEPTS
from ci_workflow.reports.b.portal_science import (
    adjudicate_comparable_membership,
    efficacy_science_partition,
    validate_full_pool_inputs,
)
from ci_workflow.reports.b.semantic_contract import (
    BUBBLE_PRESETS,
    semantic_value_is_unknown,
)
from ci_workflow.reports.b.semantic_grouping import (
    ApprovedSemanticMerge,
    SemanticGroupingProposal,
    proposed_semantic_buckets,
    semantic_row_digest,
    semantic_source_digest,
)
from ci_workflow.reports.common.evidence_view import (
    EvidenceField,
    EvidenceFieldState,
    EvidenceObservationKind,
    EvidenceView,
    OriginalTextStatus,
    assert_evidence_views_serializable,
    clean_evidence_locator,
    field_path_is_precise,
    is_local_path_shape,
    precise_locator_anchor,
)
from ci_workflow.reports.common.numeric_projection import (
    NumericMeasureKind,
    infer_numeric_kind,
    project_numeric,
)
from ci_workflow.reports.common.page_registry import PageRegistry, ReportCatalog, StaticPage
from ci_workflow.reports.common.view_state import ReportRow
from ci_workflow.storage.manifest_store import (
    ArtifactFileBinding,
    ArtifactManifest,
    DesignContractBinding,
    DeterministicCheck,
    RendererBinding,
    RenderVerdict,
)
from ci_workflow.storage.render_transaction import (
    RenderTransactionError,
    UnpublishedRenderTransaction,
)
from ci_workflow.storage.snapshot_store import (
    LockedSnapshot,
    ReportSnapshotManifest,
    SnapshotIntegrityError,
    SnapshotStore,
    compute_locked_snapshot,
)

from .active_fact_projection import (
    ActiveFactBinding,
    ActiveFactRevision,
    PortalConsumerNode,
    canonical_sha256,
    canonical_source_pointer,
    numeric_value,
    user_edit_disclosure,
    validate_active_fact_binding,
    write_render_receipt,
)
from .builder import resolve_echarts_bundle, resolve_logo_src, resolve_portal_asset
from .evidence_drawer import render_evidence_drawer_embed, render_evidence_drawer_host
from .report_a import (
    _ARM_CODE_ZH,
    _POPULATION_TOKENS,
    EfficacyRow,
    ReportAPortalData,
    SafetyRow,
    TrialRow,
    _git_commit,
    _native_timepoint_zh,
)

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates" / "b"
_ASSET_DIR = Path(__file__).resolve().parent / "assets"

# B's static route authority is the frozen catalog.  The tuple below is only a
# dispatch map for page data; it intentionally contains no route strings.
_BASELINE_PAGE_IDS = frozenset(
    {
        "baseline-overview",
        "baseline-demographics",
        "baseline-disease-context",
        "baseline-severity",
    }
)
_BASELINE_PAGE_CONCEPTS: dict[str, frozenset[str]] = {
    "baseline-demographics": frozenset({"age", "sex"}),
    "baseline-disease-context": frozenset({"disease_duration"}),
    "baseline-severity": frozenset({"baseline_easi", "baseline_hemoglobin", "baseline_ldh"}),
}
_BASELINE_STAT_FAMILY = {
    "mean": "central", "median": "central", "other": "central",
    "not_reported": "central",
    "standard_deviation": "spread", "quartiles": "spread", "range": "spread",
    "count": "count", "sample_size": "count", "proportion": "proportion",
}

_DISPOSITION_PAGE_IDS = frozenset(
    {
        "disposition-overview",
        "participant-flow",
        "adherence",
        "loss-exit",
        "screen-failure",
        "rescue-treatment",
        "prohibited-medication",
        "plan-deviation",
    }
)

_DISPOSITION_PAGE_ELEMENTS: dict[str, frozenset[str]] = {
    "disposition-overview": frozenset(
        {
            "已筛选",
            "筛选失败",
            "已随机",
            "已接受治疗",
            "完成治疗",
            "完成研究",
            "停止治疗",
            "退出研究",
            "失访",
            "停止治疗原因",
            "退出研究原因",
        }
    ),
    "participant-flow": frozenset(
        {
            "已筛选",
            "筛选失败",
            "已随机",
            "已接受治疗",
            "完成治疗",
            "完成研究",
            "停止治疗",
            "退出研究",
            "失访",
        }
    ),
    "adherence": frozenset({"依从性"}),
    "loss-exit": frozenset({"停止治疗", "停止治疗原因", "退出研究", "退出研究原因", "失访"}),
    "screen-failure": frozenset({"筛选失败", "筛选失败原因"}),
    "rescue-treatment": frozenset({"补救治疗"}),
    "prohibited-medication": frozenset({"禁用药物"}),
    "plan-deviation": frozenset({"方案偏离", "重要方案偏离", "导致分析集排除的方案偏离"}),
}

_MISSING_STATE_LABELS = {
    "not_reported": "未报告",
    "not_publicly_disclosed": "未公开",
    "not_applicable": "不适用",
    "below_reporting_threshold": "低于报告阈值",
    "unresolved_due_to_route": "路径未解析",
    "conflicting": "来源冲突",
    "conflicting_sources": "来源冲突",
    "user_cleared": "用户清除，待重新核实",
}
_STATE_ALIASES = {
    "已公开": "reported_value",
    "已报告": "reported_value",
    "已报告值": "reported_value",
    "已报告零值": "reported_zero",
    "已报告为零": "reported_zero",
    "未公开": "not_publicly_disclosed",
    "尚未公开": "not_publicly_disclosed",
    "未报告": "not_reported",
    "原文未报告": "not_reported",
    "不适用": "not_applicable",
    "低于报告阈值": "below_reporting_threshold",
    "路径未解析": "unresolved_due_to_route",
    "来源冲突": "conflicting",
    "用户清除，待重新核实": "user_cleared",
}
_CONCRETE_STATES = frozenset({"reported_value", "reported_zero"})
_FILTER_DIMENSION_LABELS = {
    "product": "产品",
    "target": "靶点/机制",
    "trial": "试验",
    "group": "组别",
    "cohort": "队列",
    "period": "阶段/期间",
    "element": "终点/事件/字段",
    "clinical_concept": "标准临床概念",
    "time_window_band": "标准时间窗",
    "population_context": "标准分析人群",
    "statistical_form_family": "标准统计形式",
    "arm_role": "标准组别角色",
    "time": "时间点",
    "time_window": "时间窗",
    "population": "分析人群",
    "field_family": "指标类别",
    "reason": "原因",
    "denominator_role": "分母口径",
    "measure_object": "统计对象",
    "statistic_form": "统计形式",
    "disclosure_state": "披露状态",
}

_NATIVE_LABELS = {
    "c3": "补体C3",
    "c5": "补体C5",
    "factor-d": "补体因子D",
    "factor-b": "因子B",
    "apply-cohort": "APPLY-PNH队列",
    "alpha-safety-cohort": "ALPHA安全性分析队列",
    "appoint-cohort": "APPOINT-PNH队列",
    "pegasus-cohort": "PEGASUS队列",
    "extension-through-week-48": "延长期至第48周",
    "nct03500549-primary-period": "NCT03500549主要研究期",
    "nct04469465-primary-period": "NCT04469465主要研究期",
    "baseline_hgb_eligibility_threshold": "基线血红蛋白入组阈值",
    "treated": "已治疗",
    "period_start": "研究期开始",
    "analysis": "分析",
    "other": "其他",
    "median": "中位数",
    "adherence_summary": "依从性概览",
    "screening-through-week-24": "筛选期至第24周",
    "randomized-through-week-24": "随机至第24周",
    "treatment-through-week-24": "治疗期至第24周",
    "study-through-week-24": "研究期至第24周",
    "baseline_sample_size": "基线样本量",
    "sample_size": "样本量",
    "age": "年龄",
    "sex": "性别",
    "baseline_hemoglobin": "基线血红蛋白",
    "baseline_pnh_clone_size": "PNH 克隆大小",
    "baseline_free_hemoglobin": "游离血红蛋白",
    "baseline_ldh": "基线 LDH",
    "screened": "已筛选",
    "screen_failure": "筛选失败",
    "randomized": "已随机",
    "received_treatment": "已接受治疗",
    "completed_treatment": "完成治疗",
    "completed_study": "完成研究",
    "treatment_discontinued": "停止治疗",
    "study_withdrawal": "退出研究",
    "lost_to_follow_up": "失访",
    "screen_failure_reason": "筛选失败原因",
    "treatment_discontinuation_reason": "停止治疗原因",
    "study_withdrawal_reason": "退出研究原因",
    "adherence": "依从性",
    "rescue_treatment": "补救治疗",
    "prohibited_medication": "禁用药物",
    "protocol_deviation": "方案偏离",
    "major_protocol_deviation": "重要方案偏离",
    "protocol_deviation_leading_to_exclusion": "导致分析集排除的方案偏离",
    "Any treatment-emergent adverse event": "治疗期间出现的任何不良事件",
    "Adverse events of special interest": "特别关注不良事件",
    "Breakthrough haemolysis": "突破性溶血",
    "Discontinuation due to adverse event": "因不良事件停药",
    "Headache": "头痛",
    "Serious adverse reactions": "严重不良反应",
    "Treatment discontinuations due to TEAE": "因治疗期间不良事件停止治疗",
    "source_other": "其他来源",
    "demographics": "人口学特征",
    "baseline_severity": "基线疾病严重程度",
    "reason": "原因",
    "subject": "受试者",
    "mean": "均值",
    "proportion": "比例",
    "count": "例数",
    "response_rate": "应答率",
    "comparable": "可比较",
    "unplottable": "暂不形成坐标",
    "accepted": "已核定",
    "registry_result_or_primary_report": "登记结果或主要试验报告",
    "reported_value": "已报告值",
    "reported_zero": "已报告零值",
    **_MISSING_STATE_LABELS,
}
# ---------------------------------------------------------------------------
# Controlled clinical semantics for cross-trial presentation
# ---------------------------------------------------------------------------

# Presentation grouping is deliberately controlled.  These aliases are not a
# general-purpose similarity matcher: an observation only joins a clinical
# family when its normalized token is explicitly listed here.
_SEMANTIC_TOKEN_RE = re.compile(r"[^0-9a-z\u3400-\u9fff]+")


def _semantic_token(value: Any) -> str:
    if isinstance(value, Enum):
        value = value.value
    if value is None:
        return ""
    text = str(value).strip().casefold()
    text = text.replace("≥", "ge").replace("≤", "le").replace("％", "%")
    return _SEMANTIC_TOKEN_RE.sub("", text)


def _concept_family(*concepts: str) -> frozenset[str]:
    return frozenset(_semantic_token(concept) for concept in concepts)


_BASELINE_CONCEPT_FAMILY_ORDER: tuple[frozenset[str], ...] = (
    _concept_family("baseline_sample_size", "sample_size", "baseline_n", "n"),
    _concept_family("age", "baseline_age", "age_at_baseline"),
    _concept_family("sex", "gender", "baseline_sex", "baseline_gender"),
    _concept_family("disease_duration"),
    _concept_family("baseline_easi", "baseline_hemoglobin", "baseline_ldh"),
)


def _alias_lookup(groups: Mapping[str, Sequence[str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for canonical, aliases in groups.items():
        for alias in (canonical, *aliases):
            token = _semantic_token(alias)
            if not token:
                continue
            existing = result.get(token)
            if existing is not None and existing != canonical:
                raise RuntimeError(f"B 类临床别名冲突：{token}")
            result[token] = canonical
    return result


_CLINICAL_CONCEPT_GROUPS: dict[str, dict[str, tuple[str, ...]]] = {
    "efficacy": {
        "easi75_response": (
            "easi75",
            "easi_75",
            "easi-75",
            "easi75_response",
            "easi 75 response",
            "easi-75 response",
            "easi-75 responder rate",
            "easi75 responder rate",
            "easi-75 应答",
            "easi-75应答者比例",
            "easi75应答率",
            "easi-75 responder proportion",
            "easi75 responder proportion",
            "easi-75应答比例",
            "easi-75 response rate",
            "easi 75 response rate",
            "easi75 response rate",
            "easi-75 responders",
        ),
        "easi90_response": (
            "easi90",
            "easi_90",
            "easi-90",
            "easi90_response",
            "easi-90 response",
            "easi-90 responder rate",
            "easi-90应答",
            "easi-90 response rate",
            "easi 90 response rate",
            "easi90 response rate",
        ),
        "iga_0_1_response": (
            "iga01",
            "iga_0_1",
            "iga 0/1",
            "iga 0 or 1",
            "viga 0/1",
            "viga01",
            "investigator global assessment 0 or 1",
            "iga 0/1 response",
            "viga 0/1 response",
            "viga 0/1 response rate",
            "iga 0/1 response rate",
        ),
        "hemoglobin_response_without_transfusion": (
            "hemoglobin sustained increase without transfusion",
            "hemoglobin increase without transfusion",
            "hemoglobin sustained increase >=2 g/dl without transfusion",
            "hemoglobin sustained increase ge2 g/dl without transfusion",
            "血红蛋白较基线持续升高≥2 g/dL且无需输血",
            "血红蛋白较基线持续升高2g/dl且无需输血",
            "血红蛋白持续升高且无需输血",
            "hemoglobin_response",
            "hemoglobin response",
            "hemoglobin response rate",
            "血红蛋白应答率",
            "hb response",
            "hgb response",
            "hemoglobin response rate without transfusion",
        ),
        "easi_total_score": (
            "easi_total_score",
            "easi total score",
            "easi_total_score_change",
            "easi_total_change",
            "easi total score change",
            "easi总分",
            "easi总分变化",
        ),
        "itch_score": (
            "itch",
            "itch score",
            "peak pruritus nrs",
            "pruritus nrs",
            "瘙痒评分",
            "峰值瘙痒数字评分",
        ),
        "ldh_change": (
            "ldh",
            "ldh change",
            "lactate dehydrogenase",
            "乳酸脱氢酶",
            "乳酸脱氢酶变化",
        ),
        "breakthrough_hemolysis_rate": (
            "breakthrough_hemolysis",
            "breakthrough hemolysis",
            "breakthrough hemolysis rate",
            "突破性溶血",
            "突破性溶血比例",
            "突破性溶血发生率",
        ),
    },
    "baseline": {
        "baseline_sample_size": (
            "sample_size",
            "baseline_n",
            "n",
            "number randomized",
            "基线样本量",
            "样本量",
            "入组人数",
        ),
        "age": ("age", "baseline_age", "age_at_baseline", "年龄", "基线年龄"),
        "sex": ("sex", "gender", "baseline_sex", "baseline_gender", "性别"),
        "baseline_hemoglobin": (
            "baseline hemoglobin",
            "hemoglobin at baseline",
            "hemoglobin",
            "hgb",
            "baseline_hgb",
            "baseline_hgb_actual",
            "血红蛋白",
            "基线血红蛋白",
            "基线血红蛋白实测均值",
        ),
        "baseline_pnh_clone_size": (
            "pnh_clone_size",
            "pnh clone size",
            "clone size",
            "克隆大小",
            "pnh 克隆大小",
        ),
        "baseline_free_hemoglobin": (
            "free_hemoglobin",
            "free hemoglobin",
            "free hgb",
            "游离血红蛋白",
        ),
        "baseline_ldh": (
            "baseline ldh",
            "baseline lactate dehydrogenase",
            "ldh",
            "lactate dehydrogenase",
            "乳酸脱氢酶",
            "基线乳酸脱氢酶",
        ),
        "baseline_easi": (
            "baseline easi",
            "easi at baseline",
            "基线easi",
            "基线easi评分",
        ),
        "disease_duration": (
            "disease duration",
            "duration of disease",
            "病程",
            "疾病持续时间",
        ),
    },
    "safety": {
        "any_teae": (
            "teae",
            "any teae",
            "any treatment emergent adverse event",
            "any treatment-emergent adverse event",
            "any treatment emergent adverse events",
            "any treatment-emergent adverse events",
            "治疗期间不良事件",
            "任何teae",
            "治疗期间出现的任何不良事件",
        ),
        "any_sae": (
            "sae",
            "any sae",
            "saes",
            "serious adverse event",
            "serious adverse events",
            "any serious adverse event",
            "any serious adverse events",
            "严重不良事件",
            "任何sae",
        ),
        "aesi": (
            "aesi",
            "adverse event of special interest",
            "adverse events of special interest",
            "特别关注不良事件",
            "特殊关注不良事件",
        ),
        "common_adverse_event": (
            "common ae",
            "common adverse event",
            "common adverse events",
            "常见不良事件",
        ),
        "treatment_related_teae": (
            "treatment related teae",
            "treatment-related teae",
            "treatment related adverse event",
            "treatment related adverse events",
            "treatment-related adverse events",
            "治疗相关不良事件",
        ),
        "discontinuation_adverse_event": (
            "discontinuation ae",
            "adverse event leading to discontinuation",
            "adverse events leading to discontinuation",
            "discontinuation due to ae",
            "导致停药不良事件",
        ),
        "death": ("death", "deaths", "死亡"),
        "grade_3_or_higher": (
            "grade 3 or higher",
            "grade 3+",
            "grade_3_plus",
            "3级及以上不良事件",
        ),
    },
    "disposition": {
        "screened": ("screened", "screening", "已筛选"),
        "screen_failure": ("screen failure", "screen failures", "筛选失败"),
        "randomized": ("randomized", "randomised", "已随机"),
        "received_treatment": ("received treatment", "treated", "已接受治疗", "已治疗"),
        "completed_treatment": ("completed treatment", "完成治疗"),
        "completed_study": ("completed study", "study completion", "完成研究"),
        "treatment_discontinued": (
            "treatment discontinued",
            "discontinued treatment",
            "停止治疗",
        ),
        "study_withdrawal": ("study withdrawal", "withdrawal", "退出研究"),
        "lost_to_follow_up": ("lost to follow-up", "lost to follow up", "失访"),
        "screen_failure_reason": ("screen failure reason", "筛选失败原因"),
        "treatment_discontinuation_reason": ("treatment discontinuation reason", "停止治疗原因"),
        "study_withdrawal_reason": ("study withdrawal reason", "退出研究原因"),
        "adherence": ("adherence", "treatment adherence", "依从性"),
        "rescue_treatment": ("rescue treatment", "补救治疗"),
        "prohibited_medication": ("prohibited medication", "禁用药", "禁用药物"),
        "protocol_deviation": ("protocol deviation", "方案偏离"),
        "major_protocol_deviation": ("major protocol deviation", "重要方案偏离"),
        "protocol_deviation_leading_to_exclusion": (
            "protocol deviation leading to exclusion",
            "导致分析集排除的方案偏离",
        ),
    },
}
_CLINICAL_CONCEPT_LOOKUPS = {
    domain: _alias_lookup(groups) for domain, groups in _CLINICAL_CONCEPT_GROUPS.items()
}
_CLINICAL_CONCEPT_LABELS = {
    "easi75_response": "EASI-75应答",
    "easi90_response": "EASI-90应答",
    "iga_0_1_response": "IGA 0/1应答",
    "hemoglobin_response_without_transfusion": "血红蛋白持续升高且无需输血",
    "easi_total_score": "EASI总分",
    "itch_score": "瘙痒评分",
    "ldh_change": "乳酸脱氢酶变化",
    "breakthrough_hemolysis_rate": "突破性溶血",
    "baseline_sample_size": "基线样本量",
    "age": "年龄",
    "sex": "性别",
    "baseline_hemoglobin": "基线血红蛋白",
    "baseline_pnh_clone_size": "PNH 克隆大小",
    "baseline_free_hemoglobin": "游离血红蛋白",
    "baseline_ldh": "基线乳酸脱氢酶",
    "baseline_easi": "基线EASI",
    "disease_duration": "病程",
    "any_teae": "任何治疗期间不良事件",
    "any_sae": "任何严重不良事件",
    "aesi": "特别关注不良事件",
    "common_adverse_event": "常见不良事件",
    "treatment_related_teae": "治疗相关不良事件",
    "discontinuation_adverse_event": "导致停药不良事件",
    "death": "死亡",
    "grade_3_or_higher": "3级及以上不良事件",
    "screened": "已筛选",
    "screen_failure": "筛选失败",
    "randomized": "已随机",
    "received_treatment": "已接受治疗",
    "completed_treatment": "完成治疗",
    "completed_study": "完成研究",
    "treatment_discontinued": "停止治疗",
    "study_withdrawal": "退出研究",
    "lost_to_follow_up": "失访",
    "screen_failure_reason": "筛选失败原因",
    "treatment_discontinuation_reason": "停止治疗原因",
    "study_withdrawal_reason": "退出研究原因",
    "adherence": "依从性",
    "rescue_treatment": "补救治疗",
    "prohibited_medication": "禁用药物",
    "protocol_deviation": "方案偏离",
    "major_protocol_deviation": "重要方案偏离",
    "protocol_deviation_leading_to_exclusion": "导致分析集排除的方案偏离",
}

_STATISTICAL_FORM_GROUPS = {
    "response_rate": (
        "response",
        "response rate",
        "responder rate",
        "responder proportion",
        "response proportion",
        "应答率",
        "应答比例",
    ),
    "change_from_baseline": (
        "change",
        "change from baseline",
        "change_from_baseline",
        "baseline change",
        "较基线变化",
        "基线变化值",
        "变化值",
    ),
    "absolute_value": (
        "absolute",
        "absolute value",
        "absolute_value",
        "绝对值",
    ),
    "event_rate": (
        "event rate",
        "incidence",
        "incidence rate",
        "发生率",
        "事件发生率",
    ),
    "time_to_event": ("time to event", "time_to_event", "事件发生时间"),
    "hazard_ratio": ("hazard ratio", "hazard_ratio", "风险比"),
    "mean_difference": ("mean difference", "均值差", "平均值差"),
    "median_difference": ("median difference", "中位数差"),
    "mean": ("mean", "average", "均值", "平均值"),
    "median": ("median", "中位数"),
    "proportion": (
        "proportion", "participant_proportion", "percentage", "percent", "比例", "百分比",
    ),
    "count": ("count", "number", "n", "例数", "人数", "数量"),
    "event_count": ("event count", "event_count", "events", "事件数", "事件计数", "件数"),
    "adherence_summary": ("adherence summary", "adherence_summary", "依从性概览"),
    "other": ("other", "other statistic", "其他统计形式"),
    "range": ("range", "interval", "范围", "区间"),
}
_STATISTICAL_FORM_LOOKUP = _alias_lookup(_STATISTICAL_FORM_GROUPS)
_STATISTICAL_FORM_LABELS = {
    "response_rate": "应答率",
    "change_from_baseline": "较基线变化",
    "absolute_value": "绝对值",
    "event_rate": "事件发生率",
    "time_to_event": "事件发生时间",
    "hazard_ratio": "风险比",
    "mean_difference": "均值差",
    "median_difference": "中位数差",
    "mean": "均值",
    "median": "中位数",
    "proportion": "比例",
    "count": "例数",
    "event_count": "事件数",
    "adherence_summary": "依从性概览",
    "other": "其他统计形式",
    "range": "区间",
    "not_reported": "报告未注明统计口径",
}

_POPULATION_GROUPS = {
    "full_analysis_set": (
        "full analysis set",
        "full analysis population",
        "fas",
        "全分析集",
        "全分析人群",
    ),
    "intention_to_treat": ("itt", "intention to treat", "意向性分析集", "意向治疗集"),
    "per_protocol": ("pp", "per protocol", "符合方案集", "方案符合集"),
    "safety_set": ("safety set", "safety population", "安全性分析集", "安全性人群"),
    "randomized_set": ("randomized set", "randomised set", "随机集", "随机人群"),
    "treated_set": ("treated set", "treated population", "治疗集", "接受治疗人群"),
    "all_participants": ("all participants", "all subjects", "全部受试者", "全体受试者"),
}
_POPULATION_LOOKUP = _alias_lookup(_POPULATION_GROUPS)
_POPULATION_LABELS = {
    "full_analysis_set": "全分析集",
    "intention_to_treat": "意向性分析集",
    "per_protocol": "符合方案集",
    "safety_set": "安全性分析集",
    "randomized_set": "随机集",
    "treated_set": "治疗集",
    "all_participants": "全部受试者",
    "not_reported": "分析人群未列示",
}

_ARM_ROLE_ALIASES = {
    "treatment": "treatment",
    "treated": "treatment",
    "intervention": "treatment",
    "active": "treatment",
    "treatmentarm": "treatment",
    "治疗组": "treatment",
    "治疗臂": "treatment",
    "干预组": "treatment",
    "control": "control",
    "placebo": "control",
    "comparator": "control",
    "controlarm": "control",
    "placeboarm": "control",
    "comparatorarm": "control",
    "对照组": "control",
    "对照臂": "control",
    "安慰剂": "control",
    "单臂": "single_arm",
    "singlearm": "single_arm",
    "singlearmstudy": "single_arm",
    "singlearmtrial": "single_arm",
    "single": "single_arm",
}

_TIME_UNIT_CANONICAL = {
    "d": "day",
    "day": "day",
    "days": "day",
    "日": "day",
    "天": "day",
    "w": "week",
    "wk": "week",
    "week": "week",
    "weeks": "week",
    "周": "week",
    "mo": "month",
    "month": "month",
    "months": "month",
    "月": "month",
    "y": "year",
    "yr": "year",
    "year": "year",
    "years": "year",
    "年": "year",
}
_TIMEPOINT_PATTERN = re.compile(
    r"^(?:约|around|approximately|approx\.?|about|at)?\s*第?\s*(?P<low>[0-9]+(?:\.[0-9]+)?)"
    r"(?:\s*(?:至|-|–|—)\s*(?P<high>[0-9]+(?:\.[0-9]+)?))?"
    r"\s*(?P<unit>日|天|d|day|days|周|w|wk|week|weeks|月|mo|month|months|年|y|yr|year|years)?$",
    re.IGNORECASE,
)
_TIMEPOINT_PREFIX_PATTERN = re.compile(
    r"^(?:约|around|approximately|approx\.?|about|at)?\s*"
    r"(?P<unit>日|天|d|day|days|周|w|wk|week|weeks|月|mo|month|months|年|y|yr|year|years)"
    r"\s*第?\s*(?P<low>[0-9]+(?:\.[0-9]+)?)"
    r"(?:\s*(?:至|-|–|—)\s*(?P<high>[0-9]+(?:\.[0-9]+)?))?$",
    re.IGNORECASE,
)
_TIME_BAND_LABELS = {
    "lteperiod": "长期扩展期",
    "lte_period": "长期扩展期",
    "longterm_extension": "长期扩展期",
    "extension_period": "扩展期",
    "extension": "扩展期",
    "around_day_28": "约第28天",
    "around_week_12": "约第12周",
    "longterm_extension_period_52w": "长期扩展期（52周）",
    "longtermextensionperiod52w": "长期扩展期（52周）",
    "longtermextensionperiod52weeks": "长期扩展期（52周）",
    "longtermextensionlte": "长期扩展期（LTE）",
    "extensionperiod": "扩展期",
    "followup": "随访期",
    "screening": "筛选期",
    "around_month_6": "约6个月",
    "around_year_1": "约1年",
    "baseline": "基线",
    "treatment_period": "治疗期间",
    "follow_up": "随访期",
    "study_period": "研究期间",
    "time_not_reported": "时间点未列示",
}


def _unknown_semantic_key(prefix: str, value: Any) -> str:
    token = _semantic_token(value)
    return f"{prefix}:{token or 'not_reported'}"


def _controlled_concept(
    value: Any,
    *,
    domain: str,
    fallback: Any = None,
) -> tuple[str, str]:
    lookup = _CLINICAL_CONCEPT_LOOKUPS.get(domain, {})
    candidates = (value, fallback)
    first_text = ""
    for candidate in candidates:
        if candidate is None:
            continue
        if not first_text:
            first_text = _text(candidate)
        canonical = lookup.get(_semantic_token(candidate))
        if canonical is not None:
            return canonical, _CLINICAL_CONCEPT_LABELS.get(canonical, _native_text(candidate))
    canonical = _unknown_semantic_key(domain, first_text)
    return canonical, _native_text(first_text, "临床概念未列示")


def _canonical_statistical_form(
    value: Any,
    *,
    domain: str,
    concept: str,
    unit: Any = None,
    numerator: Any = None,
    denominator: Any = None,
) -> tuple[str, str]:
    if domain == "efficacy" and concept == "breakthrough_hemolysis_rate":
        return "event_rate", "事件发生率（越低越好）"
    canonical = _STATISTICAL_FORM_LOOKUP.get(_semantic_token(value))
    if canonical is not None:
        return canonical, _STATISTICAL_FORM_LABELS[canonical]
    unit_token = _text(unit).strip().casefold().replace("％", "%")
    if domain == "safety":
        # 独立复核 B r38（issue-4）：计数与发生率口径分离——
        # 登记只报组别受累人数（例）时不得标成"事件发生率"
        if unit_token in {"例", "人", "count", "名"}:
            return "event_count", "受累人数（例）"
        return "event_rate", _STATISTICAL_FORM_LABELS["event_rate"]
    if domain == "efficacy":
        if concept.endswith("_response") or concept == "hemoglobin_response_without_transfusion":
            return "response_rate", _STATISTICAL_FORM_LABELS["response_rate"]
        if unit_token in {"%", "percent", "percentage"}:
            return "proportion", _STATISTICAL_FORM_LABELS["proportion"]
    if domain == "baseline":
        if concept == "baseline_sample_size":
            return "count", _STATISTICAL_FORM_LABELS["count"]
        if numerator is not None and denominator is not None:
            return "proportion", _STATISTICAL_FORM_LABELS["proportion"]
    if domain == "disposition":
        if unit_token in {"%", "percent", "percentage"}:
            return "proportion", _STATISTICAL_FORM_LABELS["proportion"]
        if unit_token in {"人", "例", "subjects", "participants"}:
            return "count", _STATISTICAL_FORM_LABELS["count"]
    return "not_reported", _STATISTICAL_FORM_LABELS["not_reported"]


def _canonical_population(value: Any) -> tuple[str, str]:
    if value is None or not _text(value):
        return "not_reported", _POPULATION_LABELS["not_reported"]
    canonical = _POPULATION_LOOKUP.get(_semantic_token(value))
    if canonical is not None:
        return canonical, _POPULATION_LABELS[canonical]
    # 独立复核 B r35：登记人群原文走 token 转写，残余英文显式声明
    transcribed = _b_native_label(_text(value))
    if transcribed is not None:
        return _unknown_semantic_key("population", value), transcribed
    return _unknown_semantic_key("population", value), "登记分析人群（定义详见登记来源）"


def _canonical_arm_role(value: Any) -> tuple[str, str]:
    candidates = (value,)
    for candidate in candidates:
        token = _semantic_token(candidate)
        canonical = _ARM_ROLE_ALIASES.get(token)
        if canonical is not None:
            return canonical, {
                "treatment": "治疗组",
                "control": "对照组",
                "single_arm": "单臂",
            }[canonical]
        if any(
            marker in token for marker in ("control", "placebo", "comparator", "对照", "安慰剂")
        ):
            return "control", "对照组"
        if any(marker in token for marker in ("treat", "intervention", "active", "治疗", "干预")):
            return "treatment", "治疗组"
    return "unknown", "组别未列示"


def _time_band(value: Any, explicit_unit: Any = None) -> tuple[str, str]:
    if value is None or not _text(value):
        return "time_not_reported", _TIME_BAND_LABELS["time_not_reported"]
    text = _text(value)
    # 独立复核第三十二轮：EOT 访视（最长暴露 N 周）不是固定评价时点，
    # 不得折算为"第213.4周"
    if "eot" in text.casefold() or "最大暴露" in text:
        return "eot_visit", "治疗结束访视（EOT）"
    # 独立复核 B r42（issue-2）："Maximum exposure: N weeks" 是最长暴露时长，
    # 不得折算为"约第N周"的访视时点
    if re.search(r"maximum\s+exposure", text, re.I):
        return "max_exposure", "最长暴露期（登记）"
    token = _semantic_token(text)
    if any(marker in token for marker in ("baseline", "基线", "screening", "筛选期")):
        return "baseline", _TIME_BAND_LABELS["baseline"]
    if any(marker in token for marker in ("treatmentperiod", "treatment", "治疗期间", "治疗期")):
        return "treatment_period", _TIME_BAND_LABELS["treatment_period"]
    if any(marker in token for marker in ("followup", "follow", "随访")):
        return "follow_up", _TIME_BAND_LABELS["follow_up"]
    if any(marker in token for marker in ("studyperiod", "study", "研究期间")):
        return "study_period", _TIME_BAND_LABELS["study_period"]
    candidate_text = text.replace("months", "month").replace("weeks", "week").replace("days", "day")
    match = _TIMEPOINT_PATTERN.fullmatch(candidate_text)
    if match is None:
        match = _TIMEPOINT_PREFIX_PATTERN.fullmatch(candidate_text)
    if match is None:
        # 独立复核 B r35：登记英文时间窗不得直出，先走确定性中文转写
        return _unknown_semantic_key("time", text), _native_timepoint_zh(text)
    low = float(match.group("low"))
    high = float(match.group("high") or match.group("low"))
    value_num = (low + high) / 2.0
    raw_unit = match.group("unit") or _text(explicit_unit)
    unit = _TIME_UNIT_CANONICAL.get(raw_unit.casefold()) if raw_unit else None
    if unit is None:
        return _unknown_semantic_key("time", text), text
    weeks = {
        "day": value_num / 7.0,
        "week": value_num,
        "month": value_num * 4.34524,
        "year": value_num * 52.1429,
    }[unit]
    if unit == "day" and 26 <= value_num <= 30:
        return "around_day_28", _TIME_BAND_LABELS["around_day_28"]
    if 10 <= weeks <= 14:
        return "around_week_12", _TIME_BAND_LABELS["around_week_12"]
    if 22 <= weeks <= 26.5:
        return "around_month_6", _TIME_BAND_LABELS["around_month_6"]
    if 48 <= weeks <= 56:
        return "around_year_1", _TIME_BAND_LABELS["around_year_1"]
    # 独立复核第二十三轮 veto：天换算的分数周不可读（第36.1429周）——
    # 恰为 1/7 周的整数天时回到天显示，其余小数至多保留一位
    if unit == "week" and value_num % 1 != 0:
        days = value_num * 7
        if abs(days - round(days)) < 0.01:
            unit = "day"
            value_num = round(days)
        else:
            value_num = round(value_num, 1)
    unit_label = {"day": "天", "week": "周", "month": "个月", "year": "年"}[unit]
    shown = f"{value_num:g}"
    if low != high:
        shown = f"{low:g}–{high:g}"
    return f"{unit}_{shown}", f"第{shown}{unit_label}"


def _semantic_projection(value: Any, source: Any, *, domain: str) -> dict[str, str]:
    typed_term_key: str | None = None
    if domain == "efficacy":
        concept_value = _first(
            value,
            "term_key",
            "clinical_concept",
            "construct_id",
            "endpoint_family_label_zh",
            "endpoint_family_id",
            "original_endpoint",
            "original_definition",
            "endpoint_id",
            "endpoint",
            default=None,
        )
        fallback_concept = _first(
            source,
            "term_key",
            "clinical_concept",
            "construct_id",
            "endpoint_family_label_zh",
            "endpoint_family_id",
            "original_endpoint",
            "original_definition",
            "endpoint",
            default=None,
        )
    elif domain == "baseline":
        concept_value = _first(
            value,
            "clinical_concept",
            "standardized_concept",
            "variable_label_zh",
            "variable",
            "source_name",
            "variable_domain",
            default=None,
        )
        fallback_concept = _first(
            source,
            "clinical_concept",
            "standardized_concept",
            "source_name",
            "variable_domain",
            default=None,
        )
    elif domain == "safety":
        typed_term_key = _first(value, "term_key", default=None)
        if typed_term_key is None:
            typed_term_key = _first(source, "term_key", default=None)
        if typed_term_key is not None:
            typed_term_key = _text(typed_term_key)
            if typed_term_key not in SAFETY_CONCEPTS:
                raise ValueError(f"B 安全性 term_key 不在受控 catalog：{typed_term_key}")
        concept_value = _first(
            value,
            "term_key",
            "clinical_concept",
            "standardized_concept",
            "standard_term",
            "source_term",
            "original_term",
            "term",
            "event_term",
            "event",
            "category",
            "family",
            "safety_family",
            default=None,
        )
        fallback_concept = _first(
            source,
            "term_key",
            "clinical_concept",
            "standardized_concept",
            "standard_term",
            "source_term",
            "original_term",
            "term",
            "event_term",
            "event",
            "category",
            "family",
            "safety_family",
            default=None,
        )
    elif domain == "disposition":
        concept_value = _first(
            value,
            "clinical_concept",
            "standardized_concept",
            "field_label_zh",
            "field",
            "source_field_name",
            "field_family",
            default=None,
        )
        fallback_concept = _first(
            source,
            "clinical_concept",
            "standardized_concept",
            "field",
            "source_field_name",
            "field_family",
            default=None,
        )
    else:
        concept_value = _first(
            value,
            "clinical_concept",
            "standardized_concept",
            "label_zh",
            default=None,
        )
        fallback_concept = _first(
            source,
            "clinical_concept",
            "standardized_concept",
            "label_zh",
            default=None,
        )
    if domain == "safety" and typed_term_key is not None:
        concept = typed_term_key
        concept_label = SAFETY_CONCEPTS[typed_term_key].label_zh
    else:
        concept, concept_label = _controlled_concept(
            concept_value if concept_value is not None else fallback_concept,
            domain=domain if domain in _CLINICAL_CONCEPT_LOOKUPS else "efficacy",
            fallback=fallback_concept,
        )
    raw_time = _first(
        value,
        "time_window",
        "time_window_zh",
        "timepoint",
        "actual_timepoint",
        "observed_timepoint",
        "timepoint_value",
        "baseline_timepoint",
        "time",
        default=None,
    )
    if raw_time is None:
        raw_time = _first(
            source,
            "time_window",
            "time_window_zh",
            "timepoint",
            "actual_timepoint",
            "observed_timepoint",
            "timepoint_value",
            "baseline_timepoint",
            "time",
            default=None,
        )
    raw_time_unit = _first(
        value,
        "actual_timepoint_unit",
        "time_unit",
        "observed_time_unit",
        "timepoint_unit",
        default=None,
    )
    if raw_time_unit is None:
        raw_time_unit = _first(
            source,
            "actual_timepoint_unit",
            "time_unit",
            "observed_time_unit",
            "timepoint_unit",
            default=None,
        )
    time_band, time_band_label = _time_band(raw_time, raw_time_unit)
    raw_statistic = _first(
        value,
        "statistical_form_family",
        "statistic_form",
        "statistic_label_zh",
        "analysis_form",
        "effect_measure",
        "measure_object",
        "statistical_form",
        default=None,
    )
    if raw_statistic is None:
        raw_statistic = _first(
            source,
            "statistical_form_family",
            "statistic_form",
            "statistic_label_zh",
            "analysis_form",
            "effect_measure",
            "measure_object",
            "statistical_form",
            default=None,
        )
    statistic, statistic_label = _canonical_statistical_form(
        raw_statistic,
        domain=domain,
        concept=concept,
        unit=_source_first(
            value,
            source,
            "unit",
            "measurement_unit",
            "measure_unit",
            "effect_unit",
            default=None,
        ),
        numerator=_source_first(value, source, "numerator", default=None),
        denominator=_source_first(value, source, "denominator", default=None),
    )
    raw_population = _first(
        value,
        "population_context",
        "analysis_population",
        "analysis_population_zh",
        "population",
        default=None,
    )
    if raw_population is None:
        raw_population = _first(
            source,
            "population_context",
            "analysis_population",
            "analysis_population_zh",
            "population",
            default=None,
        )
    population, population_label = _canonical_population(raw_population)
    raw_arm = _first(
        value,
        "arm_role",
        "group_role",
        "arm_type",
        "arm_label",
        "group_label",
        "group_label_zh",
        "arm",
        "group",
        "arm_id",
        "group_id",
        default=None,
    )
    if raw_arm is None:
        raw_arm = _first(
            source,
            "arm_role",
            "group_role",
            "arm_type",
            "arm_label",
            "group_label",
            "group_label_zh",
            "arm",
            "group",
            "arm_id",
            "group_id",
            default=None,
        )
    arm_role, arm_label = _canonical_arm_role(raw_arm)
    return {
        "clinical_concept": concept,
        "clinical_concept_label_zh": concept_label,
        "time_window_band": time_band,
        "time_window_band_label_zh": time_band_label,
        "statistical_form_family": statistic,
        "statistical_form_family_label_zh": statistic_label,
        "population_context": population,
        "population_context_label_zh": population_label,
        "arm_role": arm_role,
        "arm_role_label_zh": arm_label,
    }


class ReportBPortalError(ValueError):
    """B 类门户输入、视图适配或物理站点构建失败。"""


class ReportBSafetyRow(SafetyRow):
    """B 类安全性行允许显式保存非数值披露状态及其医学原因。"""

    disclosure_state: Literal["已公开", "未公开", "不适用", "用户清除，待重新核实"] = "已公开"
    reason_zh: str | None = None


class TypedNumericProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    projection_version: Literal["canonical_numeric_projection_v1"]
    kind: NumericMeasureKind
    raw_value: float
    raw_unit: str
    plot_value: float
    plot_unit: str
    numerator: float | None = None
    denominator: float | None = None
    direction: str = ""
    window: str
    estimand: str
    facet_key: str
    renderable: Literal[True]
    size_basis: str | None = None

    @model_validator(mode="after")
    def _matches_canonical_projection(self) -> Self:
        canonical = project_numeric(
            value=self.raw_value,
            unit=self.raw_unit,
            kind=self.kind,
            numerator=self.numerator,
            denominator=self.denominator,
            direction=self.direction,
            window=self.window,
            estimand=self.estimand,
            size_basis=self.size_basis,
        )
        if not canonical.renderable or canonical.plot_value is None:
            raise ValueError("矩阵投影原始输入不能形成可绘 canonical projection")
        if not math.isclose(self.plot_value, canonical.plot_value, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("矩阵 plot_value 与 canonical projection 不一致")
        if self.plot_unit != canonical.plot_unit or self.facet_key != canonical.facet_key:
            raise ValueError("矩阵单位或 facet 不是由 canonical projection 重算所得")
        return self


class TypedMatrixComparison(BaseModel):
    """Closed matrix input: no absolute x/y override and no inferred control."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    comparison_row_id: str
    product_id: str
    trial_id: str
    treatment_projection: TypedNumericProjection
    control_projection: TypedNumericProjection
    safety_projection: TypedNumericProjection
    size_projection: TypedNumericProjection

    @model_validator(mode="after")
    def _compatible(self) -> Self:
        treatment = self.treatment_projection
        control = self.control_projection
        if any(
            getattr(treatment, field) != getattr(control, field)
            for field in ("kind", "plot_unit", "direction", "window", "estimand", "facet_key")
        ):
            raise ValueError("矩阵治疗组与对照组投影口径不兼容")
        if self.safety_projection.kind is not NumericMeasureKind.PARTICIPANT_PROPORTION:
            raise ValueError("矩阵安全轴必须是参与者比例")
        if self.safety_projection.plot_unit != "%":
            raise ValueError("矩阵安全轴单位必须为 %")
        if self.size_projection.kind not in {
            NumericMeasureKind.SAMPLE_SIZE, NumericMeasureKind.PARTICIPANT_COUNT,
        }:
            raise ValueError("矩阵气泡大小必须是明确人数口径")
        if self.size_projection.plot_unit != "人":
            raise ValueError("矩阵气泡大小单位必须为人")
        if (
            self.size_projection.plot_value <= 0
            or not float(self.size_projection.plot_value).is_integer()
        ):
            raise ValueError("矩阵气泡大小必须是正整数人数")
        if self.size_projection.size_basis not in {
            "治疗组安全性分析人数",
            "治疗组样本量",
        }:
            raise ValueError("矩阵气泡大小必须使用批准且非空的 size_basis")
        return self


class TypedMatrixView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    rows: tuple[TypedMatrixComparison, ...]


class ReportBPortalData(ReportAPortalData):
    """B 类门户输入合同。

    The legacy report-data rows remain the minimum fixture contract.  Optional
    immutable view sets are accepted under their Task 6.1--6.8 names so a real
    B snapshot can be rendered without moving scientific projection into this
    module's templates or JavaScript.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)
    require_a_result_completeness: ClassVar[bool] = False

    safety: tuple[ReportBSafetyRow, ...] = Field(min_length=1)
    report_snapshot_id: str | None = None
    # 视图容器按结构化映射接收；任意对象（字符串/列表/模型实例）在边界被拒，
    # 使 schema 漂移在此暴露而不是深入渲染后才失败。
    efficacy_views: Mapping[str, Any] | None = None
    safety_views: Mapping[str, Any] | None = None
    baseline_views: Mapping[str, Any] | None = None
    disposition_views: Mapping[str, Any] | None = None
    supporting_evidence_views: Mapping[str, Any] | None = None
    supporting_views: Mapping[str, Any] | None = None
    subgroup_views: Mapping[str, Any] | None = None
    subgroups_views: Mapping[str, Any] | None = None
    matrix_view: TypedMatrixView | None = None
    matrix_views: TypedMatrixView | None = None
    views: Mapping[str, Any] | None = None
    view_states: Mapping[str, Any] | None = None
    semantic_proposals: tuple[SemanticGroupingProposal, ...] = Field(
        default=(), exclude_if=lambda value: not value,
    )
    semantic_adjudications: tuple[ApprovedSemanticMerge, ...] = Field(
        default=(), exclude_if=lambda value: not value,
    )

    @model_validator(mode="after")
    def _snapshot_is_not_blank(self) -> Self:
        if self.report_snapshot_id is not None and not self.report_snapshot_id.strip():
            raise ValueError("B 类报告锁定快照标识不得为空")
        return self


def load_report_b_data(path: Path) -> ReportBPortalData:
    """读取并校验 B 类门户数据包。"""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReportBPortalError(f"无法读取 B 类报告数据：{path}") from exc
    try:
        data = ReportBPortalData.model_validate(payload)
    except ValueError as exc:
        raise ReportBPortalError(f"B 类报告数据不符合合同：{exc}") from exc
    return _scrub_declared_shadow_rows(data)


def _row_is_declared_shadow(row: object) -> bool:
    """会商 round-4 #4：影子行识别——row_id 在投影/规范化环节可能被再生，
    fact_id 与 source_row_id 保留 "-declared" 后缀，三字段任一命中即判。"""
    for field in ("row_id", "fact_id", "source_row_id"):
        value = (
            row.get(field)
            if isinstance(row, dict)
            else getattr(row, field, None)
        )
        if value and str(value).endswith("-declared"):
            return True
    return False


def _scrub_declared_shadow_rows(data: ReportBPortalData) -> ReportBPortalData:
    """会商 round-4 #4（B r57/r58/r59/r60）：-declared 影子行在门户数据
    入口一次性清洗。投影会再生 row_id，后置过滤不可靠；此处先于一切
    消费者（页面/分组/证据视图/筛选）生效。包内容量不受影响（1:1 合同
    在提交校验层已履行）。"""
    updates: dict[str, Any] = {}
    for field in ("baseline_views", "safety_views", "efficacy_views", "disposition_views"):
        view = getattr(data, field, None)
        if not isinstance(view, Mapping) or "facts" not in view:
            continue
        facts = view["facts"]
        if isinstance(facts, Sequence) and not isinstance(facts, str):
            kept = tuple(
                row for row in facts if not _row_is_declared_shadow(row)
            )
            if len(kept) != len(facts):
                updates[field] = dict(view)
                updates[field]["facts"] = kept
    # 独立复核 B r61（issue-2）：report.js 嵌入数据来自 legacy 顶层列表，
    # 同样清洗（合同 1:1 在提交校验层已履行，渲染副本不受限）
    for field in ("safety", "baseline", "efficacy", "disposition"):
        rows = getattr(data, field, None)
        if rows is None or isinstance(rows, (str, Mapping)):
            continue
        if isinstance(rows, Sequence):
            kept = tuple(row for row in rows if not _row_is_declared_shadow(row))
            if len(kept) != len(rows):
                updates[field] = kept
    if updates:
        return data.model_copy(update=updates)
    return data


_BASELINE_REQUIREMENTS = {
    "baseline_sample_size": ("b_baseline_sample_size", "样本量"),
    "age": ("b_baseline_age", "年龄"),
    "sex": ("b_baseline_sex", "性别"),
    "baseline_severity": ("b_baseline_severity_anchor", "疾病严重程度"),
}


def report_b_baseline_gate_failures(data: ReportBPortalData) -> tuple[dict[str, str], ...]:
    """逐核心试验逐组检查 D70 四类基线事实，不跨组借值。"""
    baseline_source = _get(data.baseline_views, "facts", ())
    disposition_source = _get(data.disposition_views, "facts", ())
    baseline_facts = tuple(item for item in baseline_source if isinstance(item, Mapping))
    disposition_facts = tuple(item for item in disposition_source if isinstance(item, Mapping))
    core_trials = {
        trial.id: trial
        for trial in data.trials
        if "支持" not in trial.role and "事后" not in trial.role
    }
    groups_by_trial: dict[str, set[str]] = defaultdict(set)
    for fact in (*baseline_facts, *disposition_facts):
        trial_id = _text(fact.get("trial_id"))
        group_id = _text(fact.get("group_id"))
        if trial_id in core_trials and group_id:
            groups_by_trial[trial_id].add(group_id)

    concepts: dict[tuple[str, str], set[str]] = defaultdict(set)
    for fact in baseline_facts:
        trial_id = _text(fact.get("trial_id"))
        group_id = _text(fact.get("group_id"))
        if trial_id not in core_trials or not group_id:
            continue
        concept = _text(fact.get("standardized_concept"))
        if _text(fact.get("variable_domain")) == "baseline_severity":
            concepts[(trial_id, group_id)].add("baseline_severity")
        if concept in {"baseline_sample_size", "sample_size", "baseline_n", "n"}:
            concepts[(trial_id, group_id)].add("baseline_sample_size")
        elif concept in {"age", "baseline_age", "age_at_baseline"}:
            concepts[(trial_id, group_id)].add("age")
        elif concept in {"sex", "gender", "baseline_sex", "baseline_gender"}:
            concepts[(trial_id, group_id)].add("sex")

    failures: list[dict[str, str]] = []
    for trial_id, trial in sorted(core_trials.items()):
        groups = sorted(groups_by_trial.get(trial_id) or {"未识别组别"})
        for group_id in groups:
            present = concepts.get((trial_id, group_id), set())
            for concept, (failure_code, label) in _BASELINE_REQUIREMENTS.items():
                if concept in present:
                    continue
                failures.append(
                    {
                        "failure_code": failure_code,
                        "trial_id": trial_id,
                        "trial": trial.display_id,
                        "group_id": group_id,
                        "field": concept,
                        "field_zh": label,
                    }
                )
    return tuple(failures)


# ---------------------------------------------------------------------------
# Small deterministic adaptation helpers
# ---------------------------------------------------------------------------

_MISSING = object()


def _get(value: Any, name: str, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, Mapping):
        return value.get(name, default)
    try:
        return getattr(value, name)
    except (AttributeError, TypeError):
        return default


def _first(value: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        candidate = _get(value, name, _MISSING)
        if candidate is not _MISSING and candidate is not None:
            return candidate
    return default


def _enum_value(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def _text(value: Any, default: str = "") -> str:
    value = _enum_value(value)
    if value is None:
        return default
    if isinstance(value, str) and value.strip() in {"None", "null"}:
        # 独立复核 B r38（issue-1/2）：投影链产生的字面 "None" 字符串按缺失处理
        return default
    result = " ".join(str(value).split())
    return result or default


_B_VARIABLE_TOKENS: tuple[tuple[str, str], ...] = (
    (r"free[_ ]?hemoglobin", "游离血红蛋白"),
    (r"\bdiarrhoea\b", "腹泻"),
    (r"\bcohort\s*(\d+)\b", r"第\1组"),
    (r"\babsolute\b", "绝对值"),
    (r"\bgroup\s*(\d+)\b", r"第\1组"),
    (r"\bTP(\d+)\b", r"治疗期\1"),
    (r"\bLTE\b", "长期扩展期"),
    (r"treatment[- ]naive", "初治"),
    (r"treatment[- ]experienced", "经治"),
    (r"eculizumab switch", "换用依库珠单抗"),
    (r"rollover", "延续入组"),
    (r"\btreatment naive arm\b", "初治臂"),
    (r"\bsex\b|\bgender\b", "性别"),
    (r"\bage\b", "年龄"),
    (r"\brace\b", "种族"),
    (r"\bethnicity\b", "民族"),
    (r"\bweight\b", "体重"),
    (r"\bheight\b", "身高"),
    (r"\bbody mass index\b|\bbmi\b", "体质指数（BMI）"),
    (r"\bcompleted?\b", "完成"),
    (r"\bdiscontinued?\b", "提前终止"),
    (r"\bwithdrawn\b", "退出"),
    (r"\bdeaths?\b|\bdied\b", "死亡"),
    (r"\badverse events?\b|\baes?\b", "不良事件"),
    (r"\bserious\b", "严重"),
    (r"\binfections?\b", "感染"),
    (r"\breason\b", "原因"),
    (r"\black of (?:efficacy|effect)\b", "疗效不足"),
)


def _b_native_label(text: str) -> str | None:
    """B 类标签确定性转写漏斗：字面映射 → 变量 token → 人群 token。

    返回 None 表示残余英文过多、无法诚实转写，由调用方选择显式声明。
    """
    out = _text(text)
    if not out:
        return out
    out = _NATIVE_LABELS.get(out, out)
    out = out.replace("Other events", "其他不良事件")
    # 括号配平提前：纯中文串也可能带孤立括号（B r50 issue-3）
    cleaned_chars = []
    depth = 0
    for ch in out:
        if ch == "（":
            depth += 1
            cleaned_chars.append(ch)
        elif ch == "）":
            if depth > 0:
                depth -= 1
                cleaned_chars.append(ch)
        else:
            cleaned_chars.append(ch)
    out = "".join(cleaned_chars)
    if not re.search(r"[A-Za-z]{3,}", out):
        return out
    for pattern, rep in _B_VARIABLE_TOKENS:
        out = re.sub(pattern, rep, out, flags=re.I)
    for pattern, population_rep in _POPULATION_TOKENS:
        out = re.sub(pattern, population_rep, out, flags=re.I)
    out = re.sub(r"\s*and\s*", "、", out, flags=re.I)
    out = re.sub(r",\s*", "、", out)
    out = re.sub(r"\(\s*", "（", out)
    out = re.sub(r"\s*\)", "）", out)
    out = re.sub(r"(?<=[\u4e00-\u9fff]) (?=[\u4e00-\u9fff])", "", out)
    # 括号配平：按深度丢弃孤立右括号（"（第28天））"类残缺）
    cleaned_chars = []
    depth = 0
    for ch in out:
        if ch == "（":
            depth += 1
            cleaned_chars.append(ch)
        elif ch == "）":
            if depth > 0:
                depth -= 1
                cleaned_chars.append(ch)
            # 深度为 0 的孤立右括号直接丢弃
        else:
            cleaned_chars.append(ch)
    out = "".join(cleaned_chars)
    out = re.sub(r"\s{2,}", " ", out).strip(" 、（")
    residual = [w for w in re.findall(r"[A-Za-z]{3,}", out) if not w.isupper()]
    if len(residual) >= 2:
        return None
    return out


def _native_text(value: Any, default: str = "") -> str:
    text = _text(value, default)
    transcribed = _b_native_label(text)
    return text if transcribed is None else transcribed


def _iter_values(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        return (value,)
    if isinstance(value, Mapping):
        return (value,)
    try:
        return tuple(value)
    except TypeError:
        return (value,)


def _collection(source: Any, *names: str) -> tuple[Any, ...]:
    if source is None:
        return ()
    if isinstance(source, (list, tuple, set, frozenset)):
        return tuple(source)
    for name in names:
        candidate = _get(source, name, _MISSING)
        if candidate is not _MISSING and candidate is not None:
            return _iter_values(candidate)
    return ()


def _flatten_view_rows(values: Sequence[Any]) -> tuple[Any, ...]:
    result: list[Any] = []
    nested_names = (
        "complete_table",
        "table_rows",
        "fact_rows",
        "selected_facts",
        "facts",
        "effect_rows",
        "rows",
    )
    for value in values:
        nested = _collection(value, *nested_names)
        if nested:
            result.extend(nested)
        else:
            result.append(value)
    return tuple(result)


def _number(value: Any) -> int | float | None:
    value = _enum_value(value)
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value
    if isinstance(value, Mapping):
        for key in ("value", "numeric_value", "number"):
            if key in value:
                return _number(value[key])
    nested = _get(value, "value", _MISSING)
    if nested is not _MISSING and nested is not value:
        return _number(nested)
    return None


def _reported_numeric(row: Mapping[str, Any]) -> int | float | None:
    """证据视图展示的“值”＝原始报告值，而不是派生绘图值。

    ``_project_record`` 把 ``raw_numeric_value`` 保存为原始报告值、``numeric_value``
    保存为绘图投影值（不可绘图时为 None）。不可绘图不等于未报告：原始数值必须
    仍可展示，缺失仍由互斥状态表达。
    """
    for name in ("raw_numeric_value", "value", "numeric_value"):
        candidate = _number(row.get(name))
        if candidate is not None:
            return candidate
    return None


def _state(value: Any, numeric: int | float | None) -> str:
    value = _enum_value(value)
    if value is not None:
        state = _STATE_ALIASES.get(str(value), str(value))
    else:
        state = "reported_value" if numeric is not None else "not_reported"
    if numeric is None and state in _CONCRETE_STATES:
        return "not_reported"
    return state


def _state_label(state: str) -> str:
    return {
        "reported_value": "已报告值",
        "reported_zero": "已报告零值",
        **_MISSING_STATE_LABELS,
    }.get(state, "已报告")


def _json(value: Any) -> str:
    """Encode inline JSON safely for a file:// script block."""
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


def _view_source(data: ReportBPortalData, name: str) -> Any:
    candidates = [name]
    aliases = {
        "supporting_evidence_views": (
            "supporting_views",
            "subgroup_views",
            "subgroups_views",
            "supporting_evidence",
            "subgroups",
        ),
    }
    candidates.extend(aliases.get(name, ()))
    if name.endswith("_views"):
        candidates.append(name.removesuffix("_views"))
    if name == "matrix_view":
        candidates.append("matrix_views")
    for candidate_name in candidates:
        candidate = _get(data, candidate_name, None)
        if candidate is not None:
            return candidate
    for container_name in ("views", "view_states"):
        container = _get(data, container_name, None)
        if isinstance(container, Mapping):
            for candidate_name in candidates:
                if candidate_name in container and container[candidate_name] is not None:
                    return container[candidate_name]
    return None


def _unwrap_fact(value: Any) -> Any:
    for name in ("fact", "observation", "original_observation"):
        nested = _get(value, name, _MISSING)
        if nested is not _MISSING and nested is not None:
            return nested
    return value


def _stable_row_id(value: Any, fallback: str) -> str:
    candidate = _first(
        value,
        "row_id",
        "fact_row_id",
        "fact_version_id",
        "comparison_row_id",
        "source_row_id",
        "id",
        default=None,
    )
    return _text(candidate, fallback)


def _source_row_id(value: Any, fallback: str) -> str:
    return _text(
        _first(value, "source_row_id", "source_row", "source_line_id", "row_ref", default=None),
        fallback,
    )


def _product_id(value: Any) -> str:
    return _text(_first(value, "product_id", "project_id", default=""))


def _trial_id(value: Any) -> str:
    return _text(_first(value, "trial_id", "study_id", default=""))


def _label_for(value: Any, domain: str) -> str:
    if domain == "efficacy":
        candidate = _first(
            value,
            "endpoint_family_label_zh",
            "endpoint_label_zh",
            "family_label_zh",
            "original_endpoint",
            "endpoint",
            "endpoint_family_id",
            default=None,
        )
        label = _native_text(candidate, "疗效指标")
        # 独立复核第二十三轮 veto：通用兜底族标签（"未分类登记观察"）不得
        # 顶替登记终点身份——此类行直接以登记原文为显示标签
        family_id = _text(_first(value, "endpoint_family_id", default=""))
        if "generic-unclassified" in family_id or label in ("未分类登记观察", "登记通用观察"):
            original = _text(_first(
                value,
                "original_definition",
                "endpoint_definition",
                "original_endpoint",
                "endpoint",
                default="",
            ))
            if original:
                return original
        return label
    if domain == "safety":
        measured_class = _text(_first(value, "source_class_title", default=""))
        typed_key = _text(_first(value, "term_key", default=""))
        if measured_class and typed_key in SAFETY_CONCEPTS:
            return SAFETY_CONCEPTS[typed_key].label_zh
        candidate = _first(
            value,
            "standard_term",
            "source_term",
            "term",
            "event_term",
            "category",
            "family",
            default=None,
        )
        return _native_text(candidate, "安全性事件")
    if domain == "baseline":
        candidate = _first(
            value,
            "variable_label_zh",
            "standardized_concept",
            "source_name",
            "variable_domain",
            default=None,
        )
        text = _native_text(candidate, "基线变量")
        # 独立复核第二十轮 veto：内部概念键（pnh_clone_size 等）不得直出为
        # 图表类别标签；snake_case 令牌映射为中文概念名
        if re.fullmatch(r"[a-z0-9_]+", text):
            text = _BASELINE_CONCEPT_TOKEN_ZH.get(text, text)
        return text
    if domain == "disposition":
        candidate = _first(
            value,
            "field_label_zh",
            "field",
            "source_field_name",
            "field_family",
            default=None,
        )
        return _native_text(candidate, "试验完成情况")
    candidate = _first(value, "display_label_zh", "name", "label_zh", default=None)
    return _native_text(candidate, "研究记录")


def _is_pure_role_label(raw: str) -> bool:
    """登记组名本身即纯角色词（Placebo/Treatment/…）才允许角色归一。

    复合登记名（Placebo-Danicopan、Group 1: Treatment Naive、Cohort 1）
    含药物/队列身份，归一会抹平登记组别（第二十四轮 veto）。
    """
    tokens = {t for t in re.split(r"[^a-z0-9]+", raw.casefold()) if t}
    role_tokens = tokens & {
        "placebo", "active", "control", "comparator", "treatment",
        "treated", "experimental", "arm", "group", "cohort", "therapy",
    }
    allowed_suffixes = {"matching", "dose", "a", "b", "c", "1", "2", "3", "4"}
    return bool(role_tokens) and tokens <= role_tokens | allowed_suffixes


def _arm_code_zh(code: str) -> str:
    """组标识中的药名/角色代码 → 展示名（拉丁药名按登记惯例保留）。"""
    if code.casefold() == "placebo":
        return "安慰剂"
    known = _ARM_CODE_ZH.get(code.upper())
    if known:
        return known
    out = _b_native_label(code) or code
    return out[:1].upper() + out[1:] if out and out[0].isalpha() else out


def _decode_arm_identifier(identifier: str) -> str | None:
    """组标识 → 中文序数标签（第N组/第N期/长期扩展期）；未命中返回 None。

    独立复核 B r51/r55/r56：行标签与图表系列标签共用本解码，
    SVG 文本层与表格不再各说各话。"""
    human = re.sub(r"^nct[0-9]+-arm-", "", identifier.casefold()).replace("-", " ").strip()
    if not human:
        return None
    canonical, canonical_label = _canonical_arm_role(human)
    if canonical != "unknown" and _is_pure_role_label(human):
        return canonical_label
    m_cohort = re.fullmatch(r"cohort\s*(\d+)", human, re.I)
    if m_cohort:
        return f"第{m_cohort.group(1)}组"
    m_group = re.fullmatch(r"group\s*(\d+)(?:\s+(.*))?", human, re.I)
    if m_group:
        qualifier = _b_native_label(m_group.group(2) or "") if m_group.group(2) else ""
        base = f"第{m_group.group(1)}组"
        return f"{base}（{qualifier}）" if qualifier else base
    m_tp = re.search(r"(?:^|\s)([a-z0-9]+)\s*tp(\d+)$", human)
    if m_tp:
        return f"第{m_tp.group(2)}期 {_arm_code_zh(m_tp.group(1))}"
    m_lte = re.search(r"(?:^|\s)([a-z0-9]+)\s*lte$", human)
    if m_lte:
        return f"长期扩展期 {_arm_code_zh(m_lte.group(1))}"
    return None


def _arm_label(value: Any) -> str:
    candidate = _first(value, "arm_label", "group_label", "group_label_zh", "arm", default=None)
    if candidate is not None:
        raw = _text(_enum_value(candidate))
        canonical, canonical_label = _canonical_arm_role(raw)
        # 角色归一仅当登记名本身是纯角色词（第二十四轮 veto：复合登记名
        # 中的 placebo/treat 子串不得触发归一）；登记专名一律保留原文
        if canonical != "unknown" and _is_pure_role_label(raw):
            return canonical_label
        if raw:
            # 独立复核 B r56（issue-3）：纯英文复合组名（如 "Placebo (TP1)"）
            # 先按组标识解码为第N期/第N组序数标签，与图表层同源；未命中
            # 解码模式的登记专名仍保留原文（第二十四轮 veto 口径不变）
            if not re.search(r"[\u4e00-\u9fff]", raw):
                decoded = _decode_arm_identifier(
                    _text(_first(value, "group_id", "arm_id", "cohort_id", default=""))
                )
                if decoded is not None:
                    return decoded
            return raw
    role = _text(_first(value, "arm_role", "group_role", "arm_type", default=""))
    canonical, canonical_label = _canonical_arm_role(role)
    if canonical != "unknown":
        return canonical_label
    identifier = _text(_first(value, "group_id", "arm_id", "cohort_id", default=""))
    # 第二十四轮 veto：无登记名时回退解码组标识本身，
    # 不得折叠为"全研究人群/对照组"等泛化角色
    decoded = _decode_arm_identifier(identifier)
    if decoded is not None:
        return decoded
    human = re.sub(r"^nct[0-9]+-arm-", "", identifier.casefold()).replace("-", " ").strip()
    return human or "组别未列示"


def _category_for(value: Any, domain: str, arm: str) -> str:
    if domain != "safety":
        return arm
    category = _text(
        _first(value, "category", "family", "event_family", "safety_family", default=""),
        "安全性事件",
    )
    aliases = {
        "teae": "治疗期间不良事件",
        "sae": "严重不良事件",
        "aesi": "特别关注不良事件",
        "common_ae": "常见不良事件",
        "death": "死亡",
        "grade_3_plus": "3级及以上不良事件",
        "discontinuation_ae": "导致停药不良事件",
        "treatment_related_teae": "治疗相关不良事件",
    }
    return aliases.get(category.casefold(), category)


def _time_label(value: Any) -> str:
    raw_time_text = _text(_first(
        value,
        "timepoint",
        "actual_timepoint",
        "observed_timepoint",
        "timepoint_value",
        "time_window_zh",
        "time_window",
        default=None,
    ))
    # 独立复核第三十二轮：登记原文含 EOT 访视语义时显示访视名，
    # 不把"最长暴露 213.4 周"折算为固定周数
    if "eot" in raw_time_text.casefold():
        return "治疗结束访视（EOT）"
    candidate = raw_time_text
    if not candidate:
        return "时间点未列示"
    unit = _first(value, "actual_timepoint_unit", "time_unit", "timepoint_unit", default=None)
    # 独立复核 B r37（issue-1）：candidate 已被 _text 字符串化，
    # 数字+单位必须在此恢复数值路径；分数周回读为整数天
    numeric = None
    if unit:
        try:
            numeric = float(candidate)
        except (TypeError, ValueError):
            numeric = None
    if unit and numeric is not None:
        unit_key = _text(unit).casefold()
        unit_zh = {
            "day": "天", "days": "天", "week": "周", "weeks": "周",
            "month": "个月", "months": "个月", "year": "年", "years": "年",
        }.get(unit_key, _text(unit))
        if "week" in unit_key and abs(numeric * 7 - round(numeric * 7)) < 0.01:
            return f"第{round(numeric * 7):g}天"
        if numeric == int(numeric):
            return f"第{int(numeric):g}{unit_zh}"
        return f"约第{round(numeric, 1):g}{unit_zh}"
    return _text(candidate, "时间点未列示")


def _value_for(value: Any) -> int | float | None:
    candidate = _first(
        value,
        "numeric_value",
        "observed_value",
        "value",
        "reported_proportion",
        "effect_value",
        "raw_numeric_value",
        default=None,
    )
    return _number(candidate)


def _unit_for(value: Any, default: str = "") -> str:
    return _text(
        _first(
            value,
            "unit",
            "measurement_unit",
            "measure_unit",
            "effect_unit",
            default=default,
        )
    )


def _source_version(value: Any) -> str | None:
    return _text(
        _first(value, "source_version_id", "source_version", "captured_version", default=None)
    ) or None


def _exact_source_locator(value: Any) -> EvidenceLocator | None:
    """精确、非本机的来源锚点；本机路径字段被去除，弱锚点一律返回 None。

    独立会商 R24-25 FAIL 复现：绝对路径、UNC、上跳相对路径与仅链接/仅章节
    曾被当作精确定位。此处只保留字段、页、表、行、列、段落锚点，且字段路径
    必须是具体测量/字段（``$.`` 一类粗容器不算）。同一位置对象里若另有好锚点，
    仅移除携带本机路径的脏字段，不丢弃整个定位。
    """
    candidate = _first(value, "source_locator", "locator", "source_location", default=None)
    if isinstance(candidate, (EvidenceLocator, Mapping)):
        locator = clean_evidence_locator(candidate)
        if locator is None or precise_locator_anchor(locator) is None:
            return None
        return locator
    # Existing source-bound builder inputs carry the exact JSON field directly.
    # It is a source pointer, not evidence that the source is a registry or has
    # a public URL; neither property may be inferred from a trial identifier.
    raw_field_path = _first(value, "source_field_path", default=None)
    field_path = raw_field_path if isinstance(raw_field_path, str) else ""
    field_path = _text(field_path)
    if field_path and not is_local_path_shape(field_path) and field_path_is_precise(field_path):
        return EvidenceLocator(document_role="source_record", field_path=field_path)
    return None


def _source_first(value: Any, source: Any, *names: str, default: Any = None) -> Any:
    candidate = _first(value, *names, default=_MISSING)
    if candidate is not _MISSING and candidate is not None:
        return candidate
    return _first(source, *names, default=default)


def _project_record(
    value: Any,
    *,
    domain: str,
    names: Mapping[str, str],
    trial_names: Mapping[str, str],
    fallback: str,
) -> dict[str, Any]:
    if domain == "matrix":
        raise ReportBPortalError(
            "矩阵记录不得由任意 Mapping 投影；请使用 TypedMatrixView"
        )
    source = _unwrap_fact(value)
    row_id = _stable_row_id(value, fallback)
    product_id = _product_id(value) or _product_id(source)
    trial_id = _trial_id(value) or _trial_id(source)
    numeric = _value_for(value)
    raw_state = _first(value, "disclosure_state", default=None)
    state = _state(raw_state, numeric)
    renderable = numeric is not None and state in _CONCRETE_STATES
    group_assignment_state = _text(
        _source_first(value, source, "group_assignment_state", default="unassessed")
    )
    unassigned_product = (
        domain in {"efficacy", "safety"} and group_assignment_state == "unknown"
    )
    product_name = (
        "结果组别产品归属待核"
        if unassigned_product else names.get(product_id, "未列示产品")
    )
    trial_name = trial_names.get(trial_id, "未列示试验")
    label = _label_for(value, domain)
    arm = _arm_label(value)
    category = _category_for(value, domain, arm)
    unit = _text(
        _source_first(
            value,
            source,
            "unit",
            "measurement_unit",
            "measure_unit",
            "effect_unit",
            default="%" if domain in {"efficacy", "safety"} else "",
        )
    )
    cohort = _native_text(_source_first(value, source, "cohort_id", "cohort", default=""))
    period = _native_text(_source_first(value, source, "period_id", "period", "phase", default=""))
    reason = _native_text(
        _source_first(value, source, "canonical_reason", "reason_zh", "reason", default="")
    )
    target = _native_text(_source_first(value, source, "target_id", "target", default=""))
    group_id = _text(_source_first(value, source, "group_id", "arm_id", "group", default=""))
    population = _text(
        _source_first(
            value,
            source,
            "analysis_population_zh",
            "analysis_population",
            "population",
            default="",
        ),
    )
    field_family = _native_text(
        _source_first(value, source, "field_family", "variable_domain", default="")
    )
    statistic_form = _native_text(
        _source_first(
            value,
            source,
            "statistic_form",
            "statistic_label_zh",
            "statistical_form",
            default="",
        )
    )
    denominator_role = _native_text(_source_first(value, source, "denominator_role", default=""))
    # A machine enum is scientific typing, not display copy: translating only
    # part of it would make numeric-kind and statistical-form inference diverge.
    measure_object = _text(_source_first(value, source, "measure_object", default=""))
    time_label = _time_label(value)
    time_window = _text(
        _source_first(
            value,
            source,
            "time_window_zh",
            "time_window",
            "baseline_timepoint",
            default=time_label,
        ),
        time_label,
    )
    numerator = _number(_source_first(value, source, "numerator", default=None))
    denominator = _number(_source_first(value, source, "denominator", default=None))
    semantics = _semantic_projection(value, source, domain=domain)
    # 独立复核 B r56（issue-2）：角色归一未知时展示已解码的组标签
    # （第1组/第N期 等），不再把"组别未列示"直出到表格与图例
    _role_label_zh = semantics["arm_role_label_zh"]
    if semantics["arm_role"] == "unknown" and arm and arm not in {"", "组别未列示"}:
        _role_label_zh = arm
    actual_timepoint = _source_first(
        value,
        source,
        "actual_timepoint",
        "timepoint",
        "observed_timepoint",
        "timepoint_value",
        default=None,
    )
    actual_timepoint_unit = _text(
        _source_first(
            value,
            source,
            "actual_timepoint_unit",
            "time_unit",
            "observed_time_unit",
            "timepoint_unit",
            default="",
        )
    )
    original_endpoint = _text(
        _source_first(
            value,
            source,
            "original_endpoint",
            "endpoint_id",
            "raw_endpoint",
            "endpoint",
            "original_event",
            "original_term",
            "standard_term",
            "source_term",
            "term",
            "event_term",
            "event",
            default="",
        )
    )
    original_definition = _text(
        _source_first(
            value,
            source,
            "original_definition",
            "endpoint_definition",
            "endpoint_definition_zh",
            "source_field_definition",
            "event_definition_zh",
            "event_definition",
            "raw_definition",
            "definition",
            "source_definition",
            "baseline_definition",
        )
    )
    if domain == "safety" and not original_definition:
        original_definition = "｜".join(
            part for part in (
                _text(_source_first(value, source, "source_class_title", default="")),
                _text(_source_first(value, source, "source_category_title", default="")),
            ) if part
        )
    original_variable = _text(
        _source_first(
            value,
            source,
            "original_variable",
            "variable_label_zh",
            "variable",
            "variable_name",
            "source_field_name",
            "source_field",
            "source_name",
            "standardized_concept",
            "source_definition",
            default="",
        )
    )
    study_identity = "｜".join(item for item in (product_name, trial_name) if item)
    source_name = _text(_source_first(value, source, "source_name", "source", default=""))
    scope = _text(_source_first(value, source, "scope", default=""))
    maturity = _text(_source_first(value, source, "maturity", default=""))
    limitation = _text(_source_first(value, source, "limitation", default=""))
    status_value = _native_text(
        _source_first(value, source, "status", "status_label_zh", default="")
    )
    role = _text(_source_first(value, source, "role", default=""))
    phase = _text(_source_first(value, source, "phase", default=""))
    sample_size = _number(_source_first(value, source, "sample_size", default=None))
    treatment_sample_size = _number(
        _source_first(value, source, "treatment_sample_size", default=None)
    )
    modality = _text(_source_first(value, source, "modality", default=""))
    developer = _text(_source_first(value, source, "developer", default=""))
    mechanism = _text(_source_first(value, source, "mechanism", default=""))
    route = _text(_source_first(value, source, "route", default=""))
    result_status = _text(_source_first(value, source, "result_status", default=""))
    regions = _first(value, "regions", default=None)
    if regions is None:
        regions = _first(source, "regions", default=None)
    coverage = _number(_source_first(value, source, "coverage", default=None))
    numeric_kind = infer_numeric_kind(
        measure_object=measure_object, statistic_form=statistic_form,
        unit=unit, domain=domain,
    )
    plot_numerator = numerator
    plot_denominator = denominator
    plot_estimand = _text(_source_first(value, source, "estimand", default=label))
    value_basis = _text(_source_first(value, source, "value_basis", default=""))
    if domain == "efficacy":
        if value_basis in {"modeled_estimate", "reported_estimate"}:
            numeric_kind = NumericMeasureKind.ADJUSTED_ESTIMATE
            plot_numerator = None
            plot_denominator = None
            plot_estimand = f"{plot_estimand}|{value_basis}"
        elif (
            unit in {"%", "百分比"}
            and numeric is not None
            and numerator is not None
            and denominator is not None
            and abs(float(numeric) - numerator / denominator * 100) > 0.11
        ):
            if value_basis == "crude_rate":
                raise ReportBPortalError("B 疗效声明粗率但报告值与原始计数不一致")
            # Keep the reported number and the raw counts, but never let the
            # latter overwrite an unresolved statistical form in the plot.
            plot_numerator = None
            plot_denominator = None
            plot_estimand = f"{plot_estimand}|reported_value_not_count_derived"
    projection = project_numeric(
        value=numeric, unit=unit,
        kind=numeric_kind,
        numerator=plot_numerator, denominator=plot_denominator,
        direction=_text(_source_first(value, source, "direction", default="")),
        window=time_window, estimand=plot_estimand,
    )
    renderable = renderable and projection.renderable and not unassigned_product
    numeric_projection = projection.as_dict()
    if unassigned_product:
        numeric_projection["renderable"] = False
        numeric_projection["unrenderable_reason"] = "group_product_relationship_unresolved"
    result: dict[str, Any] = {
        "row_id": row_id,
        "_domain": domain,
        "product_id": product_id,
        "trial_id": trial_id,
        "target": target,
        "target_id": target,
        "display_label_zh": label,
        "element": label,
        "product_zh": product_name,
        "trial_zh": trial_name,
        "study_identity": study_identity,
        "identity_label_zh": study_identity or "产品与试验未列示",
        "arm": arm,
        "group": arm,
        "group_id": group_id,
        "group_assignment_state": group_assignment_state,
        "unrendered_reason": (
            "group_product_relationship_unresolved" if unassigned_product else None
        ),
        "arm_role": semantics["arm_role"],
        "arm_role_label_zh": _role_label_zh,
        # 独立复核 B r36（issue-1）：剂量递增队列行（Cohort 1..4）原臂标签
        # 不得在角色收敛（治疗组）后丢失，兜底到原始臂名并经漏斗转写
        "arm_detail": _native_text(
            _source_first(value, source, "arm_detail", "arm_name", "group_name",
                          "arm_label", "arm", "group", default="")
        ),
        # 独立复核 B r35：基线类别值（女/男等）随行走，行级可归属
        "category_level": _text(
            _source_first(value, source, "category_level", default="")
        ),
        "category_level_label_zh": _baseline_category_zh(
            {"category_level": _text(
                _source_first(value, source, "category_level", default="")
            )}
        ),
        "cohort": cohort,
        "period": period,
        "category": category,
        "event": label,
        "term_key": _text(
            _source_first(value, source, "term_key", default="unknown"), "unknown"
        ),
        "polarity": _text(_source_first(value, source, "polarity", default="affirmed"), "affirmed"),
        "grade_set": tuple(_source_first(value, source, "grade_set", default=()) or ()),
        "seriousness": _text(
            _source_first(value, source, "seriousness", default="unspecified"), "unspecified"
        ),
        "teae": _source_first(value, source, "teae", default=None),
        "relatedness": _text(
            _source_first(value, source, "relatedness", default="unspecified"), "unspecified"
        ),
        "parent": _source_first(value, source, "parent", default=None),
        "children": tuple(_source_first(value, source, "children", default=()) or ()),
        "count_basis": _text(
            _source_first(value, source, "count_basis", default="participants"), "participants"
        ),
        "at_risk_stat": _source_first(value, source, "at_risk_stat", default=None),
        "time": time_label,
        "actual_timepoint": actual_timepoint,
        "actual_timepoint_unit": actual_timepoint_unit,
        # 独立复核 B r35：展开表直读的 time_window/arm_detail 必须中文化
        "time_window": _native_timepoint_zh(time_window),
        "time_window_band": semantics["time_window_band"],
        "time_window_band_label_zh": semantics["time_window_band_label_zh"],
        "population": population,
        "population_context": semantics["population_context"],
        "population_context_label_zh": semantics["population_context_label_zh"],
        "field_family": field_family,
        "reason": reason,
        "statistic_form": statistic_form,
        "statistical_form_family": semantics["statistical_form_family"],
        "statistical_form_family_label_zh": semantics["statistical_form_family_label_zh"],
        "clinical_concept": semantics["clinical_concept"],
        "clinical_concept_label_zh": semantics["clinical_concept_label_zh"],
        "semantic_definition": original_definition,
        "semantic_direction": _text(
            _source_first(value, source, "direction", "endpoint_direction", default=""),
            "direction-not-reported",
        ),
        "semantic_estimand": _text(
            _source_first(value, source, "estimand", "estimand_label", default=""),
            "estimand-not-reported",
        ),
        "semantic_denominator": _text(
            _source_first(
                value,
                source,
                "denominator_semantics",
                "denominator_definition",
                "denominator_role",
                default="",
            ),
            "denominator-not-reported",
        ),
        "semantic_analysis_set": semantics["population_context"],
        "semantic_analysis_form": semantics["statistical_form_family"],
        "semantic_instrument_or_scale": _text(
            _source_first(
                value,
                source,
                "instrument_or_scale",
                "scale_version",
                "scale",
                "instrument",
                default="",
            ),
            "instrument-or-scale-not-reported",
        ),
        "original_endpoint": original_endpoint,
        "original_definition": original_definition,
        "original_variable": original_variable,
        # 独立复核 B r36（issue-2）：变量名转写失败时显式声明，
        # 不再原样漏出登记英文原句；原文保留在"简短原文"引文与证据层
        "original_variable_label_zh": (
            _b_native_label(original_variable)
            or ("登记变量（原文见来源）" if _text(original_variable) else "原始变量未列示")
        ),
        "status": status_value or _state_label(state),
        "source_version_id": _source_version(value),
        "source_name": source_name,
        "scope": scope,
        "maturity": maturity,
        "limitation": limitation,
        "role": role,
        "phase": phase,
        "sample_size": sample_size,
        "treatment_sample_size": treatment_sample_size,
        "modality": modality,
        "developer": developer,
        "mechanism": mechanism,
        "route": route,
        "result_status": result_status,
        "regions": regions,
        "coverage": coverage,
        "denominator_role": denominator_role,
        "measure_object": measure_object,
        "unit": unit,
        "numerator": numerator,
        "denominator": denominator,
        "value_basis": value_basis,
        "value": numeric,
        "raw_numeric_value": numeric,
        "numeric_value": projection.plot_value,
        "numeric_projection": numeric_projection,
        "renderable": renderable,
        "disclosure_state": state,
        "difference_note": "；".join(
            dict.fromkeys(
                _native_text(item)
                for item in (
                    *_iter_values(
                        _source_first(
                            value,
                            source,
                            "compatibility_difference_labels_zh",
                            "difference_labels_zh",
                            default=(),
                        )
                    ),
                    _source_first(value, source, "reason_zh", "reason", default=""),
                )
                if _text(item)
            )
        ),
    }
    if unassigned_product:
        warning = "结果组别与产品关联待核；原始值保留，不进入产品间共轴比较"
        result["difference_note"] = "；".join(
            item for item in (result["difference_note"], warning) if item
        )
    result["_source_binding"] = semantic_source_digest(value)
    if domain == "safety":
        result["value_matrix"] = numeric
    if domain == "baseline":
        result["variable"] = label
        result["statistic"] = (
            _native_text(
                _source_first(
                    value,
                    source,
                    "statistic_label_zh",
                    "statistic_form",
                    "statistical_form",
                    default="",
                )
            )
            or semantics["statistical_form_family_label_zh"]
        )
        result["time"] = _text(
            _source_first(
                value,
                source,
                "baseline_timepoint",
                "time_window",
                "timepoint",
                default=result["time"],
            ),
            result["time"],
        )
        result["actual_timepoint"] = _source_first(
            value,
            source,
            "baseline_timepoint",
            "actual_timepoint",
            "timepoint",
            default=result["actual_timepoint"],
        )
    if domain == "disposition":
        result["field"] = label
        result["status"] = (
            _native_text(
                _first(value, "display_value_zh", "status_label_zh", default="已报告"),
                "已报告",
            )
            if renderable
            else _state_label(state)
        )
    if domain == "matrix":
        point = _first(value, "point", default=None)
        result["x_value"] = _number(_first(point, "x_value", "x", default=None))
        result["y_value"] = _number(_first(point, "y_value", "y", default=None))
        result["size"] = _number(_first(point, "radius", "area", "size", default=None))
        result["renderable"] = all(
            result[key] is not None for key in ("x_value", "y_value", "size")
        )
        result["value"] = result["x_value"]
        result["numeric_value"] = result["x_value"]
        if result["renderable"]:
            result["arm"] = "试验内治疗组与对照组"
            result["group"] = result["arm"]
            result["status"] = "可比较"
            result["disclosure_state"] = "reported_value"
        elif result["status"] == "不适用":
            result["arm"] = "不适用"
            result["group"] = result["arm"]
            result["disclosure_state"] = "not_applicable"
    return result


def _dedupe_records(
    records: Sequence[tuple[dict[str, Any], Any]],
) -> tuple[tuple[dict[str, Any], Any], ...]:
    seen: dict[str, tuple[str, str]] = {}
    result: list[tuple[dict[str, Any], Any]] = []
    for row, source in records:
        row_id = _text(row.get("row_id"))
        if not row_id:
            raise ValueError("科学视图观察缺少标识")
        identity = (_text(row.get("_domain")), semantic_row_digest(row))
        if row_id in seen:
            if seen[row_id] != identity:
                raise ValueError("科学视图同一观察标识存在域或事实冲突")
            continue
        seen[row_id] = identity
        result.append((row, source))
    return tuple(result)


def _without_declared_shadow_rows(rows: Sequence[Any]) -> tuple[Any, ...]:
    """会商 round-4 #4（B r57/r58/r59）：-declared 影子行只在门匹配索引
    中生效，任何展示路径（表格/图/证据视图）一律过滤。"""
    return tuple(row for row in rows if not _row_is_declared_shadow(row))


def _with_uncovered_legacy_rows(
    view_rows: Sequence[Any], legacy_rows: Sequence[Any],
) -> tuple[Any, ...]:
    """A precise view may cover only part of B's related-study universe."""
    views = _without_declared_shadow_rows(view_rows)
    legacy = _without_declared_shadow_rows(legacy_rows)
    by_id = {
        row_id: row
        for row in views
        if (row_id := _text(_first(row, "row_id", default=None)))
    }
    linked: set[str] = set()
    uncovered: list[Any] = []
    for row in legacy:
        view_id = _text(_first(row, "source_view_row_id", "row_id", default=None))
        view = by_id.get(view_id)
        if view is None:
            uncovered.append(row)
            continue
        if view_id in linked:
            raise ReportBPortalError("多个领域行指向同一来源视图观察")
        linked.add(view_id)
        view_fact = _unwrap_fact(view)
        for field in ("product_id", "trial_id", "unit", "source_version_id"):
            expected = _text(_first(row, field, default=None))
            observed = _text(_source_first(view, view_fact, field, default=None))
            if expected and observed and expected != observed:
                raise ReportBPortalError(f"来源视图与领域行{field}冲突")
        view_value = _value_for(view)
        row_value = _value_for(row)
        view_state = _state(_first(view, "disclosure_state", default=None), view_value)
        row_state = _state(_first(row, "disclosure_state", default=None), row_value)
        same_zero = view_value == row_value == 0 and {
            view_state, row_state,
        } == {"reported_value", "reported_zero"}
        if view_value != row_value or (view_state != row_state and not same_zero):
            raise ReportBPortalError("来源视图与领域行数值或披露状态冲突")
    return (*views, *uncovered)


def _select_view_coverage(
    view_rows: Sequence[Any], legacy_rows: Sequence[Any], coverage_mode: str,
) -> tuple[Any, ...]:
    if coverage_mode == "legacy_complete":
        return _without_declared_shadow_rows(view_rows)
    selected = _with_uncovered_legacy_rows(view_rows, legacy_rows)
    if coverage_mode == "complete" and len(selected) > len(
        _without_declared_shadow_rows(view_rows)
    ):
        raise ReportBPortalError("声明完整的来源视图遗漏领域行")
    return selected


def _legacy_or_view_rows(
    data: ReportBPortalData,
    *,
    view_name: str,
    legacy_name: str,
    view_fields: tuple[str, ...],
    table_fields: tuple[str, ...] = (),
) -> tuple[Any, ...]:
    legacy = tuple(_get(data, legacy_name, ()) or ())
    source = _view_source(data, view_name)
    if source is not None:
        coverage_mode = _get(source, "coverage_mode", "legacy_complete")
        if not isinstance(coverage_mode, str) or coverage_mode not in {
            "legacy_complete", "complete", "partial",
        }:
            raise ReportBPortalError("来源视图 coverage_mode 仅允许 complete 或 partial")
        fields = (
            *view_fields,
            "single_timepoint_views",
            "longitudinal_views",
            "source_effect_size_views",
            "heatmap_views",
            "chart_panels",
        )
        if isinstance(source, Mapping):
            for field in fields:
                candidate = _get(source, field, _MISSING)
                if candidate is not _MISSING and candidate is not None:
                    rows = _flatten_view_rows(_iter_values(candidate))
                    if rows:
                        return _select_view_coverage(rows, legacy, coverage_mode)
        rows = _flatten_view_rows(_collection(source, *view_fields))
        if rows:
            # A view state complete table is already a projection; its nested
            # fact is unwrapped by the record adapter without recomputation.
            return _select_view_coverage(rows, legacy, coverage_mode)
        if coverage_mode == "complete" and _without_declared_shadow_rows(legacy):
            raise ReportBPortalError("声明完整的来源视图遗漏领域行")
    # 会商 round-4 #4：-declared 声明臂影子行是 B 门匹配的内部索引，
    # 展示层在唯一视图行入口统一过滤（安全/基线/疗效域同规则）
    return _without_declared_shadow_rows(legacy)


def _efficacy_records(
    data: ReportBPortalData,
    names: Mapping[str, str],
    trial_names: Mapping[str, str],
) -> tuple[tuple[dict[str, Any], Any], ...]:
    values = _legacy_or_view_rows(
        data,
        view_name="efficacy_views",
        legacy_name="efficacy",
        view_fields=("fact_rows", "facts", "rows"),
    )
    records: list[tuple[dict[str, Any], Any]] = []
    for index, value in enumerate(values):
        row = _project_record(
            value,
            domain="efficacy",
            names=names,
            trial_names=trial_names,
            fallback=f"efficacy-{index + 1}",
        )
        records.append((row, value))
    return _dedupe_records(records)


def _safety_records(
    data: ReportBPortalData,
    names: Mapping[str, str],
    trial_names: Mapping[str, str],
) -> tuple[tuple[dict[str, Any], Any], ...]:
    values = _legacy_or_view_rows(
        data,
        view_name="safety_views",
        legacy_name="safety",
        view_fields=("fact_rows", "facts", "rows"),
    )
    # 会商 round-4 #4（B r57 issue-2）：-declared 声明臂影子行是 B 门
    # 匹配的内部索引（与所在期间行同值），渲染层统一过滤，不再展示
    visible_values = [
        value
        for value in values
        if not str(
            (value.get("row_id") if isinstance(value, dict) else getattr(value, "row_id", ""))
            or ""
        ).endswith("-declared")
    ]
    records = [
        (
            _project_record(
                value,
                domain="safety",
                names=names,
                trial_names=trial_names,
                fallback=f"safety-{index + 1}",
            ),
            value,
        )
        for index, value in enumerate(visible_values)
    ]
    row_ids = {row["row_id"] for row, _source in records}
    for legacy in data.safety:
        if legacy.row_id in row_ids or legacy.disclosure_state == "已公开":
            continue
        records.append(
            (
                _project_record(
                    legacy,
                    domain="safety",
                    names=names,
                    trial_names=trial_names,
                    fallback=legacy.row_id,
                ),
                legacy,
            )
        )
    return _dedupe_records(records)


def _state_rows_from_view(
    data: ReportBPortalData,
    *,
    view_name: str,
    page_id: str,
    names: Mapping[str, str],
    trial_names: Mapping[str, str],
    domain: str,
) -> tuple[tuple[dict[str, Any], Any], ...]:
    source = _view_source(data, view_name)
    if source is None:
        return ()
    if isinstance(source, Mapping):
        page_source = _get(source, page_id, _MISSING)
        if page_source is not _MISSING and page_source is not None:
            source = page_source
    values = _flatten_view_rows(
        _collection(
            source,
            "complete_table",
            "selected_facts",
            "facts",
            "table_rows",
            "rows",
        )
    )
    # 会商 round-4 #4（B r58 issue-2）：-declared 影子行过滤统一到
    # 视图行入口——基线域与安全域同规则，不再只在安全域过滤
    visible_values = [
        value
        for value in values
        if not str(
            (value.get("row_id") if isinstance(value, dict) else getattr(value, "row_id", ""))
            or ""
        ).endswith("-declared")
    ]
    records_list: list[tuple[dict[str, Any], Any]] = []
    for index, value in enumerate(visible_values):
        row = _project_record(
            value,
            domain=domain,
            names=names,
            trial_names=trial_names,
            fallback=f"{domain}-{index + 1}",
        )
        row["_domain"] = domain
        records_list.append((row, value))
    records = tuple(records_list)
    return _dedupe_records(records)


def _synthetic_status_records(
    data: ReportBPortalData,
    *,
    page_id: str,
    names: Mapping[str, str],
    trial_names: Mapping[str, str],
    include_products: bool = False,
    domain: str = "generic",
) -> tuple[tuple[dict[str, Any], Any], ...]:
    def project_status(source: Mapping[str, Any], row_id: str) -> dict[str, Any]:
        # A matrix data row is accepted only through TypedMatrixView.  Empty-page
        # status rows are UI metadata, not comparisons, so keep them explicitly
        # non-renderable and outside the matrix projection entrance.
        projection_domain = "generic" if domain == "matrix" else domain
        row = _project_record(
            source,
            domain=projection_domain,
            names=names,
            trial_names=trial_names,
            fallback=row_id,
        )
        if domain == "matrix":
            row.update(
                {
                    "_domain": "matrix",
                    "x_value": None,
                    "y_value": None,
                    "size": None,
                    "renderable": False,
                    "disclosure_state": "not_applicable",
                    "status": "未形成封闭 typed 比较",
                    "reason": (
                        "当前数据包未形成经验证的试验内疗效—安全性比较；"
                        "原因需核对对照、人群、统计口径和来源版本，"
                        "不等于研究未公开结果"
                    ),
                }
            )
        return row

    records: list[tuple[dict[str, Any], Any]] = []
    if include_products:
        for product in data.products:
            row_id = f"{page_id}-product-{product.id}"
            source: dict[str, Any] = {
                "row_id": row_id,
                "product_id": product.id,
                "label_zh": product.name,
                "target": product.target,
                "modality": product.modality,
                "phase": product.phase,
                "status": product.status,
                "result_status": product.result_status,
                "regions": product.regions,
                "route": product.route,
                "developer": product.developer,
                "mechanism": product.mechanism,
                "disclosure_state": "reported_value",
            }
            synthetic_row = project_status(source, row_id)
            synthetic_row["_synthetic"] = True
            records.append((synthetic_row, source))
    else:
        for trial in data.trials:
            row_id = f"{page_id}-{trial.id}"
            source = {
                "row_id": row_id,
                "product_id": trial.product_id,
                "trial_id": trial.id,
                "label_zh": f"{trial_names.get(trial.id, trial.name)}的相关记录",
                "unit": "人",
                "phase": trial.phase,
                "status": trial.status,
                "role": trial.role,
                "sample_size": trial.sample_size,
                "treatment_sample_size": trial.treatment_sample_size,
                # 独立审阅 R13：未知样本量显式 not_reported，不得伪造成 reported_value
                "disclosure_state": (
                    "reported_value" if trial.sample_size is not None else "not_reported"
                ),
            }
            synthetic_row = project_status(source, row_id)
            synthetic_row["_synthetic"] = True
            records.append((synthetic_row, source))
    return tuple(records)


def _domain_empty_records(
    data: ReportBPortalData,
    *,
    page_id: str,
    names: Mapping[str, str],
    trial_names: Mapping[str, str],
    domain: str,
) -> tuple[tuple[dict[str, Any], Any], ...]:
    records: list[tuple[dict[str, Any], Any]] = []
    for trial in data.trials:
        row_id = f"{page_id}-{trial.id}-empty"
        label_key = "variable_label_zh" if domain == "baseline" else "field_label_zh"
        source: dict[str, Any] = {
            "row_id": row_id,
            "product_id": trial.product_id,
            "trial_id": trial.id,
            label_key: "暂无公开记录",
            "disclosure_state": "not_reported",
            "_empty_state": True,
        }
        row = _project_record(
            source,
            domain=domain,
            names=names,
            trial_names=trial_names,
            fallback=row_id,
        )
        row["_empty_state"] = True
        row["status"] = "暂无公开记录"
        records.append((row, source))
    return tuple(records)


def _trial_context_records(
    data: ReportBPortalData,
    names: Mapping[str, str],
    trial_names: Mapping[str, str],
) -> tuple[tuple[dict[str, Any], Any], ...]:
    records: list[tuple[dict[str, Any], Any]] = []
    for trial in data.trials:
        row_id = f"trial-context-{trial.id}"
        source = {
            "row_id": row_id,
            "product_id": trial.product_id,
            "trial_id": trial.id,
            "display_label_zh": f"{trial_names.get(trial.id, trial.name)}样本量",
            "value": trial.sample_size,
            "unit": "人",
            "disclosure_state": (
                "reported_value" if trial.sample_size is not None else "not_reported"
            ),
            "status": trial.status,
            "role": trial.role,
            "phase": trial.phase,
            "sample_size": trial.sample_size,
            "treatment_sample_size": trial.treatment_sample_size,
            "time": trial.phase,
        }
        records.append(
            (
                _project_record(
                    source,
                    domain="generic",
                    names=names,
                    trial_names=trial_names,
                    fallback=row_id,
                ),
                source,
            )
        )
    return tuple(records)


def _matrix_records(
    data: ReportBPortalData,
    names: Mapping[str, str],
    trial_names: Mapping[str, str],
) -> tuple[tuple[dict[str, Any], Any], ...]:
    source = _view_source(data, "matrix_view")
    if source is None:
        return ()
    if not isinstance(source, TypedMatrixView):
        raise ReportBPortalError("矩阵输入必须通过封闭 typed projection 合同")
    result: list[tuple[dict[str, Any], Any]] = []
    for value in source.rows:
        treatment = value.treatment_projection
        control = value.control_projection
        row = {
            "row_id": value.comparison_row_id, "_domain": "matrix",
            "product_id": value.product_id, "trial_id": value.trial_id,
            "product_zh": names.get(value.product_id, "未列示产品"),
            "trial_zh": trial_names.get(value.trial_id, "未列示试验"),
            "x_value": treatment.plot_value - control.plot_value,
            "y_value": value.safety_projection.plot_value,
            "size": value.size_projection.plot_value,
            "x_unit": treatment.plot_unit, "y_unit": value.safety_projection.plot_unit,
            "size_basis": value.size_projection.size_basis,
            "renderable": True, "status": "可比较",
            "disclosure_state": "reported_value",
            "arm": "试验内治疗组与对照组", "group": "试验内治疗组与对照组",
        }
        result.append((row, value))
    return _dedupe_records(result)


# ---------------------------------------------------------------------------
# Evidence projection and chart payloads
# ---------------------------------------------------------------------------


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


def _disclosure_enum(state: str) -> FactDisclosureState:
    try:
        return FactDisclosureState(state)
    except ValueError:
        return FactDisclosureState.NOT_REPORTED


def _extension_field(source: Any, row: Mapping[str, Any], *names: str) -> EvidenceField:
    value = _first(source, *names, default=None)
    if value is None and names:
        value = row.get(names[0])
    if isinstance(value, (list, tuple)):
        value = "、".join(_text(item) for item in value if _text(item)) or None
    return _evidence_field(value, str(row.get("disclosure_state", "not_reported")))


def _evidence_view(
    data: ReportBPortalData,
    *,
    row: Mapping[str, Any],
    source: Any,
    page_id: str,
    observation_kind: EvidenceObservationKind,
    names: Mapping[str, str],
    trial_names: Mapping[str, str],
) -> EvidenceView:
    row_id = _text(row.get("row_id"), "unknown-row")
    state = _text(row.get("disclosure_state"), "not_reported")
    product_id = _text(row.get("product_id"))
    trial_id = _text(row.get("trial_id"))
    snapshot = _text(
        data.report_snapshot_id
        or _first(source, "report_snapshot_id", "snapshot_id", default=None),
        f"b-{data.report_version}",
    )
    product = (
        "结果组别产品归属待核"
        if row.get("group_assignment_state") == "unknown"
        else names.get(product_id, "未列示产品")
    )
    trial = trial_names.get(trial_id, "未列示试验")
    if page_id == "evidence-limitations" and not product_id and not trial_id:
        product = ""
        trial = ""
    label = _text(row.get("display_label_zh"), "研究记录")
    reported_numeric = _reported_numeric(row)
    numeric_projection = row.get("numeric_projection")
    if (
        isinstance(reported_numeric, float)
        and reported_numeric.is_integer()
        and isinstance(numeric_projection, Mapping)
        and numeric_projection.get("kind") in {"participant_count", "event_count"}
    ):
        reported_numeric = int(reported_numeric)
    value_field = (
        _evidence_field(reported_numeric)
        if reported_numeric is not None and state in _CONCRETE_STATES
        else _evidence_field(None, state)
    )
    # 独立会商 R24-25 FAIL：数值披露与来源追溯必须分离；真零由 reported_zero
    # 显式表达（缺失仍为互斥状态，绝不当 0）
    evidence_state = (
        "reported_zero"
        if reported_numeric == 0 and state in _CONCRETE_STATES
        else state
    )
    group = _text(row.get("arm"), "组别未列示")
    source_id = _source_version(source)
    # 引文是来源原始片段；只用 strip 判断是否为空，不折叠其空白或换行。
    raw_quote = _first(source, "source_text", default=None)
    source_quote = raw_quote if isinstance(raw_quote, str) and raw_quote.strip() else ""
    exact_locator = _exact_source_locator(source)
    located = bool(source_id and source_quote and exact_locator is not None)
    source_label = "逐事实来源待核"
    if located:
        # 来源版本标签是用户可见文案：提供方中文标签优先，其余回落到原生中文，
        # 不把英文提供方名（如 ClinicalTrials.gov）当作版本标签直出
        source_label = _text(
            _first(source, "source_version_label_zh", default=None),
            "来源版本已定位",
        )
        if not re.search(r"[\u4e00-\u9fff]", source_label):
            source_label = "来源版本已定位"
    original_text = source_quote if located else ""
    user_edit = data.user_edits.get(row_id)
    if located and user_edit is not None:
        explanation = (
            "当前数值由用户清除，待重新核实；原始来源值和定位仍可查。"
            if state == "user_cleared"
            else "当前数值由用户修订，尚未独立复核；原始来源值和定位仍可查。"
        )
    elif located:
        explanation = f"该记录保留来源披露状态：{_state_label(state)}。"
    else:
        explanation = (
            "该观察仍可检索；逐事实来源版本、原文和精确定位待核，"
            "不能作为已验科学结论。"
        )
    if row.get("group_assignment_state") == "unknown":
        explanation += " 结果组别与产品关联待核；原始值可查，不进入产品间共轴比较。"
    report_row = ReportRow.model_construct(
        row_id=row_id,
        fact_id=_source_row_id(source, row_id),
        claim_id=None,
        product_id=(None if row.get("group_assignment_state") == "unknown"
                    else product_id or None),
        trial_id=trial_id or None,
        group_id=None,
        endpoint_id=None,
        event_id=None,
        timepoint_id=None,
        display_label_zh=label,
        page_responsibility_id=page_id,
        report_snapshot_id=snapshot,
        disclosure_state=_disclosure_enum(evidence_state),
    )
    common = {
        "report_kind": ReportKind.B,
        "observation_kind": observation_kind,
        "row": report_row,
        "product_zh": product,
        "trial_zh": trial,
        "group_zh": _evidence_field(group),
        "element_zh": label,
        "scale": _extension_field(source, row, "scale", "scale_version"),
        "timepoint": _evidence_field(row.get("time"), state),
        "value": value_field,
        "threshold": _extension_field(source, row, "threshold", "adherence_threshold"),
        "unit": _evidence_field(row.get("unit"), state),
        "numerator": _evidence_field(
            _first(source, "numerator", default=row.get("numerator")), state
        ),
        "denominator": _evidence_field(
            _first(source, "denominator", default=row.get("denominator")), state
        ),
        "source_trace_state": "located" if located else "unverified",
        "source_version_id": source_id if located else None,
        "source_version_label_zh": source_label,
        "locator": exact_locator if located else None,
        "explanation": _evidence_field(explanation),
        "original_text": original_text or None,
        "original_text_status": (
            OriginalTextStatus.PROVIDED
            if original_text
            else OriginalTextStatus.NOT_PROVIDED
        ),
        "user_edit": user_edit,
        "conflicts": (),
        "historical_versions": (),
    }
    if observation_kind in {
        EvidenceObservationKind.BASELINE_OBSERVATION,
        EvidenceObservationKind.TRIAL_DISPOSITION_OBSERVATION,
    }:
        common.update(
            {
                "canonical_variable_family": _extension_field(
                    source, row, "canonical_variable_family", "variable_domain", "field_family"
                ),
                "source_field_name": _extension_field(
                    source, row, "source_field_name", "source_name", "source_field_definition"
                ),
                "source_field_definition": _extension_field(
                    source, row, "source_field_definition", "source_definition"
                ),
                "statistical_form_or_measurement_object": _extension_field(
                    source, row, "statistical_form", "statistic_form", "measure_object"
                ),
                "scale_version_direction": _extension_field(
                    source, row, "scale_version", "direction"
                ),
                "denominator_role": _extension_field(source, row, "denominator_role"),
                "time_window_or_baseline_definition": _extension_field(
                    source, row, "time_window", "baseline_definition", "baseline_timepoint"
                ),
                "reason_original_text": None,
                "canonical_reason": _extension_field(source, row, "canonical_reason", "reason_zh"),
                "mutual_exclusion_exhaustiveness": _extension_field(
                    source, row, "mutual_exclusion_exhaustiveness"
                ),
                "compatibility_rule": _extension_field(source, row, "compatibility_rule"),
                "difference_label": _extension_field(
                    source, row, "difference_labels_zh", "difference_label"
                ),
            }
        )
    return EvidenceView.model_construct(None, **common)


def _observation_kind(page_id: str) -> EvidenceObservationKind:
    if page_id in _BASELINE_PAGE_IDS:
        return EvidenceObservationKind.BASELINE_OBSERVATION
    if page_id in _DISPOSITION_PAGE_IDS:
        return EvidenceObservationKind.TRIAL_DISPOSITION_OBSERVATION
    return EvidenceObservationKind.GENERAL


def _observation_kind_for_row(
    row: Mapping[str, Any],
    page_id: str,
) -> EvidenceObservationKind:
    domain = _text(row.get("_domain"))
    if domain == "baseline":
        return EvidenceObservationKind.BASELINE_OBSERVATION
    if domain == "disposition":
        return EvidenceObservationKind.TRIAL_DISPOSITION_OBSERVATION
    return _observation_kind(page_id)


def _semantic_domain_for_page(page_id: str) -> str:
    if page_id in {"efficacy", "longitudinal-results"}:
        return "efficacy"
    if page_id == "subgroups-supporting-evidence":
        return "supporting"
    if page_id == "safety":
        return "safety"
    if page_id in _BASELINE_PAGE_IDS:
        return "baseline"
    if page_id in _DISPOSITION_PAGE_IDS:
        return "disposition"
    return "generic"


def _records_with_semantics(
    records: Sequence[tuple[dict[str, Any], Any]],
    *,
    page_id: str,
) -> tuple[tuple[dict[str, Any], Any], ...]:
    """Ensure legacy adapters also expose the R13 comparison dimensions."""
    domain = _semantic_domain_for_page(page_id)
    result: list[tuple[dict[str, Any], Any]] = []
    for row, source in records:
        copied = dict(row)
        existing = _text(copied.get("_domain"))
        if domain != "generic":
            if existing and existing != domain:
                raise ValueError(
                    f"观察域与页面域不一致，拒绝静默改写：{existing} → {domain}"
                )
            copied["_domain"] = domain
        if domain in _CLINICAL_CONCEPT_LOOKUPS and not copied.get("clinical_concept"):
            copied.update(_semantic_projection(copied, source, domain=domain))
        elif domain in _CLINICAL_CONCEPT_LOOKUPS:
            # A partially migrated row may carry only one normalized field.
            semantics = _semantic_projection(copied, source, domain=domain)
            for key, value in semantics.items():
                if not copied.get(key):
                    copied[key] = value
        result.append((copied, source))
    return tuple(result)


_BASELINE_CATEGORY_ZH = {
    "female": "女",
    "male": "男",
    "other": "其他",
    "unknown": "未知",
    "not reported": "未报告",
    "hispanic or latino": "西班牙裔或拉丁裔",
    "not hispanic or latino": "非西班牙裔或拉丁裔",
    "white": "白人",
    "black or african american": "黑人或非裔美国人",
    "asian": "亚裔",
    "american indian or alaska native": "美洲印第安人或阿拉斯加原住民",
    "native hawaiian or other pacific islander": "夏威夷原住民或其他太平洋岛民",
    "yes": "是",
    "no": "否",
}


def _baseline_category_zh(row: Mapping[str, Any]) -> str:
    """登记基线类别值的中性中文呈现；数字区间等原样保留。"""
    raw = _text(row.get("category_level"))
    if not raw:
        return ""
    low = raw.casefold()
    return _BASELINE_CATEGORY_ZH.get(low, raw)


def _chart_series_key(row: Mapping[str, Any]) -> str:
    role = _text(row.get("arm_role"), "unknown")
    group_id = _text(row.get("group_id"))
    key = role if role != "unknown" or not group_id else group_id
    # 独立复核 B r35：基线类别行（女/男）并入系列键，同卡不同类别不再同系列
    category = _text(row.get("category_level"))
    if category:
        key = f"{key}::category-{category}"
    return key


def _chart_series_label(row: Mapping[str, Any], key: str) -> str:
    role_label = _text(
        row.get("arm_role_label_zh"),
        _text(row.get("arm"), _text(row.get("group"), "组别未列示")),
    )
    # 独立复核 B r51/r55（issue-2）：role 归一为"组别未列示"时，回退组标识解码
    # （-arm-cohort-N → 第N组；-arm-group-N-treatment-naive → 第N组（初治）；
    #  -arm-<code>-tpN → <code> 第N期）
    if role_label in {"", "组别未列示"}:
        # 独立复核 B r51/r55/r56：与 _arm_label 共用同一组标识解码（同源）
        decoded = _decode_arm_identifier(_text(row.get("group_id")))
        if decoded is not None:
            return decoded
    # 独立复核 B r35：基线类别必须出现在系列标签上，数值才可归属
    category = _baseline_category_zh(row)
    if category:
        return f"{role_label}（{category}）"
    if key.startswith("treatment:") or key.startswith("control:"):
        for detail in (
            _text(row.get("arm_detail")),
            _text(row.get("group_label_zh")),
            _text(row.get("group")),
            _text(row.get("arm")),
        ):
            if detail and detail not in {role_label, "组别未列示"}:
                return f"{role_label}（{detail}）"
        return role_label
    return role_label


def _group_title(
    row: Mapping[str, Any],
    *,
    domain: str,
    include_time: bool = True,
    include_population: bool = True,
    include_statistic: bool = True,
) -> str:
    concept = _text(
        row.get("clinical_concept_label_zh"),
        _text(row.get("display_label_zh"), "临床指标"),
    )
    statistic = _text(
        row.get("statistical_form_family_label_zh"),
        _text(row.get("statistic_form"), "报告未注明统计口径"),
    )
    time_band = _text(row.get("time_window_band_label_zh"))
    population = _text(row.get("population_context_label_zh"))
    parts = [concept]
    if include_statistic:
        parts.append(statistic)
    if include_time and time_band and time_band != "时间点未列示":
        parts.append(time_band)
    if include_population and population and population != "分析人群未列示":
        parts.append(population)
    if domain == "safety":
        family = _text(row.get("family", row.get("event_family", "")))
        if "sae" in family.casefold() or "严重" in family:
            parts.insert(0, "严重不良事件")
        else:
            parts.insert(0, "安全性")
    elif domain == "baseline":
        parts.insert(0, "基线")
    elif domain == "disposition":
        parts.insert(0, "完成情况")
    return " · ".join(dict.fromkeys(part for part in parts if part))


def _chart_comparison_context(row: Mapping[str, Any]) -> tuple[str, str]:
    """Keep exact observation timing separate from a broad clinical time band.

    This key only licenses a shared chart category. It is not a claim that
    different trial estimates are interchangeable or head-to-head evidence.
    """
    axes = (
        *_semantic_group_key(row, include_time=True, include_domain=True),
        _text(row.get("time")),
        _text(row.get("period")),
        _text(row.get("actual_timepoint")),
        _text(row.get("actual_timepoint_unit")),
        _text(row.get("visit")),
        _text(row.get("analysis_population")),
        _text(row.get("time_window")),
        _text(row.get("cohort")),
    )
    key = hashlib.sha256(_canonical_json(axes)).hexdigest()
    time = _text(row.get("time"))
    window = _text(row.get("time_window"))
    time_tp = re.search(r"TP\s*(\d+)", time, flags=re.IGNORECASE)
    window_tp = re.search(r"TP\s*(\d+)", window, flags=re.IGNORECASE)
    same_tp = bool(time_tp and window_tp and time_tp.group(1) == window_tp.group(1))
    label_parts = []
    if time and (not window or not same_tp):
        label_parts.append(time)
    if window and window not in label_parts:
        label_parts.append(window)
    period = re.sub(r"^nct\d{8}-", "", _text(row.get("period")), flags=re.IGNORECASE)
    if period and period not in {time, window}:
        label_parts.append(f"登记期 {period}" if re.fullmatch(r"p\d+", period) else period)
    cohort = re.sub(r"^nct\d{8}-", "", _text(row.get("cohort")), flags=re.IGNORECASE)
    if cohort and cohort.casefold() not in {"全部", "all"} and cohort not in label_parts:
        label_parts.append(cohort)
    label = " · ".join(dict.fromkeys(label_parts)) or _text(
        row.get("time_window_band_label_zh"), "时间点未列示"
    )
    return key, label


def _group(
    title: str,
    records: Sequence[tuple[dict[str, Any], Any]],
    *,
    chart_type: str,
    cross_trial: bool = False,
    identity_series: bool = False,
    x_axis_label_zh: str | None = None,
    y_axis_label_zh: str | None = None,
    size_label_zh: str | None = None,
) -> dict[str, Any]:
    series_variants: dict[tuple[str, str], set[str]] = defaultdict(set)
    series_variant_by_row: dict[int, str] = {}
    details_by_variant: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    series_indexes: dict[tuple[str, str], list[int]] = defaultdict(list)
    identity_aware = cross_trial or identity_series
    if identity_aware:
        for index, (row, _source) in enumerate(records):
            identity_key = "::".join((_text(row.get("product_id")), _text(row.get("trial_id"))))
            base_key = _chart_series_key(row)
            variant_key = (identity_key, base_key)
            variant = _semantic_token(_text(row.get("group_id"), _text(row.get("arm_detail"))))
            series_variant_by_row[index] = variant
            details_by_variant[(identity_key, base_key, variant)].add(
                _semantic_token(_text(row.get("arm_detail")))
            )
            series_indexes[variant_key].append(index)
        for index, (row, _source) in enumerate(records):
            identity_key = "::".join((_text(row.get("product_id")), _text(row.get("trial_id"))))
            base_key = _chart_series_key(row)
            variant = series_variant_by_row[index]
            if len(details_by_variant[(identity_key, base_key, variant)]) > 1:
                variant += ":" + _semantic_token(_text(row.get("arm_detail")))
            series_variant_by_row[index] = variant
            series_variants[(identity_key, base_key)].add(variant)
    duplicate_series_keys: dict[int, str] = {}
    for (_identity_key, base_key), variants in series_variants.items():
        if len(variants) < 2:
            continue
        for index in series_indexes[(_identity_key, base_key)]:
            row = records[index][0]
            variant = series_variant_by_row[index]
            suffix = variant or _semantic_token(_text(row.get("row_id"))) or f"group-{index + 1}"
            duplicate_series_keys[index] = f"{base_key}:{suffix}"
    rows: list[dict[str, Any]] = []
    for index, (row, _source) in enumerate(records):
        copied = dict(row)
        copied["_chart_type"] = chart_type
        if identity_aware:
            copied["_chart_identity_key"] = "::".join(
                (_text(copied.get("product_id")), _text(copied.get("trial_id")))
            )
            copied["_chart_identity_label"] = _text(
                copied.get("identity_label_zh"),
                "｜".join(
                    item
                    for item in (
                        _text(copied.get("product_zh"), "未列示产品"),
                        _text(copied.get("trial_zh"), "未列示试验"),
                    )
                    if item
                ),
            )
            base_series_key = _chart_series_key(copied)
            series_key = duplicate_series_keys.get(index, base_series_key)
            copied["_chart_series_key"] = series_key
            copied["_chart_series_label"] = _chart_series_label(copied, series_key)
            context_key, context_label = _chart_comparison_context(copied)
            copied["_chart_comparison_context_key"] = context_key
            copied["_chart_comparison_context_label"] = context_label
            copied["_chart_time_key"] = _text(
                copied.get("time_window_band"),
                _text(copied.get("time"), "时间点未列示"),
            )
        rows.append(copied)
    result: dict[str, Any] = {
        "title_zh": title,
        "title_complete": cross_trial,
        "cross_trial": cross_trial,
        "identity_series": identity_aware,
        "rows": rows,
        "scientific_group_id": "b-group-" + hashlib.sha256(_canonical_json(sorted(
            (str(row["row_id"]), semantic_row_digest(row)) for row, _source in records
        ))).hexdigest(),
    }
    if x_axis_label_zh:
        result["x_axis_label_zh"] = x_axis_label_zh
    if y_axis_label_zh:
        result["y_axis_label_zh"] = y_axis_label_zh
    if size_label_zh:
        result["size_label_zh"] = size_label_zh
    return result


def _project_scientific_groups(
    groups: Sequence[dict[str, Any]],
    records: Sequence[tuple[dict[str, Any], Any]],
) -> tuple[dict[str, Any], ...]:
    """Select already-adjudicated observations without recomputing membership."""
    selected = {str(row["row_id"]): row for row, _source in _dedupe_records(records)}
    available = {str(row["row_id"]): row for group in groups for row in group["rows"]}
    for row_id, row in selected.items():
        original = available.get(row_id)
        if original is None:
            raise ValueError("页面观察不属于完整科学视图")
        if (row.get("_domain") != original.get("_domain") or
                semantic_row_digest(row) != semantic_row_digest(original)):
            raise ValueError("页面观察域或事实摘要与完整科学视图不一致")
    result: list[dict[str, Any]] = []
    for group in groups:
        rows = []
        for row in group["rows"]:
            selected_row = selected.get(str(row["row_id"]))
            if selected_row is None:
                continue
            copied = dict(row)
            if "_user_edit" in selected_row:
                copied["_user_edit"] = selected_row["_user_edit"]
            rows.append(copied)
        if rows:
            result.append({**group, "rows": rows,
                           "cross_trial": _bucket_spans_trials([(row, None) for row in rows])})
    return tuple(result)


def _semantic_group_key(
    row: Mapping[str, Any],
    *,
    include_time: bool,
    include_domain: bool = False,
    include_population: bool = True,
    include_statistic: bool = True,
    include_unit: bool = True,
) -> tuple[str, ...]:
    values = [
        _text(row.get("clinical_concept"), _text(row.get("display_label_zh"), "clinical-concept")),
    ]
    if include_statistic:
        values.append(
            _text(
                row.get("statistical_form_family"),
                _text(row.get("statistic_form"), "statistic-not-reported"),
            )
        )
    if include_unit:
        values.append(_text(row.get("unit"), "unit-not-reported"))
    if include_population:
        values.append(
            _text(
                row.get("population_context"),
                _text(row.get("population"), "population-not-reported"),
            )
        )
    if include_domain:
        values.append(_text(row.get("field_family"), "field-not-reported"))
    if include_time:
        values.append(
            _text(row.get("time_window_band"), _text(row.get("time"), "time-not-reported"))
        )
    if row.get("_domain") in {"efficacy", "safety"}:
        values.extend(
            (
                _text(
                    row.get("semantic_definition"),
                    _text(row.get("original_definition"), "definition-not-reported"),
                ),
                _text(row.get("semantic_direction"), "direction-not-reported"),
                _text(row.get("semantic_estimand"), "estimand-not-reported"),
                _text(
                    row.get("semantic_denominator"),
                    _text(row.get("denominator_role"), "denominator-not-reported"),
                ),
                _text(
                    row.get("semantic_analysis_set"),
                    _text(row.get("population_context"), "analysis-set-not-reported"),
                ),
                _text(
                    row.get("semantic_analysis_form"),
                    _text(row.get("statistical_form_family"), "analysis-form-not-reported"),
                ),
                _text(
                    row.get("semantic_instrument_or_scale"),
                    "instrument-or-scale-not-reported",
                ),
            )
        )
    return tuple(values)


def _sorted_bucket(
    bucket: Sequence[tuple[dict[str, Any], Any]],
) -> tuple[tuple[dict[str, Any], Any], ...]:
    def key(item: tuple[dict[str, Any], Any]) -> tuple[str, ...]:
        row = item[0]
        arm_role = _text(row.get("arm_role"), "unknown")
        arm_priority = {
            "treatment": "0",
            "control": "1",
            "single_arm": "2",
            "unknown": "3",
        }.get(arm_role, "9")
        return (
            _text(row.get("product_id")),
            _text(row.get("trial_id")),
            arm_priority,
            arm_role,
            _text(row.get("group_id")),
            _text(row.get("time_window_band"), _text(row.get("time"))),
            _text(row.get("actual_timepoint")),
            _text(row.get("row_id")),
        )

    return tuple(sorted(bucket, key=key))


def _cross_trial_groups(
    records: Sequence[tuple[dict[str, Any], Any]],
    *,
    page_id: str,
    domain: str,
    include_time: bool,
    chart_type: str | None = None,
    semantic_proposals: Sequence[SemanticGroupingProposal] = (),
    semantic_adjudications: Sequence[ApprovedSemanticMerge] = (),
) -> tuple[dict[str, Any], ...]:
    buckets: dict[tuple[str, ...], list[tuple[dict[str, Any], Any]]] = defaultdict(list)
    if domain in {"efficacy", "safety"}:
        # 跨试验可比域的成员裁决唯一真源在科学层；渲染器只做展示组装。
        membership = adjudicate_comparable_membership(
            domain, tuple(records),
            bucket_key_fn=lambda row: _semantic_group_key(row, include_time=include_time),
            semantic_proposals=semantic_proposals,
            semantic_adjudications=semantic_adjudications,
        )
        for index, group in enumerate(membership):
            buckets[("__membership__", str(index))] = list(group)
        return _dress_membership_groups(
            membership, page_id=page_id, domain=domain, include_time=include_time,
            chart_type=chart_type, semantic_proposals=semantic_proposals,
        )
    for item in records:
        row = item[0]
        key = _semantic_group_key(row, include_time=include_time)
        if any(semantic_value_is_unknown(value) for value in key):
            # Retain source observations, but unknown axes cannot license cross-trial comparison.
            # Without a trial identity even a within-trial descriptive grouping is unproven.
            key += (
                "source-specific",
                _text(row.get("product_id")),
                _text(row.get("trial_id"), _text(row.get("row_id"))),
            )
        buckets[key].append(item)
    merged = proposed_semantic_buckets(
        tuple(buckets.values()), semantic_proposals,
        approved_merges=semantic_adjudications,
    )
    return _dress_membership_groups(
        tuple(tuple(bucket) for bucket in merged),
        page_id=page_id, domain=domain, include_time=include_time,
        chart_type=chart_type, semantic_proposals=semantic_proposals,
    )


def _dress_membership_groups(
    membership: Sequence[Sequence[tuple[dict[str, Any], Any]]],
    *,
    page_id: str,
    domain: str,
    include_time: bool,
    chart_type: str | None,
    semantic_proposals: Sequence[SemanticGroupingProposal],
) -> tuple[dict[str, Any], ...]:
    """把科学层成员组组装为门户图表组（标题/排序/图形类型，不裁决成员）。"""
    buckets = {
        (*_semantic_group_key(bucket[0][0], include_time=include_time), str(index)):
        list(bucket)
        for index, bucket in enumerate(membership)
    }
    groups: list[dict[str, Any]] = []
    bucket_keys = sorted(
        buckets,
        key=lambda key: (
            not any(item[0].get("renderable") for item in buckets[key]),
            key,
        ),
    )
    for key in bucket_keys:
        bucket = _sorted_bucket(buckets[key])
        first = bucket[0][0]
        times = {
            _text(row.get("time_window_band"), _text(row.get("time")))
            for row, _source in bucket
            if _text(row.get("time_window_band"), _text(row.get("time")))
        }
        resolved_chart_type = chart_type or (
            "line" if page_id == "longitudinal-results" and len(times) > 1 else "bar"
        )
        title = _group_title(first, domain=domain, include_time=include_time)
        ids = {str(row["row_id"]) for row, _source in bucket}
        if any(set(proposal.row_ids).issubset(ids) for proposal in semantic_proposals):
            actual_times = tuple(dict.fromkeys(
                f'{row.get("actual_timepoint")} '
                + {"week": "周", "day": "天", "month": "个月", "year": "年"}.get(
                    str(row.get("actual_timepoint_unit")), str(row.get("actual_timepoint_unit")),
                )
                for row, _source in bucket
            ))
            title += " · 实际观察时间：" + " / ".join(actual_times)
        # 独立复核 B r39（issue-2）：合并标记按"事实是否发生"判定——
        # 仅当桶内确实合并了多个登记臂（或分组键含未知值且臂缺失）时标注；
        # 此前按分组键含未知值判定，834 张组别完整的图被错误标注
        bucket_arms = {
            _text(r.get("arm"))
            for r, _s in bucket
            if _text(r.get("arm"))
        }
        if any(semantic_value_is_unknown(value) for value in key) and not bucket_arms:
            title += " · 该组部分观察的登记分组信息不全，已按试验合并展示"
        elif len(bucket_arms) > 1:
            title += " · 多登记臂已合并展示"
        group = _group(
            title,
            bucket,
            chart_type=resolved_chart_type,
            cross_trial=_bucket_spans_trials(bucket),
            identity_series=True,
            x_axis_label_zh="产品｜试验",
        )
        group["title_complete"] = True
        if page_id == "longitudinal-results":
            values = [
                float(row["numeric_value"])
                for row, _source in bucket
                if isinstance(row.get("numeric_value"), (int, float))
                and not isinstance(row.get("numeric_value"), bool)
            ]
            if values:
                group["y_axis_min"] = min(0.0, min(values))
                group["y_axis_max"] = max(0.0, max(values))
        groups.append(group)
    return tuple(_disambiguate_group_titles(groups))


def _disambiguate_group_titles(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """同页标题逐字相同的图卡消歧（独立复核 B r35 veto）。

    以组内登记测量原文（semantic_definition/original_definition）签名区分；
    原文一致者按登记终点定义序号显式标注，使数值可唯一归属。
    """
    by_title: dict[str, list[dict[str, Any]]] = {}
    import re as _re
    for group in groups:
        # 剥离此前 pass 加的序号后缀，页级统一重新编号（幂等）
        base = _re.sub(r"（登记终点定义(?:变体)?\d*）$", "", str(group.get("title_zh")))
        group["title_zh"] = base
        by_title.setdefault(base, []).append(group)
    for title, dups in by_title.items():
        if len(dups) < 2:
            continue
        signatures = []
        for group in dups:
            sigs = sorted({
                _text(row.get("semantic_definition"),
                      _text(row.get("original_definition"),
                            _text(row.get("endpoint_source"),
                                  _text(row.get("time"), ""))))
                for row in group.get("rows", ())
            })
            signatures.append("||".join(sigs))
        # 无论签名是否相异，同名图卡一律顺序编号，保证页内标题唯一可归属；
        # 序号同时落到行级 _endpoint_ordinal（下划线键不参与事实摘要），
        # 展开表按行也能归属到具体终点定义
        for i, group in enumerate(dups, start=1):
            group["title_zh"] = f"{title}（登记终点定义{i}）"
            for row in group.get("rows", ()):
                row["_endpoint_ordinal"] = f"登记终点定义{i}"
    return groups


def _baseline_bucket_sort_key(key: tuple[str, ...]) -> tuple[int, tuple[str, ...]]:
    concept = key[0] if key else ""
    for rank, family in enumerate(_BASELINE_CONCEPT_FAMILY_ORDER):
        if _semantic_token(concept) in family:
            return (rank, key)
    return (len(_BASELINE_CONCEPT_FAMILY_ORDER), key)


def _bucket_spans_trials(bucket: Sequence[tuple[dict[str, Any], Any]]) -> bool:
    trial_ids = {
        _text(row.get("trial_id"))
        for row, _source in bucket
        if _text(row.get("trial_id"))
    }
    return len(trial_ids) > 1


_POOL_ADJUDICATION_DOMAINS: dict[str, str] = {
    "efficacy": "efficacy",
    "safety": "safety",
    "baseline": "baseline-overview",
    "disposition": "disposition-overview",
    "matrix": "efficacy-safety-matrix",
    "supporting": "subgroups-supporting-evidence",
}


def _adjudicate_full_pool(
    records: Sequence[tuple[dict[str, Any], Any]],
    *,
    semantic_proposals: Sequence[SemanticGroupingProposal],
    semantic_adjudications: Sequence[ApprovedSemanticMerge] = (),
) -> tuple[dict[str, Any], ...]:
    """完整观察池一次裁决的唯一入口；详情子集不得进入。

    全池语境下，引用不存在观察的提案是陈旧或错误输入，必须拒绝；
    跨域提案在分域前拒绝；未知域记录失败关闭。
    """
    pool = _dedupe_records(records)
    # 池级校验唯一真源在科学层（域白名单/孤儿/跨域/摘要/外层重验）。
    validate_full_pool_inputs(
        pool,
        semantic_proposals=semantic_proposals,
        semantic_adjudications=semantic_adjudications,
    )
    groups: list[dict[str, Any]] = []
    for domain, domain_page in _POOL_ADJUDICATION_DOMAINS.items():
        selected = [item for item in pool if item[0].get("_domain") == domain]
        if selected:
            groups.extend(_groups_for_page(
                domain_page, selected, semantic_proposals=semantic_proposals,
                semantic_adjudications=semantic_adjudications,
            ))
    return tuple(_disambiguate_group_titles(groups))


def _assert_page_fallback_only_uncovered(
    uncovered: Sequence[tuple[dict[str, Any], Any]],
) -> None:
    """页面回退分组只允许显式合成/空态记录，真实域观察必须经全池裁决。"""
    for row, _source in uncovered:
        domain = _text(row.get("_domain"))
        if (domain in _POOL_ADJUDICATION_DOMAINS
                and not row.get("_synthetic") and not row.get("_empty_state")):
            raise ValueError(
                f"真实域观察（{domain}）未经完整观察池裁决，禁止页面回退重分组"
            )


def _groups_for_page(
    page_id: str,
    records: Sequence[tuple[dict[str, Any], Any]],
    *, semantic_proposals: Sequence[SemanticGroupingProposal] = (),
    semantic_adjudications: Sequence[ApprovedSemanticMerge] = (),
) -> tuple[dict[str, Any], ...]:
    if not records:
        return ()
    records = _records_with_semantics(records, page_id=page_id)
    if page_id in {"overview", "product-trial-profiles"}:
        by_id = {str(row["row_id"]): row for row, _source in _dedupe_records(records)}
        for proposal in semantic_proposals:
            present = [by_id[row_id] for row_id in proposal.row_ids if row_id in by_id]
            if len(present) == 2 and present[0].get("_domain") != present[1].get("_domain"):
                raise ValueError("跨域语义提案不受支持，必须拆分研究问题")
    if page_id in {"efficacy", "longitudinal-results", "subgroups-supporting-evidence"}:
        return _cross_trial_groups(
            records,
            page_id=page_id,
            domain="efficacy",
            include_time=page_id != "longitudinal-results",
            semantic_proposals=semantic_proposals,
            semantic_adjudications=semantic_adjudications,
        )
    if page_id == "safety":
        return _cross_trial_groups(
            records,
            page_id=page_id,
            domain="safety",
            include_time=True,
            chart_type="heatmap",
            semantic_proposals=semantic_proposals,
            semantic_adjudications=semantic_adjudications,
        )
    if page_id == "overview":
        efficacy = [item for item in records if item[0].get("_domain") == "efficacy"]
        safety = [item for item in records if item[0].get("_domain") == "safety"]
        matrix = [item for item in records if item[0].get("_domain") == "matrix"]
        baseline = [item for item in records if item[0].get("_domain") == "baseline"]
        disposition = [item for item in records if item[0].get("_domain") == "disposition"]
        overview_groups: list[dict[str, Any]] = []
        if efficacy:
            overview_groups.extend(_groups_for_page(
                "efficacy", efficacy, semantic_proposals=semantic_proposals,
                semantic_adjudications=semantic_adjudications,
            ))
        if safety:
            overview_groups.extend(_groups_for_page(
                "safety", safety, semantic_proposals=semantic_proposals,
                semantic_adjudications=semantic_adjudications,
            ))
        for related_page_id, related_records in (
            ("efficacy-safety-matrix", matrix),
            ("baseline-overview", baseline),
            ("disposition-overview", disposition),
        ):
            if related_records:
                overview_groups.extend(_groups_for_page(
                    related_page_id, related_records, semantic_proposals=semantic_proposals,
                    semantic_adjudications=semantic_adjudications,
                ))
        return tuple(overview_groups)
    if page_id == "efficacy-safety-matrix":
        chart_type = (
            "bubble" if any(item[0].get("renderable") for item in records) else "status_matrix"
        )
        matrix_groups = []
        typed_facets: dict[
            tuple[str, str, str], list[tuple[dict[str, Any], Any]]
        ] = defaultdict(list)
        for item in records:
            row = item[0]
            typed_facets[(
                _text(row.get("x_unit")),
                _text(row.get("y_unit")),
                _text(row.get("size_basis"), "明确样本量"),
            )].append(item)
        for (x_unit, y_unit, size_basis), facet_records in typed_facets.items():
            # 两组百分比相减得到百分点；原臂的百分比单位仍留在源投影中。
            difference_unit = "百分点" if x_unit == "%" else x_unit
            for bucket in proposed_semantic_buckets(
                (tuple(facet_records),), semantic_proposals, descriptive_only=True,
                approved_merges=semantic_adjudications,
            ):
                group = _group("疗效与安全性观察位置", bucket, chart_type=chart_type)
                if all(row.get("_synthetic") is True for row in group["rows"]):
                    group["empty_message"] = "当前未形成可绘制的试验内比较"
                group.update(
                    x_axis_label_zh=f"试验内疗效差（{difference_unit or '数值'}）",
                    y_axis_label_zh=f"治疗组安全性观察值（{y_unit or '数值'}）",
                    size_label_zh=f"气泡大小：{size_basis}",
                    x_unit=difference_unit,
                    y_unit=y_unit,
                    size_basis=size_basis,
                )
                matrix_groups.append(group)
        return tuple(matrix_groups)
    if page_id in _BASELINE_PAGE_IDS:
        buckets: dict[tuple[str, ...], list[tuple[dict[str, Any], Any]]] = defaultdict(list)
        for item in records:
            buckets[
                _semantic_group_key(
                    item[0],
                    include_time=True,
                    include_domain=True,
                    include_population=True,
                    include_statistic=False,
                    include_unit=False,
                )
                + (
                    # 第十三轮复核修复：粗粒度统计族参与分组——
                    # 均值/中位数等中心趋势可并图，计数/比例不得与连续量混轴
                    _BASELINE_STAT_FAMILY.get(
                        _text(item[0].get("statistic_form"), "other"), "central"),
                )
            ].append(item)
        groups: list[dict[str, Any]] = []
        baseline_buckets = proposed_semantic_buckets(
            tuple(buckets[key] for key in sorted(buckets, key=_baseline_bucket_sort_key)),
            semantic_proposals, descriptive_only=True,
            approved_merges=semantic_adjudications,
        )
        for raw_bucket in baseline_buckets:
            bucket = _sorted_bucket(raw_bucket)
            first = bucket[0][0]
            chart_type = (
                "bar" if any(item[0].get("renderable") for item in bucket) else "status_matrix"
            )
            statistic_labels = tuple(
                dict.fromkeys(
                    _text(
                        row.get("statistical_form_family_label_zh"),
                        _text(row.get("statistic_form"), "报告未注明统计口径"),
                    )
                    for row, _source in bucket
                )
            )
            # 独立复核第二十轮 veto：同图多统计口径时不再把"未注明"占位与
            # 具体口径并列入标题；单位同理做包含去重，登记原串与规范串不重复展示
            if len(statistic_labels) > 1:
                statistic_labels = tuple(
                    label for label in statistic_labels
                    if label not in ("报告未注明统计口径", "其他统计形式")
                ) or ("报告未注明统计口径",)
            title = _group_title(
                first,
                domain="baseline",
                include_population=True,
                include_statistic=len(statistic_labels) == 1,
            )
            if len(statistic_labels) > 1:
                title += " · 统计形式：" + "/".join(statistic_labels)
            unit_labels = tuple(
                dict.fromkeys(_text(row.get("unit"), "单位未列示") for row, _source in bucket)
            )
            if len(unit_labels) > 1:
                folded = [u.casefold() for u in unit_labels]
                # 保留更短（更规范）的写法：若另一单位是本单位的真子串，本单位为冗长原串
                unit_labels = tuple(
                    u for i, u in enumerate(unit_labels)
                    if not any(
                        folded[i] != folded[j] and folded[j] in folded[i]
                        for j in range(len(unit_labels))
                    )
                )
            if len(unit_labels) > 1:
                title += " · 单位：" + "/".join(unit_labels)
            group = _group(
                title,
                bucket,
                chart_type=chart_type,
                cross_trial=_bucket_spans_trials(bucket),
                x_axis_label_zh="产品｜试验",
            )
            group["title_complete"] = True
            groups.append(group)
        return tuple(groups)
    if page_id in _DISPOSITION_PAGE_IDS:
        disposition_buckets: dict[tuple[str, ...], list[tuple[dict[str, Any], Any]]] = defaultdict(
            list
        )
        for item in records:
            disposition_buckets[
                _semantic_group_key(item[0], include_time=True, include_domain=False)
            ].append(item)
        groups = []
        for raw_bucket in proposed_semantic_buckets(
            tuple(disposition_buckets[key] for key in sorted(disposition_buckets)),
            semantic_proposals, descriptive_only=True,
            approved_merges=semantic_adjudications,
        ):
            bucket = _sorted_bucket(raw_bucket)
            first = bucket[0][0]
            chart_type = (
                "bar" if any(item[0].get("renderable") for item in bucket) else "status_matrix"
            )
            group = _group(
                _group_title(first, domain="disposition"),
                bucket,
                chart_type=chart_type,
                cross_trial=_bucket_spans_trials(bucket),
                x_axis_label_zh="产品｜试验",
            )
            group["title_complete"] = True
            groups.append(group)
        return tuple(groups)
    if page_id == "trial-exposure-context":
        return (_group("试验规模与研究角色", records, chart_type="bar"),)
    if page_id == "product-trial-profiles":
        # 页面入口只服务合成/覆盖状态展示；真实域观察的科学分组必须来自
        # _adjudicate_full_pool 的投影，不得用筛选子集重新裁决。
        real_domains = {
            _text(item[0].get("_domain"))
            for item in records
        } - {"profile", "", "generic"}
        if real_domains:
            raise ValueError(
                "产品/试验档案页收到真实域观察，必须走完整观察池裁决入口："
                + ", ".join(sorted(real_domains))
            )
        if all(_text(item[0].get("_domain")) in {"profile", ""} for item in records):
            return (_group("产品与试验覆盖", records, chart_type="status_matrix"),)
        return ()
    return (_group("当前页面记录", records, chart_type="bar"),)


def _filter_dimensions(
    records: Sequence[tuple[dict[str, Any], Any]],
    targets: Mapping[str, str] | None = None,
) -> tuple[dict[str, str], ...]:
    target_by_product = targets or {}
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for row, _source in records:
        row_id = _text(row.get("row_id"))
        if not row_id or row_id in seen:
            continue
        seen.add(row_id)
        product_id = _text(row.get("product_id"))
        # 独立复核第二十三轮 veto：组别筛选值显示登记臂名，不显示内部组标识
        _arm_display = _text(row.get("arm"), "")
        _raw_group = re.sub(r"^nct[0-9]+-arm-", "", _text(
            row.get("group"), _arm_display or "组别未列示"
        )) or "组别未列示"
        _group_value = (
            _raw_group
            if _arm_display in ("治疗组", "对照组", "单臂", "组别未列示", "")
            else _arm_display
        )
        # 独立复核 A r47（issue-3）：筛选维度组名残留英文按惯例标注
        if (
            _group_value
            and _group_value not in ("治疗组", "对照组", "单臂", "组别未列示")
            and re.findall(r"[A-Za-z]{3,}", _group_value)
            and not _group_value.endswith("（登记原文，未译）")
        ):
            _group_value = _group_value + "（登记原文，未译）"
        result.append(
            {
                "id": row_id,
                "product": product_id,
                "target": _text(row.get("target"), target_by_product.get(product_id, "")),
                "trial": _text(row.get("trial_id")),
                "group": _group_value,
                "arm_role": _text(row.get("arm_role")),
                "element": _text(
                    row.get("clinical_concept_label_zh"),
                    _text(
                        row.get("display_label_zh"),
                        _text(row.get("element"), "研究记录"),
                    ),
                ),
                "clinical_concept": _text(row.get("clinical_concept")).split(":")[-1],
                "polarity": _text(row.get("polarity"), "affirmed"),
                "seriousness": _text(row.get("seriousness"), "unspecified"),
                "teae": (
                    "true" if row.get("teae") is True
                    else "false" if row.get("teae") is False else "unknown"
                ),
                "relatedness": _text(row.get("relatedness"), "unspecified"),
                "count_basis": _text(row.get("count_basis"), "participants"),
                "time": _text(row.get("time"), "时间点未列示"),
                "time_window": _text(row.get("time_window")),
                "time_window_band": _text(row.get("time_window_band")).split(":")[-1],
                "population": _text(row.get("population")),
                "population_context": _text(row.get("population_context")).split(":")[-1],
                "field_family": _text(row.get("field_family")),
                "reason": _text(row.get("reason")),
                "denominator_role": _text(row.get("denominator_role")),
                "measure_object": _text(row.get("measure_object")),
                "statistic_form": _text(row.get("statistic_form")),
                "statistical_form_family": _text(row.get("statistical_form_family")),
                "cohort": _text(row.get("cohort")),
                "period": _text(row.get("period")),
                "disclosure_state": _text(row.get("disclosure_state"), "not_reported"),
            }
        )
    return tuple(result)


_FILTER_WEEK_BAND_RE = re.compile(r"^week_([0-9]+(?:\.[0-9]+)?)$")
_FILTER_DAY_BAND_RE = re.compile(r"^day_([0-9]+(?:\.[0-9]+)?)$")
_FILTER_COHORT_RE = re.compile(r"^cohort\s*(\d+)$")
# 独立复核第二十轮 veto：基线概念内部键 → 中文概念名（图表类别/筛选直出兜底）
_BASELINE_CONCEPT_TOKEN_ZH = {
    "pnh_clone_size": "PNH 克隆大小",
    "free_hemoglobin": "游离血红蛋白",
    "free_hemoglobin_pct": "游离血红蛋白变化（%）",
    "hemoglobin": "血红蛋白",
    "ldh": "乳酸脱氢酶",
    "ldh_uln_ratio": "LDH/ULN 比值",
    "sample_size": "样本量",
    "age": "年龄",
    "sex": "性别",
    "easi": "EASI",
    "baseline_easi": "基线EASI",
}
_FILTER_STATIC_LABELS = {
    "treatment": "治疗组",
    "control": "对照组",
    "single_arm": "单臂",
    "unknown": "未列示",
    "not_reported": "未列示",
    "all": "登记全队列",
    "received_treatment": "接受治疗",
    "completed_treatment": "完成治疗",
    "participant_flow": "受试者流转",
    "baseline_sample_size": "基线样本量",
    "sample_size": "样本量",
    "baseline_pnh_clone_size": "PNH 克隆大小",
    "baseline_free_hemoglobin": "游离血红蛋白",
    "baseline_hemoglobin": "基线血红蛋白",
    "baseline_ldh": "基线乳酸脱氢酶",
    "baseline_easi": "基线EASI",
    "baseline_age": "基线年龄",
    # 独立复核第二十九轮：披露状态筛选键映射中文（与表格列口径一致）
    "reported_value": "已报告值",
    "reported_zero": "已报告零值",
    "not_applicable": "不适用",
    "pnh_clone_size": "PNH 克隆大小",
    "free_hemoglobin": "游离血红蛋白",
    "free_hemoglobin_pct": "游离血红蛋白变化（%）",
    "hemoglobin": "血红蛋白",
    "ldh": "LDH",
    "ldh_uln_ratio": "LDH/ULN 比值",
    "transfusion_burden": "输血负担",
    "transfusion_burden_change": "输血次数变化",
    "rbc_units_burden": "红细胞单位输注数",
    "rbc_units_change": "红细胞单位输注变化",
    "adherence_summary": "依从性概览",
    **_STATISTICAL_FORM_LABELS,
    **_TIME_BAND_LABELS,
}


def _filter_value_label_zh(dimension: str, value: Any, label: Any) -> str:
    """筛选按钮文本中文兜底：剥前缀键、清洗拼接尾、映射已知令牌。

    独立复核第八轮：label 字段本身可能已被上游写入内部键
    （如 population:登记结果人群fullanalysis），不得因其含中文而照抄。
    """
    for candidate in (label, value):
        text = str(candidate or "").strip()
        if not text:
            continue
        if ":" in text:
            tail = text.split(":", 1)[1].strip()
            if tail and re.search(r"[\u4e00-\u9fff]", tail):
                return tail
        zh_trim = re.sub(r"[A-Za-z0-9_.\-]+$", "", text)
        if zh_trim and re.search(r"[\u4e00-\u9fff]", zh_trim):
            return zh_trim
        mapped = _FILTER_STATIC_LABELS.get(text)
        if mapped:
            return mapped
    text = str(value or "")
    week = _FILTER_WEEK_BAND_RE.match(text)
    if week:
        return f"第{float(week.group(1)):g}周"
    day = _FILTER_DAY_BAND_RE.match(text)
    if day:
        return f"第{float(day.group(1)):g}天"
    cohort = _FILTER_COHORT_RE.match(text.casefold())
    if cohort:
        return f"第{int(cohort.group(1))}队列"
    if text.startswith("nct") and text.endswith("-all"):
        return "登记全队列"
    period_match = re.match(r"^(nct[0-9]+)-p(\d+)$", text)
    if period_match:
        return f"第{int(period_match.group(2))}治疗期"
    # 独立复核 B r58（issue-1）：登记长句/机器拼接串直出前按惯例标注，
    # 不再伪装中文标签
    if re.findall(r"[A-Za-z]{3,}", text) and not re.search(r"[\u4e00-\u9fff]", text):
        short = " ".join(text.split())
        return (short[:28] + "…") if len(short) > 28 else short
    # 独立复核 B r60（issue-2）：形态质量门槛（B r53 口径）——中英混排且
    # 含机器拼接碎片（change/duration/drug 等未转写词或 2–5 字母小写残片）
    # 的串判定为转写失败，按惯例标注，不冒充已译口径
    if re.search(r"[\u4e00-\u9fff]", text) and re.search(
        r"\b[a-z]{2,5}\b|changefrom|研究 drug|duration", text, re.I
    ):
        return text + "（登记原文，未译）"
    return text


def _filter_groups(
    filter_rows: Sequence[Any],
    names: Mapping[str, str],
    trial_names: Mapping[str, str],
    *,
    page_id: str,
) -> tuple[dict[str, Any], ...]:
    """筛选面板分组：维度 → 候选值（含中文标签），组名按页面语境命名。"""
    dimensions = (
        "product", "target", "trial", "group", "arm_role", "element",
        "clinical_concept", "polarity", "seriousness", "teae", "relatedness", "count_basis",
        "time", "time_window", "time_window_band",
        "population", "population_context", "field_family", "reason",
        "denominator_role", "measure_object", "statistic_form",
        "statistical_form_family", "cohort", "period", "disclosure_state",
    )
    collected: dict[str, list[str]] = {dimension: [] for dimension in dimensions}

    def _row_field(row: Any, key: str) -> Any:
        if isinstance(row, Mapping):
            return row.get(key)
        return getattr(row, key, None)

    def _row_values(row: Any, key: str) -> tuple[Any, ...]:
        value = _row_field(row, key)
        if value is None:
            return ()
        if isinstance(value, (str, bytes)):
            return (value,)
        if isinstance(value, (list, tuple, set, frozenset)):
            return tuple(value)
        return (value,)

    for row in filter_rows:
        for dimension in dimensions:
            for value in _row_values(row, dimension):
                text = str(value)
                if text and text not in collected[dimension]:
                    collected[dimension].append(text)
    groups: list[dict[str, Any]] = []
    for dimension in dimensions:
        values = collected.get(dimension) or []
        if not values:
            continue
        # 独立复核 B r39（issue-4）：分组标题按维度命名，
        # 不再整页复用主题词（此前 13 个分组标题全部同名）
        dimension_labels = {
            "product": "产品", "target": "靶点/机制", "trial": "试验",
            "group": "组别", "arm_role": "组别角色", "element": "设计要素",
            "clinical_concept": "临床概念", "time": "时间点", "time_window": "时间窗",
            "polarity": "否定/肯定", "seriousness": "严重性", "teae": "TEAE语义",
            "relatedness": "相关性", "count_basis": "计数基础",
            "time_window_band": "时间窗分组", "population": "人群",
            "population_context": "分析人群", "field_family": "字段族",
            "reason": "原因", "denominator_role": "分母角色",
            "measure_object": "计量对象", "statistic_form": "统计形式",
            "statistical_form_family": "统计口径", "cohort": "队列",
            "period": "周期", "disclosure_state": "披露状态",
        }
        label = dimension_labels.get(dimension, dimension)
        options = []
        label_fields = {
            "clinical_concept": "clinical_concept_label_zh",
            "time_window_band": "time_window_band_label_zh",
            "population_context": "population_context_label_zh",
            "statistical_form_family": "statistical_form_family_label_zh",
            "arm_role": "arm_role_label_zh",
        }
        for value in values:
            option_label = None
            if dimension == "product":
                option_label = names.get(value, value)
            elif dimension == "trial":
                option_label = trial_names.get(value, value)
            elif dimension == "disclosure_state":
                option_label = _state_label(value)
            elif dimension in label_fields:
                option_label = next(
                    (
                        _text(_row_field(row, label_fields[dimension]))
                        for row in filter_rows
                        if _text(_row_field(row, dimension)) == value
                        and _text(_row_field(row, label_fields[dimension]))
                    ),
                    value,
                )
                # 独立复核第四十三轮：未映射的概念键走 _CLINICAL_CONCEPT_LABELS 查表
                if option_label == value and value in _CLINICAL_CONCEPT_LABELS:
                    option_label = _CLINICAL_CONCEPT_LABELS[value]
            else:
                option_label = value
            # 中文原生兜底：canonical 令牌/合成键不得直接作为按钮文本
            option_label = _filter_value_label_zh(dimension, value, option_label)
            # 独立复核 B r39（issue-4）：残余英文/内部串经漏斗转写；
            # 披露状态值不得混入指标/概念等分组
            if dimension not in {"product", "trial", "disclosure_state"}:
                if value in {"未公开披露", "未公开", "not_reported"}:
                    continue
                zh = _b_native_label(str(option_label))
                option_label = zh if zh else option_label
            # 独立复核 B r43（issue-3）：时间窗/时间点维度接确定性时间转写
            if dimension in {"time_window", "timepoint", "time"}:
                zh_t = _native_timepoint_zh(str(option_label))
                if zh_t != "登记时间窗（详见登记来源）":
                    option_label = zh_t
            options.append({"value": value, "label": option_label})
        groups.append({"dimension": dimension, "label": label, "options": tuple(options)})
    return tuple(_disambiguate_group_titles(groups))


def _display_trial_name(trial: TrialRow, product_name: str) -> str:
    del product_name
    return trial.name


def _nav_groups(catalog: ReportCatalog, *, prefix: str, current: str) -> tuple[dict[str, Any], ...]:
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
    return tuple(_disambiguate_group_titles(groups))


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
    ):
        shutil.copy2(resolve_portal_asset(name), assets / name)
    shutil.copy2(_ASSET_DIR / "report-b.css", assets / "report-b.css")
    shutil.copy2(_ASSET_DIR / "report-b.js", assets / "report-b.js")
    shutil.copy2(resolve_echarts_bundle(), assets / "echarts.min.js")


def _tag_records(
    values: Sequence[tuple[dict[str, Any], Any]],
    domain: str,
) -> tuple[tuple[dict[str, Any], Any], ...]:
    return tuple(({**row, "_domain": domain}, source) for row, source in values)


def _page_records(
    data: ReportBPortalData,
    *,
    page_id: str,
    names: Mapping[str, str],
    trial_names: Mapping[str, str],
    efficacy: Sequence[tuple[dict[str, Any], Any]],
    safety: Sequence[tuple[dict[str, Any], Any]],
) -> tuple[tuple[dict[str, Any], Any], ...]:
    return _without_declared_shadow_pairs(_page_records_unfiltered(
        data, page_id=page_id, names=names, trial_names=trial_names,
        efficacy=efficacy, safety=safety,
    ))


def _without_declared_shadow_pairs(
    records: Sequence[tuple[dict[str, Any], Any]],
) -> tuple[tuple[dict[str, Any], Any], ...]:
    """会商 round-4 #4：-declared 影子行在页面记录总出口过滤——
    任何页面域（含 subgroups/matrix）都不再泄漏到表格与证据视图。"""
    return tuple(
        (row, source)
        for row, source in records
        if not _row_is_declared_shadow(row)
    )


def _page_records_unfiltered(
    data: ReportBPortalData,
    *,
    page_id: str,
    names: Mapping[str, str],
    trial_names: Mapping[str, str],
    efficacy: Sequence[tuple[dict[str, Any], Any]],
    safety: Sequence[tuple[dict[str, Any], Any]],
) -> tuple[tuple[dict[str, Any], Any], ...]:
    def tagged(
        values: Sequence[tuple[dict[str, Any], Any]],
        domain: str,
    ) -> list[tuple[dict[str, Any], Any]]:
        result: list[tuple[dict[str, Any], Any]] = []
        for row, source in values:
            copied = dict(row)
            copied["_domain"] = domain
            result.append((copied, source))
        return result

    if page_id == "overview":
        baseline = _page_records(
            data,
            page_id="baseline-overview",
            names=names,
            trial_names=trial_names,
            efficacy=efficacy,
            safety=safety,
        )
        disposition = _page_records(
            data,
            page_id="disposition-overview",
            names=names,
            trial_names=trial_names,
            efficacy=efficacy,
            safety=safety,
        )
        matrix = _matrix_records(data, names, trial_names)
        return _dedupe_records(
            (
                *tagged(efficacy, "efficacy"),
                *tagged(safety, "safety"),
                *tagged(matrix, "matrix"),
                *tagged(baseline, "baseline"),
                *tagged(disposition, "disposition"),
            )
        )
    if page_id in {"efficacy", "longitudinal-results"}:
        return tuple(tagged(efficacy, "efficacy"))
    if page_id == "subgroups-supporting-evidence":
        return _state_rows_from_view(
            data,
            view_name="supporting_evidence_views",
            page_id=page_id,
            names=names,
            trial_names=trial_names,
            domain="supporting",
        )
    if page_id == "safety":
        return tuple(tagged(safety, "safety"))
    if page_id in _BASELINE_PAGE_IDS:
        values = _state_rows_from_view(
            data,
            view_name="baseline_views",
            page_id=page_id,
            names=names,
            trial_names=trial_names,
            domain="baseline",
        )
        allowed = _BASELINE_PAGE_CONCEPTS.get(page_id)
        if allowed is not None:
            values = tuple(
                item for item in values if _text(item[0].get("clinical_concept")) in allowed
            )
        if values or _view_source(data, "baseline_views") is not None:
            return values
        return _domain_empty_records(
            data,
            page_id=page_id,
            names=names,
            trial_names=trial_names,
            domain="baseline",
        )
    if page_id in _DISPOSITION_PAGE_IDS:
        values = _state_rows_from_view(
            data,
            view_name="disposition_views",
            page_id=page_id,
            names=names,
            trial_names=trial_names,
            domain="disposition",
        )
        allowed = _DISPOSITION_PAGE_ELEMENTS[page_id]
        values = tuple(
            item
            for item in values
            if _text(item[0].get("element"), _text(item[0].get("display_label_zh"))) in allowed
        )
        if values or _view_source(data, "disposition_views") is not None:
            return values
        return _domain_empty_records(
            data,
            page_id=page_id,
            names=names,
            trial_names=trial_names,
            domain="disposition",
        )
    if page_id == "efficacy-safety-matrix":
        values = _matrix_records(data, names, trial_names)
        if values:
            return values
        return _synthetic_status_records(
            data,
            page_id=page_id,
            names=names,
            trial_names=trial_names,
            domain="matrix",
        )
    if page_id == "trial-exposure-context":
        return _trial_context_records(data, names, trial_names)
    if page_id == "product-trial-profiles":
        return _synthetic_status_records(
            data,
            page_id=page_id,
            names=names,
            trial_names=trial_names,
            include_products=True,
            domain="profile",
        ) + _synthetic_status_records(
            data,
            page_id=page_id + "-trial",
            names=names,
            trial_names=trial_names,
            domain="profile",
        )
    return tuple(efficacy) or tuple(safety)


def _external_source_entries(data: ReportBPortalData) -> tuple[dict[str, str | None], ...]:
    entries: list[dict[str, str | None]] = []
    seen: set[str] = set()
    for source in data.sources:
        label = _text(getattr(source, "source", None))
        if not label or label in seen:
            continue
        seen.add(label)
        url_match = re.search(r"https?://[^\s<>\"']+", label, flags=re.IGNORECASE)
        entries.append(
            {
                "label": label,
                "url": None if url_match is None else url_match.group(0).rstrip(".,;"),
                "scope": _text(getattr(source, "scope", None)),
                "limitation": _text(getattr(source, "limitation", None)),
            }
        )
    return tuple(entries)


def _disposition_pool_records(
    data: ReportBPortalData,
    *,
    names: Mapping[str, str],
    trial_names: Mapping[str, str],
) -> tuple[tuple[dict[str, Any], Any], ...]:
    """完整观察池消费全量处置记录；各处置子页只是其元素级投影。

    子页（adherence/participant-flow 等）按元素过滤，若池只收集
    disposition-overview 的过滤结果，子页记录将绕过全池裁决。
    """
    values = _state_rows_from_view(
        data,
        view_name="disposition_views",
        page_id="disposition-overview",
        names=names,
        trial_names=trial_names,
        domain="disposition",
    )
    if values or _view_source(data, "disposition_views") is not None:
        return values
    return _domain_empty_records(
        data,
        page_id="disposition-overview",
        names=names,
        trial_names=trial_names,
        domain="disposition",
    )


def semantic_review_domain_inputs(
    data: ReportBPortalData,
) -> dict[str, tuple[tuple[dict[str, Any], Any], ...]]:
    """导出发射语义复核工作项所需的 (域, 观察池)。

    观察池与渲染端全池裁决使用同一构造；初始分桶由
    :func:`semantic_review_buckets_for` 按域给出，保证宿主裁决的
    对选择与渲染端合并语义一致。
    """
    names = {product.id: product.name for product in data.products}
    trial_names = {
        trial.id: _display_trial_name(trial, names.get(trial.product_id, "未列示产品"))
        for trial in data.trials
    }
    efficacy = _tag_records(
        _efficacy_records(data, names, trial_names), "efficacy",
    )
    safety = _tag_records(_safety_records(data, names, trial_names), "safety")
    return {"efficacy": efficacy, "safety": safety}


def semantic_review_buckets_for(
    domain: str,
    records: Sequence[tuple[dict[str, Any], Any]],
) -> tuple[tuple[tuple[dict[str, Any], Any], ...], ...]:
    """按域给出与渲染端一致的初始分桶（科学分区/文本键）。"""
    if domain == "efficacy":
        partition = efficacy_science_partition(records)
        buckets = tuple(tuple(bucket) for bucket in partition.buckets)
        buckets += tuple((record,) for record in partition.unmatched)
        return buckets
    grouped: dict[tuple[str, ...], list[tuple[dict[str, Any], Any]]] = defaultdict(list)
    for item in records:
        grouped[_semantic_group_key(item[0], include_time=True)].append(item)
    return tuple(tuple(grouped[key]) for key in sorted(grouped))


def _render_page_context(
    data: ReportBPortalData,
    *,
    page: StaticPage,
    catalog: ReportCatalog,
    names: Mapping[str, str],
    trial_names: Mapping[str, str],
    efficacy: Sequence[tuple[dict[str, Any], Any]],
    safety: Sequence[tuple[dict[str, Any], Any]],
    scientific_groups: Sequence[dict[str, Any]] = (),
    longitudinal_groups: Sequence[dict[str, Any]] = (),
    prefix: str = "",
    current: str | None = None,
    semantic_adjudications: Sequence[ApprovedSemanticMerge] = (),
    detail_records: Sequence[tuple[dict[str, Any], Any]] | None = None,
    detail_kind: str | None = None,
    detail_id: str | None = None,
    publication_limitation_zh: str | None = None,
) -> dict[str, Any]:
    page_id = current or page.id
    records = (
        tuple(detail_records)
        if detail_records is not None
        else _page_records(
            data,
            page_id=page_id,
            names=names,
            trial_names=trial_names,
            efficacy=efficacy,
            safety=safety,
        )
    )
    records = tuple(
        (
            {
                **row,
                "_user_edit": data.user_edits[str(row["row_id"])].model_dump(mode="json"),
            }
            if str(row.get("row_id")) in data.user_edits
            else row,
            source,
        )
        for row, source in records
    )
    if page_id == "longitudinal-results":
        scientific_groups = longitudinal_groups
    covered_ids = {str(row["row_id"]) for group in scientific_groups for row in group["rows"]}
    covered = [item for item in records if str(item[0]["row_id"]) in covered_ids]
    uncovered = [item for item in records if str(item[0]["row_id"]) not in covered_ids]
    _assert_page_fallback_only_uncovered(uncovered)
    groups = _disambiguate_group_titles(list((
        *_project_scientific_groups(scientific_groups, covered),
        *_groups_for_page(
            page_id, uncovered,
            semantic_proposals=data.semantic_proposals,
            semantic_adjudications=semantic_adjudications,
        ),
    )))
    has_domain_empty_state = bool(records) and all(
        row.get("_empty_state") is True for row, _source in records
    )
    has_drawable_data = any(row.get("renderable") is True for row, _source in records)
    views = tuple(
        _evidence_view(
            data,
            row=row,
            source=source,
            page_id=page.id,
            observation_kind=_observation_kind_for_row(row, page.id),
            names=names,
            trial_names=trial_names,
        )
        for row, source in records
    )
    # 序列化边界复核：本页嵌入前逐条确认来源追溯合同（model_construct 不豁免）
    assert_evidence_views_serializable(views)
    chart_groups_json = _json(groups)
    target_by_product = {product.id: product.target for product in data.products}
    filter_rows = _filter_dimensions(records, target_by_product)
    dimensions = {
        item["id"]: {key: value for key, value in item.items() if key != "id"}
        for item in filter_rows
    }
    filter_groups = _filter_groups(filter_rows, names, trial_names, page_id=page_id)
    essential_filter_dimensions = (
        ("target", "trial", "group", "time")
        if page_id == "overview"
        else ("target", "trial", "group", "element", "time")
    )
    quick_filter_groups = tuple(group for group in filter_groups if group["dimension"] == "product")
    title = page.title_zh
    if detail_kind == "product":
        title = f"{names.get(detail_id or '', '产品')}产品档案"
    elif detail_kind == "trial":
        title = f"{trial_names.get(detail_id or '', '试验')} · 试验档案"
    if page_id in _BASELINE_PAGE_IDS:
        empty_state_title = "暂无公开记录（基线）"
    elif page_id in _DISPOSITION_PAGE_IDS:
        empty_state_title = "暂无公开记录（试验完成情况）"
    else:
        empty_state_title = "当前选择下暂无可比较数据"
    filter_note = "可同时选择多个条件。"
    if page_id == "efficacy-safety-matrix":
        lead = "暂无可绘制的真实疗效—安全性覆盖值，完整比较状态见表。"
    elif page_id in _BASELINE_PAGE_IDS:
        lead = "暂无公开基线记录，完整字段与披露状态见表。"
    elif page_id in _DISPOSITION_PAGE_IDS:
        lead = "暂无公开试验完成情况记录，完整字段与披露状态见表。"
    elif not has_drawable_data:
        lead = "当前没有可绘制的真实数值，完整数据表保留原始披露状态。"
    else:
        lead = page.responsibility_zh
    matrix_unplotted_trials: tuple[str, ...] = ()
    if page_id == "efficacy-safety-matrix":
        plotted_trials = {
            _text(row.get("trial_id"))
            for row, _source in records if row.get("renderable") is True
        }
        related_trials = {
            _text(row.get("trial_id")) for row, _source in efficacy if row.get("trial_id")
        }
        matrix_unplotted_trials = tuple(
            trial_names.get(trial_id, trial_id)
            for trial_id in sorted(related_trials - plotted_trials)
        )
    section_titles = {
        "overview": "关键结果",
        "efficacy": "疗效结果",
        "longitudinal-results": "疗效随访变化",
        "safety": "安全性结果",
        "efficacy-safety-matrix": "疗效与安全性观察位置",
        "baseline-overview": "基线特征",
        "baseline-demographics": "人口学特征",
        "baseline-disease-context": "疾病特征",
        "baseline-severity": "基线疾病严重程度",
        "disposition-overview": "试验完成情况",
        "participant-flow": "受试者流转",
        "adherence": "依从性",
        "loss-exit": "失访与退出",
        "screen-failure": "筛败与原因",
        "rescue-treatment": "补救治疗",
        "prohibited-medication": "禁用药使用",
        "plan-deviation": "方案偏离",
        "trial-exposure-context": "试验与暴露情况",
        "subgroups-supporting-evidence": "亚组与支持证据",
    }
    return {
        "report": data,
        "report_version": data.report_version,
        "report_title": f"{data.indication}临床试验结果比较",
        "overview_conclusions": (
            [
                {"label": "试验宇宙", "text": (
                    f"覆盖 {len(data.products)} 个产品、"
                    f"{len(data.trials)} 项基线信息完整的注册试验；"
                    "宇宙按登记检索全闭包，不以名单排序替代。")},
                {"label": "疗效证据", "text": (
                    "公开疗效观察按登记终点族与观察窗分组呈现，与数据表同源，数值可回溯登记来源；"
                    "特殊观察窗（如基线至某周的窗口期汇总）按窗口口径标注，排除口径见数据依据。")},
                {"label": "安全性证据", "text": (
                    "严重不良事件与死亡病例按登记组别汇总呈现，并附登记的同组风险人数分母。")},
                {"label": "阅读边界", "text": (
                    "不同试验的测量与人群不同，数值不默认可比；跨试验比较以同试验内治疗—对照差值为准。")},
            ]
            if page_id == "overview" and detail_kind is None
            else None
        ),
        "page_title": title,
        "page_id": page.id,
        "page": page,
        "catalog": catalog,
        "site_prefix": prefix,
        "empty_state_title": empty_state_title,
        "has_domain_empty_state": has_domain_empty_state,
        "has_drawable_data": has_drawable_data,
        "filter_note": filter_note,
        "matrix_unplotted_trials": matrix_unplotted_trials,
        "nav_groups": _nav_groups(catalog, prefix=prefix, current=current or page.id),
        "home_href": f"{prefix}{catalog.pages[0].id}.html",
        "data_prefix": f"{prefix}data",
        "asset_prefix": f"{prefix}assets",
        "snapshot_id": _text(data.report_snapshot_id, f"b-{data.report_version}"),
        "row_set_digest": hashlib.sha256(
            _canonical_json([row["row_id"] for row, _source in records])
        ).hexdigest(),
        "lead": lead,
        "section_title": section_titles.get(page_id, title),
        "visuals": page.visuals,
        "records": records,
        "external_sources": _external_source_entries(data),
        "bubble_presets": tuple(item.model_dump(mode="json") for item in BUBBLE_PRESETS),
        "chart_groups_json": chart_groups_json,
        "filter_rows_json": _json(filter_rows),
        "row_dimensions_json": _json(dimensions),
        "filter_groups": filter_groups,
        "essential_filter_dimensions": essential_filter_dimensions,
        "filter_dimensions_json": _json(tuple(_FILTER_DIMENSION_LABELS)),
        "evidence_embed": render_evidence_drawer_embed(views),
        "quick_filter_groups": quick_filter_groups,
        "evidence_host": render_evidence_drawer_host(),
        "filter_products": tuple({"id": p.id, "name": p.name} for p in data.products),
        "filter_trials": tuple(
            {"id": t.id, "name": trial_names.get(t.id, t.name)} for t in data.trials
        ),
        "detail_kind": detail_kind or "",
        "detail_id": detail_id or "",
        "detail_product": names.get(detail_id or "", "") if detail_kind == "product" else "",
        "detail_trial": trial_names.get(detail_id or "", "") if detail_kind == "trial" else "",
        "detail_data_attribute": (
            "data-product-id"
            if detail_kind == "product"
            else "data-trial-id"
            if detail_kind == "trial"
            else ""
        ),
        "publication_limitation_zh": publication_limitation_zh,
    }


def _reset_site_root(site_root: Path) -> None:
    if site_root.exists() and not site_root.is_dir():
        raise ReportBPortalError(f"站点目标不是目录：{site_root}")
    if site_root.exists():
        for child in site_root.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    site_root.mkdir(parents=True, exist_ok=True)


def _project_active_facts_b(
    data: ReportBPortalData,
    active_revision: ActiveFactRevision,
) -> tuple[ReportBPortalData, tuple[PortalConsumerNode, ...]]:
    payload = data.model_dump(mode="python")
    user_edits = dict(data.user_edits)
    consumers: list[PortalConsumerNode] = []
    for fact, binding in active_revision.bindings_for("B"):
        if binding.collection not in {"safety", "efficacy"}:
            raise ReportBPortalError("B renderer只接受safety/efficacy领域绑定")
        collection = cast(list[dict[str, Any]], payload[binding.collection])
        matches = [row for row in collection if str(row.get("row_id")) == binding.row_id]
        if len(matches) != 1:
            raise ReportBPortalError(
                f"B active fact绑定必须命中唯一领域行：{binding.collection}/{binding.row_id}"
            )
        row = matches[0]
        try:
            verified_binding = validate_active_fact_binding(
                fact,
                binding,
                active_fact_binding_for_b(data, binding.collection, binding.row_id),
            )
        except ValueError as error:
            raise ReportBPortalError(str(error)) from error
        fact_extra = fact.model_extra or {}
        if fact_extra.get("review_state") != "user_modified":
            continue
        visible_row_id = str(
            _b_source_view_row(data, binding.collection, binding.row_id)["row_id"]
        )
        unit = str(
            fact_extra.get("normalized_unit")
            or fact_extra.get("unit")
            or row["unit"]
        )
        endpoint = (
            fact_extra.get("endpoint_definition")
            or row.get("term")
            or row.get("endpoint")
        )
        cleared = fact.disclosure_state == "user_cleared"
        narrative = (
            f"{endpoint}：用户清除，待重新核实。"
            if cleared else f"{endpoint}：{fact.raw_value or fact.normalized_value}。"
        )
        original_unit = str(row.get("unit") or "")
        unit_separator = "" if original_unit in {"", "%", "％", "‰", "°C"} else " "
        original_value = (
            "未公开" if row.get("value") is None
            else f"{row['value']:g}{unit_separator}{original_unit}"
        )
        if row.get("numerator") is not None and row.get("denominator") is not None:
            original_value += f" ({row['numerator']}/{row['denominator']})"
        row.update(
            {
                "value": None if cleared else numeric_value(fact),
                "unit": unit,
                "clinical_narrative": narrative,
            }
        )
        if cleared:
            row.update(
                numerator=None,
                denominator=None,
                disclosure_state=(
                    "用户清除，待重新核实"
                    if binding.collection == "safety" else "user_cleared"
                ),
            )
        for field in ("numerator", "denominator"):
            value = fact_extra.get(field)
            if isinstance(value, int):
                row[field] = value
        view_name = f"{binding.collection}_views"
        view = payload.get(view_name)
        view_matches: list[dict[str, Any]] = []
        if isinstance(view, Mapping):
            facts = view.get("facts")
            if isinstance(facts, list):
                view_matches = [
                    candidate
                    for candidate in facts
                    if isinstance(candidate, dict)
                    and str(candidate.get("row_id")) == visible_row_id
                ]
        if view_matches:
            if len(view_matches) != 1:
                raise ReportBPortalError("B active fact领域view行不唯一")
            projected = view_matches[0]
            projected.update(
                {
                    "value": None if cleared else numeric_value(fact),
                    "raw_value": (
                        None if cleared else fact.raw_value or str(fact.normalized_value)
                    ),
                    "unit": unit,
                }
            )
            if cleared:
                projected.update(
                    numerator=None,
                    denominator=None,
                    disclosure_state="user_cleared",
                )
            for field in ("numerator", "denominator"):
                value = fact_extra.get(field)
                if isinstance(value, int):
                    projected[field] = value
        user_edits[visible_row_id] = user_edit_disclosure(
            fact,
            active_revision,
            original_value=original_value,
        )
        page = "safety.html" if binding.collection == "safety" else "efficacy.html"
        consumers.append(
            PortalConsumerNode(
                report="B",
                fact_id=fact.fact_id,
                fact_version_id=fact.fact_version_id,
                collection=binding.collection,
                row_id=binding.row_id,
                binding_identity=verified_binding,
                original_row_sha256=verified_binding.original_row_sha256,
                page_relative_path=page,
                chart_consumer=f"__CHART_GROUPS__.rows[row_id={visible_row_id}].value",
                table_consumer=f"{page}#table-row:{visible_row_id}",
                narrative_consumer=f"evidence-view:{visible_row_id}.user_edit.current_value",
                index_consumer=f"data/search-index.js#{binding.collection}:{visible_row_id}",
                source_binding_consumer=f"evidence-view:{visible_row_id}.source_locator",
            )
        )
    payload["user_edits"] = user_edits
    try:
        projected_data = ReportBPortalData.model_validate(payload)
    except ValueError as error:
        raise ReportBPortalError(f"B active fact投影不符合领域合同：{error}") from error
    return projected_data, tuple(consumers)


def validate_active_fact_revision_b(
    data: ReportBPortalData,
    active_revision: ActiveFactRevision,
) -> None:
    """Validate every B binding before a render transaction can begin."""
    for fact, binding in active_revision.bindings_for("B"):
        if binding.collection not in {"safety", "efficacy"}:
            raise ReportBPortalError("B renderer只接受safety/efficacy领域绑定")
        try:
            validate_active_fact_binding(
                fact,
                binding,
                active_fact_binding_for_b(data, binding.collection, binding.row_id),
            )
        except ValueError as error:
            raise ReportBPortalError(str(error)) from error


def _b_source_view_row(
    data: ReportBPortalData,
    collection: str,
    row_id: str,
) -> dict[str, Any]:
    domain_rows = getattr(data, collection, ())
    domain_matches = [row for row in domain_rows if row.row_id == row_id]
    if len(domain_matches) != 1:
        raise ReportBPortalError("B active fact目标必须有唯一领域行")
    domain_row = domain_matches[0]
    view_row_id = (
        domain_row.source_view_row_id
        if collection == "efficacy" and domain_row.source_view_row_id
        else row_id
    )
    view = getattr(data, f"{collection}_views", None)
    facts = view.get("facts") if isinstance(view, Mapping) else None
    matches = [
        candidate
        for candidate in facts or ()
        if isinstance(candidate, dict) and str(candidate.get("row_id")) == view_row_id
    ]
    if len(matches) != 1:
        raise ReportBPortalError("B active fact目标必须有唯一来源view行")
    candidate = dict(matches[0])
    if collection == "efficacy" and any(
        candidate.get(field) != expected
        for field, expected in (
            ("product_id", domain_row.product_id),
            ("trial_id", domain_row.trial_id),
            ("original_definition", domain_row.endpoint),
            ("arm_label", domain_row.arm),
            ("analysis_population", domain_row.population),
            ("unit", domain_row.unit),
            ("value", domain_row.value),
            ("denominator", domain_row.denominator),
        )
    ):
        raise ReportBPortalError("B 疗效领域行与显式来源view身份不一致")
    return candidate


def _b_statistical_identity(row: SafetyRow | EfficacyRow) -> tuple[str, str]:
    if isinstance(row, EfficacyRow):
        if (
            row.unit.strip().casefold() in {
                "人", "例", "participants", "number of participants",
            }
            and row.numerator is not None
            and row.value == row.numerator
            and row.value_basis is None
        ):
            return "count", "participants"
        if row.value_basis in {"modeled_estimate", "reported_estimate"}:
            return "estimate", "estimate"
        if row.value_basis == "crude_rate" and (
            row.numerator is None or row.denominator is None or row.unit != "%"
        ):
            raise ReportBPortalError("B 疗效粗率缺少百分比及完整原始计数")
        if (
            row.unit == "%"
            and row.numerator is not None
            and row.denominator is not None
            and row.value is not None
            and abs(row.value - row.numerator / row.denominator * 100) > 0.11
        ):
            raise ReportBPortalError("B 疗效百分比与原始计数不一致，缺少类型化数值依据")
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


def active_fact_binding_for_b(
    data: ReportBPortalData,
    collection: Literal["safety", "efficacy"],
    row_id: str,
) -> ActiveFactBinding:
    """Resolve a B row together with its immutable evidence-view identity."""
    if collection not in {"safety", "efficacy"}:
        raise ReportBPortalError("B renderer只接受safety/efficacy领域绑定")
    rows = getattr(data, collection)
    matches = [row for row in rows if row.row_id == row_id]
    if len(matches) != 1:
        raise ReportBPortalError(f"B active fact绑定必须命中唯一领域行：{collection}/{row_id}")
    row = matches[0]
    if row.trial_id is None:
        raise ReportBPortalError("B active fact目标原行缺少试验身份")
    view_row = _b_source_view_row(data, collection, row_id)
    source_version = str(view_row.get("source_version_id") or "").strip()
    locator = view_row.get("source_locator")
    if not source_version or not isinstance(locator, Mapping):
        raise ReportBPortalError("B active fact目标原行缺少来源版本或来源指针")
    products = {item.id: item for item in data.products}
    trials = {item.id: item for item in data.trials}
    digest = canonical_sha256(
        {"domain_row": row.model_dump(mode="json"), "evidence_view_row": view_row}
    )
    statistical_form, measure_object = _b_statistical_identity(row)
    return ActiveFactBinding(
        report="B",
        collection=collection,
        row_id=row.row_id,
        product_id=row.product_id,
        drug_name=products[row.product_id].name,
        trial_id=row.trial_id,
        registry_id=trials[row.trial_id].display_id,
        group_id=str(view_row.get("arm_id")) if view_row.get("arm_id") else None,
        arm=row.arm,
        cohort_id=(
            str(view_row.get("analysis_population_zh"))
            if view_row.get("analysis_population_zh")
            else None
        ),
        period=row.time_window if isinstance(row, SafetyRow) else row.timepoint,
        endpoint_definition=row.endpoint if isinstance(row, EfficacyRow) else None,
        event_definition=row.term if isinstance(row, SafetyRow) else None,
        statistical_form=statistical_form,
        measure_object=measure_object,
        unit=row.unit,
        normalized_unit=row.unit,
        source_version_id=source_version,
        source_pointer=canonical_source_pointer(locator),
        original_row_sha256=digest,
    )


def render_report_b_site(
    data: ReportBPortalData,
    site_root: Path,
    *,
    publication_limitation_zh: str | None = None,
    active_revision: ActiveFactRevision | None = None,
) -> tuple[Path, ...]:
    """Render all B catalog pages plus every product and trial dossier."""
    site_root = Path(site_root)
    consumers: tuple[PortalConsumerNode, ...] = ()
    if active_revision is not None:
        data, consumers = _project_active_facts_b(data, active_revision)

    registry = PageRegistry.load()
    catalog = registry.catalog(ReportKind.B)
    names = {product.id: product.name for product in data.products}
    trial_names = {
        trial.id: _display_trial_name(trial, names.get(trial.product_id, "未列示产品"))
        for trial in data.trials
    }
    efficacy = _efficacy_records(data, names, trial_names)
    safety = _safety_records(data, names, trial_names)
    baseline = _page_records(
        data,
        page_id="baseline-overview",
        names=names,
        trial_names=trial_names,
        efficacy=efficacy,
        safety=safety,
    )
    disposition = _disposition_pool_records(data, names=names, trial_names=trial_names)
    supporting = _page_records(
        data,
        page_id="subgroups-supporting-evidence",
        names=names,
        trial_names=trial_names,
        efficacy=efficacy,
        safety=safety,
    )
    matrix = _matrix_records(data, names, trial_names)
    detail_pool = _dedupe_records(
        (
            *_tag_records(efficacy, "efficacy"),
            *_tag_records(safety, "safety"),
            *_tag_records(baseline, "baseline"),
            *_tag_records(matrix, "matrix"),
            *_tag_records(disposition, "disposition"),
            *_tag_records(supporting, "supporting"),
        )
    )
    # Adjudicate against the full observation universe once. Every physical page
    # (including dossiers) consumes a projection of these same group identities.
    scientific_groups = _adjudicate_full_pool(
        detail_pool, semantic_proposals=data.semantic_proposals,
        semantic_adjudications=data.semantic_adjudications,
    )
    # Longitudinal description is a separate full-view projection purpose, not a
    # fresh cross-trial comparability decision made from a filtered page.
    trial_series: dict[tuple[str, ...], list[tuple[dict[str, Any], Any]]] = defaultdict(list)
    for row, source in efficacy:
        trial_series[(_text(row.get("product_id")), _text(row.get("trial_id")),
                      _text(row.get("group_id")), _text(row.get("arm_role")))].append((row, source))
    longitudinal_groups = tuple(
        {**group, "scientific_group_kind": "within_trial_longitudinal"}
        for key in sorted(trial_series)
        for group in _groups_for_page("longitudinal-results", trial_series[key],
                                       semantic_proposals=data.semantic_proposals)
    )
    _reset_site_root(site_root)
    _copy_assets(site_root)
    (site_root / "data").mkdir(parents=True, exist_ok=True)

    # The standalone report literal intentionally contains only source rows and
    # metadata.  The optional B view objects are implementation inputs, not a
    # second mutable browser data store.
    report_payload = data.model_dump(
        mode="json",
        exclude={
            "report_snapshot_id",
            "efficacy_views",
            "safety_views",
            "baseline_views",
            "disposition_views",
            "supporting_evidence_views",
            "supporting_views",
            "subgroup_views",
            "subgroups_views",
            "matrix_view",
            "matrix_views",
            "views",
            "view_states",
            "semantic_proposals",
        },
    )
    (site_root / "data" / "report.js").write_text(
        "window.REPORT_B=" + _json(report_payload) + ";\n", encoding="utf-8"
    )

    env = Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    page_template = env.get_template("page.html.j2")
    dossier_template = env.get_template("dossier.html.j2")
    generated: list[Path] = []

    for page in catalog.pages:
        context = _render_page_context(
            data,
            page=page,
            catalog=catalog,
            names=names,
            trial_names=trial_names,
            efficacy=efficacy,
            safety=safety,
            scientific_groups=scientific_groups,
            longitudinal_groups=longitudinal_groups,
            publication_limitation_zh=publication_limitation_zh,
            semantic_adjudications=data.semantic_adjudications,
        )
        context["current_revision"] = active_revision.revision if active_revision else 0
        output = site_root / f"{page.id}.html"
        output.write_text(page_template.render(**context), encoding="utf-8")
        generated.append(output)

    products_dir = site_root / "products"
    trials_dir = site_root / "trials"
    products_dir.mkdir(exist_ok=True)
    trials_dir.mkdir(exist_ok=True)
    profile_page = next(page for page in catalog.pages if page.id == "product-trial-profiles")

    for product in data.products:
        records = tuple(item for item in detail_pool if item[0].get("product_id") == product.id)
        context = _render_page_context(
            data,
            page=profile_page,
            catalog=catalog,
            names=names,
            trial_names=trial_names,
            efficacy=efficacy,
            safety=safety,
            scientific_groups=scientific_groups,
            prefix="../",
            current=profile_page.id,
            semantic_adjudications=data.semantic_adjudications,
            detail_records=records
            or tuple(
                item
                for item in _synthetic_status_records(
                    data,
                    page_id=f"product-{product.id}",
                    names=names,
                    trial_names=trial_names,
                    include_products=True,
                )
                if item[0].get("product_id") == product.id
            ),
            detail_kind="product",
            detail_id=product.id,
            publication_limitation_zh=publication_limitation_zh,
        )
        context["detail_product_obj"] = product
        context["detail_product_trials"] = tuple(
            {
                "id": trial.id,
                "name": trial_names.get(trial.id, trial.name),
                "display_id": trial.display_id,
                "phase": trial.phase,
                "region": trial.region,
                "status": trial.status,
                "sample_size": trial.sample_size,
            }
            for trial in data.trials
            if trial.product_id == product.id
        )
        context["detail_product_regulatory"] = tuple(
            item for item in data.regulatory if item.product_id == product.id
        )
        context["detail_product_companies"] = tuple(
            item for item in data.companies if item.product_id == product.id
        )
        context["detail_product_patents"] = tuple(
            item for item in data.patents if item.product_id == product.id
        )
        context["detail_product_history"] = tuple(
            item for item in data.history if item.product_id == product.id
        )
        output = products_dir / f"{product.id}.html"
        context["current_revision"] = active_revision.revision if active_revision else 0
        output.write_text(dossier_template.render(**context), encoding="utf-8")
        generated.append(output)

    for trial in data.trials:
        records = tuple(item for item in detail_pool if item[0].get("trial_id") == trial.id)
        context = _render_page_context(
            data,
            page=profile_page,
            catalog=catalog,
            names=names,
            trial_names=trial_names,
            efficacy=efficacy,
            safety=safety,
            scientific_groups=scientific_groups,
            prefix="../",
            current=profile_page.id,
            semantic_adjudications=data.semantic_adjudications,
            detail_records=records
            or tuple(
                item
                for item in _synthetic_status_records(
                    data,
                    page_id=f"trial-{trial.id}",
                    names=names,
                    trial_names=trial_names,
                )
                if item[0].get("trial_id") == trial.id
            ),
            detail_kind="trial",
            detail_id=trial.id,
            publication_limitation_zh=publication_limitation_zh,
        )
        context["detail_trial_product_obj"] = next(
            product for product in data.products if product.id == trial.product_id
        )
        context["detail_trial_obj"] = trial
        output = trials_dir / f"{trial.id}.html"
        context["current_revision"] = active_revision.revision if active_revision else 0
        output.write_text(dossier_template.render(**context), encoding="utf-8")
        generated.append(output)

    expected_routes = registry.sitemap(
        ReportKind.B,
        product_ids=data.product_ids,
        trial_ids=data.trial_ids,
    )
    routes = [
        {"route": route, "path": route_to_site_path(route).as_posix()} for route in expected_routes
    ]
    sitemap_payload = {
        "report": "B",
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
            candidates = (
                candidate
                if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes))
                else (candidate,)
            )
            for item in candidates:
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
        add_search_entry(
            f"{product.name}产品档案",
            f"products/{product.id}",
            "产品档案",
            product.name,
            product.target,
            product.modality,
            product.phase,
            product.status,
            product.regions,
            product.developer,
            product.mechanism,
        )
    for trial in data.trials:
        product_name = names.get(trial.product_id, "未列示产品")
        display_name = trial_names.get(trial.id, trial.name)
        add_search_entry(
            f"{display_name} · 试验档案",
            f"trials/{trial.id}",
            "试验档案",
            "试验登记",
            "登记结果",
            "注册研究",
            product_name,
            display_name,
            trial.name,
            trial.display_id,
            trial.phase,
            trial.region,
            trial.status,
            trial.role,
        )
    for row, _source in efficacy:
        row_id = _text(row.get("row_id"))
        product_name = _text(row.get("product_zh"), "未列示产品")
        trial_name = _text(row.get("trial_zh"), "未列示试验")
        label = _text(row.get("display_label_zh"), "疗效指标")
        add_search_entry(
            f"{label} · {product_name} · {trial_name}",
            "efficacy",
            "疗效",
            label,
            row.get("element"),
            product_name,
            trial_name,
            row.get("target"),
            row.get("time"),
            row.get("arm"),
            row.get("population"),
            row.get("unit"),
            row.get("value"),
            row.get("numerator"),
            row.get("denominator"),
            row.get("original_definition"),
            row.get("source_version_id"),
            row_id,
            row_id=row_id,
        )
    for row, _source in safety:
        row_id = _text(row.get("row_id"))
        product_name = _text(row.get("product_zh"), "未列示产品")
        trial_name = _text(row.get("trial_zh"), "未列示试验")
        event = _text(row.get("display_label_zh"), "安全性事件")
        add_search_entry(
            f"{event} · {product_name} · {trial_name}",
            "safety",
            "安全性",
            event,
            row.get("category"),
            product_name,
            trial_name,
            row.get("arm"),
            row.get("time_window"),
            row.get("population"),
            row.get("unit"),
            row.get("value"),
            row.get("numerator"),
            row.get("denominator"),
            row.get("original_definition"),
            row.get("source_version_id"),
            row_id,
            row_id=row_id,
        )
    search_json = _json(search)
    (site_root / "data" / "search-index.js").write_text(
        "window.__SEARCH_INDEX__=" + search_json + ";\n",
        encoding="utf-8",
    )
    if active_revision is not None:
        write_render_receipt(
            site_root,
            report="B",
            active_revision=active_revision,
            consumers=consumers,
        )
    return tuple(generated)


def _report_b_claim_ids(data: ReportBPortalData) -> tuple[str, ...]:
    """为门户中实际呈现的结果与事实生成稳定声明标识。"""
    result_rows = cast(
        tuple[EfficacyRow | SafetyRow, ...],
        (*data.efficacy, *data.safety),
    )
    row_ids = [row.row_id for row in result_rows]
    for view_name in (
        "efficacy_views",
        "safety_views",
        "baseline_views",
        "disposition_views",
        "supporting_evidence_views",
    ):
        source = _view_source(data, view_name)
        for index, row in enumerate(_collection(source, "facts", "rows")):
            row_ids.append(_stable_row_id(row, f"{view_name}-{index + 1}"))
    return tuple(dict.fromkeys(stable_id("claim", row_id) for row_id in row_ids))


def build_report_b_artifact(
    *,
    project_root: Path,
    data_path: Path,
    project_id: str,
    contract_version: int,
    run_id: str,
    publication_limitation_zh: str | None = None,
    extra_adjudications: Sequence[ApprovedSemanticMerge] = (),
) -> tuple[Path, Path, str]:
    """生成 B 类站点、锁定报告快照并写入当前运行产物清单。

    站点先写入未发布事务的 staging 目录；只有清单原子写入成功后，最终
    ``html/`` 目录才出现。中断只留下可证明未发布的残留，重跑自动恢复；
    任何已有清单或完成绑定一律拒绝覆盖。
    """
    data = load_report_b_data(data_path)
    if extra_adjudications:
        if data.semantic_adjudications:
            raise ReportBPortalError(
                "载荷已自带语义裁决，拒绝再注入项目级裁决（双来源）"
            )
        payload = data.model_dump(mode="json")
        payload["semantic_adjudications"] = [
            merge.model_dump(mode="json") for merge in extra_adjudications
        ]
        data = ReportBPortalData.model_validate(payload)
    # 会商 round-4 #4：影子行清洗挂在构建入口（load 之外的直接校验路径）
    data = _scrub_declared_shadow_rows(data)
    started_at = datetime.now(UTC)
    transaction = UnpublishedRenderTransaction(
        project_root,
        report="B",
        report_version=data.report_version,
        run_id=run_id,
    )
    try:
        staging_root = transaction.begin()
    except RenderTransactionError as error:
        raise ReportBPortalError(str(error)) from error
    render_report_b_site(
        data,
        staging_root,
        publication_limitation_zh=publication_limitation_zh,
    )

    data_digest = hashlib.sha256(_canonical_json(data.model_dump(mode="json"))).hexdigest()
    coverage_projection_id = stable_id("coverage-projection", project_id, "B", data.report_version)
    declared_snapshot: ReportSnapshotManifest | None = None
    locked: LockedSnapshot | None = None
    if data.report_snapshot_id is not None:
        snapshot_path = (
            project_root
            / "snapshots"
            / "reports"
            / "B"
            / f"{data.report_snapshot_id}.json"
        )
        if snapshot_path.is_file():
            try:
                declared_snapshot = ReportSnapshotManifest.model_validate_json(
                    snapshot_path.read_bytes()
                )
                locked = compute_locked_snapshot(
                    kind="report",
                    report="B",
                    manifest=declared_snapshot.model_dump(mode="json"),
                )
            except (OSError, ValueError, SnapshotIntegrityError) as error:
                raise ReportBPortalError(
                    "B 类门户引用的报告快照存在但不可信"
                ) from error
            if (
                locked.snapshot_id != data.report_snapshot_id
                or declared_snapshot.project_id != project_id
                or declared_snapshot.contract_version != contract_version
                or declared_snapshot.report_version != data.report_version
                or declared_snapshot.data_cutoff != data.data_cutoff
            ):
                raise ReportBPortalError("B 类门户与已锁定报告快照身份不一致")
        # 声明的快照不在项目内：调用方声明不被信任，预览路径按数据字节
        # 确定性自锁定快照，运行保持 rendered_unreviewed，不进入任何接受。
    if declared_snapshot is None or locked is None:
        claim_ids = _report_b_claim_ids(data)
        if not claim_ids:
            raise ReportBPortalError("B 类报告没有可锁定的结果或基线事实")
        evidence_snapshot_id = stable_id("evidence-snapshot", project_id, data_digest)
        claim_snapshot_id = stable_id("claim-snapshot", project_id, data_digest)
        coverage_set_id = stable_id("coverage-set", project_id, "B", data_digest)
        declared_snapshot = ReportSnapshotManifest(
            schema_version="1.0",
            project_id=project_id,
            contract_version=contract_version,
            report="B",
            report_version=data.report_version,
            data_cutoff=data.data_cutoff,
            evidence_snapshot_id=evidence_snapshot_id,
            claim_snapshot_id=claim_snapshot_id,
            coverage_set_id=coverage_set_id,
            claim_ids=claim_ids,
            created_at=started_at,
        )
        locked = SnapshotStore(project_root).lock_report_snapshot(
            report="B", manifest=declared_snapshot.model_dump(mode="json")
        )
    snapshot = declared_snapshot
    assert snapshot is not None and locked is not None
    claim_ids = snapshot.claim_ids
    evidence_snapshot_id = snapshot.evidence_snapshot_id
    claim_snapshot_id = snapshot.claim_snapshot_id
    coverage_set_id = snapshot.coverage_set_id
    site_digest, site_bytes = site_directory_digest(staging_root)
    modified_at = datetime.fromtimestamp(
        max(path.stat().st_mtime for path in staging_root.rglob("*") if path.is_file()),
        tz=UTC,
    )
    package_digest = hashlib.sha256(
        (Path(__file__).resolve().parents[4] / "package-manifest.json").read_bytes()
    ).hexdigest()
    catalog = PageRegistry.load().catalog(ReportKind.B)
    manifest = ArtifactManifest(
        schema_version="1.0",
        manifest_id=stable_id("artifact-manifest", project_id, run_id, "B", data.report_version),
        project_id=project_id,
        contract_version=contract_version,
        report="B",
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
        chart_ids=(
            "efficacy-comparison",
            "safety-heatmap",
            "efficacy-safety-matrix",
            "baseline-comparison",
            "trial-disposition",
        ),
        table_ids=(
            "efficacy",
            "safety",
            "baseline",
            "trial-disposition",
            "products",
            "trials",
        ),
        evidence_reference_ids=tuple(
            dict.fromkeys(stable_id("source", row.source) for row in data.sources)
        ),
        design_contract=DesignContractBinding(
            roles=("report-portal",),
            digest=package_digest,
            applicable_sections=("项目设计合同", "站点式门户"),
        ),
        renderer=RendererBinding(name="report-b-portal", version="1.0"),
        filter_state={},
        generated_at=started_at,
        deterministic_checks=(
            DeterministicCheck(
                check_id="baseline-required-fields-complete",
                status="passed",
                receipt=data_digest,
            ),
            DeterministicCheck(
                check_id="catalog-routes-rendered",
                status="passed",
                receipt=site_digest,
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
            relative_path=f"reports/B/{data.report_version}/html",
            sha256=site_digest,
            byte_size=site_bytes,
            modified_at=modified_at,
            media_type="directory",
        ),
        status="quality_check",
        supersedes_manifest_id=None,
    )
    try:
        site_root, manifest_path = transaction.commit(
            _canonical_json(manifest.model_dump(mode="json"))
        )
    except RenderTransactionError as error:
        raise ReportBPortalError(str(error)) from error
    return site_root, manifest_path, locked.snapshot_id


__all__ = [
    "ReportBPortalData",
    "ReportBPortalError",
    "build_report_b_artifact",
    "load_report_b_data",
    "render_report_b_site",
    "report_b_baseline_gate_failures",
]
