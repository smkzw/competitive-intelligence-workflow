# Quality Guidelines

> Code quality standards for backend development.

---

## Overview

Backend acceptance is fail-closed for evidence-to-report transformations. A green
model constructor is not an integrity proof when later code can receive Pydantic
instances produced by `model_copy(update=...)`.

---

## Forbidden Patterns

- Do not export a constructor/aggregator pair that accepts detached evaluated
  results and stamps a new evidence snapshot or rule fingerprint onto them.
- Do not trust `frozen=True` or construction-time validators at an authoritative
  aggregation boundary; `model_copy(update=...)` does not re-run validation.
- Do not accept report-gate results without independently deriving the complete
  `(unit_id, object_id)` matrix from the current `GateSpec` and closed universe.

---

## Required Patterns

- Public evaluation must be atomic: current rule + current closed snapshot +
  current fact bindings go in; one immutable report result comes out.
- Internal aggregate boundaries must re-derive content digests and identity keys
  from the instance's current serialized content before semantic aggregation.
- Rule content fingerprints, evidence snapshot identifiers, universe summaries,
  and distinct immutable fact lineage must all participate in validation.

---

## Testing Requirements

- Every authoritative Pydantic boundary needs a `model_copy` adversarial test.
- Changed-snapshot and same-version changed-rule tests must prove recomputation,
  not only key inequality.
- Public-surface tests must verify unsupported detached constructors are absent,
  while production call-site search verifies there is no alternate supported path.

---

## Code Review Checklist

- Does any public path accept pre-evaluated unit results?
- Does aggregation revalidate current content before reading semantic fields?
- Are thresholds and the complete object matrix derived from the current spec?
- Do parent results remain immutable during project-rule recomputation?
- Do exact attacks, full regression, lint, strict typing, and package verification pass?

## Scenario: Atomic evidence evaluation and batch-integrity revalidation

### 1. Scope / Trigger

- Trigger: adding or changing a gate evaluator, report result loader, evidence
  snapshot, project-rule override, or any intermediate Pydantic batch used before
  report acceptance.
- Prevents: stale unit results being re-stamped under a new snapshot or changed
  rule, and unvalidated `model_copy` mutations producing a false pass.

### 2. Signatures

Supported public evaluation signature:

```python
def evaluate_report(
    spec: GateSpec,
    snapshot: ApplicableUniverseSnapshot,
    bindings: Sequence[GateEvidenceBinding],
    *,
    contract_version: str,
) -> ReportGateResult: ...
```

Internal-only aggregation shape:

```python
def _aggregate_report_gates(
    *,
    spec: GateSpec,
    snapshot: ApplicableUniverseSnapshot,
    batch: _GateEvaluationBatch,
    contract_version: str,
) -> ReportGateResult: ...
```

`_GateEvaluationBatch`, `_aggregate_report_gates`, batch-key helpers, and detached
unit-result construction are not package-root exports.

### 3. Contracts

- `spec.spec_fingerprint` identifies rule content, not only version text.
- `snapshot` must be closed and carries `evidence_snapshot_id` and
  `universe_summary`.
- `batch_key` is derived from report kind, snapshot identifier, universe summary,
  rule fingerprint, and the ordered canonical digest of all unit results.
- The authoritative output derives identity from the current `spec` and
  `snapshot`; callers cannot supply replacement identity strings.

### 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| Forged batch key via `model_copy` | Raise `GateEvaluationError` before aggregation |
| Nested unit result changed without matching original key | Raise `GateEvaluationError` before aggregation |
| Batch snapshot differs from current snapshot | Reject as snapshot mismatch |
| Batch rule fingerprint differs from current spec | Reject as rule mismatch |
| Missing or extra `(unit_id, object_id)` result | Reject as incomplete matrix |
| Same-version rule raises threshold | Re-evaluate bindings; block when count is insufficient |
| New snapshot with the same object IDs | Re-evaluate and emit a new snapshot-bound result |

### 5. Good / Base / Bad Cases

- Good: `evaluate_report(current_spec, current_snapshot, current_bindings, ...)`
  evaluates units and aggregates in one call.
- Base: repeating the call with unchanged inputs yields the same deterministic
  result identity.
- Bad: constructing results under A, then asking an exported helper to stamp them
  as B. No supported public helper may provide this behavior.
- Bad: relying on `frozen=True` after `batch.model_copy(update=...)`.

### 6. Tests Required

- `test_aggregate_rejects_model_copy_tampered_batch_key_or_unit_results`
  asserts a valid internal batch passes, forged key and nested lineage changes
  fail, and the source batch bytes stay unchanged.
- `test_public_batch_constructor_rejects_detached_unit_results_from_changed_snapshot_or_spec`
  asserts the detached API is absent and public evaluation recomputes for a new
  snapshot and raised same-version threshold.
- Exact report-gate, report-specific, and override suites must remain green with
  the full repository regression.

### 7. Wrong vs Correct

#### Wrong

```python
old_results = evaluate_units(spec_a, snapshot_a, bindings)
batch_b = PublicBatch.from_evaluation(spec_b, snapshot_b, old_results)
return public_aggregate(spec_b, snapshot_b, batch_b)
```

#### Correct

```python
return evaluate_report(
    spec_b,
    snapshot_b,
    bindings,
    contract_version=contract_version,
)
```
