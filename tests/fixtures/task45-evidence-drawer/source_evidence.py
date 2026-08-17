"""Task 4.5 数据依据面板合成夹具：证据视图负载。

所有负载在构建夹具站点时经生产校验器 ``validate_evidence_view_payload``
验证（冻结页面目录权威 + 观察类型与抽屉配置一致 + 披露状态与值一致），
展示层只允许渲染本模块字段。

覆盖（全部为合成数据，不含真实医学结论）：
- A 疗效与安全性概览（common-clinical）：确定值、对照组并列、未公开、
  已报告零值、来源未列示/技术暂不可用、冲突、历史版本、无链接定位、
  非法链接定位。
- B 人口学（baseline-observation）：完整扩展字段族。
- B 试验完成情况（trial-disposition）：完整扩展字段族 + 原因原文 + 冲突。
"""

from __future__ import annotations

from typing import Any

from ci_workflow.reports.common.view_state import derive_row_id

SNAPSHOT = "report-snapshot-45"
PAGE_EFFICACY = "efficacy"
PAGE_BASELINE = "baseline-demographics"
PAGE_DISPOSITION = "disposition-overview"

CT_GOV_URL = "https://clinicaltrials.gov/study/NCT20260001"
CONFERENCE_URL = "https://conference.example.org/abstract-2026-045"


def _row(
    *,
    page: str,
    state: str,
    label: str,
    **identity: str,
) -> dict[str, Any]:
    return {
        "row_id": derive_row_id(**identity),
        "display_label_zh": label,
        "page_responsibility_id": page,
        "report_snapshot_id": SNAPSHOT,
        "disclosure_state": state,
        **identity,
    }


def _field(*, value: str | None = None, state: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if value is not None:
        payload["value"] = value
    if state is not None:
        payload["state"] = state
    return payload


def _registry_locator(*, table: str, page: int, url: str | None) -> dict[str, Any]:
    locator: dict[str, Any] = {
        "document_role": "primary_registry",
        "field_path": "Results.outcomeMeasures",
        "table": table,
        "page": page,
    }
    if url is not None:
        locator["url"] = url
    return locator


# ─── A 疗效与安全性概览：通用观察 ────────────────────────────────────────────


def _general_evidence(
    *,
    row_id: str,
    product: str,
    product_id: str,
    group: str,
    group_id: str,
    element: str,
    label: str,
    trial: str = "试验一",
    disclosure: str = "reported_value",
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "report_kind": "A",
        "observation_kind": "general",
        "row": _row(
            page=PAGE_EFFICACY,
            state=disclosure,
            label=label,
            product_id=product_id,
            trial_id="trial-nct20260001",
            group_id=group_id,
            endpoint_id=f"endpoint-{row_id}",
        ),
        "product_zh": product,
        "trial_zh": trial,
        "group_zh": _field(value=group),
        "element_zh": element,
        "scale": _field(value="原始"),
        "timepoint": _field(value="第16周"),
        "value": _field(value="-18.4"),
        "threshold": _field(state="not_applicable"),
        "unit": _field(value="分"),
        "numerator": _field(state="not_applicable"),
        "denominator": _field(value="120"),
        "source_version_id": "ctgov-2026-05-01",
        "source_version_label_zh": "ClinicalTrials.gov 登记结果（2026年5月1日）",
        "locator": _registry_locator(table="主要终点结果表", page=14, url=CT_GOV_URL),
        "explanation": _field(value="直接取自登记结果，未做换算"),
    }
    payload.update(overrides)
    return payload


GENERAL_PAYLOADS: list[dict[str, Any]] = [
    _general_evidence(
        row_id="treat-hba1c",
        product="产品甲",
        product_id="product-alpha",
        group="治疗组",
        group_id="group-treat",
        element="主要终点 EASI评分较基线变化值",
        label="疗效 · 产品甲 · 治疗组 · EASI评分变化值",
        original_text=(
            "At week 16, the mean change from baseline in EASI total score "
            "was -18.4 points in the treatment arm."
        ),
        original_text_status="provided",
        conflicts=[
            {
                "conflicting_source_version_id": "会议摘要（2026年2月）",
                "conflicting_value_zh": "-16.9 分",
                "conflict_note_zh": (
                    "会议摘要的早期数值与登记结果不一致，本报告以登记结果为准并保留差异记录"
                ),
                "locator": {
                    "document_role": "conference_disclosure",
                    "heading": "Late-breaking abstract",
                    "url": CONFERENCE_URL,
                },
            }
        ],
    ),
    _general_evidence(
        row_id="ctrl-hba1c",
        product="产品甲",
        product_id="product-alpha",
        group="对照组",
        group_id="group-ctrl",
        element="主要终点 EASI评分较基线变化值",
        label="疗效 · 产品甲 · 对照组 · EASI评分变化值",
        value=_field(value="-8.6"),
        denominator=_field(value="118"),
    ),
    _general_evidence(
        row_id="undisclosed-hba1c",
        product="产品乙",
        product_id="product-beta",
        group="治疗组",
        group_id="group-treat",
        element="主要终点 EASI评分较基线变化值",
        label="疗效 · 产品乙 · 治疗组 · EASI评分变化值",
        disclosure="not_publicly_disclosed",
        trial="试验二",
        scale=_field(state="source_not_listed"),
        timepoint=_field(value="第24周"),
        value=_field(state="not_yet_disclosed"),
        unit=_field(state="technically_unavailable"),
        denominator=_field(state="not_yet_disclosed"),
        explanation=_field(value="来源尚未公开主要终点数值，保留未公开状态"),
    ),
    _general_evidence(
        row_id="zero-teae",
        product="产品乙",
        product_id="product-beta",
        group="治疗组",
        group_id="group-treat",
        element="治疗期不良事件发生例数",
        label="安全 · 产品乙 · 治疗组 · 治疗期不良事件",
        trial="试验二",
        disclosure="reported_zero",
        value=_field(value="0"),
        unit=_field(value="例"),
        numerator=_field(value="0"),
        denominator=_field(value="96"),
        historical_versions=[
            {
                "source_version_id": "登记早期版本（2026年1月15日）",
                "previous_value": _field(value="1"),
                "supersession_note_zh": ("早期登记版本报告 1 例，2026年4月10日勘误后为 0 例"),
                "locator": {
                    "document_role": "primary_registry",
                    "field_path": "Results.adverseEvents",
                    "page": 21,
                    "url": CT_GOV_URL,
                },
            }
        ],
    ),
    _general_evidence(
        row_id="no-link-locator",
        product="产品丙",
        product_id="product-gamma",
        group="治疗组",
        group_id="group-treat",
        element="次要终点疾病活动度评分较基线变化值",
        label="疗效 · 产品丙 · 治疗组 · 疾病活动度变化值",
        trial="试验三",
        value=_field(value="-12.1"),
        unit=_field(value="分"),
        denominator=_field(value="104"),
        locator={
            "document_role": "primary_trial_report",
            "heading": "Efficacy results",
            "table": "表 2",
            "page": 18,
            "paragraph": "次要终点部分",
        },
        conflicts=[
            {
                "conflicting_source_version_id": "企业演示材料（2026年3月）",
                "conflicting_value_zh": "-10.8 分",
                "conflict_note_zh": "企业演示材料与论文数值不同，以论文为准",
                "locator": {
                    "document_role": "company_disclosure",
                    "paragraph": "第 12 页疾病活动度部分",
                },
            }
        ],
    ),
    _general_evidence(
        row_id="invalid-scheme-url",
        product="产品丙",
        product_id="product-gamma",
        group="对照组",
        group_id="group-ctrl",
        element="次要终点疾病活动度评分较基线变化值",
        label="疗效 · 产品丙 · 对照组 · 疾病活动度变化值",
        trial="试验三",
        value=_field(value="-9.4"),
        unit=_field(value="分"),
        denominator=_field(value="102"),
        locator={
            "document_role": "primary_trial_report",
            "field_path": "Results.secondaryOutcomes",
            "url": "javascript:alert(1)",
        },
    ),
    _general_evidence(
        row_id="ftp-url",
        product="产品乙",
        product_id="product-beta",
        group="对照组",
        group_id="group-ctrl",
        element="主要终点 EASI评分较基线变化值",
        label="疗效 · 产品乙 · 对照组 · EASI评分变化值",
        trial="试验二",
        value=_field(value="-7.9"),
        denominator=_field(value="101"),
        locator={
            "document_role": "primary_registry",
            "field_path": "Results.outcomeMeasures",
            "url": "ftp://example.org/nct20260001-results.pdf",
        },
    ),
    _general_evidence(
        row_id="status-complete",
        product="产品甲",
        product_id="product-alpha",
        group="全试验",
        group_id="group-all",
        element="试验完成状态",
        label="进展 · 产品甲 · 试验一 · 试验完成状态",
        trial="试验一",
        scale=_field(state="not_applicable"),
        timepoint=_field(value="数据截止日"),
        value=_field(value="已完成"),
        unit=_field(state="not_applicable"),
        denominator=_field(state="not_applicable"),
        explanation=_field(value="直接取自试验登记状态，未做推断"),
    ),
    _general_evidence(
        row_id="status-ongoing",
        product="产品乙",
        product_id="product-beta",
        group="全试验",
        group_id="group-all",
        element="试验完成状态",
        label="进展 · 产品乙 · 试验二 · 试验完成状态",
        trial="试验二",
        scale=_field(state="not_applicable"),
        timepoint=_field(value="数据截止日"),
        value=_field(value="进行中"),
        unit=_field(state="not_applicable"),
        denominator=_field(state="not_applicable"),
        explanation=_field(value="直接取自试验登记状态，未做推断"),
    ),
]

# ─── B 人口学：基线观察（完整扩展字段族） ───────────────────────────────────


def _baseline_extension() -> dict[str, Any]:
    return {
        "canonical_variable_family": _field(value="人口学特征"),
        "source_field_name": _field(value="Age"),
        "source_field_definition": _field(value="入选时年龄（岁）"),
        "statistical_form_or_measurement_object": _field(value="均值（标准差）"),
        "scale_version_direction": _field(state="not_applicable"),
        "denominator_role": _field(value="随机化人群"),
        "time_window_or_baseline_definition": _field(value="基线＝首次给药前最近一次评估"),
        "reason_original_text": "Age at enrollment",
        "canonical_reason": _field(value="按登记原字段直接规范为年龄变量"),
        "mutual_exclusion_exhaustiveness": _field(state="not_applicable"),
        "compatibility_rule": _field(value="同定义可直接合并比较"),
        "difference_label": _field(state="not_applicable"),
    }


def _baseline_easi_extension() -> dict[str, Any]:
    return {
        "canonical_variable_family": _field(value="疾病严重程度"),
        "source_field_name": _field(value="EASI total score"),
        "source_field_definition": _field(value="基线湿疹面积与严重程度指数总分"),
        "statistical_form_or_measurement_object": _field(value="均值（标准差）"),
        "scale_version_direction": _field(
            value="EASI；0–72分；分数越高表示病情越重"
        ),
        "denominator_role": _field(value="随机化人群"),
        "time_window_or_baseline_definition": _field(
            value="基线＝首次给药前最近一次评估"
        ),
        "reason_original_text": "EASI total score at baseline",
        "canonical_reason": _field(value="按来源原字段规范为基线疾病严重程度"),
        "mutual_exclusion_exhaustiveness": _field(state="not_applicable"),
        "compatibility_rule": _field(value="同量表、同版本、同基线定义时可直接比较"),
        "difference_label": _field(state="not_applicable"),
    }


BASELINE_PAYLOADS: list[dict[str, Any]] = [
    {
        "report_kind": "B",
        "observation_kind": "baseline_observation",
        "row": _row(
            page=PAGE_BASELINE,
            state="reported_value",
            label="基线 · 产品甲 · 治疗组 · 年龄",
            product_id="product-baseline-alpha",
            trial_id="trial-baseline-01",
            group_id="group-baseline-treat",
            timepoint_id="baseline-day-1",
        ),
        "product_zh": "产品甲",
        "trial_zh": "基线试验一",
        "group_zh": _field(value="治疗组"),
        "element_zh": "基线变量：年龄",
        "scale": _field(state="not_applicable"),
        "timepoint": _field(value="基线"),
        "value": _field(value="42.3"),
        "threshold": _field(state="not_applicable"),
        "unit": _field(value="岁"),
        "numerator": _field(state="not_applicable"),
        "denominator": _field(value="120"),
        "source_version_id": "ctgov-baseline-2026-05-01",
        "source_version_label_zh": "ClinicalTrials.gov 登记结果（2026年5月1日）",
        "locator": {
            "document_role": "primary_registry",
            "field_path": "Results.baselineCharacteristics",
            "table": "基线特征表",
            "page": 16,
            "url": CT_GOV_URL,
        },
        "explanation": _field(value="直接取自登记基线特征表，未做换算"),
        "original_text_status": "provided",
        "original_text": "Mean age 42.3 years (SD 11.2) in the treatment arm.",
        **_baseline_extension(),
    },
    {
        "report_kind": "B",
        "observation_kind": "baseline_observation",
        "row": _row(
            page=PAGE_BASELINE,
            state="reported_value",
            label="基线 · 产品乙 · 治疗组 · 湿疹面积与严重程度指数",
            product_id="product-baseline-beta",
            trial_id="trial-baseline-02",
            group_id="group-baseline-treat",
            timepoint_id="baseline-day-1",
        ),
        "product_zh": "产品乙",
        "trial_zh": "基线试验二",
        "group_zh": _field(value="治疗组"),
        "element_zh": "基线变量：湿疹面积与严重程度指数",
        "scale": _field(value="EASI"),
        "timepoint": _field(value="基线"),
        "value": _field(value="24.6"),
        "threshold": _field(state="not_applicable"),
        "unit": _field(value="分"),
        "numerator": _field(state="not_applicable"),
        "denominator": _field(value="96"),
        "source_version_id": "publication-baseline-2026-04",
        "source_version_label_zh": "期刊论文（2026年4月）",
        "locator": {
            "document_role": "publication",
            "heading": "Baseline characteristics",
            "table": "表 1",
            "page": 5,
        },
        "explanation": _field(value="直接取自论文基线特征表，未做换算"),
        **_baseline_easi_extension(),
    },
]

# ─── B 试验完成情况：处置观察（完整扩展字段族 + 原因原文） ───────────────────


def _disposition_extension() -> dict[str, Any]:
    return {
        "canonical_variable_family": _field(value="停止治疗原因"),
        "source_field_name": _field(value="Reason for treatment discontinuation"),
        "source_field_definition": _field(value="受试者停止治疗的主要原因分类"),
        "statistical_form_or_measurement_object": _field(value="计数（百分比）"),
        "scale_version_direction": _field(state="not_applicable"),
        "denominator_role": _field(value="随机化人群"),
        "time_window_or_baseline_definition": _field(value="治疗期（第1天至第12周）"),
        "reason_original_text": "Adverse event",
        "canonical_reason": _field(value="按原字段规范为不良事件类别"),
        "mutual_exclusion_exhaustiveness": _field(value="互斥但未穷尽"),
        "compatibility_rule": _field(value="按规范原因族对齐后比较"),
        "difference_label": _field(value="来源未报告全部原因明细"),
    }


DISPOSITION_PAYLOADS: list[dict[str, Any]] = [
    {
        "report_kind": "B",
        "observation_kind": "trial_disposition_observation",
        "row": _row(
            page=PAGE_DISPOSITION,
            state="reported_value",
            label="完成情况 · 产品甲 · 治疗组 · 停止治疗（不良事件）",
            product_id="product-disp-alpha",
            trial_id="trial-disp-01",
            group_id="group-disp-treat",
            event_id="event-stop-ae",
        ),
        "product_zh": "产品甲",
        "trial_zh": "完成情况试验一",
        "group_zh": _field(value="治疗组"),
        "element_zh": "停止治疗原因：不良事件",
        "scale": _field(state="not_applicable"),
        "timepoint": _field(value="第1天至第12周"),
        "value": _field(value="3"),
        "threshold": _field(state="not_applicable"),
        "unit": _field(value="例"),
        "numerator": _field(value="3"),
        "denominator": _field(value="118"),
        "source_version_id": "ctgov-disp-2026-05-01",
        "source_version_label_zh": "ClinicalTrials.gov 登记结果（2026年5月1日）",
        "locator": {
            "document_role": "primary_registry",
            "field_path": "Results.participantFlow",
            "table": "受试者处置表",
            "page": 19,
            "url": CT_GOV_URL,
        },
        "explanation": _field(value="直接取自登记处置表，按原因族规范"),
        "conflicts": [
            {
                "conflicting_source_version_id": "会议摘要（2026年2月）",
                "conflicting_value_zh": "2 例",
                "conflict_note_zh": "会议摘要与登记结果的停止治疗原因口径不同，以登记结果为准",
                "locator": {
                    "document_role": "conference_disclosure",
                    "heading": "Disposition results",
                    "url": CONFERENCE_URL,
                },
            }
        ],
        **_disposition_extension(),
    },
]

ALL_PAYLOADS: list[dict[str, Any]] = [
    *GENERAL_PAYLOADS,
    *BASELINE_PAYLOADS,
    *DISPOSITION_PAYLOADS,
]
