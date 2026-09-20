# Conference Context: ci-phase6-task610-visual-review

Created: 2026-08-30 11:08:32 CST
Objective: 以真实中国临床试验医学经理视角对 B 类 PNH 最终候选进行视觉、交互、中文原生性、数值完整性和默认视野独立终验
Task type: `visual_delivery_conference`
Risk: `medium`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`visual_single_object`) with no sub-venue chair. Its effective `CST` route chain is `kimi-code/k3-256k:medium -> openai-codex/gpt-5.6-terra:medium`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-phase6-task610-visual-execution`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `grok-build/grok-4.6`, `openai-codex/gpt-5.6-luna`, `cursor-cli/cursor-grok-4.6`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- Final candidate site: `output/acceptance/task-6.10/b-pnh-current-v8/reports/B/v-fixture-b-pnh-001/html/`.
- Candidate input: `fixtures/positive/b-pnh/inputs/report-data.json`.
- Project visual contract: `contracts/kangzhe/design_specs/project_profile.md`, `contracts/kangzhe/design_specs/core.md`, and `contracts/kangzhe/design_specs/track_interactive.md`.
- Browser acceptance contract: `tests/browser/test_b_portal.py`.
- Execution findings and repair history: `runs/execution/ci-phase6-task610-visual-execution/worker_01.md`, `worker_02.md`, and `worker_03.md`.
- Do not add production paths unless the user explicitly authorized reading them for this task.

## Scope

- In scope: real-browser visual use at 1024, 1280, and 1440 widths; home, efficacy, safety, efficacy-safety matrix, baseline, disposition, product/trial dossiers, filtering, data-basis drawer, back navigation, native Chinese, value consistency, missing-state semantics, typography, spacing, and information density.
- Out of scope: security testing, production writes, new evidence research, PDF/PPT generation, and scientific recomputation.

## Success Criteria

- A lazy, visually sensitive Chinese medical manager can see core charts without horizontal dragging at the default target widths.
- Numeric values agree across chart, table, and data-basis drawer; zero, not reported, not public, and not applicable remain distinct.
- User-visible labels contain no backend keys or untranslated internal states.
- Any P0/P1 finding includes route, viewport, reproduction path, observed evidence, and minimum repair.
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

- 2026-08-30 11:08:32 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
- 2026-08-30 11:50 CST: Codex repaired the first review findings and promoted the immutable review target to `b-pnh-current-v6`; earlier v4 reports remain historical evidence only.
- 2026-08-30 12:22 CST: Codex closed the reproducible v6 follow-up findings and promoted the immutable review target to `b-pnh-current-v7`; v6 remains round-2 evidence only.
- 2026-08-30 12:44 CST: Codex repaired the independent conference P1 findings and promoted the immutable review target to `b-pnh-current-v8`; v7 remains round-3 evidence only.
