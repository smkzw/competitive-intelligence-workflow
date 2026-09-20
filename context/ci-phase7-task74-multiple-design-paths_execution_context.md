# Execution Context: ci-phase7-task74-multiple-design-paths

Created: 2026-08-30 21:11:14 CST
Objective: 实现并验证 C 类事实模式、差异、异常点和至少两条有证据候选设计路径，禁止唯一最佳方案
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

- Approved implementation plan: `/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md`, Task 7.4.
- Trellis requirements: `.trellis/tasks/08-30-phase-7-task-74-multiple-design-paths/{prd.md,design.md,implement.md,checkpoint.md}`.
- Accepted C contracts and views: `src/ci_workflow/reports/c/contracts.py`, `design.py`, `pages.py` and their tests under `tests/reports/c/`.
- Stable identity contract: `src/ci_workflow/domain/ids.py`.
- Current limitation: no complete C report fixture and no product-specific background contract. Tests may use deterministic multi-trial design facts, but must not claim a real product recommendation or end-to-end C report.
- Do not add production paths without explicit Codex authorization.

## Authorized Files By Role

- `worker_01`: create or modify only `tests/reports/c/test_multiple_design_paths.py` and `tests/reports/c/test_no_unique_recommendation.py`; preserve real RED and do not create implementation stubs.
- `worker_02`: begin only after Worker 01's RED exists; create or modify only `src/ci_workflow/reports/c/synthesis.py` and minimal `src/ci_workflow/reports/c/__init__.py` exports. Do not edit tests.
- `worker_03`: independently audit after GREEN; may add adversarial tests only to the two Task 7.4 test files. Do not edit implementation.
- All roles may read listed sources and run focused/shared tests. Runner-owned reports are never written with tools.

## Acceptance Details

- Synthesis accepts an indication identity plus validated `DesignObservation` facts; indication alone, empty facts, unresolved/undisclosed critical facts, or fewer than two distinct evidence-backed design signatures cannot produce candidate paths.
- The result must separate sourced patterns/differences/outliers from model synthesis. Each item and path binds existing observation and trial identities; no invented evidence identifiers.
- At least two candidate paths are required for a successful result. Path identity and content are deterministic under input reordering and carry no rank, score, winner, best, preferred, or unique recommendation semantics.
- Path assumptions and tradeoffs must be derived from disclosed differences among supporting trials. Text must remain natural Chinese and avoid internal codes in user-facing fields.
- No product-specific recommendation may be emitted because this task has no product-background contract.
- No normalized/radar score may be emitted without raw numeric value, unit, formula and a reversible raw row. The minimal implementation may omit normalized views entirely.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 建立至少两条路径、前提、权衡和观察证据绑定的真实 RED
2. 最小实现 synthesis.py 的事实模式与多路径综合并保持输入顺序不变
3. 独立攻击隐性排名、凑数路径、产品特异臆测、无原始值归一化和共享合同回归

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
