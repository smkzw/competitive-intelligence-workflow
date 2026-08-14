# Execution Output: ci_phase4_task46_execution - worker_03

## Boundary And Context Check

- Worked only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`. No production paths read or written; no network access; no site/project modifications by the verifier (enforced by test and by construction).
- Initial read set consumed: `AGENTS.md`, `context/ci_phase4_task46_execution_execution_context.md`, `plans/codex_execution_ci_phase4_task46_execution.md`. Additional context read for contract grounding (recorded per boundary rules): `context/ci_phase4_task46_context.md`, spec v1.2 §15.1–15.7, Hermes plan Task 4.6 (Steps + acceptance), `.trellis/tasks/08-13-phase-4-common-report-portal/{prd.md,task.json}`, `page_registry.py`, `renderers/portal/{builder,page_shell}.py`, `tests/browser/test_portal_shell.py` (harness conventions), `cli.py` (ChineseArgumentParser pattern), `fixture_runner.py`, `runs/execution/…/worker_01.md` + `worker_02.md` (predecessor state).
- Assigned item: 先写 Chromium/WebKit 1280/1440/1920 运行时失败测试，再实现 CLI、原分辨率截图和交互 trace 输出 (worker_03, third in sequence). worker_01/02 contracts in `src/ci_workflow/qc/browser.py` untouched — their 34 nodes still pass inside the 49.
- No peer review, no conference, no final visual acceptance (Codex owns that). Did not create the runner-managed report file; this report is returned inline.

## Work Performed

RED → GREEN, in order:

**RED (recorded before implementation):** appended 15 worker_03 test functions to `tests/acceptance/test_portal_runtime.py` (imports of not-yet-existing `DEFAULT_VIEWPORTS` / `collect_page_runtime_observations` / `merge_page_observations`; CLI tests invoke the not-yet-existing `tools/verify_portal.py`). Ran:
- `ImportError: cannot import name 'DEFAULT_VIEWPORTS' from 'ci_workflow.qc.browser'` — collection error, 1 error in 0.18s.

**GREEN (implementation):**

1. `src/ci_workflow/qc/browser.py` (worker_03 section, ~180 lines appended after `scan_page_html`; only added imports: `Mapping`, `typing.Any/cast`):
   - `DEFAULT_VIEWPORTS = ((1280, 800), (1440, 900), (1920, 1080))` — shared viewport contract for CLI and tests.
   - `collect_page_runtime_observations(page, route, url, *, settle_ms=250) -> PageInspection` — Playwright-page runtime collector: attaches console/pageerror/request listeners before navigation (closed message/resource-type sets, unknown resource types → `other`), navigates `domcontentloaded`, settles, then evaluates viewport/scroll-width (overflow) and fixed/sticky-vs-content rect pairs (occlusion) in-page; returns a `PageInspection` consumable by worker_02's `verify_page_defects`. Browser-agnostic (no playwright import in the module).
   - `merge_page_observations(static, runtime) -> PageInspection` — composes static scan (links/requests/footer) with runtime (console/errors/requests/occlusion/layout); requests deduped by (url, resource_type); route mismatch fails closed.
2. `tools/verify_portal.py` (new, 449 lines) — the CLI:
   - Chinese `ChineseArgumentParser` (mirrors `ci_workflow/cli.py`): missing required args → 缺少必填参数；invalid choice → 参数值不在允许范围内；bad viewport format → passthrough Chinese message. Exit 2.
   - Flags: `--report {A,B,C}` `--project` `--version` (required), `--browser {chromium,webkit}` (repeatable, default chromium), `--viewport WxH` (repeatable, default `DEFAULT_VIEWPORTS`), `--product`/`--trial` (repeatable snapshot identities), `--all-routes` (explicit full-site mode), `--output-dir` (default `<project>/verification/<报告>/<版本>/`, never touches the audited `html/` site).
   - Flow: input validation (identity slug boundary first) → sitemap one-to-one gate (worker_01; fail exits 1 before any browser) → per-browser context with `tracing.start(title=f"run:{run_digest} site:{site_digest}", screenshots=True, snapshots=True)` → per (browser, viewport, route): static scan + runtime collect + merge + `verify_page_defects` + original-resolution viewport screenshot (DPR 1, PNG width/height == viewport) → per-browser trace zip named with run digest → `report.json` (ok/run_digest/site_digest/browsers/viewports/routes/sitemap/pages/screenshots count/traces/message_zh) → Chinese verdict + `A_PORTAL_OK|FAIL routes=N browsers=M` token. Exit codes: 0 pass, 1 audit failure, 2 input/env.
   - `_site_digest` = SHA-256 over sorted site files (path + bytes); `_run_digest` = site digest + audit config + UTC start time.
3. `tests/acceptance/test_portal_runtime.py` (15 new nodes + fixture + helpers; docstring/imports extended, worker_01/02 nodes untouched):
   - Input validation: missing required args; unknown report/browser/bad viewport; invalid identity slug; missing site directory — all exit 2 with Chinese stderr.
   - Runtime failure matrix: `test_runtime_collection_detects_errors_overflow_and_occlusion_fail_closed` × chromium/webkit × 1280/1440/1920 — defect page with `console.error` + uncaught throw + fixed overlay over h1 + 1500px-wide div → CONSOLE_ERROR/PAGE_ERROR/CONTENT_OCCLUSION always, HORIZONTAL_OVERFLOW only when viewport < 1500.
   - Clean-shell runtime+static merge passes; merge contract (dedupe, footer/layout propagation).
   - CLI end-to-end: full pass with 2 browsers × 3 viewports × 16 routes → 96 original-resolution PNGs (dims asserted via PNG header), 2 digest-carrying trace zips (digest strings verified inside zip content), report.json fields, and read-only site guarantee (bytes unchanged); runtime-defect fail (console.error + fixed overlay → exit 1, Chinese message naming route/浏览器/视口/控制台错误, `console_error` in report.json); sitemap-gate fail before browsers launch (no screenshots dir).
   - Fixture: `_build_task46_project` renders all 11 frozen A static pages via `build_portal` + product/trial detail pages via `render_page_html` with `../`-prefixed hrefs/assets.

Verification: RED → 49/49 GREEN in `tests/acceptance/test_portal_runtime.py`; adjacent regression 69 passed; ruff clean on all four touched files; strict mypy clean on `src/` (84 files) + `tools/verify_portal.py`; repo-wide ruff errors are pre-existing in harness dirs (`.trellis/`, `.cursor/`, `.codebuddy/`, `runs/` — none in touched files); test-file mypy shows only the pre-existing `import-untyped` installed-wheel artifact documented by worker_01.

## Artifacts And Evidence

| File | Change | Evidence |
|---|---|---|
| `src/ci_workflow/qc/browser.py` | +worker_03 runtime collection/merge (1082 ln total) | RED import error → 49/49 pass; strict mypy clean |
| `tools/verify_portal.py` | new CLI (449 ln) | exit 0 real run; strict mypy clean |
| `tests/acceptance/test_portal_runtime.py` | +15 worker_03 nodes + fixture (1068 ln) | `49 passed in 88.55s` |
| `src/ci_workflow/qc/__init__.py` | untouched by me (worker_01's ` M` docstring edit) | — |

Real CLI run (scratch fixture, chromium-only): `全站验收通过：16 个路由在 chromium 的 1280×800、1440×900、1920×1080 视口下全部无缺陷…` + `A_PORTAL_OK routes=16 browsers=1`; report.json `ok: True | routes: 16 | shots: 48 | traces: ['chromium']`; trace zip contains `trace.trace`/`trace.network` + run/site digest strings; screenshots `a_clinical-portfolio__chromium__1280x800.png` etc. at exact viewport pixel dims. Input errors: `verify_portal.py：参数错误：缺少必填参数：--report, --project, --version` / `参数值不在允许范围内，请查看 --help` (exit 2).

## Commands And Observations

| Command | Result |
|---|---|
| `uv run pytest tests/acceptance/test_portal_runtime.py -q` (pre-implementation) | **RED**: `ImportError: cannot import name 'DEFAULT_VIEWPORTS'` |
| `uv run pytest tests/acceptance/test_portal_runtime.py -q -k "cli_rejects or merge_observations or sitemap_gate"` | 1st: 4/5 — CLI argv lacked fixture identities → contract was static-only vs 16-route site (test bug, fixed by passing `--product/--trial`); then 5 passed |
| `uv run pytest tests/acceptance/test_portal_runtime.py -q -k runtime_collection` | 1st: 7 failed `NameError: cast` (missing typing import — fixed); then 8 passed |
| `uv run pytest tests/acceptance/test_portal_runtime.py -q -k "cli_full_site or cli_fails_closed_on_runtime"` | 1st: 2 failed `'BrowserContext' object has no attribute 'set_viewport_size'` (sync API lacks it → switched to per-page `page.set_viewport_size`); then 2 passed (82.70s) |
| `uv run pytest tests/acceptance/test_portal_runtime.py -q` (final) | **49 passed in 88.55s** |
| `uv run pytest tests/unit/reports/test_view_model.py tests/contract/test_coverage_set.py tests/acceptance/test_html_ppt_runtime_smoke.py -q` | 69 passed — adjacent regression clean |
| `uv run ruff check` (4 touched files) + `uv run ruff format --check` | All checks passed (3 lint fixes + format applied); repo-wide ruff errors pre-existing in `.trellis/.cursor/.codebuddy/runs` |
| `uv run mypy src/` + `tools/verify_portal.py` | `Success: no issues found in 84 source files` + tool clean (strict) |
| Real CLI run (`--report A --project <scratch> --version v-fixture-001 --product … --trial … --browser chromium --all-routes`) | exit 0, Chinese verdict + `A_PORTAL_OK routes=16 browsers=1`, 48 screenshots, 1 trace; scratch removed |

Environment: `.venv` Python 3.12.13, playwright 1.61.0 with chromium + webkit installed (probed empirically: both launch; viewport screenshots at DPR 1 are exactly viewport-resolution; `tracing.start(title=…)` embeds run/site digests in the trace zip).

## Blockers Or Missing Environment

None. No packages installed, no external access, no site/production writes. Two implementation-only notes (resolved): Playwright sync API lacks `BrowserContext.set_viewport_size` (per-page `page.set_viewport_size` used); CLI must receive snapshot identities explicitly via `--product/--trial` (sitemap contract derives expected routes from provided identities — matches worker_01 semantics; a future pipeline passes the locked snapshot's identity list).

## Rerun Requests Or Next Step

- Codex acceptance: `uv run pytest tests/acceptance/test_portal_runtime.py -q` (49 nodes; 15 sitemap + 19 defect + 15 worker_03) — the full-file run is the single gate. Optionally re-run the real CLI against a Phase-5 project with `--browser chromium --browser webkit --all-routes`.
- Not done by me (out of scope): final visual/rendered acceptance, commit, `cleanup-execution` archive, and wiring the CLI's `--product/--trial` inputs to the Phase-5 locked-snapshot identity source when that snapshot contract lands.
- Tree state for Codex: `src/ci_workflow/qc/browser.py`, `tests/acceptance/test_portal_runtime.py`, `tools/verify_portal.py` new; `src/ci_workflow/qc/__init__.py` carries worker_01's earlier docstring edit; no other files touched.
