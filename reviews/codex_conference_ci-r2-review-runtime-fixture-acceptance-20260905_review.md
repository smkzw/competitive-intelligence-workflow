# Codex Conference Review: ci-r2-review-runtime-fixture-acceptance-20260905

Date: 2026-09-05

## Verdict

`revise`. The current direction is sound, but R2.4 must not be treated as closed.

## Boundary Compliance

The declared CodeBuddy/deepseek-v4-flash max route completed once with no
fallback. Conference packet validation passed. The participant remained
read-only and did not claim final acceptance. The separately requested
`gpt-6-astra:high` review also completed after the CLI upgrade; it was not a
substitute for the governed conference and is assessed as an additional
independent challenge. Hermes was not used as a transport or hidden fallback.

## Participant Outputs Reviewed

- `runs/conference/ci-r2-review-runtime-fixture-acceptance-20260905/general_single_object.md`
- `runs/conference/ci-r2-stage-review-astra-20260905/reviewer.md`

## Conference Panel Review

Both reviewers independently identified the same load-bearing gaps: no
production receipt issuer tied to captured host execution, promotion occurring
before the format node, no promotion-time portal byte check, and incomplete
fresh-A report-state/review wiring. Astra additionally found an exact bundle
allowlist omission and validity-time/retry weaknesses. CodeBuddy found that the
retained-format gate claim describes only unit/contract smoke, not all 18 marked
files. No reviewer recommended changing the A/B/C product direction.

## Main-Venue Codex Review

Codex reopened the cited source. The promotion-before-format order, missing
fresh-A `report_states`, missing `qc/review_receipt.py` bundle allowlist entry,
absence of promotion-time validity checks, strict two-run acceptance assumption,
and partial retained-test execution are directly confirmed. The existing
structural receipt checks do prevent accidental drift and basic replay, but
cannot prove independent issuance because all inputs are locally recomputable.

Decision:

- Adopt now: productionized receipt issuance trust root, post-format promotion,
  candidate byte binding, validity-time checks, A parity, bundle closure, and
  controlled retry/idempotence tests.
- Modify then adopt: retained-format gate wording/coverage; keep it a bounded
  compatibility smoke rather than reactivating the full excluded product track.
- Defer: screenshot-byte enforcement to the R4 visual acceptance slice;
  `expected_run_id` binding to R6 matrix execution.
- Reject under YAGNI: PKI, external signing service, OS process attestation,
  nonce registry, second receipt system, and reopening PDF/PPT/monitoring scope.

## Codex Independent Verification

Source-level findings were reproduced by direct inspection. The preceding
bounded execution gate remains valid evidence for its declared scope, but it
does not close these newly identified paths. New code changes must begin with
focused RED tests and finish with focused suites plus `tools/gate.sh`. Browser
and real-host issuance were not part of this read-only conference and remain
open.

## Final Decision

Proceed with a new governed R2 repair execution. Do not advance the R2 milestone
until the accepted findings are implemented and a real independent-host issuance
exercise succeeds. No RC or release status change.
