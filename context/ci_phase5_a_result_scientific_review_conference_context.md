# Conference Context: ci_phase5_a_result_scientific_review

Created: 2026-08-27 22:58:03
Objective: 独立复核特应性皮炎A类报告重建候选的ClinicalTrials.gov结果覆盖、人数到发生率换算、组别语义及不得误报未公开；仅输出接受或拒绝及可执行缺口，不修改文件。
Task type: `competitive_intelligence`
Risk: `high`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Visual/design/HTML/PPT tasks use a Codex-led panel with no sub-venue chair. The effective visual participant chain is ``; it is filtered against the actual execution route nodes recorded below before dispatch.
- Chinese labels or Chinese sentence review is handled directly by Codex and does not start a conference.
- Other complex, logic-heavy, evidence-sensitive, artifact-heavy, code-review, and high-risk contradiction work uses a Codex-chaired panel with no sub-venue chair. Participant 1 is Pi/google-antigravity `gemini-3.7-flash` (high) -> Pi/OpenCode Go `muse-spark-1.2-contributor` (high) -> Kimi Code `k3-256k` (medium) -> Codex subAgent `gpt-5.6-luna` (max). Participant 2 is Grok Build `grok-4.6` (medium) -> Pi/Cursor `cursor-grok-4.6` (medium) -> Pi/cms-router `minimax-m3` (high). Codex remains the final authority.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci_phase5_a_result_visibility_repair`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `codex/gpt-5.6-luna`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- Locked input package: `.artifacts/a-fresh-source/evidence/library/a-research-package.json`.
- Rebuilt review candidate: `.artifacts/a-atopic-dermatitis-rebuild/research-content.json`.
- Deterministic rebuild manifest: `.artifacts/a-atopic-dermatitis-rebuild/rebuild-manifest.json`.
- Extraction and validation code: `tools/rebuild_atopic_dermatitis_package.py` and `src/ci_workflow/application/source_research_service.py`.
- Regression checks: `tests/integration/test_atopic_dermatitis_package_rebuild.py` and `tests/integration/test_ctgov_result_coverage_audit.py`.
- The candidate contains 38 products, 43 trials, 65 locked sources, 6,755 efficacy rows and 10,173 safety rows. The manifest records 10 explicit not-reported values, zero parse failures and zero unmapped sources.
- Codex independently validated the candidate with `FreshAResearchContent.model_validate`; its embedded ClinicalTrials.gov coverage audit found zero issues across 6,745 outcome values, 34 TEAE values, 3,956 SAE values and 6,105 common-AE values. These counts and zero-issue claim must be independently reproduced, not trusted as authority.
- Do not access the network. Source truth for this pass is the locked local package.

## Scope

- In scope: determine whether all safely parseable locked ClinicalTrials.gov result values are represented with exact source paths; inspect the participant-count-to-rate conversion; verify treatment/control role and exact regimen preservation; distinguish explicit not-reported/zero-denominator records from parser failures; find material contradictions or silent omissions.
- Out of scope: visual design, browser acceptance, endpoint Chinese localization, web refresh, changing code or data, and final user acceptance.

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- Return `accepted` only if independent commands reproduce zero coverage issues, no displayed percentage above 100%, exact 411/602 -> 68.3%, 133/196 -> 67.9%, and 150/510 -> 29.4% conversions, and exact regimen titles remain available separately from treatment/control role.
- Return `rejected` if a safely parseable value is missing, a count is shown as a percent, a zero-risk denominator is fabricated as 0%, an active regimen is collapsed beyond recoverability, or the validation accepts a known semantic contradiction.

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

- 2026-08-27 22:58:03: Conference initialized by `hermes_workflow_guard.py init-conference`.
- 2026-08-27 23:14: Grok round 1 rejected the candidate for count-as-percent efficacy rows, mixed AE/SAE misclassification, subset TEAE collapse, false `reported_zero` states and switch-arm role errors. Codex reproduced every blocking issue.
- 2026-08-27 23:27: Targeted repair completed and the same locked input was rebuilt. The new candidate converts participant-count efficacy values with their source denominators (including 178/543 -> 32.8%); class `AEs` on a generic mixed AE/SAE measure is now `任何AE`, while the paired `SAEs` class is `任何SAE` (23/602 -> 3.8%, 8/196 -> 4.1%); subset TEAE titles remain distinct; `reported_zero` requires exact numeric zero; active post-switch regimens are treatment arms. `FreshAResearchContent.model_validate` now passes with zero efficacy or safety percentages above 100 and zero false-zero facts. Round 2 must independently re-run the prior objections against the current digest and either accept or identify remaining blockers.
- 2026-08-27 23:43: Grok round 2 accepted the repaired science but identified two bounded residual semantics. Codex fixed both without changing the locked source: hyphenated `Placebo- Tezepelumab` post-switch rows are now treatment arms, and the aggregate 150/510 TEAE measure is `任何TEAE` while skin-infection/discontinuation TEAE subsets remain distinct. Final candidate digest is `21e8a4c39a30cb6b2c00ed90a265f7e843f93bffeb9b811f3da45b44183fefaa`; validation has zero coverage issues and no displayed percentage above 100. Round 3 must verify this exact digest before review metadata is created.
