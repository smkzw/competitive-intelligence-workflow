# Execution Context: ci-rebaseline-rebuild-20260904

Created: 2026-09-04 14:36:17 CST
Objective: Implement the approved competitive-intelligence multi-Skill rebaseline and rebuild plan, beginning with R0 provenance recovery and R1 canonical design/roadmap/execution documents, then bounded R2-R6 implementation with deterministic, scientific, visual, packaging, and recovery acceptance.
Task type: `long_horizon_code`
Risk: `high`
Execution module trigger: Codex identified 4 independent work items, which is greater than two.
Route schedule: `peak`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `openai-codex/gpt-5.6-luna:max -> codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `long_horizon_code_executor` -> `pi` / `openai-codex` / `gpt-5.6-luna`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- User-approved implementation plan in the current Codex task (2026-09-04). Its locked product decisions supersede conflicting ZCode recommendations.
- `AGENTS.md` and `/Users/smkzw/.codex/AGENTS.md` for workspace, execution, evidence, and acceptance boundaries.
- `docs/specs/competitive-intelligence-workflow-design-v1.3.md` is the current approved complete specification. v1.2 is retained only as historical provenance and has no independent authority where v1.3 is silent or different.
- `docs/specs/competitive-intelligence-workflow-design-v1.3-draft.md`, `reviews/zcode_ci_engineering_audit_20260902.md`, `plans/zcode_revised_roadmap_20260902.md`, and `plans/zcode_execution_plan_v2_20260902.md` are review inputs, not authority.
- The currently installed and repository-local `competitive-intelligence-workflow` Skill is also a historical implementation input, not normative authority. Audit every clause against the current user decisions and canonical v1.3 contract; revise stale behavior instead of inheriting it.
- `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/PAUSE_HANDOFF_20260902_114643.md` preserves the pause state; the same task's current `prd.md`, `design.md`, `implement.md`, `task.json`, `implement.jsonl`, and `check.jsonl` define the resumed v1.3 task. This is the active Trellis task for the current Codex session.
- `docs/decisions/0013-site-first-v1-delivery-scope.md` is the existing HTML-only release decision; do not recreate it as new work.
- `docs/specs/competitive-intelligence-workflow-design-v1.3.md`, `plans/competitive-intelligence-workflow-roadmap-v1.3.md`, `plans/codex_execution_ci-rebaseline-rebuild-v3.md`, and the synchronized active Task 10.6 documents are the canonical implementation contract. They supersede conflicting v1.2, historical Skill, catalog, implementation, or ZCode clauses. Independent R1 review may identify defects to repair but cannot silently replace user decisions.
- `reviews/codex_v13_implementation_gap_matrix_20260904.md` is the verified R2-R4 RED-to-GREEN routing list. It is an implementation review aid, not a substitute for the complete v1.3 design; every worker and checker must read that design in full from disk.
- Current filesystem and Git state are authoritative for implementation. Preserve completed Task 10.3-10.5 checkpoints and do not edit sealed historical acceptance records.
- Do not read, inventory, chmod, or modify `/Users/smkzw/Documents/AI Products/竞品调研工作流` during R0-R6.

## Authorized Write Sets

- `worker_01`: R0-only governance/rebaseline artifacts under `context/`, `docs/governance/`, `tools/`, and focused tests; it may repair repository quality errors only after recording the pre-change inventory and must not edit the R1 canonical documents or Task 10.6 documents.
- `worker_02`: `docs/specs/competitive-intelligence-workflow-design-v1.3.md`, a new canonical roadmap and execution-plan v3 under `plans/`, one ZCode disposition review under `reviews/`, and the active Task 10.6 `prd.md`, `design.md`, and `implement.md`. Preserve ZCode inputs and v1.2 unchanged.
- `worker_03`: do not dispatch until Codex accepts workers 01 and 02. After that, product source, schemas, package Skills, tools, fixtures, and focused tests required by R2-R4 are authorized; do not edit sealed Task 10.3-10.5 evidence.
- `worker_04`: do not dispatch until Codex accepts worker 03. It may create new R5-R6 projects, acceptance artifacts, reviews, receipts, and checkpoints; it may not emit `RC_FROZEN` or delete/touch the legacy root.

## Locked Product Decisions

- One public entry Skill with typed, independently testable internal Skills; one-sentence autonomous research and optional typed research-package input.
- A/B/C are separate high-density multi-page HTML portals. No combined portal, PDF/PPT runtime, export files, radar chart, evidence-maturity view, or scheduled monitoring in v1.
- Every structured dataset has an appropriate visualization plus an inline collapsed complete table. Narrative and absence explanations are not forced into charts. Each page has one consolidated external-source section; user-visible tables contain no internal file locators.
- A is a landscape console, B an evidence comparison room, and C a design atlas. They share accessibility/responsive/source foundations but not a dashboard template.
- First-run competitor-universe closure is mandatory and independently reviewed. Key absence/abnormal zero gets two alternate recovery searches plus a clean-context final review. Missing independent-review capability fails preflight.
- B uses model-assisted whole-clinical-concept semantic grouping with deterministic conflict guards. Near windows such as 48 versus 50 weeks may share a frame with subtle annotation; incompatible scales, directions, estimands, denominators, or analysis sets remain separate.
- Yaozh is optional, browser-session assisted, and never a sole authority. Ask once whether access is available; credentials and tokens never enter artifacts.
- Registry-linked primary, extension, and key long-term/safety publications are required. Inaccessible required papers create one Markdown manual-supply gate. User files are content-checked then renamed in place with pre-rename name/hash/identity mapping and collision protection. If unavailable after one user response, do not reprompt in the same snapshot; continue with an explicit limitation only if official evidence still answers the core question, otherwise produce an evidence-insufficiency page.
- Publication classification combines versioned rules, model review and independent clean-context review for blocking edges; reviews, routine ad hoc and irrelevant exploratory analyses are excluded by default. In-place rename must not copy, move or alter bytes and must pre-record original name, SHA-256, DOI/registry identity and target name.
- B bubble plots use only the three prescribed clinical families and size semantics: efficacy versus overall safety with treatment N/exposure, efficacy versus serious risk with efficacy analysis-set size, and durability versus discontinuation risk with long-term exposure. Only full clinical-semantic compatibility permits a shared plot; routine output is factual/neutral, with no default ranking, composite score or R&D recommendation.
- Preserve immutable historical snapshots, a latest pointer, and added/changed/withdrawn diffs. The user manually triggers refresh; once triggered, source recheck, diff, snapshot and affected HTML rebuild are automatic. No scheduled monitoring, background polling or untriggered refresh.
- Every structured table is default-collapsed and expands inline; every physical page ends with one consolidated external-source section. No empty axes, fixed zero walls or engineering diagnostics on the first screen. Test every physical page in Chromium and WebKit at desktop, tablet, phone and narrow-screen viewports (at least 1440x900, 1024x1366, 390x844 and 320x568).
- Package one HTML-only universal core with lightweight Codex/Hermes/OMP adapters and expose one installed public entry. Exclude credentials, cache, raw run evidence, deferred format runtimes and their runtime dependencies.
- Real-data acceptance matrix: atopic dermatitis, severe asthma, rheumatoid arthritis, ulcerative colitis, CRSwNP, prurigo nodularis, IgAN, and PNH; each produces A/B/C (24 portals). Execution/conference agents test; Codex accepts. P0/P1 must be zero; P2 requires repair or explicit non-impact disposition.
- Release states are only `DEVELOPMENT_CANDIDATE -> RC_FROZEN -> RELEASED`; Task 10.6 may retain `pending_future=1` but cannot claim `legacy_absent=passed`.
- Legacy retirement remains a separate future action. It requires at least three real projects covering A/B/C, successful user-triggered refresh/history/recovery/three-host operation, zero severe defects and verified rollback, followed by a new explicit user approval before any access or deletion.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. R0: audit and recover the dirty-tree provenance, establish immutable inventory and explicit release source set, and repair truthful quality gates without touching the legacy Chinese root.
2. R1: reconcile ZCode audit input with approved user decisions and create canonical v1.3 design, revised roadmap, execution plan v3, and synchronized Task 10.6 contracts.
3. R2-R4: implement the typed multi-Skill graph, publication/manual-source gates, universe and absence review, semantic grouping, three independent HTML portals, and HTML-only multi-host package.
4. R5-R6: execute the eight-indication A/B/C real-data matrix, independent scientific and visual conferences, three-host/recovery acceptance, RC freeze, and gated legacy-retirement handoff.

## Current Milestone Status — 2026-09-04 16:22 CST

- `M0 Provenance recovered`: accepted by Codex after an initial independent VETO, complete remediation and a same-session independent PASS. The authoritative full gate reports Ruff passed, strict mypy passed over 191 files, 860 unit/contract tests passed and `LEGACY_REF_OK`; its success state is deliberately `quality-only`.
- `M1 Canonical contracts`: accepted by Codex and an independent same-session correction review. Canonical v1.3, the roadmap, execution v3, ZCode disposition, Task 10.6 documents and G01-G20 gap matrix are the current implementation route.
- The original `worker_01` report is rejected as acceptance evidence because it overstated scope and provenance. Its useful bytes were independently audited and corrected; current files plus Codex checks and conference records supersede its claims.
- `worker_02` contract work is accepted after the R1 conference corrections.
- Previous recovery point: `context/ci-rebaseline-rebuild-20260904_recovery_snapshot_receipt.json`.
- Current M1 recovery point: `context/ci-rebaseline-rebuild-20260904_m1_recovery_snapshot_receipt.json`; 18,878 nodes and 5,888,661,178 bytes were source/backup matched, rehashed against the live read-only backup, and verified with zero writable nodes.
- Milestone disk hygiene: `metrics/ci-rebaseline-m1-disk-hygiene-20260904.md`; 54 unique reproducible cache directories were removed, and two validation-regenerated paths were removed again, conservatively reclaiming 53,584 KiB. Evidence and both recovery points were retained.
- R2-R4 (`worker_03`) is now dependency-unblocked but not yet accepted or implemented. Before dispatch, Codex must verify that the generated worker prompt still reads canonical v1.3 in full and does not inherit stale Skill or ZCode behavior.

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.

User amendment (2026-09-04): at every milestone, report progress and perform targeted disk hygiene. Inventory space before deletion; remove only task-generated, exactly identified, reproducible caches, temporary files, and failed-test copies after their decisive evidence is summarized or hashed. Preserve normative documents, checkpoints, manifests, receipts, raw scientific evidence, unaccepted reports, and at least the current and previous recovery points. Never use broad globs or repository-wide clean, and never include the zero-contact legacy root in an inventory or cleanup command. Record removed targets and reclaimed bytes in the milestone checkpoint.

## No-loss Pause — 2026-09-04 16:38:38 CST

The user explicitly paused the Goal. `worker_03` was interrupted with SIGINT before any product/source edit and before a runner report was emitted. Its pending OMP session is `01a06b86-e2ea-7000-89b2-64ea7a838e91`; exact session path, hash, current Git state and resume protocol are recorded in `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/PAUSE_HANDOFF_20260904_163838.md`. Do not dispatch `worker_04`, do not accept R2-R4, and do not clean the pause-state caches. Resume only through the recorded same-session continuation after revalidating the pause snapshot.
