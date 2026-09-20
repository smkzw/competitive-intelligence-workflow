# Codex Main-Venue Plan: ci-phase8-task82-final-visual-review

Date: 2026-08-31
Objective: 以资深中国临床医学经理视角，对Task 8.2当前A/B/C三类原生PDF共55页进行独立逐页视觉与科学表达验收审阅，重点核对图表诚实性、中文原生表达、信息密度、跨页连续性、裁切重叠和康哲设计规范一致性；不得修改文件或代替Codex最终验收

## Task Decomposition

1. Verify PDF hashes, page counts, and render counts before visual review.
2. Inspect all 55 page renders independently as a Chinese clinical medical manager.
3. Separate release blockers from optional density polish and acceptable truthful whitespace.
4. Recheck B page 5 and C page 13 explicitly, then return a page-referenced defect inventory.

## Source Packet

- A/B/C current PDFs and their 144-dpi renders listed in the conference context.
- `docs/acceptance/runs/8.2/verification/summary.json`.
- Project-owned PDF design specification in `contracts/kangzhe/design_specs/`.

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `visual_single_object` | `grok-build` | `grok-4.6` | `runs/conference/ci-phase8-task82-final-visual-review/visual_single_object.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

- Start pending. Use one runner dispatch and wait up to the 120-minute hard limit; same-session follow-up only for a concrete gap.

## Codex Verification Checklist

- [ ] Participant inspected all 55 pages and reported actual evidence rather than filenames only.
- [ ] No current hash mismatch or stale-render mismatch.
- [ ] Any blocking defect is independently reopened by Codex at native resolution.
- [ ] Machine verification remains green after any repair.
- [ ] Final acceptance is made only by Codex.
