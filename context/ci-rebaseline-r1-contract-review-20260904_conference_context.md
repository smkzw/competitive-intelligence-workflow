# Conference Context: ci-rebaseline-r1-contract-review-20260904

Created: 2026-09-04 15:04:29 CST
Objective: 独立审查当前 v1.3 正式设计、路线图、执行计划 v3、ZCode 处置和 Task 10.6 三文档是否完整、互相一致并忠实实现 2026-09-04 已锁定产品裁决；只返回证据化 PASS/VETO 与具体缺口，不修改文件，不重新裁决用户已定事项。
Task type: `high_risk_contradiction_review`
Risk: `high`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`general_single_object`) with no sub-venue chair. Its effective `CST` route chain is `cursor/default -> opencode-go/muse-spark-1.3-contributor:xhigh -> cms-router/minimax-m3:xhigh -> google-antigravity/gemini-3.8-flash-high:high`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-rebaseline-rebuild-20260904`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `openai-codex/gpt-5.6-luna`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- Current user-approved rebaseline decisions as recorded below.
- `docs/specs/competitive-intelligence-workflow-design-v1.3.md`
- `plans/competitive-intelligence-workflow-roadmap-v1.3.md`
- `plans/codex_execution_ci-rebaseline-rebuild-v3.md`
- `reviews/zcode_disposition_ci-rebaseline-rebuild_20260904.md`
- `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/prd.md`
- `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/design.md`
- `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/implement.md`
- Historical comparison only: `docs/specs/competitive-intelligence-workflow-design-v1.2.md`, `reviews/zcode_ci_engineering_audit_20260902.md`, `plans/zcode_revised_roadmap_20260902.md`, `plans/zcode_execution_plan_v2_20260902.md`, and `docs/specs/competitive-intelligence-workflow-design-v1.3-draft.md`.
- The historical `competitive-intelligence-workflow` Skill and all ZCode outputs are non-authoritative inputs; do not infer a requirement merely because they contain it.

## Scope

- In scope: read-only contradiction, omission, provenance, testability and cross-document consistency review of the seven current R1 artifacts.
- Out of scope: editing any file; runtime implementation; browser/visual acceptance; re-deciding settled product choices; reading, inventorying, validating, chmod-ing, modifying, deleting or absence-checking `/Users/smkzw/Documents/AI Products/竞品调研工作流`.

## Locked Decisions To Test

- One public entry, with one-sentence autonomous research by default and an optional typed research-package; internal Skills remain typed and independently testable.
- If report type is unspecified, native Ask explains A/B/C; cutoff date is optional; each new project asks once about Yaozh access.
- A/B/C are three independent high-density multipage portals with distinct information and visual grammar; v1 delivers HTML only.
- No CSV/XLSX export, radar, evidence-maturity view, scheduled monitoring, default ranking/composite score, Meta/NMA or mandatory LangGraph.
- A user manually triggers refresh; after trigger, source recheck, diff, immutable snapshot and affected HTML rebuild are automatic.
- Every first report closes the complete competitor universe through global/China routes and alias/target/company/trial reverse expansion, followed by clean-context independent review.
- Critical missing or abnormal zero runs two different recovery strategies. If the core remains answerable, deliver with limits; otherwise show only a concise evidence-insufficiency page while retaining the internal blocker audit.
- Required publications are primary results, extension primary results and key safety/long-term exposure papers. Reviews, routine ad hoc and irrelevant exploratory analyses are excluded by default. Rules + model + independent review classify blocking edges.
- Inaccessible required publications create one Markdown request. A validated user file is renamed in place in the inbox after pre-recording original name, SHA-256, DOI/registry ID and new name; collision fails closed and bytes do not change. One user response per snapshot.
- B uses full clinical-semantic grouping with deterministic incompatibility guards, plus three prescribed bubble families: efficacy versus overall safety, efficacy versus serious risk, and durability versus discontinuation risk with the approved size semantics. Normal output is factual and neutral, not a recommendation.
- Structured data uses a suitable chart plus an inline, default-collapsed complete table. Each page ends with one consolidated external-source section. User tables expose no internal locators. Empty data never produces empty axes or fixed zero walls.
- Every physical page is tested at desktop, tablet, phone and narrow-screen viewports in Chromium and WebKit.
- One HTML-only universal core package plus lightweight Codex/Hermes/OMP adapters; one public installed entry; no credentials, cache, raw run evidence or PDF/PPT runtime/dependencies in the bundle.
- Real acceptance is eight indications times A/B/C = 24 portals, executed/reviewed by independent agents with Codex final acceptance. Release states are only DEVELOPMENT_CANDIDATE, RC_FROZEN and RELEASED.
- Legacy-root retirement is separate: only after at least three real projects covering A/B/C, refresh/history/recovery/three-host success, zero severe defects and verified rollback, then the user must explicitly approve before any access or deletion.

## Success Criteria

- Return PASS only if every locked decision is faithfully represented, cross-document status/signal semantics agree, and planned tests can prove the claims. Otherwise return VETO with file/line evidence and a concrete minimal correction.
- Distinguish historical terminology from current authority, especially ZCode `D71-D78`, `formats=4`, monitoring, and `FINAL_ACCEPTANCE_OK`/legacy-absence claims.
- Inspect all seven current artifacts and only the historical files needed for a cited comparison.
- No file is modified and the forbidden legacy root is not accessed; Codex retains final acceptance.

## Parallel Work Rule

For logic-heavy, rigor-sensitive, or artifact-heavy tasks, each participant independently runs the whole bounded workflow and writes a separate output. Leads compare after all available participant outputs are in or explicitly marked pending.

## Codex Disposition After Round 1

Round 1 returned VETO. Codex accepted the substantive findings and made a bounded correction round without reopening any user decision:

- Task 10.6 `prd.md` now states independently testable internal Skills, global/China plus alias/target/company/trial universe closure, publication default exclusions and rules/model/independent classification, tiered evidence-insufficiency behavior, and the three B bubble presets with neutral/non-ranking output.
- Canonical v1.3 now describes itself as the self-contained authority, limits v1.2 carry-forward to Appendix C explicit incorporation, removes the ambiguous four-format carry-forward, and names LangGraph as non-required/non-authoritative infrastructure.
- Roadmap and execution v3 use the same explicit-incorporation rule; execution v3 also names the LangGraph boundary.
- Task 10.6 PRD now marks the pause handoff as historical and explicitly rejects its old `formats=4` contract.
- Historical draft bytes were preserved. New `docs/specs/README.md` marks it superseded and identifies its obsolete clauses, avoiding retroactive alteration of historical evidence.

Round 2 should be a narrow same-session recheck of these corrections plus the seven authority files. Return PASS only if the original veto causes are closed and no new current-authority contradiction was introduced; otherwise return a concrete residual VETO. Do not restart broad historical exploration.

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

- 2026-09-04 15:04:29 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
