You are the isolated independent verifier for competitive-intelligence workflow rebuild Task 3.7. You did not build this change and may veto it. Do not modify any file.

Read and comply with workspace `AGENTS.md`.

Hard boundaries:
- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Do not read worker prompts, worker reports, stdout, reasoning/session JSONL, reviews, metrics, or prior verifier output.
- Do not write source/tests or any other workspace file. Write exactly one output file: `runs/conference/ci_phase3_task37_review/luna_independent_verifier.md`; runner-owned, so return the full report rather than writing it with tools.
- No browser/visual/PPT/PDF, external clinical research, host installation, or security testing.

Read these files only:
- `AGENTS.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/prd.md`
- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/design.md`
- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/implement.md`
- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/task.json`

After these anchors, inspect only the current uncommitted Task 3.7 source, schema and test diff.

Acceptance question: does the current Task 3.7 diff mechanically enforce that only an independent, current, schema-valid scientific-QC acceptance bound to the exact report candidate, GateSpec result, criteria, coverage, sources, precise locators and immutable review input can transition `scientific_qc -> snapshot_locked`; and do all veto paths route correctly without any report/downstream artifact?

Verify SQ01-SQ04 and actively try to falsify them. At minimum inspect and attack:
- GateSpec pass or raw graph booleans cannot lock without validated authorization material;
- review bundle/verdict/current snapshot/gate contract/current criteria/current coverage/source/locator/input digest bindings, freshness and SHA-256 strictness;
- producer/reviewer identity separation and no producer reasoning/prompt/log fields;
- verdict cannot rewrite candidate facts/claims and scientific-QC node cannot write snapshot/evidence/analysis/artifact;
- accepted vs recoverable veto vs exhausted veto are closed and consistent;
- exhausted veto requires a fully raw-revalidated same-project/same-report DoubleExhaustionRecord; model_copy or cross-project/report attacks fail;
- naked boolean attack begins from the real `scientific_qc` state and is rejected by the guard for missing authorization material;
- A/B/C recoverable/exhausted veto paths leave zero report snapshots, coverage sets/projections, format jobs, render queue, artifact records and report directories;
- typed node output rejects a plain `"accepted"` string;
- schema and package manifest are coherent and the diff contains no unrelated semantic changes.

Run independently:
1. exact Task 3.7 suite;
2. directly affected graph/node/transition/checkpoint/partial-delivery/snapshot suite;
3. at least one additional adversarial script or temporary test (outside tracked files or via inline Python) probing a plausible bypass not already asserted;
4. Ruff, strict mypy for affected source, package verify with `--root .`, schema validation, `git diff --check`, and full pytest if feasible.

Output exactly:
# Task 3.7 Independent Verification
## Verdict
`PASS` only if P0=0 and P1=0; otherwise `FAIL`.
## Counts
`P0=<n>; P1=<n>; P2=<n>`
## Findings
For every finding: severity, exact file/line, reproducible evidence, why it violates the approved contract, minimal repair. If none, say none.
## Commands And Results
List actual commands and exact outcomes.
## Residual Uncertainty
State what remains unverified.

Do not repair, do not self-expand scope, and do not accept based only on existing tests being green.
