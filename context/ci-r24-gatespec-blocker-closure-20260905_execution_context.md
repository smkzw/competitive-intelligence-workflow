# Execution Context: ci-r24-gatespec-blocker-closure-20260905

Created: 2026-09-05 18:50:20 CST
Objective: 独立审计 R2.4 逐对象 GateSpec、信息增益恢复、blocker audit 与 no-draft 产品链，为 Codex 提供最小修复和负向验收依据
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

- `docs/specs/competitive-intelligence-workflow-design-v1.3.md` 第 5.4、5.5、6 节。
- `plans/codex_execution_ci-rebaseline-rebuild-v3.md` R2.4。
- `.trellis/tasks/09-05-r24-gatespec-blocker-closure/{prd,design,implement}.md`。
- `src/ci_workflow/gates/{models,evaluator,exhaustion,blocker_audit}.py`、
  `src/ci_workflow/sources/retries.py`、`src/ci_workflow/capabilities/scientific_qc.py`、
  `src/ci_workflow/application/{run_service,terminal_recovery}.py`。
- `policies/gates/{A,B,C}-v1.yaml`、`schemas/{gate-spec,blocker-audit}.schema.json` 及对应
  unit/contract/integration/graph 测试。
- 当前文件是待核验实现；R2.2、R2.3 已归档 checkpoint 只作为稳定上游合同，不重复建设。
- 不添加生产路径、外部账号、旧工程或凭据来源。

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 只读审计 GateSpec models/evaluator 与 A/B/C YAML：逐对象适用矩阵、来源角色、成熟度、新鲜度、缺失/零值/冲突和候选不可删减绕过点
2. 只读审计 exhaustion/route recovery/scientific QC：两轮不同策略、真实执行回执、信息增益历史和独立遗漏复核绑定缺口
3. 只读审计 blocker_audit/run_service/no-draft 产品链：机器审计完整性、用户简页、原子幂等、历史恢复及下游残留负向矩阵

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
