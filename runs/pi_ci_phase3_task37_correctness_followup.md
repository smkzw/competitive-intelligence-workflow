All verification complete. Report for the runner to persist to `runs/pi_ci_phase3_task37_correctness_followup.md`:

---

# Execution Output:

## Boundary And Context Check

- Working dir: `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`. No writes outside it.
- Files touched this round (all directly affected Task 3.7 source/tests): `src/ci_workflow/qc/scientific.py`, `src/ci_workflow/capabilities/scientific_qc.py`, `src/ci_workflow/graph/definitions/new_report.py`, `src/ci_workflow/graph/state.py` (required by item 5: `report_scoped_key` validates family membership, so the new `qc.{report_kind}` write key needs `"qc"` in `REPORT_SCOPED_FAMILIES`), `schemas/scientific-qc-verdict.schema.json`, `tests/integration/test_scientific_qc_gate.py`, `tests/graph/test_scientific_qc_isolated_veto.py`, `tests/graph/test_graph_node_contracts.py`.
- No specs, plans, Trellis, prompts, run/review/metrics files edited. No commit/stage. No browser/visual/research/security work.
- Previously closed paths preserved: mandatory bundle/coverage/contract/source equality, veto disposition, exhaustion raw-revalidation, naked-boolean guard rejection, typed `QCVerificationReference` node output. Task 3.2 regression file untouched (6/6 pass).

## Work Performed (5 Codex findings closed)

1. **Strict SHA-256 digests.** `_sha256_digest()` (lowercase `^[0-9a-f]{64}$`) applied to `candidate_content_digest` + `coverage_digest` on `ScientificQcReviewBundle`, and `candidate_content_digest` + `coverage_digest` + `review_input_digest` on `ScientificQcVerdict`. Schema also carries `pattern: ^[0-9a-f]{64}$` on the three verdict digest properties. Real digests (recomputed from snapshot/bundle) preserved.
2. **Locator precision + source lineage.** `LocatorDetail` now requires ≥1 real retrievable dimension (field_path/heading/page/table/row/column/paragraph/url) with nonblank text; `page` is `Field(ge=1)`. `SourceRef.fragment_ids/claim_ids/fact_version_ids/locators` all `Field(min_length=1)` — a source with no claim/fact lineage cannot support acceptance.
3. **Mandatory current `criteria_version`.** `apply_scientific_qc_verdict` now requires `criteria_version: str` (keyword-only) and binds both `bundle.criteria_version` and `verdict.criteria_version` to it (analogous to coverage). All callers updated (12 SQ01 calls + 7 SQ04 calls + 3 SQ03 calls).
4. **Producer/reviewer identity separation.** `producer_id` (nonblank) added to `ScientificQcReviewBundle`, included in `input_digest` (it is a bundle field). Boundary rejects `b.producer_id == v.reviewer_id` (“审查者必须与候选快照生产者是不同身份”). SQ03 proves same-person rejection and distinct-person acceptance through the real boundary.
5. **Node write key.** `scientific_qc` node `writes` changed from `("snapshot.{report_kind}",)` to `("qc.{report_kind}",)`; `reads` stays `("snapshot.{report_kind}",)`. `state.REPORT_SCOPED_FAMILIES` gains `"qc"`. `test_graph_node_contracts.py` GT09 asserts `writes == ("qc.{report_kind}",)` and that the node writes none of snapshot/evidence/analysis/artifact keys; scoped-key count 12 → 15.

## Artifacts And Evidence

- `src/ci_workflow/qc/scientific.py` — `_sha256_digest`, `LocatorDetail` precision validator, `SourceRef` min_lengths, bundle `producer_id`, digest field validators.
- `src/ci_workflow/capabilities/scientific_qc.py` — required `criteria_version`, producer/reviewer identity check.
- `src/ci_workflow/graph/state.py` + `definitions/new_report.py` — `qc.{report_kind}` write family.
- `schemas/scientific-qc-verdict.schema.json` — digest `pattern` constraints.
- Tests — SQ01 cases 20–24 (digest/locator/lineage/criteria/producer attacks), SQ03 identity-separation boundary tests, GT09 write-set assertions.

## Commands And Observations

- **Targeted attack evidence** (direct script, pre-transition rejection): digest `"x"`/`"A"*64`/`"a"*63`/`"g"*64` → `SHA-256` rejected (8/8); role-only locator → `真实维度`; blank `field_path` → `文本不能为空`; `page=0` → `ge`; empty `claim_ids` → `item`. All fail before any graph transition.
- **Repaired nodes individually** (7 collected): `uv run pytest ...::test_snapshot_lock_requires_explicit_schema_valid_scientific_qc_acceptance ...::test_verdict_has_report_scope_snapshot_candidate_sources_issues_and_locators ...::test_scientific_qc_receives_artifact_and_criteria_not_worker_reasoning_context ...::test_recoverable_veto_routes_to_recovering_and_exhausted_veto_blocks_without_artifacts ...::test_snapshot_analysis_format_and_acceptance_nodes_declare_complete_contracts -v` → **7 passed**.
- **Exact Task 3.7 suite**: `uv run pytest tests/integration/test_scientific_qc_gate.py tests/graph/test_scientific_qc_isolated_veto.py tests/integration/test_no_draft_after_scientific_qc_rejection.py -q` → **13 passed**.
- **Directly affected graph/node/transition/checkpoint/partial-delivery regressions**: `uv run pytest tests/graph/test_graph_node_contracts.py tests/graph/test_transition_matrix.py tests/graph/test_checkpoint_replay.py tests/graph/test_partial_delivery.py tests/graph/test_partial_delivery_blocked.py -q` → **13 passed**.
- **Ruff** (9 changed files): `All checks passed!`
- **Strict mypy** (6 source files): `Success: no issues found in 6 source files`.
- **Schema/package manifest**: `tests/contract/test_package_manifest.py` → **1 passed**.
- **`uv run ci-workflow package verify --root .`** → `PACKAGE_OK version=0.1.0a0 stage=phase-2-accepted`.
- **`git diff --check`** → exit 0.
- **Full suite**: `uv run pytest -q` → **464 passed in 51.46s**.

## Blockers Or Missing Environment

- None. Only residual note: digest `pattern` in the JSON schema is declarative (runtime enforcement is the Pydantic field validator); both are consistent. `state.py` change is the single file beyond the original allowlist, required by item 5's write-key contract.

## Rerun Requests Or Next Step

- No rerun needed. Exact suite 13, graph regressions 13, full suite 464, Ruff/mypy/schema/package-verify/`git diff --check` all clean. Codex and the isolated reviewer own acceptance. Runner: persist this report to `runs/pi_ci_phase3_task37_correctness_followup.md`. No commit made.
