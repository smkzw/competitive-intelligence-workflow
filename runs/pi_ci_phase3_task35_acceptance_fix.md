**Acceptance-fix report — Task 3.5 (session 019ff749-046b-7000-9f78-a4922036f2f3)**

## v1.2 §10.2 table erratum (item 1)
The spec table only declared `partially_delivered -> partial_delivery_blocked`; with a delivered target and all remaining selected objects terminal-blocked, a project in `running`/`awaiting_user` could deadlock (no candidate → stuck `running`/`awaiting_user` with no legal move). Fix:
- `src/ci_workflow/graph/transitions.py`: added declared edges `running -> partial_delivery_blocked` and `awaiting_user -> partial_delivery_blocked`, trigger `remaining_selected_blocked`, reusing existing guard `g_project_partially_delivered_partial_delivery_blocked` (no guard changes, no weakened conditions).
- `tests/graph/test_transition_matrix.py`: GT01 literal fixture updated with the same two `LiteralEdge`s — GT01's missing=0/extra=0 assertion holds (verified by the passing GT01 node).
- `recovery.py` `reconcile` order: `running: (complete, blocked, partial_delivery_blocked, partially_delivered)`, `awaiting_user: (complete, blocked, partial_delivery_blocked)`. Guards remain mutually exclusive, so only the correct one fires — no fake two-step.
- Tests (scenario-2 node): 9a A-HTML-ready + B evidence_blocked → direct `partial_delivery_blocked` with no `partially_delivered` in the project event history; reopen → `running`, silent `reconcile` returns to `partial_delivery_blocked` (from_state `running`); 9b A-only HTML-ready + PPTX-blocked → direct `partial_delivery_blocked`; 9c `awaiting_user` + delivered + terminal → direct `partial_delivery_blocked` from `awaiting_user`.

## Items 2–7 exact fixes
2. **Stale contracts**: `conditions()` now requires authority — contract bound, bound version == latest, selection matches (`_require_authoritative`); unbound → `CoordinationError`, stale version or same-version mismatch → `ContractDriftError`. `_ensure_selection_bound` now also rejects a **recorded** older version once a higher version is bound (`< max`, previously `<= max` only for unrecorded), so every write/reopen/rebind method rejects v1 after v2. Tests: scenario-1 node asserts `conditions(v1)`/`conditions(unbound v3)`/`conditions(v2 mismatch)` all fail, authoritative `conditions(v2)` readable, and `reconcile(v1)` fails closed so v1 can never complete a project while v2 requires an undelivered format.
3. **Canonical strings**: `_validate_rebind_event` rejects `old_object_id`/`new_object_id` unless already equal to `" ".join(value.split())`, before any bookkeeping — so a forged whitespace variant can neither consume a reopen nor redirect target resolution. Four raw-append forges (trailing/internal whitespace on old and new) each raise `CoordinatorEventContractError` with `match="未规范化"`.
4. **Reopen identity**: now `("project", "running", source_state, f"entry:{generation}")` — source state plus per-source entry generation. Replays reconstruct the last accepted reopen's (source, generation) from the event stream. Tests: two consecutive `running -> awaiting_user -> running` cycles each get one accepted reopen (distinct event ids), replay within the same awaiting occurrence appends nothing, reason drift raises `EventConflictError`; a mixed root proves a blocked reopen and a later awaiting reopen do not collide.
5. **Format `new_contract_version_reopens`**: `_version_at_blocked` falls back to the latest validated selection binding whose event sequence is ≤ the blocked-entry sequence when the block guard evidence lacks `contract_version`. Test (phase 11): v1 bound → A-pptx blocked (evidence without version) → `reopen_format(v1, new_contract_version_reopens)` fails, v2 bound → `reopen_format(v2, …)` accepted; environment behavior retained with v2 after a re-block.
6. **Rebind result**: after appending the rebind event, `rebind_report` re-runs `_validate_coordinator_events` and computes `conditions` from the fresh view — the returned `CoordinationResult.conditions` already resolves `report_C_v2` (asserted in phase 4; no second public read needed).
7. Deleted dead `_selection_material`.

## Files changed
- `src/ci_workflow/graph/recovery.py`, `src/ci_workflow/graph/transitions.py`, `tests/graph/test_transition_matrix.py` (GT01 fixture only), `tests/graph/test_partial_delivery.py`, `tests/graph/test_partial_delivery_blocked.py`. No commit/stage; direct graph accepted-event forging treated as out of scope (security excluded per instruction, no work added).

## Verification results
| Check | Result |
|---|---|
| GT01 exact node | 1 passed |
| Both Task 3.5 nodes individually / together | 1 passed each / 2 passed |
| `uv run pytest tests/graph -q` | 13 passed |
| `uv run pytest -q` | 445 passed |
| `uv run ruff check src tests` | All checks passed |
| `uv run mypy src/ci_workflow/graph` | Success, 11 files (strict) |
| `uv build` wheel | contains `ci_workflow/graph/recovery.py` + `transitions.py`; temp dir cleaned (subshell-scoped) |
| `git diff --check` / `git status --short` | clean; only the 5 permitted files modified/added + pre-existing untracked runner files |

## Failed paths and corrections
- Phase 11 initially blocked the format **before** any binding existed (bind-v1 reconcile came after the block), so the version fallback found no prior binding (`vNone`) and v2 reopen failed. Corrected the test to bind v1 first, then drive the block — the fallback then resolves v1 and v2 reopens.
- Scenario-1 stale-contract section needed `CoordinationError` added to its function-scope imports.
- Ruff SIM102 on the new reopen-identity branch and the version-fallback loop — combined with `and`.

## Residual uncertainty
- Reopen replay reconstruction uses the **last** accepted project reopen for the contract; replaying an older occurrence after a newer reopen exists would resolve to the newer one (no error). Not exercised; the tested contract is "replay within the same occurrence".
- Per-source generation means `blocked` and `partial_delivery_blocked` counts are independent; a project alternating sources never collides (covered by the mixed root), but a dedicated blocked→blocked double cycle with the new identity was not re-added (previous two-cycle test now exercises `partial_delivery_blocked` twice, which passed).
- The erratum reuses the existing guard whose name references `partially_delivered`; semantics (delivered + exhausted + no running) are identical to the original edge.

## Next
Codex owns acceptance: re-verify P0/P1=0 and boundary (only the 5 permitted files), then record acceptance and proceed to Task 3.6 (fixture/project CLI) or Task 3.7 (science QC bound to real verification results).
