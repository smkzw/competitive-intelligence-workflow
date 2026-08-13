继续同一 Worker 01 会话，只加强测试合同，不改实现。

## Hard boundaries

- 只在 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow` 工作。
- 只修改 `tests/unit/reports/test_chart_compatibility.py`；不改源代码、浏览器层、设计/计划或生产路径；不提交。
- runner 管理 `runs/execution/ci_phase4_task44_execution/worker_01_followup.md`，不得用工具写它。

Read these files only:
- `AGENTS.md`
- `context/ci_phase4_task44_execution_execution_context.md`
- `tests/unit/reports/test_chart_compatibility.py`
- `src/ci_workflow/reports/common/chart_specs.py`
- `runs/execution/ci_phase4_task44_execution/manager.md`

## Task

1. 新增精确测试：当 `direction` 触发小多图拆分时，标题必须使用中文原生临床语义，冻结为 `越高越有利` / `越低越有利`；标题不得含 `higher_better`、`lower_better`、snake_case 或其他后端枚举。
2. 新增精确测试：任何用户可见小多图标题不得暴露分析人群等内部 snake_case；已知内部枚举必须有中文显示映射，未知含下划线的值失败关闭而不是直出。
3. 保持 `control_role`、`denominator` 为组内展示语境，不触发拆图；治疗组与对照组、不同分母仍同图。
4. 先运行新增节点证明 RED；不要改实现使其 GREEN。最终报告列出节点、RED 原因和测试文件 Ruff 结果。

Runner-managed output path: `runs/execution/ci_phase4_task44_execution/worker_01_followup.md`. Never invoke a write/edit tool on this report path.
