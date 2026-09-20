# Codex Conference Review: ci-rebaseline-r2-science-review-20260905

Date: 2026-09-05

## Verdict

Revise. The participant completed successfully, but its aggregate PASS labels
overstated G04, G07, and G08. Codex reproduced the useful findings and retained
the cross-report VETO; no R2 or M2 acceptance is issued.

## Boundary Compliance

- Read-only participant stayed inside the authorized repository and did not use
  the prohibited former workspace.
- Runner verified `zcode/zcode/GLM-5.3-Flash`, effort `max`; one full round,
  no fallback, no terminal failure.
- The global Hermes workflow guard and conference runner supplied the governed
  packet, route identity, persistence, and audit boundary.
- No participant implementation changes were accepted as evidence of done.

## Participant Outputs Reviewed

`runs/conference/ci-rebaseline-r2-science-review-20260905/general_single_object.md`
and its runner log were reviewed in full.

## Conference Panel Review

- Accepted: the participant correctly identified the B/C scientific-QC reachability
  defect, the all-three-views typed-graph defect, stale multi-format integration
  tests, missing closure convergence proof, and unsafe baseline population
  normalization.
- Rejected: G07 is not PASS. Approved v1.3 explicitly forbids copying a validated
  user file; `ManualInboxService.accept()` copied it into `evidence/raw`.
- Rejected: G08 is not fully PASS. Exact string equality is not model-assisted
  medical semantic adjudication, and baseline grouping ignored analysis population.
- Corrected: `access_blocked` may count as route completion only when a typed route
  receipt retains the diagnostic; it is not scientific absence and cannot satisfy
  a missing critical fact.

## Main-Venue Codex Review

Codex added RED tests and implemented the first contract repairs:

- explicit zero-addition universe convergence and representable empty-universe state;
- conditional recovery with contiguous rounds and two distinct saturated tail rounds;
- diagnosed `access_blocked` route completion;
- manual-file validation receipts plus no raw/library copy;
- report-scoped scientific-QC graph input;
- indication grammar cleanup;
- fail-closed baseline population grouping;
- typed model-assisted semantic adjudication whose result cannot override hard
  conflicts in direction, unit, estimand, denominator, analysis set/form, or scale.

Focused contract and adjacent integration tests passed after the repairs. Ruff,
strict mypy, and the 861-test unit/contract shutter also passed. Broader runtime,
B/C research-package wiring, browser matrix, and visual conference remain pending.

## Codex Independent Verification

- `uv run ruff check src tools tests`: passed at the first post-repair static pass.
- `uv run mypy --strict src/ci_workflow`: passed, 175 source files.
- `uv run pytest tests/unit tests/contract -q -p no:cacheprovider`: 861 passed.
- Focused scientific/manual/semantic suite: 48 passed across the two grouped runs.
- Migrated stale public multi-format tests: 15 passed.
- Browser runtime download is still in progress; no visual acceptance claimed.

## Final Decision

Keep R2 open. Finish B/C research-to-gate-to-snapshot-to-independent-QC wiring,
remove preview paths that falsely label data fixtures `snapshot_locked`, run the
broader non-browser suite, then perform the separate browser/visual execution and
conference gates. Only then may Codex consider M2/M3 acceptance.
