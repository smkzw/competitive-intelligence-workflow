# Execution Context: ci-r2-multireport-yaozh-20260905

Created: 2026-09-05 13:58:58 CST
Objective: 闭合 v1.3 多报告 A/B/C 联合产品执行与每项目一次 Yaozh 选择持久化，不放宽严格 research submission、科学复核或 HTML-only 边界。
Task type: `long_horizon_code`
Risk: `high`
Execution module trigger: Codex assigned 3 bounded work item(s). Each item must identify its inputs, allowed paths, deliverable and acceptance check.
Route schedule: `off_peak`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `zcode/glm-5.3:max -> cursor/default -> openai-codex/gpt-5.6-luna:max -> openai-codex/gpt-6-astra:medium`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `long_horizon_code_executor` -> `zcode` / `zcode` / `GLM-5.3`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.3.md`
- `plans/codex_execution_ci-rebaseline-rebuild-v3.md`
- `src/ci_workflow/application/run_service.py`
- `src/ci_workflow/application/research_package_submission.py`
- `src/ci_workflow/application/autonomous_research.py`
- `src/ci_workflow/application/intake.py`
- `src/ci_workflow/cli.py`
- `src/ci_workflow/domain/research_package.py`
- `tests/integration/test_research_package_submission.py`
- `tests/integration/test_project_run_cli.py`
- `tests/contract/test_v13_intake_package.py`
- Public/internal Skills are implementation surfaces, not requirement authority.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.
- Work only in the isolated checkout supplied as the runner workdir. Never inspect, resolve,
  inventory, modify or make claims about any legacy workspace. Do not reset, checkout, clean,
  install packages, use credentials or contact external accounts.

## Work Items

1. 实现并测试已提交 A/B/C 多报告载荷逐报告独立执行、状态聚合与幂等 resume；不得建立融合门户。
2. 实现并测试 Yaozh 访问选择的项目级持久化、一次回答、幂等重放和无凭据 CLI 边界。
3. 独立审计多报告与 Yaozh 方案的失败关闭、现有单报告兼容、bundle/Skill 命令和最小负向矩阵，提出最小集成建议。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
