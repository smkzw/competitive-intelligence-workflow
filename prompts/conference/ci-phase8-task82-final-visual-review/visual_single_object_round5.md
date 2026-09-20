Delegated mode. You are a bounded conference reviewer, not the user-facing agent.
Follow only this prompt's Hard boundaries, assigned work, and output schema.

Conference role:
- Role id: `visual_single_object`
- Agent/provider/model: `pi` / `cursor` / `cursor-grok-4.6`, effort high
- Same-session continuation: `01a05425-2e14-7000-a169-cdcf911e88c2`.

Hard boundaries:
- Work only in the runner-provided current workspace.
- Do not modify files, browse the internet, start another agent, or claim Codex final authority.
- Runner-managed output file: `runs/conference/ci-phase8-task82-final-visual-review/visual_single_object_round5.md`. Never write it with tools; return the complete report in your final response.

Read only at the start:
- `docs/acceptance/runs/8.2/verification/summary.json`
- `contracts/kangzhe/design_specs/track_pdf.md`

# Task 8.2 targeted round 5

Round 4 found a new C5/C12 line-break regression in the content column. The shared table wrapper now treats clinical time expressions as atomic units across every table column. Verify the current artifact only:

- C PDF: `.artifacts/pdf-complete/report-c.pdf`
- SHA-256: `667715ae76cde0d72149b9fb4d938541ceea71cd07c0001163bfbd9913938343`
- 19 pages
- renders: `docs/acceptance/runs/8.2/verification/C/renders/page-*.png`

Inspect C5、C8、C12、C13 at original resolution and use `pdftotext -layout` where useful. Decide:

1. C5/C12 no longer render `诱导期1` / `6周` or `治疗至第16` / `周`.
2. Every visible `第N周` / `N周` expression in those pages keeps its number and unit together in both content and timepoint columns.
3. The shared wrapper did not introduce clipping, overlap, broken borders, unexpected extra pages, or a new material readability defect.

If closed, explicitly state that the round-4 blocker is closed and no new visual blocker was introduced on the current C hash. This is a targeted current-hash recheck, not a full A/B re-audit.

Output schema:
1. `# Conference Participant Output: ci-phase8-task82-final-visual-review - visual_single_object round 5`
2. `## Boundary Check`
3. `## Current Artifact Verification`
4. `## Targeted Adjudication`
5. `## Remaining Blockers`
6. `## Non-blocking Improvements`
7. `## Recommended Next Step`
