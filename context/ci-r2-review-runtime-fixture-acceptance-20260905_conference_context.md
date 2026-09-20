# Conference Context: ci-r2-review-runtime-fixture-acceptance-20260905

Created: 2026-09-05 10:17:04 CST
Objective: 独立挑战并验收 R2 两阶段科学复核授权、preview-only 快照、HTML-only 测试分层及真实来源接受边界；输出必须修复、延期和拒绝项，不得宣称 R2 或 RC 完成。
Task type: `high_risk_contradiction_review`
Risk: `high`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`general_single_object`) with no sub-venue chair. Its effective `CST` route chain is `codebuddy-cli/deepseek-v4-flash:max -> grok-build/grok-4.6:medium -> cursor/cursor-grok-4.6:medium -> openai-codex/gpt-5.6-luna:max`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-r2-review-runtime-fixture-rebaseline-20260905`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `zcode/glm-5.3-flash`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- Current user direction and active Goal.
- `docs/specs/competitive-intelligence-workflow-design-v1.3.md`.
- `plans/competitive-intelligence-workflow-roadmap-v1.3.md`.
- `plans/codex_execution_ci-rebaseline-rebuild-v3.md`.
- `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/checkpoint_20260905_r2_review_runtime_fixture_rebaseline.md`.
- `reviews/codex_execution_ci-r2-review-runtime-fixture-rebaseline-20260905_review.md`.
- Actual current source and tests named in the participant prompt. Worker reports are
  secondary evidence only and cannot establish acceptance.
- The installed competitive-intelligence Skill, old ZCode plans, old reports and
  old fixtures are non-authoritative historical evidence.

## Scope

- In scope: read-only challenge of B/C scientific-review promotion, receipt and
  verdict binding, preview snapshot behavior, HTML-only test layering,
  two-run real-source acceptance, negative tests, remaining R2 gaps, and precise
  design/roadmap/plan amendment proposals.
- Out of scope: source edits, runtime upgrades, credential/session access, web
  research, rendered visual acceptance, stale external project mutation,
  R3-R6 implementation, RC/release claims, and any access to the former
  Chinese-named workspace.

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

- 2026-09-05 10:17:04 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
- 2026-09-05: Resume preflight source packet added before first dispatch. The
  user-requested Astra route remains a separate terminally unavailable attempt
  and is not substituted by this conference.
