# ruff: noqa: E501
"""Remaining B-class slides after efficacy/longitudinal."""

from __future__ import annotations

from typing import Any

from ci_workflow.renderers.html_ppt.charts import bubble_chart, heatmap_chart
from ci_workflow.renderers.html_ppt.components import Slide
from ci_workflow.renderers.html_ppt.projections.b import (
    FLOW_ZH,
    REQUIRED_IDS,
    _disp_rows,
    _fact_value,
    _group_label,
    _state,
)
from ci_workflow.renderers.html_ppt.projections.common import (
    FAMILY_ZH,
    disclosure_rows,
    esc,
    notes,
    stat,
)


def finish_b_slides(**ctx: Any) -> list[Slide]:
    slides: list[Slide] = ctx["slides"]
    data = ctx["data"]
    date_zh = ctx["date_zh"]
    product = ctx["product"]
    trials = ctx["trials"]
    apply = ctx["apply"]
    appoint = ctx["appoint"]
    safety = ctx["safety"]
    apply_matrix = ctx["apply_matrix"]
    appoint_matrix = ctx["appoint_matrix"]
    baseline = ctx["baseline"]
    disposition = ctx["disposition"]
    disclosed_n = ctx["disclosed_n"]
    unpublished_n = ctx["unpublished_n"]

    heat_rows = ["APPLY 治疗组", "APPLY 对照组", "APPOINT 治疗组"]
    heat_cols = ["治疗期间", "严重", "特别关注", "常见"]
    cat_map = {
        "治疗期间不良事件": "治疗期间",
        "严重不良事件": "严重",
        "特别关注不良事件": "特别关注",
        "常见不良事件": "常见",
    }
    heat_values: dict[tuple[str, str], float | None] = {}
    row_key = {
        ("nct04558918", "治疗组"): "APPLY 治疗组",
        ("nct04558918", "对照组"): "APPLY 对照组",
        ("nct04820530", "治疗组"): "APPOINT 治疗组",
    }
    for row in safety:
        key = row_key.get((row["trial_id"], row["arm"]))
        col = cat_map.get(row["category"])
        if key is None or col is None:
            continue
        heat_values[(key, col)] = None if row.get("value") is None else float(row["value"])
    family_note = "、".join(FAMILY_ZH.values())
    slides.append(
        Slide(
            slide_id="b-safety",
            kind="content",
            title="安全性",
            responsibility="safety",
            date_zh=date_zh,
            body_html='<div class="chart-stage">' + heatmap_chart(heat_rows, heat_cols, heat_values, title="安全性四类", width=1168, height=492) + "</div>",
            conclusion_html=f"四列依次是{family_note}；已公开为零的突破性溶血要读成零事件，不是缺失。",
            notes_html=notes(
                "b-safety",
                "安全性四列请用中文：治疗期间、严重、特别关注、常见。APPLY 治疗组治疗期间百分之五十四点八，严重百分之九点七，"
                "特别关注突破性溶血是<strong>已公开为零</strong>。APPOINT 没有对照列，缺格不要读成零。常见不良事件本快照点名头痛，不要扩成完整清单。",
            ),
        )
    )

    point = apply_matrix["point"]
    slides.append(
        Slide(
            slide_id="b-matrix",
            kind="content",
            title="疗效与安全性矩阵",
            responsibility="efficacy-safety-matrix",
            date_zh=date_zh,
            body_html=(
                '<div class="matrix-layout">'
                '<div class="chart-stage matrix-chart">'
                + bubble_chart(
                    [
                        {
                            "label_zh": "APPLY",
                            "x": point["x_value"],
                            "y": point["y_value"],
                            "size": point["size"],
                        }
                    ],
                    title="APPLY 疗效与安全性矩阵",
                    x_name="治疗组与对照组应答率差（百分点）",
                    y_name="治疗期间不良事件（%）",
                    width=760,
                    height=430,
                )
                + '</div><div class="matrix-callouts">'
                '<div class="kz-card"><h3>APPLY 可比较</h3>'
                f"<p>横轴 {esc(point['x_value'])} 个百分点，纵轴 {esc(point['y_value'])}%，气泡大小对应治疗组 {esc(point['size'])} 例。</p>"
                "<p><strong>不计算综合分</strong>。</p></div>"
                f'<div class="kz-card"><h3>APPOINT 不适用</h3><p>{esc(appoint_matrix["reason_zh"])}</p></div>'
                "</div></div>"
            ),
            conclusion_html="只有 APPLY 进入可比较点；APPOINT 必须展示单臂不适用原因。",
            notes_html=notes(
                "b-matrix",
                "矩阵页先讲 APPLY 可以比，再讲 APPOINT 不能比。"
                f"不适用原因请读<strong>{appoint_matrix['reason_zh']}</strong>。"
                "不要把单臂百分之九点二和治疗期间百分之六十画成疗效差。没有综合分。",
            ),
        )
    )

    demo = [row for row in baseline if row.get("variable_domain") == "demographics"]
    sev = [row for row in baseline if row.get("variable_domain") == "baseline_severity"]
    slides.append(
        Slide(
            slide_id="b-baseline-overview",
            kind="content",
            title="基线与人群总览",
            responsibility="baseline-overview",
            date_zh=date_zh,
            body_html=(
                '<div class="stat-strip">'
                + stat(len(baseline), "基线事实")
                + stat(len(demo), "人口学行")
                + stat(len(sev), "严重程度行")
                + stat("0", "疾病语境行")
                + "</div>"
                + '<div class="kz-card" style="margin-top:16px"><h3>当前能讲的只有两类</h3>'
                + "<p>人口学是样本量、年龄、女性比例；严重程度是基线血红蛋白。疾病语境域在本快照为零行，下一页单独披露，不拿血红蛋白顶替。</p></div>"
            ),
            conclusion_html="基线总览只报告有域的事实；零行语境不得用血红蛋白填空。",
            notes_html=notes(
                "b-baseline-overview",
                f"基线一共 {len(baseline)} 条，人口学 {len(demo)} 条，严重程度 {len(sev)} 条，疾病语境<strong>零条</strong>。"
                "请预告听众：后面人口学和血红蛋白会有数字，语境页会看到未提供独立域，不要把两页讲成一页。",
            ),
        )
    )
    concept_zh = {"baseline_sample_size": "基线样本量", "age": "年龄", "sex": "女性比例"}
    demo_rows = [
        (
            _group_label(row.get("group_id")),
            f"{concept_zh.get(str(row.get('standardized_concept')), str(row.get('source_name')))} {_fact_value(row)}",
            "已公开",
        )
        for row in demo
    ]
    slides.append(
        Slide(
            slide_id="b-demographics",
            kind="content",
            title="人口学",
            responsibility="baseline-demographics",
            date_zh=date_zh,
            body_html=disclosure_rows(demo_rows),
            conclusion_html="APPLY 两组年龄约五十岁、女性近七成；APPOINT 更年轻、女性四成。",
            notes_html=notes(
                "b-demographics",
                "人口学请按组读：APPLY 治疗六十二人、对照三十五人，年龄五十一点七和四十九点八岁，女性约百分之六十九。"
                "APPOINT 四十人、四十二点一岁、女性百分之四十二点五。这些是基线时点按随机化组列示，<strong>不是疗效结果</strong>。",
            ),
        )
    )
    slides.append(
        Slide(
            slide_id="b-disease-context",
            kind="content",
            title="疾病语境",
            responsibility="baseline-disease-context",
            date_zh=date_zh,
            body_html=disclosure_rows(
                [
                    ("疾病语境域", "本快照未提供独立疾病语境事实", "未公开"),
                    ("禁止替代表述", "不得把基线血红蛋白读成病史或溶血语境", "不适用"),
                    ("可讲内容", "仅能说明该模块存在且当前为空", "已公开结构"),
                ]
            ),
            conclusion_html="疾病语境页是披露矩阵；禁止用血红蛋白冒充语境。",
            notes_html=notes(
                "b-disease-context",
                "这一页没有病史年数、输血依赖或溶血活动的数字。请直接说<strong>本快照没有疾病语境域</strong>。"
                "如果有人指着八点九克每分升问是不是语境，明确回答那是下一页的严重程度，不是本页内容。不要编既往治疗。",
            ),
        )
    )
    slides.append(
        Slide(
            slide_id="b-severity",
            kind="content",
            title="基线疾病严重程度",
            responsibility="baseline-severity",
            date_zh=date_zh,
            body_html=disclosure_rows(
                [(_group_label(row.get("group_id")), f"基线血红蛋白 {_fact_value(row)}", "已公开") for row in sev]
            ),
            conclusion_html="APPLY 两组均为八点九克每分升，APPOINT 八点二克每分升；数值越低表示更重。",
            notes_html=notes(
                "b-severity",
                "严重程度只有基线血红蛋白。APPLY 治疗和对照都是<strong>八点九克每分升</strong>，APPOINT 八点二。"
                "请说明越低越重，但不要把它讲成疗效终点，疗效终点是第24周升高至少两克每分升且无需输血。",
            ),
        )
    )
    slides.append(
        Slide(
            slide_id="b-disposition-overview",
            kind="content",
            title="试验完成情况总览",
            responsibility="disposition-overview",
            date_zh=date_zh,
            body_html=(
                '<div class="stat-strip">'
                + stat(len(disposition), "处置事实")
                + stat(disclosed_n, "已公开")
                + stat(unpublished_n, "未公开")
                + stat("6", "完成情况模块页")
                + "</div>"
                + '<div class="kz-card" style="margin-top:16px"><h3>已公开与未公开分区</h3>'
                + "<p>已公开主要是筛选、随机、接受治疗和完成治疗或研究。依从、失访原因、补救、禁用药和方案偏离整组未公开。</p>"
                + "<p>未公开不得记成零例，也不得把筛败派到随机组。</p></div>"
            ),
            conclusion_html="五十四条事实中十四条已公开、四十条未公开；后续分页保留全部模块。",
            notes_html=notes(
                "b-disposition-overview",
                f"完成情况一共五十四条，已公开 {disclosed_n}，未公开 {unpublished_n}。"
                "请预告：流转页会看到筛选一百二十和完成数字，后面依从到偏离都是未公开矩阵。"
                "强调一句：<strong>未公开不是零</strong>。不要把模块合并成一页。",
            ),
        )
    )
    flow = _disp_rows(
        disposition,
        fields={"screened", "randomized", "received_treatment", "completed_treatment", "completed_study", "screen_failure"},
    )
    flow_pairs = [
        (
            f"{trials[row['trial_id']]['name']} {_group_label(row.get('group_id'))}",
            f"{FLOW_ZH.get(str(row.get('field')), str(row.get('field')))} {_fact_value(row)}",
            _state(row.get("disclosure_state")),
        )
        for row in flow
        if row.get("field") != "source_other"
    ]
    slides.append(
        Slide(
            slide_id="b-flow",
            kind="content",
            title="受试者流转",
            responsibility="participant-flow",
            date_zh=date_zh,
            body_html=disclosure_rows(flow_pairs),
            conclusion_html="两项试验筛选均为一百二十人；筛败未公开，不得记零，也不得派到随机组。",
            notes_html=notes(
                "b-flow",
                "流转先报筛选：APPLY 和 APPOINT 都是一百二十人已公开。随机和接受治疗与基线样本量一致。"
                "APPLY 治疗完成六十一、完成研究六十二；APPOINT 完成治疗三十八、完成研究三十七。"
                "筛败请读<strong>未公开</strong>，不要用一百二十减六十二去倒推。",
            ),
        )
    )

    def unpublished(slide_id: str, title_zh: str, responsibility: str, families: set[str] | None, fields: set[str] | None, notes_body: str, conclusion: str) -> Slide:
        rows = _disp_rows(disposition, families=families, fields=fields)
        if not rows:
            raise ValueError(f"{slide_id} 缺少对应处置事实，禁止删模块")
        pairs = [
            (
                f"{trials[row['trial_id']]['name']} {_group_label(row.get('group_id'))}",
                FLOW_ZH.get(str(row.get("field")), str(row.get("source_field_name") or row.get("field"))),
                _state(row.get("disclosure_state")),
            )
            for row in rows
        ]
        return Slide(
            slide_id=slide_id,
            kind="content",
            title=title_zh,
            responsibility=responsibility,
            date_zh=date_zh,
            body_html=disclosure_rows(pairs),
            conclusion_html=conclusion,
            notes_html=notes(slide_id, notes_body),
        )

    slides.append(unpublished("b-adherence", "依从性", "adherence", {"adherence"}, None, "依从性三条都是未公开。请对着矩阵把 APPLY 两组和 APPOINT 治疗组都读成未公开，不要估计服药百分比。定义和阈值字段也是空的。强调<strong>未公开不是高依从</strong>，更不是零不依从。", "依从性三条均未公开；禁止估计服药比例。"))
    slides.append(unpublished("b-loss-exit", "失访与退出", "loss-exit", None, {"lost_to_follow_up", "study_withdrawal", "treatment_discontinued", "study_withdrawal_reason", "treatment_discontinuation_reason"}, "失访、退出研究和治疗中止，以及对应原因，当前都是未公开。完成研究数字已经在流转页出现，不能反向推出退出例数。请读<strong>未公开</strong>，不要用完成例数相减。", "失访、退出与停药均未公开；不得用完成例数反推。"))
    screen_rows = _disp_rows(disposition, fields={"screened", "screen_failure", "screen_failure_reason"})
    slides.append(
        Slide(
            slide_id="b-screen-failure",
            kind="content",
            title="筛败与原因",
            responsibility="screen-failure",
            date_zh=date_zh,
            body_html=disclosure_rows(
                [
                    (
                        f"{trials[row['trial_id']]['name']} {_group_label(row.get('group_id'))}",
                        f"{FLOW_ZH.get(str(row.get('field')), '筛败原因')} {_fact_value(row)}",
                        _state(row.get("disclosure_state")),
                    )
                    for row in screen_rows
                ]
            ),
            conclusion_html="筛选一百二十已公开；筛败人数和原因未公开，不得派到随机组。",
            notes_html=notes(
                "b-screen-failure",
                "筛败页要同时保住已公开的筛选人数和未公开的筛败。两项试验筛选都是一百二十。筛败和原因请读未公开。"
                "关键纪律：<strong>不得把筛败派到随机组</strong>，也不能用筛选减随机当筛败。",
            ),
        )
    )
    slides.append(unpublished("b-rescue", "补救治疗", "rescue-treatment", {"rescue_treatment"}, None, "补救治疗三条全未公开。不要把对照组抗补体治疗讲成补救，那是试验设计里的对照臂。本页只报告披露状态。请说<strong>来源未公开补救治疗</strong>，不要推测输血或加药。", "补救治疗全未公开；对照臂不是补救。"))
    slides.append(unpublished("b-prohibited", "禁用药使用", "prohibited-medication", {"prohibited_medication"}, None, "禁用药使用三条全未公开。不要用常识去补哪些药被禁止。请逐行读出 APPLY 两组和 APPOINT 治疗组都是未公开。强调<strong>未公开不是未使用</strong>。", "禁用药使用全未公开；禁止补清单。"))
    slides.append(unpublished("b-deviation", "方案偏离", "plan-deviation", {"protocol_deviation"}, None, "方案偏离、重大偏离和导致剔除的偏离全部未公开。不要把完成治疗差一例讲成方案偏离。请读披露矩阵，并说明<strong>没有分级数字</strong>。", "方案偏离三类均未公开；完成例数差不能当偏离。"))
    slides.append(
        Slide(
            slide_id="b-exposure",
            kind="content",
            title="试验与暴露语境",
            responsibility="trial-exposure-context",
            date_zh=date_zh,
            body_html=(
                '<div class="grid g2">'
                f'<div class="kz-card"><h3>{esc(apply["name"])}</h3><p>{esc(apply["display_id"])}</p>'
                f"<p>角色 {esc(apply['role'])}，阶段 {esc(apply['phase'])}，地区 {esc(apply['region'])}，状态 {esc(apply['status'])}。</p>"
                f"<p>样本量 {esc(apply['sample_size'])}，治疗组 {esc(apply['treatment_sample_size'])}，对照三十五。</p></div>"
                f'<div class="kz-card"><h3>{esc(appoint["name"])}</h3><p>{esc(appoint["display_id"])}</p>'
                f"<p>角色 {esc(appoint['role'])}，阶段 {esc(appoint['phase'])}，地区 {esc(appoint['region'])}，状态 {esc(appoint['status'])}。</p>"
                f"<p>样本量 {esc(appoint['sample_size'])}，全部为治疗组，<strong>无对照臂</strong>。</p></div></div>"
            ),
            conclusion_html="暴露语境只报告角色、样本量与臂；不编累积剂量。",
            notes_html=notes("b-exposure"),
        )
    )
    slides.append(
        Slide(
            slide_id="b-subgroups",
            kind="content",
            title="亚组与支持证据",
            responsibility="subgroups-supporting-evidence",
            date_zh=date_zh,
            body_html=disclosure_rows(
                [
                    ("独立亚组行", "本快照未提供独立亚组结果", "未公开"),
                    ("禁止动作", "不得按年龄或性别拆分第24周应答率", "不适用"),
                    ("可讲内容", "主分析仍以全分析集第24周为准", "已公开结构"),
                ]
            ),
            conclusion_html="亚组页说明未提供独立亚组结果；禁止捏造估计值。",
            notes_html=notes("b-subgroups"),
        )
    )
    slides.append(
        Slide(
            slide_id="b-profiles",
            kind="content",
            title="产品与试验档案",
            responsibility="product-trial-profiles",
            date_zh=date_zh,
            body_html=(
                '<div class="grid g3">'
                f'<div class="kz-card"><h3>{esc(product["name"])}</h3><p>靶点 {esc(product.get("target"))}</p><p>阶段 {esc(product.get("phase"))}</p></div>'
                f'<div class="kz-card"><h3>{esc(apply["name"])}</h3><p>{esc(apply["display_id"])}</p><p>{esc(apply["role"])}</p></div>'
                f'<div class="kz-card"><h3>{esc(appoint["name"])}</h3><p>{esc(appoint["display_id"])}</p><p>单臂 {esc(appoint["role"])}</p></div></div>'
            ),
            conclusion_html="档案必须能读到伊普可泮、APPLY、APPOINT 及其登记号。",
            notes_html=notes("b-profiles"),
        )
    )
    limit_pairs = [(str(item.get("source")), str(item.get("limitation")), str(item.get("maturity"))) for item in data.get("sources") or []]
    if not limit_pairs:
        raise ValueError("B 类缺少来源局限")
    slides.append(
        Slide(
            slide_id="b-limitations",
            kind="content",
            title="研究依据与局限",
            responsibility="evidence-limitations",
            date_zh=date_zh,
            body_html=disclosure_rows(limit_pairs),
            conclusion_html="分层安全性、处置原因明细和单臂无对照是当前主要边界。",
            notes_html=notes("b-limitations"),
        )
    )
    slides.append(
        Slide(
            slide_id="b-ending",
            kind="ending",
            title="谢谢",
            responsibility="overview",
            date_zh=date_zh,
            notes_html=notes("b-ending"),
        )
    )
    ids = [slide.slide_id for slide in slides]
    if ids != REQUIRED_IDS:
        raise ValueError(f"B 类页序必须与合同一致，实际 {ids}")
    return slides
