You are Pi continuing Task 3.7 in the SAME OMP session `019ff883-4620-7000-8dec-bc07b18315a4`. Do not restart or create a new session. The isolated Luna second continuation still found `P0=1; P1=2`.

Read `AGENTS.md`, `runs/conference/ci_phase3_task37_review/luna_independent_verifier_followup_2.md`, then only directly affected Task 3.7 source/schema/tests. Work only inside this repo. Do not commit/stage. Do not edit approved specs/plans/Trellis/context/prompts/run/review/metrics. No browser/visual/external/security work. This is functional graph provenance correctness.

Close these three findings RED-first:

1. **Remove public self-issuance and direct-append acceptance (P0).** `GraphExecutor.issue_scientific_qc_authorization()` must no longer be a public caller-supplied issuance API. Ordinary code must not be able to provide arbitrary verdict/candidate/context/SHA fields and obtain an accepted authorization. Refactor to the smallest coherent internal boundary capability:
   - The only supported issuance path is the already-validating `apply_scientific_qc_verdict` boundary, after it raw-revalidates current context + review bundle + verdict + GateResult + full candidate snapshot + reviewer identity + exhaustion and computes all digests itself.
   - Use an internal opaque capability/proof object whose construction is module-private and identity-checked by the executor; remove/rename the public issuance method. Tests outside the boundary must not construct it. Do not expose a public factory accepting raw authorization fields.
   - An authorization event must carry enough canonical proof/binding for replay validation. A caller directly appending a shape-correct event without the internal issued proof must be rejected by EventStore/reducer/replay. Since Python is not a hostile security boundary, do not pretend underscores are cryptography; the mechanical contract is that public APIs cannot mint it, issuance proof is opaque/non-serializable at ingress, and persisted authorization carries a deterministic boundary-proof digest recomputed from the fully validated inputs. If a durable issuer registry/receipt is needed, keep it project/run scoped and generated only by the boundary.
   - Rewrite existing tests/helpers that call the public issuance method: valid test setup must go through the real `apply_scientific_qc_verdict` boundary, or a test-only fixture isolated from production. Do not normalize direct issuance in production tests.
   - Exact attacks: ordinary public method absent/unavailable; direct EventStore append of a shape-correct authorization followed by transition/replay fails; real boundary path passes.

2. **One-time consumption / epoch (P1).** A QC authorization may be consumed once for a new transition. Exact idempotent replay of the same request/event remains valid, but after `scientific_qc -> recovering -> scientific_qc`, a new request ID using the old authorization must reject. Track consumption deterministically in executor and reducer state, bind authorization to the current QC entry epoch or accepted transition event, and test normal replay, crash replay, and recovery-cycle reuse.

3. **Production semantic validation parity (P1).** `check_scientific_qc_verdict_semantics()` must run inside `_revalidate_verdict`/public boundary before issuance, after JSON Schema validation of the raw verdict against the packaged schema. Raise a deterministic boundary error on any schema/semantic violation. Complete model/runtime checks for:
   - duplicate `SourceRef.locators[].fragment_id` even when locator details differ;
   - each nested source locator fragment belongs to that same SourceRef.fragment_ids;
   - top-level locators bind declared fragments;
   - unique source_version_id, top-level locator fragment_id, issue_id;
   - issue source/fragment binding and precise locator dimensions.
   Add attacks showing Pydantic/schema/semantic/public apply all reject the nested duplicate/unbound cases before any authorization event is written. Ensure the formal package/schema verifier uses the same schema+semantic validator rather than a test-only helper.

Preserve the already-closed complete candidate digest, spec/criteria binding, contradictions, typed node output, and no-downstream veto behavior.

Required verification: each attack node individually with outcomes; exact Task 3.7; affected executor/reducer/replay/gate/graph/node/checkpoint/partial/no-draft; Ruff; strict mypy; schema/package; diff; full pytest. Return exact counts and changed files. Do not self-accept. Return runner report for `runs/pi_ci_phase3_task37_third_verifier_fix.md`; do not write it yourself.
