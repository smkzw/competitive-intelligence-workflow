# Conference Context: ci-phase10-task104-migration-manifest-review

Created: 2026-09-02 10:14:09 CST
Objective: 独立审查 Task 10.4 最终迁移清单闭环：验证 10 项白名单、11 类排除、敏感哨兵、目标摘要、D01-D70 非运行归档与 Task 10.5/10.8 边界；只读，P0/P1 为零才可建议接受。
Task type: `finite_code_task`
Risk: `medium`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`general_single_object`) with no sub-venue chair. Its effective `CST` route chain is `codebuddy-cli/deepseek-v4-flash:max -> grok-build/grok-4.6:medium -> cursor/cursor-grok-4.6:medium -> openai-codex/gpt-5.6-luna:max`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-phase10-task104-migration-manifest`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `zcode/glm-5.3-flash`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- `migration/legacy_manifest.jsonl` and `migration/legacy_manifest.schema.json`.
- `tests/migration/test_manifest_closure.py`, `tests/migration/test_legacy_manifest_contract.py`, and `tests/migration/test_no_legacy_runtime_dependency.py`.
- `docs/acceptance/migration.md` and `archives/decision-context/ci_workflow_rearchitecture_20260809_context.md`.
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`, `docs/decisions/0002-kangzhe-contract-reconciliation.md`, and the internalized contract/fixture targets named by the manifest.
- Do not add production paths unless the user explicitly authorized reading them for this task.

## Scope

- In scope: read-only verification of the exact 10-item migration whitelist, all 11 required exclusion categories, target/source digest semantics, sensitive redacted sentinels, D01-D70 archival status, and the Task 10.5/10.8 boundary.
- Out of scope: reading sensitive source contents, writing the legacy root, real inventory/cutover/delete operations, release-candidate acceptance, browser/PPT/PDF acceptance, and implementation changes by the participant.

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.

## Parallel Work Rule

For logic-heavy, rigor-sensitive, or artifact-heavy tasks, each participant independently runs the whole bounded workflow and writes a separate output. Leads compare after all available participant outputs are in or explicitly marked pending.

## Timeout Policy

- Participant soft wait: 60 minutes.
- Large-task participant wait: 120 minutes.
- Chair hard wait: 120 minutes.
- Failure rule: Do not fail a model for slow response alone; fail only on terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no useful progress after the high-budget same-session recovery loop. A catalog/auth/transport health preflight timeout or malformed response is diagnostic and must still allow one live route attempt; explicit user routes also proceed when the catalog is stale or incomplete, while a genuinely missing CLI or native transport boundary may block. If a resumable session exists after a step/size boundary, continue it before fallback; repeated identical output/tool evidence triggers the no-progress breaker.
- Pass/turn boundary: one conference prompt is one conference pass. The
  `--max-turns` value controls internal Agent tool-calling turns and is never
  set to 1 for substantive conference execution; generated participant and
  chair commands use the route budgets recorded by the guard.

## Risk Boundaries

- External Agents are advisory; Codex remains final authority.
- Codex owns visual/browser/PPT/PDF/rendered checks, live authority checks, final clinical/regulatory conclusions, and production writes.
- Do not mark a slow model failed solely due to latency.

## Loop Log

- 2026-09-02 10:14:09 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
