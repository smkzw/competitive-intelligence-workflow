# Codex SubAgent Task: ci_phase3_task31_acceptance

## Boundary Check

Read-only review completed within the authorized workspace and file set. No files were modified. Worker/manager claims were independently checked; final acceptance remains with parent Codex.

## Work Performed

- Read the approved contract, ADR, task plan, gate policies/schemas, implementation, tests, and worker handoffs.
- Attempted the exact Task 3.1 command; default pytest capture failed because no writable temporary directory exists.
- Ran the same three exact test files with `-s -p no:cacheprovider`: **100 passed**.
- Ran adversarial probes for B scope/numerics, A derivation and applicability, missing-versus-zero, C registry-only behavior, empty-object omission, and immutable overrides.

## Evidence And Observations

### P0-1 — B efficacy accepts one numeric as treatment/control coverage

Location: `policies/gates/B-v1.yaml:181`; `src/ci_workflow/gates/models.py:818`, `:856`.

Reproduction: supply a critical `b_core_efficacy_endpoint` binding with:

```text
object_id=endpoint-1
endpoint_id=endpoint-1
trial_id=trial-1
numeric_value=12.5
treatment_group=治疗组
control_group=安慰剂组
```

and valid bindings for the other critical B units. Actual output:

```text
B_ONE_NUMERIC satisfied 1 passed
```

Expected: blocked until distinct numeric treatment and applicable-control values are present. Group labels do not prove two numeric values.

Impact: directly allows a critical B report to pass with missing efficacy evidence.

Smallest repair boundary: model B efficacy as two role-distinct numeric bindings, or add a typed treatment/control pair validator and enforce it in the evaluator.

Regression test: `test_b_core_efficacy_requires_distinct_treatment_and_control_numeric_values`.

### P0-2 — Arbitrary `not_applicable` evidence satisfies always-applicable A units

Location: `policies/gates/A-v1.yaml:46`; `src/ci_workflow/gates/models.py:507`, `:803`; `src/ci_workflow/gates/evaluator.py:211`.

Reproduction: mark every always-applicable critical A unit as:

```text
disclosure_state=not_applicable
applicability_predicate_id=arbitrary_not_applicable
```

Actual output:

```text
A_ARBITRARY_NA satisfied passed ()
```

Expected: identity, mechanism, modality, developer, and indication fields must block unless a recognized versioned applicability rule proves non-applicability.

Impact: a critical A report can pass without core product evidence.

Smallest repair boundary: bind `not_applicable` to the evaluator’s recognized predicate and reject it for `always_applicable` units unless explicit applicability evidence exists.

Regression test: `test_a_always_applicable_critical_unit_rejects_unproven_not_applicable_binding`.

### P0-3 — Empty endpoint sets silently remove a critical B unit

Location: `src/ci_workflow/gates/models.py:732`; `src/ci_workflow/gates/evaluator.py:255`.

Reproduction: use:

```text
endpoint_ids=()
empty_set_justification="任意字符串，并非逐对象穷尽证据"
```

while retaining trial, comparison, and group objects and satisfying their remaining critical units.

Actual output:

```text
EMPTY_ENDPOINT_OMISSION passed 0
```

Expected: fail closed or create a blocked B result; the core efficacy unit must not disappear merely because an untyped string justifies an empty object class.

Impact: silently drops an applicable critical endpoint and allows a false-green B report.

Smallest repair boundary: require typed, evidence-backed empty-set proofs per object class and ensure required critical object classes produce a blocked result when unjustified or empty.

Regression test: `test_gate_evaluator_rejects_unjustified_empty_endpoint_set_and_does_not_drop_b_core_efficacy`.

### P0-4 — Flat IDs permit cross-trial/group/comparison evidence stitching

Location: `src/ci_workflow/gates/models.py:754`; `src/ci_workflow/gates/evaluator.py:114`.

Reproduction:

```text
trial_ids=(trial-1, trial-2)
endpoint_ids=(endpoint-1,)
comparison_ids=(comparison-1,)

binding:
  object_id=endpoint-1
  endpoint_id=endpoint-1
  trial_id=trial-2
```

with `endpoint-1` conceptually belonging to `trial-1`. Equivalent comparison and group bindings also pass.

Actual output:

```text
FLAT_PARENT_SCOPE satisfied satisfied
```

Expected: reject evidence whose parent trial does not match the endpoint/group/comparison parent.

Impact: critical B evidence can be attributed to the wrong trial or comparison, producing wrong per-trial conclusions.

Smallest repair boundary: represent trial→comparison/group/endpoint/timepoint parent edges in the universe snapshot, validate the full scope path, and include the relationship graph in the universe digest.

Regression test: `test_gate_evaluator_rejects_cross_trial_group_endpoint_and_comparison_bindings`.

### P0-5 — Override recomputation does not verify parent rule identity

Location: `src/ci_workflow/gates/coverage.py:241`; `src/ci_workflow/gates/models.py:700`.

Reproduction: create a blocked parent result from the full A spec, then pass a same-version/same-spec-ID but unrelated reduced parent/child spec pair to `recompute_report_result`.

Actual output:

```text
OVERRIDE_SPEC_IDENTITY blocked passed
```

Expected: reject before child evaluation because the supplied parent spec is not the spec that produced the parent result.

Impact: corrupts immutable lineage and can turn a blocked result into a passed child result.

Smallest repair boundary: bind results to an immutable spec content fingerprint, verify the parent spec fingerprint before recomputation, and include it in the result key or result record.

Regression test: `test_recompute_rejects_parent_spec_fingerprint_mismatch_and_preserves_blocked_parent`.

### P0-6 — Aggregation accepts inconsistent satisfied results

Location: `src/ci_workflow/gates/models.py:531`, `:580`.

Reproduction:

```python
bad = GateUnitResult(
    unit_id="a_product_identity",
    report_kind=ReportKind.A,
    object_id="product-a",
    applicable=True,
    outcome=GateUnitOutcome.SATISFIED,
    blocking=False,
    threshold=1,
    satisfied_count=0,
)
aggregate_report_gates(..., unit_results=(bad,))
```

Actual output:

```text
INCONSISTENT_RESULT_AGGREGATION passed () 0 1
```

Expected: reject the inconsistent result or force a blocked decision.

Impact: direct API use or deserialized malformed results can bypass the critical threshold.

Smallest repair boundary: add model/schema invariants linking outcome, blocking, threshold, and satisfied count; aggregate only validated results.

Regression test: `test_aggregate_report_rejects_satisfied_unit_below_threshold`.

### P1-1 — A result-bearing helper accepts evidence with no trial

Location: `src/ci_workflow/gates/models.py:949`; contrasting stricter logic is at `src/ci_workflow/gates/evaluator.py:191`.

Reproduction: observed numeric efficacy binding with `trial_id=None`.

Actual:

```text
derive_result_bearing(...) == True
check_result_bearing(...) == False
```

Expected: both derivations must be false without an eligible clinical trial.

Impact: inconsistent public derivation APIs can trigger A result-bearing state incorrectly.

Smallest repair boundary: centralize derivation and require non-null membership in the eligible-trial set.

Regression test: `test_derive_result_bearing_requires_eligible_trial_scope`.

### P1-2 — Single-arm core efficacy incorrectly requires a control group

Location: `policies/gates/B-v1.yaml:168`; `src/ci_workflow/gates/evaluator.py:222`.

Reproduction: single-arm snapshot with one endpoint and one treatment numeric, `control_group=None`, and no comparison IDs.

Actual output:

```text
SINGLE_ARM_CORE blocked 0 blocked
```

Expected: evaluate the unique study group without fabricating or requiring a control.

Impact: blocks valid single-arm/special-core B reports and makes recovery unreliable.

Smallest repair boundary: use conditional control requirements or a dedicated single-arm efficacy unit while retaining comparison-unit non-applicability.

Regression test: `test_b_single_arm_core_efficacy_accepts_unique_group_without_control`.

### P1-3 — C region/visit/operational applicability defaults to critical

Location: `policies/gates/C-v1.yaml:142`; `src/ci_workflow/gates/evaluator.py:224`.

Reproduction: provide all other C critical registry fields but no indication-specific rule or `c_region_visit_operational` binding.

Actual output:

```text
C_REGION_DEFAULT blocked blocked True
```

Expected: this field should be applicable only when the indication-specific GateSpec marks it critical; otherwise it should be explicitly non-applicable or non-blocking.

Impact: registry-only C reports can be falsely blocked by an unconfigured critical field.

Smallest repair boundary: require the indication rule set at evaluation time; remove the unconditional `True` fallback.

Regression test: `test_c_region_visit_operational_requires_explicit_indication_rule`.

Additional positive checks passed: missing evidence blocked while explicit zero satisfied; C registry-only evidence passed without Protocol/SAP; missing C core design evidence blocked.

## Verification And Gaps

- Exact Task 3.1 files: **100 passed** with capture/cache disabled.
- Unmodified exact command could not initialize pytest because the environment has no writable temporary directory.
- No full-suite rerun was performed.
- No project files were modified.

## Next Action For Parent Codex

Do not accept Task 3.1. Repair the six P0 findings first, add the listed regressions, then rerun the exact suite in a writable test environment. Review the three P1 scope/derivation issues before reassessment.

## Verdict

**FAIL; P0=6; P1=3; P2=0**
