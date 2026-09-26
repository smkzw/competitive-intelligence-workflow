"""R13 图例、产品来源与数据依据面板的静态回归合同。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "src" / "ci_workflow" / "renderers" / "portal" / "assets"


def test_grouped_bar_legend_uses_the_same_colors_as_the_bars() -> None:
    source = (ASSETS / "charts.js").read_text(encoding="utf-8")

    assert 'var seriesColor = String(key).split(":")[0] === "control"' in source
    assert "itemStyle: { color: seriesColor }" in source
    assert "color: seriesColor" in source


def test_grouped_bar_category_does_not_repeat_identity_under_the_legend() -> None:
    source = (ASSETS / "charts.js").read_text(encoding="utf-8")
    grouped_bar = source.split("  function groupedBarOption(group) {", 1)[1].split(
        "  function buildBarOption(group) {", 1
    )[0]

    assert "data: categories" in grouped_bar
    assert 'name: group.x_axis_label_zh || "产品｜试验"' not in grouped_bar
    assert 'type: "scroll"' in grouped_bar
    assert "top: 2" in grouped_bar
    assert "top: hasLegend ? 52 : 32" in source


def test_grouped_bar_evidence_targets_follow_series_order_without_overlap() -> None:
    source = (ASSETS / "charts.js").read_text(encoding="utf-8")
    css = (ASSETS / "report-b.css").read_text(encoding="utf-8")

    assert "function groupedSeriesOrder(rows)" in source
    assert 'data-chart-series-index' in source
    assert 'data-chart-data-index' in source
    assert "getItemGraphicEl(dataIndex)" in source
    assert "seriesOffset" not in source
    assert "width: 32px" in css
    assert "height: 32px" in css


def test_b_rebuilt_table_cells_open_the_evidence_drawer() -> None:
    source = (ASSETS / "report-b.js").read_text(encoding="utf-8")

    assert 'event.target.closest("[data-evidence-open]")' in source
    assert "drawer.openByRowId(rowId, trigger)" in source
    assert "bindEvidenceTriggers();" in source


def test_shared_evidence_drawer_is_a_modal_dialog_and_traps_focus() -> None:
    markup = (
        ROOT / "src" / "ci_workflow" / "renderers" / "portal" / "evidence_drawer.py"
    ).read_text(encoding="utf-8")
    behavior = (ASSETS / "evidence-drawer.js").read_text(encoding="utf-8")

    assert 'role="dialog" aria-modal="true"' in markup
    assert 'aria-labelledby="kz-evidence-drawer-title"' in markup
    assert "if (closeBtn) closeBtn.focus();" in behavior
    assert 'if (e.key !== "Tab") return;' in behavior


def test_product_drawer_filters_product_specific_patent_sources() -> None:
    source = (ASSETS / "report-a.js").read_text(encoding="utf-8")

    assert "var productSources = sources.filter" in source
    assert "return patents[i].product_id === product.id" in source
    assert 'appendInsightField(fields, "来源数量", productSources.length)' in source


def test_a_bubble_uses_formal_parenthetical_code_without_generic_product_prefix() -> None:
    source = (ASSETS / "report-a.js").read_text(encoding="utf-8")

    assert "if (/^\\d+$/.test(shortName) && parenthetical)" in source
    assert 'shortName = "产品" + shortName' not in source
    assert "shortName.length > 12" in source


def test_c_evidence_explanation_does_not_expose_internal_identifiers() -> None:
    source = (
        ROOT / "src" / "ci_workflow" / "renderers" / "portal" / "report_c.py"
    ).read_text(encoding="utf-8")

    assert '"Identification": "研究基本信息"' in source
    assert "本条信息摘自临床试验登记页" in source
    explanation = source[
        source.index("explanation=_evidence_field(") : source.index(
            "original_text=", source.index("explanation=_evidence_field(")
        )
    ]
    assert "证据标识" not in explanation
    assert "observation.row_id" not in explanation


def test_b_safety_uses_chinese_event_labels_and_explains_heatmap_color() -> None:
    renderer = (
        ROOT / "src" / "ci_workflow" / "renderers" / "portal" / "report_b.py"
    ).read_text(encoding="utf-8")
    template = (
        ROOT
        / "src"
        / "ci_workflow"
        / "renderers"
        / "portal"
        / "templates"
        / "b"
        / "page.html.j2"
    ).read_text(encoding="utf-8")

    for label in (
        "特别关注不良事件",
        "突破性溶血",
        "因不良事件停药",
        "头痛",
        "严重不良反应",
        "因治疗期间不良事件停止治疗",
    ):
        assert label in renderer
    assert "颜色深浅仅表示同一图内发生率高低" in template
    assert "不同图的色阶不可直接比较" in template


def test_a_product_drawer_separates_program_stage_trial_phase_and_observation_time() -> None:
    source = (ASSETS / "report-a.js").read_text(encoding="utf-8")

    assert '["项目最高阶段", product.phase]' in source
    assert '["证据试验分期", trial ? trial.phase : "未公开"]' in source
    assert '["疗效数据时间点", pair ? efficacyObservationTimepoint(pair)' in source
    assert '"｜项目最高阶段：" + product.phase' in source
    assert "function efficacyObservationTimepoint(pair)" in source


def test_c_full_design_matrix_precedes_disclosure_status_chart() -> None:
    template = (
        ROOT
        / "src"
        / "ci_workflow"
        / "renderers"
        / "portal"
        / "templates"
        / "c"
        / "page.html.j2"
    ).read_text(encoding="utf-8")

    # v1.3 统一门户规范要求先用适配图形回答问题，再原位折叠完整表格。
    assert template.index('id="kz-c-chart-visuals"') < template.index(
        'id="kz-c-design-matrix"'
    )
