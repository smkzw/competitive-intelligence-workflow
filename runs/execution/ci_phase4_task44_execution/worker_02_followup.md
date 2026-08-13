Trellis SessionStart ✓ — continuing Worker 02 repair: adding RED counterexamples for the five false-green findings, then fixing implementation to GREEN within the authorized files only.Updating tests to RED first: correcting false contracts and adding the five counterexample classes.Rewriting the test contract file with corrected RED cases, then implementing the GREEN fixes.RED confirmed. Implementing GREEN fixes in `chart_specs.py` and exports.96 GREEN. Running quality gates and full unit regression.# Execution Output: ci_phase4_task44_execution - worker_02_followup

## Boundary And Context Check

- **Role:** same Worker 02 repair session; Cursor tools only (no Alibaba/Qwen).
- **Authorized edits:** `chart_specs.py`, `__init__.py`, `test_chart_compatibility.py` only.
- **Not touched:** browser layer, Task 4.3, design/plan, production, no commit.
- **Runner path:** `runs/execution/ci_phase4_task44_execution/worker_02_followup.md` — not written by tools.

## Work Performed

RED-first then GREEN for five Codex false-green findings:

1. **`COMPARABILITY_DIMS`** — dropped `control_role` / `denominator`; added `DISPLAY_CONTEXT_DIMS`; treatment/control + different denominators stay one group; time-window whitespace bucket normalized.
2. **`resolve_chart_type`** — validates required fields for disclosed rows; sets `renderable`; forest CI order, bubble `size>0`, radar length checks; missing disclosure → `renderable=False`, no numeric zeroing.
3. **`validate_chart_input_rows`** — unique non-empty `row_id`, single non-empty `report_snapshot_id`, known `FactDisclosureState`; used by resolve/split.
4. **`validate_all_rows_covered`** — rejects duplicate original `row_id`; scientific digest equality (excludes `_chart_type`/`renderable`).
5. **Ruff B905** — `zip(..., strict=True)`; authorized trio ruff/mypy clean.

## Artifacts And Evidence

| File | Change |
|---|---|
| `tests/unit/reports/test_chart_compatibility.py` | Contract corrected + new RED nodes (54→96) |
| `src/ci_workflow/reports/common/chart_specs.py` | False-green repairs |
| `src/ci_workflow/reports/common/__init__.py` | Export `DISPLAY_CONTEXT_DIMS`, `validate_chart_input_rows` |

**New / corrected precise nodes (examples):**
- `test_comparability_dims_tuple_exists` / `test_display_context_dims_are_not_split_triggers`
- `test_treatment_and_control_roles_stay_same_group`, `test_different_denominators_stay_same_group`, `test_roles_and_denominators_mixed_stay_same_group`
- `test_time_window_normalized_bucket_does_not_split`
- `TestRequiredFieldsAndRenderability` (9×3 parametrized + forest/bubble/radar)
- `TestLockedSnapshotIngress` (7)
- `test_validate_fails_on_duplicate_original_row_id`, `test_validate_fails_when_group_rewrites_row_content`

**RED cause (pre-fix):** missing API (`DISPLAY_CONTEXT_DIMS`, `validate_chart_input_rows`), old dims still split on role/denominator, no `renderable`/field checks, coverage Counter false-green.

**GREEN counts:** chart suite **96 passed**; Task 4.1+4.4 reports **132 passed**; full `tests/unit` **274 passed**.

## Commands And Observations

```text
# After RED tests only: 96 failed (ImportError / assert)
# After implementation:
uv run ruff check|format → clean on 3 authorized files
uv run mypy chart_specs.py __init__.py → Success
uv run pytest test_chart_compatibility.py → 96 passed
uv run pytest test_chart_compatibility.py test_view_model.py → 132 passed
uv run pytest tests/unit → 274 passed
```

## Blockers Or Missing Environment

None for this repair.

**Still uncovered (real data binding boundary for Codex/Worker 03):**
- No proof that portal/ECharts options bind only via locked snapshot lookup rather than dict field values as scientific source of truth.
- No end-to-end binding from `FilteredRowSet`/`ReportRow` → chart payload without intermediate free-form dict widening.
- Conflicting disclosure path is `renderable=False` only; no clinical display contract beyond that.
- Browser chart↔table row-ID sync still Worker 03.

## Rerun Requests Or Next Step

1. Codex may re-challenge false-green on the new nodes.
2. Worker 03 may proceed on browser/ECharts once Codex accepts this repair.
3. No further Worker 02 action unless Codex assigns another bounded defect.
