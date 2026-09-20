# Checkpoint — R2.4 P3–P5 闭包

Date: 2026-09-06
Status: P3/P4/P5 completed; P2 freshness decision and P6 conference/governance pending.

## Durable outcome

- Recovery novelty is bound to distinct strategy families plus actual query/access signatures; rounds,
  receipts and information-gain fragment/unit/conflict identities must align exactly.
- Omission review requires independent producer/reviewer context digests and a content-derived input
  digest. Science/conflict terminal claims require `no_material_omission`; technical terminal claims
  require `technical_access_unresolved` and cannot carry fabricated gain.
- Publication-unavailable, scientific-QC exhausted and canonical evidence gaps now publish typed,
  schema-valid blocker packages through the same atomic/idempotent boundary. Existing packages are
  revalidated; symlinks, extra bytes and drift fail closed.
- Candidate universes are bound per report payload inside the independent universe-review digest, so
  an A/B/C projection cannot silently delete an expected candidate or borrow another report universe.
- B baseline incompleteness remains recovery-required and cannot publish a terminal lite blocker.

## Decisive verification

- Focused R2.4 chain before conference repairs: `124 passed`; final affected matrix: `233 passed`.
- Full development gate: Ruff passed; strict-mypy passed for 211 source files; active v1 unit/contract
  `945 passed, 20 deselected`; retained compatibility `20 passed`; layer audit `7 passed`; legacy
  runtime-path check passed.
- Product chain after all repairs: integration/graph/application `579 passed`.
- Fixture cascade repair verification: `42 passed` after recomputing omission-review input digests,
  fixture SHA-256 values and catalog case digests from the authoritative functions.
- Bundle/fresh-install/host contract: `28 passed, 1 skipped` (the skip is environment-conditional real
  host smoke, not converted to accepted).
- Final independent candidate bundle: 328 files, `required-v12`, archive SHA-256
  `8d2aeca2f01fa9039cb16ae26041b0559345d164b48ecbb7cf86ca21908eb011`; temporary directory was
  deleted after verification.

## Remaining decision and safe next action

P2 cannot be honestly closed until the user chooses, through native Ask, the freshness model, default
age windows and historical-cutoff behavior. Continue with independent conference and governance audit
without inventing those semantics. After the decision, add RED tests first, implement the selected
policy in model/schema/YAML/evaluator/override monotonicity, rerun all gates, then close P2/P6.

The native Ask call was attempted after implementation and rejected by the current Default-mode
product surface. No text-form substitute was used. Execution review-gate, execution audit, conference
review-gate and conference structure validation all passed. The two-round ZCode conference reused the
same session and had no fallback; its final P2 typed-error finding was repaired and reverified.

Final cache hygiene removed only `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, and `__pycache__` under
`src/`, `tests/`, and `tools/` (about 65 MiB before removal). Historical `tmp/`, fixtures and runner
evidence were not touched because ownership or acceptance relevance was not safely attributable.

## Boundaries preserved

No reset, checkout, clean, broad staging, production write, credential access, old-workspace access or
RC/release signal. Sealed Task 10.3–10.5 records were not modified.
