Trellis SessionStart ✓ — continuing Worker 03 repairs. Reading the current filter, chart, and Task 4.3 URL-state surfaces first.Implementing filter overlay + portal.js URL contract, then charts.js visual/axis/undisclosed-group repairs.继续核对当前资产、测试和 Task 4.3 URL 合同，再把视觉试用问题固化进双引擎回归。正在落实筛选浮层、URL 合同、未公开态和柱图零基线，并把这些问题写进双引擎回归。**STATUS:** GREEN。未提交。

三位医学经理 REVISE 的根因是：夹具自造了 `fixture-filter.js`，把筛选面板挂到 `body` 末尾、不写 Task 4.3 的 `v1~pid~ps` URL，chip 只报「已选 N 项」；图筛选只把柱变淡、空卡和旧 tooltip 仍在；未公开组仍 `echarts.init` 出 340px 空轴；柱轴 `scale:true` 从 3.6 起、负对照柱几乎看不见且无柱端数值。已在原授权范围内直接修掉，并冻成 Chromium/WebKit 回归。

## 改动

- `assets/portal/charts.js` 与包内副本：未公开整组改为紧凑「该指标结果尚未公开」（无 canvas/svg、不映射 0）；柱图强制含 0 基线、柱端比较值、治疗组橙/对照蓝、组别图例；筛选隐藏未命中整组并清 selection/tooltip；键盘 ArrowUp/Down 按可见行；空结果不再与门户空态重复。
- `portal.js` / `portal.css`（仓库与包内同步）+ `page_shell.py`：筛选浮层挂在 `.kz-filter-host` 按钮下方；chip 写具体中文；`__PORTAL_FILTER__.reapply` 让刷新/前进后退后图表跟上 URL；无匹配时面板改为文档流以免挡住一键清除。
- 夹具改走 `_render_filter_panel` + 包内 `portal.js/css`，删除 `fixture-filter.js`；表增「组别」列。
- `tests/browser/test_chart_table_sync.py`：面板 bounding box、chip 原文、hash 刷新/历史、整组 `display:none`、空态清除、未公开无大空白、负值双柱像素高度、真实 pointer/键盘、可见内部词扫描。
- `assets/portal/manifest.json` 哈希已对齐。截图 18 张、内容互不重复：`.artifacts/task44-chart/current/`。

## 精确测试

| 命令 | 结果 |
|---|---|
| `.venv/bin/python -m pytest tests/browser/test_chart_table_sync.py -q` | **52 passed**（Chromium+WebKit） |
| `.venv/bin/python -m pytest tests/browser/test_filter_state.py tests/browser/test_portal_shell.py -q` | **91 passed** |
| `.venv/bin/python -m pytest tests/unit/reports/test_chart_compatibility.py -q` | **102 passed** |
| `.venv/bin/ruff check`（page_shell / 4.4 测试 / fixture） | All checks passed |
| `.venv/bin/mypy --strict`（5 个源文件） | Success: no issues |
| `.venv/bin/ci-workflow package verify --root .` | `PACKAGE_OK version=0.1.0a0 stage=phase-2-accepted` |

未改 `chart_specs.py`、批准设计书/计划、Trellis、运行记录。

## 残余边界

- 顶部仍保留「已选 N 项」摘要，具体条件在 chip（如「整份报告 · 单位：nmol/L」）。
- 无匹配且面板打开时，面板临时改为文档流，避免挡住 `#kz-filter-empty-reset-page`（Task 4.3 原合同）。
- 第一组 DOM 顺序是对照→治疗，ArrowDown 按可见行顺序而不是 `ALL_ROW_IDS` 声明序。
- 柱图 tooltip 关闭，比较值靠柱端标签；选择态为表行浅橙左边线 + 柱描边，不强闪。
- 静态夹具 `tests/fixtures/task44-chart-table-sync/` 含本地 ECharts 副本，供 `127.0.0.1:8766` 直开；pytest 仍写临时站点。

**NO_COMMIT**
