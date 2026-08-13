Continue the same Cursor Task 4.2 session. Codex's independent EOF and screenshot review found three remaining P1 false-green defects. Make a final bounded correction; do not create a new route, implement later tasks, invent data, or commit.

Hard boundaries:

- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Modify only Task 4.2 portal code/assets/tests and the task asset manifest if its hashes change.
- Preserve all unrelated and frozen contract changes.
- Write exactly one output file: `runs/cursor_ci_phase4_task42_copy_followup.md`. This path is runner-owned; return the handoff and do not write it with tools.

Read these files only:

- `context/ci_phase4_task42_context.md`
- `src/ci_workflow/renderers/portal/builder.py`
- `src/ci_workflow/renderers/portal/page_shell.py`
- `src/ci_workflow/renderers/portal/assets/portal.css`
- `src/ci_workflow/renderers/portal/assets/portal.js`
- `assets/portal/portal.css`
- `assets/portal/portal.js`
- `assets/portal/manifest.json`
- `tests/browser/test_portal_shell.py`
- `.artifacts/task42-portal/current/screenshots/overview-1280.png`

Defects and required exact closure:

1. The real screenshot still exposes implementation scaffolding to a medical reader: `图表与完整表位预留于此，待数据填入`, `具体图、表与证据稍后填入同一位置`, `本页先给出结构入口`, and fixture copy such as `本页预留…`. These are programmer/placeholder statements, explicitly forbidden by the user. Remove all audience-visible placeholder/future-work language from the renderer and fixtures. The reading-path scaffold may show section number + native clinical section title and one neutral instruction such as `按页面结构快速定位重点内容`, but must never mention pending data, reserved slots, later filling, implementation structure, workflow, or evidence-process chatter. Remove the shell-note aside entirely if it has no immediate reader value. Add exact visible-text negative tests for `预留|待数据|待补齐|稍后填入|结构入口|程序|占位`.
2. Multi-page group triggers look like ordinary links; add a restrained visible disclosure chevron/indicator, with accessible expanded state and without English text. Test its presence and state.
3. `_build_nav_groups` ignores `PortalSpec.nav`, so an explicitly declared navigation order/group can validate successfully but render in page order instead. Preserve explicit nav order/labels/groups when supplied, map them to pages, and keep default page-derived behavior when absent. Add an exact test with page order intentionally different from explicit nav order. Every declared page must remain reachable; reject duplicate/missing nav coverage rather than silently hiding pages.

Re-render 1280 and 1024 screenshots and visually inspect them. Run focused browser tests, design/package tests, Ruff, strict mypy, package verify, and full pytest. Return exact evidence and no-commit statement.
