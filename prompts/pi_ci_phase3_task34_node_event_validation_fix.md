Continue the same Task 3.4 implementation session `019ff6c3-4c09-7000-a9bc-59e7ba5061c8`. Codex independently reproduced the same canonical-log trust defect for `graph.node.completed`; close it before verifier reruns.

Hard boundaries:

- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Edit only `src/ci_workflow/graph/reducer.py` and `tests/graph/test_checkpoint_replay.py`.
- Keep exactly eleven approved top-level tests; extend GT11 only.
- Do not edit Trellis, context, prompts, runs, reviews, metrics, package metadata, other sources/tests, or Task 3.5+; do not stage or commit.
- Runner-managed output path: `runs/pi_ci_phase3_task34_node_event_validation_fix.md`. Never write it with tools.

Read these files only:

- `src/ci_workflow/graph/reducer.py`
- `src/ci_workflow/graph/types.py`
- `src/ci_workflow/graph/definitions/new_report.py`
- `src/ci_workflow/graph/executor.py`
- `tests/graph/test_checkpoint_replay.py`
- `src/ci_workflow/domain/ids.py`
- `src/ci_workflow/storage/event_store.py`
- `src/ci_workflow/storage/checkpoint_store.py`

Direct reproduction from production code:

- A raw, schema-valid `graph.node.completed` for node `gate`, report A, with outputs `gate_passed="YES"`, `failures="not-a-list"`, `evidence_digest=""` is currently accepted by `GraphExecutor.state()` and writes those values into `gate.A`.
- `complete_node()` would reject this, but the shared EventStore is canonical; reducer validation cannot be weaker than the public execution boundary for graph-owned events that mutate canonical state.

Required correction:

1. Before `_apply_node_completed`, validate `graph.node.completed` payload under `GraphEventContractError`:
   - `node_id`, `input_digest`, `completion_digest` nonblank strings; `scope` equals the declared NodeContract scope; `outputs` is a dict;
   - shared nodes require `report_kind is None`; report/artifact nodes require exactly A/B/C;
   - output key set exactly equals declared typed outputs;
   - completion predicate passes and `validate_typed_outputs` passes; wrap any contract/type error as `GraphEventContractError`;
   - recompute completion digest from `{node_id, report_kind, input_digest, outputs}` using the same canonical JSON algorithm as `complete_node` and require exact match;
   - recompute expected event_id from envelope project/run + node/report/input and require exact match;
   - recompute expected idempotency key and require exact match.
   Validation must occur before state mutation. Future node-contract versions need a versioned resolver before current contracts change; document this, do not weaken replay.
2. Extend GT11 with isolated raw events proving rejection/no checkpoint for: wrong output types; scope/report mismatch; missing/extra output; false completion predicate; drifted completion digest; drifted event ID or idempotency key. Add one fully legal raw node-completed event (or one created through `complete_node` and then replayed by a fresh executor) that succeeds, proving no blanket rejection.
3. Keep foreign non-graph no-op and the new accepted-transition checks unchanged. Do not add tests outside GT11.
4. Re-run GT11, all 11 approved nodes, exact suite, full pytest, Ruff, strict graph mypy and package build. Return actual evidence; Codex and original independent sessions own acceptance.
