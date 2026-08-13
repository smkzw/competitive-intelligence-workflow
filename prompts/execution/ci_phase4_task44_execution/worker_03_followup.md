继续同一 Worker 03 会话。执行经理已否决当前浏览器层，请在原授权范围内修复，不要只解释。

## Hard boundaries

- 只在 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow` 工作。
- 仅修改 Task 4.4 浏览器资产/最小门户接线、`tests/browser/test_chart_table_sync.py`、`tests/fixtures/task44-chart-table-sync/`、必要的资源 manifest/包内副本与 `.artifacts/task44-chart/current/`。
- 不修改 Python 科学兼容性合同、Task 4.3 语义、设计/计划、生产路径；不提交。
- runner 管理 `runs/execution/ci_phase4_task44_execution/worker_03_followup.md`，不得用工具写它。

Read these files only:
- `AGENTS.md`
- `context/ci_phase4_task44_execution_execution_context.md`
- `src/ci_workflow/reports/common/chart_specs.py`
- `assets/portal/charts.js`
- `src/ci_workflow/renderers/portal/builder.py`
- `src/ci_workflow/renderers/portal/page_shell.py`
- `tests/browser/test_chart_table_sync.py`
- `tests/fixtures/task44-chart-table-sync/index.html`
- `runs/execution/ci_phase4_task44_execution/manager.md`
- `runs/execution/ci_phase4_task44_execution/worker_02_followup2.md`

## Required repairs

1. Fixture 不能再手写与 Python 不同的组。建立一个测试内/fixture 构建器，从当前 `split_compatible_groups` + `resolve_chart_type` 的实际输出生成 HTML payload，或以精确合同测试证明静态 payload 与实时 Python 输出逐字段相等。当前方向不同的未公开行必须按 Python 结果形成第 4 组；小多图标题只显示中文 `越高越有利/越低越有利`，不含内部枚举。
2. 正式 `build_portal` 必须在有图表模块时（本任务可先始终复制/加载）把已固定的 `assets/third-party/echarts/echarts.min.js` 复制到生成站点的本地相对路径，并在 `charts.js` 之前加载。添加真实 builder 生成站点测试，不允许仅 fixture 手写 script；从生成页面在 Chromium/WebKit 实际确认 ECharts 6.1.0 渲染且无远程请求。包内解析路径必须明确；若当前 wheel 尚不携带 1.1MB ECharts，失败关闭并把包入包安排写成可测试资源合同，不能静默依赖仓库绝对路径。
3. `charts.js` 为九类注册图形分别实现真实 option 构建：bar、line、forest（置信区间必须实际绘制，不能只有点）、heatmap、bubble、scatter_interval、timeline、radar、status_matrix。不得把七类默认回退成柱状图。新增九类逐一用真实 `window.echarts.init/setOption` 渲染的 Chromium/WebKit smoke；每类 option 保留全部 row ID、缺失行 null/status、不转 0。
4. 图表点击测试禁止“真实几何没点中就调用 API”仍算同一通过。真实 pointer click 必须单独通过 Chromium/WebKit；程序化 `selectByRowId` 可另测但不能掩盖 pointer failure。
5. overflow 只保留真实、非重复证据：不要为同一状态保存两个不同文件名。截图至少覆盖 1280/1024 的初始、组合小多图/未公开状态、真实点选高亮；每个状态文件内容应不同，并继续做 DOM 溢出断言。
6. 页面可见内容不得出现 `row_id/renderable/_chart_type/snapshot/gate/signal/test/log/fixture`、英文图类型或内部方向键。Task 4.5 抽屉不进入本轮。
7. 重新同步 repo/package `charts.js` 与 manifest 摘要；运行双引擎新浏览器套件、Task 4.3 浏览器回归、102 项兼容性测试、Ruff、strict mypy、包校验。不要提交。

Runner-managed output path: `runs/execution/ci_phase4_task44_execution/worker_03_followup.md`. Never invoke a write/edit tool on this report path.
