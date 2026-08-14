Continue the same Pi/CMS-SMK DeepSeek V4 Flash `worker_01` session. Codex visual acceptance found a concrete P1 false-green: all dynamic product/trial files exist, but none is reachable from the portal or global search, so direct file opening passes while a medical manager cannot navigate to them. Repair only this issue and the synthetic user-facing names; do not broaden into Phase 5 business content.

Hard boundaries:
- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Modify only `src/ci_workflow/qc/browser.py`, `tools/verify_portal.py`, `tests/acceptance/test_portal_runtime.py`.
- Do not modify portal production renderer, design assets, generated sites, manifests, snapshots, or unrelated files.
- Runner-managed output path: `runs/execution/ci_phase4_task46_execution/worker_01_reachability_followup.md`. Return the complete report and never write it with tools.

Read these files only:
- `AGENTS.md`
- `context/ci_phase4_task46_execution_execution_context.md`
- `runs/conference/ci_phase4_task46_visual_acceptance/grok_build_46_followup.md`
- `src/ci_workflow/qc/browser.py`
- `tools/verify_portal.py`
- `tests/acceptance/test_portal_runtime.py`
- `src/ci_workflow/renderers/portal/page_shell.py`
- `src/ci_workflow/renderers/portal/assets/portal.js`

## Required repair

1. Add a deterministic, read-only route reachability contract. Starting from the report’s overview route, follow local HTML anchors across the expected sitemap. Every expected route, especially each product/trial detail route, must be reachable. An existing but orphaned page is a failure before browser screenshots. Use existing link parsing/resolution where possible; avoid duplicate weaker URL rules.
2. Integrate reachability into `verify_portal.py`. Failure must exit 1, not launch browsers or create screenshots, and give concise native Chinese guidance naming unreachable routes.
3. Add RED→GREEN tests for: all expected routes reachable; an existing orphan dynamic page fails; a multi-hop route remains reachable; external/fragment/mail links do not count; no site mutation.
4. Make the Task 4.6 synthetic portal expose visible, clickable entries for all 3 product and 2 trial detail pages from appropriate static pages and include them in the global search index. The links must be user-visible Chinese labels, not internal route IDs.
5. Replace synthetic detail H1/body machine text such as `产品档案：product-01` and `锁定快照中该对象` with native Chinese fixture names/phrasing while keeping stable route slugs internally. It is acceptable for this fixture to define explicit Chinese display-name maps; do not change production domain models.
6. Fix only if directly caused by the fixture: the context’s entry is `overview.html`, not nonexistent `index.html`. Do not refactor accepted portal shell behavior.
7. Add black-box CLI tests proving orphan files now fail and the complete fixture succeeds using a relative `--project` path.
8. Run the full Task 4.6 acceptance file, adjacent 69 tests, Ruff and strict mypy. Investigate failures; do not accept from exit code alone.

User-facing text must be native Chinese medical-product language, with no programmer/log/prompt labels. Do not modify artifacts to make the verifier pass; fix source fixture and mechanical acceptance.
