# Codex SubAgent Task: ci_phase3_task31_acceptance

## Boundary Check

Read-only review completed. No source, test, Trellis, or runner report files were modified. Temporary pytest artifacts were removed.

## Work Performed

- Exact Task 3.1 trio: `141 passed`.
- Full suite with cache/bytecode disabled and project-local `TMPDIR`: `329 passed`.
- Additional adversarial probes: `24 passed`.
- Tested batch tampering, reordering, duplicate/cross-report results, snapshot/spec drift, detached results, and parent immutability.

## Evidence And Observations

The five followup2 findings are closed on the canonical path:

- Zero-group comparisons now fail closed by iterating every comparison object ([models.py:1260](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/gates/models.py:1260>)); regression `test_comparative_trial_rejects_comparison_with_zero_group_associations`.
- B effect evidence without endpoint lineage now blocks; `endpoint_id` is required in B policy ([B-v1.yaml:204](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/policies/gates/B-v1.yaml:204>)); regression `test_b_effect_support_requires_explicit_comparison_endpoint_association_when_endpoint_is_omitted`.
- Raised B endpoint thresholds apply in direct and recompute paths ([evaluator.py:420](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/gates/evaluator.py:420>)); regressions `test_b_core_efficacy_respects_raised_unit_threshold` and `test_b_core_efficacy_respects_raised_unit_threshold_during_recompute`.
- Aggregation derives and enforces the complete rule-by-object matrix ([models.py:1752](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/gates/models.py:1752>)), including a missing second object; regression `test_aggregate_rejects_incomplete_spec_unit_result_set`.
- Normal satisfied-result construction requires unique immutable fact lineage ([models.py:735](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/gates/models.py:735>)); regression `test_aggregate_rejects_satisfied_result_without_distinct_fact_lineage`.
- Reusing an already-constructed batch under another snapshot or same-version changed spec is rejected ([models.py:1715](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/gates/models.py:1715>)); regression `test_aggregate_rejects_unit_result_batch_from_different_snapshot_or_spec`.

Other boundaries passed: mixed comparative/single-arm trials, exhaustive-search versus `study_design_single_arm`, multi-comparison/multi-endpoint group associations, per-group efficacy lineage, product/trial isolation, always-applicable units, result-bearing derivation, role-set identity, tighten-only overrides, registry-only C sufficiency, and conditional C fields.

### Current P0-1 — Batch validator bypass through `model_copy`

- Severity: P0.
- Location: batch validation ([models.py:1102](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/gates/models.py:1102>)); aggregation directly consumes the supplied batch ([models.py:1696](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/gates/models.py:1696>)).
- Reproduction:

```python
batch = GateEvaluationBatch.from_evaluation(
    spec=spec, snapshot=snapshot, unit_results=_matrix_results(spec, snapshot)
)
forged = batch.model_copy(update={"batch_key": "forged-key"})
aggregate_report_gates(
    spec=spec, snapshot=snapshot, batch=forged, contract_version="1"
)
```

Also, replacing a unit result’s `fact_version_ids` through nested `model_copy` was accepted.

- Actual: aggregation returned `passed`.
- Expected: reject the batch before aggregation because its key/content no longer validate.
- Impact: a critical report can pass with altered evidence lineage; `frozen=True` prevents assignment but does not prevent Pydantic’s unvalidated `model_copy`.
- Smallest repair boundary: revalidate the batch or invoke an explicit integrity check at the start of `aggregate_report_gates`; add an opaque/validated batch boundary rather than trusting the model instance.
- Regression: `test_aggregate_rejects_model_copy_tampered_batch_key_or_unit_results`.

### Current P0-2 — Exported detached-result constructor can re-stamp stale results

- Severity: P0.
- Location: `GateEvaluationBatch.from_evaluation` ([models.py:1127](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/gates/models.py:1127>)); both batch and aggregator are package exports ([__init__.py:68](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/gates/__init__.py:68>), [__init__.py:86](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/gates/__init__.py:86>)).
- Reproduction:

```python
raw_a = _matrix_results(spec_a, snapshot_a)

batch_b = GateEvaluationBatch.from_evaluation(
    spec=spec_a,
    snapshot=snapshot_b,
    unit_results=raw_a,
)
aggregate_report_gates(
    spec=spec_a, snapshot=snapshot_b, batch=batch_b, contract_version="1"
)
# returned: passed

spec_b = _minimal_spec(_identity_unit(threshold=2))
batch_changed_spec = GateEvaluationBatch.from_evaluation(
    spec=spec_b, snapshot=snapshot_a, unit_results=raw_a
)
aggregate_report_gates(
    spec=spec_b, snapshot=snapshot_a,
    batch=batch_changed_spec, contract_version="1"
)
# returned: passed; unit threshold remained 1
```

- Actual: stale results were stamped with the new snapshot/spec identity and aggregated as `passed`.
- Expected: reject detached results or recompute them; the changed-threshold case must block.
- Impact: directly permits a critical report to pass from stale evidence or an old threshold, corrupting snapshot/spec lineage.
- Smallest repair boundary: make batch construction/aggregation evaluator-owned through an opaque provenance token or private canonical path. Matrix validation alone cannot prove that results came from the supplied snapshot/spec.
- Regression: `test_public_batch_constructor_rejects_detached_unit_results_from_changed_snapshot_or_spec`.

### Manager P2 classifications

- Context-free `ReportGateResult` loading remains P2. A same-report unknown unit is accepted by the model validator because it has no `GateSpec` context ([models.py:797](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/gates/models.py:797>)). The authoritative aggregator rejects unknown units and matrix drift ([models.py:1735](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/gates/models.py:1735>)); no direct load path appears in the inspected evaluator/coverage code. Regression: `test_context_free_report_gate_result_load_is_not_authoritative_for_unknown_unit`.
- Detached `GateEvaluationBatch.from_evaluation(...)` is escalated from P2 to P0 because the constructor and aggregator are exported and the probe creates a passed result under changed identity.

## Verification And Gaps

Canonical `evaluate_report` creates one batch and immediately aggregates that same batch ([evaluator.py:585](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/gates/evaluator.py:585>)); recomputation delegates through `evaluate_report` ([coverage.py:301](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/gates/coverage.py:301>).

The existing suite does not cover Pydantic `model_copy` tampering or exported detached-result construction. Those failures were found by read-only in-memory probes.

## Next Action For Parent Codex

Repair both P0 batch boundaries, add the two regression tests, then rerun the exact trio and full suite.

## Verdict

FAIL; P0=2; P1=0; P2=1
