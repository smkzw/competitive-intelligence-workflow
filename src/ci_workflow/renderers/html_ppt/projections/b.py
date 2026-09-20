# ruff: noqa: E501
"""B-class HTML-PPT visual narrative from locked PNH report-data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ci_workflow.renderers.html_ppt.charts import grouped_bar_chart
from ci_workflow.renderers.html_ppt.components import Slide
from ci_workflow.renderers.html_ppt.projections.common import (
    DISCLOSURE_ZH,
    cutoff_zh,
    esc,
    load_report,
    notes,
    set_notes_date,
    stat,
    write_report_deck,
)

REQUIRED_IDS = [
    "b-cover",
    "b-toc",
    "b-summary",
    "b-efficacy",
    "b-longitudinal",
    "b-safety",
    "b-matrix",
    "b-baseline-overview",
    "b-demographics",
    "b-disease-context",
    "b-severity",
    "b-disposition-overview",
    "b-flow",
    "b-adherence",
    "b-loss-exit",
    "b-screen-failure",
    "b-rescue",
    "b-prohibited",
    "b-deviation",
    "b-exposure",
    "b-subgroups",
    "b-profiles",
    "b-limitations",
    "b-ending",
]

FLOW_ZH = {
    "screened": "筛选",
    "randomized": "随机",
    "received_treatment": "接受治疗",
    "completed_treatment": "完成治疗",
    "completed_study": "完成研究",
    "screen_failure": "筛败",
    "treatment_discontinued": "治疗中止",
    "study_withdrawal": "退出研究",
    "lost_to_follow_up": "失访",
    "study_withdrawal_reason": "退出研究原因",
    "treatment_discontinuation_reason": "治疗中止原因",
    "adherence": "依从性",
    "rescue_treatment": "补救治疗",
    "prohibited_medication": "禁用药使用",
    "protocol_deviation": "方案偏离",
    "major_protocol_deviation": "重要方案偏离",
    "protocol_deviation_leading_to_exclusion": "导致分析集排除的方案偏离",
}
GROUP_ZH = {
    "apply-treatment": "APPLY 治疗组",
    "apply-control": "APPLY 对照组",
    "appoint-treatment": "APPOINT 治疗组",
    None: "队列合计",
}


def _group_label(group_id: object) -> str:
    if group_id is None:
        return GROUP_ZH[None]
    label = str(group_id)
    return GROUP_ZH.get(label, label or GROUP_ZH[None])


def _state(raw: object) -> str:
    text = str(raw or "")
    return DISCLOSURE_ZH.get(text, text if text in DISCLOSURE_ZH.values() else "未公开")


def _fact_value(row: dict[str, Any]) -> str:
    if row.get("disclosure_state") not in {"reported_value", "reported_zero"} and row.get("value") is None:
        return "未公开"
    value = row.get("value")
    unit = row.get("unit") or ""
    if value is None:
        return str(row.get("raw_value") or "未公开")
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    spacer = "" if not unit or str(unit) == "%" else " "
    return f"{value}{spacer}{unit}"


def _disp_rows(facts: list[dict[str, Any]], *, fields: set[str] | None = None, families: set[str] | None = None) -> list[dict[str, Any]]:
    out = []
    for row in facts:
        if fields is not None and row.get("field") not in fields:
            continue
        if families is not None and row.get("field_family") not in families:
            continue
        out.append(row)
    return out


def _assert_locked_shape(data: dict[str, Any]) -> None:
    if data.get("indication") != "阵发性睡眠性血红蛋白尿":
        raise ValueError("B 类适应症必须为阵发性睡眠性血红蛋白尿")
    products = data.get("products") or []
    if len(products) != 1 or products[0].get("name") != "伊普可泮":
        raise ValueError("B 类必须投影伊普可泮单产品快照")
    trials = {item["id"]: item for item in data.get("trials") or []}
    if set(trials) != {"nct04558918", "nct04820530"}:
        raise ValueError("B 类试验身份与锁定快照不符")
    timepoints = {str(row.get("timepoint")) for row in data.get("efficacy") or []}
    if timepoints != {"第24周"}:
        raise ValueError("B 类纵向结果只能有第24周，禁止编造其他访视")
    domains = {row.get("variable_domain") for row in (data.get("baseline_views") or {}).get("facts") or []}
    if "disease_context" in domains:
        raise ValueError("当前快照不应出现疾病语境域事实")
    if "baseline_severity" not in domains or "demographics" not in domains:
        raise ValueError("B 类基线必须含人口学与严重程度")


def build_report_b_slides(data: dict[str, Any]) -> list[Slide]:
    _assert_locked_shape(data)
    date_zh = cutoff_zh(data.get("data_cutoff"))
    set_notes_date(date_zh)
    product = (data.get("products") or [])[0]
    trials = {item["id"]: item for item in data.get("trials") or []}
    apply = trials["nct04558918"]
    appoint = trials["nct04820530"]
    efficacy = list(data.get("efficacy") or [])
    apply_t = next(row for row in efficacy if row["trial_id"] == "nct04558918" and row["arm"] == "治疗组")
    apply_c = next(row for row in efficacy if row["trial_id"] == "nct04558918" and row["arm"] == "对照组")
    appoint_t = next(row for row in efficacy if row["trial_id"] == "nct04820530" and row["arm"] == "治疗组")
    if any(row["trial_id"] == "nct04820530" and row["arm"] == "对照组" and row.get("value") is not None for row in efficacy):
        raise ValueError("禁止把 APPOINT 画成有对照的疗效差")
    safety = [row for row in data.get("safety") or [] if row.get("disclosure_state") != "不适用"]
    matrix_rows = (data.get("matrix_view") or {}).get("comparison_rows") or []
    appoint_matrix = next(row for row in matrix_rows if row["trial_id"] == "nct04820530")
    if appoint_matrix.get("status") != "not_applicable" or not appoint_matrix.get("reason_zh"):
        raise ValueError("APPOINT 矩阵必须展示不适用原因")
    apply_matrix = next(row for row in matrix_rows if row["trial_id"] == "nct04558918")
    baseline = (data.get("baseline_views") or {}).get("facts") or []
    disposition = (data.get("disposition_views") or {}).get("facts") or []
    disclosed_n = sum(1 for row in disposition if row.get("disclosure_state") == "reported_value")
    unpublished_n = sum(1 for row in disposition if row.get("disclosure_state") == "not_publicly_disclosed")
    if unpublished_n != 40 or disclosed_n != 14:
        raise ValueError("B 类处置披露计数与锁定快照不符")

    title = "阵发性睡眠性血红蛋白尿临床试验结果比较"
    slides: list[Slide] = []

    slides.append(
        Slide(
            slide_id="b-cover",
            kind="cover",
            title=title,
            responsibility="overview",
            date_zh=date_zh,
            cover_highlight="阵发性睡眠性血红蛋白尿",
            notes_html=notes(
                "b-cover",
                "各位同事，今天只讲阵发性睡眠性血红蛋白尿里伊普可泮的两项关键确证结果，不讲系统流程。"
                f"资料截止到<strong>{date_zh}</strong>。请先记住：APPLY 有同期对照，APPOINT 是单臂，不能把后者画成疗效差。"
                "后面按疗效与安全性、基线、试验完成情况、档案局限四条线走，缺项只报未公开，不补零。",
            ),
        )
    )
    slides.append(
        Slide(
            slide_id="b-toc",
            kind="toc",
            title=title,
            responsibility="overview",
            date_zh=date_zh,
            toc_items=[
                ("结果比较", "疗效、纵向与安全性", "b-efficacy"),
                ("基线人群", "人口学、语境与严重度", "b-baseline-overview"),
                ("试验完成", "流转、依从与偏离", "b-disposition-overview"),
                ("档案与局限", "产品试验与资料边界", "b-profiles"),
            ],
            notes_html=notes(
                "b-toc",
                "目录四个一级章节请按顺序讲。第一块是第24周血红蛋白应答和安全性；第二块是基线，疾病语境本快照没有独立域；"
                "第三块把筛选、随机、完成和未公开的依从偏离分开；第四块回到伊普可泮与两项试验身份。"
                "目录卡只负责导航。<strong>汇报章节</strong>保持母版原样，不要把完成情况模块删掉。",
            ),
        )
    )

    summary_body = (
        '<div class="stat-strip">'
        + stat(product["name"], "纳入产品")
        + stat("2", "关键确证试验")
        + stat(f"{apply['treatment_sample_size']}/{apply['sample_size'] - apply['treatment_sample_size']}", "APPLY 治疗/对照")
        + stat(appoint["treatment_sample_size"], "APPOINT 单臂例数")
        + "</div>"
        + '<div class="grid g2" style="margin-top:16px">'
        + f'<div class="kz-card"><h3>{esc(apply["name"])}</h3><p>{esc(apply["display_id"])}，{esc(apply["role"])}，境外已完成。</p>'
        + f"<p>治疗组 {esc(apply['treatment_sample_size'])} 例，对照 {esc(apply['sample_size'] - apply['treatment_sample_size'])} 例。</p></div>"
        + f'<div class="kz-card"><h3>{esc(appoint["name"])}</h3><p>{esc(appoint["display_id"])}，{esc(appoint["role"])}，单臂已完成。</p>'
        + f"<p>治疗组 {esc(appoint['treatment_sample_size'])} 例，<strong>无同期对照</strong>。</p></div></div>"
    )
    slides.append(
        Slide(
            slide_id="b-summary",
            kind="content",
            title="首页摘要",
            responsibility="overview",
            date_zh=date_zh,
            body_html=summary_body,
            conclusion_html="数字全部来自本快照：伊普可泮，APPLY 六十二对三十五，APPOINT 四十例单臂。",
            notes_html=notes(
                "b-summary",
                "开场先报身份：产品是伊普可泮，试验是 APPLY 和 APPOINT，都是关键确证、境外已完成。"
                f"APPLY 治疗组<strong>{apply['treatment_sample_size']} 例</strong>、对照三十五例；APPOINT 四十例没有对照。"
                "后面疗效页会看到百分之八点三对百分之一点八，以及单臂百分之九点二，不要提前合成一个总应答率。",
            ),
        )
    )

    series = [
        {
            "label_zh": apply["name"],
            "treatment": apply_t["value"],
            "control": apply_c["value"],
            "note_zh": "第24周",
        },
        {
            "label_zh": appoint["name"],
            "treatment": appoint_t["value"],
            "control": None,
            "note_zh": "无同期对照",
        },
    ]
    slides.append(
        Slide(
            slide_id="b-efficacy",
            kind="content",
            title="疗效",
            responsibility="efficacy",
            date_zh=date_zh,
            body_html='<div class="chart-stage">'
            + grouped_bar_chart(
                series,
                title="第24周血红蛋白应答率",
                height=480,
                y_name="第24周应答率（%）",
            )
            + "</div>",
            conclusion_html="终点为血红蛋白较基线持续升高至少两克每分升且无需输血；橙柱治疗组，蓝柱对照。",
            notes_html=notes(
                "b-efficacy",
                f"请先点 APPLY：治疗组<strong>{apply_t['value']}%</strong>，对照 {apply_c['value']}%。"
                f"再点 APPOINT 治疗组 {appoint_t['value']}%，下面标注无同期对照，千万不要补蓝柱。"
                "终点定义是血红蛋白较基线持续升高至少两克每分升且无需输血，分析集是全分析集。跨试验不能把两个橙柱加总。",
            ),
        )
    )
    slides.append(
        Slide(
            slide_id="b-longitudinal",
            kind="content",
            title="纵向结果",
            responsibility="longitudinal-results",
            date_zh=date_zh,
            body_html='<div class="stat-strip" style="margin-bottom:16px">'
            + stat("第24周", "本快照仅有时点")
            + stat(f"{apply_t['value']}%", "APPLY 治疗")
            + stat(f"{apply_c['value']}%", "APPLY 对照")
            + stat(f"{appoint_t['value']}%", "APPOINT 治疗")
            + "</div>"
            + '<div class="kz-card"><h3>没有其他访视曲线</h3>'
            + "<p>疗效行的时间点全部是第24周。本页重复同一时点，是为了说明纵向模块存在，而不是另造第十二周或第五十二周。</p>"
            + "<p>若被问到中间访视，请回答<strong>本快照未提供其他时点</strong>，不要手绘趋势。</p></div>",
            conclusion_html="纵向结果只有第24周；禁止编造其他访视点。",
            notes_html=notes(
                "b-longitudinal",
                "这一页最容易讲错。听众会以为纵向就是一条随时间升高的曲线，但锁定快照里疗效时间点只有第24周。"
                "请把四个数字再报一遍，并明确说<strong>没有其他访视曲线</strong>。APPLY 对照百分之一点八不是缺失，是已公开的对照值。",
            ),
        )
    )


    from ci_workflow.renderers.html_ppt.projections import b_pages

    return b_pages.finish_b_slides(
        slides=slides,
        data=data,
        date_zh=date_zh,
        product=product,
        trials=trials,
        apply=apply,
        appoint=appoint,
        apply_t=apply_t,
        apply_c=apply_c,
        appoint_t=appoint_t,
        safety=safety,
        apply_matrix=apply_matrix,
        appoint_matrix=appoint_matrix,
        baseline=baseline,
        disposition=disposition,
        disclosed_n=disclosed_n,
        unpublished_n=unpublished_n,
    )


def build_report_b_html_ppt(*, output_path: Path | str, root: Path | None = None) -> Path:
    data, digest = load_report("B", root=root)
    slides = build_report_b_slides(data)
    return write_report_deck(
        report="B",
        slides=slides,
        title="阵发性睡眠性血红蛋白尿临床试验结果比较",
        date_zh=cutoff_zh(data.get("data_cutoff")),
        digest=digest,
        output_path=Path(output_path),
        root=root,
    )
