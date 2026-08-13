"""从 Python 权威 API 生成 Task 4.4 浏览器夹具 HTML（禁止手写分组）。"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from ci_workflow.reports.common.chart_specs import (
    ChartType,
    resolve_chart_type,
    split_compatible_groups,
    validate_all_rows_covered,
)

_THIS_DIR = Path(__file__).resolve().parent


def _raw_source() -> list[dict[str, Any]]:
    import importlib.util

    path = _THIS_DIR / "source_rows.py"
    spec = importlib.util.spec_from_file_location("task44_source_rows", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载夹具行定义：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return [dict(row) for row in module.SOURCE_ROWS]


def build_chart_payload(
    *,
    chart_type: ChartType | str = ChartType.BAR,
    source_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Resolve + split; return browser payload (snapshot + digest + groups)."""
    rows = [dict(r) for r in (source_rows if source_rows is not None else _raw_source())]
    resolved = resolve_chart_type(rows, chart_type)
    groups = split_compatible_groups(resolved)
    validate_all_rows_covered(resolved, groups)

    snapshot_id = str(resolved[0]["report_snapshot_id"]) if resolved else ""
    digest_payload = {
        "kind": "fixture-row-set",
        "snapshot_id": snapshot_id,
        "row_ids": sorted(str(r["row_id"]) for r in resolved),
    }
    row_set_digest = hashlib.sha256(
        json.dumps(
            digest_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()

    group_payloads = [
        {
            "title_zh": group.title_zh,
            "split_dims": list(group.split_dims),
            "rows": [dict(row) for row in group.rows],
        }
        for group in groups
    ]
    return {
        "snapshot_id": snapshot_id,
        "row_set_digest": row_set_digest,
        "chart_rows": resolved,
        "chart_groups": group_payloads,
    }


def render_fixture_html(
    *,
    assets_rel: str,
    payload: dict[str, Any] | None = None,
) -> str:
    """Render fixture using Task 4.3 filter URL contract + local ECharts."""
    from ci_workflow.renderers.portal.page_shell import _render_filter_panel

    data = payload or build_chart_payload()
    styles = (_THIS_DIR / "shell.css").read_text(encoding="utf-8")
    chart_rows_json = json.dumps(data["chart_rows"], ensure_ascii=False)
    chart_groups_json = json.dumps(data["chart_groups"], ensure_ascii=False)

    filter_rows = [
        {
            "id": row["row_id"],
            "unit": row.get("unit"),
            "time_window": row.get("time_window"),
            "analysis_population": row.get("analysis_population"),
            "control_role": row.get("control_role"),
            "module_id": "efficacy",
        }
        for row in data["chart_rows"]
    ]
    filter_groups = [
        {
            "title": "单位",
            "scope": "page",
            "items": [
                {"id": "mg/dL", "label": "mg/dL", "dim": "unit"},
                {"id": "nmol/L", "label": "nmol/L", "dim": "unit"},
            ],
        },
        {
            "title": "时间窗",
            "scope": "page",
            "items": [
                {"id": "12周", "label": "12周", "dim": "time_window"},
                {"id": "24周", "label": "24周", "dim": "time_window"},
            ],
        },
        {
            "title": "分析人群",
            "scope": "page",
            "items": [
                {"id": "ITT", "label": "意向治疗人群（ITT）", "dim": "analysis_population"},
                {"id": "PP", "label": "符合方案人群（PP）", "dim": "analysis_population"},
            ],
        },
        {
            "title": "对照角色",
            "scope": "module",
            "module_id": "efficacy",
            "module_label": "疗效数据",
            "items": [
                {"id": "安慰剂", "label": "安慰剂", "dim": "control_role"},
                {"id": "活性对照", "label": "活性对照", "dim": "control_role"},
            ],
        },
    ]
    filter_html = _render_filter_panel(
        filter_groups=filter_groups,
        synthetic_rows=filter_rows,
        page_id="/overview",
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="only light">
  <title>疗效与安全性概览</title>
  <link rel="stylesheet" href="{assets_rel}/portal.css">
  <style>
{styles}
  </style>
</head>
<body>
  <header class="portal-page-head">
    <h1 class="portal-page-title">疗效与安全性概览</h1>
    <p class="portal-lead">主要终点与关键次要终点的疗效比较及安全性监测。
    图表与完整表格联动展示。</p>
  </header>

{filter_html}
  <div class="kz-chart-empty" id="kz-chart-empty" style="display:none" aria-live="polite">
    <p class="kz-chart-empty__title">当前选择下暂无可比较数据</p>
  </div>
  <section class="kz-chart-module" id="kz-chart-module" aria-label="图表与数据表"></section>
  <div class="kz-meta" id="kz-meta" hidden>
    <span id="kz-meta-row-set-digest"></span>
    <span id="kz-meta-snapshot-id"></span>
    <span id="kz-meta-row-count"></span>
  </div>

  <script src="{assets_rel}/echarts.min.js"></script>
  <script>
  window.__CHART_ROWS__ = {chart_rows_json};
  window.__CHART_GROUPS__ = {chart_groups_json};
  window.__SNAPSHOT_ID__ = {json.dumps(data["snapshot_id"])};
  window.__ROW_SET_DIGEST__ = {json.dumps(data["row_set_digest"])};
  </script>
  <script src="{assets_rel}/portal.js"></script>
  <script src="{assets_rel}/charts.js"></script>
</body>
</html>
"""


def write_fixture_site(output_dir: Path, *, repo_root: Path) -> Path:
    """Write a self-contained fixture site with local packaged assets."""
    output_dir.mkdir(parents=True, exist_ok=True)
    assets = output_dir / "assets"
    assets.mkdir(exist_ok=True)

    packaged = repo_root / "src/ci_workflow/renderers/portal/assets"
    echarts_src = packaged / "echarts.min.js"
    charts_src = repo_root / "assets/portal/charts.js"
    portal_js = packaged / "portal.js"
    portal_css = packaged / "portal.css"
    if not echarts_src.is_file():
        raise FileNotFoundError(f"包内 ECharts 缺失（失败关闭）：{echarts_src}")
    if not charts_src.is_file():
        raise FileNotFoundError(f"charts.js 缺失：{charts_src}")
    if not portal_js.is_file() or not portal_css.is_file():
        raise FileNotFoundError("包内 portal.js / portal.css 缺失（失败关闭）")

    shutil.copy2(echarts_src, assets / "echarts.min.js")
    shutil.copy2(charts_src, assets / "charts.js")
    shutil.copy2(portal_js, assets / "portal.js")
    shutil.copy2(portal_css, assets / "portal.css")

    index = output_dir / "index.html"
    index.write_text(render_fixture_html(assets_rel="assets"), encoding="utf-8")
    return index
