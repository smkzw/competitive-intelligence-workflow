You are Pi continuing Task 3.7 in the same OMP session after Codex's second correctness review. Do not restart or create a new session.

Read and comply with workspace `AGENTS.md`.

Hard boundaries:
- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Read these files only: `AGENTS.md`, `context/ci_phase3_task37_context.md`, `runs/pi_ci_phase3_task37_acceptance_fix.md`, and the current Task 3.7 changed source/tests needed for this correction.
- Use the already-authorized Task 3.7 files and directly affected graph/node tests only. Do not edit specs, plans, Trellis, context, prompts, run/review/metrics files, legacy workspaces, or user data.
- Do not commit or stage. Write exactly one output file: `runs/pi_ci_phase3_task37_correctness_followup.md`; runner-owned, so return the report rather than writing it with tools.
- No browser/visual/PPT/PDF, external or clinical-content research, host installation, or security testing.

Read these files only:
- `AGENTS.md`
- `context/ci_phase3_task37_context.md`
- `runs/pi_ci_phase3_task37_acceptance_fix.md`

After these anchors, read only the current Task 3.7 changed source and tests needed for this correction.

Codex correctness review found four remaining functional false-green surfaces. Close them with targeted attack tests before final acceptance:

1. Digest fields are only nonblank strings. Add strict lowercase SHA-256 validation for `candidate_content_digest`, `coverage_digest`, and `review_input_digest` wherever they are declared. A bundle/verdict/current coverage using `"x"`, uppercase, wrong length or non-hex must fail before graph transition. Preserve actual deterministic digests.

2. A `LocatorDetail` containing only `document_role` currently counts as a “precise locator”. Require at least one real retrievable locator dimension among field path, heading, page, table, row, column, paragraph or URL, with nonblank text and page >= 1 where present. Add attacks proving role-only and blank locator values fail. Also require non-empty `fragment_ids`, `claim_ids`, `fact_version_ids`, and `locators` in every `SourceRef`; a nominal source with no claim/fact lineage cannot support acceptance.

3. `criteria_version` currently only agrees between bundle and verdict; both can choose an arbitrary version. Add required current `criteria_version` to the public boundary and bind both bundle and verdict to it, analogous to current coverage. Add omitted/wrong-current-criteria attacks. Update all callers coherently.

4. SQ03 says verifier/producer isolation but the model has no producer identity. Add a nonblank `producer_id` to the review bundle, include it in `input_digest`, and reject a verdict whose `reviewer_id == producer_id`. Add real-boundary tests for same-person rejection and distinct-person acceptance. This is identity separation, not chain-of-thought inspection.

5. The `scientific_qc` node still declares `writes=("snapshot.{report_kind}",)`, contradicting “the verifier cannot rewrite facts/report”. Change its declared write set to a dedicated QC result key such as `qc.{report_kind}` and add an exact node-contract assertion that the scientific-QC node does not write snapshot/evidence/analysis/artifact keys.

Keep the previously closed mandatory bundle/coverage/contract/source equality/veto disposition/exhaustion/naked-boolean/typed-output paths intact.

Required verification:
- First run targeted attacks for the five findings and record their prior failure/new rejection behavior.
- Exact Task 3.7 suite; directly affected graph/node/transition/checkpoint/partial-delivery/snapshot/no-draft regressions.
- Ruff, strict mypy, schema/package manifest validation, correct `uv run ci-workflow package verify --root .`, `git diff --check`, and full suite.
- Report exact commands/counts and residual uncertainty. Do not self-accept.
