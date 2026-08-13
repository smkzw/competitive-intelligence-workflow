Continue the same Cursor Task 4.2 execution session. Codex has now rendered the current portal at 1280px and found two reproducible P1 user-facing defects that the existing 30 browser tests do not cover. Repair only these bounded Task 4.2 defects; do not implement Task 4.3 filters, Task 4.4 business charts/tables, Task 4.5 evidence drawer, or any real clinical claims.

Hard boundaries:

- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Preserve unrelated work and the already frozen Kangzhe contract update.
- Modify only Task 4.2 portal code, assets, tests, and directly necessary package metadata. Do not commit.
- Parent Codex owns acceptance. Write exactly one output file: `runs/cursor_ci_phase4_task42_visual_repair.md`. This path is runner-owned: return the handoff in your final response and do not write it with tools.

Read these files only:

- `context/ci_phase4_task42_context.md`
- `contracts/kangzhe/design.md`
- `contracts/kangzhe/design_specs/ROUTER.md`
- `contracts/kangzhe/design_specs/core.md`
- `contracts/kangzhe/design_specs/project_profile.md`
- `contracts/kangzhe/design_specs/track_site.md`
- `docs/architecture/page-catalogs/`
- `src/ci_workflow/renderers/portal/`
- `assets/portal/`
- `assets/brand/cms-logo.svg`
- `tests/browser/test_portal_shell.py`
- `tests/contract/test_design_contract_hashes.py`
- `tests/contract/test_package_manifest.py`
- `package-manifest.json`
- `pyproject.toml`
- `.artifacts/task42-portal/current/screenshots/overview-1280.png`

Observed evidence:

1. `.artifacts/task42-portal/current/screenshots/overview-1280.png` is a sparse list of three underlined headings with the summary paragraph incorrectly placed after all headings and most of the viewport empty. The Task 4.2 contract says an empty shell must still be visually meaningful without fake numbers, and the frozen site contract forbids falling back to a flat static page.
2. The tests exercise only three top-level links. The canonical A/B/C page catalogs contain 11/21/12 pages, grouped by `navigation_group`; the current one-row navigation cannot represent these catalogs at 1280px without collision or clipping. A three-page demo therefore gives a false green for the real portal.

Required repair:

- Add failing tests first for a clinically natural, full B-catalog-scale navigation fixture (or equivalent 21-page grouped fixture) at 1280/1440/1920 and <=1024. The shell must expose every physical page through an understandable, keyboard-accessible grouped navigation model while keeping the top header shallow. Do not solve this with tiny text, hidden/clipped text, a horizontal-scroll nav, or an unexplained generic backend label. Use concise native Chinese group/page labels and clear current-page state.
- Make the content shell visually meaningful without invented values: put the page summary immediately below the page title and render the declared sections as an intentional reading-path/section scaffold with useful hierarchy, modest Kangzhe identity, and restrained interaction/focus feedback. It must remain a shell that later Tasks can populate; do not fabricate charts, effect values, counts, status, or medical conclusions.
- Keep the official logo, one quiet footer, global search, file:// safety, no remote assets, reduced-motion, and existing deterministic generation.
- Remove any `overflow:hidden`/ellipsis approach that can mask audience text clipping; validate or lay out concise report titles explicitly.
- Replace the consumer-style default footer wording with quiet internal professional wording appropriate to senior medical staff, without technical/version/evidence-process chatter.
- Strengthen browser tests so visible Chinese workflow/log/programmer vocabulary is rejected too, not only English tokens.
- Inspect the real screenshots yourself at 1280 and 1024 after repair. Run the focused browser suite, design/package tests, Ruff, strict mypy, package verify, and full pytest. Do not commit. Return a compact execution handoff with exact files and evidence.
