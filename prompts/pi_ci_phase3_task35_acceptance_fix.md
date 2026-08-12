This is the final acceptance correction in the same Pi implementation session `019ff749-046b-7000-9f78-a4922036f2f3`. Do not restart or open a new session.

Hard boundaries:
- Work only in the competitive-intelligence-workflow workspace.
- You may now edit exactly: `src/ci_workflow/graph/recovery.py`, `src/ci_workflow/graph/transitions.py`, `tests/graph/test_transition_matrix.py`, `tests/graph/test_partial_delivery.py`, `tests/graph/test_partial_delivery_blocked.py`.
- Keep the existing two Task 3.5 top-level nodes; Task 3.4 GT01 top-level name remains unchanged.
- Runner-managed output path: `runs/pi_ci_phase3_task35_acceptance_fix.md`; never write it with tools.
- No commit/stage; no other file changes.

Two independent reviewers found blocking defects. Implement all corrections and permanent regressions:

1. State-table erratum / deadlock: add declared project transitions `running -> partial_delivery_blocked` and `awaiting_user -> partial_delivery_blocked`, using trigger `remaining_selected_blocked` and existing guard `g_project_partially_delivered_partial_delivery_blocked`. Update the independent literal GT01 fixture so missing=0/extra=0 still holds. In `reconcile`, try `partial_delivery_blocked` from running/awaiting_user when delivered=true, remaining exhausted=true, no running object. Tests must first reconcile these orderings, without an intermediate partially_delivered state:
   - A HTML ready + B evidence_blocked;
   - A-only HTML ready + PPTX blocked;
   - awaiting_user + a delivered target + remaining terminal blocked;
   - after partial_delivery_blocked -> running, if no object actually reopened/rebound, silent reconcile returns to partial_delivery_blocked rather than staying running.
   No fake two-step and no weakened guard.

2. Stale contract operations: after contract v2 is bound, every public method including read-only `conditions(v1)` and all write/reopen/rebind methods must reject v1, even if v1 was previously bound. Same-version selection mismatch must also fail from `conditions()`. A legal unbound higher version may be previewed only if explicitly marked non-authoritative; safest for this API is to require it be bound before `conditions()` returns authoritative aggregate conditions. Choose one clear behavior and test it. Crucially v1 cannot make the project complete while current v2 still requires an undelivered format.

3. Coordinator event canonical strings: `_validate_rebind_event` must reject old/new IDs unless they already equal the canonical whitespace-normalized form. Add raw forge attacks for trailing and internal repeated whitespace in both fields; neither may consume a reopen or redirect target resolution.

4. Reopen project identity: include source state and entry generation, not only blocked epoch. Two consecutive `running -> awaiting_user -> running` cycles must each get one accepted reopen; replay within the same awaiting occurrence appends nothing; reason drift fails closed. An awaiting-user reopen must not collide with an earlier blocked reopen.

5. Format `new_contract_version_reopens`: derive the contract version in force at the format block from the latest validated selection binding at or before the blocked-entry sequence when block guard evidence has no version. v1 format block + bound v2 + reason new_contract_version_reopens must reopen; v1 or older must fail. Retain environment/generator behavior.

6. After successful `rebind_report`, returned `CoordinationResult.conditions` must already resolve the new target, not require a second public read. Revalidate the appended event/view before constructing the result.

7. Delete dead `_selection_material` if still unused. Add the reviewers' attacks inside the two existing Task3.5 nodes and GT01 fixture only. Treat direct graph accepted-event forging as out of scope/security and do not add work for it; the user explicitly excludes security testing.

Run:
- GT01 exact node;
- both Task3.5 exact nodes individually and together;
- all tests/graph;
- full pytest;
- Ruff; strict mypy graph; wheel check and temp cleanup; diff/status.

Return concise report including the v1.2 table erratum, exact fixes, test evidence and residual uncertainty. Codex owns acceptance.
