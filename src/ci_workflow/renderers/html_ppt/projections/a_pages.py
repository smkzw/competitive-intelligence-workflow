# ruff: noqa: E501
"""A-class slide bodies assembled from locked snapshot facts."""

from __future__ import annotations

from typing import Any

from ci_workflow.renderers.html_ppt.charts import (
    bubble_chart,
    count_matrix_chart,
    grouped_bar_chart,
    heatmap_chart,
)
from ci_workflow.renderers.html_ppt.components import Slide
from ci_workflow.renderers.html_ppt.projections.a import REQUIRED_IDS, _esc, _stat
from ci_workflow.renderers.html_ppt.projections.common import notes as _notes


def finish_a_slides(**ctx: Any) -> list[Slide]:
    data = ctx["data"]
    products = ctx["products"]
    listed = ctx["listed"]
    targets = ctx["targets"]
    phases = ctx["phases"]
    easi_series = ctx["easi_series"]
    easi_packs = ctx["easi_packs"]
    iga_packs = ctx["iga_packs"]
    landscape_cells = ctx["landscape_cells"]
    target_rows = ctx["target_rows"]
    phase_cols = ctx["phase_cols"]
    modalities = ctx["modalities"]
    modality_cells = ctx["modality_cells"]
    trial_phase = ctx["trial_phase"]
    role_core = ctx["role_core"]
    heat_products = ctx["heat_products"]
    heat_values = ctx["heat_values"]
    heat_cols = ctx["heat_cols"]
    teae_by_pid = ctx["teae_by_pid"]
    indication = ctx["indication"]
    date_zh = ctx["date_zh"]
    return _build(
        data, products, listed, targets, phases, easi_series, easi_packs, iga_packs,
        landscape_cells, target_rows, phase_cols, modalities, modality_cells,
        trial_phase, role_core, heat_products, heat_values, heat_cols, teae_by_pid,
        indication, date_zh,
    )


def _build(
    data: Any,
    products: Any,
    listed: Any,
    targets: Any,
    phases: Any,
    easi_series: Any,
    easi_packs: Any,
    iga_packs: Any,
    landscape_cells: Any,
    target_rows: Any,
    phase_cols: Any,
    modalities: Any,
    modality_cells: Any,
    trial_phase: Any,
    role_core: Any,
    heat_products: Any,
    heat_values: Any,
    heat_cols: Any,
    teae_by_pid: Any,
    indication: Any,
    date_zh: Any,
) -> list[Slide]:
    matrix_points = []
    unpaired = 0
    easi_treat = {item["product_id"]: item for item in easi_series if item.get("treatment") is not None}
    for pid, item in easi_treat.items():
        y_val = teae_by_pid.get(pid)
        if y_val is None:
            unpaired += 1
            continue
        matrix_point = {
            "label_zh": item["label_zh"],
            "x": float(item["treatment"]),
            "y": y_val,
            "size": item.get("size") or 1,
        }
        if str(item["label_zh"]).startswith("611"):
            matrix_point["label_position"] = "below"
        matrix_points.append(matrix_point)
    if not matrix_points:
        raise ValueError("疗效-安全性矩阵无配对点，禁止池化")
    cn_ok = sum(1 for row in data.get("regulatory") or [] if row.get("track") == "中国" and row.get("status") == "已获批")
    overseas_ok = sum(1 for row in data.get("regulatory") or [] if row.get("track") == "境外" and "已获批" in str(row.get("status") or ""))
    cn_unknown = sum(1 for row in data.get("regulatory") or [] if row.get("track") == "中国" and "未核实" in str(row.get("status") or ""))
    edge = [item for item in products.values() if any(token in f"{item.get('status')}{item.get('phase')}" for token in ("终止", "停止", "历史", "撤回", "清算"))]
    title = f"{indication}竞品全景"
    top = next(iter(targets))
    slides = []
    slides.append(Slide(slide_id="a-cover", kind="cover", title=title, responsibility="overview", date_zh=date_zh, cover_highlight=indication, notes_html=_notes("a-cover", "各位同事，今天只讲特应性皮炎已经锁定的竞品全景，不讲系统流程，也不讲证据门槛。" + f"资料截止到<strong>{date_zh}</strong>，范围内有三十八个产品和四十九项试验。" + "请先记住两条阅读纪律：跨试验数字不能直接相加；没有同期对照的产品会明确标出，而不是填零。后面按格局、疗效与安全性、监管权益、局限四条线往下走，每一页都对着当前快照里的结果说话。")))
    slides.append(Slide(slide_id="a-toc", kind="toc", title=title, responsibility="overview", date_zh=date_zh, toc_items=[("竞品与开发", "格局、产品与试验组合", "a-landscape"), ("医学比较", "疗效、安全性与矩阵", "a-efficacy"), ("监管与权益", "中国境外、企业与专利", "a-regulatory"), ("观察与依据", "历史边缘与资料局限", "a-history")], notes_html=_notes("a-toc", "目录只有四个一级章节，请按这个顺序讲，不要跳着把表格念完。第一块看谁在场、处在什么阶段；第二块看主要疗效和安全性怎么并列；第三块看中国和境外监管以及企业和专利能说到哪一步；第四块把终止、边缘和资料缺口单独放下，避免听众把未核实内容当成结论。目录卡只负责导航。<strong>汇报章节</strong>这四个字保持母版原样，日期已经换成当前快照。")))
    phase_counts = {("产品数", key): phases.get(key, 0) for key in phase_cols}
    summary_body = '<div class="two-layer"><div class="main"><div class="stat-strip">' + _stat(len(products), "纳入产品") + _stat(len(data.get("trials") or []), "纳入试验") + _stat(len(listed), "已上市品种") + _stat(len(targets), "作用靶点") + '</div><div class="chart-stage" style="height:360px;margin-top:16px">' + count_matrix_chart(["产品数"], phase_cols, phase_counts, title="阶段结构", height=280) + "</div></div></div>"
    slides.append(Slide(slide_id="a-summary", kind="content", title="首页摘要", responsibility="overview", date_zh=date_zh, body_html=summary_body, conclusion_html=f"已上市十二个品种，其中包括<strong>{_esc(listed[0]['name'])}</strong>；后续疗效页用 EASI-75 族而不是只取字面终点。", notes_html=_notes("a-summary", "开场先把体量说清楚：三十八个产品、四十九项试验、十二个已上市品种。" + f"已上市名字请点到<strong>{listed[0]['name']}</strong>、乌帕替尼、来布利珠单抗，不要把其余品种说成不重要。阶段条只说明结构，不代表疗效排序。如果有人问为什么看不到系统来源原文，明确告诉他今天只讲报告结果，原始登记文本不进观众页。")))
    slides.append(Slide(slide_id="a-landscape", kind="content", title="竞争格局", responsibility="landscape", date_zh=date_zh, body_html='<div class="chart-stage">' + count_matrix_chart(list(target_rows[:8]), phase_cols, landscape_cells, title="靶点与阶段", height=360) + "</div>", conclusion_html="格子里是产品计数，不是疗效高低；终止和历史项目仍计在对应阶段桶中。", notes_html=_notes("a-landscape", "这一页回答谁在场。横轴是开发阶段，纵轴是出现最多的靶点。" + f"最多的是<strong>{top}</strong>。请强调计数不是排名，更不是疗效。有人盯着空白格时，说明这个靶点在该阶段没有纳入产品，不是数据丢失。边缘和终止项目没有从格局里删掉，后面历史页会点名。")))
    slides.append(Slide(slide_id="a-products", kind="content", title="产品总览", responsibility="product-overview", date_zh=date_zh, body_html='<div class="chart-stage">' + count_matrix_chart(modalities, phase_cols, modality_cells, title="模态与阶段", height=360) + "</div>", conclusion_html="单克隆抗体仍是主体；局部小分子和口服小分子并行，不在本页展开全表。", notes_html=_notes("a-products", "产品总览改成模态乘阶段的计数矩阵，避免把三十八行名单塞进幻灯片。请指出单克隆抗体最多，同时局部小分子已经有上市品种。身份字段都在锁定快照里：靶点、模态、阶段、状态、给药途径。如果被问到某一个代码药，告诉听众完整身份在报告表里，" + f"今天只保证<strong>{len(products)} 个产品</strong>都进了计数，没有按知名度删减。")))
    clinical_series = [{"label_zh": name, "treatment": trial_phase.get(name, 0), "control": None, "note_zh": ""} for name in phase_cols if trial_phase.get(name, 0)]
    n_trials = len(data.get("trials") or [])
    slides.append(Slide(slide_id="a-clinical", kind="content", title="临床开发组合", responsibility="clinical-portfolio", date_zh=date_zh, body_html='<div class="stat-strip" style="margin-bottom:16px">' + _stat(n_trials, "试验总数") + _stat(role_core, "核心角色试验") + _stat(trial_phase.get("III期", 0), "III期试验") + _stat(trial_phase.get("已上市", 0), "已上市相关") + '</div><div class="chart-stage" style="height:280px">' + grouped_bar_chart(clinical_series, title="试验阶段分布", height=280, y_name="试验项数", show_legend=False, value_decimals=0) + "</div>", conclusion_html="柱高是试验项数；核心角色优先用于后面疗效锚定，不删除非核心试验。", notes_html=_notes("a-clinical", f"四十九项试验里，核心角色有<strong>{role_core} 项</strong>，后面疗效页会优先用它们锚定。这一页不要念试验英文全称。阶段柱只说明组合结构，地域在快照里多为登记所列地区，不要讲成已经完成全球申报。产品和试验的关系是一对多，有的品种有多项登记，有的还停在早期。")))
    def efficacy_slide(slide_id: str, pack: Any, heading: str, family: str) -> Slide:
        targets_on_page = "、".join(dict.fromkeys(item["target"] for item in pack))
        return Slide(slide_id=slide_id, kind="content", title=heading, responsibility="efficacy", date_zh=date_zh, body_html='<div class="chart-stage">' + grouped_bar_chart(list(pack), title=heading, height=360, y_name="应答率（%）") + "</div>", conclusion_html=f"{family}；本页靶点 {_esc(targets_on_page)}。橙柱为治疗组，蓝柱为对照；无蓝柱即无同期对照，不是零。", notes_html=_notes(slide_id, f"本页是{family}，按靶点分组，没有按效应值做前几名。请先点橙色治疗组，再看蓝色对照。没有蓝柱的产品请读出<strong>无同期对照</strong>，千万不要补零。时间点优先第十六周，再退到含第十六周的登记窗。跨试验高度不能比绝对值，只能比各自试验内部的治疗组与对照。"))
    for index, pack in enumerate(easi_packs):
        slide_id = "a-efficacy" if index == 0 else f"a-efficacy-{index + 1}"
        heading = "疗效" if index == 0 else f"疗效（续{index}）"
        slides.append(efficacy_slide(slide_id, pack, heading, "EASI-75 族"))
    for index, pack in enumerate(iga_packs):
        slide_id = f"a-efficacy-{len(easi_packs) + index + 1}"
        heading = "疗效（IGA 应答）" if index == 0 else f"疗效（IGA 续{index}）"
        slides.append(efficacy_slide(slide_id, pack, heading, "IGA 零或一且改善至少两分"))
    heat_row_labels = [str(item["name"]) for item in heat_products]
    slides.append(Slide(slide_id="a-safety", kind="content", title="安全性", responsibility="safety", date_zh=date_zh, body_html='<div class="chart-stage">' + heatmap_chart(heat_row_labels, heat_cols, heat_values, title="已上市品种安全性", width=1168, height=360) + "</div>", conclusion_html="颜色深浅是已公开发生率；米色格子是未公开，禁止读成零事件。", notes_html=_notes("a-safety", "安全性先看已上市十二个品种的三列：治疗期间、严重、特别关注。特别关注这一列在当前快照里几乎都没有治疗组数值，请直接说<strong>未公开</strong>，不要用常见不良事件去填。严重不良事件有数值的可以点相对高低，但观察窗并不完全相同，不能做合并发生率。热图不是完整表。")))
    unpaired_names = [easi_treat[pid]["label_zh"] for pid in easi_treat if pid not in teae_by_pid]
    matrix_packs = [matrix_points[offset : offset + 10] for offset in range(0, len(matrix_points), 10)]
    for index, pack in enumerate(matrix_packs):
        slide_id = "a-matrix" if index == 0 else f"a-matrix-{index + 1}"
        heading = "疗效与安全性矩阵" if index == 0 else f"疗效与安全性矩阵（续{index}）"
        notes_id = "a-matrix" if index == 0 else "a-matrix-2"
        scope = f"第 {index + 1} 组，共 {len(matrix_packs)} 组；本页 {len(pack)} 个配对产品"
        if index == len(matrix_packs) - 1:
            missing = "、".join(unpaired_names[:6]) or "无"
            conclusion = f"{scope}。未配对 {unpaired} 个，不画点：{missing}。"
        else:
            conclusion = f"{scope}。下一页继续展示其余配对产品；不按效应值排序。"
        slides.append(
            Slide(
                slide_id=slide_id,
                kind="content",
                title=heading,
                responsibility="matrix",
                date_zh=date_zh,
                body_html='<div class="chart-stage" style="height:430px">'
                + bubble_chart(
                    pack,
                    title=heading,
                    x_name="EASI-75 治疗组（%）",
                    y_name="治疗期间不良事件（%）",
                    width=1168,
                    height=430,
                )
                + "</div>",
                conclusion_html=conclusion,
                notes_html=_notes(notes_id, ""),
            )
        )
    slides.append(Slide(slide_id="a-regulatory", kind="content", title="中国与全球监管", responsibility="regulatory", date_zh=date_zh, body_html='<div class="stat-strip" style="margin-bottom:16px">' + _stat(cn_ok, "中国已获批") + _stat(cn_unknown, "中国未核实") + _stat(overseas_ok, "境外已获批口径") + _stat(len(data.get("regulatory") or []), "监管记录") + '</div><div class="grid g2"><div class="kz-card"><h3>中国状态</h3><p>三十八条中国记录中，明确已获批的品种为度普利尤单抗、阿布昔替尼和司普奇拜单抗；其余多数品种的特应性皮炎适应证状态尚未核实。</p></div><div class="kz-card"><h3>境外状态</h3><p>境外获批品种更多，但不能由境外状态推定中国已经可及。所有状态均截至当前资料日期。</p></div></div>', conclusion_html="中国与境外状态分别呈现；尚未核实不等于未获批。", notes_html=_notes("a-regulatory", "中国状态请先报三个已获批品种：度普利尤单抗、阿布昔替尼、司普奇拜单抗，" + f"其余 {cn_unknown} 条尚未核实。境外获批不能自动等同于中国可及。")))
    company_cards = []
    for item in list(data.get("companies") or [])[:3]:
        product = products.get(str(item.get("product_id")), {})
        company_cards.append('<div class="kz-card">' + f"<h3>{_esc(product.get('name'))}</h3>" + f"<p>开发主体 {_esc(item.get('licensor'))}</p>" + f"<p>权益关系 {_esc(item.get('relationship'))}</p><p>未公开条款不推测。</p></div>")
    n_companies = len(data.get("companies") or [])
    slides.append(Slide(slide_id="a-companies", kind="content", title="企业与交易", responsibility="companies-transactions", date_zh=date_zh, body_html='<div class="stat-strip" style="margin-bottom:16px">' + _stat(n_companies, "企业记录") + _stat("不推测", "未公开条款") + '</div><div class="grid g3">' + "".join(company_cards) + "</div>", conclusion_html="三十八条记录都是当前开发主体与公开权益关系；不编交易金额。", notes_html=_notes("a-companies", "企业页不要讲成并购故事。三十八条记录的关系字段都是当前开发主体与公开权益关系。许可方可以读产品后面的开发主体，被许可和地域很多是以公开资料为准。遇到金额、分成、是否独家，统一答<strong>未公开条款不推测</strong>。这不是回避，是快照边界。")))
    patent_parts = []
    for row in list(data.get("patents") or [])[:8]:
        name = products.get(str(row.get("product_id")), {}).get("name")
        patent_parts.append(
            '<div class="disclosure-row">'
            + f"<span>{_esc(name)}</span>"
            + f"<span>{_esc(row.get('scope'))}</span>"
            + f"<span class='state'>{_esc(row.get('display_family'))}</span></div>"
        )
    patent_html = "".join(patent_parts)
    slides.append(Slide(slide_id="a-patents", kind="content", title="专利与保护", responsibility="patents-protection", date_zh=date_zh, body_html='<div class="disclosure-list disclosure-list--dense">' + patent_html + "</div>", conclusion_html="专利页全部是待核实与不得推测；缺检索不能写成没有专利。", notes_html=_notes("a-patents", "这一页最容易讲错。快照明确写了未完成逐法域专利检索，范围不得由药名推测，到期日未核实。请重复一句：<strong>待核实不是没有保护</strong>。不要用同类药的常识去补核心专利年。如果领导问独占期，让他看各监管机构公开信息，今天的演示不提供推断结论。")))
    edge_names = "、".join(str(item.get("name")) for item in edge[:8])
    first_edge = str(edge[0]["name"]) if edge else "相关品种"
    slides.append(Slide(slide_id="a-history", kind="content", title="历史与边缘观察", responsibility="historical-edge", date_zh=date_zh, body_html='<div class="grid g2"><div class="kz-card"><h3>仍保留在范围内</h3>' + f"<p>因停止、终止、无效性或历史观察被点名的品种包括 {_esc(edge_names)} 等，共计 {len(edge)} 个，不因失败删除。</p></div>" + '<div class="kz-card"><h3>状态分层</h3><p>已上市、登记进行中、已停止招募、因疗效或策略停止，是不同层。历史页只说明边缘观察，不改写前面疗效柱的产品集合。</p></div></div>', conclusion_html="终止与边缘项目仍在三十八个产品里；本页点名，避免听众以为只剩成功品种。", notes_html=_notes("a-history", f"请点名至少两个停止开发的品种，例如 {first_edge}。当前快照里这类边缘观察大约 <strong>{len(edge)} 个</strong>。强调保留它们是为了避免成功者偏差，不是为了暗示还会回来。不要把历史观察写成安全性结论，那是另一页的事。")))
    source_cards = ['<div class="kz-card">' + f"<h3>{_esc(row.get('source'))}</h3>" + f"<p>范围 {_esc(row.get('scope'))}</p>" + f"<p>局限 {_esc(row.get('limitation'))}</p></div>" for row in data.get("sources") or []]
    slides.append(Slide(slide_id="a-limitations", kind="content", title="研究依据与局限", responsibility="evidence-limitations", date_zh=date_zh, body_html='<div class="grid g3">' + "".join(source_cards[:3]) + "</div>", conclusion_html="来源局限来自报告资料本身；中国项目需与国内登记并集，部分中国适应证状态尚未核实。", notes_html=_notes("a-limitations", "收口时把局限讲完，不要道歉式地否定前面所有数字。登记是主要来源，中国项目要和国内登记并集；论文不能用事后分析替换主要报告；监管来源里部分中国适应证仍未核实；企业公告不能替代完整安全性。请用<strong>资料边界</strong>这个词，不要说成系统故障。")))
    slides.append(Slide(slide_id="a-ending", kind="ending", title="谢谢", responsibility="overview", date_zh=date_zh, notes_html=_notes("a-ending", "结束页只留谢谢。如果还有时间，回到疗效页或监管页回答一个具体产品，不要在这一页追加新结论。提醒听众今天所有数字都来自特应性皮炎当前锁定快照，" + f"截止<strong>{date_zh}</strong>。跨试验比较需要看试验设计，设计比较报告才展开。讲完停住，把屏幕留在谢谢。")))
    ids = [slide.slide_id for slide in slides]
    for required in REQUIRED_IDS:
        if required not in ids:
            raise ValueError(f"缺少必选页 {required}")
    return slides
