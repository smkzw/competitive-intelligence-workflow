# Conference Context: ci_phase3_task36_acceptance

Created: 2026-08-13 07:10:01
Objective: 独立验收 Task 3.6 项目/fixture CLI、恢复语义、当前运行清单与无草稿真实案例，识别任何用户功能性 false-green
Task type: `complex_delivery_conference`
Risk: `high`
Conference mode: `parallel`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

    - Visual/design/HTML/PPT tasks use a Codex-led panel with no sub-venue chair: Pi/Oh My Pi `kimi-code/k3-256k` (high). If unavailable, the runner tries Grok Build `grok-4.6` (high), then the distinct Cursor `cursor-grok-4.6-high` route, then the distinct Pi/OpenCode Go `gpt-5.6-luna` (max) route. The Codex subAgent Luna route remains a separate native/CLI compatibility path.
- Chinese labels or Chinese sentence review is handled directly by Codex and does not start a conference.
    - Other complex tasks use a Codex-chaired panel with no sub-venue chair. Participant 1 is Pi/Alibaba `qwen3.8-max` (xhigh) during the Beijing 22:00-07:00 window. Outside that window its exact Qwen Max node is replaced by Pi/OpenCode Go `deepseek-v4-flash` (max); during the night window, every exact Pi/cms-smk `deepseek-v4-flash` node is replaced by the same Pi/OpenCode Go route. Its remaining fallbacks are Pi/cms-smk `deepseek-v4-flash` (max) and Pi/OpenCode Go `deepseek-v4-flash` (max), with effective-route deduplication. Participant 2 is Grok Build `grok-4.6` (high), with the distinct Cursor `cursor-grok-4.6-high` and Pi/cms-router `minimax-m3` as fallbacks. Codex remains the final authority. The explicit Luna native/CLI compatibility route remains available for execution roles that declare Codex subAgent.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Source Of Truth

- `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 3.6 exact nodes EX01–EX02/FX01–FX06 and command/exit semantics.
- `context/ci_phase3_task36_context.md` task contract and failure history.
- Current dirty Task 3.6 implementation/tests/fixture/schema/package diff; implementation worker reports are excluded from participant read sets.
- Deterministic anchors available for rerun: the four exact integration files, relevant regressions, full pytest suite, Ruff, strict mypy, package verify, wheel inspection and a fresh real fixture CLI run.
- Do not add production paths unless the user explicitly authorized reading them for this task.

## Scope

- In scope: read-only independent audit of production semantics, test strength, installed/package behavior, resume correctness, output provenance, manifest/event/checkpoint binding, native Chinese user guidance and no-draft behavior.
- In scope: create disposable temporary projects and run non-destructive tests/CLI commands inside the workspace or system temporary directory.
- Out of scope: source edits, Task 3.7 scientific QC, A/B/C report data/renderers, browser/PDF/PPT/visual review, network research, clinical-content conclusions and system-security testing.

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- A PASS requires P0=0 and P1=0. Every defect must identify file/behavior, reproducible evidence, severity and minimal functional remedy; do not grade from worker claims.

## Parallel Work Rule

For logic-heavy, rigor-sensitive, or artifact-heavy tasks, each participant independently runs the whole bounded workflow and writes a separate output. Leads compare after all available participant outputs are in or explicitly marked pending.

## Timeout Policy

- Participant soft wait: 60 minutes.
- Large-task participant wait: 120 minutes.
- Chair hard wait: 120 minutes.
- Failure rule: Do not fail a model for slow response alone; fail only on terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no useful progress after the high-budget same-session recovery loop. A catalog/auth/transport health preflight timeout or malformed response is diagnostic and must still allow one live route attempt; only a missing CLI or an explicitly invalid, retired, or unlisted model may block before live dispatch. If a resumable session exists after a step/size boundary, continue it before fallback; repeated identical output/tool evidence triggers the no-progress breaker.
- Pass/turn boundary: one conference prompt is one conference pass. The
  `--max-turns` value controls internal Agent tool-calling turns and is never
  set to 1 for substantive conference execution; generated participant and
  chair commands use the route budgets recorded by the guard.

## Risk Boundaries

- External Agents are advisory; Codex remains final authority.
- Codex owns visual/browser/PPT/PDF/rendered checks, live authority checks, final clinical/regulatory conclusions, and production writes.
- Do not mark a slow model failed solely due to latency.

## Loop Log

- 2026-08-13 07:10:01: Conference initialized by `hermes_workflow_guard.py init-conference`.
