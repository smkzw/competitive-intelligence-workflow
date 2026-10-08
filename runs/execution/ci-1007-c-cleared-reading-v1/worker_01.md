I'll start by reading the initial read set to understand the assignment.

HEAD matches the context (`51f8d1e`). Now let me read the affected renderer file and its key functions.

Now let me examine the `DesignObservation` model and related enums.

Now let me read the existing test family and check the fixture data.

Let me inspect the fixture's criterion/sample-size observation details and reproduce the described defect.

Now let me probe the actual runtime behavior to confirm the defect family.

Confirmed defect #1. Let me check the criterion-split path and the user-edit/active-revision model.

Let me probe the criterion split path and check how existing tests exercise user-modified/cleared rows.

Let me read the remaining relevant helpers and enums.

Let me check existing tests that exercise user-modified/cleared C rows, so the fix stays compatible.

Let me verify the zero and evidence-view behaviors before writing tests.

The defect family is confirmed. Let me check the C templates and browser consumers for any other revival path before writing the fix.

The defect family is fully confirmed. Now I'll write the dedicated RED test family first, per the assignment.

RED confirmed (5 defect failures, 4 regression anchors green). Now the minimal state-first fix in `report_c.py`.

Now the state-first reason and the two split gates.

All 9 green. Now the assigned verification batch plus the adjacent existing family.

12 failures in an adjacent C integration test — I must determine whether my change caused them. Let me inspect.

These failures are in browser-asset JS tests (`charts.js`/`report-b.js`) — let me verify they're independent of my Python change.

The 12 failures are pre-existing browser-asset tests (assets byte-identical to HEAD, no `report_c` import). Let me run a few more directly-related C renderer tests.

This test name directly matches the objective. Let me run it.

Both probe paths are coherent. Let me harden the family with the two state-precedence cases, then re-run the batch.
