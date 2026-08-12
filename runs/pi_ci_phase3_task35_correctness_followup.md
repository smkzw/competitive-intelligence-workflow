All five P1 defects are fixed and verified. Writing the correction report:

**Correction report — Task 3.5 (session 019ff749-046b-7000-9f78-a4922036f2f3)**

## Files changed
- `src/ci_workflow/graph/recovery.py` — reworked coordinator (P1-1..P1-5).
- `tests/graph/test_partial_delivery.py` — same top-level node; added P1 attacks inside it.
- `tests/graph/test_partial_delivery_blocked.py` — same top-level node; added cycles/rebind/version-proof inside it.
- No other files touched; no commit/stage; `__init__.py` unchanged (no public export required).

## Root causes → fixes

1. **P1-1 duplicates / version type**: `__post_init__` only checked `sorted == list`, so `("pptx","pptx")` passed; `contract_version` was an arbitrary string. Fix: reject duplicate formats and duplicate report kinds; `contract_version` is now a positive `int` (rejects `"banana"`, `0`, `True`).
2. **P1-2 selection not durably bound**: drift detection only read `graph.transition.accepted` evidence, so a no-candidate `reconcile` bound nothing and a later `formats=()` silently dropped PPTX. Fix: every mutating public action calls `_ensure_selection_bound`, which persists `coordinator.selection_bound` (project/run/contract id/version, kinds, `mandatory_html`, formats, `selection_digest`, stable event/idempotency identity) in the existing `executor.store` even when no transition occurs; same identity+selection is a no-op, same identity+different selection raises `ContractDriftError`, and `EventStore.append` is the second fail-closed layer. `graph_reducer` safely no-ops it (test asserts `graph_reducer(initial_state(), bound) == initial_state()` and state unchanged).
3. **P1-3 version ordering + reopen proof**: `_ensure_selection_bound` rejects any contract version `<= max` recorded version for the same `contract_id` (older/equal versions cannot appear after a newer binding). `reopen_project`/`reopen_format` with `new_contract_version_reopens` now prove the passed version is strictly higher than the version recorded in the accepted transition that entered the current blocked state (derived from `guard_evidence.contract_version` of the last blocked-entry event). Test corrected: bind v1 → block → v1 "new version" reopen rejected (`CoordinationError`) → bind v2 → v2 reopen accepted. User-material/env reopen needs no version bump.
4. **P1-4 frozen reopen identity**: reopen request identity had no occurrence, so the second cycle returned the first event. Fix: deterministic blocked-entry epoch (`_blocked_entry_info` counts accepted transitions into the family's terminal blocked states, event-derived) is part of the request identity (`entry:{epoch}`), mirrored by `_existing_transition_event` (same `stable_id("graph-transition", …)` derivation as `executor.submit`) so a replay of the same occurrence returns the original event before state pre-checks, and evidence drift within an occurrence raises `EventConflictError`. Test: two full project block/reopen cycles + one format cycle — each occurrence gets exactly one accepted reopen, replay appends nothing, reason drift fails closed.
5. **P1-5 selection vs. runtime targets conflated**: `DeliveryContract.reports` is now kinds only (immutable output selection); runtime object IDs resolve from `coordinator.report_target_bound` rebind events (latest per kind, else `report_{kind}`). New `rebind_report` validates: kind in selection, project `running` (explicit reopen happened), `old_object_id` == current recorded target (wrong-kind rebind fails), old report `evidence_blocked` (non-blocked fails), new object unseen in canonical state (reuse fails), reason in `PROJECT_REOPEN_REASONS`. Rebind is persisted, replay-idempotent (same event id+payload → `replay_noop`; drift → `ContractDriftError`), never mutates graph state; after rebind, `conditions`/`reconcile` resolve C → `report_C_v2` while `report_C` stays `evidence_blocked`. Rebind before explicit reopen (blocked project) fails closed.

## True results
| Check | Result |
|---|---|
| Both exact nodes individually | 1 passed each |
| Both exact nodes together | 2 passed |
| `uv run pytest tests/graph -q` | 13 passed |
| `uv run pytest -q` | 445 passed |
| `uv run ruff check src tests` | All checks passed |
| `uv run mypy src/ci_workflow/graph` | Success, 11 files (strict) |
| `uv build` wheel | contains `ci_workflow/graph/recovery.py`; temp dir cleaned |
| `git diff --check` / `git status --short` | clean; only the 3 intended files + pre-existing untracked runner files |

## Failed paths and corrections
- Coordinator pre-checks ran before `executor.submit`'s replay precheck, so replaying a reopen after the state changed (e.g. `running`) raised "不可重新打开". Fixed by replay-first lookup of the accepted event via the identical `stable_id("graph-transition", …)` identity; evidence equality decides replay vs. drift.
- Test-side: order-root project create initially used the wrong executor (run mismatch rejection) — switched to its own `GraphExecutor`; stage-7 final `reconcile(v2)` legitimately re-blocks `running → blocked` after reopen (accepted, epoch 2) — assertion corrected, and v1+v2 binding counts verified.
- A transient full-suite regression (5 Playwright smoke failures, `ENOENT …/tmp.Oe7Cg3HXoL`) was caused by my wheel-check `mktemp -d` leaving `TMPDIR` pointing at the cleaned dir in the persistent shell; after `unset TMPDIR` the same file passes 5/5 and the full suite is 445 passed. Not a product defect.

## Residual uncertainty
- Selection binding is written on mutating public actions (`reconcile`/`reopen_project`/`reopen_format`/`rebind_report`); read-only `conditions()` does not bind. The P1-2 reproducer (reconcile) is covered.
- Rebind drift surfaces as `ContractDriftError` (coordinator check mirroring EventStore semantics), reopen drift as `EventConflictError` (executor-level) — both fail closed with distinct, test-asserted types.
- Replaying an *older* occurrence's reopen after a newer occurrence is blocked by the state guard (each occurrence has exactly one accepted reopen); documented behavior, not tested as an attack.

## Next
Codex owns acceptance: re-verify P0/P1=0, boundary check (only the three allowed files changed), then record acceptance and proceed to Task 3.6 (fixture/project CLI) or Task 3.7 (science QC bound to real verification results).
