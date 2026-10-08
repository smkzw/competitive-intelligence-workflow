# Execution Context: ci-1007-historical-save-retry-v1

Owner Codex, 1007V1 ACTIVE, baseline a36e4ff33b0b7d19951970d65e2683f018bd2496.
Mode execution: bounded historical replay repair is disjoint from owner's fixed
installed-current sharing proof; one owner keeps mutable QA/scientific state.
- First-line executor: `finite_code_executor` -> `pi` / `openai-codex` / `gpt-6-luna`

## Route and budget
Existing E03 qualified Pi/openai-codex/gpt-6-luna:max alternative preselected before
first dispatch. Native tools now visible, but this is the existing Pi CLI adapter,
not a claimed codex-subagent/native route. Cursor default is not an attested exact
model. Codex account observed21% weekly used, other pools unknown; preserve owner
capacity and balance this finite unit after CodeBuddy work. No global route changes
or invented primary failure. Freeze both packet branches, no fallback. Runtime
model/effort separately attest.128turns/7200s total, tools on, no recursive dispatch,
progress polling, relaunch or owner acceptance before terminal result.

## Source and observed failure
Installed a36 real source QA already committed set r6, clear r7, undo r8, restore r9.
All four A+B/current checks and immediate identical retries passed. Replaying the
older completed r6 request after r9 incorrectly returns409 because
current_transaction_committed proves only current selection, not historical commit.
Owner first checker KeyError(optional absent numerator) is separate and preserved.
Do not read/write actual QA, parent, raw projects or worker histories.

Read complete affected definitions:
- src/ci_workflow/application/latest_delivery.py
- src/ci_workflow/application/user_fact_edit.py (commands,save,_request_row,_finish_save)
- tests/integration/test_w04_user_fact_edit.py (helpers and transaction/retry families)
- tests/integration/test_1007_presentation_current.py
- src/ci_workflow/storage/sqlite.py and migrations defining generation tables as needed
- pyproject.toml
Concrete adjacent dependencies read only.

## Exact write paths
1.src/ci_workflow/application/latest_delivery.py
2.src/ci_workflow/application/user_fact_edit.py
3.tests/integration/test_1007_historical_save_retry.py (new)
Only these code files plus pytest tmp_path. No unrelated files/helper probes,
actual source/QA/DB/current/receipts, install/network/browser/Git/cleanup or old
Chinese root. Preserve five user edits. Report is runner-managed, not written by tools.

## Minimal coherent repair
Separate current visibility from historical committed proof; don't change semantics
of current_transaction_committed or source refresh callers. A stored complete
request/result or ready journal alone cannot prove publication: an immutable matching
generation must exist in the committed DB generations ledger and byte file, bound
to project/request/revision/result generation digest and ready transaction journal.
Validate matching identities and result fact version membership; fail closed on
corruption/mismatch, don't rewrite history. Prefer standard library/existing contracts.
A historical exact retry returns original save result while current remains later.
It must not rebuild, append events/versions/derivations, republish or roll back.
Do not accept staged or failed-before-selector attempts as published. Existing
same-request incomplete recovery, new stale conflict, changed-payload conflict remain.
No new executor/table/platform, medical approval or weak bypass.

## Grouped tests and acceptance
One production root-cause RED family; coherent repair; one relevant batch:
.venv/bin/python -m pytest -q tests/integration/test_1007_historical_save_retry.py tests/integration/test_w04_user_fact_edit.py -k "not actual_loopback_browser" --tb=short -o tmp_path_retention_count=1000
First inspect exact browser node name and accurately exclude it; don't launch
Playwright or use a guessed exclusion that runs it. If family too broad choose
explicit adjacent retry/fault node IDs with owner-visible scope. Negative cases:
later save/clear/undo historical retry; changed payload sameID; complete/ready but
no committed ledger; staged and pre-selector failure recovery; mismatched project/
request/revision/result fact/digest, corrupt generation/journal; current and all
history/source/events unchanged. HTTP actual loopback one case desirable, no browser.
Ruff these3, strict affected2 with MYPYPATH=src; no full gate or repeated per-line run.
Output true commands/counts/hashes; no installed/scientific/browser/release claims.
