Trellis SessionStart ✓. Cursor fallback `cursor-cli` / `auto` is taking this bounded `worker_03` role because the primary Pi route was unavailable before a resumable session existed. I’ll stay inside the assigned Task 4.5 contract and start from the authorized read set.I’ll load the Task 4.5 source of truth, prior worker reports, and current implementation so the remaining linkage, URL, and focus work stays on the authorized tree.Next I’ll inspect the existing URL, chart, and drawer contracts so linkage, restore, and focus return can extend worker_01/02 without relaxing filters.I’ll inspect URL state, chart–table sync, and the Task 4.5 fixture next so pointer hits, restore, and Esc can share the same `row_id`.I have the contract: wire chart/table `row_id` hits, persist open/pinned in the existing hash, restore without widening filters, and prove it with real pointer tests. I’ll inspect chart-row requirements, then implement.I have the contract and the seams. Next I’ll implement URL restore, real pointer hits on the same `row_id`, Esc/focus return, and the fixture copy change together.I’ll start with the URL contract (`eo=` for the open row, `e=` for pins), then wire drawer restore, chart hits, and the fixture.I’ll update the fixture next: natural Chinese copy, data-cell triggers, and bar/heatmap/status-matrix charts that share the same `row_id`.Filter prune is missing extra DOM nodes that share the same `row_id`, and chart clicks are landing off-viewport. I’ll hide every matching row and scroll charts into view before pointer hits.Filter and pointer tests passed. Next I’ll inspect the three remaining failures: chart table cell, URL restore, and back/forward.The chart-cell keyboard failure is a focus issue: chart `td`s aren’t tabbable, so Enter retriggers the previous row. I’ll make those cells focusable and fix the URL/`wait_for_function` test bugs.Chart-cell keyboard is fixed. I’ll dump live hash, parse errors, and drawer state for the two URL tests.The Task 4.3 URL test failed: `e=frag-a` disappeared. I’ll check whether Task 4.5 reused that fragment slot.# Execution Output: ci_phase4_task45_execution - worker_03

## Boundary And Context Check

- **Fallback (explicit):** Primary Pi / Qwen Max was unavailable before a resumable session existed. This pass ran as the declared **Cursor fallback** `cursor-cli` / `auto` (effective overlay label `opencode-go/deepseek-v4-pro`). I did **not** invoke Oh My Pi, OpenCode Go, or switch providers. Tools used were this session’s local read/search/edit/shell/pytest/Playwright stack.
- **Capability limits:** No final visual / PPT / PDF / clinical / regulatory acceptance. No conference. Did not write `runs/execution/ci_phase4_task45_execution/worker_03.md` (runner persists this report). Did not independently re-judge worker_02 1280/1024 screenshots; Codex remains authority there.
- **Assigned item:** 实现图表/表格同 `row_id` 联动、筛选同步、网址恢复、Esc 与焦点返回并运行回归.
- **Read:** `AGENTS.md`, `context/ci_phase4_task45_execution_execution_context.md`, `plans/codex_execution_ci_phase4_task45_execution.md`, plus production portal JS/Python, Task 4.3 filter tests, and the worker_01/02 tree already on disk.
- **Boundary:** Edits stayed inside this repo’s Task 4.5 portal sources, asset mirrors, fixture, and tests. No production writes, no new dependencies, no silent package installs.

## Work Performed

Continued on the worker_01/02 tree. Implemented linkage, URL restore, Esc/focus, and the remaining regressions.

**Product**
- Chart marks, heatmap/status-matrix cells, and real table **data cells** open the same stable `row_id`. Chart selection highlight is unchanged. Chart data cells are `tabindex=0` + `role=button` so Tab/Enter/Space hit the cell, not a leftover trigger.
- Open id is `eo=`; pinned ids remain `e=` in the existing v1 hash. Refresh / copy / back / forward restore. Unknown, expired, or filtered-out **row** ids are stripped with `replaceState`; filters are never widened.
- Esc closes (capture) and returns focus to the exact trigger; open/close keep `scrollY`; `prefers-reduced-motion` already in drawer CSS.
- Fixture lead copy is natural Chinese「点击任一数据项」;「查看数据依据」is on name/product/trial **data cells**, not a first-column button. No user-facing「事实行」.

**Defects found and fixed (not “it ran”)**
1. **Pointer / keyboard on chart tables:** non-focusable `td` left focus on the previous trigger; Enter re-opened the wrong row. Cells are now keyboard-operable. Pointer tests use real `mouse.click` coordinates, not `openByRowId`.
2. **URL restore / back-forward no-ops:** `readFilterFromHash` called `filterVisibleRows()` which `syncEvidenceVarsFromDrawer()` **before** applying the hash, overwriting parsed `eo=`/`e=` with the still-open drawer. Skip prune/sync while `applyingFromUrl`.
3. **Unknown ids left in the hash:** same overwrite, plus first-load `applyEvidenceFromHash` used to return early when the drawer API was missing. Unknown ids are now dropped from `__EVIDENCE_VIEWS__` even before drawer init.
4. **Task 4.3 `e=frag-a,frag-b` dropped:** visibility pruning treated opaque fragment ids as row ids. Visibility/catalog drops apply **only when an evidence-view catalog exists**.
5. **Playwright `wait_for_function`:** third positional arg is invalid; now `arg=`. Unknown-id navigation uses the live `data-page-id` instead of a hardcoded pid.

## Artifacts And Evidence

| Path | Change |
|---|---|
| `src/ci_workflow/renderers/portal/assets/portal.js` | `eo=` encode/parse, restore/normalize, skip drawer sync while applying URL, fragment-id compatibility |
| `src/ci_workflow/renderers/portal/assets/charts.js` | pointer + data-cell keyboard → same `row_id`; keep chart highlight |
| `src/ci_workflow/renderers/portal/assets/evidence-drawer.js` | Esc, `openByRowId(rowId, null)` for URL restore, bubbling change |
| `src/ci_workflow/renderers/portal/{filters.py,url_state.py}` | `EvidenceSelection.open_id` + `eo=` |
| `assets/portal/{portal.js,charts.js,evidence-drawer.js,manifest.json}` | byte-identical mirrors; hashes match |
| `tests/fixtures/task45-evidence-drawer/render_fixture.py` | 「点击任一数据项」; data-cell triggers; bar/heatmap/status_matrix |
| `tests/browser/test_evidence_drawer.py` | real pointer, URL, history, filter-normalize, vocab |
| `tests/unit/test_portal_filter_contracts.py` | `eo=` roundtrip / duplicate fail-closed |

Asset identity (src == `assets/portal`, manifest sha256/bytes): `portal.js` 37833 / `52edbb0d…`; `charts.js` 38135 / `f1bfd3bc…`; `evidence-drawer.js` 24813 / `4ab28278…`.

## Commands And Observations

- Chromium evidence-drawer iteration: pointer/filter/Esc green after cell-focus + URL-sync fixes.
- `uv run pytest tests/browser/test_portal_shell.py tests/browser/test_filter_state.py tests/browser/test_chart_table_sync.py tests/browser/test_evidence_drawer.py -q` → **195 passed** (Chromium + WebKit, Task 4.3–4.5).
- `uv run ruff check` on touched Python → **All checks passed.** `uv run mypy --strict` on `filters.py` `url_state.py` `page_shell.py` `builder.py` `evidence_drawer.py` `evidence_view.py` → **no issues.**
- `uv run pytest -q` (full library) → **930 passed, 1 failed.**
- The full-suite failure was `tests/browser/test_filter_state.py::TestFilterState::test_back_forward_and_refresh_restore_state[webkit]`: `Page.goto` **30s timeout** on first navigation to `filter-test.html` — no hash assertion ran. Isolated re-run of that test: **2 passed** in 2.14s. Same case was already in the 195-pass 4.3–4.5 run. **Evidence:** load flake under full-suite Playwright contention, not a product URL defect.
- Pointer tests assert `getOpenRowId()`, 产品/试验/组别 against the hit row; they do not fall back to `openByRowId`.

## Blockers Or Missing Environment

- None for the assigned implementation. Playwright Chromium/WebKit were available.
- Full-suite WebKit `goto` timeout is environmental; not treated as a code blocker after isolated pass.
- `from ci_workflow.renderers.portal import render_page_html` fails (`render_page_html` is documented in `__init__.py` but not re-exported). Pre-existing export mismatch; package tests import via `page_shell` / `builder`. Not changed here.

## Rerun Requests Or Next Step

- Codex: accept linkage/URL/Esc from this pass; independently accept visuals (worker_02 screenshots plus any fixture-copy delta from「点击任一数据项」).
- Optional: re-run `uv run pytest tests/browser/test_filter_state.py::TestFilterState::test_back_forward_and_refresh_restore_state -q` if a clean full-suite WebKit line is required.
- No worker rerun requested for the assigned item; remaining authority is Codex acceptance, not another first-line execution pass.
