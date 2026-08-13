继续同一 Worker 02 会话，把 Worker 01 新增的五个中文标题节点从 RED 修到 GREEN。

## Hard boundaries

- 只在 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow` 工作。
- 只修改 `src/ci_workflow/reports/common/chart_specs.py` 与必要的 `__init__.py`；不得修改测试、浏览器层、Task 4.3、设计/计划或生产路径；不提交。
- runner 管理 `runs/execution/ci_phase4_task44_execution/worker_02_followup2.md`，不得用工具写它。

Read these files only:
- `AGENTS.md`
- `context/ci_phase4_task44_execution_execution_context.md`
- `src/ci_workflow/reports/common/chart_specs.py`
- `tests/unit/reports/test_chart_compatibility.py`
- `runs/execution/ci_phase4_task44_execution/worker_01_followup.md`

## Task

1. 标题显示映射冻结：`higher_better→越高越有利`、`lower_better→越低越有利`；`intention_to_treat→意向治疗人群`、`modified_intention_to_treat→改良意向治疗人群`、`per_protocol→符合方案人群`。保留内部稳定键用于分组，映射只用于用户可见中文标题。
2. 用户可见标题遇到未知 snake_case/含下划线内部值必须失败关闭，不能原样泄露；普通单位（如 `mg/dL`）和自然中文/通用缩写值仍可显示。
3. 保持 `control_role` / `denominator` 为展示语境，不触发拆图。
4. 运行 102 项完整兼容性测试、Task 4.1 回归、Ruff、strict mypy；不进入浏览器层。

Runner-managed output path: `runs/execution/ci_phase4_task44_execution/worker_02_followup2.md`. Never invoke a write/edit tool on this report path.
