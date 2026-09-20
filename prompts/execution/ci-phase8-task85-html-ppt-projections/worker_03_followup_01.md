Delegated mode remains in effect. Continue the same `worker_03` session and the same authorized write boundaries from the original execution prompt. Do not create a Trellis task, do not ask the user for permission, and do not declare Task 8.5 or visual acceptance complete.

Codex rejected the prior handoff as malformed and found a deterministic user-facing defect. Complete this bounded repair and return the original seven-section execution output schema.

Required work:

1. Repair the shared speaker-note generator. `src/ci_workflow/renderers/html_ppt/projections/common.py` currently pads short notes by repeatedly appending `请对着屏幕上的数字讲，不要改口成系统流程或内部日志。`. Speaker notes are presenter-facing content, so this engineering/prompt-like filler is forbidden. Remove generic padding. Every A/B/C slide must still have a genuinely page-specific, Chinese-native 150–300 Han-character script with at least one `<strong>` cue. Do not satisfy length by repeating a stock sentence or by mentioning systems, prompts, logs, gates, workflows, fixtures, tests, or internal implementation.

2. Inspect the real A/B/C candidates in Chromium at 1440x900. For B and C, inspect every slide at least through DOM geometry; visually open representative pages including B efficacy, safety, matrix, demographics, flow/disposition and C inclusion, endpoints, statistics, identity and both design paths. Detect and repair page-local clipping, overlapping, tiny or truncated medical labels, excessive empty space, and unreadable disclosure rows. Preserve the locked 1280x720 canvas, Kangzhe master, Task 8.4 runtime and exact gx_fx assets.

3. Preserve data truth. Do not fabricate unavailable values. B must keep APPOINT single-arm non-comparability, all baseline/disposition modules, and `未公开` distinct from zero. C must keep drug + trial + registry identity + score/threshold + timepoint where the source supports them, and two non-ranked design paths.

4. Strengthen deterministic tests so they fail if generic padding or engineering/log/prompt language appears in presenter notes, and fail on the actual page overflow/clipping defect classes you inspect. Regenerate A/B/C HTML and manifests after repair. Add representative Task 8.5 browser screenshots and concise evidence under `docs/acceptance/runs/8.5/`; this is baseline evidence only and must not be called the Task 8.6 all-page final visual acceptance.

5. Run the focused HTML-PPT tests, Ruff on changed Python, and Chromium/WebKit file:// browser contract. Report exact commands, counts, changed files, remaining visual uncertainties, and the current A/B/C input/output hashes. Do not write the runner-owned report file yourself.
