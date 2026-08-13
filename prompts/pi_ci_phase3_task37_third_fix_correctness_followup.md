Continue the SAME Pi/OMP session. Codex inspected the third repair and found two concrete remaining false claims. Do not restart, broaden, or self-accept.

Read only current affected source/tests and this instruction. Work within existing allowlist; no commit/stage; no specs/plans/Trellis/context/run/review/metrics edits.

1. `boundary_proof_digest` is currently recomputed solely from serialized event payload fields in `reducer.py`; any ordinary caller can compute the exact same digest. Therefore direct EventStore append remains forgeable if the attacker computes correctly. Fix the ingress contract mechanically:
   - `EventStore.append()` (public general append) must reject `scientific_qc.authorization.issued` unconditionally with a deterministic error.
   - Add a private/specialized EventStore append path that requires an opaque module-private capability object checked by identity; only `GraphExecutor._issue_scientific_qc_authorization()` receives/uses that capability. There must be no public factory accepting raw fields.
   - Persisted replay still validates full deterministic payload/event ID/evidence/epoch/proof digest. Be honest: Python private symbols are not hostile-process security; the contract is public API provenance correctness.
   - Add exact attack where attacker computes the CORRECT boundary_proof_digest and correct event/id/key but calls public `EventStore.append`: must reject before storage. Add `hasattr`/public API assertion. Real boundary issuance and replay pass.
   - Ensure any generic test/event helper cannot normalize direct specialized append in production.

2. `_revalidate_verdict` currently runs Pydantic + semantic helper, but it does NOT run Draft 2020-12 JSON Schema. The prior report's “package/schema verifier uses same boundary” is false. Create one production validator function that performs, in order, packaged `schemas/scientific-qc-verdict.schema.json` Draft202012 validation + Pydantic model validation + semantic validation, with deterministic errors. `_revalidate_verdict` must call it. Resolve schema path in both source tree and packaged-install layout without accepting caller-selected schema. Package verification or a dedicated contract test must call the same validator. Add a negative payload that Pydantic/semantic alone would otherwise miss but schema rejects, and prove public apply rejects before authorization write.

Also recheck one-time consumption and nested SourceRef locator validation remain closed.

Run exact new attacks, exact Task3.7, affected EventStore/executor/reducer/replay/schema/package suites, Ruff, strict mypy, diff, full pytest. Return exact counts and changed files for runner-owned `runs/pi_ci_phase3_task37_third_fix_correctness_followup.md`. Do not write the report or self-accept.
