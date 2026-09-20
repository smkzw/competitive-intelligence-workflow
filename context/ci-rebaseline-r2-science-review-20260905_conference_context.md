# Conference Context: ci-rebaseline-r2-science-review-20260905

Created: 2026-09-05 00:39:19 CST
Objective: 独立审查 v1.3 R2 G01-G09 实现的科学、状态机与合同正确性，重点验证入口消歧、竞品宇宙闭包、按条件触发的两轮恢复、细粒度路由失败、publication/manual-supply 单次中断、原地重命名与 B 类医学语义归并；逐项给出 PASS/VETO 和可复现证据，不做实现修改。
Task type: `competitive_intelligence`
Risk: `high`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`general_single_object`) with no sub-venue chair. Its effective `CST` route chain is `zcode/glm-5.3-flash:max -> codebuddy-cli/deepseek-v4-flash:max -> grok-build/grok-4.6:medium -> cursor/cursor-grok-4.6:medium`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-rebaseline-rebuild-20260904`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `openai-codex/gpt-5.6-luna`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.3.md` is the approved product and scientific contract.
- `plans/competitive-intelligence-workflow-roadmap-v1.3.md` and `plans/codex_execution_ci-rebaseline-rebuild-v3.md` define the accepted sequencing and G01-G09 acceptance intent.
- `src/ci_workflow/`, `tests/`, and `schemas/` are the current implementation and executable contract surfaces.
- `runs/execution/ci-rebaseline-rebuild-20260904/worker_03.md` is worker evidence only, not acceptance authority.
- The current repository state and reproducible focused tests outrank narrative worker claims.
- The former workspace at `/Users/smkzw/Documents/AI Products/竞品调研工作流` is prohibited: do not read, resolve, inventory, existence-check, modify, or mention it in commands.

## Scope

- In scope: read-only review of G01-G09 and adjacent contracts; indication disambiguation; typed graph branch/join correctness; route-state and conditional recovery semantics; empty-universe/evidence-insufficiency representation; publication/manual-supply interruption and one-confirmation behavior; in-place rename/no-copy/no-archive guarantees; B-report semantic grouping and deterministic conflict guards; focused test adequacy.
- Out of scope: implementation edits; R3 visual acceptance; R4 host distribution; R5 real 24-portal matrix; release or RC claims; internet research; any access to the prohibited former workspace.

## Success Criteria

- Give an explicit PASS or VETO for each G01-G09 area, with file/line or reproducible-test evidence.
- Separate contract defects from missing tests and non-blocking future enhancements.
- For every VETO, propose the smallest typed state/contract correction and at least one decisive negative test.
- Resolve or explicitly frame the semantics of `access_blocked`, condition-triggered two-round recovery, genuinely empty universes, and manual file acceptance identity binding.
- Verify that a single requested report branch can reach scientific QC without requiring unselected A/B/C analysis views.
- Verify that B-report grouping permits clinically close windows only through model-assisted adjudication while deterministic guards block incompatible scale, direction, estimand, denominator, and analysis set.
- No files are modified; Codex retains final acceptance.

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

- 2026-09-05 00:39:19 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
