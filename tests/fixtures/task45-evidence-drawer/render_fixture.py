"""从生产校验器生成 Task 4.5 数据依据面板浏览器夹具站点。

- 全部证据负载经 ``validate_evidence_view_payload`` 验证（冻结页面目录权威、
  观察类型与抽屉配置一致、披露状态与值一致）。
- 三页站点：疗效与安全性概览（A，通用观察）、人口学（B，基线观察）、
  试验完成情况总览（B，处置观察）；每页经 ``render_page_html`` 渲染并把
  ``evidence_views`` 嵌入同一页面。
- 疗效页同时嵌入与证据行同一 ``row_id`` 的柱状图、热图与状态矩阵，供
  真实 pointer 命中测试；表格数据单元（名称/产品/试验）本身即可打开
  数据依据，不再使用独立首列按钮或「事实行」工程说法。
- 筛选可见性变化经 MutationObserver 与生产 ``portal.js`` 同步到
  ``pruneToVisible``，不得放宽筛选。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

from ci_workflow.reports.common.chart_specs import (
    ChartType,
    resolve_chart_type,
    split_compatible_groups,
)
from ci_workflow.reports.common.evidence_view import EvidenceView, validate_evidence_view_payload

_THIS_DIR = Path(__file__).resolve().parent

PAGE_EFFICACY = "efficacy"
PAGE_BASELINE = "baseline-demographics"
PAGE_DISPOSITION = "disposition-overview"
SNAPSHOT = "report-snapshot-45"


def _load_source_payloads() -> list[dict[str, Any]]:
    path = _THIS_DIR / "source_evidence.py"
    spec = importlib.util.spec_from_file_location("task45_source_evidence", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载夹具证据负载：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return [dict(payload) for payload in module.ALL_PAYLOADS]


def validated_views() -> list[EvidenceView]:
    """逐条经生产校验器验证的不可变证据视图（同页固定对照行唯一）。"""
    views = [validate_evidence_view_payload(p) for p in _load_source_payloads()]
    row_ids = [view.row.row_id for view in views]
    if len(set(row_ids)) != len(row_ids):
        raise RuntimeError("夹具证据负载包含重复行，必须失败关闭")
    return views


def fixture_row_ids() -> dict[str, str]:
    """稳定行标识映射：中文显示标签 → row_id（测试按标签取行）。"""
    return {view.row.display_label_zh: view.row.row_id for view in validated_views()}


def _views_by_page(views: list[EvidenceView]) -> dict[str, list[EvidenceView]]:
    grouped: dict[str, list[EvidenceView]] = {}
    for view in views:
        grouped.setdefault(view.row.page_responsibility_id, []).append(view)
    return grouped


def _field_text(field: Any) -> str:
    value = getattr(field, "value", None)
    return "" if value is None else str(value)


def _numeric_or_none(field: Any) -> float | None:
    raw = getattr(field, "value", None)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _chart_base(view: EvidenceView, **extra: Any) -> dict[str, Any]:
    row = view.row
    group_text = _field_text(view.group_zh) or "治疗组"
    disclosure = getattr(row.disclosure_state, "value", None) or str(row.disclosure_state)
    payload: dict[str, Any] = {
        "row_id": row.row_id,
        "display_label_zh": view.element_zh,
        "product_zh": view.product_zh,
        "trial_zh": view.trial_zh,
        "group_zh": group_text,
        "unit": _field_text(view.unit),
        "scale": "原始",
        "statistical_form": "均值差",
        "direction": "lower_better",
        "time_window": "16周",
        "analysis_population": "ITT",
        "control_role": "安慰剂",
        "denominator": 120,
        "disclosure_state": disclosure,
        "report_snapshot_id": row.report_snapshot_id,
        "product_id": row.product_id,
        "trial_id": row.trial_id,
        "group_id": row.group_id,
        "endpoint_id": row.endpoint_id or "endpoint-fixture",
        "category": group_text,
    }
    payload.update(extra)
    return payload


def _groups_for(chart_type: ChartType, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    resolved = resolve_chart_type(rows, chart_type)
    groups = split_compatible_groups(resolved)
    return [
        {
            "title_zh": group.title_zh,
            "split_dims": list(group.split_dims),
            "rows": [dict(row) for row in group.rows],
        }
        for group in groups
    ]


def build_efficacy_chart_payload(views: list[EvidenceView]) -> dict[str, Any]:
    """疗效页图表：柱状、热图、状态矩阵，行标识与证据视图同一集合。"""
    by_label = {view.row.display_label_zh: view for view in views}
    treat = by_label["疗效 · 产品甲 · 治疗组 · EASI评分变化值"]
    ctrl = by_label["疗效 · 产品甲 · 对照组 · EASI评分变化值"]
    beta_treat = by_label["疗效 · 产品乙 · 治疗组 · EASI评分变化值"]
    beta_ctrl = by_label["疗效 · 产品乙 · 对照组 · EASI评分变化值"]
    no_link = by_label["疗效 · 产品丙 · 治疗组 · 疾病活动度变化值"]
    invalid = by_label["疗效 · 产品丙 · 对照组 · 疾病活动度变化值"]
    completed = by_label["进展 · 产品甲 · 试验一 · 试验完成状态"]
    ongoing = by_label["进展 · 产品乙 · 试验二 · 试验完成状态"]

    bar_rows = [
        _chart_base(
            treat,
            value=_numeric_or_none(treat.value),
            numeric_value=_numeric_or_none(treat.value),
            display_value=_field_text(treat.value),
        ),
        _chart_base(
            ctrl,
            value=_numeric_or_none(ctrl.value),
            numeric_value=_numeric_or_none(ctrl.value),
            display_value=_field_text(ctrl.value),
        ),
        _chart_base(
            beta_treat,
            value=None,
            numeric_value=None,
            display_value="",
        ),
        _chart_base(
            beta_ctrl,
            value=_numeric_or_none(beta_ctrl.value),
            numeric_value=_numeric_or_none(beta_ctrl.value),
            display_value=_field_text(beta_ctrl.value),
        ),
    ]
    heatmap_rows = [
        _chart_base(
            no_link,
            event=_field_text(no_link.group_zh) or "治疗组",
            value_matrix=[_numeric_or_none(no_link.value) or 0.0],
            unit="分",
        ),
        _chart_base(
            invalid,
            event=_field_text(invalid.group_zh) or "对照组",
            value_matrix=[_numeric_or_none(invalid.value) or 0.0],
            unit="分",
        ),
    ]
    status_rows = [
        _chart_base(completed, status="已完成", coverage=0.92, unit=""),
        _chart_base(ongoing, status="进行中", coverage=0.61, unit=""),
    ]

    groups = (
        _groups_for(ChartType.BAR, bar_rows)
        + _groups_for(ChartType.HEATMAP, heatmap_rows)
        + _groups_for(ChartType.STATUS_MATRIX, status_rows)
    )
    all_rows = [row for group in groups for row in group["rows"]]
    digest_payload = {
        "kind": "task45-chart-row-set",
        "snapshot_id": SNAPSHOT,
        "row_ids": sorted({str(row["row_id"]) for row in all_rows}),
    }
    row_set_digest = hashlib.sha256(
        json.dumps(
            digest_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    return {
        "snapshot_id": SNAPSHOT,
        "row_set_digest": row_set_digest,
        "chart_rows": all_rows,
        "chart_groups": groups,
    }


_FILTER_GROUPS_EFFICACY: list[dict[str, Any]] = [
    {
        "title": "产品",
        "scope": "page",
        "items": [
            {"id": "product-alpha", "label": "产品甲", "dim": "product"},
            {"id": "product-beta", "label": "产品乙", "dim": "product"},
            {"id": "product-gamma", "label": "产品丙", "dim": "product"},
        ],
    },
]

_FIXTURE_SCRIPT = """<script>
/* Task 4.5 夹具：数据单元打开数据依据；筛选可见性变化同步固定对照。 */
(function () {
  "use strict";
  document.addEventListener("click", function (event) {
    var target = event.target;
    var btn = target && target.closest ? target.closest("[data-evidence-open]") : null;
    if (btn && window.__EVIDENCE_DRAWER__) {
      window.__EVIDENCE_DRAWER__.openByRowId(btn.getAttribute("data-evidence-open"), btn);
    }
  });
  document.addEventListener("keydown", function (event) {
    if (event.key !== "Enter" && event.key !== " ") return;
    var target = event.target;
    var cell = target && target.closest ? target.closest("[data-evidence-open]") : null;
    if (!cell || !window.__EVIDENCE_DRAWER__) return;
    event.preventDefault();
    window.__EVIDENCE_DRAWER__.openByRowId(cell.getAttribute("data-evidence-open"), cell);
  });
  function syncPrune() {
    var visible = [];
    var rows = document.querySelectorAll("[data-filter-row-id]");
    for (var i = 0; i < rows.length; i++) {
      if (rows[i].style.display !== "none") {
        visible.push(rows[i].getAttribute("data-filter-row-id"));
      }
    }
    if (window.__EVIDENCE_DRAWER__) window.__EVIDENCE_DRAWER__.pruneToVisible(visible);
  }
  var observer = new MutationObserver(syncPrune);
  var rows = document.querySelectorAll("[data-filter-row-id]");
  for (var j = 0; j < rows.length; j++) {
    observer.observe(rows[j], { attributes: true, attributeFilter: ["style"] });
  }
  window.__FIXTURE_PRUNE_SYNC__ = syncPrune;
})();
</script>
"""

_FIXTURE_STYLES = """<style>
.kz-fixture-facts {
  margin: 12px 0;
}
.kz-fixture-facts h2 {
  margin: 0 0 8px;
  font-size: 15px;
  color: #0f1115;
}
.kz-fixture-facts__table {
  border-collapse: collapse;
  width: 100%;
  max-width: 640px;
  background: #fff;
}
.kz-fixture-facts__table th,
.kz-fixture-facts__table td {
  padding: 6px 10px;
  text-align: left;
  border: 1px solid #e5e7eb;
  font-size: 13px;
  line-height: 1.3;
}
.kz-fixture-facts__table th {
  background: #f8f9fa;
  font-weight: 600;
}
.kz-fixture-cell {
  cursor: pointer;
  scroll-margin-top: 88px;
  scroll-margin-bottom: 16px;
}
.kz-fixture-cell:focus-visible {
  outline: 2px solid #407aaa;
  outline-offset: -2px;
}
.kz-chart-module {
  margin: 16px 0 8px;
}
.kz-chart-group__chart {
  width: 100%;
  min-height: 340px;
}
</style>
"""


def _render_trigger_table(views: list[EvidenceView], *, include_charts: bool = False) -> str:
    rows: list[str] = []
    disclosure_labels = {
        "reported_value": "已报告值",
        "reported_zero": "已报告零值",
        "not_publicly_disclosed": "未公开",
        "not_reported": "原文未报告",
        "below_reporting_threshold": "低于披露阈值",
        "unresolved_due_to_route": "当前技术条件下暂不可核实",
        "conflicting": "来源间存在差异",
    }
    for view in views:
        row = view.row
        label = view.row.display_label_zh
        disclosure = getattr(row.disclosure_state, "value", str(row.disclosure_state))
        disclosure_zh = disclosure_labels.get(disclosure, "披露状态待核对")
        rows.append(
            f'        <tr data-filter-row-id="{row.row_id}">\n'
            f'          <td tabindex="0" role="button" class="kz-fixture-cell '
            f'kz-fixture-cell--label" data-evidence-open="{row.row_id}" '
            f'data-evidence-field="label" aria-label="查看数据依据：{label}">{label}</td>\n'
            f'          <td tabindex="0" role="button" class="kz-fixture-cell '
            f'kz-fixture-cell--product" data-evidence-open="{row.row_id}" '
            f'data-evidence-field="product" aria-label="查看数据依据：{view.product_zh}">'
            f"{view.product_zh}</td>\n"
            f'          <td tabindex="0" role="button" class="kz-fixture-cell '
            f'kz-fixture-cell--trial" data-evidence-open="{row.row_id}" '
            f'data-evidence-field="trial" aria-label="查看数据依据：{view.trial_zh}">'
            f"{view.trial_zh}</td>\n"
            f'          <td tabindex="0" role="button" class="kz-fixture-cell '
            f'kz-fixture-cell--disclosure" data-evidence-open="{row.row_id}" '
            f'data-evidence-field="disclosure" aria-label="查看数据依据：{disclosure_zh}">'
            f"{disclosure_zh}</td>\n"
            "        </tr>"
        )
    body = "\n".join(rows)
    chart_section = (
        '<section class="kz-chart-module" id="kz-chart-module" '
        'aria-label="图表与数据表"></section>\n'
        if include_charts
        else ""
    )
    spacer = (
        '<div class="kz-fixture-spacer" style="height:420px" aria-hidden="true"></div>'
        if include_charts
        else ""
    )
    return (
        '<section class="kz-fixture-facts" aria-label="数据项">\n'
        "  <h2>当前数据</h2>\n"
        '  <table class="kz-fixture-facts__table">\n'
        "    <thead><tr><th>名称</th><th>产品</th><th>试验</th><th>披露状态</th></tr></thead>\n"
        "    <tbody>\n"
        f"{body}\n"
        "    </tbody>\n"
        "  </table>\n"
        "</section>\n"
        f"{chart_section}"
        f"{spacer}"
    )


def _filter_rows_for(views: list[EvidenceView]) -> list[dict[str, str]]:
    return [
        {
            "id": view.row.row_id,
            "module_id": "efficacy",
            "product": str(view.row.product_id or ""),
            "label": view.row.display_label_zh,
        }
        for view in views
    ]


def write_fixture_site(output_dir: Path, *, repo_root: Path) -> Path:
    """生成三页夹具站点；返回首页（疗效与安全性概览）路径。"""
    from ci_workflow.renderers.portal.builder import (
        NavEntry,
        PageSpec,
        PortalSpec,
        build_portal,
    )
    from ci_workflow.renderers.portal.global_search import SearchIndexEntry, build_search_index
    from ci_workflow.renderers.portal.page_shell import (
        render_page_html,
        render_search_index_json,
    )

    views = validated_views()
    grouped = _views_by_page(views)
    chart_payload = build_efficacy_chart_payload(grouped[PAGE_EFFICACY])

    page_specs = [
        PageSpec(
            slug="efficacy",
            title="疗效与安全性概览",
            nav_label="疗效与安全性概览",
            nav_group="医学结果",
            sections=["主要终点", "安全性事件"],
            body_text="点击任一数据项，在原页面右侧查看来源版本与精确定位。",
        ),
        PageSpec(
            slug="baseline",
            title="人口学",
            nav_label="人口学",
            nav_group="基线与人群",
            sections=["年龄", "疾病严重程度"],
            body_text="点击任一数据项，查看基线观察的规范变量族、来源字段原名与定义。",
        ),
        PageSpec(
            slug="disposition",
            title="试验完成情况总览",
            nav_label="试验完成情况",
            nav_group="试验完成情况",
            sections=["停止治疗"],
            body_text="点击任一数据项，查看停止治疗原因、互斥穷尽标记与兼容规则。",
        ),
    ]
    spec = PortalSpec(
        title="特应性皮炎竞品研究",
        footer_text="仅供产品中心医学部内部研判使用。",
        pages=page_specs,
        nav=[
            NavEntry(slug="efficacy", label="疗效与安全性概览", group="医学结果"),
            NavEntry(slug="baseline", label="人口学", group="基线与人群"),
            NavEntry(slug="disposition", label="试验完成情况", group="试验完成情况"),
        ],
    )

    build_portal(spec, output_dir)

    # 真实使用者会先搜产品/试验，而不只搜页面标题。夹具把实体入口加入同一
    # 本地搜索索引，以验证全局实体搜索不是一个只有外观的输入框。
    page_by_responsibility = {
        PAGE_EFFICACY: ("efficacy", "疗效与安全性概览"),
        PAGE_BASELINE: ("baseline", "人口学"),
        PAGE_DISPOSITION: ("disposition", "试验完成情况总览"),
    }
    entity_buckets: dict[tuple[str, str], dict[str, set[str]]] = {}
    for view in views:
        slug, page_title = page_by_responsibility[view.row.page_responsibility_id]
        key = (slug, view.product_zh)
        bucket = entity_buckets.setdefault(
            key,
            {"titles": {page_title}, "keywords": {view.product_zh}},
        )
        bucket["keywords"].update({view.trial_zh, view.element_zh})
    search_entries = build_search_index(spec.pages)
    for (slug, product), bucket in sorted(entity_buckets.items()):
        page_title = sorted(bucket["titles"])[0]
        search_entries.append(
            SearchIndexEntry(
                slug=slug,
                title=f"{product}｜{page_title}",
                keywords=sorted(bucket["keywords"]),
            )
        )
    (output_dir / "assets" / "search-index.js").write_text(
        render_search_index_json(search_entries), encoding="utf-8"
    )

    page_views = {
        "efficacy": grouped[PAGE_EFFICACY],
        "baseline": grouped[PAGE_BASELINE],
        "disposition": grouped[PAGE_DISPOSITION],
    }
    groups_json = json.dumps(chart_payload["chart_groups"], ensure_ascii=False)
    rows_json = json.dumps(chart_payload["chart_rows"], ensure_ascii=False)
    snapshot_json = json.dumps(chart_payload["snapshot_id"], ensure_ascii=False)
    digest_json = json.dumps(chart_payload["row_set_digest"], ensure_ascii=False)
    chart_boot = (
        "<script>\n"
        f"window.__CHART_GROUPS__ = {groups_json};\n"
        f"window.__CHART_ROWS__ = {rows_json};\n"
        f"window.__SNAPSHOT_ID__ = {snapshot_json};\n"
        f"window.__ROW_SET_DIGEST__ = {digest_json};\n"
        "</script>\n  "
    )
    for page in spec.pages:
        views_for_page = page_views[page.slug]
        filter_groups = _FILTER_GROUPS_EFFICACY if page.slug == "efficacy" else None
        filter_rows = _filter_rows_for(views_for_page) if page.slug == "efficacy" else None
        html = render_page_html(
            page=page,
            spec=spec,
            assets_rel="assets",
            filter_groups=filter_groups,
            synthetic_rows=filter_rows,
            evidence_views=views_for_page,
        )
        trigger = _render_trigger_table(views_for_page, include_charts=page.slug == "efficacy")
        html = html.replace(
            '<section class="portal-reading-path"',
            trigger + '\n  <section class="portal-reading-path"',
            1,
        )
        html = html.replace("<head>", "<head>\n" + _FIXTURE_STYLES, 1)
        if page.slug == "efficacy":
            html = html.replace(
                '<script src="assets/echarts.min.js"></script>',
                chart_boot + '<script src="assets/echarts.min.js"></script>',
                1,
            )
        html = html.replace("</body>", _FIXTURE_SCRIPT + "\n</body>", 1)
        (output_dir / f"{page.slug}.html").write_text(html, encoding="utf-8")

    return output_dir / "efficacy.html"
