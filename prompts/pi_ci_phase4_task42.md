You are the write-capable Pi execution worker for Phase 4 Task 4.2. Use the selected visual/browser-capable route. The parent Codex owns acceptance. Implement the bounded portal shell in the current repository; do not merely write a plan.

Hard boundaries:

- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Preserve unrelated changes, including the parent-prepared latest frozen Kangzhe site contract and its manifest/test update. Do not revert or re-sync it.
- Do not commit; parent Codex owns commits and final acceptance.
- Do not implement Task 4.3 filters/URL state, Task 4.4 data charts/tables, Task 4.5 evidence drawer, complete A/B/C business pages, PDF/PPT, external research, or security testing.
- User-facing copy must be native Chinese for senior clinical-trial medical professionals. Never expose prompt/log/backend vocabulary or explain what A/B/C report classes mean.
- Runner-managed output path: `runs/pi_ci_phase4_task42.md`. Do not write that report path with tools; return the complete handoff for the runner.

Read these files only:

- `AGENTS.md`
- `context/ci_phase4_task42_context.md`
- `.trellis/tasks/08-13-phase-4-common-report-portal/prd.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- `contracts/kangzhe/design.md`
- `contracts/kangzhe/design_specs/ROUTER.md`
- `contracts/kangzhe/design_specs/core.md`
- `contracts/kangzhe/design_specs/project_profile.md`
- `contracts/kangzhe/design_specs/track_site.md`
- `contracts/kangzhe/design_specs/assets/logo_bot.svg`
- `assets/brand/cms-logo.svg`
- `docs/architecture/page-catalogs/`
- `src/ci_workflow/reports/common/`
- `src/ci_workflow/renderers/` if it exists
- `package-manifest.json`
- `pyproject.toml`
- `tests/acceptance/test_html_ppt_runtime_smoke.py` only as a Playwright style reference
- `tests/browser/` if it exists

Implement exactly Task 4.2:

1. Add `src/ci_workflow/renderers/portal/{__init__,builder,page_shell,global_search}.py`, `assets/portal/{portal.css,portal.js}`, package data/manifest entries as needed, and `tests/browser/test_portal_shell.py`.
2. Start with failing exact browser/unit nodes that prove: official logo in the upper-left; concise report title; no collision among title/navigation/search; correct current-page indicator; exactly one global footer; at least three real mutually linked physical HTML pages; no dead links; global search works with keyboard and lands on/highlights a target; no visible workflow/log/prompt/backend vocabulary; mobile navigation collapses; reduced-motion is complete and readable.
3. Build a pure static, framework-free shell that works from `file://` and a static server. Do not use `fetch` for local data and do not load any remote font/image/script. The builder must copy the official packaged SVG, shared CSS/JS, and generate deterministic physical page files from typed page specs.
4. Follow the project-frozen Kangzhe site contract: light sticky header, readable official Logo, deep text, orange active identity, shallow brand area, Chinese font stack, tabular numerals, body/labels >=16px and normal reading content preferably >=19px, white/light area >=80%, orange/yellow <=12%, risk red only for risk, orange solid controls use dark centered text. Include focus-visible and reduced-motion behavior.
5. The header should show only information a medical manager needs: official logo, the actual report title, page navigation, and search. Do not show report-class definitions, evidence thresholds, source process, AI synthesis labels, status telemetry, or technical version chatter. Footer is one quiet global footer per physical page, not repeated by section.
6. Use synthetic but clinically natural Chinese labels only to exercise the shell, e.g. `竞品全景 / 疗效比较 / 安全性比较`; do not invent clinical effect values or claims in this task. Empty shells must still be visually meaningful without fake numbers.
7. In Playwright, exercise Chromium and WebKit at 1280/1440/1920 desktop widths plus one <=1024 responsive case, for both `file://` and a real local static HTTP server when practical. Capture screenshots into pytest temp paths only; tests must assert geometry (no overlaps/clipping), actual logo load, links, current state, search behavior, console/page errors, and audience-text vocabulary. Investigate any empty output or browser discrepancy at root cause.
8. Read every changed/generated source file back to EOF. Run exact new nodes RED then GREEN, the full browser test file, relevant design/package tests, Ruff, strict mypy, package verify, and full pytest. Return changed files, RED/GREEN evidence, real browser matrix, screenshots generated in temp paths, unexpected-result diagnoses, remaining uncertainty, and no-commit statement.

Do not claim visual acceptance. Codex and the later specified real-medical-manager visual testers own that decision.
