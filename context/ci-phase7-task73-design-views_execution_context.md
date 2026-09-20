# Execution Context: ci-phase7-task73-design-views

Created: 2026-08-30 20:46:06 CST
Objective: 实现并验证 C 类设计图谱、终点—定义—时间点三元身份和逐试验完整设计档案
Task type: `finite_code_task`
Risk: `medium`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.
Route schedule: `day`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `cursor/default -> google-antigravity/gemini-3.7-flash:high -> mtplx/mtplx-qwen38-27b-optimized-quality:medium -> opencode-go/muse-spark-1.2-contributor:xhigh -> openai-codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `finite_code_executor` -> `pi` / `cursor` / `default`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- Approved implementation plan: `/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md`, Task 7.3.
- Trellis requirements: `.trellis/tasks/08-30-phase-7-task-73-design-views/{prd.md,design.md,implement.md,checkpoint.md}`.
- Accepted C contracts: `src/ci_workflow/reports/c/contracts.py`, `src/ci_workflow/reports/c/design.py`, `schemas/reports/c-design-observation.schema.json`.
- Existing C tests: `tests/reports/c/test_design_gate.py`, `tests/reports/c/test_precise_eligibility_drilldown.py`.
- C page responsibility catalog: `src/ci_workflow/reports/common/page-catalogs/C.yaml`.
- Stable identity and locator contracts: `src/ci_workflow/domain/ids.py`, `src/ci_workflow/domain/evidence.py`.
- Current limitation: there is no complete C report fixture. Tests may build deterministic registry-observation corpora for this data-projection layer, but must not claim an end-to-end C report or invent real competitive conclusions.
- Do not add production paths without explicit Codex authorization.

## Authorized Files By Role

- `worker_01`: create or modify only `tests/reports/c/test_endpoint_definition_timepoint.py`; preserve a real RED and do not create implementation stubs.
- `worker_02`: begin only after Worker 01's RED exists; create or modify only `src/ci_workflow/reports/c/pages.py` and the minimal `src/ci_workflow/reports/c/__init__.py` exports needed by that RED. Do not edit tests.
- `worker_03`: independently audit after GREEN; create or modify only `tests/reports/c/test_trial_dossier.py` and, if a deterministic endpoint defect is found, add adversarial tests to `tests/reports/c/test_endpoint_definition_timepoint.py`. Do not edit implementation.
- All roles may read the listed sources and run focused/shared tests. Runner-owned reports are never written with tools.

## Acceptance Details

- Endpoint comparison identity is a triple: endpoint display name, full source definition, and assessment timepoint. All three must be present and traceable; same-name rows with differing definition or timepoint stay separate.
- Endpoint and timepoint observations may pair only through an explicit stable pairing key represented in existing contract fields; positional order, loose text similarity, and cross-trial/group fallback are prohibited.
- Trial dossier observation identities must equal every validated input observation for that trial, with no allowlist truncation. A sibling trial must not leak into the dossier.
- Every projected record retains observation identity, source text, source version, full locator, disclosure state, review state, and conflict disposition.
- Design map and topical views must be deterministic under input reordering and must not invent missing statistics or normalize away disclosed differences.
- Task 7.2 eligibility rows are reused for inclusion/exclusion; do not copy their projection logic.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 建立终点三元身份、同名不合并和跨试验不误配的真实 RED
2. 基于现有 C 观察与入排投影最小实现 pages.py 的设计视图和逐试验档案
3. 独立审计全字段档案、来源保真、输入顺序不变性和共享合同回归

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
