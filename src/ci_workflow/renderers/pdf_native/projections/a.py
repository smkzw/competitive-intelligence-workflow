"""A-class native PDF projection (PDF01–PDF02)."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

# ReportLab 5 has no compatible type-stub release; keep ignores local to this deferred renderer.
from reportlab.lib.units import mm  # type: ignore[import-untyped]
from reportlab.platypus import KeepTogether, Paragraph, Spacer  # type: ignore[import-untyped]

from ci_workflow.renderers.pdf_native.projections._layout import (


    UNPUBLISHED,
    bookmark,
    bubble_matrix_chart,
    continuation_table_blocks,
    cover_block,
    cutoff_zh,
    disclosure_zh,
    display_value,
    efficacy_forest_chart,
    efficacy_grouped_bar_chart,
    executive_summary_page,
    make_doc,
    make_styles,
    product_map,
    safety_heatmap_chart,
    section_break,
    section_heading,
    styled_table,
    toc_page,
    trial_map,
)


def _is_any_teae_row(row) -> bool:
    """会商 #2：概念匹配按 term_key（词表单源），旧数据回退基础类别名。"""
    if row.get("term_key"):
        return row["term_key"] == "any_teae"
    base = str(row.get("category") or "").replace("（登记）", "").strip()
    return base in {"治疗期间不良事件", "治疗中出现的不良事件"}


_FORBIDDEN = ("html", "chromium", "playwright", "browser", "screenshot")

_A_TOC: list[tuple[str, str]] = [
    ("总览", "封面"),
    ("总览", "目录"),
    ("总览", "首页摘要"),
    ("竞品与开发", "竞争格局"),
    ("竞品与开发", "产品总览"),
    ("竞品与开发", "临床开发组合"),
    ("监管与权益", "中国与全球监管"),
    ("监管与权益", "企业与交易"),
    ("监管与权益", "专利与保护"),
    ("医学结果", "疗效"),
    ("医学结果", "安全性"),
    ("医学结果", "疗效与安全性矩阵"),
    ("观察与依据", "历史与边缘观察"),
    ("观察与依据", "研究依据与局限"),
]


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("report-a-data root must be object")
    return payload


def _name(products: dict[str, dict[str, Any]], product_id: str) -> str:
    return str(products.get(product_id, {}).get("name") or product_id)


def _trial_name(trials: dict[str, dict[str, Any]], trial_id: str | None) -> str:
    if not trial_id:
        return UNPUBLISHED
    return str(trials.get(trial_id, {}).get("name") or trial_id)


def _usable_width(*, landscape: bool = False) -> float:
    from ci_workflow.renderers.pdf_native import tokens

    size = tokens.A4_LANDSCAPE if landscape else tokens.A4_PORTRAIT
    return float(size[0]) - 2 * float(tokens.MARGIN_X)


def _efficacy_points(
    data: dict[str, Any],
    products: dict[str, dict[str, Any]],
    trials: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for row in data.get("efficacy") or []:
        points.append(
            {
                "product_zh": _name(products, str(row["product_id"])),
                "trial_zh": _trial_name(trials, row.get("trial_id")),
                "arm_zh": str(row.get("arm") or UNPUBLISHED),
                "endpoint_zh": str(row.get("endpoint") or UNPUBLISHED),
                "timepoint_zh": str(row.get("timepoint") or UNPUBLISHED),
                "population_zh": str(row.get("population") or UNPUBLISHED),
                "value": row.get("value"),
                "unit": str(row.get("unit") or "%"),
                "numerator": row.get("numerator"),
                "denominator": row.get("denominator"),
            }
        )
    return points


def _forest_rows(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_product: dict[str, dict[str, float]] = defaultdict(dict)
    for point in points:
        if point.get("value") is None:
            continue
        by_product[str(point["product_zh"])][str(point["arm_zh"])] = float(point["value"])
    rows: list[dict[str, Any]] = []
    for product, arms in by_product.items():
        treatment = arms.get("治疗组")
        control = arms.get("对照组", arms.get("安慰剂组"))
        if treatment is None or control is None:
            continue
        rows.append({"label_zh": product, "difference": treatment - control})
    return rows


def _safety_cells(
    data: dict[str, Any], products: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for row in data.get("safety") or []:
        cells.append(
            {
                "product_zh": _name(products, str(row["product_id"])),
                "category_zh": str(row.get("category") or UNPUBLISHED),
                "value": row.get("value"),
                "term_zh": str(row.get("term") or UNPUBLISHED),
                "arm_zh": str(row.get("arm") or "治疗组"),
                "trial_zh": str(row.get("trial_id") or UNPUBLISHED),
                "time_window_zh": str(row.get("time_window") or UNPUBLISHED),
                "disclosure_zh": disclosure_zh(row.get("disclosure_state")),
                "unit": str(row.get("unit") or "%"),
                "numerator": row.get("numerator"),
                "denominator": row.get("denominator"),
            }
        )
    return cells


def _matrix_points(
    data: dict[str, Any],
    products: dict[str, dict[str, Any]],
    trials: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    treatment_eff: dict[str, float] = {}
    for row in data.get("efficacy") or []:
        if row.get("arm") == "治疗组" and row.get("value") is not None:
            treatment_eff[str(row["product_id"])] = float(row["value"])
    teae: dict[str, float] = {}
    for row in data.get("safety") or []:
        if (
            _is_any_teae_row(row)
            and row.get("arm", "治疗组") == "治疗组"
            and row.get("value") is not None
        ):
            teae[str(row["product_id"])] = float(row["value"])
    points: list[dict[str, Any]] = []
    for product in data.get("products") or []:
        pid = str(product["id"])
        trial = next(
            (item for item in data.get("trials") or [] if item.get("product_id") == pid), None
        )
        size = None
        if trial is not None:
            size = trial.get("treatment_sample_size") or trial.get("sample_size")
        x_val = treatment_eff.get(pid)
        y_val = teae.get(pid)
        points.append(
            {
                "label_zh": _name(products, pid),
                "trial_zh": _trial_name(trials, None if trial is None else str(trial.get("id"))),
                "x": x_val,
                "y": y_val,
                "size": size,
                "status_zh": "可比" if x_val is not None and y_val is not None else UNPUBLISHED,
            }
        )
    return points


def _summary_highlights(
    data: dict[str, Any],
    products: dict[str, dict[str, Any]],
    trials: dict[str, dict[str, Any]],
) -> tuple[list[str], list[list[Any]]]:
    bullets: list[str] = []
    bullets.append(
        f"范围内产品 {len(products)} 个、试验 {len(trials)} 项；含终止/边缘观察，不删减已纳入项目。"
    )
    highlight_rows: list[list[Any]] = []
    for row in data.get("efficacy") or []:
        if row.get("arm") != "治疗组" or row.get("value") is None:
            continue
        control = next(
            (
                item
                for item in data.get("efficacy") or []
                if item.get("product_id") == row.get("product_id")
                and item.get("trial_id") == row.get("trial_id")
                and item.get("arm") in {"对照组", "安慰剂组"}
                and item.get("value") is not None
            ),
            None,
        )
        delta = float(row["value"]) - float(control["value"]) if control is not None else None
        highlight_rows.append(
            [
                _name(products, str(row["product_id"])),
                _trial_name(trials, row.get("trial_id")),
                str(row.get("endpoint") or UNPUBLISHED),
                display_value(row.get("value"), unit="%"),
                display_value(None if control is None else control.get("value"), unit="%"),
                "—" if delta is None else f"{delta:+.1f} 百分点",
            ]
        )
    if highlight_rows:
        bullets.append("核心疗效比较以锚定试验内治疗组与对照组并列呈现，不进行跨试验合并。")
    teae_open = [
        row
        for row in data.get("safety") or []
        if _is_any_teae_row(row) and row.get("value") is not None
    ]
    if teae_open:
        bullets.append(
            f"已披露治疗期间不良事件观察 {len(teae_open)} 条；安全性完整表保留观察窗与披露状态。"
        )
    terminated = [
        item
        for item in data.get("products") or []
        if item.get("status") in {"终止", "暂停", "撤回"}
    ]
    if terminated:
        bullets.append(
            "历史与边缘层保留：" + "、".join(str(item.get("name")) for item in terminated) + "。"
        )
    return bullets, highlight_rows


def build_report_a_native_pdf(*, report_data_path: Path | str, output_path: Path | str) -> Path:
    """Build complete A-class native PDF from locked report-data JSON."""
    for name in ("report_data_path", "output_path"):
        if any(marker in name for marker in _FORBIDDEN):
            raise ValueError(f"forbidden parameter name: {name}")

    source = Path(report_data_path)
    output = Path(output_path)
    data = _load(source)
    products = product_map(list(data.get("products") or []))
    trials = trial_map(list(data.get("trials") or []))
    styles = make_styles()
    output.parent.mkdir(parents=True, exist_ok=True)

    title = f"{data.get('indication', '适应症')}竞品全景"
    doc = make_doc(
        str(output),
        title=title,
        indication=str(data.get("indication") or ""),
        footer_label=title,
    )
    story: list[Any] = []

    # ---- Front matter: cover / 目录 / 首页摘要 ----
    bookmark(story, "cover", "封面")
    cover_block(
        story,
        styles=styles,
        title=title,
        subtitle="竞品格局 · 产品与临床 · 监管权益 · 医学比较",
        indication=str(data.get("indication") or UNPUBLISHED),
        cutoff=cutoff_zh(data.get("data_cutoff")),
    )

    section_break(story)
    bookmark(story, "toc", "目录")
    toc_page(story, styles=styles, entries=_A_TOC)

    section_break(story)
    bookmark(story, "summary", "首页摘要")
    summary_bullets, highlight_rows = _summary_highlights(data, products, trials)
    executive_summary_page(
        story,
        styles=styles,
        bullets=summary_bullets,
        highlight_rows=highlight_rows,
        highlight_headers=["产品", "试验", "终点", "治疗组", "对照组", "组间差值"],
        highlight_widths=[28 * mm, 24 * mm, 36 * mm, 22 * mm, 22 * mm, 28 * mm],
    )

    # ---- Dense profile family ----
    section_break(story, landscape=True)
    bookmark(story, "landscape", "竞争格局")
    section_heading(
        story,
        styles,
        "竞争格局",
        caption="展示全部项目的靶点、模态、阶段、地域和开发状态；不截断证据稀疏或已终止项目。",
    )
    landscape_rows = [
        [
            item.get("name"),
            item.get("target"),
            item.get("modality"),
            item.get("phase"),
            item.get("status"),
            " / ".join(item.get("regions") or []) or UNPUBLISHED,
            item.get("developer"),
        ]
        for item in data.get("products") or []
    ]
    story.extend(
        continuation_table_blocks(
            title="竞争格局完整表",
            headers=["产品", "靶点", "模态", "阶段", "状态", "地域", "开发方"],
            rows=landscape_rows,
            styles=styles,
            col_widths=[28 * mm, 18 * mm, 22 * mm, 16 * mm, 16 * mm, 28 * mm, 34 * mm],
            rows_per_page=8,
        )
    )

    # Same landscape reading cluster: product overview follows without forced sparse page.
    bookmark(story, "product-overview", "产品总览")
    section_heading(story, styles, "产品总览")
    product_rows = [
        [
            item.get("name"),
            item.get("route"),
            item.get("mechanism"),
            item.get("status"),
            item.get("phase"),
        ]
        for item in data.get("products") or []
    ]
    story.extend(
        continuation_table_blocks(
            title="产品总览完整表",
            headers=["产品", "给药途径", "机制", "状态", "阶段"],
            rows=product_rows,
            styles=styles,
            col_widths=[28 * mm, 22 * mm, 90 * mm, 18 * mm, 18 * mm],
            rows_per_page=8,
        )
    )

    bookmark(story, "clinical-portfolio", "临床开发组合")
    section_heading(story, styles, "临床开发组合")
    clinical_rows = [
        [
            _name(products, str(item.get("product_id"))),
            item.get("name"),
            item.get("display_id") or UNPUBLISHED,
            item.get("phase"),
            item.get("region"),
            item.get("status"),
            item.get("role") or UNPUBLISHED,
            display_value(item.get("sample_size"), unit="例"),
            display_value(item.get("treatment_sample_size"), unit="例"),
        ]
        for item in data.get("trials") or []
    ]
    story.extend(
        continuation_table_blocks(
            title="临床开发组合完整表",
            headers=["产品", "试验", "登记号", "阶段", "地域", "状态", "角色", "总N", "治疗N"],
            rows=clinical_rows,
            styles=styles,
            col_widths=[
                24 * mm,
                24 * mm,
                28 * mm,
                14 * mm,
                14 * mm,
                16 * mm,
                28 * mm,
                14 * mm,
                16 * mm,
            ],
            rows_per_page=10,
        )
    )

    # Regulatory / companies / patents share one dense portrait page.
    section_break(story)
    bookmark(story, "regulatory", "中国与全球监管")
    section_heading(story, styles, "中国与全球监管")
    regulatory_rows = [
        [
            _name(products, str(item.get("product_id"))),
            item.get("track"),
            item.get("event"),
            item.get("date") or UNPUBLISHED,
            item.get("status") or UNPUBLISHED,
        ]
        for item in data.get("regulatory") or []
    ]
    story.extend(
        continuation_table_blocks(
            title="监管事件完整表",
            headers=["产品", "分轨", "事件", "日期", "状态"],
            rows=regulatory_rows,
            styles=styles,
            col_widths=[28 * mm, 18 * mm, 55 * mm, 28 * mm, 28 * mm],
            rows_per_page=8,
        )
    )

    bookmark(story, "companies-transactions", "企业与交易")
    section_heading(story, styles, "企业与交易")
    company_rows = [
        [
            _name(products, str(item.get("product_id"))),
            item.get("relationship"),
            item.get("licensor") or UNPUBLISHED,
            item.get("licensee") or UNPUBLISHED,
            item.get("territory") or UNPUBLISHED,
            item.get("transaction") or UNPUBLISHED,
        ]
        for item in data.get("companies") or []
    ]
    story.extend(
        continuation_table_blocks(
            title="企业与交易完整表",
            headers=["产品", "关系", "许可方", "被许可方", "地域权益", "交易条款"],
            rows=company_rows,
            styles=styles,
            col_widths=[24 * mm, 24 * mm, 26 * mm, 26 * mm, 24 * mm, 34 * mm],
            rows_per_page=8,
        )
    )

    bookmark(story, "patents-protection", "专利与保护")
    section_heading(story, styles, "专利与保护")
    patent_rows = [
        [
            _name(products, str(item.get("product_id"))),
            item.get("display_family") or item.get("family") or UNPUBLISHED,
            item.get("jurisdiction") or UNPUBLISHED,
            item.get("scope") or UNPUBLISHED,
            item.get("expiry") or UNPUBLISHED,
            item.get("exclusivity") or UNPUBLISHED,
        ]
        for item in data.get("patents") or []
    ]
    story.extend(
        continuation_table_blocks(
            title="专利与保护完整表",
            headers=["产品", "专利族", "法域", "保护范围", "到期", "监管独占"],
            rows=patent_rows,
            styles=styles,
            col_widths=[24 * mm, 28 * mm, 28 * mm, 40 * mm, 28 * mm, 28 * mm],
            rows_per_page=8,
        )
    )

    # ---- Comparison family ----
    efficacy_points = _efficacy_points(data, products, trials)
    section_break(story, landscape=True)
    bookmark(story, "efficacy", "疗效")
    section_heading(
        story,
        styles,
        "疗效",
        caption="按锚定核心试验比较常用主要疗效终点；治疗组与各自对照组始终并列，不跨试验池化。",
    )
    story.append(Paragraph("疗效比较图", styles["caption"]))
    story.append(
        efficacy_grouped_bar_chart(
            efficacy_points,
            width=_usable_width(landscape=True),
            height=120,
            title="疗效比较柱状图 · 治疗组与对照组同屏",
        )
    )
    story.append(Spacer(1, 2))
    story.append(Paragraph("不合并森林图（组间差值）", styles["caption"]))
    story.append(
        efficacy_forest_chart(
            _forest_rows(efficacy_points),
            width=_usable_width(landscape=True),
            height=120,
            title="疗效森林图 · 治疗—对照差值",
        )
    )
    story.append(Spacer(1, 2))
    efficacy_table_rows = [
        [
            point["product_zh"],
            point["trial_zh"],
            point["arm_zh"],
            point["endpoint_zh"],
            point["timepoint_zh"],
            display_value(point["value"], unit=point["unit"]),
            (
                f"{point['numerator']}/{point['denominator']}"
                if point.get("numerator") is not None and point.get("denominator") is not None
                else UNPUBLISHED
            ),
            point["population_zh"],
        ]
        for point in efficacy_points
    ]
    story.extend(
        continuation_table_blocks(
            title="疗效完整数据表",
            headers=["产品", "试验", "组别", "终点", "时间点", "数值", "例数", "人群"],
            rows=efficacy_table_rows,
            styles=styles,
            col_widths=[24 * mm, 24 * mm, 16 * mm, 32 * mm, 18 * mm, 18 * mm, 20 * mm, 22 * mm],
            rows_per_page=10,
        )
    )

    safety_cells = _safety_cells(data, products)
    section_break(story, landscape=True)
    bookmark(story, "safety", "安全性")
    heatmap_source: dict[tuple[str, str], dict[str, Any]] = {}
    for cell in safety_cells:
        key = (str(cell["product_zh"]), str(cell["category_zh"]))
        heatmap_source.setdefault(key, cell)
    story.append(
        KeepTogether(
            [
                Paragraph("安全性", styles["section"]),
                Paragraph(
                    "以热图和完整表格比较严重、特别关注、治疗期间及常见不良事件；保留观察窗和披露状态。",
                    styles["caption"],
                ),
                Paragraph("安全性热图", styles["caption"]),
                safety_heatmap_chart(
                    list(heatmap_source.values()),
                    width=_usable_width(landscape=True),
                    height=150,
                    title="安全性热图 · 产品 × 事件类别",
                ),
            ]
        )
    )
    story.append(Spacer(1, 2))
    safety_rows = [
        [
            cell["product_zh"],
            cell["category_zh"],
            cell["term_zh"],
            cell["arm_zh"],
            cell["time_window_zh"],
            display_value(cell["value"], unit=cell["unit"]),
            (
                f"{cell['numerator']}/{cell['denominator']}"
                if cell.get("numerator") is not None and cell.get("denominator") is not None
                else UNPUBLISHED
            ),
            cell["disclosure_zh"],
        ]
        for cell in safety_cells
    ]
    story.extend(
        continuation_table_blocks(
            title="安全性完整数据表",
            headers=["产品", "类别", "术语", "组别", "观察窗", "发生率", "例数", "披露"],
            rows=safety_rows,
            styles=styles,
            col_widths=[22 * mm, 28 * mm, 28 * mm, 16 * mm, 24 * mm, 18 * mm, 18 * mm, 18 * mm],
            rows_per_page=12,
        )
    )

    matrix_points = _matrix_points(data, products, trials)
    section_break(story, landscape=True)
    bookmark(story, "matrix", "疗效与安全性矩阵")
    section_heading(
        story,
        styles,
        "疗效与安全性矩阵",
        caption=(
            "气泡面积反映治疗组样本量；不生成综合分数。当前映射：X=所选疗效终点治疗臂数值，"
            "Y=治疗期间不良事件发生率（图中倒序），半径∝√N。"
        ),
    )
    story.append(Paragraph("疗效与安全性气泡图", styles["caption"]))
    story.append(
        bubble_matrix_chart(
            [pt for pt in matrix_points if pt.get("x") is not None and pt.get("y") is not None],
            width=_usable_width(landscape=True),
            height=150,
            title="疗效与安全性气泡图",
            mapping_note="气泡面积反映治疗组样本量；缺失坐标不绘制为数值零。",
        )
    )
    story.append(Spacer(1, 2))
    story.append(Paragraph("疗效与安全性矩阵完整数据表", styles["caption"]))
    matrix_rows = [
        [
            pt["label_zh"],
            pt["trial_zh"],
            display_value(pt.get("x"), unit="%"),
            display_value(pt.get("y"), unit="%"),
            display_value(pt.get("size"), unit="例"),
            pt["status_zh"],
        ]
        for pt in matrix_points
    ]
    story.append(
        styled_table(
            ["产品", "试验", "疗效X", "安全性Y", "计划治疗N", "状态"],
            matrix_rows,
            styles,
            [32 * mm, 32 * mm, 24 * mm, 28 * mm, 22 * mm, 24 * mm],
        )
    )

    if UNPUBLISHED not in " ".join(str(cell) for row in safety_rows for cell in row):
        story.append(
            Paragraph(
                f"例数栏指终点分析例数；未随结果公开时记为{UNPUBLISHED}，不以计划治疗组样本量代填。",
                styles["caption"],
            )
        )

    # History + evidence share one dense page.
    section_break(story)
    bookmark(story, "historical-edge", "历史与边缘观察")
    section_heading(
        story,
        styles,
        "历史与边缘观察",
        caption="保留暂停、终止、撤回、放弃项目及邻近机制观察层，不从当前竞品范围静默删除。",
    )
    history_rows = [
        [
            _name(products, str(item.get("product_id"))),
            item.get("status") or UNPUBLISHED,
            item.get("date") or UNPUBLISHED,
            item.get("observation") or UNPUBLISHED,
        ]
        for item in data.get("history") or []
    ] or [[UNPUBLISHED, UNPUBLISHED, UNPUBLISHED, UNPUBLISHED]]
    story.extend(
        continuation_table_blocks(
            title="历史与边缘观察完整表",
            headers=["产品", "状态", "日期", "观察"],
            rows=history_rows,
            styles=styles,
            col_widths=[28 * mm, 22 * mm, 28 * mm, 90 * mm],
            rows_per_page=8,
        )
    )

    bookmark(story, "evidence-limitations", "研究依据与局限")
    section_heading(
        story,
        styles,
        "研究依据与局限",
        caption="只呈现影响医学解释的来源、方法与简洁局限；检索尝试和技术诊断留在项目记录。",
    )
    source_rows = [
        [
            item.get("source") or UNPUBLISHED,
            item.get("scope") or UNPUBLISHED,
            item.get("maturity") or UNPUBLISHED,
            item.get("limitation") or UNPUBLISHED,
        ]
        for item in data.get("sources") or []
    ] or [[UNPUBLISHED, UNPUBLISHED, UNPUBLISHED, UNPUBLISHED]]
    story.extend(
        continuation_table_blocks(
            title="研究依据与局限完整表",
            headers=["来源", "范围", "成熟度", "局限"],
            rows=source_rows,
            styles=styles,
            col_widths=[36 * mm, 42 * mm, 36 * mm, 54 * mm],
            rows_per_page=8,
        )
    )

    doc.build(story)
    if not output.is_file() or output.stat().st_size < 2000:
        raise RuntimeError(f"A PDF 生成失败或过小：{output}")
    return output


__all__ = ["build_report_a_native_pdf"]
