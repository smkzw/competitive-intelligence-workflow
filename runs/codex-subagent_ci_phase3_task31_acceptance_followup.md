# Codex SubAgent Task: ci_phase3_task31_acceptance

## Boundary Check

Read-only review completed within the authorized file set. No source, test, Trellis, or runner-report files were modified. No network or security testing performed.

## Work Performed

- Reproduced/refuted all prior P0-1–P0-6 and P1-1–P1-3.
- Ran exact Task 3.1 tests: **115 passed**.
- Ran full suite with project-local TMPDIR, bytecode, and pytest cache disabled: **303 passed**.
- Ran additional adversarial probes for multi-trial scope, comparator cardinality, invalid numerics, aggregation, lineage, and duplicate evidence.

## Evidence And Observations

### Prior finding disposition

The original attacks for arbitrary A `NOT_APPLICABLE`, unjustified empty endpoints, direct inconsistent satisfied results, no-trial result-bearing derivation, ordinary empty-comparison proof, single-arm core efficacy, C conditional applicability, cross-trial endpoint/group/comparison bindings, and parent fingerprint mismatch are now covered by passing regressions.

However, the following residual findings remain.

### P0-1 — Comparator-present B efficacy accepts one group

Location: `src/ci_workflow/gates/evaluator.py:313`; `policies/gates/B-v1.yaml:154`.

Concrete input:

```text
comparison_ids = ("comparison-1",)
group_ids = ("group-1",)
endpoint_ids = ("endpoint-1",)

one b_core_efficacy_endpoint binding:
  endpoint_id = endpoint-1
  group_id = group-1
  numeric_value = 12.5
```

A full synthetic B fixture with all other critical bindings populated returned:

```text
passed
b_core_efficacy_endpoint: satisfied, satisfied_count=1, threshold=1
```

Expected: blocked because a comparator-present trial lacks a distinct treatment/control group value.

Impact: B can pass with missing control efficacy evidence.

Smallest repair: require comparator-present endpoints to have distinct treatment and applicable-control group coverage, or require an explicit per-trial single-arm proof.

Regression: `test_b_core_efficacy_with_comparator_requires_distinct_treatment_and_control_group_values`.

### P0-2 — B efficacy accepts wrong-domain, planned, and non-finite numerics

Locations: `src/ci_workflow/gates/models.py:1163`; `src/ci_workflow/gates/models.py:553`; `policies/gates/B-v1.yaml:160`.

Concrete variants:

```text
fact_domain = SAFETY, observation_kind = OBSERVED_RESULT
fact_domain = EFFICACY, observation_kind = PLANNED_VALUE
numeric_value = float("nan")
```

Each returned:

```text
passed satisfied 1
```

Expected: only finite observed efficacy numerics may satisfy the efficacy unit.

Impact: invalid or non-efficacy data can directly satisfy a critical B gate.

Smallest repair: enforce unit-level fact-domain and observation-kind constraints; reject non-finite numeric values.

Regression: `test_b_core_efficacy_rejects_wrong_domain_planned_or_nonfinite_numeric_evidence`.

### P0-3 — Product-scoped evidence can cross product/trial lineage

Locations: `src/ci_workflow/gates/models.py:1077`; `src/ci_workflow/gates/evaluator.py:201`.

Concrete input:

```text
product-a -> trial-1
product-b -> trial-2

A bindings:
  object_id = product-a
  trial_id = trial-2
```

With valid bindings for both products, the full A result returned:

```text
passed 0 ()
```

Expected: reject because product A’s evidence belongs to product B’s trial.

Impact: wrong-trial evidence can trigger maturity/result-bearing state and produce a false A pass.

Smallest repair: validate product→trial ancestry for product-scoped bindings and result-bearing derivation.

Regression: `test_gate_evaluator_rejects_cross_product_trial_evidence_stitching`.

### P0-4 — Single-arm/comparator applicability is global, not per trial

Locations: `src/ci_workflow/gates/evaluator.py:255`; `src/ci_workflow/gates/evaluator.py:313`.

Concrete input:

```text
trial-1 has comparison-1
trial-2 has no comparison and no study_design_single_arm proof
trial-1 and trial-2 each have one endpoint and one group
```

A full B fixture returned:

```text
passed ()
b_treatment_control_identity: comparison-1 satisfied
b_core_efficacy_endpoint:
  endpoint-1 satisfied
  endpoint-2 satisfied
```

Expected: trial 2 must block or have an explicit per-trial single-arm proof.

Impact: a comparator-less trial can bypass the stricter single-arm boundary and silently omit applicable comparison evidence.

Smallest repair: bind comparison presence/emptiness to each trial and require `study_design_single_arm` evidence for each comparator-less trial.

Regression: `test_b_multitrial_requires_per_trial_comparator_or_single_arm_proof`.

### P0-5 — Caller can force an always-applicable A unit to NOT_APPLICABLE

Locations: `src/ci_workflow/gates/evaluator.py:1210`; `src/ci_workflow/gates/models.py:1290`.

Concrete reproduction:

```python
evaluate_unit_decision(
    always_applicable_identity,
    object_id="product-a",
    applicable=False,
    applicability_justified=True,
    bindings=(),
)
```

Actual:

```text
not_applicable False False
```

Such a result also aggregates to a passed report.

Expected: reject caller-supplied non-applicability for always-applicable units.

Impact: direct API callers can bypass mandatory A evidence.

Smallest repair: derive applicability inside the decision function, or assert that `always_applicable` units cannot receive `applicable=False`.

Regression: `test_evaluate_unit_decision_cannot_force_always_applicable_unit_to_not_applicable`.

### P0-6 — Malformed or context-incoherent results still aggregate to pass

Locations: `src/ci_workflow/gates/models.py:645`; `src/ci_workflow/gates/models.py:724`; `src/ci_workflow/gates/models.py:1290`; `schemas/gate-result.schema.json:105`.

Reproductions:

```text
SATISFIED, threshold=0, satisfied_count=0 -> passed
SATISFIED B unit aggregated as report A -> passed
NOT_APPLICABLE a_product_identity -> passed
EXTENSION_MISSING a_product_identity -> passed
```

A directly constructed `ReportGateResult(decision="passed", unit_results=[BLOCKED])` is also accepted.

Expected: reject malformed results or force a blocked decision.

Impact: malformed/deserialized results can bypass critical thresholds and create a false pass.

Smallest repair: enforce threshold/count bounds, report-kind/spec-unit correspondence, critical-unit applicability, and report decision consistency at aggregation/model/schema boundaries.

Regression: `test_aggregate_rejects_malformed_or_cross_report_unit_results`.

### P1-1 — Comparison effect evidence is not bound to an endpoint

Locations: `src/ci_workflow/gates/models.py:1087`; `policies/gates/B-v1.yaml:184`.

Concrete input:

```text
comparison-1 -> group-1
endpoint-2 -> group-2

binding:
  object_id = comparison-1
  comparison_id = comparison-1
  endpoint_id = endpoint-2
  group_id = None
  numeric_value = 5.0
```

Actual:

```text
passed satisfied 1 comparison-1
```

Expected: reject without an explicit comparison↔endpoint association.

Impact: effect support can be attributed to the wrong endpoint/comparison.

Smallest repair: add and validate explicit comparison–endpoint association edges.

Regression: `test_b_effect_support_rejects_cross_endpoint_comparison_binding`.

### P1-2 — Research-role-set changes are absent from the universe fingerprint

Locations: `src/ci_workflow/gates/models.py:832`; `src/ci_workflow/gates/models.py:475`.

Concrete reproduction:

```text
snapshot-1 research_role_set_id = research-roles-v1
snapshot-2 research_role_set_id = research-roles-v2
```

Actual:

```text
universe_summary_equal = True
recompute with snapshot-2 = passed
```

Expected: the changed role set must change the summary/key or cause recomputation rejection.

Impact: immutable recovery lineage is not bound to the research-role contract.

Smallest repair: include `research_role_set_id` in `compute_universe_summary` and recomputation identity checks.

Regression: `test_recompute_rejects_research_role_set_mismatch_and_binds_summary`.

### P1-3 — Raised thresholds can be satisfied by duplicate fact bindings

Locations: `src/ci_workflow/gates/models.py:1233`; `src/ci_workflow/gates/models.py:1269`.

Concrete input:

```text
unit.threshold = 2
binding-1.fact_version_id = same-fact-v1
binding-2.fact_version_id = same-fact-v1
```

Actual:

```text
satisfied 2 2 ('same-fact-v1', 'same-fact-v1')
```

Expected: one immutable fact version counts once; the unit remains blocked.

Impact: tighten-only overrides can be bypassed by replaying the same evidence.

Smallest repair: count distinct fact versions per unit, or reject duplicate fact-version bindings.

Regression: `test_threshold_counts_distinct_fact_versions_not_duplicate_bindings`.

## Verification And Gaps

- Exact Task 3.1 suite: **115 passed**.
- Full suite: **303 passed**.
- The passing suite does not cover the residual adversarial inputs above.
- C registry-only sufficiency was independently confirmed: full C result `passed`, with no Protocol/SAP bindings.
- C region/visit/operational behavior is correct for absent predicate → `NOT_APPLICABLE`, explicit predicate → blocking when missing, and supplied evidence → satisfied.
- This review is limited to gate acceptance; it is not clinical, visual, browser, or report-artifact acceptance.

## Next Action For Parent Codex

Do not accept Task 3.1. Repair all six P0 findings first, then add the listed regressions and rerun the exact and full suites. Address the three P1 lineage/scope issues before final acceptance.

## Verdict

FAIL; P0=6; P1=3; P2=0
