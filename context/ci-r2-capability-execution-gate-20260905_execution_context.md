# Execution Context: ci-r2-capability-execution-gate-20260905

Created: 2026-09-05 16:46:26 CST
Objective: 独立审查并验证核心 capability matrix 的持久化、不可复用预检与按研究/HTML 交付选择性阻断合同，给 Codex 提供可执行缺口和验收结论
Task type: `long_horizon_code`
Risk: `high`
Execution module trigger: Codex assigned 3 bounded work item(s). Each item must identify its inputs, allowed paths, deliverable and acceptance check.
Route schedule: `peak`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `cursor/default -> openai-codex/gpt-5.6-luna:max -> openai-codex/gpt-6-astra:low`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `long_horizon_code_executor` -> `pi` / `cursor` / `default`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- Active task: `.trellis/tasks/09-05-r2-capability-execution-gate` (`prd.md`,
  `design.md`, `implement.md`).
- Approved product contract: `docs/specs/competitive-intelligence-workflow-design-v1.3.md`.
- Current implementation truth: `src/ci_workflow/application/capability_preflight.py`,
  `src/ci_workflow/application/run_service.py`, `src/ci_workflow/cli.py`,
  `src/ci_workflow/hosts/base.py`.
- Current contract/tests: `schemas/capability-matrix.schema.json`,
  `tests/contract/test_capability_matrix.py`,
  `tests/integration/test_capability_preflight.py`,
  `tests/integration/test_selective_capability_blocking.py`,
  `tests/integration/test_project_run_cli.py`, and relevant host tests.
- Previous verified boundary: `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/checkpoint_20260905_r2_yaozh_optional_routing.md`.
- Existing competitive-intelligence Skill and historical ZCode material are non-authoritative audit input.
- Workers are read-only: no product-code, test, task, plan, prompt, review, or metrics writes.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 追踪 run_service 全路径并审查研究与交付阻断插入点，禁止写产品代码
2. 审查 capability matrix 原子持久化、软链接与重放安全边界，禁止写产品代码
3. 设计最小负向与恢复测试矩阵，核查 CLI/宿主语义一致性，禁止写产品代码

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
