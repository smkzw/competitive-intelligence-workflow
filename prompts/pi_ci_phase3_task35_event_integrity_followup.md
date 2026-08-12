This is a second targeted correction in the same Pi implementation session `019ff749-046b-7000-9f78-a4922036f2f3`. Do not restart or open a new session.

Hard boundaries:
- Work only in the competitive-intelligence-workflow workspace.
- Edit only `src/ci_workflow/graph/recovery.py`, `tests/graph/test_partial_delivery.py`, `tests/graph/test_partial_delivery_blocked.py`.
- Keep exactly the two approved top-level pytest nodes; add attacks inside them.
- Runner-managed output path: `runs/pi_ci_phase3_task35_event_integrity_followup.md`; never write it with tools.
- No commit/stage and no other file edits.

Initial read set:
- `src/ci_workflow/graph/recovery.py`
- `tests/graph/test_partial_delivery.py`
- `tests/graph/test_partial_delivery_blocked.py`

Two Task 3.5 P1 gaps remain:

1. `rebind_report()` claims the project was explicitly reopened, but only checks current project state == running. If report B becomes evidence_blocked while report C remains active and the project is still running, `rebind_report(B, reason=user_material_accepted)` currently succeeds without any accepted explicit reopen event. Bind each rebind to a concrete accepted project reopen event occurring after the old report's current blocked-entry event. The supplied rebind reason must equal the reason recorded in that reopen event. That reopen event must not already have been consumed to rebind a different blocked occurrence of the same kind. If no such event exists, the reason mismatches, or the reopen predates the report block, fail closed. Persist the reopen event id/digest in the rebind payload and idempotency identity. Add exact attacks for the still-running-project reproducer, mismatched reason, and stale reopen.

2. `coordinator.selection_bound` and `coordinator.report_target_bound` are trusted when read. A raw `WorkflowEvent` directly appended to the shared EventStore can currently forge selection/version or redirect C to an arbitrary object, because `_recorded_binding`, `_recorded_bindings`, `_recorded_rebind_event`, and `_resolve_target` do not validate payload schema, selection digest, event_id, idempotency_key, project/run, chain continuity, blocked occurrence, or reopen receipt. Implement one fail-closed coordinator-event validator used on every read path before any event influences state/selection/target resolution. It must validate:
   - exact payload key sets and types; positive integer contract version; sorted unique report kinds/formats; mandatory_html exactly html; recomputed selection digest;
   - recomputed event ID and idempotency key for selection binding;
   - for rebind: exact kind/old/new/reason/version/selection/blocked occurrence/reopen receipt; current chain continuity per kind from default target through each prior validated rebind; new target not reused; recomputed event/idempotency identity; referenced accepted project reopen exists, is after the correct report blocked-entry event, matches project/run/reason, and is not reused for an invalid occurrence;
   - malformed/forged coordinator events raise a typed `CoordinatorEventContractError` from `conditions()`, `reconcile()`, reopen and rebind read paths before any new event/checkpoint is written. Foreign non-coordinator business events remain ignored.

Add raw EventStore attack cases for at least: forged selection digest, drifted event id/key, duplicate formats, forged rebind redirect, broken rebind chain, nonexistent/mismatched reopen receipt. Also retain legal selection/rebind replay counter-cases. Do not weaken Task 3.4 reducer; these are coordinator-owned business events and validation belongs in recovery.py.

Then run both exact nodes, graph suite, full suite, Ruff, strict mypy, wheel check/temp cleanup, diff/status. Return a concise correction report; Codex owns acceptance.
