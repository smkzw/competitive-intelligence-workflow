All checks green and `git diff --check` clean. Final report:

**Correction report — Task 3.5 event-integrity followup (session 019ff749-046b-7000-9f78-a4922036f2f3)**

## Files changed
- `src/ci_workflow/graph/recovery.py` — coordinator-event validator + validated view; reopen-anchored rebinds.
- `tests/graph/test_partial_delivery.py` — forged `selection_bound` attacks inside the approved node.
- `tests/graph/test_partial_delivery_blocked.py` — rebind reopen-anchoring attacks + forged `report_target_bound` attacks inside the approved node.
- No other files; no commit/stage.

## Root causes → fixes

**Gap 1 (rebind not anchored to a real reopen).** `rebind_report` only checked `project_state == "running"`, so a report blocked mid-run (project never blocked/reopened) could rebind. Fix: every rebind must be anchored to a concrete accepted project reopen event (`graph.transition.accepted`, family=project, blocked → running) that (a) occurs strictly **after** the old report's current blocked-entry event (position-aware via sequence), (b) carries the supplied reason in its guard evidence (`_reopen_matches_reason`), and (c) is not already consumed for another blocked occurrence of the same kind (`consumed_reopens`, per kind). `reopen_event_id`/`reopen_event_digest` are persisted in the rebind payload **and** the event id/idempotency key. Replay of the same (kind, old, new, occurrence) is detected via `rebind_by_identity` before reopen lookup — reason drift on an existing rebind raises `ContractDriftError`, a genuinely new rebind with no qualifying reopen raises `CoordinationError`. The existing "reason drift" assertion (previously relying on payload drift) now triggers the stored-reason mismatch path and still passes unchanged.

**Gap 2 (coordinator events trusted on read).** Raw `WorkflowEvent`s with `coordinator.selection_bound` / `coordinator.report_target_bound` were consumed without validation. Fix: one `_validate_coordinator_events()` pass runs at the top of **every** public read path (`conditions`, `reconcile`, `reopen_project`, `reopen_format`, `rebind_report`), first reducing state (forged graph events fail there via the Task 3.4 reducer), then validating each coordinator event in stream order and building an immutable `_CoordinatorView` used for all subsequent selection/target/blocked-entry resolution. Validation recomputes: exact payload key sets and types; positive-int contract version; sorted unique report kinds/formats; `mandatory_html == "html"`; selection digest; event id and idempotency key (selection and rebind); per-kind target-chain continuity from the default target; new-target reuse (bound targets + report objects seen **before** that event's position — position-aware so a later legal rebind/replay stays valid); blocked occurrence existence; reopen receipt existence, ordering (`reopen.sequence > blocked_seq`), digest match, project/run match, reason match, and per-kind non-consumption. Violations raise `CoordinatorEventContractError` before any event/checkpoint is written; foreign non-coordinator business events are ignored.

## Test additions (inside the two approved nodes)
- Scenario one: forged selection with wrong digest; correct digest + drifted event id; duplicate optional formats — each on a fresh root, `conditions()` raises `CoordinatorEventContractError`. Legal binding + replay counter-case (one binding event, replay appends nothing).
- Scenario two phase 4: new-rebind reason mismatch (`environment_fix_confirmed` vs recorded `user_material_accepted` reopen → `CoordinationError`); legal rebind payload now asserts `reopen_event_id`/`reopen_event_digest` equal the accepted reopen event's identity.
- Phase 6: legal rebind A→A_v2 on the env reopen, then A_v2 re-blocked after the reopen → **stale reopen** rebind fails closed.
- Phase 6b: still-running reproducer (B blocked, C continuable, project stays running, no reopen) → rebind fails closed.
- Phase 8: forged rebind attacks on fresh roots — nonexistent reopen receipt, mismatched reopen reason, redirect to another kind's current target, broken chain (old ≠ current after a legal rebind), stale reopen receipt; plus legal rebind + replay counter-case.

## True results
| Check | Result |
|---|---|
| Both exact nodes individually | 1 passed each |
| Both exact nodes together | 2 passed |
| `uv run pytest tests/graph -q` | 13 passed |
| `uv run pytest -q` | 445 passed |
| `uv run ruff check src tests` | All checks passed |
| `uv run mypy src/ci_workflow/graph` | Success, 11 files (strict) |
| `uv build` wheel | contains `ci_workflow/graph/recovery.py`; temp dir cleaned (subshell-scoped, no `TMPDIR` pollution) |
| `git diff --check` / `git status --short` | clean; only the 3 intended files + pre-existing untracked runner files |

## Failed paths and corrections
- First run: validator's "new target reused" check read **current** canonical state, so a legal rebind became invalid once its new object was driven into state (false positive on replay). Corrected to position-aware tracking: the validator records report objects seen in accepted transitions **before** the rebind's sequence and checks against that, keeping replays stable. `CoordinatorEventContractError` for the legal-rebind path disappeared; all attacks still caught (redirect to `report_A` fails via bound targets, redirect to any pre-existing object fails via seen set).
- Ruff I001 import ordering in the two tests (function-scoped imports) — auto-fixed; no semantic change.

## Residual uncertainty
- Per-kind reopen consumption is defense-in-depth: in realistic flows a reopen always predates a later block of the same kind, so the "already consumed" branch mainly fires on forged streams; ordering (stale) and reason-mismatch branches are directly tested.
- Selection version monotonicity is enforced by the validator and the bind-time check (P1-3); a forged older-version binding after a newer one is rejected by the validator but has no dedicated raw-append test (write-path test exists).
- The validator bookkeeping trusts accepted graph transitions because `executor.state()` validates them first (Task 3.4 reducer); forged graph events fail with `GraphEventContractError` before the coordinator validator — Task 3.4 reducer untouched.

## Next
Codex owns acceptance: verify P0/P1=0, boundary check (only the three allowed files), then record acceptance and proceed to Task 3.6 (fixture/project CLI) or Task 3.7 (science QC bound to real verification results).
