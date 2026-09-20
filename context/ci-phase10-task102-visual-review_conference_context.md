# Conference Context: ci-phase10-task102-visual-review

Created: 2026-09-01 15:12:23 CST
Objective: 以真实医学经理视角独立审阅 Task 10.2 三个站点式 HTML：信息架构、默认首屏、图先表后、安全性矩阵无需横向拖动、中文原生性、图表/卡片/间距/配色/交互一致性与全路由可读性；只报告缺陷与接受/否决，不修改产物。
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

- User-approved visual authority: `contracts/kangzhe/design_specs/project_profile.md` and `docs/decisions/0012-pre-delivery-visual-finalization-loop.md`.
- Actual immutable HTML sites and browser-verifier evidence under `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-20260901-123524/{a-real,b-real,c-real}/reports/` and `/verification/`; these isolated acceptance roots are explicitly authorized for read-only review.
- Browser reports:
  - `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-20260901-123524/a-real/verification/A/v1/report.json`
  - `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-20260901-123524/b-real/verification/B/v1/report.json`
  - `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-20260901-123524/c-real/verification/C/v1/report.json`
- Representative screenshots must include, at both 1280 and 1920 widths where available: A overview/efficacy/safety/matrix, B overview/efficacy/safety/efficacy-safety-matrix/baseline/disposition, and C overview/design-map/endpoint-timepoint-matrix/trial detail. Reviewers must inspect actual PNGs with a visual/image tool, not infer appearance from filenames or HTML source.

## Scope

- In scope: medical-manager usability, first-screen hierarchy, chart-before-table, safety matrix and heatmap fit without horizontal dragging, native Chinese labels, typography/spacing/color/card/chart/table polish, filters/drilldowns/evidence drawer consistency, and cross-browser visual parity.
- Out of scope: changing source/evidence, scientific conclusions, PDF/PPT, security testing, migration, production writes, or modifying any accepted site.

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- Report every inspected screenshot/path and viewport. Distinguish deterministic browser pass from subjective visual acceptance.
- A pass requires no P0/P1 medical-manager usability defect and no default-view horizontal scrolling of key efficacy, safety, or matrix visualizations.

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

- 2026-09-01 15:12:23 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
