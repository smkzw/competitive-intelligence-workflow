Trellis SessionStart context loaded.

# Execution Output: ci-1007-c-cleared-reading-v1 - worker_01

## Boundary And Context Check

- Read the initial read set in full: `context/ci-1007-c-cleared-reading-v1_execution_context.md`, `plans/codex_execution_ci-1007-c-cleared-reading-v1.md`.
- Verified HEAD = `51f8d1ee33feb2218f6b302b4610f207e90aee57` (matches context). Workspace root = runner-bound cwd.
- Additional reads (declared, necessary to trace the affected call sites): `src/ci_workflow/renderers/portal/report_c.py` (`_numeric_for`, `_value_text`, `_chart_row`, `_evidence_view`, `_table_rows`, `_matrix_item_summaries`, `_numeric_frame_reason_zh`, `design_comparison_workspace`, `_render_page_context`, `render_report_c_site` active-revision projection), `src/ci_workflow/reports/c/contracts.py` (`DesignObservation`), `src/ci_workflow/renderers/portal/active_fact_projection.py` (`user_edit_disclosure`), `src/ci_workflow/domain/enums.py`, `fixtures/positive/c-atopic-dermatitis/inputs/report-data.json` (read only), `tests/reports/c/test_1007_workspace_contracts.py`, `tests/integration/test_w04_user_fact_edit.py`, one read-only probe of the candidate pack `.artifacts/.../c-candidate/source-context-v3-portal-data.json`.
- Writes performed: exactly the two authorized paths — `src/ci_workflow/renderers/portal/report_c.py` (modified, +51/−13) and `tests/reports/c/test_1007_current_reading_state.py` (new, 341 lines). Confirmed by `git status --short`: only ` M src/.../report_c.py` and `?? tests/reports/c/test_1007_current_reading_state.py`; all five pre-existing unrelated user modifications untouched.
- No geometry/CSS/source-authority/gate/medical-approval changes; no fixtures, assets, mirrors, docs, DB, current, evidence, scripts, git, cleanup, network, browser, routes, or recursive dispatch touched. No package installation, no credential handling. No final visual/clinical/release acceptance claimed; Codex remains final authority.

## Work Performed

**Root cause (state-first reading violated in four consumers).** Production probe reproduced the owner's finding on the fixture:

1. `_numeric_for` used `observation.threshold_value or observation.source_text`. A USER_CLEARED sample-size row with `threshold_value=None` (the active-revision clear contract) fell back to the original source and returned `740.0` (positive case) / `0.0` (reported-zero case) — reviving the old value. This flowed into `_value_text` (numeric branch first) → design-matrix cell summary, evidence-view `value`, and for USER_MODIFIED rows also bubble drawability + chart `value`/`numeric_projection`.
2. `_matrix_item_summaries` and `_table_rows` split `observation.source_text` unconditionally for inclusion/exclusion rows, so an edited/cleared criterion whose multiline original stays in `source_text` re-presented the stale original clauses as **current** matrix summaries / table values (probe: 3 stale parts), and the split overwrote the "（用户修订，未独立复核）" suffix.

**Fix (minimal coherent change, one family).**

- Added `_user_current_state(observation)` — USER_CLEARED or USER_MODIFIED ⇒ current reading comes from the explicit current projection (`display_text`) or the state label; `source_text` is source evidence only.
- `_numeric_for`: USER_CLEARED ⇒ `None` (even if a threshold axis is left over); USER_MODIFIED without a current `threshold_value` ⇒ no source fallback. A user-edited current threshold is still the current numeric.
- `_value_text`: after the numeric branch, user states with no current numeric return `_text(display_text) or _state_label(state)` — never source text/segments (also closes the verbatim `source_clause_context` fallthrough for cleared rows without display text).
- `_numeric_frame_reason_zh`: state-first, so cleared sample sizes keep the truthful reason `数值当前状态为用户清除，待重新核实…` (existing reason strings for unparseable / non-disclosed / text rows unchanged).
- `_matrix_item_summaries` and `_table_rows`: user states are not split from stale source; they keep exactly one current reading.
- `source_text`, `display_text`, `threshold_value` axes and all source fields are never rewritten (asserted in tests; no observation mutated).

**RED-first discipline.** The dedicated family was created and run before the source change: **5 failed, 4 passed** (failures: cleared positive `_numeric_for` 740.0; cleared zero 0.0; evidence value `'740'`; edited criterion 3 stale parts; cleared criterion 3 stale parts). After the fix: **11 passed**.

**Preserved behaviors (anchored by green tests):** genuine REPORTED_ZERO still reads `'0'` and stays drawable; a user-edited current threshold still reads/plots (`500`); unedited sample sizes keep source-derived current readings and all 4 stay drawable; unedited multiline criteria still split into per-clause items; NOT_REPORTED stays `未报告`, remains a member, and is never relabeled as cleared.

## Artifacts And Evidence

| Artifact | State | Evidence |
|---|---|---|
| `src/ci_workflow/renderers/portal/report_c.py` | modified, +51/−13 | sha256 `254a81af1e24fcb22d6a79d8f7ea1819e7b90e46af3b30ea43b5477965933651` |
| `tests/reports/c/test_1007_current_reading_state.py` | new, 341 lines, 11 tests | sha256 `d6e0de05def1e280a9221c49b2f6ea7041abce06e7f128ab12edc7b93f4fa490` |

Before → after (production functions, fixture data; read-only probes):

| Case | Before | After |
|---|---|---|
| Cleared sample size, source `'740'`, `threshold_value=None`, display cleared | `_numeric_for`=`740.0`; `_value_text`=`'740'`; matrix summary `('740',)`; evidence value `'740'` | `_numeric_for`=`None`; `_value_text`=current text; matrix `(current text,)`; evidence value=current text |
| Cleared reported zero (`'0'`, `reported_zero_text='0'`) | `_numeric_for`=`0.0`; matrix `('0',)` | `None`; current text; never `'0'` as current |
| Genuine REPORTED_ZERO (unedited) | `'0'`, drawable | unchanged `'0'`, drawable |
| Edited criterion + multiline original | matrix/table split 3 stale original clauses | 1 current reading; `source_text`/`evidence.original_text` still the multiline original |
| Cleared criterion + multiline original | 3 stale clauses; table rows lost cleared reading | 1 current reading containing 用户清除; cleared state preserved on rows |
| USER_MODIFIED sample size with current `threshold_value='500'` | 500 (via threshold) | 500, still drawable/plotted, `source_text='740'` preserved |
| USER_CLEARED with leftover `threshold_value='740'` | 740 revived | `None`; state reason preserved |

Preservation anchors asserted: `_chart_row["source_text"]`, design-matrix item `source_text`, and evidence-view `original_text` remain the verbatim original (`'740'` / multiline clause), and `source_trace_state == "located"` is retained.

## Commands And Observations

- `.venv/bin/python` heredoc probes (fixture + functions) — reproduced revival for cleared positive/zero and stale-split for edited/cleared criteria; confirmed `_chart_row` status/current guards and numeric eligibility were already correct (not redone).
- `.venv/bin/pytest tests/reports/c/test_1007_current_reading_state.py -q --tb=short` — **RED before change: 5 failed / 4 passed**; after change **11 passed**.
- `.venv/bin/pytest tests/reports/c/test_1007_current_reading_state.py tests/reports/c/test_1007_workspace_contracts.py -q --tb=short` — **37 passed**.
- `.venv/bin/pytest tests/reports/c/ -q --tb=short` — **206 passed** (related C batch).
- `.venv/bin/pytest tests/integration/test_w04_user_fact_edit.py -q` — **68 passed**, including `test_rereview3_user_values_never_replace_original_source_layers` (C threshold edit: source fields/evidence views byte-identical, current/original layers intact) and `test_clear_c_threshold_removes_current_numeric_but_preserves_source` (real clear→rebuild path).
- `.venv/bin/pytest tests/integration/test_r24_c_eligibility_source_fidelity.py tests/integration/test_r24_c_clause_context.py tests/integration/test_1007_c_locked_source_display.py tests/integration/test_r24_c_statistics_source_presentation.py tests/integration/test_r24_c_text_source_comparison.py tests/integration/test_r24_c_endpoint_descriptions.py tests/unit/test_c_design_display_projection.py -q` — **78 passed**.
- `.venv/bin/ruff check <two files>` — All checks passed. `.venv/bin/python -m mypy --no-incremental --strict src/ci_workflow/renderers/portal/report_c.py --show-error-codes` — Success, no issues.
- Read-only candidate sanity probe (`.artifacts/.../c-candidate/source-context-v3-portal-data.json`, 258 observations): 0 user-state rows ⇒ zero blast radius expected on the current candidate; all `_value_text` non-empty, 4 drawable, all undrawable reasons non-empty.
- Unrelated observed failure (not caused by this change, not fixed — outside allowed writes): `tests/integration/test_r24_unplotted_table_values.py` mode `b` cases fail with `Error: B page payload script missing before report-b.js` (12 failed / 54 passed). Proof of independence: the test only spawns `node` against `assets/charts.js` and `assets/report-b.js`; it does not import `report_c`; `git diff HEAD -- src/.../assets/` is empty (assets byte-identical to HEAD), and both HEAD and working `report-b.js` contain the same payload guard.

## Blockers Or Missing Environment

- No blockers for the assigned work. No missing tools; nothing installed.
- The 12 mode-`b` node cases above appear to be a pre-existing stale-test/asset contract in the B-report browser layer; report-b.js/assets are outside this pass's allowed writes, so it is reported, not touched.
- Per assignment: real-browser, current/share, rendered-candidate and visual acceptance remain **NOT_RUN** here (owner retains them). No network/browser tool was needed.

## Rerun Requests Or Next Step

- Codex: review the two-file diff and, if you want rendered confirmation, run a C render with a pack containing a cleared/edited fact (the current candidate pack contains none, so no visual delta is expected on it); the producer path is covered by the W04 service tests above.
- Two precise decisions for Codex (out of my boundary, deliberately unchanged):
  1. NOT_REPORTED sample-size rows that still carry a numeric axis keep a numeric current reading in matrix/evidence while chart/table show 未报告. Bringing them under the same state-first rule would touch the "do not convert not-reported" boundary — confirm whether that is wanted as a follow-up.
  2. For USER_MODIFIED sample sizes whose edit removed the current number, the undrawable reason is the existing shape message `样本量不能核实为非负整数…`; a dedicated "当前未给出数值" reason may read better — confirm wording if desired.
- Resume point: both files are final and verified as above; no pending edits, no partial work. Any further change request can continue from sha256 `254a81af…` (renderer) / `d6e0de05…` (test).
