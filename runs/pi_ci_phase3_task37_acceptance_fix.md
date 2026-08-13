All verification complete. Here is the acceptance-fix report for the runner to persist to `runs/pi_ci_phase3_task37_acceptance_fix.md`.

---

# Execution Output:

## Boundary And Context Check

- Working dir: `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`. No writes outside it.
- Repair scope (per Codex REVISE verdict + explicit authorization): `src/ci_workflow/capabilities/scientific_qc.py`, `src/ci_workflow/qc/scientific.py`, `src/ci_workflow/graph/guards.py`, `src/ci_workflow/graph/types.py`, `src/ci_workflow/graph/definitions/new_report.py`, `schemas/scientific-qc-verdict.schema.json`, `package-manifest.json` (surgical 1-line), and the two approved test files plus directly affected existing transition/node tests (`test_graph_node_contracts.py`, `test_transition_matrix.py`, `test_checkpoint_replay.py`, `test_partial_delivery.py`, `test_partial_delivery_blocked.py`).
- No specs, plans, Trellis, prompts, context, run/review/metrics files edited (except `context/ci_phase3_task37_context.md` which was already modified by the runner pre-session — untouched by me). No commit/stage. No browser/visual/research/security work.
- Task 3.2 public rejection behavior (`apply_scientific_qc_rejection` regression) preserved — 6/6 pass unchanged.

## Work Performed (8 Codex items closed)

1. **Mandatory review bundle.** `apply_scientific_qc_verdict` now requires `review_bundle` (dict or model); `None` → `审查包缺失`. Both bundle and verdict are revalidated from raw serialized content (`_strip_computed`). Boundary requires exact agreement among snapshot, gate result, current coverage, bundle, verdict on project, report kind/version, candidate snapshot ID/content digest, criteria version, gate result key, coverage ID/digest, source refs and locators. `bundle.input_digest` recomputed and `verdict.review_input_digest == bundle.input_digest` enforced. Tests: cases 3, 14, 15 (missing/tampered bundle, arbitrary review digest) + SQ03 real-boundary calls.
2. **Mandatory coverage.** `coverage_set_id`/`coverage_digest` are now required positional args (no `None` default); both bundle and verdict must match them. `verdict.contract_version` bound to `gate_result.contract_version`. Tests: cases 12–13.
3. **Mechanical source/issue consistency.** Verdict `source_refs` and `locators` must be identical to the validated bundle (model-level equality in boundary agreement tuple). Every issue's `source_version_id`/`fragment_ids` must exist in the reviewed refs (verdict model validator). `accepted` → zero blocking issues; `veto` → ≥1 blocking issue. Semantically empty/generic evidence rejected (empty source_refs/locators at model layer).
4. **Closed veto disposition.** Verdict gains `veto_disposition: Literal["recoverable","exhausted"] | None`. `accepted` must have `None`; `veto` must have exactly one. Recoverable veto rejects a supplied exhaustion record. Exhausted veto requires a raw-revalidated `DoubleExhaustionRecord` bound to same project/report kind; `model_copy`-forged role/content/digest fails revalidation. No-downstream asserted before and after transitions.
5. **Naked-boolean bypass closed.** The SQ04 forged object is now driven through `queued → collecting → scientific_qc` FIRST, then a direct transition with only `{"isolated_qc_accepted": True}` is submitted. Result: `graph.transition.rejected`, `reason=guard_failed`, `guard_id=g_report_scientific_qc_snapshot_locked`, `guard_reason=missing_evidence:qc_verdict_id`, state unchanged. Guards `g_report_scientific_qc_snapshot_locked` / `_recovering` / `_evidence_blocked` now require `required_fields=(qc_verdict_id, qc_verdict_digest, qc_candidate_snapshot_id, qc_candidate_content_digest, qc_review_input_digest)`; the capability emits this material (`_verdict_auth_evidence`) and no other producer exists. Directly affected transition/node tests updated coherently (GT02 valid evidence, contradiction test, GT10, checkpoint-replay, partial-delivery paths).
6. **Typed node output.** `scientific_qc` node output changed from `qc_verdict: str` to `QCVerificationReference` (closed type added in `graph/types.py` requiring a dict with the 5 auth keys, all non-blank). Node-contract fixture updated to the dict; `_INVALID_FLIPS["QCVerificationReference"] = "accepted"` proves a plain `"accepted"` string fails `validate_typed_outputs`.
7. **SQ03 strengthened.** Now exercises the real public boundary: valid bundle+verdict accepted through `apply_scientific_qc_verdict` with the object positioned at `scientific_qc`; candidate content digest byte-identical before/after; forbidden producer context (worker_reasoning, chain_of_thought, scratch_notes, prompt, log, task_context, mutable_callback, review_verdict) rejected; verdicts cannot carry rewritten claims (`extra="forbid"` + no claim fields).
8. **Manifest restored.** Reverted the 259-line formatting rewrite; `package-manifest.json` diff is exactly 1 insertion of the schema entry.

## Artifacts And Evidence

- `src/ci_workflow/qc/scientific.py` — verdict with `veto_disposition`; bundle with `locators`; mechanical issue-source consistency; digest determinism.
- `src/ci_workflow/capabilities/scientific_qc.py` — mandatory bundle/coverage, raw revalidation of all inputs, `_verdict_auth_evidence`, exhaustion revalidation.
- `src/ci_workflow/graph/guards.py` — 3 QC guards require auth material.
- `src/ci_workflow/graph/types.py` — `QCVerificationReference` closed output type.
- `src/ci_workflow/graph/definitions/new_report.py` — node output typed.
- `schemas/scientific-qc-verdict.schema.json` — regenerated with `veto_disposition` + `verdict_digest`.
- `tests/integration/test_scientific_qc_gate.py`, `tests/graph/test_scientific_qc_isolated_veto.py` — rewritten; `tests/graph/*` — coherent guard-evidence updates.

## Commands And Observations

- **Repaired nodes individually** (6 collected):
  `uv run pytest tests/integration/test_scientific_qc_gate.py::test_snapshot_lock_requires_explicit_schema_valid_scientific_qc_acceptance tests/integration/test_scientific_qc_gate.py::test_verdict_has_report_scope_snapshot_candidate_sources_issues_and_locators tests/graph/test_scientific_qc_isolated_veto.py::test_scientific_qc_receives_artifact_and_criteria_not_worker_reasoning_context tests/graph/test_scientific_qc_isolated_veto.py::test_recoverable_veto_routes_to_recovering_and_exhausted_veto_blocks_without_artifacts -v`
  → **6 passed** (SQ01, SQ02, SQ03, SQ04[A/B/C]).
- **Exact Task 3.7 suite**: `uv run pytest tests/integration/test_scientific_qc_gate.py tests/graph/test_scientific_qc_isolated_veto.py tests/integration/test_no_draft_after_scientific_qc_rejection.py -q` → **13 passed**.
- **Directly related regressions**: `uv run pytest tests/graph/test_graph_node_contracts.py tests/graph/test_transition_matrix.py tests/graph/test_checkpoint_replay.py tests/graph/test_partial_delivery.py tests/graph/test_partial_delivery_blocked.py -q` → **13 passed**.
- **Ruff** (12 changed files): `All checks passed!`
- **Strict mypy** (5 affected source files): `Success: no issues found in 5 source files`.
- **Package/schema**: `tests/contract/test_package_manifest.py` → **1 passed**.
- **`git diff --check`** → exit 0.
- **Full suite**: `uv run pytest -q` → **464 passed in 51.83s**.

## Blockers Or Missing Environment

- None. All required verification completed; the previously accepted attacks are now mechanically rejected (asserted on rejection reason + guard evidence, not merely state).

## Rerun Requests Or Next Step

- No rerun needed. Codex and the isolated reviewer own acceptance; the decisive anchors are the exact suite (13), related regressions (13), full suite (464), Ruff/mypy/schema clean, `git diff --check` clean, and `package-manifest.json` surgical 1-line diff. No commit made. Runner: persist this report to `runs/pi_ci_phase3_task37_acceptance_fix.md`.
