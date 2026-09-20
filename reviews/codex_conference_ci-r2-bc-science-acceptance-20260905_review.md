# Codex Conference Review: ci-r2-bc-science-acceptance-20260905

Date: 2026-09-05

## Verdict

**Revise, with both original P1 findings closed.** The fresh B/C chain is materially
stronger and the development gate is green, but R2 is not accepted: terminal
double-exhaustion handling, host-verifiable independent-review receipts, and release
surface isolation for `rendered_unreviewed` paths remain open.

## Boundary Compliance

- Participant stayed read-only in the authorized new workspace and did not claim final
  acceptance.
- Route remained `codebuddy/codebuddy-cli/deepseek-v4-flash:max`; round 2 resumed
  session `980383c6-05cb-4589-af0f-7e9021bb2f63` with no fallback or re-dispatch.
- Hermes was not the selected route for this packet and was not used as an undeclared
  transport or substitute.
- The participant could not run Bash. Codex therefore reproduced findings against the
  current bytes and ran the deterministic checks itself.

## Participant Outputs Reviewed

- `runs/conference/ci-r2-bc-science-acceptance-20260905/general_single_object.md`
- Round 1 found two P1 defects and several P2/P3 gaps.
- Round 2 correctly retracted the original P1 classifications after the source repairs,
  but incorrectly retained two stale findings: efficacy numerator backfill had already
  been removed, and C endpoint/timepoint validation had already become key-paired.
  These claims are rejected by direct byte inspection and focused tests.

## Conference Panel Review

Accepted findings and dispositions:

1. **P1 blocked-run classification:** fixed. B/C deterministic gate blocks now produce
   `running + recovery_required`, an idempotent recovery work item, current manifest,
   and no HTML. They do not masquerade as malformed input or completed reports.
2. **P1 efficacy numerator contamination:** fixed. `numerator` is typed and portal-bound;
   the renderer no longer performs cross-row legacy backfill.
3. **P2 fact-version binding:** fixed. Runtime gate bindings map to persisted immutable
   fact versions; B and C projections reopen the evidence snapshot and verify membership.
4. **P2 C endpoint/timepoint pairing:** fixed. Each endpoint/timepoint observation has a
   normalized `endpoint_key`; per-trial endpoint and timepoint key sets must match.
5. **P3 zero relabeling:** fixed. The renderer no longer converts numeric zero into
   `reported_zero` without explicit source disclosure state.
6. **P2 terminal double exhaustion:** accepted as open. The current recovery work item
   deliberately does not fabricate two exhausted recovery rounds or a terminal evidence-
   insufficient page. A typed, receipt-bound terminal handoff still needs implementation.
7. **P2 release-surface isolation:** accepted as open. `rendered_unreviewed` preview/data
   paths must be prevented from satisfying release acceptance.
8. **P3 independent context:** partially closed only. Producer/reviewer inequality,
   content-digest binding, and review-after-acquisition ordering are enforced; host-level
   clean-context creation still needs an immutable execution receipt.
9. **P3 effect-difference policy:** retained as a conservative unresolved design item.
   Current source-direct behavior is safer than silently computing a clinically invalid
   effect; deterministic recomputation needs an explicit rule contract before addition.

## Main-Venue Codex Review

Codex inspected the current renderer and C package validator directly. The exact review
target hashes are recorded in the associated checkpoint. No RC-frozen conclusion is
drawn from this moving development tree.

The participant's recommendation to freeze a review target is accepted for RC, not for
normal R2 TDD iteration. R2 remains a development phase and may change under tests;
the final RC conference will bind a commit and source-set hash.

## Codex Independent Verification

- Focused B/C package and run-service suite: **57 passed**.
- Added and passed negative coverage for portal numerator drift, blocked B/C recovery
  state, stale review timestamps, and a second C endpoint lacking its own timepoint.
- Full development gate: Ruff passed; strict mypy passed for **200 source files**;
  **885 unit/contract tests passed**; forbidden legacy dependency scan passed.
- Browser acceptance was not rerun because this pass changed scientific contracts and
  blocked-state orchestration, not portal layout. R3 visual acceptance remains separate.

## Final Decision

Conference objective is closed as a **revision decision**, not R2 acceptance. Continue
with the smallest next R2 slice: typed double-exhaustion/terminal blocker flow, immutable
independent-review receipt binding, and release exclusion of unreviewed preview paths.
