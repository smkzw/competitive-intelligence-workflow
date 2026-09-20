# ruff: noqa: E501
"""C-class HTML-PPT visual narrative from locked design-comparison report-data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ci_workflow.renderers.html_ppt.components import Slide
from ci_workflow.renderers.html_ppt.projections.common import (
    cutoff_zh,
    disclosure_rows,
    esc,
    load_report,
    notes,
    set_notes_date,
    stat,
    write_report_deck,
)

REQUIRED_IDS = [
    "c-cover",
    "c-toc",
    "c-summary",
    "c-design-map",
    "c-population",
    "c-inclusion",
    "c-exclusion",
    "c-arms",
    "c-endpoints",
    "c-visits",
    "c-stats",
    "c-dossiers",
    "c-identity",
    "c-patterns",
    "c-path-1",
    "c-path-2",
    "c-limitations",
    "c-ending",
]

PRODUCT_ZH = {
    "dupilumab": "度普利尤单抗",
    "lebrikizumab": "来布利珠单抗",
    "nemolizumab": "奈莫利珠单抗",
}

BANNED_AUDIENCE = (
    "the registry record does not",
    "allocation=randomized",
    "chronic ad that",
    "eczema area and severity",
)


def _product_zh(product: dict[str, Any]) -> str:
    mapped = PRODUCT_ZH.get(str(product.get("id")))
    if mapped:
        return mapped
    name = str(product.get("name") or "")
    if name and any("\u4e00" <= ch <= "\u9fff" for ch in name):
        return name.split("（")[0]
    raise ValueError(f"C 类产品缺少中文身份：{product.get('id')}")


def _obs(data: dict[str, Any], field: str) -> list[dict[str, Any]]:
    rows = [row for row in data.get("observations") or [] if row.get("field") == field]
    if len(rows) != 4:
        raise ValueError(f"C 类字段 {field} 必须覆盖四项试验")
    return rows


def _identity(row: dict[str, Any], products: dict[str, Any], trials: dict[str, Any]) -> str:
    product = products[str(row["product_id"])]
    trial = trials[str(row["trial_id"])]
    return f"{_product_zh(product)} · {trial['name']} · {trial['display_id']}"


def _scale_line(row: dict[str, Any]) -> str:
    if row.get("disclosure_state") == "not_publicly_disclosed":
        return "登记记录未单独公开分析集"
    scale = row.get("scale")
    value = row.get("threshold_value")
    if scale and value not in (None, ""):
        operator = str(row.get("operator") or "").replace(">=", "≥").replace("<=", "≤")
        unit = row.get("threshold_unit") or ""
        if str(scale).upper() == "EASI" and str(value) == "75" and str(unit).startswith("%"):
            return "EASI-75 应答"
        value_with_unit = (
            f"{value}{unit}" if str(unit).startswith("%") else f"{value} {unit}".strip()
        )
        return f"{scale} {operator} {value_with_unit}".replace("  ", " ").strip()
    labels = [str(item) for item in (row.get("difference_labels_zh") or []) if item]
    if labels:
        return "；".join(labels)
    if row.get("randomization") or row.get("blinding"):
        parts = [part for part in (row.get("randomization"), row.get("blinding")) if part]
        return "、".join(str(part) for part in parts)
    timepoint = row.get("assessment_timepoint")
    if timepoint:
        return f"评估时点 {timepoint}"
    if value not in (None, ""):
        unit = row.get("threshold_unit") or ""
        return f"{value} {unit}".strip()
    return "登记已公开该字段，未单列中文差标或量表阈值"


def _assert_no_english_dump(html: str, slide_id: str) -> None:
    lowered = html.lower()
    for token in BANNED_AUDIENCE:
        if token in lowered:
            raise ValueError(f"{slide_id} 观众页出现英文登记原文")


def _field_rows(
    data: dict[str, Any],
    field: str,
    products: dict[str, Any],
    trials: dict[str, Any],
) -> list[tuple[str, str, str]]:
    from ci_workflow.renderers.html_ppt.projections.common import DISCLOSURE_ZH

    pairs = []
    for row in _obs(data, field):
        state = DISCLOSURE_ZH.get(str(row.get("disclosure_state")), "已公开")
        pairs.append((_identity(row, products, trials), _scale_line(row), state))
    return pairs


def build_report_c_slides(data: dict[str, Any]) -> list[Slide]:
    if data.get("indication") != "中重度特应性皮炎":
        raise ValueError("C 类适应症必须为中重度特应性皮炎")
    date_zh = cutoff_zh(data.get("data_cutoff"))
    set_notes_date(date_zh)
    products = {str(item["id"]): item for item in data.get("products") or []}
    trials = {str(item["id"]): item for item in data.get("trials") or []}
    if len(products) != 3 or len(trials) != 4:
        raise ValueError("C 类必须为三药四试验")
    observations = data.get("observations") or []
    if len(observations) != 48:
        raise ValueError("C 类观察必须为四十八行")
    title = "中重度特应性皮炎临床试验设计比较"
    slides: list[Slide] = []

    slides.append(
        Slide(
            slide_id="c-cover",
            kind="cover",
            title=title,
            responsibility="overview",
            date_zh=date_zh,
            cover_highlight="中重度特应性皮炎",
            notes_html=notes(
                "c-cover",
                "各位同事，今天只比较中重度特应性皮炎三项生物制剂的关键确证设计，不汇报疗效数字，也不讲系统流程。"
                f"资料截止到<strong>{date_zh}</strong>。请先记住三药四试验：度普利尤单抗的CHRONOS，来布利珠单抗的两项，奈莫利珠单抗一项。"
                "每一页都要能指到药物、试验、评分和时间点。",
            ),
        )
    )
    slides.append(
        Slide(
            slide_id="c-toc",
            kind="toc",
            title=title,
            responsibility="overview",
            date_zh=date_zh,
            toc_items=[
                ("设计图谱", "三药四试验结构", "c-design-map"),
                ("元素对照", "人群、入排、干预与终点", "c-population"),
                ("试验定位", "档案、量表与时间点", "c-dossiers"),
                ("可选路径", "模式、路径与登记版本", "c-patterns"),
            ],
            notes_html=notes(
                "c-toc",
                "目录按元素对照、试验定位、可选路径走，最后才是局限。不要一上来讲谁更好。"
                "设计图谱只看结构，入排和终点才给量表阈值。"
                "两条路径都是可执行对照，不是排名。<strong>汇报章节</strong>保持母版，日期已换成当前登记版本。",
            ),
        )
    )

    product_names = "、".join(_product_zh(item) for item in products.values())
    summary_cards = []
    for trial in trials.values():
        product = products[str(trial["product_id"])]
        summary_cards.append(
            '<div class="kz-card">'
            + f"<h3>{esc(trial['name'])}</h3>"
            + f"<p>{esc(_product_zh(product))} · {esc(trial['display_id'])}</p>"
            + f"<p>{esc(trial['role'])}，样本量 {esc(trial['sample_size'])} 例。</p></div>"
        )
    slides.append(
        Slide(
            slide_id="c-summary",
            kind="content",
            title="首页摘要",
            responsibility="overview",
            date_zh=date_zh,
            body_html='<div class="stat-strip">'
            + stat("3", "纳入药物")
            + stat("4", "关键确证试验")
            + stat("12", "设计字段")
            + stat("48", "观察行")
            + "</div>"
            + '<div class="grid g2" style="margin-top:16px">'
            + "".join(summary_cards)
            + "</div>",
            conclusion_html=f"{esc(product_names)} 四项试验都是第三期关键确证；本页只钉身份，不报结果。",
            notes_html=notes(
                "c-summary",
                f"开场报三药：<strong>{product_names}</strong>。四项试验是CHRONOS、ADvocate2、奈莫利珠单抗疗效与安全性研究、ADvantage。"
                "十二个设计字段乘四项试验得到四十八行观察。如果有人问有效率，告诉他今天是设计比较，结果报告不在这套稿。",
            ),
        )
    )

    grouping = _obs(data, "arm_randomization_blinding")
    map_rows = []
    for trial in trials.values():
        product = products[str(trial["product_id"])]
        group = next(row for row in grouping if row["trial_id"] == trial["id"])
        map_rows.append(
            (
                f"{_product_zh(product)} · {trial['name']}",
                f"{trial['display_id']} · {_scale_line(group)} · {trial['sample_size']}例",
                trial["role"],
            )
        )
    slides.append(
        Slide(
            slide_id="c-design-map",
            kind="content",
            title="设计图谱",
            responsibility="design-map",
            date_zh=date_zh,
            body_html=disclosure_rows(map_rows),
            conclusion_html="四项都是随机平行分组；CHRONOS 三盲，其余四盲。",
            notes_html=notes(
                "c-design-map",
                "设计图谱先看谁和谁比。四项都是随机平行分组的关键确证。"
                "请点出CHRONOS是<strong>三盲</strong>，其余三项四盲。样本量七百四十、四百四十五、九百四十一、三百三十一，只说明体量，不是疗效。",
            ),
        )
    )
    slides.append(
        Slide(
            slide_id="c-population",
            kind="content",
            title="人群与疾病定义",
            responsibility="population-disease-definition",
            date_zh=date_zh,
            body_html=disclosure_rows(_field_rows(data, "target_population", products, trials)),
            conclusion_html="CHRONOS 强调成人慢性病程三年；其余三项覆盖十二岁及以上青少年与成人。",
            notes_html=notes(
                "c-population",
                "人群页只用中文差标。CHRONOS 是成人入组、慢性病程至少三年；ADvocate2 还加了体重至少四十公斤；"
                "奈莫利珠单抗和ADvantage都是十二岁及以上。"
                "不要念英文登记原文。评估时点多在筛选期，ADvantage写在知情同意时。<strong>差标已经够讲</strong>。",
            ),
        )
    )
    slides.append(
        Slide(
            slide_id="c-inclusion",
            kind="content",
            title="入选标准",
            responsibility="inclusion-criteria",
            date_zh=date_zh,
            body_html=disclosure_rows(_field_rows(data, "inclusion_criterion", products, trials)),
            conclusion_html="后三项入组对齐湿疹面积和严重度指数至少十六分；CHRONOS 未单列该量表阈值。",
            notes_html=notes(
                "c-inclusion",
                "入选优先读量表阈值。ADvocate2、奈莫利珠单抗研究和ADvantage都是湿疹面积和严重度指数至少十六分。"
                "CHRONOS 这一行没有单列量表阈值，请说<strong>登记已公开入选项但未单列阈值</strong>，不要把人群页的三年病程重复当成入组分数。",
            ),
        )
    )
    slides.append(
        Slide(
            slide_id="c-exclusion",
            kind="content",
            title="排除标准",
            responsibility="exclusion-criteria",
            date_zh=date_zh,
            body_html=disclosure_rows(_field_rows(data, "exclusion_criterion", products, trials)),
            conclusion_html="可结构化的排除项包括奈莫利珠单抗体重低于三十公斤；其余多为已公开但未单列阈值。",
            notes_html=notes(
                "c-exclusion",
                "排除页能明确读出的阈值是奈莫利珠单抗体重低于三十公斤。"
                "CHRONOS、ADvocate2和ADvantage登记已公开排除项，但没有可投影的中文差标或量表阈值，请照屏幕说未单列，"
                "不要翻译英文原文里的既往用药名单。<strong>不要编排除清单</strong>。",
            ),
        )
    )


    from ci_workflow.renderers.html_ppt.projections import c_pages

    return c_pages.finish_c_slides(
        slides=slides,
        data=data,
        date_zh=date_zh,
        products=products,
        trials=trials,
        grouping=grouping,
        title=title,
    )


def build_report_c_html_ppt(*, output_path: Path | str, root: Path | None = None) -> Path:
    data, digest = load_report("C", root=root)
    slides = build_report_c_slides(data)
    return write_report_deck(
        report="C",
        slides=slides,
        title="中重度特应性皮炎临床试验设计比较",
        date_zh=cutoff_zh(data.get("data_cutoff")),
        digest=digest,
        output_path=Path(output_path),
        root=root,
    )
