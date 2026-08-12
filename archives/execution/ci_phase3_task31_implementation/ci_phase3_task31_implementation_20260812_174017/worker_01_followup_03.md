All green. Final state: 49 passed, Ruff clean, mypy strict clean, package imports.

---

# Execution Output: ci_phase3_task31_implementation - worker_01

## Boundary And Context Check

- Re-read `AGENTS.md`, `runs/codex-subagent_ci_phase3_task31_acceptance_followup.md`, `implement.md`, `0011`, and the five owned artifacts (`models.py`, `evaluator.py`, `coverage.py`, both schemas, test file).
- Modified only `src/ci_workflow/gates/models.py`, `src/ci_workflow/gates/__init__.py` (additive), `schemas/gate-spec.schema.json`, `schemas/gate-result.schema.json`, `tests/unit/test_gate_evaluator.py`. Evaluator/coverage/policies/report tests untouched. Report returned inline.

## Work Performed

Implemented all nine kernel/model contracts (second-round P0-2/P0-3/P0-5/P0-6, P1-1/P1-2/P1-3):

1. **Per-trial design evidence** — `TrialDesignKind` (closed: `comparative`/`single_arm`) + `TrialDesignEvidence` (trial_id, kind, evidence_version_id, explanation_zh). Snapshot requires exactly one record per trial, none when no trials (model validator). Closure (`_assert_trial_design_closed`) enforces: comparative ⇒ ≥1 trial→comparison edge; single-arm ⇒ 0 comparison edges; every comparison ⇒ ≥2 distinct comparison→group associations, all within the comparison's trial. Design evidence is in the universe fingerprint.
2. **comparison→endpoint associations** — added `(comparison, endpoint)` to allowed/association edge sets; association edges may connect same-rank objects (rank guard relaxed for associations), duplicate-exact edges still rejected. `assert_bindings_in_universe` requires the exact comparison→endpoint edge when a binding carries both ids.
3. **Product→trial ancestry** — product-scoped bindings carrying `trial_id` must match the trial's unique product parent (rejects cross-product stitching), enforced in both `assert_bindings_in_universe` and `derive_result_bearing`.
4. **research_role_set_id in fingerprint** — added to `compute_universe_summary`, snapshot validation, and closure recompute; result keys change with role-set version.
5. **Non-finite numerics** — `GateEvidenceBinding.numeric_value` rejects NaN/±inf at model validation.
6. **Closed domain/kind allowlists** — `GateUnitSpec.allowed_fact_domains`/`allowed_observation_kinds` (unique, non-empty; defaults = full closed enum sets), schema-declared (optional), enforced in `evidence_binding_qualifies`.
7. **always_applicable guard** — `evaluate_unit_decision` raises `GateEvaluationError` for `applicable=False` on always-applicable units even with justification.
8. **Distinct fact-version counting** — threshold counts unique `fact_version_id`; duplicate bindings of one fact version count once; returned fact-version list is unique.
9. **Aggregation/model hardening** — `GateUnitResult.threshold ≥ 1`/`satisfied_count ≥ 0`; `aggregate_report_gates` requires the canonical `GateSpec` (rejects unknown/cross-report units, duplicate `(unit_id, object_id)`, `NOT_APPLICABLE` for always-applicable, `EXTENSION_MISSING` for critical); `ReportGateResult` model validator recomputes decision/applicable+blocked ID sets/summary/result key from stored identity fields and rejects inconsistent direct construction; schema mirrors decision↔blocked-contains and all mechanically expressible bounds.

## Artifacts And Evidence

- `models.py`: `TrialDesignKind`, `TrialDesignEvidence`, `ALL_FACT_DOMAINS`/`ALL_OBSERVATION_KINDS`, comparison→endpoint edges, per-trial design closure, product ancestry, finite-numeric validator, domain/kind enforcement, always-applicable guard, distinct-fact counting, canonical-spec aggregation, deterministic report validator.
- `gate-spec.schema.json`: `allowed_fact_domains`/`allowed_observation_kinds` properties.
- `gate-result.schema.json`: top-level `allOf` (blocked ⇒ contains blocked unit; passed ⇒ none).
- `__init__.py`: additive `TrialDesignEvidence`/`TrialDesignKind` exports.
- `tests/unit/test_gate_evaluator.py`: 10 exact new nodes + factory migration (design records, group-2 cardinality, role-set summary, canonical-spec aggregates, endpoint-variant/association graph updates).

## Commands And Observations

| Step | Command | Observation |
|---|---|---|
| RED | `pytest -q -p no:cacheprovider` (TMPDIR=`.pytest-tmp`) after test edits | Collection `ImportError: cannot import name 'TrialDesignEvidence'` — target contract missing. Behavioral attacks (P0-2/3/5/6, P1-1/2/3) were independently reproduced by the acceptance agent with locations; all now covered by the passing regressions. |
| GREEN | same file after implementation | **49 passed** (39 prior + 10 new) |
| Ruff | `ruff check models.py __init__.py test_gate_evaluator.py` | All checks passed (removed 1 unused import) |
| mypy | `mypy --strict models.py` | Success: no issues |
| Smoke | `python -c "import ci_workflow.gates"` + enum probe | ok; `TrialDesignKind` = `['comparative','single_arm']` |

## Blockers Or Missing Environment

None. Pytest requires `TMPDIR="$PWD/.pytest-tmp"` and `-p no:cacheprovider` (no writable system temp dir). Package-manifest contract is outside this worker's file ownership.

## Rerun Requests Or Next Step

Codex to rerun exact Task 3.1 + full suite after worker_02/03 migration. **Migration notes:**
- worker_02 (`evaluator.py`): `aggregate_report_gates` now takes `spec=` (canonical GateSpec) and drops `report_kind`/`spec_version`/`spec_fingerprint` args; snapshot factories must supply per-trial `trial_design_evidence` + `research_role_set_id` in summaries, give every comparison ≥2 in-trial groups, and never pass `applicable=False` for always-applicable units; tighten A/B numeric YAML units with `allowed_fact_domains`/`allowed_observation_kinds`.
- worker_03 (`coverage.py`): recompute identity now depends on role-set-aware summaries and spec fingerprints; factories need the same snapshot upgrades; `compute_universe_summary` gained required `research_role_set_id` and `trial_design_evidence` keyword args.
- Both: product-scoped bindings with `trial_id` must match the trial's product parent; bindings carrying both `comparison_id` and `endpoint_id` need an explicit comparison→endpoint association edge in the graph.
