Continue the same Task 3.4 implementation session `019ff6c3-4c09-7000-a9bc-59e7ba5061c8`. An independent verifier reproduced one P1 in the crash-window path. Make only the bounded correction below; do not redesign or broaden scope.

Hard boundaries:

- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Edit only `src/ci_workflow/graph/executor.py`, `src/ci_workflow/graph/reducer.py`, and `tests/graph/test_checkpoint_replay.py`.
- Keep exactly the existing eleven approved top-level test nodes; extend GT11, do not add another test.
- Do not edit Trellis, context, prompts, runs, reviews, metrics, package metadata, other sources/tests, or Task 3.5+; do not stage or commit.
- Runner-managed output path: `runs/pi_ci_phase3_task34_side_effect_fix.md`. Never write it with tools.

Read these files only:

- `src/ci_workflow/graph/executor.py`
- `src/ci_workflow/graph/reducer.py`
- `tests/graph/test_checkpoint_replay.py`
- `src/ci_workflow/storage/event_store.py`
- `src/ci_workflow/storage/checkpoint_store.py`

Verified defect:

- `IdempotentSideEffects._delete` accepts an `artifact.delete` payload with `path` and no `target_identity`, deriving identity from `path`.
- `graph_reducer._side_effect_target` instead falls back to `approval_id` for every operation, so the same delete event raises `KeyError('approval_id')` before the side effect and can never checkpoint.

Required correction:

1. Define one shared, typed target-identity derivation used by both the reducer and side-effect executor. Operation-specific rules: `revision.approve` requires nonblank `approval_id`; `artifact.publish` and `artifact.move` require nonblank `target_identity`; `artifact.delete` uses nonblank `target_identity`, otherwise nonblank `path`. Missing/wrong-type fields fail closed with a graph-owned domain error, never bare `KeyError`.
2. Avoid an import cycle. A small shared helper/error in `executor.py` cannot be imported by reducer if executor imports reducer; place it in an already allowed neutral Task 3.4 module only if strictly necessary, but remain within the three-file edit boundary if possible. The preferred minimal option is a helper in `reducer.py` imported by executor, since reducer does not import executor.
3. Extend the approved GT11 node with a second, isolated temp project whose `artifact.delete` event contains only `path`. Replay must delete exactly once, record the same path identity in canonical state and side-effect ledger, and exact replay must not duplicate. Also assert malformed per-operation target payloads fail with the typed error rather than KeyError.
4. Run GT11, all eleven approved nodes, the exact three-file suite, full pytest, Ruff, strict graph mypy and package build. Return actual evidence and residual uncertainty. Codex and independent verifiers own acceptance.
