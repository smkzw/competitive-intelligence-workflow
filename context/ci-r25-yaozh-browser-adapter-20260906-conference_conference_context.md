# Conference Context: ci-r25-yaozh-browser-adapter-20260906-conference

Created: 2026-09-05 21:24:07 CST
Objective: Independently review the current R2.5 Yaozh optional-browser adapter implementation and Codex disposition for false readiness, secret leakage, source-authority escalation, scientific gate regressions, scope integrity, and pause readiness. Do not modify files or inspect real browser sessions.
Task type: `competitive_intelligence`
Risk: `high`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`general_single_object`) with no sub-venue chair. Its effective `CST` route chain is `opencode-go/muse-spark-1.3-contributor:xhigh -> codebuddy-cli/deepseek-v4-flash:max -> openai-codex/gpt-5.6-sol:medium`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-r25-yaozh-browser-adapter-20260906`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `zcode/glm-5.3-flash`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- `.trellis/tasks/09-06-r25-yaozh-browser-adapter/{prd,design,implement}.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.3.md`
- `src/ci_workflow/application/{yaozh_access,capability_preflight,research_package_submission}.py`
- `src/ci_workflow/domain/research_package.py`
- `src/ci_workflow/gates/evaluator.py`
- `policies/gates/B-v1.yaml` and `policies/sources/source-policy-v1.yaml`
- the touched schemas, package manifest, Skills and focused tests
- `reviews/codex_execution_ci-r25-yaozh-browser-adapter-20260906_review.md`
- worker outputs are not in the participant's initial read set and must not substitute for an
  independent pass.
- Do not add production paths unless the user explicitly authorized reading them for this task.

## Scope

- In scope: read-only review of current R2.5 code, tests and dispositions; exact P0/P1 defects;
  smallest remediation and truthful pause status.
- Out of scope: file edits, real browser/session access, credentials, legacy workspace, broad web
  research, RC/release acceptance, and redesign of all A/B/C payload contracts.

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

- 2026-09-05 21:24:07 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
