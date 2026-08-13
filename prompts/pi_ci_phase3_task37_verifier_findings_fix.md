You are Pi continuing Task 3.7 in the same OMP session after the isolated Luna verifier vetoed the change. Do not restart or create a new session.

Read and comply with workspace `AGENTS.md`.

Hard boundaries:
- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Read these files only: `AGENTS.md`, `context/ci_phase3_task37_context.md`, `runs/conference/ci_phase3_task37_review/luna_independent_verifier.md`, and the current Task 3.7 source/schema/tests directly needed for these findings.
- Use the existing Task 3.7 and directly affected graph/node/schema/test allowlist. Do not edit approved specs/plans, Trellis, context, prompts, run/review/metrics files, legacy workspaces, or user data.
- Do not commit or stage. Write exactly one output file: `runs/pi_ci_phase3_task37_verifier_findings_fix.md`; runner-owned, so return the report rather than writing it.
- No browser/visual/PPT/PDF, external/clinical research, host installation, or security testing.

Read these files only:
- `AGENTS.md`
- `context/ci_phase3_task37_context.md`
- `runs/conference/ci_phase3_task37_review/luna_independent_verifier.md`

After these anchors, read only the current Task 3.7 source, schema and tests directly needed for these findings.

Independent verdict: FAIL P0=4 P1=2. Close the concrete functional bypasses below. Do not weaken tests or claim that green existing tests are enough.

1. Cross-snapshot GateSpec: require `gate_result.evidence_snapshot_id == current snapshot.evidence_snapshot_id` and `gate_result.universe_summary == current snapshot.universe_summary` before any verdict transition. Add exact attacks.

2. Cross-report graph object: bind the reviewed report object identity into both review bundle and verdict (e.g. `report_object_id`) and into their digests/schema. Require public boundary `object_id` to equal both. Tests must show an A verdict cannot transition a B/different object already in `scientific_qc`.

3. Empty issue evidence: make every `ScientificIssue.fragment_ids` non-empty, unique, nonblank and bound to its source; add Pydantic and JSON Schema attacks.

4. Guard authorization shape: direct transitions from a real `scientific_qc` state with non-SHA digest strings or mismatched candidate/report authorization must be rejected. Extend the deterministic guard contract enough to validate lowercase SHA-256 fields and exact report-object binding. Capability must emit the matching validated fields. Add assertions for rejection reason, not just unchanged state. Do not introduce secrets or call this security; it is graph-state correctness.

5. JSON Schema must independently reject structurally inconsistent verdicts, not merely rely on Pydantic runtime. Ensure minItems/uniqueItems for source/fragment/claim/fact/locator/issue identities where applicable; require non-empty issue fragment IDs; encode accepted => no veto disposition/no blocking issues and veto => required disposition plus at least one blocking issue as far as Draft 2020-12 supports. Add direct `Draft202012Validator` negative cases.

6. Exhausted veto graph guard must require a validated exhaustion record digest in authorization material; capability derives it only after raw revalidation and same-project/same-report checks. Direct exhausted transition without this digest or with non-SHA digest must reject. Recoverable veto must not emit it.

7. Authority-bound current criteria/coverage/identity: do not silently invent a Phase 4 coverage persistence layer. Inspect current Phase 3 source of truth and produce the smallest coherent solution available now. At minimum remove caller freedom to supply criteria/coverage values independently of the immutable review bundle: derive the current values from one typed immutable `ScientificQcCurrentContext`/equivalent created by the orchestration layer, digest it, bind it to bundle+verdict+guard evidence, and reject `model_copy`/dict drift. Include producer identity plus candidate/gate/coverage/criteria/source lineage in that context. If there is an existing persistent record, load it; if not, make the typed current context explicit and record in the report that persistence is deferred rather than claiming database authority. Tests must prove arbitrary separate strings no longer select a different current context.

8. Independent identity: bind producer/reviewer separation to the typed current context's producer identity and the boundary's reviewer actor identity. Do not let both be chosen independently in verdict/bundle. If no host identity authority exists in Phase 3, fail closed unless the orchestration supplies the reviewer actor explicitly and bind it into transition actor/verdict; document the exact remaining trust boundary without overstating it.

Required verification:
- Add and run targeted attacks corresponding to all Luna findings.
- Exact Task 3.7 suite; affected graph/node/transition/checkpoint/partial-delivery/snapshot/no-draft suites.
- Ruff, strict mypy, JSON Schema negative contract tests, package verify `--root .`, `git diff --check`, full pytest.
- Return exact counts, concrete attack outcomes and an honest statement of any remaining authority/persistence boundary. Do not self-accept.
