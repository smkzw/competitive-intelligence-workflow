# ruff: noqa: E501
"""Remaining C-class slides after population/inclusion/exclusion."""

from __future__ import annotations

from typing import Any

from ci_workflow.renderers.html_ppt.components import Slide
from ci_workflow.renderers.html_ppt.projections.c import (
    REQUIRED_IDS,
    _assert_no_english_dump,
    _field_rows,
    _obs,
    _product_zh,
    _scale_line,
)
from ci_workflow.renderers.html_ppt.projections.common import disclosure_rows, esc, notes


def _esc_scale(row: dict[str, Any]) -> str:
    return esc(_scale_line(row))


def finish_c_slides(**ctx: Any) -> list[Slide]:
    slides: list[Slide] = ctx["slides"]
    data = ctx["data"]
    date_zh = ctx["date_zh"]
    products = ctx["products"]
    trials = ctx["trials"]
    grouping = ctx["grouping"]

    arm_html = []
    for trial in trials.values():
        product = products[str(trial["product_id"])]
        group = next(row for row in grouping if row["trial_id"] == trial["id"])
        experimental = next(row for row in _obs(data, "experimental_arm") if row["trial_id"] == trial["id"])
        control = next(row for row in _obs(data, "control_arm") if row["trial_id"] == trial["id"])
        dosing = next(row for row in _obs(data, "dosing_regimen") if row["trial_id"] == trial["id"])
        arm_html.append(
            '<div class="kz-card">'
            + f"<h3>{esc(trial['name'])}</h3>"
            + f"<p>{esc(_product_zh(product))} · {esc(_scale_line(group))}</p>"
            + f"<p>试验组干预已公开；对照为对照臂登记项。给药：{esc(_scale_line(dosing))}</p>"
            + f"<p>试验组字段 {esc(experimental['source_field_name'])}，对照字段 {esc(control['source_field_name'])}。</p></div>"
        )
    slides.append(
        Slide(
            slide_id="c-arms",
            kind="content",
            title="分组、干预与对照",
            responsibility="treatment-arms",
            date_zh=date_zh,
            body_html='<div class="grid g2">' + "".join(arm_html) + "</div>",
            conclusion_html="分组用中文盲法差标；试验组与对照只报已公开字段名和给药差标，不粘贴英文给药原文。",
            notes_html=notes(
                "c-arms",
                "分组页把随机化和盲法放在前：CHRONOS 三盲，其余四盲，都是平行分组。"
                "试验组和对照不要念英文药名剂量串。给药差标已经够用：CHRONOS 每两周到第五十一周，"
                "ADvocate2 维持到第五十二周，ADvantage 主要治疗期到第十六周。强调<strong>对照都是对照臂</strong>，不是无对照。",
            ),
        )
    )
    endpoint_cards = []
    for trial in trials.values():
        product = products[str(trial["product_id"])]
        definition = next(row for row in _obs(data, "primary_endpoint_definition") if row["trial_id"] == trial["id"])
        timepoint = next(row for row in _obs(data, "primary_endpoint_timepoint") if row["trial_id"] == trial["id"])
        endpoint_cards.append(
            '<div class="kz-card endpoint-card">'
            + f"<h3>{esc(_product_zh(product))} · {esc(trial['name'])}</h3>"
            + f'<p class="muted">{esc(trial["display_id"])}</p>'
            + f"<p>{esc(_scale_line(definition))}；{esc(_scale_line(timepoint))}</p>"
            + "</div>"
        )
    slides.append(
        Slide(
            slide_id="c-endpoints",
            kind="content",
            title="终点、定义与时间点",
            responsibility="endpoint-timepoint-matrix",
            date_zh=date_zh,
            body_html='<div class="grid g2 endpoint-grid">'
            + "".join(endpoint_cards)
            + "</div>",
            conclusion_html="前三项采用研究者整体评估成功且至少改善 2 分；ADvantage 采用 EASI-75。主要评估时间点均为第 16 周。",
            notes_html=notes(
                "c-endpoints",
                "终点页必须三元身份一起读：药物、试验、量表加时间点。"
                "CHRONOS、ADvocate2和奈莫利珠单抗研究都是研究者整体评估零或一且至少改善两分，时间点第十六周。"
                "ADvantage 换成湿疹面积和严重度指数至少百分之七十五改善，时间点仍是第十六周。请说<strong>时间点对齐、量表不完全对齐</strong>。",
            ),
        )
    )
    slides.append(
        Slide(
            slide_id="c-visits",
            kind="content",
            title="访视、疗程与随访",
            responsibility="visit-duration-followup",
            date_zh=date_zh,
            body_html=disclosure_rows(_field_rows(data, "visit_schedule", products, trials)),
            conclusion_html="第十六周是共同主评估窗；CHRONOS 另有长期安全性随访，两项来布利珠单抗试验写明维持到第五十二周。",
            notes_html=notes(
                "c-visits",
                "访视页看疗程而不是疗效。四项都能读到第十六周。"
                "CHRONOS 还有长期安全性随访；ADvocate2和ADvantage写了诱导期第十六周、维持期第五十二周；"
                "奈莫利珠单抗研究本页只钉到第十六周。请不要把维持期讲成已经完成的结果。<strong>这是设计安排</strong>。",
            ),
        )
    )
    sample_rows = _field_rows(data, "planned_or_actual_sample_size", products, trials)
    analysis_rows = _field_rows(data, "analysis_population", products, trials)
    slides.append(
        Slide(
            slide_id="c-stats",
            kind="content",
            title="样本量与分析集",
            responsibility="sample-analysis-statistics",
            date_zh=date_zh,
            body_html='<div class="grid g2"><div class="kz-card"><h3>样本量</h3>'
            + disclosure_rows(sample_rows)
            + '</div><div class="kz-card"><h3>分析集</h3>'
            + disclosure_rows(analysis_rows)
            + "</div></div>",
            conclusion_html="样本量四项均已公开；分析集四项均为登记记录未单独公开分析集。",
            notes_html=notes(
                "c-stats",
                "统计页左边是样本量：七百四十、四百四十五、九百四十一、三百三十一例。"
                "右边分析集四项都要读成<strong>登记记录未单独公开分析集</strong>，不要推断意向性治疗或安全性集。"
                "奈莫利珠单抗终点行里出现过意向性治疗字样，但不等于本页分析集已公开。",
            ),
        )
    )
    dossier_cards = []
    identity_rows = []
    for trial in trials.values():
        product = products[str(trial["product_id"])]
        definition = next(row for row in _obs(data, "primary_endpoint_definition") if row["trial_id"] == trial["id"])
        timepoint = next(row for row in _obs(data, "primary_endpoint_timepoint") if row["trial_id"] == trial["id"])
        inclusion = next(row for row in _obs(data, "inclusion_criterion") if row["trial_id"] == trial["id"])
        dossier_cards.append(
            '<div class="kz-card">'
            + f"<h3>{esc(_product_zh(product))}</h3>"
            + f"<p>{esc(trial['name'])} · {esc(trial['display_id'])}</p>"
            + f"<p>终点 {_esc_scale(definition)}</p>"
            + f"<p>时间点 {_esc_scale(timepoint)}</p></div>"
        )
        identity_rows.append(
            (
                f"{_product_zh(product)} · {trial['name']} · {trial['display_id']}",
                f"入组 {_scale_line(inclusion)}；终点 {_scale_line(definition)}；{_scale_line(timepoint)}",
                "已公开",
            )
        )
    slides.append(
        Slide(
            slide_id="c-dossiers",
            kind="content",
            title="试验档案",
            responsibility="trial-profile",
            date_zh=date_zh,
            body_html='<div class="grid g2">' + "".join(dossier_cards) + "</div>",
            conclusion_html="四张档案卡都能同时读到中文药名、登记号、评分和时间点。",
            notes_html=notes(
                "c-dossiers",
                "档案卡是给听众定位用的。请逐张点：度普利尤单抗 CHRONOS 登记号 NCT02260986；"
                "来布利珠单抗两项分别是ADvocate2和ADvantage；奈莫利珠单抗一项登记号 NCT03985943。"
                "每张卡都有评分和时间点。下一页把入组阈值再并排一次。<strong>不要比谁更优</strong>。",
            ),
        )
    )
    slides.append(
        Slide(
            slide_id="c-identity",
            kind="content",
            title="试验定位核对",
            responsibility="trial-profile",
            date_zh=date_zh,
            body_html=disclosure_rows(identity_rows),
            conclusion_html="药物、试验、入组阈值和主要终点并列呈现，便于快速定位设计差异。",
            notes_html=notes(
                "c-identity",
                "定位核对是检查页。请让听众在同一行看到药物、试验、入组阈值和终点时间点。"
                "CHRONOS 入组没有十六分阈值，终点仍是研究者整体评估第十六周；后三项入组对齐十六分。"
                "ADvantage 终点量表不同。读完这一页再进路径，避免把试验讲串。<strong>身份先于评价</strong>。",
            ),
        )
    )
    slides.append(
        Slide(
            slide_id="c-patterns",
            kind="content",
            title="设计模式与权衡",
            responsibility="design-patterns",
            date_zh=date_zh,
            body_html=disclosure_rows(
                [
                    ("盲法", "CHRONOS 三盲，其余四盲", "已公开"),
                    ("入组阈值", "后三项 EASI ≥ 16 分，CHRONOS 未单列该量表阈值", "已公开"),
                    ("主终点量表", "三项采用研究者整体评估成功，ADvantage 采用 EASI-75", "已公开"),
                    ("对照构造", "均为对照臂平行分组，不是单臂", "已公开"),
                ]
            ),
            conclusion_html="各试验在盲法、入组阈值和主要终点上各有取向，不作单一优选。",
            notes_html=notes(
                "c-patterns",
                "模式页只归纳差异，不排名。盲法、入组阈值、主终点量表、对照构造四条都能在前面的观察里找到来源。"
                "请避免说谁更严格或谁更像注册标准。下一页开始给两条可执行路径，每条都要落到具体试验。"
                "记住口令：<strong>没有单一优选</strong>。",
            ),
        )
    )
    slides.append(
        Slide(
            slide_id="c-path-1",
            kind="content",
            title="可选路径一",
            responsibility="design-patterns",
            date_zh=date_zh,
            body_html='<div class="kz-card" style="margin-bottom:14px"><h3>度普利尤单抗 · CHRONOS</h3><p>NCT02260986</p></div>'
            + '<div class="grid g3">'
            + '<div class="kz-card"><span class="kz-label">设计框架</span><h3>三盲、平行分组</h3><p>对照臂设计；外用背景治疗同期使用至第 16 周。</p></div>'
            + '<div class="kz-card"><span class="kz-label">治疗安排</span><h3>由主评估延伸至长期治疗</h3><p>第 16 周完成主要评估，治疗期延伸至第 51 周。</p></div>'
            + '<div class="kz-card"><span class="kz-label">人群与终点</span><h3>成人慢性特应性皮炎</h3><p>病程至少 3 年；第 16 周研究者整体评估成功且较基线改善至少 2 分。</p></div>'
            + "</div>",
            conclusion_html="CHRONOS 展示了三盲、平行对照与外用背景治疗并行的设计路径。",
            notes_html=notes(
                "c-path-1",
                "路径一只讲CHRONOS。请把药物、登记号、三盲、成人病程三年、第十六周研究者整体评估一次说完。"
                "外用背景治疗来自访视安排，不要扩展成疗效获益。"
                "结束时加一句：这是可选路径，<strong>不是推荐标准</strong>。下一条看后续确证试验怎么对齐入组阈值。",
            ),
        )
    )
    slides.append(
        Slide(
            slide_id="c-path-2",
            kind="content",
            title="可选路径二",
            responsibility="design-patterns",
            date_zh=date_zh,
            body_html='<div class="kz-card" style="margin-bottom:14px"><h3>来布利珠单抗与奈莫利珠单抗确证试验</h3><p>ADvocate2 · ADvantage · NCT03985943</p></div>'
            + '<div class="grid g3">'
            + '<div class="kz-card"><span class="kz-label">共同入组条件</span><h3>EASI ≥ 16 分</h3><p>三项试验采用相同的疾病严重程度入组阈值。</p></div>'
            + '<div class="kz-card"><span class="kz-label">共同设计</span><h3>四盲、平行分组</h3><p>三项均设对照臂，不按单臂试验解读。</p></div>'
            + '<div class="kz-card"><span class="kz-label">终点差异</span><h3>量表构造并不相同</h3><p>ADvantage 采用第 16 周 EASI-75；其余试验采用研究者整体评估成功。</p></div>'
            + "</div>",
            conclusion_html="路径二不少于一项后续确证试验，强调入组阈值对齐与终点构造差异。",
            notes_html=notes(
                "c-path-2",
                "路径二把后三项放在一起：入组都是十六分，盲法都是四盲。"
                "请点出ADvantage终点量表不同，避免听众以为三项完全同构。"
                "对照仍是对照臂。收尾必须说<strong>两条路径并列</strong>，不要比较哪条更值得学。",
            ),
        )
    )
    version_rows = [
        (
            f"{_product_zh(products[str(trial['product_id'])])} · {trial['name']}",
            "当前比较依据登记版本，不外推此后方案修订",
            "登记版本",
        )
        for trial in trials.values()
    ]
    slides.append(
        Slide(
            slide_id="c-limitations",
            kind="content",
            title="资料版本与局限",
            responsibility="evidence-versions-limitations",
            date_zh=date_zh,
            body_html=disclosure_rows(version_rows)
            + '<div class="kz-card" style="margin-top:12px"><h3>本页口径</h3>'
            + "<p>观众页只说登记版本。分析集未单独公开，入选排除中未单列的阈值也不推断。</p>"
            + "<p>没有独立模式对象，路径由观察差标推导，至少两条，且不给出单一优选。</p></div>",
            conclusion_html="资料边界以登记版本为准；未单列分析集保持未公开。",
            notes_html=notes(
                "c-limitations",
                "局限页把口径收死：我们用的是登记版本，不是全文方案书。"
                "分析集四项未单独公开，排除清单也不完整。"
                "有人要单一优选时，请回答<strong>本比较不给单一优选</strong>，只能回到两条路径和具体登记号。",
            ),
        )
    )
    slides.append(
        Slide(
            slide_id="c-ending",
            kind="ending",
            title="谢谢",
            responsibility="overview",
            date_zh=date_zh,
            notes_html=notes(
                "c-ending",
                "结束页只说谢谢。若还有问题，请对方指定试验或字段，再翻回对应页。"
                "不要在结束页补疗效。提醒今天比较的是<strong>中重度特应性皮炎设计</strong>，不是结果排名。",
            ),
        )
    )
    ids = [slide.slide_id for slide in slides]
    if ids != REQUIRED_IDS:
        raise ValueError(f"C 类页序必须与合同一致，实际 {ids}")
    if sum(1 for slide in slides if slide.slide_id.startswith("c-path-")) < 2:
        raise ValueError("C 类路径数必须不少于二")
    for slide in slides:
        _assert_no_english_dump(slide.body_html + slide.conclusion_html, slide.slide_id)
        if "唯一最佳" in (slide.body_html + slide.conclusion_html):
            raise ValueError("C 类观众页不得输出唯一最佳")
    return slides
