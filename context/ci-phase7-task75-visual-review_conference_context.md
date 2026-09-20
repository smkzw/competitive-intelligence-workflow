# Conference Context: ci-phase7-task75-visual-review

Created: 2026-08-30 22:53:33 CST
Objective: 以资深临床试验医学经理视角，对C类特应性皮炎十二页设计门户和逐试验详情进行独立视觉、中文表达、信息完整性与交互一致性验收；候选摘要必须匹配冻结版本
Task type: `visual_delivery_conference`
Risk: `medium`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`visual_single_object`) with no sub-venue chair. Its effective `CST` route chain is `cursor/cursor-grok-4.6:high -> codebuddy-cli/glm-5.3-flash:max -> openai-codex/gpt-5.6-terra:medium`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-phase7-task75-report-c-portal`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `grok-build/grok-4.6`, `openai-codex/gpt-5.6-luna`, `cursor-cli/cursor-grok-4.6`, `cursor/default`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- Frozen rendered site: `reviews/ci-phase7-task75-report-c-portal/site/`
- Current repaired site tree digest: `bcf4fb223bea61c282684e80d2bae8c1906ecc7b2cf9d500970ee385da4df058`.
  Reproduce from the site directory with:
  `find . -type f -print0 | sort -z | xargs -0 shasum -a 256 | shasum -a 256`.
- Real source-backed input: `fixtures/positive/c-atopic-dermatitis/inputs/report-data.json`
- Four byte-bound ClinicalTrials.gov registry snapshots and receipts:
  `fixtures/positive/c-atopic-dermatitis/sources/clinicaltrials/` and
  `fixtures/positive/c-atopic-dermatitis/source-receipts.json`
- Browser attack observations:
  `reviews/ci-phase7-task75-report-c-portal/observations/medical-manager-attack.json`
  (Chromium/WebKit, 120 page checks, 740 passed checks, zero recorded defect)
- Representative screenshots:
  `reviews/ci-phase7-task75-report-c-portal/screenshots/`
- User-facing requirements and page responsibilities:
  `.trellis/tasks/08-30-phase-7-task-75-report-c-portal/prd.md` and
  `configs/report-page-catalog/C.yaml`
- Project-owned Kangzhe site contract:
  `contracts/kangzhe/design_specs/core.md`,
  `contracts/kangzhe/design_specs/project_profile.md`, and
  `contracts/kangzhe/design_specs/track_site.md`
- Functional/browser evidence: 193 C-related tests passed after repair; focused
  medical-manager browser matrix passed 48/48; Ruff passed.

## Scope

- In scope: independently inspect the actual frozen HTML and screenshots as a
  Chinese senior clinical-trial medical manager; assess first-screen hierarchy,
  readability, chart/table sequence, 12-page responsibility differences,
  trial-specific drill-down, filter/evidence interaction, Chinese-native labels,
  density, spacing, color, and clinical usefulness.
- In scope: actively open representative pages in a browser or inspect screenshots;
  a source-code-only review is insufficient.
- In scope: return concrete page/viewport evidence for every blocker and separate
  release-blocking defects from later polish.
- Out of scope: editing any file, adding product features, PDF/PPT generation,
  security testing, production changes, or accepting clinical/regulatory claims.

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- The review explicitly covers at least overview, treatment arms, endpoint/timepoint,
  sample/statistics, design paths, one trial dossier, and one evidence drawer view.
- The review states whether a medical manager can see the core visual without
  horizontal dragging at 1024/1280/1920 and whether any user-visible engineering
  label, raw registry enum, duplicated label, or untranslated phrase remains.
- The result is accepted only when no unresolved high/critical visual or clinical-UX
  blocker remains; nonblocking polish must be listed separately.

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

- 2026-08-30 22:53:33 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
- 2026-08-30: First visual pass rejected the frozen candidate because shared
  A-class chart code erased the C-class table, reused a generic status matrix,
  mis-encoded sample size as efficacy-safety, and left English registry sentences
  as primary visible values.
- 2026-08-30: Codex replaced the shared runtime with a C-specific page-aware
  visual layer, preserved the nine-column design table, added Chinese structured
  values, rerendered the site, and reran Chromium/WebKit: 120 page checks,
  740 passed checks, zero recorded defects; 187 C regressions and Ruff passed.
- Every follow-up in the same conference session must inspect the current digest;
  conclusions from an earlier candidate cannot be reused.
- 2026-08-30: Second repair removed process placeholders and Python nulls from
  user-visible facts, made unresolved critical Chinese structuring fail closed,
  shortened the first screen, placed fact values inside criteria/arm/endpoint
  matrices, exposed trial group/cohort/registry-field columns, changed source
  links to human ClinicalTrials.gov study pages, and synchronized `site/` with
  `final-candidate/site/`. Current digest is `c4cdae0a...`; 187 tests, Ruff,
  120 browser pages and 740 medical-manager checks pass with zero recorded defect.
- 2026-08-30: Third repair replaced user-visible group/cohort ids with Chinese
  clinical labels while retaining stable ids only in data; added an acceptance
  assertion against kebab-case dossier cells and archived two stale screenshots.
  `site/` and `final-candidate/site/` are byte-identical at digest `47bb95b2...`;
  187 tests, Ruff, 120 browser pages and 740 medical-manager checks pass.
- 2026-08-31: Named Minimax review reproduced digest `47bb95b2...` and correctly
  challenged two visually empty summaries: the overview coverage matrix showed
  only dots, while the design-pattern radar collapsed four trials onto the same
  outline. Hy3-x also reported defects, but its high-severity evidence referenced
  two stale 22:34/22:35 screenshots already superseded by the 23:48 batch; those
  claims were not carried forward without current-site reproduction.
- 2026-08-31: Codex replaced the overview with a four-dimension core-design fact
  matrix (population, regimen, primary endpoint, sample size), replaced the
  overlapping radar with a concrete design-choice matrix, added trial short names,
  multiline clinical facts and complete IGA threshold/timepoint display. Current
  `site/` and `final-candidate/site/` are byte-identical at digest `51bf3506...`;
  193 C tests, Ruff, 120 browser pages and 740 medical-manager checks pass with
  zero recorded defect.
- 2026-08-31: The same conference session accepted digest `51bf3506...` with no
  high/critical blocker, then identified two narrow polish items. Codex corrected
  the trial-index chart title/type collision, expanded regimen wrapping so the
  treatment period remains visible, added current trial-index screenshots, and
  replaced technical filter wording with direct Chinese user guidance. Current
  digest is `ee31bcdb...`; 195 C tests, Ruff, 120 browser pages and 740 checks pass
  with zero recorded defect, with 28 current Chromium/WebKit screenshots.
- 2026-08-31: The same session accepted `ee31bcdb...`. Codex then closed its one
  remaining chart-readability polish item: the treatment-arms matrix now keeps
  dosing frequency, loading dose and full treatment period, and displays
  Dupilumab/Nemolizumab as 度普利尤单抗/奈莫利珠单抗 in primary Chinese chart
  values. Current digest is `b2b89805...`; 197 C tests, Ruff, 120 browser pages and
  740 checks pass with zero recorded defect, with 32 current Chromium/WebKit
  screenshots.
- 2026-08-31: The same session accepted `b2b89805...`. Codex then completed the
  final typography pass: clinical facts wrap at semantic phrase or word boundaries,
  no longer split `250 mg`/`300 mg`, and `Lebrikizumab 匹配安慰剂` has a readable
  separator. Current digest is `4a5c4825...`; 197 C tests, Ruff, 120 browser pages,
  740 checks and 32 current screenshots pass with zero recorded defect.
- 2026-08-31: The same session accepted `4a5c4825...`. Codex completed the final
  Chinese typography cleanup: the long nemolizumab trial label now uses the
  meaningful short name `奈莫利珠单抗研究`, dossier headings include spacing,
  and per-trial filter guidance no longer says `模块级`. Current digest is
  `bcf4fb22...`; 197 C tests, Ruff, 120 browser pages, 740 checks and 32 current
  screenshots pass with zero recorded defect.
