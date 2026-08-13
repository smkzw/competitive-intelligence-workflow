继续同一执行经理会话，复核 W01/W02/W03 的同会话修复，不修改产品文件。

## Hard boundaries

- 只在当前项目工作；只读当前 diff、测试、截图、runner 回执。
- 不做产品代码修改、不提交、不替代 Codex 最终视觉验收。
- runner 管理 `runs/execution/ci_phase4_task44_execution/manager_followup.md`。

Read these files only:
- `AGENTS.md`
- `context/ci_phase4_task44_execution_execution_context.md`
- `runs/execution/ci_phase4_task44_execution/manager.md`
- `runs/execution/ci_phase4_task44_execution/worker_01_followup.md`
- `runs/execution/ci_phase4_task44_execution/worker_02_followup2.md`
- `runs/execution/ci_phase4_task44_execution/worker_03_followup.md`
- `src/ci_workflow/reports/common/chart_specs.py`
- `assets/portal/charts.js`
- `src/ci_workflow/renderers/portal/builder.py`
- `src/ci_workflow/renderers/portal/page_shell.py`
- `tests/unit/reports/test_chart_compatibility.py`
- `tests/browser/test_chart_table_sync.py`
- `tests/fixtures/task44-chart-table-sync/render_fixture.py`
- `tests/fixtures/task44-chart-table-sync/source_rows.py`

## Recheck

1. 复跑并核验 102 项兼容性、42 项双浏览器、Task 4.3 浏览器回归、Ruff、strict mypy、包校验。
2. 机械核对 fixture payload 是否由当前 Python 合同产生且为 4 组；中文标题无内部枚举。
3. 核对正式 builder 真复制/先加载包内 ECharts 后加载 charts.js，并从 builder 生成站点而非仅手写 fixture 实测。
4. 逐项核对九类图形不是默认柱状回退，森林图区间实际绘制；九类在 Chromium/WebKit 均产生真实 SVG/canvas，保留 row ID/缺失状态。
5. 核对 pointer 测试不含失败后 API fallback；截图状态摘要互异；用户可见文案无后台/日志词。
6. 检查新增文件是否进入 package manifest/实际 wheel 资源范围；若 package verify 只看文件存在却 wheel 会漏 1.1MB ECharts，定为阻断并给出精确修复。
7. 返回 PASS/REVISE、P0/P1/P2、证据与必要同会话修复请求。不要因测试退出 0 就放过科学或正式构建链假绿。

Runner-managed output path: `runs/execution/ci_phase4_task44_execution/manager_followup.md`. Never invoke a write/edit tool on this report path.
