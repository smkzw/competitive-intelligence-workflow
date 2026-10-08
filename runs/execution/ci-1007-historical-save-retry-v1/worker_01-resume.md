# Execution Output: ci-1007-historical-save-retry-v1 - worker_01

## Boundary And Context Check

- Read the execution context and plan, then the authorized save/retry definitions, generation/request schemas, and adjacent test helpers.
- Worker edits were limited to the three authorized code paths. No Git, install, network, browser, real QA/source/current data, or task-management writes.
- Runtime model identifier: `openai-codex/gpt-6-luna:max`. The Pi route is specified by the execution context; no separate adapter attestation was available.

## Work Performed

- Added historical commit verification requiring a ready journal, matching committed-generation ledger row, canonical immutable generation file and digest, matching stored bundle bytes, and matching request/project/revision/fact-version identities.
- Completed-save replay now validates the saved command, request row, result, and fact-version lineage before returning the original result. A verified historical retry returns before rebuilding or publishing.
- Added coverage for later save/clear/undo, changed payload under the same request ID, corrupted identities and bytes, ready journal without a committed ledger, pre-selector recovery, and loopback HTTP replay.

## Artifacts And Evidence

Worker-edited files and SHA-256:

- `src/ci_workflow/application/latest_delivery.py` — `d988f91451f19e3f7b1428680582ae6debc122ea7ced90b130417e2b7c5eeb72`
- `src/ci_workflow/application/user_fact_edit.py` — `15298f19257a64ccde161c62f2b21c87f47372e760da153e61dd7ab5909321bd`
- `tests/integration/test_1007_historical_save_retry.py` — `54a6d8a152ba1a4894511e300f659706c6c5c52426027599852d7c61348c16f6`

## Commands And Observations

- **RED:** `.venv/bin/python -m pytest -q tests/integration/test_1007_historical_save_retry.py --tb=short -o tmp_path_retention_count=1000` — `1 failed`. Replaying the original save after a later commit reached `_finish_save` and raised the expected stale-current conflict.
- **GREEN:** `.venv/bin/python -m pytest -q tests/integration/test_1007_historical_save_retry.py tests/integration/test_w04_user_fact_edit.py -k 'not test_current_share_exports_committed_a_b_edit_and_unchanged_c' --tb=short -o tmp_path_retention_count=1000` — `82 passed, 1 deselected`.
  - The excluded browser node was identified in the adjacent file as `test_current_share_exports_committed_a_b_edit_and_unchanged_c`. No Playwright/browser invocation.
  - The loopback HTTP replay case passed. No visual or scientific acceptance claim.
- `.venv/bin/python -m ruff check src/ci_workflow/application/latest_delivery.py src/ci_workflow/application/user_fact_edit.py tests/integration/test_1007_historical_save_retry.py` — `All checks passed!`
- `MYPYPATH=src .venv/bin/python -m mypy --strict src/ci_workflow/application/latest_delivery.py src/ci_workflow/application/user_fact_edit.py` — `Success: no issues found in 2 source files`.

## Blockers Or Missing Environment

None observed. Fixed-source installed proof was not part of this execution.

## Rerun Requests Or Next Step

Owner to run the separate fixed-source installed proof and final acceptance. The runner-owned report target is `runs/execution/ci-1007-historical-save-retry-v1/worker_01-resume.md`; it was not written with tools.
