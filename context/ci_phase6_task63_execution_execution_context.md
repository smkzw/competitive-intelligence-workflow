# Execution Context: ci_phase6_task63_execution

Created: 2026-08-29 18:14:00 CST
Objective: 按批准设计完成 Task 6.3 的 B 类安全性事实、披露状态、多维热图与完整 AE 视图合同，并以真实测试证明不误导、不排名、不丢失完整事件集。
Task type: `long_horizon_code`
Risk: `medium`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.
Route schedule: `unscheduled`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `openai-codex/gpt-5.6-luna:max -> openai-codex/gpt-5.6-terra:high -> codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `long_horizon_code_executor` -> `pi` / `openai-codex` / `gpt-5.6-luna`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- `.trellis/tasks/08-29-phase-6-task-63-safety-heatmap/prd.md`
- `.trellis/tasks/08-29-phase-6-task-63-safety-heatmap/design.md`
- `.trellis/tasks/08-29-phase-6-task-63-safety-heatmap/implement.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §§8.4、13.1–13.4
- `/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 6.3（只读）
- `src/ci_workflow/domain/enums.py`
- `src/ci_workflow/domain/facts.py`
- `src/ci_workflow/reports/a/contracts.py`
- `src/ci_workflow/reports/a/analysis.py` 的安全性模型与构建逻辑
- `src/ci_workflow/reports/b/contracts.py`
- `src/ci_workflow/reports/b/efficacy.py`（仅参考 Task 6.2 的失败关闭与来源谱系做法）
- 允许创建/修改的实现文件仅为 `src/ci_workflow/reports/b/safety.py`、`tests/reports/b/test_safety_heatmap.py`、`tests/reports/b/test_ae_state_semantics.py`。
- 允许运行目标测试、`tests/reports/b`、`tests/reports/a`、相关 `tests/unit`，以及 Ruff、strict mypy、`git diff --check`；不得修改测试之外的既有代码以迁就失败。
- Do not add production paths without explicit Codex authorization.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.
- 本任务只做用户导向的功能合同，不扩张为安全性方法学研究、统计综合或安全性排名。
- 所有用户可见标签使用中国临床试验语境的原生中文；测试名和内部类型名可使用必要英文标识。

## Work Items

1. 实现并测试 SafetyFactRow、披露状态数值一致性、来源谱系、阈值/技术异常分离及保守术语映射；仅修改 safety.py 与 test_ae_state_semantics.py。
2. 实现并测试同事件可比语境、多维热图、治疗—对照并列、多试验分列、单元格数值和非数值状态不着色；仅修改 safety.py 与 test_safety_heatmap.py。
3. 实现并测试默认安全维度、约 10–15 行常见 AE 确定性选择、完整事件搜索展开及无安全性排名；仅修改 safety.py 与 test_safety_heatmap.py。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
