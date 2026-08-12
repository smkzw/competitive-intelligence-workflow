# Execution Output: ci_phase3_task34 (Side-Effect Fix Follow-up)

## Changed Behavior (bounded P1 correction)

1. **One shared, typed target-identity derivation.** `reducer.py` now owns `derive_side_effect_target(event_type, payload)` plus the graph-owned domain error `SideEffectTargetError(ValueError)`; `executor.py` imports and uses the same function (reducer does not import executor, so no import cycle). Rules: `revision.approve` requires nonblank `approval_id`; `artifact.publish`/`artifact.move` require nonblank `target_identity`; `artifact.delete` uses nonblank `target_identity`, otherwise nonblank `path`. Field missing or wrong type raises `SideEffectTargetError` — never a bare `KeyError`. Identities are whitespace-normalized (`" ".join(split())`), so reducer state, ledger, and executor agree byte-for-byte.
2. **Both consumers use the shared helper.** `graph_reducer`'s side-effect branch and `IdempotentSideEffects._publish/_move/_approve/_delete` all derive the identity via the shared function; the old divergent `_side_effect_target` (approval_id fallback for every op, source of the P1) is deleted.
3. **GT11 extended (no new top-level node).** Added an isolated temp project whose `artifact.delete` event contains only `path`: replay deletes exactly once, the side-effect ledger records `target_identity == "staging/old.txt"`, canonical state records the same path identity (`checkpoint.state["side_effects"]["staging/old.txt"]["op"] == "artifact.delete"`), and exact replay returns the same checkpoint with no duplicate ledger line or file re-deletion. Five malformed per-operation payloads (publish/move without `target_identity`, approve without `approval_id`, delete with neither, publish with non-string `target_identity`) each replay-fail with `SideEffectTargetError` instead of `KeyError`.

## Commands And Observations

- `uv run pytest tests/graph/test_checkpoint_replay.py::test_replay_never_duplicates_publish_move_approve_or_delete -q` → `1 passed in 0.14s`.
- All eleven approved nodes individually, `uv run pytest <file>::<node_id> -q` → 11/11 `1 passed` (GT06: 23.29s).
- Exact suite `uv run pytest tests/graph/test_transition_matrix.py tests/graph/test_graph_node_contracts.py tests/graph/test_checkpoint_replay.py -q` → `11 passed in 23.33s`.
- Task 3.3 regression `uv run pytest tests/integration/test_download_request_transitions.py -q` → `1 passed in 0.44s`.
- Full suite `uv run pytest -q` → `443 passed in 36.42s`.
- `uv run ruff check src/ci_workflow/graph tests/graph` → `All checks passed!`; `uv run ruff check src tests` → clean.
- `uv run mypy src/ci_workflow/graph` → `Success: no issues found in 10 source files` (needed `TypeGuard` for narrowing in `derive_side_effect_target`).
- Package build `uv build --out-dir <tmp>` → sdist + wheel built; wheel contains all 12 `ci_workflow/graph/` entries; temp dir removed.
- `git status --porcelain` → no tracked modifications; untracked only `src/ci_workflow/graph/`, `tests/graph/` and runner-managed files. No commit/stage.

## Residual Uncertainty

- `derive_side_effect_target` normalizes identities with whitespace collapse; the existing GT11 success-stream identities are unaffected (no interior whitespace). Paths with surrounding whitespace would be normalized before `_relative` resolves them — deterministic and consistent across reducer/executor, but a caller-supplied path with meaningful whitespace would be altered; flagged for Codex.
- `_approve` still reads `decision` via `payload["decision"]` (`str`); the required fix scope was target-identity fields only, so a payload missing `decision` would raise `KeyError` — outside the verified defect, not changed.
- Only `executor.py`, `reducer.py`, `tests/graph/test_checkpoint_replay.py` were modified; exactly eleven approved top-level nodes remain. I do not claim acceptance; Codex and independent verifiers own it.
