# Execution Output: ci_phase3_task34 (Reducer Validation Fix)

## Changed Behavior (bounded P1 correction)

1. **Typed graph-event contract error** `GraphEventContractError(ValueError)` added in `reducer.py`; raised for malformed/forged graph-owned events, never a bare `KeyError`/generic error. Unknown `graph.*` event types now raise this typed error with the same message (`未知图事件类型`), so the existing GT11 assertion still holds.
2. **Full pre-apply validation of `graph.transition.accepted`** in `_validate_accepted_transition(state, event)`, executed before any state mutation:
   - closed types: `family`/`object_id`/`to_state`/`trigger`/`guard_id`/`request_digest` nonblank strings (whitespace-normalized), `from_state` string-or-None, `guard_evidence` dict;
   - family ∈ runtime families; `to_state`/`from_state` ∈ that family's state values (or `None`, per default contract);
   - `(family, from_state, to_state)` is a declared edge (`TRANSITION_REGISTRY.declared`);
   - `trigger` and `guard_id` exactly match that edge;
   - current state in the reducer input for family/object equals `from_state`, with `FAMILY_DEFAULT_STATES` for unseen objects;
   - declared guard re-evaluated over `guard_evidence` for that family/object must be allowed.
   Foreign non-graph events stay no-op; unknown `graph.*` stays fail-closed.
3. **Registry-version comment** added at the validation site: event `schema_version=1.0` and the current registry are the frozen baseline; a future registry version must carry a transition-contract version and a versioned registry resolver before the table changes, not weaken replay validation.
4. **GT11 extended (no new top-level test)** with isolated raw-`EventStore` cases, each asserting `CheckpointStore.replay` raises `GraphEventContractError` and saves no checkpoint: (1) forged undeclared edge `queued -> snapshot_locked`; (2) legal edge with wrong trigger; (3) legal edge with missing guard evidence; (4) declared edge whose `from_state` mismatches the already-reduced current state; (5) wrong `guard_id`; (6a) `to_state` not in family; (6b) `from_state` of wrong type. Plus one fully legal raw accepted event that replays successfully through both `state()` and `CheckpointStore.replay` (exactly one checkpoint, replay idempotent) — proving validation, not blanket rejection.

## Commands And Observations

- `uv run pytest tests/graph/test_checkpoint_replay.py::test_replay_never_duplicates_publish_move_approve_or_delete -q` → `1 passed in 0.05s`.
- All eleven approved nodes individually → 11/11 `1 passed` (GT06: 23.58s).
- Exact suite `uv run pytest tests/graph/test_transition_matrix.py tests/graph/test_graph_node_contracts.py tests/graph/test_checkpoint_replay.py -q` → `11 passed in 23.48s`.
- Task 3.3 regression → `1 passed in 0.44s`.
- Full suite `uv run pytest -q` → `443 passed in 35.79s`.
- `uv run ruff check src tests` → `All checks passed!`.
- `uv run mypy src/ci_workflow/graph` → `Success: no issues found in 10 source files`.
- `uv build --out-dir <tmp>` → sdist + wheel; wheel contains all 12 `ci_workflow/graph/` entries; temp dir removed.
- `git status --porcelain` → no tracked modifications; only `src/ci_workflow/graph/`, `tests/graph/` and runner-managed untracked files; no commit/stage.

## Residual Uncertainty

- Validation re-evaluates the declared guard over the event's embedded `guard_evidence` against the current registry; a guard whose spec changed across registry versions would be enforced against the current table. The frozen-baseline comment documents that a versioned transition-contract/resolver must precede any table change.
- `from_state=None` in an accepted payload serializes to JSON `null` and is validated against the family default (only `project` has `None` default); a raw accepted event with `from_state=null` for a non-project family would fail the declared-edge check (no `None`-source edges exist there), which is the intended fail-closed behavior.
- GT06's legitimate run-other executor events and GT10's sequenced transitions all pass validation (confirmed by the suite), and the forged-event cases confirm the reducer itself — not just `submit` — enforces the deterministic control graph.
- Only `src/ci_workflow/graph/reducer.py` and `tests/graph/test_checkpoint_replay.py` were modified; exactly eleven approved top-level nodes remain. I do not claim acceptance; Codex and the independent sessions own re-verification.
