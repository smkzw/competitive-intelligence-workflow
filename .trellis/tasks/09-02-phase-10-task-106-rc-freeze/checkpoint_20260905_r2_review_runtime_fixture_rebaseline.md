# Checkpoint — R2 scientific review/runtime/fixture rebaseline

Date: 2026-09-05
Status: bounded slice accepted; R2 and RC remain open

## Goal and boundary

Close the B/C independent scientific-review authorization path, restore safe
preview fixture operation without making previews acceptable, and make the
HTML-only v1 versus retained non-HTML test boundary explicit. Only the new
English-named repository was used. Sealed Task 10.3-10.5 evidence was not edited.

## Completed

- B/C first render is `rendered_unreviewed`; a real, byte-verified and formally
  parsed `scientific-review-v1` verdict bound to persisted lineage, candidate
  digest, source producer identity, separate reviewer identity and review request
  is the only promotion authority.
- Review promotion is one-way and reuses immutable HTML bytes. Run manifests
  record the reused artifact and real-source acceptance verifies the two-run
  producer/reviewer chain rather than treating reuse as automatically invalid.
- Missing declared preview snapshots self-lock from actual B/C report data and
  remain preview-only. Existing corrupt or mismatched snapshots fail closed.
- HTML-only v1 active tests and retained PDF/HTML-PPT/PPTX regression tests are
  explicit layers. The gate reports both and does not count the retained layer as
  v1 release acceptance.
- B evidence drawers preserve `source_not_listed` for an absent numerator; tests
  prohibit reconstructing n from a percentage.

## Decisive evidence

- `tools/gate.sh`: Ruff passed; strict mypy passed on 204 source files; v1 fast
  `904 passed, 20 deselected`; retained legacy `20 passed, 904 deselected`; layer
  audit `4 passed`; legacy reference scan passed.
- Focused R2/runtime/preview/visual/real-source suite: 103 passed. Three positive
  external Task 10.2 A/B/C checks fail only because the preserved artifacts bind
  an older package digest. This is expected fail-closed behavior and R5
  regeneration debt, not a test waiver.
- Package verification: `PACKAGE_OK version=0.1.0a0 stage=development-candidate`.
- Governed execution audit: three declared ZCode workers present; no manager was
  required; no warnings, route drift, or missing logs.

## Independent Astra review route

The user-requested `gpt-6-astra:high` fresh-context reviewer prompt passed the
workspace preflight. Native admission rejected the model because the local model
catalog does not register it. One same-model CLI compatibility attempt reached
the service and terminated with HTTP 400: Codex CLI 0.147.0 must be upgraded for
`gpt-6-astra`. No substitute model was used and no independent Astra verdict is
claimed. The preflighted prompt is retained for exact retry after runtime support
exists.

## Remaining / next safe action

- R2.4 is not complete: finish object/field GateSpec and blocker-audit coverage,
  then run a real independent-host receipt against a current B/C candidate.
- Continue R2.1-R2.3 contract gaps before declaring the whole R2 milestone done.
- Regenerate the three stale external A/B/C real-source projects only in R5; do
  not mutate old acceptance evidence.
- After archiving this accepted execution packet, remove only its exact temporary
  worker clones and exact debug directory; preserve all source and durable proof.
