# Conference Context: ci-phase10-task105-cutover-tools

Created: 2026-09-02 11:00:06 CST
Objective: 独立验收 Task 10.5 精准切换工具与 required-v12 owner-stage release receipt 闭环：重点挑战真实旧根零触碰、planned CLI 兼容、多根 registry、无敏感内容读取、路径/symlink/inode/授权/恢复/幂等/残留失败关闭、pre-RC 与 release receipt 分层及 pending/not_applicable 语义；只读，P0/P1 为零才可接受。
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

- Linked execution task: `ci-phase10-task105-cutover-tools`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `zcode/glm-5.3-flash`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- Approved Task 10.5 plan and `.trellis/tasks/09-02-phase-10-task-105-cutover-tools/` contract.
- `tools/legacy_cutover.py`, `tests/migration/test_legacy_cutover.py`, and Task 10.4 migration checkpoint/manifest.
- `tools/verify_release_receipts.py`, `schemas/release-case-receipt.schema.json`, `fixtures/acceptance/catalog.yaml`, acceptance catalog schema/digest implementation, and `tests/acceptance/test_required_receipt_closure.py`.
- `package-manifest.json`, `docs/acceptance/legacy-cutover-tooling.md`, and Codex's deterministic verification records.
- Do not add production paths unless the user explicitly authorized reading them for this task.

## Scope

- In scope: read-only whole-contract audit of final Task 10.5 code/tests/docs, counterexamples, CLI compatibility, isolation, authorization/recovery/receipt bindings, and whether any P0/P1 remains.
- Out of scope: reading or inventorying the real legacy root/global Skill, running apply/absence against any non-temporary root, changing source, RC freeze, Task 10.7 authorization, Task 10.8 deletion, and product acceptance.

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

- 2026-09-02 11:00:06 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
- 2026-09-02: Initial pass completed in session `f5d15991-6667-4500-94f9-2f6af6e6f6f1`; P0=0, P1=0, three P2 contract ambiguities returned.
- 2026-09-02: Codex repaired F1-F3 and resumed the same session for a targeted verification pass.
- 2026-09-02: Round 2 returned P0=0, P1=0, P2=0; Codex incorporated all remaining P3 tests/documentation and reran final deterministic checks.
