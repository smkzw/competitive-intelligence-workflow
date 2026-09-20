Delegated mode continuation for the same visual `worker_02` session. Remain a bounded screenshot/browser executor.

Hard boundaries:
- Use only the repaired candidate in the execution context.
- Write only under its `reviews/visual-finalization/` directory.
- Preserve all existing screenshots/metrics until replacements are successfully written and verified.
- Runner-managed report path: `runs/execution/ci-phase6-final-render-evidence/worker_02_followup_02.md`. Return the report, do not write it through tools.

Initial read set:
- `context/ci-phase6-final-render-evidence_execution_context.md`
- `runs/execution/ci-phase6-final-render-evidence/worker_02_followup_01.md`
- `runs/execution/ci-phase6-final-render-evidence/worker_03.md`
- `src/ci_workflow/renderers/portal/assets/portal.css`
- `src/ci_workflow/renderers/portal/assets/portal.js`

Task:
1. Add fresh Chromium/WebKit `768x900` full-page screenshots for the same six pages and complete the render target matrix.
2. At both 768 and 1024, verify the existing responsive alternative exactly as a user would: press the visible “菜单” button, confirm the global search input becomes visible and focused, search for `疗效`, verify results, ArrowDown focus, Escape close, and zero page/console errors.
3. Update all affected records so `search` is passed, and record `unavailable_required_fields: ["全局搜索"]` with a verified responsive alternative explaining “点击菜单后使用全局搜索” when the input is hidden in the default header state.
4. Save one explicit responsive-search screenshot per engine/width (768 and 1024; four total) and reference their relative paths and hashes in the interaction evidence text.
5. Regenerate `browser-metrics.json`, retaining the 24 existing default screenshots and adding the 12 required 768 default screenshots. Verify all hashes and candidate digest.
6. Do not create the formal render evidence or verdict.

Output schema:
1. `# Visual Execution Follow-up 2: worker_02`
2. `## Matrix Completion`
3. `## Responsive Search Alternative`
4. `## Integrity Checks`
5. `## Remaining Boundary`
