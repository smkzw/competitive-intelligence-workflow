# Codex SubAgent Task: ci_phase3_task31_acceptance

## Boundary Check

Read-only review completed. No source, test, Trellis, or runner output files were modified or written.

## Work Performed

Reassessed all prior P0/P1 findings, inspected current gate models/evaluator/coverage/policies/schemas, ran adversarial probes, and independently ran:

- Exact Task 3.1 tests: `134 passed`
- Full suite with local TMPDIR/cache disabled: `322 passed`

## Evidence And Observations

Prior findings:

- P0-1: Refuted. B efficacy now requires every applicable group.
- P0-2: Refuted. Wrong domains, planned observations, and non-finite values do not qualify.
- P0-3: Refuted on the authoritative `evaluate_report`/`derive_result_bearing` paths; product→trial ancestry is enforced.
- P0-4: Refuted. Mixed comparative/single-arm trials are evaluated per trial.
- P0-5: Refuted. Always-applicable units reject forced `NOT_APPLICABLE`.
- P0-6: Original malformed-result cases are refuted, but additional aggregation false-green paths remain.
- P1-1: Not refuted; escalated to P0 below.
- P1-2: Refuted. Single-arm efficacy accepts its unique group without fabricating control.
- P1-3: Refuted. C registry-only evidence passes, and inactive conditional region/visit/operation remains non-applicable.

### P0-A — Comparison with zero associated groups bypasses closure

Location: `src/ci_workflow/gates/models.py:1113-1144`.

Reproduction: create a comparative snapshot containing `comparison-1`, but remove all `comparison-1 → group-*` edges.

Actual:

```text
assert_applicable_universe_closed(snapshot) -> accepted
C registry-only evaluation -> passed
```

Expected: reject the snapshot because every comparison must have at least two distinct in-trial groups.

Impact: an invalid comparative design can produce a passed critical C report.

Smallest repair: iterate over every `snapshot.comparison_ids`, including comparisons with zero group edges, and require at least two same-trial groups.

Regression: `test_comparative_trial_rejects_comparison_with_zero_group_associations`.

### P0-B — Comparison effect can pass without endpoint association

Locations: `src/ci_workflow/gates/models.py:1314-1321`; `policies/gates/B-v1.yaml:204-229`.

Concrete input:

```text
unit_id       = b_effect_difference_support
object_id     = comparison-1
comparison_id = comparison-1
endpoint_id   = None
trial_id      = trial-1
numeric_value = 5.0
fact_domain   = efficacy
observation   = observed_result
```

With all other B critical evidence valid:

```text
full B report -> passed
b_effect_difference_support -> satisfied
```

Expected: reject or block because the comparison effect lacks explicit comparison→endpoint lineage.

Impact: a critical B report can pass with an endpoint-unbound effect estimate.

Smallest repair: require non-null `endpoint_id` for `b_effect_difference_support` and always validate its explicit comparison→endpoint edge.

Regression: `test_b_effect_support_requires_explicit_comparison_endpoint_association_when_endpoint_is_omitted`.

### P0-C — Raised B endpoint thresholds are ignored

Location: `src/ci_workflow/gates/evaluator.py:538-544`.

Reproduction: raise `b_core_efficacy_endpoint.threshold` to `3`, provide two distinct group facts, and recompute through `recompute_report_result`.

Actual:

```text
parent -> passed
child spec threshold -> 3
child result threshold -> 2
child satisfied_count -> 2
child -> passed
```

Expected: child must be blocked because `2 < 3`.

Impact: an allowed tightening override can leave a critical B gate effectively unchanged.

Smallest repair: use `max(unit.threshold, len(required_groups))` in endpoint evaluation and ensure aggregation rejects results below the spec threshold.

Regression: `test_b_core_efficacy_respects_raised_unit_threshold_during_recompute`.

### P0-D — Aggregation accepts incomplete result sets

Location: `src/ci_workflow/gates/models.py:1527-1565`.

Reproduction:

```python
aggregate_report_gates(
    spec=full_b_spec,
    unit_results=(one_satisfied_b_trial_identity_result,),
    ...
)
```

Actual:

```text
passed; blocked_unit_ids=()
```

Expected: reject incomplete aggregation or synthesize blocked results for omitted critical units.

Impact: the exported report-producing aggregator can create a passed report while nearly all critical evidence is absent.

Smallest repair: aggregate only a complete `(unit_id, object_id)` matrix derived from the canonical snapshot, or make incomplete aggregation fail closed.

Regression: `test_aggregate_rejects_incomplete_spec_unit_result_set`.

### P0-E — Satisfied results can omit immutable fact lineage

Locations: `src/ci_workflow/gates/models.py:714-759`, `:1527-1565`.

Reproduction:

```python
GateUnitResult(
    unit_id="a_product_identity",
    report_kind=ReportKind.A,
    object_id="product-a",
    applicable=True,
    outcome=GateUnitOutcome.SATISFIED,
    blocking=False,
    threshold=1,
    satisfied_count=1,
    fact_version_ids=(),
)
```

Actual: aggregation returns `passed`.

A second probe with `threshold=2`, `satisfied_count=2`, and duplicate `fact_version_ids=("same-fact", "same-fact")` also returns `passed`.

Expected: reject because satisfied counts must be backed by distinct immutable fact versions.

Impact: fabricated or malformed persisted results can bypass evidence lineage and raised thresholds.

Smallest repair: enforce unique fact IDs and require satisfied counts to be supported by sufficient distinct fact lineage in `GateUnitResult` and aggregation.

Regression: `test_aggregate_rejects_satisfied_result_without_distinct_fact_lineage`.

## Verification And Gaps

The following requested boundaries were mechanically or adversarially verified:

- Multi-comparison/multi-endpoint group associations work; optional baseline/safety associations may be omitted, while explicit mismatches reject.
- B efficacy rejects missing endpoint lineage through the authoritative `evaluate_report` path, but the comparison-effect unit has the omission gap above.
- Missing evidence is distinct from reported zero.
- Empty endpoint classes produce blocked anchored results.
- Parent spec fingerprint mismatch, role-set mismatch, result key, and parent immutability tests pass.
- C registry-only evidence passes without Protocol/SAP; inactive conditional region/visit/operation is `NOT_APPLICABLE`.
- Domain/observation overrides are tighten-only, and ordinary duplicate fact bindings do not satisfy raised thresholds.

Cursor’s P2 observation is confirmed:

```text
ReportGateResult.model_validate(payload_with_same_report_unknown_unit_id)
-> accepted
```

Authoritative membership checking occurs in `aggregate_report_gates` at `models.py:1529-1538`, where a canonical `GateSpec` is available. `ReportGateResult._result_is_deterministically_consistent` at `models.py:781-832` has no `GateSpec` and therefore cannot verify unit membership. Since no separate persisted loader is present in the authorized source, this is a context-free value-object limitation, not a current P0/P1 false-green in the canonical evaluation path.

Suggested hardening regression: `test_report_gate_result_load_rejects_unknown_unit_id_with_canonical_spec`.

## Next Action For Parent Codex

Do not accept the current tree. Repair the five P0 paths, add the named regressions, then rerun the exact and full suites and repeat independent acceptance.

## Verdict

FAIL; P0=5; P1=0; P2=1
