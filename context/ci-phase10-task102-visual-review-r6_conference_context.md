# Conference Context: ci-phase10-task102-visual-review-r6

Created: 2026-09-01 16:34:07 CST
Objective: 以真实中文临床试验医学经理视角，对 Task 10.2 R6 三类站点式 HTML 进行独立视觉与端到端可用性复核，重点确认 B 类完成情况单位拆分、C 类设计图谱可比较性、A/B/C 首屏与矩阵图表可读性，并只报告证据、缺陷和通过或否决建议。
Task type: `visual_delivery_conference`
Risk: `high`
Conference mode: `parallel`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`visual_single_object`) with no sub-venue chair. Its effective `CST` route chain is `grok-build/grok-4.6:medium -> cursor/cursor-grok-4.6:medium -> openai-codex/gpt-5.6-terra:medium`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-phase10-task102-real-source-acceptance`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `openai-codex/gpt-5.6-luna`, `codex/gpt-5.6-luna`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- Project visual authority: `contracts/kangzhe/design_specs/project_profile.md` and `docs/decisions/0012-pre-delivery-visual-finalization-loop.md`.
- R6 immutable site and browser-verifier evidence:
  - `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-20260901-123524-r6/a-real/reports/A/v1/` and `/verification/A/v1/`
  - `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-20260901-123524-r6/b-real/reports/B/v1/` and `/verification/B/v1/`
  - `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-20260901-123524-r6/c-real/reports/C/v1/` and `/verification/C/v1/`
- R9 follow-up candidate and browser-verifier evidence, authorized read-only for the same-session repair review:
  - `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-20260901-123524-r9/a-real/reports/A/v1/` and `/verification/A/v1/`
  - `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-20260901-123524-r9/b-real/reports/B/v1/` and `/verification/B/v1/`
  - `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-20260901-123524-r9/c-real/reports/C/v1/` and `/verification/C/v1/`
- R1-R8 are rejected or superseded historical candidates and must not be substituted for R9.
- R11 follow-up candidate and browser-verifier evidence, authorized read-only for the same-session final repair review:
  - `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-20260901-203000-r11/a-real/reports/A/v1/` and `/verification/A/v1/`
  - `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-20260901-203000-r11/b-real/reports/B/v1/` and `/verification/B/v1/`
  - `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-20260901-203000-r11/c-real/reports/C/v1/` and `/verification/C/v1/`
- R1-R10 are rejected, incomplete, or superseded historical candidates and must not be substituted for R11.
- R12 final candidate and browser-verifier evidence, authorized read-only for the same-session polish confirmation:
  - `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-20260901-211500-r12/a-real/reports/A/v1/` and `/verification/A/v1/`
  - `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-20260901-211500-r12/b-real/reports/B/v1/` and `/verification/B/v1/`
  - `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-20260901-211500-r12/c-real/reports/C/v1/` and `/verification/C/v1/`
- R1-R11 are rejected, incomplete, or superseded historical candidates and must not be substituted for R12.

## Scope

- In scope: actual PNG and live local HTML review, first-screen hierarchy, Chinese-native medical language, chart-before-table, efficacy/safety/matrix readability, B baseline and disposition, C design-map and endpoint-timepoint pages, filtering/drill-down/evidence interactions, default-view horizontal fit, and Chromium/WebKit parity.
- Out of scope: source/evidence mutation, PDF/PPT, security testing, internet research, production writes, and claiming final acceptance.

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

- 2026-09-01 16:34:07 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
- 2026-09-01 20:36 CST: Codex authorized R11 for a same-session follow-up after rebuilding all three reports from the locked evidence inputs and completing dual-browser, four-viewport, all-route verification plus the three real-acceptance binding tests. The follow-up must independently inspect actual R11 screenshots or live local HTML; machine `ok=true` remains supporting evidence only.
- 2026-09-01 21:28 CST: After all three named reviewers recommended R11 release, Codex closed the remaining language and header consistency polish, rebuilt fresh R12 projects, and repeated all-route verification plus real-acceptance binding. R12 is authorized for a final narrow same-session confirmation of only the changed presentation surfaces.
