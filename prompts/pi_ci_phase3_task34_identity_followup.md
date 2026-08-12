Continue the same Task 3.4 Pi session and repair the remaining identity/type false-greens found by Codex. Keep the same model/session, write scope, no-commit boundary, architecture, and exactly eleven approved top-level test nodes.

Hard boundaries:

- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Edit only Task 3.4 graph sources and the three graph test files.
- Do not edit Trellis, context, prompts, runs, reviews, metrics, package metadata, Task 3.1–3.3, or Task 3.5+; do not stage or commit.
- Runner-managed output path: `runs/pi_ci_phase3_task34_identity_followup.md`. Never write it with tools.

Read these files only:

- `context/ci_phase3_task34_context.md`
- `src/ci_workflow/graph/types.py`
- `src/ci_workflow/graph/state.py`
- `src/ci_workflow/graph/reducer.py`
- `src/ci_workflow/graph/executor.py`
- `src/ci_workflow/graph/definitions/new_report.py`
- `tests/graph/test_transition_matrix.py`
- `tests/graph/test_graph_node_contracts.py`
- `tests/graph/test_checkpoint_replay.py`
- `src/ci_workflow/storage/event_store.py`
- `src/ci_workflow/storage/checkpoint_store.py`

Required focused repairs:

1. Wrong-run audit events must not poison the requested foreign run. All events produced by a `GraphExecutor` belong to `self.run_id`; a run-mismatch rejection records both `requested_run_id` and `expected_run_id` in payload but stores under the executor run. Its event/idempotency identity is anchored to the executor run, so a later legitimate executor for the requested run can process its own request normally. Exact replay/drift behavior remains deterministic. Fold this proof into GT06.

2. Enforce the project-root project identity. Once any canonical event in the project root establishes one project ID, transition and node-completion calls for another project fail closed rather than mixing project histories. A transition mismatch may append an audited rejection under the established project/run; node completion may raise before writing. Add a compact assertion in GT06/GT08 without creating a new test node.

3. `NodeContract.idempotency_material` declares `input_digest`; make `GraphExecutor.complete_node` require a nonblank `input_digest`. Build completion event ID and idempotency key from project/run/node/report-or-shared/input_digest, not output digest. Exact retry with the same input and same outputs at a later timestamp returns the original event; same input identity with changed outputs raises `EventConflictError`; different input digest may create a new completion. Two different runs remain distinct. Add all cases to GT08 and update every existing `complete_node` call.

4. Make output typing real rather than decorative. Add a small closed validator owned by `TypedField`/`NodeContract` for the output type vocabulary actually declared here: nonblank `str`, strict `bool`, JSON list/tuple of nonblank strings, evidence-reference list/tuple with nonblank `fragment_id` and 64-hex `sha256`, dictionaries, ReportKind/OutputFormat serialized enum values and their list/tuple forms. `complete_node` must reject a full-key output with wrong value type, including `gate_passed="yes"`, invalid evidence references and unknown format. The literal contract tests must use per-node valid typed output fixtures instead of filling every field with `"ok"`, and must flip each declared output to an invalid type inside GT07-GT09.

5. Foreign non-graph business events remain no-op, but any unknown event whose type starts with `graph.` must fail closed. The current final `else` is unreachable because the early membership test no-ops `graph.unknown`. Fix and prove inside GT11 by appending a separate malformed `graph.unknown` stream/project and asserting replay raises; do not contaminate the successful crash-window stream.

6. Re-run all eleven exact approved node commands, exact three-file suite, Task 3.1–3.3 regression, full pytest, Ruff, strict graph mypy and package build. Preserve literal transition fixtures and no external dependency. Report only actual results and residual uncertainty; Codex remains final verifier.
