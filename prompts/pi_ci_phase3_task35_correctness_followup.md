This is a targeted correction in the same Pi implementation session `019ff749-046b-7000-9f78-a4922036f2f3`. Do not restart or open a new session.

Hard boundaries:

- Work only in `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Edit only `src/ci_workflow/graph/recovery.py`, `tests/graph/test_partial_delivery.py`, and `tests/graph/test_partial_delivery_blocked.py`.
- Runner-managed output path: `runs/pi_ci_phase3_task35_correctness_followup.md`. Never write it with tools.
- Do not modify Task 3.4 files, schemas, CLI, application services, Trellis, context, reports, fixtures, or renderers. Do not commit or stage.
- Keep exactly the existing two approved top-level pytest nodes; add all attacks inside them.

Codex independently reproduced and classified the following Task 3.5 P1 defects. Fix all of them without weakening existing assertions:

1. `DeliveryContract(optional_formats=("pptx", "pptx"))` is currently accepted although the docstring says no duplicates, creating duplicate matrix targets. Reject duplicates. Also align `contract_version` with the canonical project contract: positive integer, not arbitrary strings such as `"banana"`.
2. Contract selection is not durably bound until an accepted coordinator transition exists. A running project can call `reconcile(v1 reports=A, formats=pptx)` while no aggregate transition is available, then call `reconcile(same id/version, formats=())`; both currently return no candidate and the PPTX selection is silently removed. Persist an immutable selection-binding event in the existing EventStore on the first public coordinator action, even if no project transition occurs. It must bind project/run/contract id/version, selected report kinds, mandatory HTML and optional formats, selection digest, event/idempotency identity, and be replay-idempotent with drift fail-closed. The graph reducer must safely no-op this non-graph business event. Do not create a second store.
3. A different version is not automatically a higher version. For one contract id, selection changes are legal only when integer `contract_version` is greater than every recorded version. Older/equal versions cannot appear after a newer binding. `new_contract_version_reopens` must prove the supplied contract is actually a newly bound higher version relative to the version that entered the blocked project state; the current test incorrectly reopens with v1 while claiming a new version. Correct it to bind v1, block, then explicitly use v2. User-material/environment reasons may reopen without a project-contract version increase.
4. Reopen request identity is fixed forever. After `blocked -> queued/running -> ... -> blocked` a second explicit fix currently returns the first stored event and leaves the object blocked. Include a deterministic blocked-entry epoch (or equivalent event-derived occurrence identity) for both project and format reopen requests. Test two complete block/reopen cycles for project and one format; each new block occurrence gets exactly one accepted reopen, replay of the same occurrence appends nothing, and reason drift within the same occurrence fails closed.
5. The current `DeliveryContract` conflates user output selection (A/B/C + formats) with mutable runtime report-version object IDs. After user material reopens a blocked report, `report_C_v2` can collect but the coordinator still reads `report_C`, so real resume cannot advance. Separate immutable output selection from versioned runtime target binding, or provide an equally strict explicit report-target rebind operation. Requirements:
   - changing selected report kinds/formats requires a higher project contract version;
   - advancing C from immutable blocked `report_C` to `report_C_v2` after an accepted explicit user-material/environment/new-contract reopen does not silently drop C and does not mutate the old object;
   - target rebind is persisted and idempotent, bound to kind, old/new object IDs, reason, project/run, current contract selection, and a fresh blocked occurrence;
   - arbitrary target drift before an explicit reopen, rebinding the wrong kind, reusing an existing object, or rebinding from a non-blocked old report fails closed;
   - subsequent `conditions/reconcile` uses the recorded current target and sees `report_C_v2`; the old `report_C` remains `evidence_blocked` in canonical state.

Add exact in-node assertions for each reproducer and prove the business binding/rebind events do not mutate graph state directly. Preserve all existing scenario assertions.

Then run:
- both exact nodes individually and together;
- `uv run pytest tests/graph -q`;
- `uv run pytest -q`;
- `uv run ruff check src tests`;
- `uv run mypy src/ci_workflow/graph`;
- wheel build containing recovery.py, temp cleanup;
- `git diff --check` and status.

Return a compact correction report with root causes, exact code/test changes, true results, and residual uncertainty. Codex owns acceptance.
