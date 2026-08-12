Continue the same Task 3.4 implementation session `019ff6c3-4c09-7000-a9bc-59e7ba5061c8`. The two independent verifiers disagreed about one remaining boundary; Codex as final authority classifies it P1 and requires the stricter deterministic behavior below.

Hard boundaries:

- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Edit only `src/ci_workflow/graph/reducer.py` and `tests/graph/test_checkpoint_replay.py`; if a type import is needed, use existing Task 3.4 modules without editing them.
- Keep exactly eleven approved top-level tests; extend GT11 only.
- Do not edit Trellis, context, prompts, runs, reviews, metrics, package metadata, other files, or Task 3.5+; do not stage or commit.
- Runner-managed output path: `runs/pi_ci_phase3_task34_reducer_validation_fix.md`. Never write it with tools.

Read these files only:

- `src/ci_workflow/graph/reducer.py`
- `src/ci_workflow/graph/registry.py`
- `src/ci_workflow/graph/state.py`
- `src/ci_workflow/graph/guards.py`
- `src/ci_workflow/graph/executor.py`
- `tests/graph/test_checkpoint_replay.py`
- `src/ci_workflow/storage/event_store.py`
- `src/ci_workflow/storage/checkpoint_store.py`

Verified boundary:

- `EventStore` is shared with Task 3.1–3.3 and is the canonical project truth. A caller can append a structurally valid `graph.transition.accepted` without using `GraphExecutor.submit`.
- The current reducer accepts that event solely by event type/family and writes `to_state`, so a forged `queued -> snapshot_locked`, trigger mismatch, current-state mismatch, or false guard can become canonical after `state()`/`replay()`.
- Task 3.4 requires the deterministic control graph itself, not only a safe submit wrapper. The reducer therefore must fail closed on malformed or forged graph-owned accepted events.

Required correction:

1. Add a typed graph-event contract error (subclass of `ValueError`) in `reducer.py`.
2. Before applying `graph.transition.accepted`, validate from the event payload:
   - all required fields have correct closed types: family/object_id/to_state/trigger/guard_id/request_digest are nonblank strings, `from_state` is string or None, `guard_evidence` is a dict;
   - family is a registered runtime family, to/from values belong to that family/default contract;
   - `(family, from_state, to_state)` is a declared edge;
   - trigger and guard_id exactly match that edge;
   - current state in the reducer input for family/object equals from_state, using `FAMILY_DEFAULT_STATES` for an unseen object;
   - re-evaluating the declared guard over `guard_evidence` for that family/object returns allowed.
   Any failure raises the typed error before mutating state. Do not re-validate foreign non-graph events; they remain no-op. Unknown `graph.*` remains fail-closed.
3. The registry/guard version concern is not solved by weakening replay. This task's event `schema_version=1.0` and current registry are the frozen baseline. Leave an explicit code comment that a future registry version must carry a transition-contract version and versioned registry resolver before changing the table.
4. Extend GT11 with isolated raw EventStore cases: forged undeclared accepted edge; legal edge with wrong trigger; legal edge with false/missing guard; legal edge whose from_state mismatches already-reduced current state; wrong guard_id; wrong family-state value/type. Each `state()` or `CheckpointStore.replay()` must raise the typed graph-event error and save no checkpoint. Include one raw, fully legal accepted event that does replay successfully, proving this is validation rather than blanket rejection.
5. Re-run GT11, all eleven approved nodes, exact suite, full pytest, Ruff, strict graph mypy and package build. Report actual results and any residual uncertainty. Codex and the original independent sessions will re-verify.
