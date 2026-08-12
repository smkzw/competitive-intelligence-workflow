# Execution Output: ci_phase3_task34

## Boundary And Context Check

- Working tree confirmed free of prior graph writes before starting: `src/ci_workflow/graph/` and `tests/graph/` did not exist.
- Read only the 11 permitted files; no other repo files opened. Modified only the 10 graph sources + 3 graph test files listed in the task boundary.
- No tracked file modified (`git status --porcelain` shows only `?? src/ci_workflow/graph/` and `?? tests/graph/` plus pre-existing untracked runner files). No commit, no staging, no Trellis/context/prompt/review/metrics changes. No external graph dependency added.
- v1.2 §10.2 semantics frozen from the spec + accepted Task 3.3 chain (`manual_inbox._DECLARED_TRANSITIONS`). Narrow fail-closed interpretations recorded in Blockers.

## RED Evidence By GT01–GT11

All 11 nodes ran individually against the absent graph implementation; every node failed with the real signal `ModuleNotFoundError: No module named 'ci_workflow.graph'`:

| Node | RED signal |
|---|---|
| GT01 project | FAILED - ModuleNotFoundError: No module named 'ci_workflow.graph' |
| GT02 report_evidence | FAILED - ModuleNotFoundError (same) |
| GT03 format_artifact | FAILED - ModuleNotFoundError (same) |
| GT04 download_chain | FAILED - ModuleNotFoundError (same) |
| GT05 revision_approval | FAILED - ModuleNotFoundError (same) |
| GT06 nine-family determinism | FAILED - ModuleNotFoundError (same) |
| GT07 node contracts | FAILED - ModuleNotFoundError (same) |
| GT08 typed io/completion | FAILED - ModuleNotFoundError (same) |
| GT09 read/write/retry/scope | FAILED - ModuleNotFoundError (same) |
| GT10 shared evidence isolation | FAILED - ModuleNotFoundError (same) |
| GT11 crash-window replay | FAILED - ModuleNotFoundError (same) |

## Work Performed

Test files (expectations are literal v1.2 fixtures inside tests; never imported from or derived from production tables):

- `tests/graph/test_transition_matrix.py` — GT01–GT06. Literal `LiteralEdge` fixtures per family with trigger + guard_id; `_assert_family_frozen` asserts `actual == fixture` (missing=0 extra=0), guard existence, missing-evidence rejection (`missing_evidence:`), valid-evidence pass, any-required-key-flipped rejection, literal contradiction-pair rejection. GT02 additionally pins QC accept→lock / fixable-veto→recovering / unfixable+exhausted→evidence_blocked. GT03 pins the 4-step chain + independent blocked/reopen + `delivery_ready→superseded`. GT04 pins the 8-edge Task 3.3 chain and asserts zero drift against `manual_inbox._DECLARED_TRANSITIONS`. GT05 pins validation-vs-user-approval separation (`validate.guard_id != approve.guard_id`), no-owner-decision rejection, approval-ID-required publish. GT06 iterates all nine families' full (from × to) Cartesian incl. `None` source, plus cross-enum foreign targets, same-state pairs; asserts evidence families never enter canonical state; asserts deterministic rejection event fields, replay-no-op, and `EventConflictError` on same-identity/different-payload.
- `tests/graph/test_graph_node_contracts.py` — GT07–GT09. Literal 14-node list; full-field completeness + `FrozenInstanceError` immutability; typed inputs/outputs + completion-predicate behavior (full declared outputs → True, empty/missing-one → False); read/write template vocabulary, scope↔writes consistency, retry ≥3 for route/ingest/extract/recovery/format (§10.4), side-effect class + scope vocabularies, 12 distinct per-report keys and absence of any shared `gate`/`snapshot`/`analysis`/`artifact` key.
- `tests/graph/test_checkpoint_replay.py` — GT10–GT11. GT10 mechanically executes shared resolve→shared `evidence` ledger, three gates reading the same `evidence_digest`, per-report gate/snapshot/analysis/artifact keys, and report-A block leaving report-B state untouched. GT11 executes publish/move/approve/delete against temp files + JSONL ledgers through a real crash window (side effect succeeds, checkpoint not saved), asserts exactly-once effects, 4-entry ledger, checkpoint equality on replay, and `EventConflictError` on same-key/different-payload.

Implementation (`src/ci_workflow/graph/`):

- `types.py` — frozen `DeclaredEdge`, `GuardResult`, pydantic-frozen `TransitionRequest` (request_id = stable idempotency identity), `TypedField`/`RetryPolicy`/`NodeContract`.
- `state.py` — evidence-family vs runtime-family registration, `EVIDENCE_LEDGER_KEY`, `REPORT_SCOPED_FAMILIES` × `A/B/C` scoped keys, `initial_state()`.
- `transitions.py` — five frozen runtime tables (50 edges: project 13, report 13, format 8, download 11, revision 8) built from enum values; `FAMILY_STATE_ENUMS` registers all nine families.
- `guards.py` — declarative `GuardSpec` evaluator: scope-mismatch (evidence-declared target_family/target_object_id), required_fields, required_true, required_any, contradiction pairs; deterministic reasons; 48 guard specs whose IDs match the fixtures exactly.
- `registry.py` — `TransitionRegistry` with constructor invariants (registered families, guard existence, no duplicate edges, zero edges for evidence families, no orphan guards), `TRANSITION_REGISTRY` singleton.
- `reducer.py` — `graph_reducer` handles accepted/rejected transitions, node completions (shared evidence-reference merge; report-scoped merge; artifact per-format slots), and side-effect ledger recording; deterministic, never mutates input state.
- `executor.py` — `GraphExecutor.submit` (declared-edge lookup → guard → acceptance/rejection event, both auditable; event_id + idempotency_key derive from request identity → replay no-op, drift → `EventConflictError` via EventStore), `complete_node` (contract-validated), `state()`, `replay()` over EventStore/CheckpointStore; `IdempotentSideEffects` with publish/move/approve/delete keyed by (idempotency_key, target identity), filesystem-idempotent ops + `state/side_effect_ledger.jsonl` + `state/approvals.jsonl`.
- `definitions/new_report.py` + `__init__.py` — 14 immutable node contracts (intake/preflight/universe/route/ingest/extract/resolve/gate/recovery/snapshot/scientific_qc/analyze/format/acceptance), each with versioned typed inputs/outputs, completion predicate, reads/writes, retry policy, declared errors, idempotency material, side-effect class, shared/report/artifact scope.
- `graph/__init__.py` — public API.

## Artifacts And Evidence

- Test files: `tests/graph/test_transition_matrix.py`, `tests/graph/test_graph_node_contracts.py`, `tests/graph/test_checkpoint_replay.py` (11 top-level GT01–GT11 node IDs).
- Sources: 10 files under `src/ci_workflow/graph/` as listed in the boundary.
- GT06/GT10/GT11 use `tmp_path` only; all probe directories created during RED runs were removed from the tree.

## Commands And Observations

- RED (pre-implementation), each node individually: `uv run pytest <file>::<node_id> -q` → 11/11 `ModuleNotFoundError: No module named 'ci_workflow.graph'` (real RED).
- Individual green: `uv run pytest <file>::<node_id> -q` → 11/11 `1 passed`.
- Exact suite: `uv run pytest tests/graph/test_transition_matrix.py tests/graph/test_graph_node_contracts.py tests/graph/test_checkpoint_replay.py -q` → `11 passed in 2.18s`.
- Task 3.3 regression: `uv run pytest tests/integration/test_download_request_transitions.py -q` → `1 passed in 0.44s`.
- Full pytest: `uv run pytest -q` → `443 passed in 18.39s`.
- Ruff: `uv run ruff check src/ tests/` → `All checks passed!`; `uv run ruff check src/ci_workflow/graph tests/graph` → clean. Repo-wide `uv run ruff check .` shows 35 diagnostics, all in pre-existing harness dirs (`.codebuddy/`, `.codex/`, `.cursor/`, `.trellis/`) — none in src/ or tests/, untouched.
- Strict mypy: `uv run mypy src/ci_workflow/graph` → `Success: no issues found in 10 source files`.
- Package validation: `uv build --out-dir <tmp>` → sdist + wheel built; wheel contains all 12 `ci_workflow/graph/` entries (10 modules + 2 package dirs).

## Blockers Or Uncertainty

- Narrow fail-closed interpretations (no second status family invented):
  - "任一未完成态" for project `→ blocked` and `→ complete` is expanded to the fixed source set `{running, awaiting_user, partially_delivered}` (not `partial_delivery_blocked`/`blocked`, which are terminal/delivery-bearing).
  - Supersede edges declared only where the fixed contract names them: report `snapshot_locked → superseded`, format `delivery_ready → superseded`.
  - The executor validates transitions against the declared-edge table (not the object's current reduced state); current-state conformance is the submitter's responsibility and is audited in the event payload. No requirement demanded current-state checking.
  - Guard scope check: evidence may optionally declare `target_family`/`target_object_id`; a declared scope disagreeing with the request fails closed (`scope_mismatch`) — covers "跨对象/跨 family" guard failure without forcing scope fields on all evidence.
- No unresolved blockers. GT06 runs ~460 event appends (~2s) — intentionally exhaustive.

## Recommended Codex Verification

1. Re-run the exact 3-file suite, Task 3.3 regression, full pytest, `ruff check src/ tests/`, `mypy src/ci_workflow/graph`, and `uv build`; confirm `git status` shows no tracked modifications and no files outside `src/ci_workflow/graph/`, `tests/graph/`.
2. Spot-check that test fixtures are literal (grep `LiteralEdge(` in the matrix test) and that production tables in `transitions.py` are not imported by tests.
3. Confirm the download-family drift assertion against `manual_inbox._DECLARED_TRANSITIONS` (GT04) — it intentionally imports the Task 3.3 constant only as a drift check, not as the expectation source.
4. Verify GT06's `EventConflictError` path and GT11's crash-window ledger counts are the assertions they appear to be (they are, per the executed outputs above).
