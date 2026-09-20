# Execution Context: ci-r2-yaozh-routing-20260905

Created: 2026-09-05 16:18:57 CST
Objective: 将项目级药智三态回答接入来源政策、自动研究工作项和宿主能力预检，保持辅助路线非阻断、会话失效可恢复且无凭据进入 artifact
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

- User-approved Goal and current v1.3 product contract:
  - `docs/specs/competitive-intelligence-workflow-design-v1.3.md`
  - `plans/competitive-intelligence-workflow-roadmap-v1.3.md`
  - `plans/codex_execution_ci-rebaseline-rebuild-v3.md`
  - `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/prd.md`
  - `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/design.md`
  - `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/implement.md`
- Current implementation and tests:
  - `src/ci_workflow/application/intake.py`
  - `src/ci_workflow/application/yaozh_access.py`
  - `src/ci_workflow/application/autonomous_research.py`
  - `src/ci_workflow/application/capability_preflight.py`
  - `src/ci_workflow/application/run_service.py`
  - `src/ci_workflow/sources/policy.py`
  - `src/ci_workflow/sources/planner.py`
  - `policies/sources/source-policy-v1.yaml`
  - `tests/integration/test_yaozh_access_cli.py`
  - `tests/integration/test_autonomous_research_work_item.py`
  - `tests/integration/test_capability_preflight.py`
  - `tests/contract/test_v13_intake_package.py`
- Existing Skill text is implementation under review, not design authority.
- Do not add production paths without explicit Codex authorization.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.
- This pass is read-only analysis. Workers may not edit product, tests, policy, docs, plans, task records, or prompts. Runner owns only each declared worker report.
- Do not accept, request, print, store, or simulate credentials, cookies, tokens, authorization headers, browser storage, or account identifiers.
- Yaozh is optional lead/cross-check support. Its absence or expired session cannot block public-source core research and cannot be treated as scientific no-data.

## Done Evidence

- Each worker supplies file/symbol-grounded findings for its assigned item.
- W01 closes the authority matrix and three-state task semantics without promoting Yaozh to direct evidence.
- W02 identifies the exact dependency split needed so optional login-browser failure does not block research or HTML delivery.
- W03 supplies positive, negative, recovery, idempotency, secret-boundary and documentation acceptance cases.

## Work Items

1. W01: 核查药智来源权威矩阵与自动研究任务三态合同，给出最小实现或补丁
2. W02: 核查能力预检与 run service 的可选登录浏览器依赖，防止核心研究被错误阻断
3. W03: 设计并验证负向测试、凭据边界、幂等与正式文档更新

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
