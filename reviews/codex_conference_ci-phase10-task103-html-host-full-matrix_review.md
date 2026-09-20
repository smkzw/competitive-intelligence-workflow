# Codex Conference Review: ci-phase10-task103-html-host-full-matrix

Date: 2026-09-02

## Verdict

Pass for Task 10.3 pre-RC HTML-only rehearsal. This is not an RC freeze or a
formal release acceptance.

## Boundary Compliance

- The registered conference participant stayed read-only and did not modify the
  R13k candidate.
- The declared output is site HTML only; PDF, HTML-PPT and PPTX remain future
  owners under ADR 0013.
- Codex retained final browser, visual and user-facing acceptance authority.
- The participant's static review is supporting evidence, not a substitute for
  Codex's current ego(lite) run.

## Participant Outputs Reviewed

- Registered `visual_single_object`: `pi / cms-router / minimax-m3 / xhigh`,
  completed without fallback.
- Earlier R13k same-session amendments were also reviewed: Gemini completed and
  passed; MiniMax completed and passed; ZCode's existing session could not be
  resumed and produced no R13k verdict, so it was not counted as agreement.

## Conference Panel Review

- The registered participant confirmed the R13k bundle digest, current run and
  pre-RC identities, B baseline page partition (4/2/0/1 chart groups), 11
  disposition groups, three ego receipts and three distinct host-smoke runs.
- It found no P0/P1. Its stale-checkpoint concern is resolved by the new R13k
  completion checkpoint. Its A drawer-click concern was independently disproved
  by Codex after scrolling the real bubble into view before using ego's click
  helper. Its limited B time-window fixture coverage remains a non-blocking
  future test-data improvement.

## Main-Venue Codex Review

- R13k supersedes R13j for Task 10.3. Bundle SHA-256:
  `d703b770b34a05dc1512bdac407947325b30158da4d476130d24bc933ba669af`
  (417 files).
- Full six-stage rehearsal returned `PRE_RC_REHEARSAL_OK` for three reports,
  HTML only, three real hosts and 23 catalog cases; 16 were rehearsed, two stay
  with future owners, one is not applicable and four are outside this suite.
  No release case was closed.
- Codex, Hermes and OMP each completed a distinct real host-smoke process,
  session and run while binding the same candidate package digest.
- B baseline duplication and disposition-title repetition are fixed without
  fabricating missing clinical facts.
- No new source change is required from the conference findings.

## Codex Independent Verification

- Focused regression tests and Ruff passed for the Report B change. The B
  non-browser suite passed 217 tests; 91 Playwright tests could not launch only
  because the deliberately removed browser cache is absent and are outside the
  Task 10.3 ego(lite)-only route.
- Ego(lite) opened all 57 routes at 1024x768, 1280x800, 1440x900 and 1920x1080:
  228 page/viewport checks, zero broken images, zero page-level horizontal
  overflow and no visible engineering markers. Two under-100-character alerts
  were verified as explicit, scientifically honest empty states.
- Interactions passed: A matrix bubble -> product insight with four tabs; B
  product filter `未设置筛选` -> `已选 1 项`; C design-map product filter 48 -> 12
  visible rows.
- Codex rechecked the repaired B pages in the live R13k site. The overview keeps
  four charts, demographics has age/sex, disease context has a dedicated empty
  state, severity has baseline EASI, and disposition titles have one indicator
  prefix.
- Ego's screenshot operation timed out repeatedly even on a light page. The
  receipts state that limitation and do not claim or reuse screenshots. Current
  DOM/interaction evidence plus two independent R13k visual amendments support
  this pre-RC decision; pixel-diff evidence is not claimed.
- `mypy --strict` on `report_b.py` still reports eight pre-existing type errors;
  this change introduced no new reported error. This is not represented as a
  green mypy result.

## Final Decision

Accept R13k as the completed Task 10.3 HTML-only pre-RC candidate. Preserve the
candidate, receipts, host evidence and conference outputs. Do not call it an RC
freeze or release, and do not close the future PDF/PPT, recovery or legacy
cutover responsibilities.
