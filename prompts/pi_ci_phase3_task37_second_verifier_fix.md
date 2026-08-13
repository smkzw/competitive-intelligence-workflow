You are Pi continuing Task 3.7 in the SAME OMP session `019ff883-4620-7000-8dec-bc07b18315a4` after the isolated Luna verifier's second pass. Do not restart, create a new session, or redo broad exploration.

Read and comply with workspace `AGENTS.md`. Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`. Do not commit or stage. Do not edit approved design/implementation-plan files, Trellis status, context, prompts, run/review/metrics files, legacy workspaces, or user data. Use the existing Task 3.7 allowlist plus only directly affected graph executor/reducer/state/gate model/schema/tests if mechanically necessary. No browser/visual/PPT/PDF, external/clinical research, installation, or security testing.

Read only:
- `AGENTS.md`
- `runs/conference/ci_phase3_task37_review/luna_independent_verifier_followup.md`
- current Task 3.7 source/schema/tests and the directly affected graph/gate contracts needed to repair the findings.

The independent verdict is `FAIL; P0=3; P1=2; P2=1`. Fix the functional correctness bypasses below with RED-first exact attacks. Do not weaken existing tests and do not treat 464 green tests as proof.

1. **Boundary-issued graph authorization (P0).** A public `GraphExecutor.submit()` call from a real `scientific_qc` state can currently self-create valid-looking SHA strings and transition. Make QC acceptance/recovery/block authorization mechanically issued by the scientific-QC boundary and verifiable by the executor/replay path, rather than inferred from caller-supplied shape. A public direct request with fully well-formed fake values must reject. Preserve deterministic replay/checkpoint validation. Prefer a minimal authorization record/event or equivalent issued-and-consumed contract bound to current project/run/report object/from/to/verdict/context/candidate/review/exhaustion digests. Do not introduce cryptographic secrecy or call this security; it is provenance/state correctness. Add exact direct-submit and replay-forgery tests.

2. **Complete GateSpec-to-candidate binding (P0).** A different candidate snapshot with the same `evidence_snapshot_id` and `universe_summary` but altered evidence content must not reuse a gate result. Add a canonical candidate snapshot content digest/fingerprint to `ReportGateResult` (or an equally strong mechanically derived binding), include it in `result_key`, construct it during gate evaluation, and require it to equal the current revalidated snapshot digest in scientific QC. Update directly affected fixtures/tests coherently. Add exact same-ID/same-universe/altered-content attack.

3. **Criteria/spec binding (P0).** Bind the current scientific-QC criteria to the GateSpec version/fingerprint that produced the gate result. At minimum require the declared criteria version to equal `gate_result.spec_version`; if the design requires a compound criteria fingerprint, implement the smallest explicit mapping rather than accepting unrelated values. Add exact `spec_version=9.9`, `criteria_version=1.0` attack.

4. **Mutually exclusive path evidence (P1).** QC accepted path must forbid every veto/recovery/exhaustion flag; recoverable veto must forbid accepted/unfixable/exhaustion flags and record; exhausted veto must forbid accepted/fixable flags. Add deterministic contradiction/forbidden rules so `isolated_qc_accepted + qc_veto`, `qc_veto_fixable + qc_veto_unfixable`, and other cross-path combinations reject even when all required values are otherwise valid. Add exact guard tests for all three destinations.

5. **JSON Schema parity (P1).** Schema must reject duplicate semantic identities (`source_version_id`, locator `fragment_id`, issue `issue_id`) even though JSON Schema cannot express arbitrary property uniqueness with plain `uniqueItems`; use a schema-representable structure or explicit custom contract keyword/check invoked by the package/schema verifier and tested directly. It must also enforce precise locator semantics matching runtime: at least one of field_path/heading/page/table/row/column/paragraph/url, nonblank strings, page >=1, and locator fragments bound where schema can express it. Do not falsely claim JSON Schema alone can enforce cross-array referential integrity; document/test the runtime validator for what Draft 2020-12 cannot express. Add direct negative cases.

6. The verifier's P2 claimed the two anchor documents were absent because it searched exact names at repository index. Before reporting this as a product issue, use `rg --files` narrowly to locate the actual current design/plan filenames/paths. Do not edit them.

Required verification:
- Run every new attack node individually and show its concrete rejection reason.
- Exact Task 3.7 suite; affected gate model/evaluation, executor/reducer/replay, graph/node/transition/checkpoint/partial-delivery/snapshot/no-draft suites.
- Ruff, strict mypy over all affected source, schema negative tests, package verify, `git diff --check`, full pytest.
- Return exact counts, changed files, remaining limits, and precise replay/provenance behavior. Do not self-accept.

Return the complete execution report for the runner to persist to `runs/pi_ci_phase3_task37_second_verifier_fix.md`; do not write that runner-owned report yourself.
