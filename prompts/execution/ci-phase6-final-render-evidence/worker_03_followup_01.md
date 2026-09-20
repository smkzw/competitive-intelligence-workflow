Delegated mode continuation for the same visual `worker_03` session. Remain a bounded evidence-packaging worker.

Hard boundaries:
- Use only the repaired candidate and refreshed metrics/screenshots.
- Write only `visual-plan.json` and `render-evidence.json` under the repaired candidate's `reviews/visual-finalization/`.
- Do not create an independent verdict or advance graph state.
- Runner-managed report path: `runs/execution/ci-phase6-final-render-evidence/worker_03_followup_01.md`. Return the report, do not write it through tools.

Initial read set:
- `context/ci-phase6-final-render-evidence_execution_context.md`
- `runs/execution/ci-phase6-final-render-evidence/worker_03.md`
- `runs/execution/ci-phase6-final-render-evidence/worker_02_followup_02.md`
- `src/ci_workflow/graph/visual_finalization.py`

Task:
- Regenerate the visual plan/render evidence from the refreshed 768/1024/1440 Chromium/WebKit metrics.
- Preserve verified responsive alternatives for narrow-width search.
- Remove only defects actually resolved by the new evidence; do not coerce failures.
- Validate JSON schemas and repository semantic validators against the current candidate, current plan digest, snapshot digest, and design-contract digest.
- Report canonical plan/render digests and exact validation results.

Output schema:
1. `# Visual Evidence Follow-up: worker_03`
2. `## Refreshed Bindings`
3. `## Validation`
4. `## Artifacts`
5. `## Remaining Boundary`
