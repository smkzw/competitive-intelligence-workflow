You are Pi (Oh My Pi) implementing one bounded code task under Codex final authority.

Hard boundaries:

- Work only in `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- You may edit only `src/ci_workflow/graph/recovery.py`, `tests/graph/test_partial_delivery.py`, `tests/graph/test_partial_delivery_blocked.py`, and only if a public export is genuinely required, `src/ci_workflow/graph/__init__.py`.
- Runner-managed output path: `runs/pi_ci_phase3_task35.md`. Never write it with tools; return the complete report and let the runner persist it.
- Do not commit or stage. Do not modify Task 3.4 source/tests, Trellis, context, reports, schemas, CLI, renderer, portal, fixtures, or real project data.
- Do not perform security, browser, PDF, PPT, visual, clinical, or regulatory testing.

Initial read set:
- `AGENTS.md`
- `context/ci_phase3_task35_context.md`
- `context/ci_phase3_task34_acceptance_2026-08-13.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- `src/ci_workflow/graph/types.py`
- `src/ci_workflow/graph/state.py`
- `src/ci_workflow/graph/transitions.py`
- `src/ci_workflow/graph/guards.py`
- `src/ci_workflow/graph/registry.py`
- `src/ci_workflow/graph/reducer.py`
- `src/ci_workflow/graph/executor.py`
- `tests/graph/test_transition_matrix.py`
- `tests/graph/test_graph_node_contracts.py`
- `tests/graph/test_checkpoint_replay.py`

Objective:

实现批准计划 Task 3.5：用真实规范事件和 GraphExecutor 构建报告/格式独立的渐进交付协调器，机械区分继续运行中的部分交付与剩余对象已穷尽的部分交付阻断，并只允许显式原因重新打开。

Required work items:

1. 先创建两个顶层精确测试：
   - `tests/graph/test_partial_delivery.py::test_reports_and_formats_progress_independently_with_partial_delivery`
   - `tests/graph/test_partial_delivery_blocked.py::test_terminal_partial_delivery_requires_explicit_reopen_before_resume`
   在 `recovery.py` 不存在时分别运行并记录真实 RED。测试的期望数据必须写成独立字面场景，不能从生产聚合器反向生成。
2. 在 `recovery.py` 实现不可变、类型化的选择/目标合同和协调器。它必须从 EventStore 归约出的规范状态计算条件，再通过 `GraphExecutor.submit()` 发出项目/格式迁移；调用者不得传入 `selected_objects_continuable`、`all_selected_*` 等结论布尔值。
3. 场景一必须真实驱动：A 证据已锁定且 HTML delivery_ready；B evidence_blocked；C 仍 collecting/recovering；A 的 PPTX 因 PPT Master 不可用而 format blocked。结果：A HTML 保持交付，PPTX 阻断不撤销 HTML，B 不污染 A/C，项目为 `partially_delivered` 而非 complete/blocked。
4. 场景二必须从上述状态继续：当 C 与所有剩余选定对象均终态阻断且没有运行对象，项目从 `partially_delivered` 到 `partial_delivery_blocked`。如果没有任何已交付产物，相同终态只能到 `blocked`。静默 reconcile 不能离开两个 blocked 终态。
5. 显式 reopen：只有接受的用户材料、环境/生成器修复或新合同版本能使项目回 running；格式 blocked 只能经环境/生成器修复或新合同版本回 queued。旧阻断报告版本保持不可变；需要恢复报告时用新版本/新对象身份，不能把旧 `evidence_blocked` 原地改 queued。
6. 完整选择矩阵必须包含每个选定报告的 mandatory HTML 和每个选定 optional format。改变选择或放弃 PPTX 需要更高的新合同版本；同合同下缺少既有选定目标应失败关闭，不能把失败格式从集合中删除后计算 complete。
7. 协调动作要有稳定 request identity；同动作重放不追加事件，身份相同但选择/原因漂移应失败关闭。不要直接修改 state dict，不要伪造 `graph.transition.accepted`，不要新建第二事件存储。
8. 将 Task 3.4 验收锚点中的相关 P2 一并纳入设计：聚合守卫使用真实规范状态；如本任务实际生产副作用事件，则必要字段在写入前用领域错误验证，否则明确说明未触及该生产边界。不要扩改 executor 以顺手重构。

Verification:

- 两个 exact nodes 各自从 RED 到 GREEN。
- `uv run pytest tests/graph/test_partial_delivery.py tests/graph/test_partial_delivery_blocked.py -q`
- `uv run pytest tests/graph -q`
- `uv run pytest -q`
- `uv run ruff check src tests`
- `uv run mypy src/ci_workflow/graph`
- `uv build --out-dir <system temp dir>` and confirm the wheel contains `ci_workflow/graph/recovery.py`; clean the temp directory.
- `git diff --check` and `git status --short`; do not commit/stage.

When an expected state is surprising, inspect the event stream, current-state derivation, selection matrix and guard evidence; do not weaken assertions merely to make the flow pass.

Return a compact Markdown report with: files changed, RED evidence, behavior implemented, exact/full/static/package results, failed paths and corrections, residual uncertainty, and next recommended action. State clearly that Codex owns acceptance.
