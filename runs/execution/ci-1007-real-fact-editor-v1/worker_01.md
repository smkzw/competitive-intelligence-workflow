Initial read set absorbed. Let me baseline the current state (ruff/mypy/target tests) and check hashes.

Baseline is clean; ruff's E501 skips space-free lines (noted). Now confirming the existing target test passes before changes.

Design settled. Writing the new test family first (RED against the current fixed-form page).

The write was truncated — rewriting the full test file now.

`fact_versions` is append-only (guard confirmed); rerouting hostile seeding through the fixture override + fragment update.

`evidence_fragments` is guard-protected too. Reworking hostile coverage: real loopback path with a hostile source identity override, plus a direct production-page embedding check across all sinks.

RED is genuine (fixed-form page + unsafe embedding). Removing the unused import, then repairing the server.

Now the coherent repair of the server file.

Two harness bugs: registry elements lack `id`, and the flow wrapper isn't actually invoked. Fixing both.

The `null` is legitimate JSON inside the real source locator, not a cleared value. Tightening the assertion to the actual 当前值 row.

All 8 pass. Checking for any other consumers of the server/page before the required batch.

Running the mandated related GREEN batch.

All checks green. Now a focused self-review of the production diff and workspace scope.

One more binding assertion (original quote retained after clear), then freeze and hash.

Trellis SessionStart context loaded.

# Execution Output: ci-1007-real-fact-editor-v1 - worker_01

## Boundary And Context Check
- One bounded worker pass, CodeBuddy CLI, effort max, no recursive dispatch/conference, tools enabled.
- Read in full: the two context/plan files, `user_fact_edit_server.py`, `user_fact_edit.py`, both named test files, `pyproject.toml`. Adjacent reads only to resolve concrete contracts: `ActiveFactBinding`/`ActiveFact` projection, `active_fact_binding_for_a/_c` semantics, append-only guard SQL, the C sample/estimate fixture rows.
- Writes: only `src/ci_workflow/application/user_fact_edit_server.py` (modified) and `tests/integration/test_1007_real_fact_editor.py` (new). Node harness files and fixture workspaces live under pytest `tmp_path`. No Git, installs, network/browser, cleanup, fixture/test/plan/context/report/receipt edits, no legacy-root contact.
- Preserved pre-existing dirty tree (HEAD 6493e37); no other tracked file changed.
- Disclosure: four throwaway ruff-behavior probe files were left in the OS temp directory outside the workspace (`/tmp/ruff_probe*_ci1007.py`); they touch no repo state and were not deleted because cleanup was out of scope.

## Work Performed
- RED first: the new family was authored before the repair. Against the pre-repair server it failed 8/8 (no facts envelope → `KeyError: 'project_id'/'facts'`; no `<script id="editor">`; raw `<img` still present in page bytes).
- Server repair (2 hunks, +388/-51):
  - Replaced the two fixed demo forms with a searchable list of all current facts plus a detail panel: human drug/study/arm/endpoint/time/unit rows, current status, current value, verbatim source quote, source locator, wiring IDs (`fact_id · fact_version_id`), IDs not used as headings.
  - One escaped JSON envelope `{project_id, revision, facts}` via `_safe_json` (`<`, `>`, `&` → `\uXXXX`); all fact data reaches the DOM only through `createElement`/`textContent`; no `innerHTML`/`document.write` in the page.
  - Controls chosen from current semantic fields: C observations + `planned_or_actual_sample_size` → paired integer value (not threshold); `threshold` → operator/value/unit; `crude_rate`+`participants` → legacy n/N path; `count`+`participants` → paired integer with no rewriteable denominator; all other scalars/estimates → paired raw+normalized. Estimates are never exposed as n/N.
  - Explicit nonblank finite input; 0 is sent as 0; blank is refused, never coerced to 0. Clear sends null to the effective numeric field (`numerator` | `normalized_value` | `threshold_value`); undo sends `operation:"undo"` with empty edits.
  - Cleared facts read 用户清除，待重新核实 in both the state and current-value rows (truthy "None"/null/未公开 never rendered); the original source quote stays. Status keeps 不继承独立科学接受.
  - A committed save is answered with `{revision, result, facts}`; the page refreshes facts/revision in place while retaining the selected fact (next save targets the refreshed version). A failed write leaves page state, current pointer and revision unchanged.
  - Loopback security machinery (Host/Origin/session/CSRF digests, JSON-only, body cap, no CORS, path gating, cookie/CSRF headers) is byte-unchanged.
- Test family: 6 tests (one parametrized ×3) = 8 items, 5 real Node VM executions of the production script extracted from the live page. Python tests drive the real loopback server/service over HTTP with exactly the payload shapes the script builds (rate, count, sample, threshold, scalar/estimate, clear, undo).

## Artifacts And Evidence
- Hashes (sha256): server before `c86c01a9349113f846b2cfea74eada9901fb7232586d3e6cb203464fad0986d3` → after `10997c3ef2a0f8eb9a946ad488be794d6ac4ae90788d1f925a44e4af90c8459e`; new test file `eadfc86640a4226e7db89d010b2234f54419313e904102a3c55958649dcd227e` (1025 lines); `user_fact_edit.py` read-only, still `fa20a293d847a659ce1cb21aa459528393b8e3c14008cb1473f00f23b7c5010d`; `test_w04_user_fact_edit.py` and `test_1007_c_sample_current_save.py` diff-empty.
- True counts: RED 8 failed / 0 passed; family GREEN 8 passed; mandated batch 9 passed (8 + reused security test); ruff both files clean; strict mypy clean.
- Service-level evidence through real HTTP: 0 saved as 0 (derived rate 0.0), blank → 400 with pointer bytes unchanged, clear → revision 2 with `user_cleared` + 用户清除，待重新核实 + original `54.8% (34/62)` retained, restore → revision 3 (`38.7096774194`), undo → revision 4 back to cleared; arbitrary A and C facts saved with only their own report rebuilt and other deliveries byte-equal; no-silent-change diff check on the saved fact.

## Commands And Observations
- `.venv/bin/python -m pytest -q tests/integration/test_1007_real_fact_editor.py tests/integration/test_w04_user_fact_edit.py::test_loopback_editor_rejects_malicious_host_origin_csrf_session_and_import` → `9 passed in 16.43s`.
- `.venv/bin/python -m pytest -q tests/integration/test_1007_real_fact_editor.py` → `8 passed in 14.51s` (frozen bytes re-verified).
- `.venv/bin/ruff check src/ci_workflow/application/user_fact_edit_server.py tests/integration/test_1007_real_fact_editor.py` → `All checks passed!`.
- `MYPYPATH=src .venv/bin/mypy src/ci_workflow/application/user_fact_edit_server.py` → `Success: no issues found in 1 source file`.
- `git diff --stat -- src/ci_workflow/application/user_fact_edit_server.py` → 388 insertions, 51 deletions; `git status --porcelain` shows only ` M user_fact_edit_server.py` and the new untracked test file for this scope (`.playwright-cli/*` untracked entries are pre-existing user artifacts).
- Observation: `fact_versions` and `evidence_fragments` carry append-only UPDATE guards, so hostile source text cannot be written into the fixture DB by update; the family seeds the hostile identity through the fixture's binding override and additionally feeds the production page function directly with hostile values in every sink plus a hostile project identity.
- Observation: the B fixture's real source locator JSON contains `"page":null,"url":null`; the cleared-render assertion is therefore bound to the 当前值/当前状态 rows instead of a blunt string scan.

## Blockers Or Missing Environment
- None blocking. Node.js v22.22.3 is available on PATH; the family fails loudly (not skips) if it is absent.
- Runtime limitations, stated plainly: the Node VM harness mocks `fetch`/DOM, so it proves payload construction, selection/version refresh and text-only rendering of the real script, but is not browser, layout, CSP/CORP, keyboard or accessibility evidence. Python wire writes are real service writes but no browser was used. The W04 fixture contains no registered source-side participants-count fact, so the count control is proven at control/payload level (paired raw+normalized, exactly two keys, no denominator field) rather than by an end-to-end registered direct-count save. C-sample, estimate and arbitrary-A runs use fixture workspaces under pytest `tmp_path`, not an actual source-linked project. No installed journey, share bundle, visual or RC acceptance is claimed.

## Rerun Requests Or Next Step
- Owner: review the exact two-file diff and hashes, replay the batch above, then run the separately gated source-linked installed save/share and Ego desktop keyboard/visual acceptance. No rerun of this bounded unit is requested.
