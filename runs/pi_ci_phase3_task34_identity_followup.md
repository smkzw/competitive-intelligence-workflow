# Execution Output: ci_phase3_task34 (Identity/Type Follow-up)

## Changed Behavior

All six identity/type false-greens repaired within the same architecture and exactly the same eleven approved top-level nodes (6+4+1; no new test nodes).

1. **Wrong-run audit events no longer poison the requested foreign run.** `submit` now anchors every event it produces to the executor: `event.run_id == self.run_id`, event_id = `stable_id("graph-transition", <established project>, self.run_id, family, object_id, request_id)`, idempotency key prefixed with `self.run_id`. A run-mismatch rejection records `requested_run_id`/`expected_run_id` in payload but stores under the executor run. GT06 proves: rejection `run_id == "run_gt06"`, payload carries both ids, the object is absent from the executor's state, and a later legitimate executor (`run_id="run_other"`) processes its own request normally and reaches `running`. Exact replay/drift remain deterministic (pre-check by anchored event_id + `request_digest`).
2. **Project-root project identity enforced.** `_established_project()` scans the canonical store; once established, `submit` for another project appends an audited `project_mismatch` rejection under the established project/run (payload `requested_project_id`/`expected_project_id`), and `complete_node` raises before writing. GT06 asserts the rejection fields and that the store never mixes projects (`{project_id} == {"p_gt06"}`); GT08 asserts the node-completion raise. Mixed-project stores fail closed (`_established_project` raises).
3. **`complete_node` identity keyed by `input_digest`.** `input_digest` is now a required nonblank parameter; event_id and idempotency key are `project_id + run_id + node_id + report-or-shared + input_digest` (not output digest). GT08 proves: blank `input_digest` raises; two runs in the same project with the same input/output append two distinct events; exact retry with the same input+outputs at a later timestamp returns the original event with no new append; same input identity with changed outputs raises `EventConflictError`; a different input digest appends a new completion. All `complete_node` call sites in GT08/GT10 updated.
4. **Output typing is real.** `types.validate_typed_outputs` implements a closed vocabulary (nonblank `str`, strict `bool`, list/tuple of nonblank strings, evidence-reference list with nonblank `fragment_id` + 64-hex `sha256`, dicts, ReportKind/OutputFormat serialized values and list forms; unknown type declarations raise). `complete_node` validates after predicate; GT07–GT09 use literal per-node typed output fixtures and flip every declared output to an invalid type; GT08 additionally drives `gate_passed="yes"`, invalid evidence references and unknown format through `complete_node` (all rejected with `输出类型`).
5. **Unknown `graph.*` events fail closed.** The reducer's early membership test now distinguishes: any event type starting with `graph.` that is not owned raises `ValueError`; non-graph business events (e.g. `download_request_state_changed`) still no-op. GT11 appends a malformed `graph.unknown` event to a separate project root and asserts `checkpoints.replay` raises (`未知图事件类型`), while the successful crash-window stream keeps its foreign event in the checkpoint lineage.
6. Full verification re-run (below). Literal v1.2 fixtures preserved; no external dependency; no commit/stage; no tracked modifications.

## Commands And Observations

- Collect: `uv run pytest tests/graph/ -q --collect-only` → exactly the 11 approved node IDs.
- Each approved plan node individually, `uv run pytest <file>::<node_id> -q` → 11/11 `1 passed` (GT06: 22.55s).
- Exact suite `uv run pytest tests/graph/test_transition_matrix.py tests/graph/test_graph_node_contracts.py tests/graph/test_checkpoint_replay.py -q` → `11 passed in 22.93s`.
- Task 3.3 regression `uv run pytest tests/integration/test_download_request_transitions.py -q` → `1 passed in 0.43s`.
- Full suite `uv run pytest -q` → `443 passed in 34.81s`.
- `uv run ruff check src tests` → `All checks passed!`; `uv run ruff check src/ci_workflow/graph tests/graph` → clean.
- `uv run mypy src/ci_workflow/graph` → `Success: no issues found in 10 source files`.
- Package build `uv build --out-dir <tmp>` → sdist + wheel built; wheel contains all 12 `ci_workflow/graph/` entries; temp dir removed.
- `git status --porcelain` → no tracked modifications; untracked only `src/ci_workflow/graph/`, `tests/graph/` and runner-managed files; no probe directories left.

## Residual Uncertainty

- The approved plan file's lines 783–795 are not present in the repo; node IDs applied verbatim from the follow-up prompt, with `recovery` grouped into GT08 and `scientific_qc` into GT09 per the original task contract's group wording ("ingest/extract/resolve/gate/recovery", "snapshot/QC/analyze/format/acceptance").
- Check orders (documented in code): `submit` = replay pre-check → project identity → run identity → undeclared → trigger → current state → guard; `complete_node` = input_digest nonblank → scope/report_kind → project identity → names → predicate → typed validation → write. A wrong-project call therefore raises before any output validation, and malformed outputs on a fresh store raise at predicate/type stage.
- `_established_project` raises on a store that already mixes projects (corruption fail-closed); the GT06 store assertion confirms the executor never creates such a mix.
- `input_digest` is normalized (whitespace-collapsed) and the normalized value is used in the identity; retry comparison ignores `occurred_at`/`actor` via the stored `completion_digest` (node/report_kind/input_digest/outputs), matching the required later-timestamp semantics.
- GT06 runtime grew to ~22.5s (each submit re-scans the store for established project + event pre-check); acceptable for the baseline local executor, flagged for Codex.

## Recommended Codex Verification

Re-run the exact suite, the 11 per-node commands, Task 3.3 regression, full pytest, `ruff check src tests`, `mypy src/ci_workflow/graph`, and `uv build`; confirm `git status` shows no tracked modifications. Spot-check: GT06's run-mismatch rejection carries `run_id == "run_gt06"` and the legit `run_other` executor reaches `running`; GT08's later-timestamp retry returns the original completion event while output drift raises `EventConflictError`; GT11's malformed `graph.unknown` replay raises and the successful stream retains the foreign event in `applied_event_ids`. I do not claim acceptance; Codex remains final verifier.
