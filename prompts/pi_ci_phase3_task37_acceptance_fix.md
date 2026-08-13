You are Pi continuing Task 3.7 in the same OMP session after Codex's first acceptance review. Do not restart or create a new session.

Read and comply with workspace `AGENTS.md`.

Hard boundaries:
- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Read these files only: `context/ci_phase3_task37_context.md`, `runs/pi_ci_phase3_task37.md`, the current Task 3.7 changed files, `src/ci_workflow/graph/guards.py`, and `tests/graph/test_graph_node_contracts.py`.
- Continue to use the original Task 3.7 source/test/schema allowlist. This repair explicitly also authorizes the minimum coherent edits to `src/ci_workflow/graph/guards.py` and `tests/graph/test_graph_node_contracts.py`. Do not edit specs, plans, Trellis, context, prompts, run/review/metrics files, legacy workspaces, or user data.
- Do not commit or stage. Write exactly one output file: `runs/pi_ci_phase3_task37_acceptance_fix.md`; runner-owned, so return the report rather than writing it with tools.
- No browser/visual/PPT/PDF, external or clinical-content research, host installation, or security testing.

Read these files only:
- `AGENTS.md`
- `context/ci_phase3_task37_context.md`
- `runs/pi_ci_phase3_task37.md`
- `src/ci_workflow/graph/guards.py`
- `tests/graph/test_graph_node_contracts.py`

After these anchors, read only the current Task 3.7 changed files needed to repair and verify the findings below.

Codex verdict: REVISE. The current 464-pass result contains functional false-greens. Close every item below with behavior-level tests; do not explain them away.

1. The public boundary currently accepts `review_bundle=None` and never uses the bundle. Make a schema-valid `ScientificQcReviewBundle` mandatory. Revalidate it from raw serialized content at the public boundary. Require exact agreement among current candidate snapshot, GateSpec result, current coverage identity/digest, bundle and verdict for project, report kind/version, candidate snapshot ID/content digest, criteria version, GateSpec result key, coverage ID/digest and source references/locators. Recompute `bundle.input_digest` and require `verdict.review_input_digest == bundle.input_digest`. Tests must call the real boundary with the real bundle; `None`, stale/tampered bundle, arbitrary review digest or verdict/bundle source drift must fail closed.

2. Coverage binding cannot be optional. Require the current coverage ID and digest at the boundary and compare both bundle and verdict to them. Bind `verdict.contract_version` to `gate_result.contract_version`. Do not allow omitted current coverage or a caller-selected alternate contract to lock.

3. Source and issue consistency must be mechanical: verdict source refs and precise locators must be identical to the validated review bundle; every issue's source/fragment must exist in those reviewed refs. An accepted verdict may have no blocking issues; a veto must carry at least one blocking issue. Reject semantically empty/generic evidence.

4. Veto routing cannot infer recoverable/exhausted merely from whether an arbitrary exhaustion object was supplied. Add a closed explicit veto disposition to the verdict (accepted must not have one; veto must have exactly one of recoverable/exhausted). Recoverable veto rejects an exhaustion record. Exhausted veto requires a raw-revalidated `DoubleExhaustionRecord`, bound to the same project/report, and must not accept `model_copy` forged role/content/digest. Preserve Task 3.2 no-downstream assertions before and after.

5. Close the naked-boolean graph bypass. The existing test is false-green because its forged object was never driven to `scientific_qc`; it was rejected for current-state mismatch. Drive the forged object to `scientific_qc` first. A direct transition with only `{"isolated_qc_accepted": true}` must still be guard-rejected. Make the graph guard require the verified verdict authorization material emitted only by the capability boundary (at minimum verdict ID/digest, candidate snapshot ID/digest and review input digest), and have the capability include it. Add exact assertions on rejection reason/guard evidence. Update directly affected existing transition/node tests coherently; do not weaken them.

6. The node contract cannot keep a plain `qc_verdict: str` merely because an old fixture expected it. Change the scientific-QC node output to a typed verdict reference/digest object, update the exact node-contract fixture, and prove a plain `"accepted"` string fails output validation. This is the approved Task 3.7 contract, not a compatibility reason to preserve a false-green surface.

7. Strengthen SQ03 so it exercises the actual public capability boundary, not `digest_after = digest_before` or construction of two unrelated models. Prove the boundary accepts a valid isolated bundle/verdict, the candidate content remains byte-for-byte unchanged, forbidden producer context is rejected, and verdicts cannot carry rewritten candidate facts/claims.

8. Restore `package-manifest.json` to its pre-task formatting and add only the one schema list entry, so the diff is surgical rather than a 259-line formatting rewrite.

Required verification:
- Run each repaired exact node first to demonstrate it now detects the previously accepted attack.
- Run the exact Task 3.7 suite.
- Run directly related graph guard/transition/node/snapshot/no-draft regressions.
- Ruff on every changed Python/test file, strict mypy on affected source packages, package/schema validation, `git diff --check`, and full suite.
- Report exact commands/counts and the corrected attack evidence. Do not claim acceptance; Codex and an isolated reviewer own it.
