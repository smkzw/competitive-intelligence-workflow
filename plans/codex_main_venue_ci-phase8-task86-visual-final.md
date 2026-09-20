# Codex Main-Venue Plan: ci-phase8-task86-visual-final

Date: 2026-08-31
Objective: 以真实中文资深医学经理视角审阅 A/B/C 62 页 HTML-PPT 在四视口与双浏览器的最终原图，核对康哲设计规范、中文原生表达、图表与表格可读性、视觉层级、信息密度和跨页一致性；只报告缺陷，不替代 Codex 终验

## Task Decomposition

1. Bind the three candidate HTML hashes and the 496-image final ledger.
2. Inspect all 62 Chromium 1920×1080 originals as a Chinese senior medical manager.
3. Recheck all pages at 1280×800 and stress-test 2048×1024; use WebKit originals
   for any page whose composition, wrapping, or chart labels may differ.
4. Record page-level findings, distinguishing visible evidence, medical-language
   judgement, and aesthetic preference; do not pass on automation alone.
5. Codex compares independent reviews, performs its own original-image acceptance,
   repairs P0/P1 defects, and repeats the same-session review when needed.

## Source Packet

- `context/ci-phase8-task86-visual-final_conference_context.md`
- `docs/acceptance/runs/8.6/visual-final/visual-baseline-ledger.{md,json}`
- `docs/acceptance/runs/8.6/visual-final/screenshots/`
- `contracts/kangzhe/design_specs/{project_profile,core,track_htmlppt,htmlppt_fx}.md`
- `.trellis/tasks/08-31-phase-8-task-86-html-ppt-visual-acceptance/{prd,design}.md`

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `visual_single_object` | `kimi-code` | `k3-256k` | `runs/conference/ci-phase8-task86-visual-final/visual_single_object.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

- Connectivity: MiniMax passed; CodeBuddy passed; Cursor/default failed exact
  title/page recognition twice in session `01a0563d-fcc8-7000-a8d5-350a242d88af`.
- The governed participant begins only after prompt preflight; wait up to 120 minutes.
- Same-session follow-up is used only for a concrete missing page range or repair check.

## Codex Verification Checklist

- Confirm 62 page ids and 496 screenshots bind to the three final hashes.
- Inspect every Chromium 1920×1080 original personally; contact sheets are index only.
- Inspect 1280×800 and 2048×1024 originals for every page before closure.
- Confirm no horizontal dragging, cropping, or unreadable chart/table labels.
- Confirm audience copy contains no backend keys, prompt language, or translated Chinese.
- Confirm notes/log material stays outside the audience surface.
- Run HTML-PPT tests, final collector, review-gate, and Trellis close only after visual pass.
