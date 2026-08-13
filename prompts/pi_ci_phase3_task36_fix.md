You are continuing the SAME Pi/OpenCode-Go implementation session for Task 3.6. The previous writable attempt left an incomplete dirty tree; preserve and repair it in place. Read workspace `AGENTS.md`, `context/ci_phase3_task36_context.md`, the Task 3.6 plan section, the current dirty diff, and only the relevant implementation/tests. Do not read unrelated reports or user data.

Hard boundaries:
- Read these files only: `AGENTS.md`; `context/ci_phase3_task36_context.md`; the Task 3.6 section of `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md`; the cited Task 3.6 sections of `docs/specs/competitive-intelligence-workflow-design-v1.2.md`; `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/{prd.md,design.md,implement.md,task.json}`; the current dirty diff; and directly relevant files under `src/ci_workflow/{application,domain,gates,graph,storage}/`, `schemas/`, `fixtures/`, and `tests/` needed for Task 3.6.
- Write exactly one output file: `runs/pi_ci_phase3_task36_fix.md`. This is the runner-owned report path: return the report content and let the runner persist it; do not write it with tools.

Route and authority:
- Stay on provider `opencode-go`, model `deepseek-v4-flash`, effort `max` in this existing session.
- Work only in `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Do not commit or stage.
- No browser/PDF/PPT/visual, network, clinical-content, or system-security work.
- The runner owns `runs/pi_ci_phase3_task36_fix.md`; return the report, do not write it with tools.

Authorized files are the original Task 3.6 set plus the already-required `package-manifest.json` declaration and, only if needed to prove bundle membership, minimal updates to `tests/contract/test_package_manifest.py`. You may also update the minimum existing CLI catalog/help assertions. Do not modify specs, plans, Trellis, accepted Task 3.2–3.5 behavior, or unrelated code.

The current implementation is NOT accepted. Fix the production design and tests rather than merely making existing weak assertions green. Required corrections:

1. Catalog/schema determinism and fail-closed behavior
- Export a public `validate_catalog` with the contract expected by the tests; wrap YAML, JSON Schema, missing file, malformed catalog and case validation failures as `FixtureCaseError` with concise Chinese diagnostics.
- The catalog is the only registry. Inventory every regular file under each case `inputs/` tree and reject any undeclared file, not just declared paths. Reject unknown case IDs, duplicate YAML keys and duplicate case IDs, absolute or escaping paths, missing inputs, hash drift and schema drift.
- Sort canonical input entries before calculating the case digest.
- Extend the fixture case contract with real `indication`, `timezone`, `data_cutoff`, and fixed offset-aware `created_at`. Include them in the canonical case digest. Fixture project creation must use these values, never `description_zh` as the indication and never the current date. Resume must keep the frozen contract.
- Update the production `no-draft-a-empty` catalog/digest accordingly and strengthen temporary-case test helpers. A temporary rendered case must have a valid full catalog/case digest; catalog integrity is checked before renderer availability.

2. One real RunService and truthful project state
- `project run` and `fixture run` must invoke the same production service.
- A newly created project with no universe input is a valid started project, not “completed” and not a technical failure: run intake/preflight, persist run/events/checkpoint/manifest, leave project outcome `running`, exit 0, and show native Chinese guidance that work has started and will continue. Add `running` to the typed outcome and tests.
- Bootstrap `None -> running` only when no project transition exists. On resume, preserve and validate the canonical persisted project state; do not resubmit the bootstrap transition.
- Remove broad `except Exception: pass` around coordinator/state operations. Catch only expected typed conditions or surface a real failure.

3. Real resume semantics
- Derive truth from persisted events/checkpoint only. A failed/interrupted node must actually be requeued and executed on `--resume`; successful upstream nodes are reused and not re-executed. Downstream is re-executed as required.
- A first run whose universe input is absent should record a universe failure plus checkpoint/manifest. After the input is supplied, resume should reuse intake/preflight and execute universe under the new run, with a new completion/failure event as applicable.
- Reuse entries use `node_id` (not `node`). Failed events from earlier runs must not permanently force the new run outcome to failed once the node has succeeded.
- All early failure paths still produce a valid replay checkpoint and current run manifest.

4. Current-run output and canonical path contract
- Capture a pre-run output baseline/run start. The manifest may enumerate only files created or materially modified by the current run; pre-existing blocker/report files cannot be adopted as current output.
- Validate output paths before persistence and on reopen. Report output paths must round-trip through `ArtifactPathService`; blocker paths are exactly `blockers/<A|B|C>/<safe-version>/{audit.json,audit.md}`. Reject absolute paths, traversal, arbitrary namespaces and noncanonical report names. Add an exact production validator and tests for both report and blocker namespaces.
- Reopen validation must compare relative POSIX path, SHA-256, byte size, and exact `mtime_ns` (you may retain a human-readable timestamp too). Missing, tampered, stale, pre-run, or namespace-invalid entries fail closed.

5. Manifest and event binding
- Write the current run manifest deterministically, including project/contract/run/case/input hashes, node summary, reused nodes, outputs and checkpoint. Calculate its digest.
- After the manifest is durably written, append a `run.manifest.recorded` event containing current `run_id`, manifest relative path, manifest digest, case digest and a deterministic digest of input hashes. The manifest's event-stream digest must explicitly describe the pre-record event stream to avoid circularity; the later event binds the manifest.
- Strengthen FX06 to require this exact current-run event and payload. Reject an old run ID, old manifest digest, altered input-hash digest or stale mtime. Do not accept a self-contained digest with no event binding.
- The run manifest does not list itself as a user report output.

6. Renderer and user-facing behavior
- Validate the full catalog and case contract first; then, for a valid case whose expected outcome requires rendering, raise `RendererUnavailableError` (not `FixtureCaseError`) before creating fake artifacts/receipts.
- Machine tokens may appear on stderr, but primary CLI/status/audit prose must be native Chinese for a clinical medical user. Do not expose `evidence_blocked`, `gate`, `signal`, `queued`, stack traces, prompt wording, or generic backend labels. `running` must not be described as “运行完成”.

7. Tests and verification
- Keep the exact node names from Task 3.6. Strengthen the four files so EX01/EX02 and FX01–FX06 prove the corrections above. Do not alter assertions to accept weaker behavior.
- The current collection ImportError is not meaningful RED evidence. After fixing collection, run each exact node and record the first behavior-level RED that existed, then GREEN.
- Run the exact four-file suite, relevant CLI/project/no-draft/graph regressions, full suite, Ruff, strict mypy for changed application modules and CLI, JSON Schema validation, wheel contents, and `git diff --check`.
- Run the real fixture CLI at `.artifacts/no-draft-a-empty`; inspect the file tree, current manifest, binding event, SHA/bytes/mtime_ns, checkpoint and absence of reports/snapshots/coverage/format jobs/HTML placeholders. Diagnose any absence from the graph/events rather than fabricating output.
- Clean only task-created `.artifacts`, pytest/mypy/Ruff caches and raw scratch after compact evidence is captured. Preserve source/tests/fixture inputs and runner-owned records.

Return a compact report with: boundary compliance; behavior-level RED/GREEN by exact node; architecture; real CLI evidence; verification matrix with exact counts; files changed; failed paths/root causes; residual uncertainty. Codex remains final authority and will independently rerun everything.
