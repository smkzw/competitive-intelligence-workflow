Continue the SAME successful Pi/DeepSeek session `019ff827-34f5-7000-8c80-47705eb9c191`. Independent acceptance rejected Task 3.6 despite 9 exact and 454 full tests passing. Repair the false-green resume semantics in the existing dirty tree; preserve all accepted work.

Hard boundaries:
- Work only in `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Read these files only: `AGENTS.md`; `context/ci_phase3_task36_context.md`; Task 3.6 of `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md`; cited §10/§18.2/§19 of the v1.2 spec; current Task 3.6 dirty source/tests/schema/fixture/package files; directly wired graph/event/checkpoint/blocker/path/project helpers. Do not read conference, reviewer or worker reports.
- Authorized edits: current Task 3.6 source/tests/schema/fixture files, `src/ci_workflow/cli.py`, and minimal existing CLI/package assertions. Do not edit specs/plans/Trellis, Task 3.2–3.5 implementations, packaging architecture or unrelated code.
- Do not commit/stage. No network, browser/PDF/PPT/visual, clinical-content or security work.
- Write exactly one output file: `runs/pi_ci_phase3_task36_acceptance_fix.md`; runner-owned, return report and do not write it with tools.

Required functional repair:

1. `resume` must control reuse.
- Only `resume=True` may reuse previously completed nodes. A new non-resume run must not silently reuse old node results; if the existing project state cannot safely start fresh, fail with concise Chinese contract guidance rather than corrupting state.
- Resume derives truth only from events/checkpoints; completed nodes with matching inputs may be reused, failed/interrupted nodes and downstream must execute.

2. CLI and fresh-context resume must rebind persisted inputs.
- The fixture already archives the universe evidence at the canonical project path `evidence/library/universe.json`. When `run_project(..., resume=True)` receives no caller path, discover and bind that canonical persisted input if present. If a prior universe failure exists and the canonical input is still absent, fail closed with Chinese guidance; do not claim “已启动”. A brand-new project with no prior universe attempt may still be `running`/exit 0.
- A fresh `RunContext` pointing at the unchanged canonical input and CLI `project run --resume` must behave consistently. Do not rely on mutation of a reused caller object.
- When universe is reused, hydrate `ctx.universe_evidence` deterministically from the bound input so downstream state/decision logic is not skipped accidentally.

3. Every resume has honest current-run evidence.
- Never derive a new current outcome solely from old report transition state while leaving current `event_count=0`, `checkpoint_id=None`, or no current evidence reference.
- Reusing a completed node must append a current-run typed reuse event binding node id/report kind, original run/event/digests and current input digest. A terminal evidence-blocked project may preserve the prior decision only through explicit current-run reuse/terminal-decision events and exact blocker file references/hashes; unchanged blocker files remain `reused_artifacts`/evidence references, not falsely “created outputs”. Alternatively, safely re-evaluate the evidence path if the graph state permits. Choose the smallest state-machine-correct design.
- Every run, including no-op terminal resume and failure, must produce a current checkpoint and manifest binding event. `validate_run_manifest` must verify the reuse/terminal evidence references and actual blocker files, including path/SHA/bytes/mtime_ns; tampering after resume fails closed.
- Do not resubmit invalid transitions from terminal states. Respect Task 3.5 explicit reopen semantics; `--resume` is not an implicit reopen.

4. Strengthen exact tests without weakening existing contracts.
- Extend EX02 or add assertions within the same exact node for: failed missing input -> create canonical input -> CLI/fresh-context resume executes universe/downstream; unchanged-input resume with a fresh context records current reuse/terminal evidence events, checkpoint, and blocker hashes; stale earlier failure does not poison the outcome; input content change is not silently reused (if terminal state requires explicit reopen, fail with explicit contract guidance rather than rerun invalid transitions).
- Add a real CLI `project run --resume` assertion, not API-only.
- FX04 must distinguish new outputs from reused artifact references. Do not assert an empty manifest is sufficient for a blocked resumed run.
- FX05 add a schema-invalid case rejection.
- `run_fixture_case` must verify actual `run_result.outcome` matches the catalog expected outcome and fail as `FixtureCaseError` on mismatch.
- Correct stale module docstrings (running vs completed; catalog validation before renderer check).

5. Packaging boundary
- Do not redesign resource loading or add full wheel data packaging here. Plan Task 9.5 owns the installable bundle containing schemas, policies, migrations, assets and fixtures. Task 3.6 wheel check is limited to the two new Python modules; record that full isolated install remains a mandatory Task 9.5 acceptance, never claim Task 3.6 wheel is installable.

6. Verification
- Create behavior-level RED for the unchanged-input fresh-context/CLI resume and schema/outcome cases, then GREEN.
- Run exact four files; related CLI/project/no-draft/graph regressions; full tests; Ruff; strict mypy; schema/catalog validation; package verify; wheel module membership; `git diff --check`.
- Run a fresh real fixture (exit 4), then real CLI `project run --resume` on it. Inspect both run IDs, current-run events, checkpoint, manifest binding, reused blocker hashes, and absence of reports/HTML/coverage projections/format jobs. Tamper a blocker after resume and prove validation fails. Clean only task-created artifacts/caches.

Return compact report: boundaries, RED/GREEN, implementation, two-run CLI evidence, verification counts, changed files, failures/root causes, residual uncertainty. Codex remains final authority.
