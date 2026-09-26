# Codex Conference Review: ci-0924-r24-57-safety-unit-review-20260926

Date: 2026-09-26

## Verdict

**Revise.** The frozen R24-57 development slice is not accepted as presented. The
independent reviewer found two user-visible defects, both reproduced by Codex
against current source and pinned data. This is not a medical or release verdict.

## Boundary Compliance

The route returned `codebuddy-cli/deepseek-v4.1-flash:max` with no fallback;
`validate-conference` returned `ok=true`. The reviewer had no Bash/SQLite
permission, so its 15/12 counts were initially receipt-derived. It also
attempted one read-only Explore dispatch despite the role's no-recursive-
delegation boundary; the delegated probe was denied and produced no data.
Treat the review as advisory with this explicit method limitation.

## Participant Outputs Reviewed

Read the full `runs/conference/ci-0924-r24-57-safety-unit-review-20260926/evidence_single_object.md`.
Its P1 product-link finding and statistical-form finding are actionable; its
regex-only page probes and private-data access limits are not direct acceptance
evidence.

## Conference Panel Review

One reviewer was enough to expose the two deterministic defects. No additional
model opinion is needed before a bounded code repair; clinical class semantics
are a separate newly discovered review object.

## Main-Venue Codex Review

Accepted P1 product-link finding: `report-b.js` guarded unknown rows in table
cells but not in `augmentEvidenceDrawer`. All **414/414** unknown rows in the
locked 514-row A payload have nonempty legacy `product_id`, so the JS path could
turn an explicitly unverified relation into a product-detail link. New source
candidate adds the missing guard in both author and mirror assets; browser
behavior remains NOT_RUN.

Accepted statistical-form finding as P2 with scientific consequence: the B
`participant_proportion` machine token missed the `proportion` alias and fell
through to `event_rate`/`事件发生率`. New source candidate adds the alias; its
focused production projection is still in the pending grouped safety test run.
No numeric risk rate was calculated by this labeling bug.

P2 original-unit visibility is open for a later evidence-drawer change; neither
the normalized `%` nor a number-only quote should be presented as the raw unit
itself. The speculative 0–1 fraction / percent-change counterexamples were not
observed in the pinned safety rows and are not asserted as defects.

## Codex Independent Verification

Codex queried the locked SQLite directly in read-only mode, restricted to
`result_context.domain='adverse_events'` and non-denominator facts: 271 affected
counts, 208 participant counts, **12** `Events/reported_measure/NUMBER`, **9+6=15**
case variants of `Percentage of participants/reported_percentage/NUMBER`, and 8
other participant counts. The 15 percentage raw values span 0–100; the 12 event
counts span 0–20. Direct rows include NCT04811716 66.7/41.7 any-TEAE and 16.7/0
serious-TEAE under distinct source classes, corroborating a separate class
semantics defect. `jq` over the locked A input confirmed 414 unknown safety rows,
all 414 with a nonempty legacy product ID. No SQLite source writes or current
selector change. Ego Lite local-page control is denied in this task, and no
alternate browser route was used: drawer/visual acceptance remains NOT_RUN.

## Final Decision

Frozen R24-57: **FAIL** on the two presentation boundaries; provenance test
results remain bounded development evidence, not invalidated history. Rebuild a
new candidate after the source-class semantic correction, run grouped
production/adjacent tests, and perform browser-level drawer/label inspection
when Ego Lite access is available. Do not rewrite the historical R24-57 receipt
or announce B science/release PASS.
