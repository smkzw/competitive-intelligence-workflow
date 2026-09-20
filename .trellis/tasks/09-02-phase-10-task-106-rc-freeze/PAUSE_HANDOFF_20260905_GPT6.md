# 竞品调研多 Skill 工作流：GPT-6 全量无损交接

Date: 2026-09-05 CST  
Handoff status: `PAUSED_BY_USER`  
Goal status: `paused`; neither complete nor blocked  
Goal thread: `019fe5be-b687-7e11-8c76-2b2c0d2126c9`  
Authorized workspace: `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`  
Git branch at pause: `main`  
Git HEAD at pause: `bb27ec9d750cf02fb64da5dfe665b2f4b262922d`

This is the controlling recovery document for GPT-6. It records the product history, user decisions,
rebaseline, implementation state, evidence, unresolved questions, safety boundaries and exact next
actions. It is a pause record, not an RC/release record and not proof that every historical task
label remains valid under the current v1.3 contract.

---

## 1. First actions for the successor

1. Set the working directory explicitly to the authorized English path above. The desktop task may
   open with a different current directory; never infer scope from that UI cwd.
2. Read this file completely, then read, in order:
   - `docs/specs/competitive-intelligence-workflow-design-v1.3.md`;
   - `plans/competitive-intelligence-workflow-roadmap-v1.3.md`;
   - `plans/codex_execution_ci-rebaseline-rebuild-v3.md`;
   - `reviews/zcode_disposition_ci-rebaseline-rebuild_20260904.md`;
   - `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/{prd,design,implement}.md`;
   - `.trellis/tasks/09-05-r24-gatespec-blocker-closure/checkpoint_20260906_p3_p5.md`;
   - `.trellis/tasks/09-06-r25-yaozh-browser-adapter/checkpoint_20260905_lossless_pause.md`.
3. Read the current global `/Users/smkzw/.codex/AGENTS.md` and this workspace's applicable
   `AGENTS.md`; use the live guard commands as route truth. Do not reproduce a route from this
   handoff or memory.
4. Recheck `git status --short`, Goal state and the current bytes before editing. The tree is
   intentionally dirty. Do not reset, checkout, clean, stash, broad-stage or infer ownership from
   mtime alone.
5. Do not resume Task 10.6 freeze steps. First close the open R2.4 freshness decisions and R2.5
   authority/consumer defects described below.

---

## 2. Non-negotiable safety boundaries

- Never read, list, inventory, resolve, chmod, validate, modify, delete or absence-check the old
  Chinese-named workspace during R0-R6/Task 10.6. Do not even use it as a command argument. Its
  retirement requires future burn-in, rollback evidence and a new explicit user approval.
- Preserve all user and historical changes in the current 1,000+ entry dirty tree. No
  `git reset`, `git checkout --`, `git clean`, speculative stash, `git add .`, or history rewrite.
- Task 10.3, 10.4 and 10.5 are sealed historical checkpoints. Do not modify their files or reinterpret
  them as current RC evidence.
- Do not treat the installed `competitive-intelligence-workflow` Skill, old v1.2, v1.3 draft,
  ZCode output, worker output, memory or an earlier report as authority. They are review inputs only.
- Never put Yaozh usernames, passwords, cookies, session IDs, authorization headers, tokens,
  browser profile/storage, HAR, full DOM or sensitive screenshots into prompts, files, logs,
  receipts, snapshots, packages or bundles.
- Do not bypass CAPTCHA, copy a browser profile, or make Yaozh required for core research.
- No production/external publication, real migration, old-root deletion, spending, or access-control
  change is authorized.
- Never output `RC_FROZEN`, `RELEASED`, `FINAL_ACCEPTANCE_OK`, `legacy_absent=passed`, or Goal
  complete until their actual current gates pass. Deferred/pending is not accepted.
- During long governed execution, dispatch once and wait on the runner's hard wait; no fixed polling,
  latency fallback or silent model substitution. The user explicitly requested main-thread silence
  during 120-minute waits.
- All user questions must use native Ask and be multiple-choice. Do not replace unavailable native
  Ask with a prose questionnaire. If Ask is unavailable, continue safe independent work and retain
  the decision as pending.

---

## 3. Authority order

When sources disagree, apply this order:

1. Current system/platform constraints and the user's latest explicit correction.
2. The active Goal reproduced in section 4.
3. Canonical approved v1.3 design, formal roadmap v1.3 and execution plan v3.
4. Current source, schemas, tests, actual browser/runtime artifacts and accepted current checkpoints.
5. Task 10.6 synchronized PRD/design/implement.
6. Accepted independent review evidence.
7. ZCode audit/plan, historical v1.2/draft, old task labels, installed Skills and model suggestions.

Checklist status is not acceptance. A worker never closes its own ticket. Codex/GPT-6 must reopen
actual files, runtime outputs and rendered pages and owns scientific, browser, package, recovery and
release conclusions.

---

## 4. Active Goal

Rebuild this workspace into an installable multi-Skill clinical competitive-intelligence system for
Codex, Hermes, OMP and compatible Agents. One public Chinese entry (“竞品调研”) accepts either a
one-sentence request or an advanced typed `research-package`; the host autonomously performs
research and compiles the same package contract. Internal research, adjudication, evidence,
analysis, rendering and review Skills remain separately testable and replaceable.

The system produces three independent Chinese-native, high-information-density, multi-page HTML
portals:

- A — 适应症竞品全景台: full innovative competitor universe, target/mechanism, modality, global and
  China development/regulatory status, trial portfolio, company/transaction/patent relations and
  appropriately comparable efficacy/safety views.
- B — 临床结果证据室: trial-level efficacy, safety, baseline, subgroup, exposure and disposition;
  neutral differences, no default ranking or composite score.
- C — 试验方案设计图谱: population, eligibility, endpoints, timepoints, visits, arms, duration,
  estimand, sample size and statistics; evidence-supported multiple design paths, never one
  unsupported “best” design.

The first release is HTML-only. It excludes PDF, HTML-PPT, PPTX, CSV/XLSX, radar charts, evidence
maturity views, scheduled monitoring, background polling, default competitor rankings, composite
efficacy-safety scores and Meta/NMA/MAIC/STC. Historical non-HTML code can remain in the development
repository under bounded compatibility checks but must not enter the v1 bundle, preflight, artifact
closure or acceptance matrix.

The final matrix is eight indications x A/B/C = 24 independent portals: atopic dermatitis, severe
asthma, rheumatoid arthritis, ulcerative colitis, CRSwNP, prurigo nodularis, IgAN and PNH. Execution
models perform real research; independent models review universe completeness, medical semantics,
sources, visual design and interaction; Codex/GPT-6 performs final source/code/science/browser/host/
package/recovery acceptance. P0/P1 must be zero and P2 fixed or have evidence-backed non-impact
disposition before freeze.

---

## 5. User-request and decision history

### 5.1 Initial product correction

The user rejected the earlier workflow as merely process-complete: architecture too shallow, rules
not scientifically detailed, A/B/C reporting not correctly separated, visual output unreadable,
data completeness unproven and presentation not intuitive. The user requested a complete repository
and document review, AI-native multi-Skill redesign, deep optimization or reconstruction, and a
Graph-engineering assessment. The adopted answer is an application-owned typed graph; LangGraph is
not a base dependency or source of truth and any future adapter must be removable.

### 5.2 ZCode audit handoff and later disposition

The user supplied a 2026-09-02 ZCode audit/roadmap/execution proposal but explicitly warned that it
could conflict with later thinking and must not be accepted wholesale. The audit correctly exposed
false full-gate claims and dirty-tree/provenance risk. It also proposed old-root chmod, spreadsheet
export, radar/maturity views and other items later rejected. The complete disposition is preserved in
`reviews/zcode_disposition_ci-rebaseline-rebuild_20260904.md`.

Key final dispositions:

- Keep formal three-host distribution and fresh-install; defer LangGraph indefinitely.
- HTML only for v1; `formats=1` must be calculated from current manifests.
- One public installable Skill entry; internal typed Skills hidden from ordinary users.
- Manual trigger only; refresh is automatic after trigger, but no scheduler/monitor.
- Yaozh is optional browser-assisted lead/cross-check, never sole authority.
- No CSV/XLSX, radar or evidence-maturity product view.
- Old-root chmod/inventory/deletion rejected in current scope.
- 24 new real portals strengthen, rather than replace, deterministic and independent gates.

### 5.3 Approved reconstruction plan

The user explicitly ordered implementation of the six-stage rebaseline/rebuild plan now captured in
canonical v1.3 documents. The user then asked to create a persistent Goal and repeatedly instructed
continuation under global AGENTS methodology, governed execution/conference, regular route refresh,
120-minute no-poll waits and periodic precise disk cleanup.

The user also requested a one-time `gpt-6-astra:high` stage review. The first attempt failed under an
old CLI. After the user reported the CLI updated, an explicit same-model CLI run succeeded. The model
read Codex memory despite an explicit limited read set; therefore its report is advisory only. Its
two reproduced P1 findings were fixed with deterministic tests in this pause slice. Do not treat it
as acceptance evidence.

The user has issued multiple “无损暂停” and resume messages. A lossless pause means preserve source,
dirty changes, hashes, logs, checkpoints, runner identity, open defects and the next safe action; it
does not mean cleanup of evidence or false completion. The latest request asks for this exhaustive
handoff to GPT-6 after safely closing the current bounded work.

---

## 6. Canonical product architecture

The control graph is application-owned, typed and versioned:

1. Public entry and host capability preflight.
2. Indication disambiguation and innovative-treatment ontology.
3. Global/China/commercial-source planning.
4. Multi-source search, retrieval and publication identification.
5. Structured extraction, entity normalization and conflict adjudication.
6. Competitor-universe closure plus independent clean-context review.
7. Report-specific A/B/C analysis.
8. Chart, local collapsible-table and source-section rendering.
9. Browser, scientific and completeness acceptance.
10. Immutable snapshot, latest pointer and added/changed/withdrawn diff.

Every internal node has typed inputs/outputs, done conditions, failure states, recovery route, an
idempotency identity and evidence receipt. The user never manually orchestrates nodes.

Scientific ingress is strict: the deterministic engine consumes only the validated v1.3 audit
package, accepted facts and locked snapshot. Host research or natural language must be compiled into
that package first. Screenshots, chat, memory, stale reports and unbound web search cannot supply
facts directly.

Completeness is closure, not Top-N. Global and China baseline routes plus alias, target, company and
trial reverse expansion must execute, with technical failures distinct from genuine zero findings.
Closure requires the last two consecutive rounds to add zero entities and an independent reviewer
with different producer/reviewer identity and context bound to the current bytes.

Publication handling distinguishes required primary result, extension primary and key safety/
long-term papers from review/ad-hoc/irrelevant exploratory material. Inaccessible required papers
create one Markdown manual-supply gate. User files are validated and renamed in place only after an
original-name/SHA-256/DOI-or-registration/new-name map and collision check; bytes are not changed.
After one confirmed-unavailable response, the same snapshot does not ask again. Official evidence
may support a limited report; otherwise only a concise insufficiency page is user-visible.

Critical missing or abnormal-zero modules require two genuinely different recovery strategies and
independent final review. Missing, zero, not reported, not publicly disclosed, access blocked,
technical failure, conflict and not-applicable are separate states. Core-insufficient means no draft
portal; optional missing modules are omitted or briefly explained, never rendered as empty axes or a
fixed blank-field wall.

B comparison is semantic, not string equality. Population, construct, definition, direction, unit,
time window, estimand, denominator, analysis set and analysis form travel as one clinical unit.
Near windows such as 48/50 weeks may share a frame only when deterministic compatibility checks pass;
otherwise they become adjacent small multiples.

---

## 7. Portal contract

Common rules: shared typography/accessibility/component quality; responsive and keyboard-usable;
offline local assets; every structured dataset has an appropriate visualization followed by an
in-place complete table hidden by default; chart/table use the same fact set; each page has one
aggregated external-source area with type, date, cutoff and limitations; no local file path or
internal locator in reader-facing tables; no Gate/prompt/coverage diagnostics on the default first
screen.

A emphasizes the full competitor universe and may use pipeline landscape, target-product relation,
stage matrix, geographic-status timeline, efficacy comparison, safety heatmap and multidimensional
bubbles. No “star product” truncation.

B emphasizes efficacy, safety, baseline, subgroup, exposure and disposition. Its fixed bubble
presets are efficacy signal x overall safety (size = treatment N/exposure), efficacy signal x serious
risk (size = analysis-set N), and durability x discontinuation risk (size = long-term exposure).
Only semantically comparable units share a plot; raw value, direction, window and denominator remain
in the table.

C emphasizes architecture, population, eligibility, endpoint/timepoint, visits, treatment period,
estimand, sample size and statistical design. It uses design pattern maps, timelines,
endpoint-window matrices, eligibility themes, arm structure and difference views. Full criteria and
parameters live in tables. Indication-only input yields multiple supported paths, not one “best”.

All physical pages require real Chromium and WebKit evidence at no less than 1440x900, 1024x1366,
390x844 and 320x568, including routes, long tables, filters, evidence drilldown, empty states,
Chinese legibility, overflow, overlap, keyboard, console and external links.

---

## 8. Historical build before rebaseline

The repository contains a large completed historical implementation. Preserve it, but distinguish
historical completion from current v1.3 acceptance:

- Phase 0/1: repository foundation, contracts, project workspace, SQLite truth store, evidence chain,
  event/snapshot and capability preflight surfaces.
- Phase 2: ontology, identity, global/China source policy and connectors, ingestion locators, facts
  and claims.
- Phase 3: evidence gates, recovery graph, isolated scientific QC and no-draft behavior.
- Phase 4: common multi-page portal shell, filters/URL state, interactive charts, complete tables,
  evidence drawer and browser acceptance harness.
- Phase 5: A portal, including profile/landscape, efficacy/safety/bubble views and later safety/value
  completeness repairs.
- Phase 6: B trial-role and semantic compatibility, longitudinal efficacy, safety heatmap,
  efficacy-safety matrix, baseline, disposition and complete portal.
- Phase 7: C design facts, eligibility drilldown, design views, multiple paths and complete portal.
- Phase 8: historical PDF/HTML-PPT/PPTX work. Many subtasks are marked complete, but this entire
  format family is excluded from v1 release. Task 8.7b remains in progress and must not be revived
  without a future scope decision.
- Phase 9: historical refresh, monitoring, host adapters and candidate bundle. Manual refresh/diff
  remains relevant; scheduled monitoring is excluded. Historical host/bundle success must be rerun
  against final v1.3 source and bundle.
- Phase 10.1/10.2/10.3: historical test matrix, product rebuild and host full-matrix rehearsal.
  10.3 is sealed. Three old external A/B/C projects later failed current package-digest checks and
  must be freshly regenerated in R5/R6; old green labels do not count.
- Task 10.4/10.5: sealed migration/cutover governance history. Do not modify.
- Task 10.6: still in progress; no checklist item A01-D04 is accepted as final freeze work under the
  current canonical contract.

Git HEAD predates most current work. At the last inventory before this document, the dirty tree had
1,171 entries: 146 modified, 1 deleted and 1,024 untracked. This is an aggregate of long-running
project/user/history work, not the output of one task. Recompute after reopening; never “fix” it by
destructive Git commands.

---

## 9. Rebaseline progress

### R0 / M0 — complete and accepted

An immutable recovery baseline and truthful all-repository quality gate were established without
cleaning the tree. The first worker's overbroad provenance/full-green claims were rejected, repaired
and independently re-reviewed. Current trusted M1 recovery snapshot:

`/Users/smkzw/Documents/AI Products/.ci-rebaseline-backups/ci-workflow-m1-20260904T082040Z`

It had 18,878 nodes and 5,888,661,178 bytes; source and backup manifests matched and the backup had
zero writable nodes. Source canonical digest:
`1e7e3aeeb031d0391a7fb333fb9825869047835cc54aff46b268fee7575b9d22`.
This is a dirty-tree recovery anchor, not the final release source set and not a pre-project backup.

### R1 / M1 — complete and accepted

Approved canonical artifacts are v1.3 design, roadmap v1.3, execution v3, ZCode disposition and the
synchronized Task 10.6 documents. Independent conference initially vetoed gaps, then passed the
same-session repairs. Draft/v1.2/ZCode originals remain unmodified history.

### R2.1 — largely implemented, not a standalone milestone close

One-sentence host research produces a typed autonomous work item; strict `research submit` binds the
v1.3 audit envelope to A/B/C payload bytes; loose product data fails closed; multi-report runs share
only input-identical nodes and still produce separate portals. One public Skill owns natural-language
intake and native Ask; no duplicate natural-language CLI was built. Three-host real entry remains R5.

### R2.2 — complete and accepted

Typed universe expansion receipts replaced prose proof; global/China routes and alias/target/company/
trial reverse expansions bind source/query/result/diagnostic/entity bytes; technical failure cannot
pretend zero results; two zero-add rounds and independent byte-bound clean-context review are
required. A/B/C share one project-level universe identity.

### R2.3 — complete and accepted except Yaozh was explicitly separate

Publication verdicts, route-family acquisition attempts, per-trial search receipts, independent
review, one-shot manual gate, wrong-file recovery, scanned-PDF OCR handoff, immutable rename mapping,
replacement/resubmit and limited/blocked outcomes are wired into product runtime and were independently
reviewed. Yaozh real browser behavior was never implied by this close.

### R2.4 — almost complete, still open

Object/unit GateSpec, source/maturity/disclosure states, candidate-universe preservation, dual
recovery and information gain, independent omission review, report-specific blocker/no-draft and
atomic/idempotent blocker recovery are implemented. A/B/C format then enter `rendered_unreviewed`;
only a real independent `review issue` receipt, issuance record, verdict bytes and current portal
digest permit one-way promotion without changing HTML bytes.

Earlier R2.4 evidence: focused 233 passed; product chain 579; full gate 945 active + 20 retained + 7
layer; a 328-file development bundle SHA-256
`8d2aeca2f01fa9039cb16ae26041b0559345d164b48ecbb7cf86ca21908eb011`.
That bundle is not RC.

R2.4 remains open because freshness semantics require native Ask. Moreover, the 2026-09-05 Astra
review uncovered a separate R3/B semantic gap: rows with identical missing semantic placeholders may
be grouped as compatible. Unknown estimand/denominator/analysis-set semantics must not automatically
share a frame. This is not fixed and must not be hidden by the older “only freshness remains” wording.

### R2.5 — current paused task, not complete

Completed now:

- removed blank-Chromium-as-login false readiness;
- added closed host session observation and immutable receipt with six technical states;
- bound project, one-time answer bytes, observation digest, offset time, host and canonical Yaozh
  origin; future time, secrets, local paths and drift fail closed;
- added CLI `yaozh observe` and content-addressed replay-stable receipt persistence;
- added `commercial_database`, limited to `secondary` and exact Yaozh enterprise host;
- synchronized schemas, manifest and public/internal Skill instructions without adding credentials or
  browser runtime to the core package;
- restored B regulatory-material baseline policy and fixed cross-group endpoint fact reuse.

Still open and completion-blocking:

1. The persisted Yaozh receipt has no product-run consumer; the optional route is non-operational.
2. Source-policy authority is declarative, not enforced through Yaozh-to-fact/gate lineage. A buggy
   adapter could relabel Yaozh content as `designated_industry_source`. Independent conference rates
   this P0 scientific integrity for R2.5 completion.
3. No max-age/current-run freshness behavior is approved. Do not invent a TTL.
4. Damaged/symlink answer records need a typed run-level failure instead of a possible raw exception.
5. No actual authenticated Yaozh session smoke has run.

Task state must remain `in_progress`; P1/P2/P3/P5 are checked, P4/P6 remain partial.

### R3-R6 — not currently accepted under rebaseline

Historical A/B/C code and portals exist, but current R3 data projection and R4 portal acceptance must
be rerun after R2 closure. R5 final bundle/three hosts/manual refresh/recovery and R6 24 new real
portals/RC freeze have not occurred. There is no RC commit, no final source set and no release.

---

## 10. Changes in the final R2.5 slice

Material product/test files edited in this slice:

- `src/ci_workflow/application/capability_preflight.py`
- `src/ci_workflow/application/yaozh_access.py`
- `src/ci_workflow/domain/research_package.py`
- `src/ci_workflow/gates/evaluator.py`
- `src/ci_workflow/cli.py`
- `policies/gates/B-v1.yaml`
- `schemas/research-package.schema.json`
- `schemas/yaozh-session-observation.schema.json`
- `schemas/yaozh-route-access-receipt.schema.json`
- `schemas/package-manifest.schema.json`
- `package-manifest.json`
- `skills/competitive-intelligence-workflow/SKILL.md`
- `skills/_internal/source-routing/SKILL.md`
- related integration/contract/report/manifest tests.

Governance artifacts created or completed:

- `.trellis/tasks/09-06-r25-yaozh-browser-adapter/`
- `context/ci-r25-yaozh-browser-adapter-20260906_execution_context.md`
- `plans/codex_execution_ci-r25-yaozh-browser-adapter-20260906.md`
- `runs/execution/ci-r25-yaozh-browser-adapter-20260906/worker_01.md` through `worker_03.md`
- matching prompts/logs, execution review and metrics;
- conference context/route manifest/prompts/run/log/review/metrics under task id
  `ci-r25-yaozh-browser-adapter-20260906-conference`;
- `prompts/reviews/ci-stage-review-gpt6-astra-high-20260906.md` and
  `runs/subagents/ci-stage-review-gpt6-astra-high-20260906.md`.

Do not delete these artifacts on resume; they support the open-task disposition and this handoff.

---

## 11. Latest deterministic evidence

At the pause boundary after the final code changes:

- Yaozh/schema focused: `39 passed`.
- Two new P1 scientific gate regressions: `2 passed`.
- Related R2.5/report/package matrix: `198 passed, 1 skipped`.
- Full product chain `tests/integration tests/graph tests/application`: `586 passed`.
- `tools/gate.sh`:
  - Ruff all `src tests tools`: passed;
  - strict mypy, no incremental cache, 211 source files: passed;
  - active v1 unit/contract: `947 passed, 20 deselected`;
  - retained non-HTML compatibility smoke: `20 passed, 947 deselected`;
  - v1 layering audit: `7 passed`;
  - old-runtime-reference scan: passed;
  - final signal: `GATE_OK status=quality-only steps=6`.

This proves current deterministic code quality only. It does not prove Yaozh live operation, source
authority enforcement, current B semantic grouping, R3/R4 browser acceptance, three-host install,
24 real portals, recovery rehearsal or RC.

Governed execution task `ci-r25-yaozh-browser-adapter-20260906` ran three independent read-only
ZCode/GLM-5.3-Flash workers. Route identity audit and Codex review/metrics gate passed. The workers
identified the missing runtime consumer and executable authority boundary.

Independent conference `ci-r25-yaozh-browser-adapter-20260906-conference` ran
Pi/opencode-go/muse-spark-1.3-contributor:xhigh, one round, no fallback. Conference validation and
Codex review/metrics gate passed. Verdict: revise R2.5 before completion; safe to pause.

The one-time Astra run actually used `gpt-6-astra` with high reasoning after CLI update, but violated
its read-set by opening Codex memory. Its output is not compliant acceptance; only independently
reproduced findings were adopted.

---

## 12. Pending native Ask decisions

Ask these through the product's native multiple-choice UI only. Do not ask as prose. The earlier
Default-mode surface did not expose native Ask, so the decisions remain unresolved.

### Ask group 1 — general evidence freshness model

1. Model: role-based hybrid (recommended) vs one uniform maximum age vs latest-version-only.
2. Default windows: 30/90 days (recommended candidate) vs 14/30 vs 60/180. The exact pairing by
   source role must be explained in the Ask UI.
3. Historical cutoff: dual lock on publication/effective time (recommended) vs disclosure-only vs
   archive-only.

### Ask group 2 — Yaozh session observation

Fold this into the same coherent freshness decision rather than inventing a hidden TTL:

1. Is a Yaozh `ready` observation valid only for the current run (recommended), for a short fixed
   window, or until an explicit negative observation?
2. If stale, should selection ignore it and re-observe (recommended) or materialize a distinct stale
   state? Never rewrite it as factual `session_expired` without observing expiry.
3. Keep bare-domain host attestation (recommended for v1) vs add a specified page-reference digest.

The canonical lineage marker should be policy `source_id=yaozh_enterprise` plus
`ResearchSource.source_role=commercial_database`; never rely on a free-text prefix. Whether every
result-bearing fact must carry a policy-resolved source lineage is an architecture requirement, not
an optional user product preference.

---

## 13. Exact next implementation sequence

### Step 1 — re-anchor and ask

- Reopen current files/checkpoints and run live route selection.
- Use native Ask for freshness/historical-cutoff/Yaozh current-run semantics.
- Record the decision in canonical design, roadmap, R2.4/R2.5 task docs and a decision record before
  code changes.

### Step 2 — close R2.5 authority and runtime consumer with TDD

Create a new bounded Trellis subtask rather than silently expanding the old patch.

RED tests first:

- package source id must exist in current source policy;
- `yaozh_enterprise` must be `commercial_database`/`secondary`/exact host;
- skipped/unavailable project cannot claim a Yaozh route or Yaozh source;
- Yaozh-derived content relabeled as `designated_industry_source`, publication, registry or
  regulatory evidence cannot satisfy a critical GateSpec unit;
- Yaozh may remain a lead/identity-discovery input and a cross-check only alongside an authoritative
  direct source where the policy allows it;
- optional Yaozh route cannot be load-bearing for universe closure;
- fresh bound ready receipt permits only the optional route; missing/stale/blocked receipt keeps the
  route non-blocking unavailable;
- receipt/project/answer/host/run drift fails closed;
- corrupt/symlink answer record becomes one typed Chinese run outcome, no re-ask and no raw traceback.

Implement the smallest policy-resolved provenance boundary. Do not blindly adopt worker_03's broad
D1-D4 redesign or add a new second evidence engine. Preserve lead discovery while preventing any
result-bearing authority escalation. Ensure the run consumes a current receipt but never claims that
the digest independently proves login; it is a governed host attestation.

Run focused, adjacent, full product and `tools/gate.sh`, then a new independent execution audit and
conference. Keep R2.5 open until a real-host smoke is performed without sensitive artifacts.

### Step 3 — close R2.4 freshness and B semantic unknowns

- Implement the selected source-role freshness model in model/schema/YAML/evaluator and monotonic
  override rules with RED tests for stale/future/cutoff behavior.
- Repair B semantic grouping so unknown/missing estimand, denominator, analysis set, direction or
  scale cannot be treated as compatibility merely because placeholders match. Preserve the 48/50
  near-window positive case and add conflicts for direction/scale/estimand/denominator/analysis set.
- Audit maturity derivation: model-derived maturity cannot elevate evidence beyond observable source
  facts. This was a P2 Astra concern and needs deterministic disposition.

Only then may M2/R2.4 and R2.5 be considered for closure.

### Step 4 — R3 data projections

Revalidate A/B/C projections against accepted evidence, new authority/freshness rules and the
semantic unit. Do not reuse old report success as acceptance. Confirm all specified A/B/C visual
datasets and neutral/non-ranking constraints.

### Step 5 — R4 portals

Rebuild/repair each portal independently; do not recolor one dashboard template. Verify chart/table
same-set closure, local source sections, interactions, responsive/keyboard behavior and all physical
pages in Chromium/WebKit at four viewports. Run a separate visual execution packet and visual
conference; a general code conference cannot substitute.

### Step 6 — R5 final bundle, hosts, refresh and recovery

- Build from an explicit clean release source set without disturbing the dirty user tree.
- HTML-only bundle; no logs/caches/raw evidence/non-HTML runtime/credentials.
- Fresh-install and native “竞品调研” trigger on Codex, Hermes and OMP from the same bundle.
- Manual trigger then automatic source recheck, immutable snapshot/latest/diff and affected-page
  rebuild.
- Recovery package/rehearsal in an isolated root.

### Step 7 — R6 24 real portals and Task 10.6 freeze

Use new project/run/job/session/artifact/verdict identities and current sources for all eight
indications x A/B/C. Complete scientific, source, visual, interaction, package and recovery
independent verdicts. Only after P0/P1=0, P2 disposition, three hosts and owner-stage receipt closure
may Task 10.6 create its unique RC commit and eventually emit the exact frozen signal. Old projects,
old screenshots and the development bundle are negative controls, not acceptable evidence.

---

## 14. Task and release truth at pause

- Goal: paused, active objective preserved; not complete, not blocked.
- M0/R0 and M1/R1: accepted.
- R2.2 and R2.3: accepted within their stated scope.
- R2.4: open for native freshness decisions and newly discovered B semantic/maturity follow-up.
- R2.5: open; optional route non-operational; P4/P6 incomplete.
- M2: not closed.
- R3/R4 current rebaseline acceptance: not closed.
- R5/R6: not started as final release work.
- Task 10.6 A01-D04: all remain unchecked.
- RC source set/commit/tag: absent.
- Final HTML-only bundle: absent.
- Three-host final install evidence: absent.
- 24 current real portals: absent.
- Recovery rehearsal: absent.
- `RC_FROZEN` / `RELEASED`: forbidden at this state.

Historical Trellis task labels marked completed are preserved history. They are not retroactively
deleted, but where the release scope or canonical contracts changed they require current revalidation
before contributing to release closure.

---

## 15. Disk, evidence and cleanup state

The workspace is approximately 5.6 GiB. Large retained surfaces observed at pause include roughly:
`logs` 1.6 GiB, `archives` 1.1 GiB, `.artifacts` 1.0 GiB, `runs` 771 MiB, `output` 337 MiB,
`docs` 300 MiB and `.venv` 303 MiB. Do not bulk-delete them: they mix active governance evidence,
historical acceptance, recovery inputs and potentially reproducible output. First build an exact
reference/ownership inventory and obtain a replacement hash/pointer before deleting any material
evidence.

At this pause, only reproducible `.pytest_cache`, `.mypy_cache`, `.ruff_cache` and `__pycache__`
under `src/tests/tools` were deleted, about 34 MiB. No source, fixture, runner report, log, snapshot,
archive, historical `tmp`, artifact, output, virtual environment, Codex session or recovery anchor was
deleted. Protected Codex runtime state under `~/.codex/sessions`, archived sessions, databases and
thread history must never be part of project cleanup.

Future cleanup procedure: inventory exact targets, prove they are generated and unreferenced, record
bytes and replacement evidence, delete only exact paths, then verify no source/checkpoint/receipt was
removed. Never use project-wide globs or `git clean`.

---

## 16. Useful commands on resume

All commands must use the authorized English-path workdir.

```bash
git branch --show-current
git rev-parse HEAD
git status --short
python3 /Users/smkzw/.codex/tools/hermes_workflow_guard.py route \
  --task-type competitive_intelligence --risk high
tools/gate.sh
```

Do not immediately rerun the entire gate just to prove activity; first verify whether the bytes have
changed since this handoff. Use focused RED/GREEN tests for the next defect, then adjacent regression,
full product chain and full gate before accepting the slice.

Current execution/conference evidence can be re-audited with the live guard, but do not archive it
until the successor has accepted this handoff and created the next durable checkpoint.

---

## 17. Final handoff warning

The present repository is healthy enough to continue—the latest broad deterministic gates are green
and the current dirty tree is recoverable—but the product is not release-ready. The most dangerous
failure mode for the successor is to see many historical completed tasks and green test counts and
resume RC freezing. Do not. The correct next edge is native freshness adjudication followed by
Yaozh authority-lineage/runtime-consumer TDD and B semantic hardening. Preserve the boundary between
engineering green, scientific acceptance, visual acceptance, real-host operation and release.
