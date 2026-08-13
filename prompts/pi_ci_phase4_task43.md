You are the write-capable execution worker for Phase 4 Task 4.3. Implement layered filters and reproducible URL state in the accepted Task 4.2 portal. Parent Codex owns acceptance; do not only write a plan.

Hard boundaries:

- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Preserve unrelated work and accepted Task 4.1/4.2 behavior. Do not commit.
- Implement only Task 4.3. Do not add charts/tables (4.4), evidence drawer contents (4.5), real clinical claims/data, PDF/PPT, external research, or security testing.
- User-visible wording must be native Chinese for a senior clinical-trial medical manager who dislikes software jargon and unnecessary instructions.
- Write exactly one output file: `runs/pi_ci_phase4_task43.md`. It is runner-owned; return the complete handoff and do not write it with tools.

Read these files only:

- `context/ci_phase4_task43_context.md`
- `.trellis/tasks/08-13-phase-4-common-report-portal/prd.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- `contracts/kangzhe/design.md`
- `contracts/kangzhe/design_specs/ROUTER.md`
- `contracts/kangzhe/design_specs/core.md`
- `contracts/kangzhe/design_specs/project_profile.md`
- `contracts/kangzhe/design_specs/track_site.md`
- `docs/architecture/page-catalogs/`
- `src/ci_workflow/reports/common/view_state.py`
- `src/ci_workflow/reports/common/page_registry.py`
- `src/ci_workflow/renderers/portal/`
- `assets/portal/`
- `tests/browser/test_portal_shell.py`
- `package-manifest.json`
- `pyproject.toml`

Implement with RED→GREEN exact tests in `tests/browser/test_filter_state.py` and focused unit tests if needed:

1. Add `src/ci_workflow/renderers/portal/filters.py` and `url_state.py`. Define immutable typed contracts for page filters, per-module filters, sort, anchor trial, selected evidence, current page, applicability and version. Identity values are stable IDs; Chinese labels remain presentation only. Unknown dimensions, duplicate values, invalid page/module IDs, bad state versions and excessive URL size fail closed with concise Chinese errors.
2. Support page dimensions `indication/product/target_or_mechanism/trial`. Support module dimensions from design §15.4, including B baseline/disposition extensions. Dimensions must declare applicability by report/page/module; an inapplicable dimension is hidden or disabled with a Chinese reason, never called missing data.
3. Page reset clears only page filters. Module reset clears only the named module. Other modules, sort, anchor/evidence selection and current page follow an explicit tested policy; no implicit cross-scope mutation.
4. Serialize state deterministically to a versioned URL. Preserve page filters, every named module, sort, anchor trial, selected evidence and current page. Test encode→decode, refresh/copy, browser back/forward, and canonical ordering. Never silently truncate. If a state exceeds the configured URL limit, return a typed “保存为本地视图” outcome rather than partial state; do not build the full named-view manager.
5. Extend the portal UI minimally and coherently: one compact “筛选” entry shows the current page-scope summary; inside, clearly separate `全页范围` and each `本模块` group, use multi-select checkboxes/chips, and keep advanced dimensions collapsed. Avoid backend labels, query-builder language and English status text. The filter panel, active chips, results count/empty state and reset actions must be keyboard usable and work from `file://` without fetch.
6. Bind a synthetic clinical row fixture with stable IDs so filtering visibly updates a row list/count without implementing Task 4.4 charts. Empty selection displays `当前选择下暂无可比较数据`, echoes the active restrictions, and offers explicit page/module reset buttons. It must not auto-expand, auto-clear, or mutate the URL behind the user.
7. Browser matrix: Chromium + WebKit; file:// + static server; 1280/1440/1920 and 1024 representative paths. Assert two reset scopes do not pollute each other, URL copy/refresh/back/forward restores exactly, no console/page errors/remote requests, no text clipping, reduced motion, focus return, and all visible labels are native Chinese. Investigate any zero-row or browser divergence at root cause.
8. Keep shared state consumption compatible with Task 4.1 `ReportViewModel`: filtering selects existing stable rows only and never creates/replaces row identities or switches snapshot/page responsibility.

Run the focused RED/GREEN nodes, full new browser file, Task 4.2 browser regression, relevant Task 4.1 view tests, Ruff, strict mypy, package verify, full pytest and real screenshots. Return exact changed files, tests, unexpected diagnoses, screenshot paths, remaining uncertainty, and NO_COMMIT.
