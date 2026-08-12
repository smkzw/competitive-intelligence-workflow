Continuing the same session for a read-only review of the P1-1 batch-identity fix. Loading the prior manager note, worker follow-up, and current batch/aggregation code.Exact suite is 141 green. Reading the batch implementation and running adversarial identity attacks next.P1-1 reuse attack is closed. One related construction-trust note remains as P2. Final report:

---

# Execution Output: ci_phase3_task31_implementation - finite_code_manager_cursor

## Boundary And Context Check

- Same session (`ci_phase3_task31_implementation` / `finite_code_manager_cursor`); no restart.
- Read-only review of the P1-1 batch-identity narrow fix. No source/tests/policies/schemas/Trellis/report writes; no acceptance record.
- Read set completed: AGENTS, `manager_followup_02.md`, `worker_02_followup_04.md`, `implement.md`, gates package (`models`/`evaluator`/`coverage`/`__init__`), three Task 3.1 test files.
- Evidence: live implementation + independent adversarial probes; worker self-report not trusted.
- Output path `manager_followup_03.md` returned inline only.

## Work Performed

Verified `GateEvaluationBatch` + batch-bound `aggregate_report_gates`, and that `evaluate_report` / `recompute_report_result` build and consume one batch.

### Attack disposition (manager probes)

| Attack | Verdict | Evidence |
|---|---|---|
| Reuse valid batch under object-identical different evidence snapshot | **REJECTED** | `GateEvaluationError` (`证据快照` / `宇宙摘要`). Role-set-only summary change also rejected. |
| Reuse under same-version changed-content spec | **REJECTED** | Threshold change → different fingerprint → `规则指纹` error before matrix. |
| Tamper `batch_key` | **REJECTED** | `ValidationError` (`批键`). |
| Reorder results keeping old key | **REJECTED** | Digest is order-sensitive; key mismatch. Fresh batch from reordered results gets a new key; same-identity aggregate still OK (set matrix). |
| Alter one unit result keeping old key | **REJECTED** | Key inconsistency. |
| Inject cross-report unit into batch | **REJECTED** | Batch construction fails. |
| Inject duplicate `(unit_id, object_id)` | **REJECTED** | Batch construction fails. |
| Source batch immutable after failed attacks | **HOLD** | `model_dump_json()` unchanged. |
| Canonical evaluate → one batch → aggregate | **HOLD** | `evaluator.py` `from_evaluation` then `aggregate_report_gates`; coverage only calls `evaluate_report`. Recompute regression green. |

### Prior five Luna P0 closures

All six prior named regressions still green (zero-group comparison, effect endpoint lineage, raised threshold direct + recompute, incomplete matrix, distinct fact lineage), plus new `test_aggregate_rejects_unit_result_batch_from_different_snapshot_or_spec`.

### Prior P1-1 status

Manager followup_02 false-green (snap1 results aggregated under snap2) is **closed** on the batch API: a batch stamped for snap1 cannot aggregate under snap2.

## Artifacts And Evidence

- `models.py`: `GateEvaluationBatch` (frozen, key-validated), `compute_unit_results_digest`, `compute_batch_key`, `from_evaluation`; `aggregate_report_gates(..., batch=)` identity checks before matrix.
- `evaluator.py`: builds batch then aggregates.
- `coverage.py`: unchanged; only `evaluate_report`.
- `__init__.py`: exports batch helpers.
- Exact regression: `test_aggregate_rejects_unit_result_batch_from_different_snapshot_or_spec`.

**Residuals**

- **P2-1** (documented): context-free `ReportGateResult` still accepts unknown `unit_id` when `report_kind` matches. Membership remains at aggregate/batch boundary.
- **P2-2** (related construction trust, not the closed reuse attack): `from_evaluation(spec, snap2, unit_results_from_snap1)` will stamp a new honest batch for snap2 and aggregate under snap2 if the object matrix matches. Unit results are not provenance-tagged to their evaluation snapshot. Canonical `evaluate_report` does not expose this (results and batch are produced together). Distinct from P1-1 batch *reuse*, which is fail-closed.

## Commands And Observations

| Command | Observation |
|---|---|
| Exact trio | **141 passed** |
| Full suite (`TMPDIR=.pytest-tmp -p no:cacheprovider`) | **329 passed** |
| Ruff (gates + 3 tests) | All checks passed |
| `mypy --strict src/ci_workflow/gates` | Success, 4 files |
| `ci-workflow package verify --root .` | `PACKAGE_OK … phase-2-accepted` |
| `git diff --check` | Clean |
| Batch + 5 prior P0 regressions | **7 passed** |
| Adversarial batch attack set | **17/17 PASS** |
| Prior P1-1 reuse under snap2 | **Fail-closed** |
| Rewrap via `from_evaluation(snap2, snap1 results)` | Accepted (P2-2 note) |

## Blockers Or Missing Environment

None. Full suite needs workspace `TMPDIR` + `-p no:cacheprovider` when system temp is unwritable. No security testing.

## Rerun Requests Or Next Step

**Manager recommendation to Codex: `PASS`**

- **P0 = 0; P1 = 0; P2 = 2** (P2-1 unknown-unit value-object load; P2-2 optional provenance binding of unit results into `from_evaluation`)
- Prior P1-1 batch-reuse false-green is closed; five prior Luna P0s remain green; canonical evaluate/recompute use one batch.
- No worker rerun required for this narrow fix.
- This is **not** Task 3.1 final acceptance. Codex remains final authority.
