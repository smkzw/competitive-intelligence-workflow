# Execution Output: ci_phase4_task46_execution - worker_01 (reachability followup)

## Boundary And Context Check

- Worked only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Modified only the three authorized files: `src/ci_workflow/qc/browser.py`, `tools/verify_portal.py`, `tests/acceptance/test_portal_runtime.py`. `git status` confirms no other tracked file changed by this follow-up (the one tracked `M` on `qc/__init__.py` is from the prior worker_01 session).
- Read only the listed set: `AGENTS.md`, execution context, `runs/conference/ci_phase4_task46_visual_acceptance/grok_build_46_followup.md`, `qc/browser.py`, `verify_portal.py`, `test_portal_runtime.py`, `page_shell.py`, `portal.js` (+ `builder.py`/`global_search.py`/`domain.enums` referenced by those files to confirm search-index wiring and `build_search_index` contract — same files the fixture already imports).
- No production renderer, design assets, generated sites, manifests, snapshots, or unrelated files modified. No external network. Verifier remains read-only (no mutation code path).

## Work Performed

**RED (tests first):** Added 7 reachability tests + 1 CLI orphan black-box test to `tests/acceptance/test_portal_runtime.py`, run before implementation → `ImportError: cannot import name 'ReachabilityViolationCode' from 'ci_workflow.qc.browser'` (RED recorded). After gate implementation but before fixture fix, CLI full-acceptance tests failed with exactly the P1 defect: `全站可达性验收失败…无法导航进入：/a/products/product-01、/a/products/product-02、/a/products/product-03、/a/trials/trial-01、/a/trials/trial-02` — RED evidence that the gate catches orphaned details before screenshots.

**GREEN — reachability contract (`qc/browser.py`):**
- `site_path_to_route(path, report)` — inverse of `route_to_site_path`; non-HTML → None.
- `ReachabilityViolationCode.UNREACHABLE_ROUTE`, `ReachabilityViolation`, `ReachabilityVerification` (ok, start_route, reachable/unreachable routes, violations, computed Chinese `message_zh` naming unreachable routes with guidance).
- `verify_route_reachability(contract, inspections)` — deterministic FIFO BFS from the overview static entry; edges resolved via the existing `resolve_local_link` (no weaker duplicate URL rules); only links landing on expected-sitemap routes count; external/fragment/mail/tel links never count; missing inspections contribute no edges; read-only.

**GREEN — CLI integration (`verify_portal.py`):**
- New gate after sitemap one-to-one: scans all expected pages, verifies reachability; failure prints Chinese message naming unreachable routes + `A_PORTAL_FAIL routes=N browsers=0`, exits 1, and returns before output-dir creation (no screenshots, no report.json).
- `reachability` block added to `report.json` on success-path runs; docstring flow updated.

**GREEN — fixture fixes (`test_portal_runtime.py`):**
- Chinese display-name maps: `环柏单抗/洛普利单抗/贝妥昔单抗`, `关键注册研究/长期扩展研究` (stable slugs kept internally).
- `_render_detail_page` now uses Chinese H1/body (`本页汇总{名称}的作用机制…` / `本页呈现{名称}的试验设计…`); removed `产品档案：product-01` and `锁定快照中该对象`.
- `_inject_detail_entries` adds visible clickable Chinese links on `product-overview.html` (3 products) and `clinical-portfolio.html` (2 trials).
- `_expand_search_index` merges detail pages into the global search index (inline literal on every `*.html` + `assets/search-index.js`, consistent with the shell's inline/external parity contract).
- Entry remains `overview.html` (registry `/a/overview`); no `index.html` fabricated; accepted portal-shell behavior untouched.

## Artifacts And Evidence

| Check | Result |
|---|---|
| Reachability unit tests (7) | PASS |
| CLI orphan black-box test | PASS — exit 1, `可达性` + `/a/products/product-02` in stdout, `browsers=0`, no screenshots/report.json |
| Full acceptance file `test_portal_runtime.py` | **62 passed** (after formatting, real Chromium+WebKit runs) |
| Adjacent 69 (`test_html_ppt_runtime_smoke.py` + `test_coverage_set.py` + `test_view_model.py`) | **69 passed** |
| `ruff check` + `ruff format --check` (3 files) | All checks passed (2 files formatted, re-verified) |
| `mypy --strict` on `qc/browser.py` + `verify_portal.py` | `Success: no issues found` |
| Built-fixture inspection | 16 routes; Chinese product/trial entries visible; trial H1 `关键注册研究`; no machine text anywhere; search index = 16 entries incl. all 5 detail slugs with Chinese titles; `overview.html` exists, `index.html` absent |

All failures investigated to root cause, not accepted from exit code: (a) test helper referenced `contract` before binding (UnboundLocalError) — restructured helper to derive the contract internally; (b) mutation test lacked `site_root.mkdir()` — fixed; (c) CLI acceptance failures were the intended gate catching the fixture's orphaned details — fixed by fixture links.

## Commands And Observations

- `uv run pytest tests/acceptance/test_portal_runtime.py -k "reachability or orphan or round_trip" -q` — RED `ImportError: cannot import name 'ReachabilityViolationCode'` → GREEN 7 passed.
- `uv run pytest tests/acceptance/test_portal_runtime.py -k "cli_full_site or cli_plan_command or cli_orphan or runtime_collection_of_clean" -q` — pre-fixture 2 failed (gate correctly vetoing orphaned fixture, browsers=0), post-fixture 4 passed.
- Full file runs: 62 passed twice (pre/post format), ~108s each (real browsers).
- Adjacent 69 passed (3.3s).
- `ruff check`/`format` clean; `mypy --strict` clean on both source files.
- Fixture observable inspection via `uv run python` (system python3 3.9 lacks `datetime.UTC` — used venv).

## Blockers Or Missing Environment

None. Playwright browsers already installed (Chromium/WebKit runs green). `mypy` on `tests/**` retains the pre-existing `import-untyped` installed-wheel artifact seen in the prior session; strict mypy on `src/` + `tools/` is clean.

## Rerun Requests Or Next Step

- Ready for Codex acceptance: re-run visual acceptance (`verify_portal.py` on a fresh fixture project) — the reachability gate now rejects orphan details pre-screenshot, and the synthetic portal shows Chinese names with navigable entries and search coverage.
- Remaining known P2s from the grok report (search placeholder truncation at 1280, logo→clinical-portfolio home link in real portal) are outside this repair's scope; flag for a Phase 5/portal-polish item if Codex wants them tracked.
