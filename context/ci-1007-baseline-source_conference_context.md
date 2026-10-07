# Conference Context: ci-1007-baseline-source

Created: 2026-10-07 22:26:49 CST
Objective: Challenge fixed four-study baseline population and measurement mapping before real multi-drug descriptive comparison; no efficacy equivalence or product guessing
Task type: `C03`
Risk: `high`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`evidence_single_object`) with no sub-venue chair. Its effective `CST` route chain is `codebuddy/codebuddy-cli/deepseek-v4.1-flash:max -> zcode/zcode/glm-5.3-flash:max -> grok/grok-build/grok-4.7:high -> pi/cursor/grok-4.7-high:high -> pi/openai-codex/gpt-6.1-sol:high`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-1007-baseline-source`
- Execution evidence status: `no linked execution packet`
- Excluded route identities: none
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. The complete agent/provider/model boundary is retained, and effort differences do not bypass deduplication.

## Source Of Truth

- User1007V1: full related-study comparison and linked common dimensions, not
  one graph per strict scientific bucket; preserve scientific unknowns, no
  efficacy/causal/head-to-head/Meta conclusions. A/B/C independent equal priority.
- Fixed original official CT.gov acquisition, read-only:
  .artifacts/1007-pn-current-source-v1/raw-descriptor.json and its raw CAS
  evidence/raw/sha256/82/82b4ed9ab0c63e227a2c4c34b85727dd988e55062850d42b41517f0749168edf.bin.
  SHA82b4ed9ab0c63e227a2c4c34b85727dd988e55062850d42b41517f0749168edf;
  2,978,130 bytes,52 registry records, not universe closure.
  Exactly NCT04202679/NCT04183335/NCT04501666/NCT04501679. Read their
  baselineCharacteristicsModule, protocol eligibility/design/arm/intervention
  and results participant-flow/group data as necessary, not other studies.
- Existing complete affected definitions only: application/source_research_service.py
  ResearchFact/ResearchResultContext/SourceCapture; reports/b/baseline.py
  BaselineObservation and baseline_views.py panel identity; reports/common
  comparison_contract.py if present (discover exact filename first). No code edit.
- Proposed bounded source adapter: existing ResearchFact with additive baseline
  domain/context; preserve each value/spread/denom scalar and its exact path,
  group ID/title/description, original paramType/unit/population/class/category.
  No derived female rate, SD replacement, array-order product assignment or
  default FAS/ITT. Source/QA current/snapshots and historical records read-only.
- Proposed presentation decision to independently challenge: explicit randomized
  baseline population may share a descriptive context while original wording
  and eligibility differences remain visible. Age MEAN+STANDARD_DEVIATION and
  years/Years may share a common age column; total is a study aggregate, not a
  treatment product. This is a candidate hypothesis, not a signed conclusion.

## Scope

- In scope: independent exact source-based challenge of baseline mapping and
  group/product relation; evidence vs inference, recommended positive/negative
  cases and smallest bounded implementation recommendation. One review object.
- Out of scope: no repo/DB/source/CAS/receipt edits, generated sites, tests with
  writes, Git, cleanup, browser, dispatch or service changes; no whole repo
  audit, source refresh, claims of science acceptance or current regulatory
  status. Optional primary official API field docs only if semantics unresolved;
  no credentials, bypass or unrelated network research. Never inspect old root.

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.

## Conference Pass Rule

This packet uses one serial Codex-led conference object. Each declared role receives one complete prompt and may use multiple internal tool turns. Codex decides whether a same-session follow-up is needed after reviewing the result; follow-ups do not create a new conference or change the route identity.

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

- Terminal owner synthesis: initial648.962s incomplete (read capability denied,
  recursive Explore boundary incident), same-session137.889s recovery exit0/
  exact CodeBuddy deepseek-v4.1-flash:max, no fallback. Failed preflight preserved,
  corrected preflight0. Limited source interpretation accepted; no code/browser/
  release acceptance or new human approval workflow. See owner review/metrics.

- 2026-10-07 22:26:49 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
