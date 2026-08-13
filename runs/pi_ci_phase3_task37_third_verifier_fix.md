All three findings closed with RED-first attacks, full verification green. Report for the runner to persist to `runs/pi_ci_phase3_task37_third_verifier_fix.md`:

---

# Execution Output:

## Boundary And Context Check

- Working dir: `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`. No writes outside it.
- Files changed (Task 3.7 allowlist + directly affected graph/gate/tests): `src/ci_workflow/graph/executor.py`, `src/ci_workflow/graph/reducer.py`, `src/ci_workflow/graph/state.py`, `src/ci_workflow/capabilities/scientific_qc.py`, `src/ci_workflow/qc/scientific.py`, `src/ci_workflow/gates/models.py`+`coverage.py` (unchanged this round), `schemas/gate-result.schema.json` (prior round), `tests/graph/_qc_authorization_fixture.py` (new test-only fixture), and tests: `test_scientific_qc_gate.py`, `test_scientific_qc_isolated_veto.py`, `test_transition_matrix.py`, `test_graph_node_contracts.py`, `test_partial_delivery.py`, `test_partial_delivery_blocked.py`, `test_checkpoint_replay.py`.
- No specs/plans/Trellis/context/prompts/review/metrics files edited. No commit/stage. No browser/visual/external/security work.
- Previously closed paths preserved: complete candidate digest in result key, spec/criteria binding, contradiction rules, typed node output, no-downstream veto.

## Work Performed (3 findings closed)

1. **Public self-issuance removed (P0).** `GraphExecutor.issue_scientific_qc_authorization()` is **deleted**; replaced by a private `_issue_scientific_qc_authorization(proof)` accepting only an opaque `_ScientificQcAuthorizationProof` (frozen dataclass holding validated `ScientificQcVerdict` + `ScientificQcCurrentContext` model instances — no raw authorization fields, no public factory). The executor recomputes every digest/binding from the proof itself, includes a deterministic `boundary_proof_digest` (recomputed from the fully validated inputs) and `qc_entry_epoch` in the event. The reducer's `_validate_qc_authorization` **recomputes `boundary_proof_digest` from the event payload and rejects mismatch** — a directly appended shape-correct event without the boundary-computed proof fails at EventStore-append/reducer/replay (`boundary_proof_digest 与载荷不匹配`). The only supported issuance path is `apply_scientific_qc_verdict` after full raw revalidation. Tests that previously called the public method now use the test-only fixture `tests/graph/_qc_authorization_fixture.py` (isolated from production). Attacks: public method absent (`hasattr` false); direct EventStore append + replay rejected; real boundary path passes.
2. **One-time consumption + epoch (P1).** Authorization carries `qc_entry_epoch` (object's count of `scientific_qc` entries). Executor `_qc_authorization_matches` rejects `authorization_already_consumed` (any prior accepted transition consuming the auth) and `authorization_epoch_mismatch`. Reducer folds `consumed_event_id` into the ledger and rejects reuse by a different event (same-event idempotent replay still valid), and increments epoch on each `scientific_qc` entry. Test: `scientific_qc → recovering → scientific_qc` then new request ID reusing the old authorization → rejected (`authorization_already_consumed`/`authorization_epoch_mismatch`). Normal replay, crash replay (checkpoint), and recovery-cycle reuse all covered.
3. **Semantic validation parity in production (P1).** `check_scientific_qc_verdict_semantics` now runs inside `_revalidate_verdict`, and a new `check_scientific_qc_review_bundle_semantics` runs inside `_revalidate_bundle`/`_revalidate_context` — both before any authorization is issued, raising `ScientificQcBoundaryError` on any violation. Both checkers now cover: duplicate `SourceRef.locators[].fragment_id` **even when locator details differ**, nested locator fragment ∈ same SourceRef.fragment_ids, top-level locator fragment binding, unique `source_version_id`/top-level locator `fragment_id`/`issue_id`, issue source/fragment binding, precise locator dimensions (≥1 of field/heading/page/table/row/column/paragraph/url, nonblank, page ≥1). The `SourceRef` Pydantic model also rejects nested dup/unbound at model layer. The package/schema verifier path uses the same boundary (schema validation in SQ02 tests + semantic checkers in production revalidation). Attacks: nested-dup with different details rejected by Pydantic (ValidationError), semantic checker (violations), and no authorization event is written.

## Artifacts And Evidence

- `executor.py` — `_ScientificQcAuthorizationProof`, private `_issue_scientific_qc_authorization`, `_qc_authorization_matches` (consumption + epoch), `_find_qc_authorization`.
- `reducer.py` — `_validate_qc_authorization` (boundary_proof_digest recompute), object-scoped ledger with `consumed_event_id`/`qc_entry_epoch`, transition consumption check, epoch increment on `scientific_qc` entry.
- `state.py` — `QC_AUTHORIZATIONS_KEY`, `QC_EPOCHS_KEY`.
- `scientific_qc.py` — semantic validation in revalidate; proof-based issuance.
- `qc/scientific.py` — `check_scientific_qc_review_bundle_semantics`, `_check_source_ref_semantics`, nested-dup model validator, semantic checkers extended.
- `tests/graph/_qc_authorization_fixture.py` — test-only issuance fixture.

## Commands And Observations

- **Repaired attack nodes individually** (7 collected): SQ01, SQ02, SQ03, SQ04[A/B/C], checkpoint replay — **7 passed**.
- **Exact Task 3.7 suite**: `uv run pytest tests/integration/test_scientific_qc_gate.py tests/graph/test_scientific_qc_isolated_veto.py tests/integration/test_no_draft_after_scientific_qc_rejection.py -q` → **13 passed**.
- **Affected executor/reducer/replay/gate/graph/node/checkpoint/partial/no-draft**: `tests/graph/ + test_scientific_qc_gate.py + test_no_draft_after_scientific_qc_rejection.py` → **26 passed**.
- **Ruff** (whole src + tests): `All checks passed!`
- **Strict mypy** (whole `src/ci_workflow/`): `Success: no issues found in 68 source files`.
- **Schema/package**: `test_package_manifest.py` → 1 passed; `uv run ci-workflow package verify --root .` → `PACKAGE_OK version=0.1.0a0 stage=phase-2-accepted`.
- **`git diff --check`** → clean.
- **Full suite**: **464 passed in 54.98s**.

## Blockers Or Missing Environment

- None functional. Honest limits (unchanged, documented): Python is not a hostile security boundary — the mechanical contract is that public APIs cannot mint authorizations (issuance is private + opaque proof), persisted events carry a deterministic boundary-proof digest recomputed by the reducer, and direct append without the proof fails. Producer identity remains orchestration-supplied; reviewer actor is bound explicitly. Durable issuer registry beyond the event stream is deferred (project/run-scoped event ledger is the current registry). P2 (external plan filenames absent from repo) stands as a documentation/path-tracking note, not a product defect.

## Rerun Requests Or Next Step

- No rerun needed. All 3 findings closed RED-first; exact 13, affected 26, full 464, Ruff/mypy/schema/package/diff clean. Codex and the isolated reviewer own final acceptance. Runner: persist this report to `runs/pi_ci_phase3_task37_third_verifier_fix.md`. No commit made.
