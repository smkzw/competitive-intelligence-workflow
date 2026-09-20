# Checkpoint — R2 B/C scientific wiring and independent review

- **Date**: 2026-09-05
- **Status**: bounded B/C wiring accepted; R2 remains open
- **Goal**: connect fresh B/C research packages to evidence ingestion, deterministic
  gates, immutable snapshots, independent scientific review and candidate-only HTML
  without trusting producer decisions or preview data.

## Completed

- Governed execution `ci-r2-bc-research-package-wiring-20260905` completed with three
  isolated workers and manager review. Worker 01 was rejected wholesale because its
  generic package trusted a caller-supplied passed decision; worker 02/03 changes were
  selectively integrated and repaired by Codex.
- Added generic evidence-only ingestion with immutable evidence snapshots and canonical
  fact-version aliases. It never persists a caller-provided gate decision.
- Added typed B and C fresh research packages, source/fact/claim closure, deterministic
  gate construction, immutable report snapshots, producer/reviewer separation and
  content-digest binding.
- RunService now executes package → ingestion → gate → report snapshot → scientific QC
  → analysis → render for B/C. Candidate reports are explicitly
  `scientifically_reviewed_rendered_candidate`; report-data shortcuts remain
  `rendered_unreviewed`.
- B efficacy numerator/denominator are typed and portal-bound; unsafe same-value legacy
  numerator backfill was removed. Numeric zero is not relabeled without explicit source
  disclosure state.
- Gate fact-version ids are remapped to versions actually persisted in the evidence
  snapshot. B and C report projection reopen and verify that immutable snapshot.
- Deterministic B/C gate blocks now finalize as a recoverable `running` state, write an
  idempotent recovery work item and current manifest, and generate no HTML.
- C endpoint and timepoint observations now share a normalized `endpoint_key`; key sets
  must match per trial, including multiple endpoint scenarios.
- Independent review now must postdate all captured sources in addition to binding the
  exact content digest and using a different producer/reviewer identity.

## Independent conference

- `ci-r2-bc-science-acceptance-20260905` completed two rounds on the same CodeBuddy
  session, with no fallback or re-dispatch.
- Round 1 found two P1 and multiple P2/P3 issues. Round 2 correctly retracted the P1s
  after repair. Codex rejected two stale residual claims by direct current-byte
  inspection: numerator backfill no longer exists and C endpoint/timepoint validation is
  now key-paired.
- Conference validation and review-gate passed. Verdict is **Revise**, not R2 or RC
  acceptance.

## Verification

- Focused B/C scientific/run-service suite: **57 passed**.
- Full Gate: Ruff passed; strict mypy passed for **200 source files**; **885** unit and
  contract tests passed; forbidden legacy dependency scan passed.
- Review target SHA-256:
  - `fresh_research_ingestion.py`: `96b563cd810cdb4239c0fb9df56dcd8297d6c690e2bd97c8520e398503ce157c`
  - `fresh_b_research_package.py`: `56af6d332aafba622410be5778b5e3e91fba2364919c1151c369f97add5e8a51`
  - `fresh_c_research_package.py`: `d23c2634630055b771cc9d13797f79dd5c0bff1f98db787983957e5ebcbed179`
  - `run_service.py`: `351b7ca02dad3cdc4dd23e347111f00ad1bd5a4086e9ea7aaed10c4d5edc1897`
  - `report_b.py`: `c587d355273b41c40339f00c35b2de4e52359c8b3527442fbb78df599d30cc78`
  - `reports/b/efficacy.py`: `791fa3845bfbb8f2c70000db2d89227f0a3c6c15c491bcc3e5658e3417459f74`
  - `reports/c/contracts.py`: `7c824d00731f6414b98f9c87e1d2c70549e24f50aa382bdc1bb31d21395dcc34`
  - `B-v1.yaml`: `96acb530d339e9a117ff6771d49c6d6d4f247149d31ed4b569e7d2dc29d60e8a`
  - `C-v1.yaml`: `62a24a7cf1b03cc5acd4660577d5888d20b81ee1554b5d624398aeaa761f56fb`

## Disk hygiene

- The three governed execution clones were deleted after acceptance; each had reported
  approximately 5.6 GB logical size.
- No normative source, review, receipt, snapshot, protected runtime/session state or
  current recovery point was removed.

## Open defects / non-acceptance

- A typed double-exhaustion record and terminal fresh B/C evidence-insufficient audit/page
  flow do not yet exist. A recoverable gate block must not be promoted to terminal state
  without two distinct recovery strategies and clean-context omission review.
- Reviewer identity is still package-asserted. Codex/Hermes/OMP adapters need an immutable
  host execution receipt proving a separate context and binding its review artifact.
- `rendered_unreviewed` preview/data paths remain reachable in development and must be
  excluded from release acceptance and bundle entry surfaces.
- Deterministic effect recomputation is not implemented. Source-direct effect evidence is
  retained conservatively until a clinical recomputation contract is explicitly defined.
- Eight indications × A/B/C, all-page/four-viewport/two-browser review, three-host install,
  refresh/recovery and RC identity binding remain incomplete.

## Next safe action

Start the next governed R2 execution slice with three independent work items: terminal
double-exhaustion/blocker contracts, immutable independent-review receipt binding, and
release-surface fail-closed tests for unreviewed preview paths. Merge only after Codex
reproduces focused RED/GREEN evidence and the full Gate remains green.
