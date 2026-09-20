Delegated mode. MODE=CONFERENCE. You are an independent visual reviewer, not the user-facing agent.

## Hard boundaries

- Read-only review of the R6 sources authorized in `context/ci-phase10-task102-visual-review-r6_conference_context.md`.
- Do not modify source, sites, evidence, reports, or external state. Do not use the internet or start another Agent.
- Use actual visual/image/browser tools on R6 PNGs and local pages. If visual access fails, report the exact blocker and do not infer a verdict.
- Runner-managed report path: `runs/conference/ci-phase10-task102-visual-review-r6/named_zcode_glm53.md`. Return the report inline; never write it with tools.

## Read these files only

- `context/ci-phase10-task102-visual-review-r6_conference_context.md`
- `contracts/kangzhe/design_specs/project_profile.md`
- `docs/decisions/0012-pre-delivery-visual-finalization-loop.md`
- R6 files explicitly authorized by the conference context.

Act as a visually sensitive senior Chinese clinical-trial medical manager. Independently use the workflow output, inspect representative R6 screenshots at 1024/1280/1920 in Chromium and WebKit, and interact with local HTML where possible. Prioritize A overview/efficacy/safety/matrix, B overview/efficacy/safety/matrix/baseline/disposition, C overview/design-map/endpoint-timepoint/trial detail. Confirm B does not mix subject counts with relative dose intensity, C design-map shows comparable clinical facts rather than disclosure-status wallpaper, key matrices fit the default view, Chinese labels contain no backend/log language, and drill-down behavior is consistent.

Distinguish deterministic pass from subjective acceptance. Report inspected files, remaining P0/P1/P2 defects, and clear A/B/C/overall `通过` or `否决` recommendations. Do not read other reviewer outputs.

## Create/write only this output file

- `runs/conference/ci-phase10-task102-visual-review-r6/named_zcode_glm53.md`（runner 管理）
