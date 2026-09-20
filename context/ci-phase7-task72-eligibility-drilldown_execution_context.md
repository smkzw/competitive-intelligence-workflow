# Execution Context: ci-phase7-task72-eligibility-drilldown

Created: 2026-08-30 20:23:13 CST
Objective: 实现并验证 C 类入排标准精确结构化和完整下钻链，覆盖全部适用观察并拒绝量表与定位信息伪造
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

- Approved implementation plan: `/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md`, Task 7.2.
- Trellis requirements: `.trellis/tasks/08-30-phase-7-task-72-eligibility-drilldown/{prd.md,design.md,implement.md,checkpoint.md}`.
- Accepted Task 7.1 contract: `src/ci_workflow/reports/c/contracts.py`, `schemas/reports/c-design-observation.schema.json`, `tests/reports/c/test_design_gate.py`.
- Precise locator contract: `src/ci_workflow/domain/evidence.py`, `tests/integration/test_fragment_locators.py`.
- Real recorded registry fragment precedent: `fixtures/recorded/phase-2-lineage/nct02912468-minimal.json`, `tests/integration/sources/test_ctgov.py`.
- C page responsibility catalog: `src/ci_workflow/reports/common/page-catalogs/C.yaml`.
- Current limitation: there is no complete C report fixture in this repository. Do not invent an end-to-end report or claim real-report completeness; Task 7.2 may create deterministic registration-observation test cases only for its bottom-layer contract.
- Do not add production paths without explicit Codex authorization.

## Authorized Files By Role

- `worker_01`: create or modify only `tests/reports/c/test_precise_eligibility_drilldown.py`; preserve a real RED and do not create implementation stubs.
- `worker_02`: begin only after Worker 01's RED exists; create or modify only `src/ci_workflow/reports/c/design.py` and the minimal `src/ci_workflow/reports/c/__init__.py` exports required by that RED. Do not edit tests.
- `worker_03`: independently audit after GREEN; may add adversarial tests only to `tests/reports/c/test_precise_eligibility_drilldown.py`; do not edit implementation.
- All roles may read the listed sources and run focused/shared tests. Runner-owned reports are never written with tools.

## Acceptance Details

- The parameterized applicable cases must be derived from the full deterministic observation corpus in the test file, with an explicit assertion that collected case identities equal the applicable observation identities; a hand-selected subset is not acceptable.
- Every applicable row must preserve one complete stable chain: indication, product, trial, cohort/group, design element, original field, scale/score applicability, screening or assessment time, operator/threshold/value/unit applicability, source version, and full `EvidenceLocator`.
- Original source text must be preserved byte-for-byte; a summary may be separate but never replace or truncate the original.
- A criterion with no named scale must use explicit not-applicable semantics and an applicability predicate; an empty string or fabricated scale is a failure.
- Different trials, groups, and fields must not collide on stable identity.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 建立覆盖全部适用 C 设计观察的参数化 RED，并保存精确失败数
2. 在真实 RED 基础上最小实现 reports/c/design.py 的稳定下钻链和不适用量表语义
3. 独立审计逐观察覆盖、原文与 locator 保真、跨试验隔离和共享合同回归

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
