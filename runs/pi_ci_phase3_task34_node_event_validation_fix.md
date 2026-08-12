# Execution Output: ci_phase3_task34 (Node-Event Validation Fix)

## Changed Behavior (bounded correction, reducer + GT11 only)

1. **`graph.node.completed` now validated under `GraphEventContractError` before any state mutation** (`_validate_node_completed` in `reducer.py`), matching the `GraphExecutor.complete_node` public boundary exactly:
   - `node_id` / `input_digest` / `completion_digest` nonblank strings; `outputs` is a dict; `scope` equals the declared NodeContract scope; shared nodes require `report_kind is None`, report/artifact nodes require exactly A/B/C;
   - output key set exactly equals declared typed outputs; completion predicate passes and `validate_typed_outputs` passes — contract/type errors wrapped as `GraphEventContractError`;
   - `completion_digest` recomputed from `{node_id, report_kind, input_digest, outputs}` with the same canonical JSON algorithm as `complete_node` (`json.dumps(ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"` → sha256) and required exact match;
   - expected event_id recomputed via `stable_id("graph-node-completed", project_id, run_id, node_id, report-or-shared, input_digest)` from the event envelope and required exact match; expected idempotency key recomputed and required exact match.
   A raw schema-valid `gate`/A event with `gate_passed="YES"`, `failures="not-a-list"`, `evidence_digest=""` (the verifier's reproduction) now raises `GraphEventContractError` in `state()`/`replay()` and writes nothing into `gate.A`.
2. **Registry/node-contract version note** added at the validation site: event `schema_version=1.0` and current node contracts are the frozen baseline; future contract versions must carry a node-contract version and versioned resolver before changing contracts — replay validation is not weakened.
3. **Foreign non-graph no-op and the accepted-transition checks unchanged** (verified by the suite); unknown `graph.*` still fails closed with the typed error.
4. **GT11 extended (no new top-level test)** with isolated raw-EventStore cases, each asserting `CheckpointStore.replay` raises `GraphEventContractError` and saves no checkpoint: (1) wrong output types incl. the exact reproduction; (2) scope mismatch, invalid report kind, report kind on a shared node; (3) missing and extra output keys; (4) false completion predicate (None value); (5) drifted `completion_digest`; (6) drifted event_id; (7) drifted idempotency key. Plus one legal completion created via `complete_node` (resolve, shared) replayed by a **fresh** executor: `state()` shows the evidence reference, replay succeeds with the event in `applied_event_ids`, exactly one checkpoint — proving validation, not blanket rejection.

## Commands And Observations

- `uv run pytest tests/graph/test_checkpoint_replay.py::test_replay_never_duplicates_publish_move_approve_or_delete -q` → `1 passed in 0.06s`.
- All eleven approved nodes individually → 11/11 `1 passed` (GT06: 23.49s).
- Exact suite `uv run pytest tests/graph/test_transition_matrix.py tests/graph/test_graph_node_contracts.py tests/graph/test_checkpoint_replay.py -q` → `11 passed in 23.33s`.
- Task 3.3 regression → `1 passed in 0.43s`.
- Full suite `uv run pytest -q` → `443 passed in 35.59s`.
- `uv run ruff check src tests` → `All checks passed!`.
- `uv run mypy src/ci_workflow/graph` → `Success: no issues found in 10 source files`.
- `uv build --out-dir <tmp>` → sdist + wheel; wheel contains all 12 `ci_workflow/graph/` entries; temp dir removed.
- `git status --porcelain` → no tracked modifications; only `src/ci_workflow/graph/`, `tests/graph/` and runner-managed untracked files; no commit/stage.

## Residual Uncertainty

- `_validate_node_completed` recomputes digests/identities against the current frozen contracts; a future contract change must ship the versioned-resolver mechanism documented in the comment before the table changes.
- The completion-digest recomputation relies on the JSON round-trip stability of `outputs` (executor computes from the pre-serialization dict; reducer from the parsed payload). All executor-written node outputs are JSON-stable (dict/list/str/bool/enum-serialized values), confirmed by the legal replay case; a hypothetical non-JSON-stable output type would fail the digest check, which is fail-closed by design.
- Only `src/ci_workflow/graph/reducer.py` and `tests/graph/test_checkpoint_replay.py` were modified; exactly eleven approved top-level nodes remain. I do not claim acceptance; Codex and the original independent sessions own re-verification.
