All P0 fixes verified. Weak API fully removed (the grep hits are the derived `MaturityGateResult` output fields, not caller-fillable contract fields). Emitting the complete report.

# Execution Output: ci_phase5_task51_execution - worker_03

## Boundary And Context Check

- Worked only inside the repo; modified only authorized paths: `src/ci_workflow/reports/a/{contracts,analysis,__init__}.py` and `tests/reports/a/{test_maturity_gate,test_result_bearing_gate,test_no_top_n}.py`. Phase 3 (`src/ci_workflow/gates/*`) and `domain/*` read-only, untouched. No production writes, no package installs, no report/HTML/PDF/PPT generation, no security testing.
- Read set: mandated files (AGENTS.md, execution context, plan) + `reviews/codex_ci_phase5_task51_review.md` (TODO template — the user's P0 list is the authoritative rejection spec), spec §2/§3.2/§12.1–12.3, Hermes plan Task 5.1, full Phase 3 `gates/models.py` + `gates/evaluator.py` + `gates/__init__.py` (ApplicableUniverseSnapshot, GateEvidenceBinding, assert_applicable_universe_closed, assert_bindings_in_universe, derive_result_bearing, derive_product_maturity), `domain/enums.py`, `reports/common/evidence_view.py`, `pyproject.toml`.
- Report file not written by me; returned here per runner contract.

## Work Performed

TDD: wrote failing strong-input tests first (RED: `ImportError: cannot import name 'RegistryResultsPostedEvidence'`), then rewrote contracts/analysis/init (GREEN).

**Weak API deleted (no entry kept):** `AProjectContract.development_maturity/result_bearing/result_bearing_basis_ids` (now `extra="forbid"` → ValidationError), `ResultBearingTriggerEvidence`, `derive_result_bearing_trigger`, `EfficacyRecord`, `SafetySummaryRecord`, `SafetySummaryKind`. `evaluate_maturity_gate(project, snapshot, bindings, results_posted_evidence=())` derives maturity via `derive_product_maturity` and result-bearing via `derive_result_bearing` (scoped per product) or the new typed flag evidence.

**New strong contract:** `RegistryResultsPostedEvidence` — binds `project_id`/`trial_id`/`fact_version_id`/`source_location`, `source_role: Literal[CLINICAL_TRIAL_REGISTRY]`, `review_state: Literal[ACCEPTED]`, `official_results_posted: Literal[True]`; evaluation validates product–trial relation (unknown trial/product, cross-product → `GateEvaluationError`). `SafetyEventUnitId` closed TEAE/SAE set; `AnchorTrialRecord` now carries `fact_version_ids` (min 1).

**P0 false-green fixes:**
1. Real result values: L4 minimums judged directly from `GateEvidenceBinding` — accepted, observed, REPORTED_VALUE/REPORTED_ZERO, real finite `numeric_value` (REPORTED_ZERO⇒0 is enforced by the Phase 3 binding contract; A additionally requires `numeric_value is not None`), positive `denominator` (Phase 3 `gt=0`; A requires not None), full definition/unit/timepoint-or-time-window/analysis_population/treatment_group, `source_location` present. No arbitrary fragment ids.
2. No free booleans: manual maturity/result-bearing fields rejected as extra; trigger only from accepted bindings or typed flag evidence; CANDIDATE/PLANNED/TARGET/PROTOCOL_ASSUMPTION never trigger.
3. Scope closure: `assert_bindings_in_universe(snapshot, bindings)` fail-closed; core trials must be in snapshot + product→trial edge; anchor must be a core trial, in snapshot, own product, and its `fact_version_ids` must resolve to accepted bindings or flag evidence for that product/trial; efficacy/safety minimums must come from the anchor trial.
4. Regulatory events: jurisdiction and date satisfied only by the same event (no stitching); region whole-group NA conflicts with same-region event → blocked; developer/originator whole-group NA only at PAUSED_TERMINATED_WITHDRAWN; denominators never NA (not-None required); control group required for COMPARATIVE design, optional for SINGLE_ARM.
5. `analyze_universe(projects, snapshot, bindings, results_posted_evidence=())`: `assert_applicable_universe_closed(snapshot)` + project ids exactly 1:1 with `snapshot.product_ids` (duplicates/missing/extra/empty → GateEvaluationError); empty universe rejected by snapshot contract (`product_ids` min_length=1). All projects retained in order, no Top-N, any block ⇒ `report_ready=False`.
6. `BlockingExplanation.message_zh` validator rejects text without any CJK character; explanations remain one-to-one with blocked projects in order.

**Tests:** 3 files rewritten to strong inputs (81 tests, all previously-failing semantics preserved: no-Top-N, retention, incremental ladder, Chinese blocking, fail-closed scope). Added exact tests per the mandate: reported-value-without-numeric blocks; reported zero real; manual fields rejected; accepted-binding-only trigger; flag triggers but missing results block; anchor≠core / cross-product / non-anchor efficacy+safety fail closed; stitched regulatory events blocked; developer/originator NA rules; region-NA vs event conflict; denominator-missing blocks; single-arm vs comparative control rules; duplicate/mismatch/empty universe; BlockingExplanation rejects pure English.

## Artifacts And Evidence

| File | Lines | Role |
|---|---|---|
| `src/ci_workflow/reports/a/contracts.py` | 319 | strong contract: RegistryResultsPostedEvidence, SafetyEventUnitId, AnchorTrialRecord(fact_version_ids), no weak fields |
| `src/ci_workflow/reports/a/analysis.py` | 849 | strong evaluation: derive maturity/result-bearing, binding-derived L4 minimums, per-product scoping, universe batch |
| `src/ci_workflow/reports/a/__init__.py` | 111 | exports updated (weak names removed) |
| `tests/reports/a/test_maturity_gate.py` | ~900 | 25 tests |
| `tests/reports/a/test_result_bearing_gate.py` | ~790 | 24 tests |
| `tests/reports/a/test_no_top_n.py` | ~850 | 24 tests |

Smoke (mixed 7-product universe): `report_ready: False | total: 7 | blocked: 2`; layers `dupilumab→result_bearing, clinical→clinical, preclinical→all_projects, submission→filing, terminated→filing, blocked-safety→result_bearing, blocked-clinical→clinical`; Chinese explanations per product with maturity layer + missing-field labels (sample verified: 缺安全摘要药 → TEAE/SAE 数值摘要 missing; 缺试验药 → L2 keys missing). RED evidence: `ImportError: cannot import name 'RegistryResultsPostedEvidence'`.

## Commands And Observations

- `uv run pytest tests/reports/a -q` → RED `ImportError` → GREEN `81 passed in 0.14s`.
- `uv run pytest tests -q --ignore=tests/browser` → `881 passed in 168.41s` (full non-browser regression; 851 baseline + 30 strong-input A tests).
- `uv run ruff check src tests` → `All checks passed!`; `ruff format --check src/ci_workflow/reports/a tests/reports/a` → `6 files already formatted`.
- `uv run mypy src/ci_workflow` (strict, warn_unreachable) → `Success: no issues found in 87 source files`.
- Browser/acceptance suites not run: Task 5.1 is pure contract (no rendering); visual acceptance is Codex's authority (Task 5.4). [INFERENCE]

## Blockers Or Missing Environment

None. No environment gaps; no Phase 3 modifications needed.

## Rerun Requests Or Next Step

- Codex acceptance: 81 A tests + 881 non-browser regression + ruff + strict mypy green; verify no Top-N/成熟项目降级/删除缺证项目 false-green (universe analysis has no such parameters; `report_ready` fail-closed; all L4 minimums binding-derived with scope closure).
- Suggested next: Task 5.1 commit `feat: implement report A scope maturity and evidence model` (now strong-input based), then Task 5.2 view models consume `UniverseAnalysisResult`/`MaturityGateResult`.

**尚未解决的边界 (for Codex):**
1. **Safety kind identification convention**: `GateEvidenceBinding` has no event-class field; the A safety minimum matches the binding's `unit` against the closed `SafetyEventUnitId` (teae/sae). The fact-pipeline must write the closed event-class id into `unit` for safety-summary bindings. Confirmed by tests; pipeline convention not yet wired (out of Task 5.1 scope). [INFERENCE]
2. **Universe closure boundary**: `assert_applicable_universe_closed` runs in `analyze_universe` only; direct `evaluate_maturity_gate` calls get `assert_bindings_in_universe` + per-field scope checks but not full closure (empty proofs, design-edge graph). A gate-level call with a non-closed snapshot still evaluates; only the batch entry is fully closed. Comparative snapshots in tests build the full comparison/group graph anyway. [INFERENCE]
3. **`_product_bindings` scoping**: result-bearing is per product (product-object facts with trial attribution, or this product's trial-object facts); other products' numeric bindings never raise a project's layer. Universe-level cross-product references still fail closed via `assert_bindings_in_universe`. [INFERENCE]
4. **Pre-existing repo format drift**: `ruff format --check src tests` reports 111 pre-existing unformatted files (baseline; worker_01/02 formatted only `reports/a`). I scoped formatting to `src/ci_workflow/reports/a` + `tests/reports/a` only, per edit boundary. Repo-wide `ruff format` remains a separate decision.
5. **Review file is a TODO template** (`reviews/codex_ci_phase5_task51_review.md`); the P0 list in the task message was treated as authoritative. No additional review findings were available to reconcile.
