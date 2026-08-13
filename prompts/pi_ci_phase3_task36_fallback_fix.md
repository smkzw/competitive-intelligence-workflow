You are Pi/DeepSeek, the next declared finite-code route after the prior Pi/OpenCode-Go session terminated with a runtime identity mismatch. Repair the existing dirty Task 3.6 implementation; do not restart or discard its work. Codex has independently confirmed eight exact tests currently pass, but several tests are materially too weak and the task is not accepted.

Hard boundaries:
- Work only in `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Read these files only: `AGENTS.md`; `context/ci_phase3_task36_context.md`; Task 3.6 of `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md`; cited §10/§18.2/§19 of `docs/specs/competitive-intelligence-workflow-design-v1.2.md`; `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/{prd.md,design.md,implement.md,task.json}`; current dirty diff; and directly relevant Task 3.6 files under `src/ci_workflow/{application,domain,gates,graph,storage}/`, `schemas/`, `fixtures/`, `tests/`, `package-manifest.json` and `pyproject.toml`.
- Authorized edits: the current Task 3.6 implementation/tests/fixture/schema files, `src/ci_workflow/cli.py`, `package-manifest.json`, and the minimum existing CLI/package contract assertions if needed. Do not edit design/spec/plan/Trellis/accepted Task 3.2–3.5 behavior.
- Do not commit or stage. No network, browser, PDF, PPT, visual, clinical-content, or system-security work.
- Write exactly one output file: `runs/pi_ci_phase3_task36_fallback_fix.md`. It is runner-owned; return the report and do not write it using tools.

Repair the remaining false-green gaps with production behavior and strengthened exact tests:

1. Deterministic fixture contract
- In `schemas/fixture-case.schema.json`, make `indication`, `timezone`, `data_cutoff`, and `created_at` required. `data_cutoff` must be a real ISO date/date-time and `created_at` an offset-aware date-time; empty strings and current-time defaults are forbidden.
- Put a realistic indication and fixed Asia/Shanghai cutoff/creation timestamps in `fixtures/catalog.yaml`; include all four fields in the sorted canonical case digest. Fixture project creation must use them exactly.
- Reject schema/YAML/date parsing errors as `FixtureCaseError`. Do not silently attach UTC to a naive `created_at`; reject it. Validate the named IANA timezone through the project contract.
- Full catalog and case digest/input integrity must pass before renderer availability is checked. A valid rendered temporary case then raises `RendererUnavailableError`; no fake project/artifact/receipt.

2. Real recovery success path
- Strengthen EX02: first run has a declared missing universe path and records failure plus checkpoint/manifest. Then create a valid universe input and call `resume=True`. Intake/preflight must be reused from run 1; universe must execute and complete under run 2; downstream A gate/recovery/report blocking must execute under run 2; final outcome is evidence-blocked, not failed. Assert no second intake/preflight completion and no stale earlier failure poisons run 2.
- Resume truth comes only from persisted event/checkpoint state. If a completed node's input digest changes, rerun it. Ensure the universe input digest includes its content hash, not only its path, so newly created or changed content cannot reuse stale output.
- Every failure return must replay/persist a checkpoint before finalizing. Project bootstrap is submitted only once; resume reads canonical persisted state. Remove the string-matching/broad `except Exception` coordinator logic; use explicit state conditions/typed exceptions.

3. Canonical current-run outputs
- Add one production output-path validator used both before manifest persistence and during reopen validation. Report paths must validate through `ArtifactPathService` and match its exact canonical artifact/manifest/projection paths. Blocker outputs must be exactly `blockers/<A|B|C>/<safe report version>/{audit.json,audit.md}`. Reject absolute paths, traversal, arbitrary namespaces, unexpected blocker filenames and noncanonical report names.
- Add assertions in FX03 that directly exercise valid report/blocker paths and reject invalid variants.
- Capture the blocker/report output baseline at run start. Only a file absent before the run or whose exact `(sha256, bytes, mtime_ns)` changed during this run may enter this run's outputs. A pre-existing unchanged blocker package must not be adopted. Strengthen FX04 with a pre-existing-file case.
- `RunOutputFile` must store exact integer `mtime_ns` from `stat()`. Do not round-trip nanoseconds through float datetime. Manifest validation must compare SHA, bytes and exact `st_mtime_ns`, and reject mtime-only drift.

4. Manifest-to-event binding
- `_write_run_manifest` must durably write and return its digest plus the digest of current pre-record run events. `_finalize_run` then appends a `run.manifest.recorded` event for the same `run_id` with manifest relative path, manifest digest, case digest, deterministic digest of sorted input hashes, and explicit `pre_record_event_stream_digest`/count. This avoids circularity while binding the manifest from the append-only event stream.
- `validate_run_manifest` must validate its own digest, every output, and the matching current-run `run.manifest.recorded` event payload. Reject missing event, wrong run/case/input digest, wrong manifest digest/path, old event and altered values.
- Strengthen FX06 to require the exact event and values; remove the current weak `manifest_digest OR any manifest event` assertion. Assert all event IDs belong to current run for a fresh fixture and no report/snapshot/coverage/format job/HTML placeholder exists.

5. Honest state and Chinese UX
- Keep new no-input project outcome `running`, exit 0, and native Chinese “已启动/正在采集” wording. Do not say completed.
- Machine tokens may remain on stderr; status/audit/primary guidance must not expose `gate`, `signal`, `queued`, `evidence_blocked`, prompt or backend labels.
- Remove duplicate docstrings/dead exception classes and keep the code typed and minimal.

6. Verification
- Preserve exact node names EX01/EX02 and FX01–FX06. Record behavior-level RED causes introduced by strengthening, then GREEN.
- Run exact four-file suite; relevant CLI/project/no-draft/graph regressions; full suite; Ruff; strict mypy on changed Python; JSON Schema validation; wheel content; package verify; `git diff --check`.
- Run real `uv run ci-workflow fixture run --case no-draft-a-empty --reports A --outputs html --project .artifacts/no-draft-a-empty`, record exit 4, inspect tree/checkpoint/manifest/event binding and prove no report/coverage/format/HTML output. Clean only task-created `.artifacts` and caches after evidence.

Return a compact execution report with boundaries, strengthened RED/GREEN evidence, implementation, real CLI evidence, exact verification counts, changed files, failures/root causes and residual uncertainty. Codex is final authority; do not self-accept.
