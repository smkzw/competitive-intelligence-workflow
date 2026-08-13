You are Pi (Oh My Pi) running as the bounded implementation worker in a Codex-controlled execution workflow.

Read and comply with workspace `AGENTS.md`. Do not read Hermes `SOUL.md`; this is a Pi route, not Hermes. Work in the current repository only.

Hard boundaries:
- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Read these files only: `context/ci_phase3_task36_context.md`; the Task 3.6 section of `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md`; `docs/specs/competitive-intelligence-workflow-design-v1.2.md` only for cited §10/§18.2/§19; `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/{prd.md,design.md,implement.md,task.json}`; relevant existing files under `src/ci_workflow/{application,domain,gates,graph,storage}/`, `schemas/`, and tests directly needed to implement or verify Task 3.6. Do not read worker reports, reviews, unrelated fixtures, old project trees, or user production data.
- You are authorized to create/edit only: `src/ci_workflow/application/run_service.py`, `src/ci_workflow/application/fixture_runner.py`, `src/ci_workflow/cli.py`, `src/ci_workflow/application/__init__.py` only if needed, `schemas/fixture-case.schema.json`, `fixtures/catalog.yaml`, `fixtures/synthetic/no-draft-a-empty/**`, `tests/integration/test_project_run_cli.py`, `tests/integration/test_fixture_run_cli.py`, `tests/integration/test_fixture_artifact_paths.py`, `tests/integration/test_fixture_case_contracts.py`, and the minimum obsolete-stub assertions in `tests/integration/test_cli_command_catalog.py` / `test_cli_help.py` if needed. Do not edit any other source, spec, plan, Trellis, review, metric, prompt, run, or acceptance file.
- Do not commit or stage. Write exactly one output file: `runs/pi_ci_phase3_task36.md`. This path is runner-owned: return the complete report and let the runner persist it; do not write it with tools.
- Do not add dependencies or a new graph framework. Reuse the accepted ProjectContract, ProjectWorkspace, GraphExecutor, node registry, blocker audit and ArtifactPathService.
- No browser/PDF/PPT/visual, network, clinical-content, or system-security testing.

Implement Task 3.6 exactly:

1. Create all eight exact tests first and run each node after the test exists to obtain a meaningful RED (assertion/known missing handler, not merely missing test file). Record the RED cause compactly.
2. EX01: `project run` loads the saved active contract and dispatches the real typed graph through one production `RunService`; persist a new run identity, events/checkpoint and a current run manifest.
3. EX02: `project run --resume` derives interrupted/failed nodes from persisted run/checkpoint state and only requeues them plus downstream; completed nodes remain reused and are evidenced in the new/continued run summary. Do not accept a caller-supplied completed list as truth.
4. FX01: `fixture run` creates an isolated project and calls that same `RunService`; no parallel fake fixture executor.
5. FX02: if a requested renderer is not registered, exit nonzero with concise Chinese guidance and create no fake artifact/receipt. Task 3.6 has no renderer registered, so any selected output is a requested contract output but the no-draft A fixture stops before rendering; a pass-case renderer request must fail explicitly.
6. FX03: all report artifacts/manifests/projections, if a registered renderer later produces them, can only be resolved by `ArtifactPathService`; reject arbitrary or absolute persisted paths. Blocker/run paths remain their separately declared canonical paths.
7. FX04: the current run manifest enumerates every real output created by that run and records exact relative path, SHA-256, bytes and mtime; validation reopens the files and rejects stale/missing/tampered entries. Do not count pre-existing project skeleton files as run outputs.
8. FX05: `fixtures/catalog.yaml` is the only registry. Validate it and each case against `schemas/fixture-case.schema.json`; reject unknown names, duplicate YAML keys/case IDs, schema drift, paths escaping the case directory, missing files, undeclared files that affect inputs, and any input digest mismatch. Case digest must be canonical and content-bound.
9. FX06: build a real `fixtures/synthetic/no-draft-a-empty/` input/expected contract. Its execution must bind `case_digest`, current `run_id`, current manifest digest and real input hashes in the event/run summary. It must invoke the accepted empty-A evidence/blocker path, create only `blockers/A/<version>/audit.json` and Chinese `audit.md` plus run/event records, and create no report snapshot, coverage projection, format job, artifact manifest entry or HTML placeholder.
10. CLI: implement real `project run --root ... [--resume]`; implement mandated `fixture run --case ... --reports ... --outputs ... --project ...`. Keep existing frozen command catalog and Chinese help. Use stable machine tokens only alongside plain Chinese user guidance. Define and test distinct nonzero codes for contract/config failure, capability/renderer unavailable and evidence-blocked completion.
11. Run the exact four-file suite, relevant existing CLI/project/no-draft/graph regressions, full suite, Ruff, strict mypy on new application modules and CLI, schema validation, wheel contents, and `git diff --check`. Inspect the real `.artifacts/no-draft-a-empty` tree and event/manifest digests; do not call the task done only because pytest is green.
12. Clean task-created caches and `.artifacts` after recording compact evidence. Preserve only source/tests/fixture inputs. Do not delete user or accepted files.

User perspective: all user-visible prose must sound native to a Chinese clinical-trial medical professional who does not know command-line internals. Never place `gate`, `signal`, `queued`, `evidence_blocked`, stack traces, prompt language, or generic programmer labels in `audit.md`, `status.md`, or the primary CLI guidance.

If any expected output is empty or absent, stop and diagnose the actual cause by tracing current events, inputs, graph state and manifest; do not weaken the test or manufacture a placeholder.

Return this report schema:
1. `# Task 3.6 Implementation Report`
2. `## Boundary And AGENTS Compliance`
3. `## RED Evidence By Exact Node`
4. `## Implementation And Architecture`
5. `## Real Fixture Run Evidence`
6. `## Verification Results`
7. `## Files Changed`
8. `## Failed Paths And Root Causes`
9. `## Residual Uncertainty And Next Step`

Codex remains final authority. Do not self-accept the task.
