# Execution Context: ci-phase9-task92-incremental-refresh

Created: 2026-09-01 01:07:08 CST
Objective: 实现 Task 9.2 增量刷新与影响传播：扩大截止日只晋级新适格候选，GateSpec 收紧只重算受影响对象，父合同和历史快照不可变，首版只处理站点式 HTML。
Task type: `finite_code_task`
Risk: `medium`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.
Route schedule: `night`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `zcode/glm-5.3-flash:max -> codebuddy-cli/deepseek-v4-flash:max -> mtplx/mtplx-qwen38-27b-optimized-quality:medium -> openai-codex/gpt-5.6-luna:xhigh`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `finite_code_executor` -> `zcode` / `zcode` / `GLM-5.3-Flash`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- `.trellis/tasks/09-01-phase-9-task-92-incremental-refresh/{prd.md,design.md,implement.md}`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §17.2
- `docs/decisions/0013-site-first-v1-delivery-scope.md`
- `/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 9.2（只读批准计划）
- `src/ci_workflow/domain/{contracts.py,evidence.py,ids.py}`
- `src/ci_workflow/gates/{coverage.py,models.py,evaluator.py}`
- `src/ci_workflow/storage/{snapshot_store.py,event_store.py,sqlite.py,migrations.py}`
- `src/ci_workflow/application/{project_service.py,correction_service.py,source_research_service.py}`
- `tests/integration/test_historical_cutoff.py`
- `tests/reports/test_gate_override_strictness.py`

允许写入仅限三个工作项声明的新文件；若确需修改共享既有文件，必须在报告中说明
原因并保持最小差异。不得读取或修改生产环境。

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 实现 graph/impact.py 和 graph/definitions/refresh.py：稳定影响闭包、复用集合、重大合同变化再基线分支；不得复制既有 GateSpec 规则。
2. 实现 application/refresh_service.py：父版本绑定、截止日扩展、候选晋级、GateSpec 收紧、局部重建回执、不可变历史和幂等恢复。
3. 新增 tests/integration/test_incremental_refresh.py 并补必要的契约/回归断言：两个批准节点、父版本不变、错误截止日、重大合同变化、影响范围和中断恢复。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
