# Execution Output: ci_phase3_task34 (Correctness Follow-up)

## Changed Behavior

All seven Codex blockers repaired inside the approved 11-node structure (6 transition + 4 node-contract + 1 checkpoint; no extra top-level tests).

1. **Approved node IDs restored verbatim** (file ownership per follow-up): transition file now has `test_project_run_transitions_and_guards_match_v12`, `test_report_evidence_transitions_and_guards_match_v12`, `test_artifact_transitions_and_guards_match_v12`, `test_download_request_transitions_and_guards_match_v12`, `test_revision_approval_transitions_and_guards_match_v12`, `test_every_undeclared_transition_is_rejected_and_logged`; node-contract file has `test_intake_preflight_universe_and_route_nodes_declare_complete_contracts`, `test_ingest_extract_resolve_and_gate_nodes_declare_complete_contracts`, `test_snapshot_analysis_format_and_acceptance_nodes_declare_complete_contracts`, `test_report_branches_share_evidence_without_sharing_gate_state`; checkpoint file has exactly one test, `test_replay_never_duplicates_publish_move_approve_or_delete`. Branch-isolation behavior moved into the node-contract GT10.
2. **`GraphExecutor.submit` now fails closed** with a deterministic rejection event for: run identity mismatch (`run_mismatch` + `expected_run_id`), undeclared edge (`undeclared_transition`, kept audited), trigger mismatch (`trigger_mismatch` + `expected_trigger`), canonical-current-state mismatch (`current_state_mismatch` + `expected_state`), and guard failure. Typed default start states (`state.FAMILY_DEFAULT_STATES`: project=None, report=queued, format=queued, download=awaiting_user, revision=submitted) are the only legal unseen-object states; callers cannot self-assert another start.
3. **Replay pre-check**: a canonical `request_digest` (sha256 of the full request JSON) is bound into both accepted and rejected event payloads; `submit` scans existing events by deterministic event_id first — exact repeat returns the existing event without re-evaluating against changed state; same request identity with any payload drift raises `EventConflictError`.
4. **GT06 rewritten to the legal-path protocol**: for every runtime (from × to) pair a fresh object is first positioned to `from` through a real declared path (BFS over the test's own literal GT01–GT05 fixtures — no production tables), then the edge is probed; evidence families stay fully non-mutable. Trigger mismatch, current-state mismatch, wrong run, guard-failed (missing evidence), scope mismatch, exact replay, and drift are all folded into GT06. GT10 initializes A/B via real `queued -> collecting` transitions before blocking/QC.
5. **`complete_node` identity now includes project ID + run ID** (event_id and idempotency_key), so two runs in the same project completing the same node with the same outputs append two distinct valid events, while exact replay in one run stays a no-op; `complete_node` now invokes the completion predicate and rejects incomplete/empty declared outputs (asserted in GT08).
6. **Reducer no-ops foreign business events** (e.g. `download_request_state_changed`) while still strictly validating graph-owned events; GT11 appends a real unrelated `WorkflowEvent` before replay and asserts recovery succeeds and the event remains in checkpoint lineage (`applied_event_ids`, `last_sequence == 5`, `event_stream_digest == store.stream_digest()`).
7. Literal v1.2 fixtures remain independent of production tables (GT01–GT05 assertions unchanged; GT06 paths derive only from the test's literal fixtures).

## Commands And Observations

- `uv run pytest tests/graph/ -q --collect-only` → `11 tests collected` with exactly the 11 approved node IDs (6+4+1).
- Each approved plan-node individually, `uv run pytest <file>::<node_id> -q` → 11/11 `1 passed` (GT06: 16.74s).
- Exact suite `uv run pytest tests/graph/test_transition_matrix.py tests/graph/test_graph_node_contracts.py tests/graph/test_checkpoint_replay.py -q` → `11 passed in 17.06s`.
- Task 3.3 regression `uv run pytest tests/integration/test_download_request_transitions.py -q` → `1 passed in 0.44s`.
- Full suite `uv run pytest -q` → `443 passed in 28.78s`.
- `uv run ruff check src tests` → `All checks passed!`; `uv run ruff check src/ci_workflow/graph tests/graph` → clean.
- `uv run mypy src/ci_workflow/graph` → `Success: no issues found in 10 source files`.
- Package build `uv build --out-dir <tmp>` → sdist + wheel built; wheel contains all 12 `ci_workflow/graph/` entries; temp out-dir removed.
- `git status --porcelain` → no tracked modifications; untracked only `src/ci_workflow/graph/`, `tests/graph/`, and the pre-existing runner-managed files. No commit, no staging; no probe directories left (`logs/` contains only pre-existing `agent_health`).

## Remaining Risks / Uncertainty

- The approved plan file's lines 783-795 are not present in the repo (grep across `plans/` and the workspace found the node IDs only in the follow-up prompt), so the IDs were applied verbatim from the follow-up; node-grouping of `recovery` into GT08 and `scientific_qc` into GT09 follows the original task contract's group wording ("ingest/extract/resolve/gate/recovery", "snapshot/QC/analyze/format/acceptance"), since the approved names enumerate 4+4+4 headline nodes over 14 contracts.
- Check order in `submit` is fixed: replay pre-check → run identity → undeclared edge → trigger → canonical current state → guard. Consequently a foreign-run request for an undeclared edge classifies as `run_mismatch` (run checked before undeclared); a same-run undeclared request is `undeclared_transition`. Documented in the submit docstring.
- `run_mismatch` rejection events carry the request's own run_id (audit fidelity) plus `expected_run_id`; they do not affect the executor's state (filtered by run_id) but coexist in the shared store.
- `submit` recomputes reduced state per call (O(n) per submission); GT06 runs ~17s. Acceptable for the baseline local executor; flagged for Codex.
- A malformed graph-owned event (unknown graph event_type) still raises `ValueError` in the reducer; only non-graph event types no-op.

## Recommended Codex Verification

Re-run the exact suite, per-node commands, Task 3.3 regression, full pytest, `ruff check src tests`, `mypy src/ci_workflow/graph`, and `uv build`; confirm `git status` shows no tracked modifications and no files outside `src/ci_workflow/graph/` and `tests/graph/`. Spot-check GT06's positioning paths are built only from the test's literal fixtures and GT11's foreign event stays in `checkpoint.applied_event_ids`. I do not claim acceptance; Codex owns final verification.
