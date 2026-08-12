You are continuing the same Task 3.4 Pi session after Codex reviewed the actual implementation. Keep the existing route, reasoning context, allowed write scope, and no-commit boundary. This is a focused correctness repair, not a redesign.

Hard boundaries:

- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- You may edit only the already-created Task 3.4 graph source files and the three graph test files listed in `prompts/pi_ci_phase3_task34.md`.
- Do not edit Trellis, context, prompts, runs, reviews, metrics, package metadata, Task 3.1–3.3 files, or Task 3.5+ surfaces. Do not commit or stage.
- Runner-managed output path: `runs/pi_ci_phase3_task34_correctness_followup.md`. Never write it with tools; return the complete handoff to the runner.

Read these files only:

- `prompts/pi_ci_phase3_task34.md`
- `context/ci_phase3_task34_context.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- `src/ci_workflow/graph/types.py`
- `src/ci_workflow/graph/state.py`
- `src/ci_workflow/graph/transitions.py`
- `src/ci_workflow/graph/guards.py`
- `src/ci_workflow/graph/registry.py`
- `src/ci_workflow/graph/reducer.py`
- `src/ci_workflow/graph/executor.py`
- `src/ci_workflow/graph/definitions/new_report.py`
- `tests/graph/test_transition_matrix.py`
- `tests/graph/test_graph_node_contracts.py`
- `tests/graph/test_checkpoint_replay.py`
- `src/ci_workflow/storage/event_store.py`
- `src/ci_workflow/storage/checkpoint_store.py`
- `src/ci_workflow/ingestion/manual_inbox.py`

Codex found the following acceptance blockers. Repair all of them and add the checks inside the approved eleven nodes; there must still be exactly eleven top-level tests.

1. Restore the exact approved node IDs and file ownership from plan lines 783-795, verbatim:
   - transition file: `test_project_run_transitions_and_guards_match_v12`, `test_report_evidence_transitions_and_guards_match_v12`, `test_artifact_transitions_and_guards_match_v12`, `test_download_request_transitions_and_guards_match_v12`, `test_revision_approval_transitions_and_guards_match_v12`, `test_every_undeclared_transition_is_rejected_and_logged`;
   - node-contract file: `test_intake_preflight_universe_and_route_nodes_declare_complete_contracts`, `test_ingest_extract_resolve_and_gate_nodes_declare_complete_contracts`, `test_snapshot_analysis_format_and_acceptance_nodes_declare_complete_contracts`, `test_report_branches_share_evidence_without_sharing_gate_state`;
   - checkpoint file: `test_replay_never_duplicates_publish_move_approve_or_delete`.
   Move the current branch-isolation behavior into the approved GT10 node in `test_graph_node_contracts.py`; do not leave an extra top-level test in the checkpoint file.

2. A declared edge is not enough to accept a request. `GraphExecutor.submit` must fail closed and append one deterministic rejection event when:
   - the request trigger differs from the declared edge trigger;
   - the request `from_state` differs from the canonical current state for that family/object in this run;
   - the request run identity differs from the executor run.
   The first state for an unseen object is fixed and typed: project=`None`, report=`queued`, format=`queued`, download=`awaiting_user`, revision=`submitted`. Do not let callers self-assert any other start state. Keep undeclared edges classified as undeclared and audited.

3. Preserve replay semantics after adding current-state checks. An exact repeat of an already accepted or rejected `TransitionRequest` must return the existing event without re-evaluating against the now-changed state. The same request identity with any payload drift must raise `EventConflictError`. Bind a canonical request digest into the event and use it for this pre-check.

4. Test the legal path in order. Rewrite GT06 so it no longer accepts every declared edge against one object in arbitrary order. For each runtime source state, create/position a fresh object through a real declared path, then probe every missing edge; evidence families remain entirely non-mutable. Fold assertions for trigger mismatch, canonical-current-state mismatch, wrong executor run, exact replay and drift into the approved GT06 node. The GT10 branch test must initialize A/B from `queued -> collecting` before blocking/QC transitions.

5. Node completion event identity and idempotency key must include project ID and executor run ID. Two runs in the same project completing the same node with the same outputs must append two distinct valid events; exact replay in one run remains a no-op. `complete_node` must call its completion predicate and reject incomplete/empty declared outputs rather than checking names only. Add these assertions to the relevant approved GT07-GT09 node.

6. The graph shares the canonical EventStore with Task 3.1–3.3. `state()` and `replay()` must safely no-op business events not owned by the graph reducer, including `download_request_state_changed`, while continuing to validate and apply graph and the four declared side-effect events. Add a real unrelated `WorkflowEvent` to GT11 before replay and assert recovery succeeds and the event remains in the checkpoint lineage. Do not weaken errors for malformed graph-owned events.

7. Keep the literal v1.2 transition fixtures independent from production tables. The exact plan-node commands must each collect exactly one test and pass. Re-run the exact 3-file suite, Task 3.1–3.3 regression, full pytest, `ruff check src tests`, strict mypy for graph sources, and package build. Be explicit about any residual uncertainty; do not claim acceptance.

Return a compact report with changed behavior, exact commands/results, and remaining risks for Codex verification.
