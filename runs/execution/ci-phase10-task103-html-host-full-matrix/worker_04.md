# Execution Output: ci-phase10-task103-html-host-full-matrix - worker_04

## Boundary And Context Check

- Primary provider unavailable before a resumable session; executed with fallback `openai-codex/gpt-5.6-luna`.
- Scope limited to F05: candidate install-root Codex/Hermes/OMP host smoke, final project verification, and failure-closure tests.
- Only authorized files changed:
  - `src/ci_workflow/application/acceptance_runner.py`
  - `tests/acceptance/test_full_matrix.py`
- No production candidate path, runner report path, browser, PDF, HTML-PPT, or PPTX artifact was written.
- No real Codex/Hermes/OMP acceptance claim was made.

## Work Performed

- Hardened candidate identity binding:
  - Reads candidate package name/version from `package-manifest.json`.
  - Captures and rechecks package-manifest and installed entrypoint SHA-256 values.
  - Rejects candidate bundle, manifest, package identity, or entrypoint drift.
- Hardened three-host batch binding:
  - Requires exactly `codex`, `hermes`, and `omp`.
  - Requires `real_host_pass=True`, `verified` statuses, `path_resolved` host executable provenance, and `host-smoke-v1`.
  - Requires distinct session IDs, process PIDs, run IDs, and per-host project roots.
  - Binds all receipts and `batch.json` to exact files under the isolated evidence root.
  - Binds receipt and batch package digests to the candidate package manifest.
  - Rejects stale, self-inconsistent, replaced, symlinked, or externally located evidence files.
  - Requires per-host project roots under the isolated acceptance project root.
- Hardened final project verification:
  - Calls `verify_project_workspace`.
  - Rechecks project contract reports, HTML-only format, indication, timezone, and cutoff against catalog truth.
  - Revalidates the current run manifest, HTML artifacts, and ego(lite) receipt digests after host smoke.
- Added failure-closure coverage for:
  - Candidate entrypoint drift.
  - Receipt path outside evidence root.
  - Batch package-manifest digest drift.
  - Project contract drift.
  - Project-root symlink and external project-root results.
  - Existing session/process/run reuse, stale evidence, receipt tampering, non-real batch, and host status/provenance failures.

## Artifacts And Evidence

- Source implementation: `src/ci_workflow/application/acceptance_runner.py`
- Acceptance tests and synthetic host batch fixtures: `tests/acceptance/test_full_matrix.py`
- No persistent acceptance evidence or runner report was generated.
- Repository matrix already documents the F05 contract in `docs/acceptance/matrix.md`; no documentation change was required.

## Commands And Observations

- `uv run python -m py_compile src/ci_workflow/application/acceptance_runner.py tests/acceptance/test_full_matrix.py`
  - Passed.
- Focused F05/full-pipeline tests:
  - `33 passed, 55 deselected`.
- Acceptance and host regression tests:
  - `99 passed, 1 skipped`.
- `uv run ruff check ...`
  - `All checks passed!`
- `uv run mypy src/ci_workflow/application/acceptance_runner.py src/ci_workflow/application/host_smoke_runner.py`
  - `Success: no issues found in 2 source files`.
- Full acceptance and host suites:
  - `295 passed, 1 skipped, 3 failed`.
  - All three failures are `tests/acceptance/test_native_pdf_slice.py`; the environment lacks `pdftotext`.
  - These are outside the Task 10.3 HTML-only F05 scope.

## Blockers Or Missing Environment

- Real candidate-host execution was not run:
  - `tests/hosts/test_fresh_install.py::test_real_host_runner_is_executable_only_when_explicitly_enabled` requires `CI_WORKFLOW_RUN_REAL_HOST_TESTS=1`.
  - The authorized worker boundary excludes the existing production-like candidate root under `~/.cc-switch`.
  - No genuine Codex/Hermes/OMP receipt set is therefore available from this worker.
- No ego(lite) browser or visual acceptance was performed; Codex remains final acceptance authority.
- `pdftotext` is unavailable for the unrelated PDF tests.

## Rerun Requests Or Next Step

1. Codex should run the real host test with an authorized isolated candidate root and `CI_WORKFLOW_RUN_REAL_HOST_TESTS=1`, verifying genuine PATH-resolved Codex/Hermes/OMP execution.
2. Continue the full pipeline with `--pipeline full --bind-ego-receipts`, using a fresh isolated acceptance root; confirm the three host receipts and final project verification pass together.
3. Codex should perform the required ego(lite) browser and visual checks.
4. Provision `pdftotext` only if the broader repository PDF suite is required; it is not part of the HTML-only F05 acceptance boundary.
