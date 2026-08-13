Trellis SessionStart ✓. Starting a fresh independent Task 3.6 acceptance audit from the allowed sources only; I will not read other reviewer reports or write the runner-owned output file.Context is loaded. Next I’ll pull Task 3.6 from the plan and inspect the dirty implementation, tests, and package files.Implementation is in view. Next I’ll read the exact tests, packaging, and related contracts, then re-run the checks.The resume path looks like the main false-green risk. I’ll inspect graph/package wiring next, then re-run the exact tests and a live resume probe.I’ve got a likely resume/provenance hole. Next I’ll re-run the exact tests, probe a fresh `resume=True` path, and inspect an isolated wheel.**FAIL** — P0=0, P1=2, P2=3. Do not accept Task 3.6. Exact EX01–EX02/FX01–FX06 tests are a user-functional false green: they stay green while production `run_project(..., resume=True)` / `ci-workflow project run --resume` can inherit an old evidence decision with no current-run evidence, checkpoint, or blocker binding.

# Conference Participant Output: ci_phase3_task36_acceptance - cursor_grok46_fallback

## Boundary Check

- Identity: Cursor CLI `cursor-grok-4.6-high` fallback; Codex remains final authority. No self-accept, no source edits, no staging/commit, no output-file write.
- Read set: `AGENTS.md`; `context/ci_phase3_task36_acceptance_conference_context.md`; `plans/codex_main_venue_ci_phase3_task36_acceptance.md`; Task 3.6 in `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md`; `context/ci_phase3_task36_context.md`; dirty Task 3.6 implementation/tests/schema/fixture/package files and directly wired graph/blocker/path/CLI helpers.
- Not read: Grok/Pi/worker/other reviewer reports; `reviews/*`; other `runs/conference/*` participant files; production user projects.
- Out of scope observed: no network, browser/PDF/PPT/visual, clinical-content, or system-security work.
- Live execution: this session’s Shell tool rejected both pytest and `git diff`, so exact tests, the disposable resume probe, and isolated wheel install were **not** re-executed here. The FAIL below is from deterministic control-flow in the current dirty sources. That is enough to reject; it is not a substitute for Codex re-running the probe.

## Independent Work Product

**Verdict: FAIL.** P0=0, P1=2, P2=3.

The eight exact nodes look internally consistent and would almost certainly stay green. That is the false green. They never exercise the conference probe: a real no-draft A run, then production `run_project(..., resume=True)` with **unchanged input and a fresh `RunContext`**.

### 1. Exact nodes (source audit)

| Node | Test | What it actually proves | Hole |
|---|---|---|---|
| EX01 | `test_project_run_dispatches_typed_graph_from_saved_project_contract` | API `run_project(project)` with no universe → `outcome=running`, exit 0, intake/preflight completed, current manifest bound | Does not call CLI; no universe; no blockers |
| EX02 | `test_project_run_resume_requeues_only_interrupted_or_failed_nodes_and_downstream` | Same in-memory `RunContext` object: missing file → fail; write file → resume completes universe/gate/recovery; byte change → universe re-runs | Never passes a **fresh** `RunContext`; never calls CLI `--resume`; `resume=` is not what causes reuse |
| FX01 | `test_fixture_run_creates_project_and_dispatches_registered_graph` | `run_fixture_case("no-draft-a-empty")` → exit 4, `blockers/A/v1/{audit.json,audit.md}`, Chinese「证据不足」 | Python API, not `ci-workflow fixture run` |
| FX02 | `test_fixture_run_exits_nonzero_when_requested_renderer_is_not_registered` | After full catalog/digest/input validation, `expected.outcome=rendered` raises `RendererUnavailableError`; no project/artifacts | Matches `fixture_runner.py` (renderer **after** catalog). Module docstring still claims the opposite |
| FX03 | `test_fixture_outputs_only_use_artifact_path_service` | Current outputs are `blockers/...` only; path validator accepts canonical blockers and `ArtifactPathService` report paths | First-run only |
| FX04 | `test_fixture_manifest_hashes_every_real_output` | SHA-256, bytes, exact `st_mtime_ns`; tamper/mtime-only/delete fail closed | Extra test **requires** a later identical run to record `outputs == []` |
| FX05 | `test_fixture_registry_rejects_unknown_duplicate_or_tampered_case` | Unknown/duplicate/escape/missing/undeclared/hash/digest fail closed | Plan text includes「schema 错」; no schema-invalid catalog case |
| FX06 | `test_no_draft_a_empty_case_records_case_digest_and_current_run_id` | First run binds case digest, `run.manifest.recorded`, input hashes, no report/HTML/coverage-projection; project → `blocked` | First run only; coordinator runs because bootstrap is in the **same** run |

Shared executor wiring is real: `cli.py` `_project_run_handler` / `_fixture_run_handler` call `run_project` / `run_fixture_case`; fixture copies `inputs/universe.json` into `evidence/library/` and passes `RunContext`. First-run no-draft A, canonical blockers, manifest self-digest, append-only `run.manifest.recorded`, native Chinese blocker title `# 证据不足说明`, and empty `_RENDERER_REGISTRY` are implemented.

### 2. Required probe — reconstructed from production code (P1-1)

Production CLI resume is:

```373:386:src/ci_workflow/cli.py
def _project_run_handler(args: argparse.Namespace) -> int:
    ...
        result = run_project(
            Path(args.root),
            resume=args.resume,
        )
```

No `RunContext`. No universe path. No discovery of `evidence/library/universe.json`.

`resume` is not a control-flow input. Completed nodes are always derived from the full event stream:

```587:603:src/ci_workflow/application/run_service.py
    # ── Resume: derive completed nodes from the persisted event stream ──
    completed = _derive_completed_nodes(all_events)
    ...
    ctx = run_context or RunContext(project_root=project_root, contract=contract)
```

After a valid no-draft A fixture run, a fresh `RunContext` / CLI `--resume` with unchanged input does this:

1. New `run_id`; baseline captures existing `blockers/A/v1/*`.
2. `universe_input_path is None` → `node_summary["universe"] = "skipped"` (not reused).
3. `ctx.universe_evidence is None` → gate/recovery skipped (`continue`), so `_drive_report_transitions` and `_drive_blocker_write` never run.
4. Coordinator runs only if **this** run submitted a project transition; bootstrap is skipped because a prior run already did, so project family is not moved to `blocked` on resume.
5. Outcome is taken from **all** historical `graph.transition.accepted` report states:

```846:854:src/ci_workflow/application/run_service.py
    report_states = _derive_full_family_state(
        event_store.read_all(), "report_evidence"
    )
    if any(state == "evidence_blocked" for state in report_states.values()):
        outcome = "evidence_blocked"
    elif node_summary.get("universe") == "skipped":
        outcome = "running"
```

6. `_finalize`: current-run event list is empty → `checkpoint_id is None`. `_collect_outputs` drops unchanged baseline files → `outputs == []`. New `manifests/current_run.json` overwrites the honest first-run binding. CLI still prints「项目因关键证据不足暂时无法继续」and exits 4.

That is exactly “inheriting old state with no current evidence.” The current manifest can say `evidence_blocked` while `node_summary` says universe/gate skipped, with no current checkpoint and no current blocker hashes. `validate_run_manifest` then only checks the empty output list, so a post-resume swap of `audit.md` is invisible to the current run.

EX02 does not catch this: it reuses the **same** `RunContext` object (so `universe_input_path` remains set) and only covers fail→fix and changed-bytes, not blocked→unchanged resume.

FX04’s extra test even locks in empty current outputs when blocker bytes already exist:

```205:207:tests/integration/test_fixture_artifact_paths.py
    manifest = _load_manifest(second_root)
    assert manifest["outputs"] == []
```

**Minimal remedy:** (a) current outcome/checkpoint/outputs must come from this `run_id`’s evidence work or an explicit, hashed reuse record of **this** run’s blocker files; never from other runs’ report states when this run skipped the evidence pipeline; (b) on resume, rebind universe from persisted project inputs (or fail closed); (c) if a universe node is reused, still materialize `ctx.universe_evidence` from the input file so gate/blocker/current binding can run; (d) add the conference probe as a regression (fresh `RunContext` + CLI `--resume`).

### 3. Failed-input recovery and changed-input (P1-2)

`resume` is only copied into the manifest (`_write_run_manifest(..., resume=resume)`). There is no `if resume` in `run_service.py`. A second `run_project(..., resume=False)` still reuses matching `graph.node.completed` nodes.

CLI cannot pass universe input at all. EX02’s recovery therefore is not the user command `project run --resume`.

Failed-input, then CLI resume, with the file now present:

- Run 1 (API with missing path): universe failed; project already bootstrapped to `running`; no report_evidence yet.
- CLI `--resume`: fresh context, universe **skipped**, no report states → `outcome = "running"`, exit 0,「项目已启动」.

That is a false-green recovery: the user added the file and the CLI reports the project started without reading it.

Changed-input (EX02 run 3) only works because the test keeps `universe_input_path` on the old context and `_universe_input_digest` includes file SHA-256. Production CLI never computes that digest.

**Minimal remedy:** `--resume` must be the only reuse switch; without it, re-execute. CLI resume must rebind or require the universe input; missing input is exit 2, not `running`. EX02 must go through `_project_run_handler` / `ci-workflow project run --resume`.

### 4. Current-run baseline / mtime / paths / digest / no fake HTML / renderer / Chinese

On a **first** no-draft A run, source looks right:

- Baseline is `(sha256, size, mtime_ns)` over `blockers/` and `reports/`.
- Outputs record exact `st_mtime_ns` (no float round-trip); `validate_run_manifest` re-opens and checks sha/size/`mtime_ns`.
- Path validator allows only `blockers/<A\|B\|C>/<version>/{audit.json,audit.md}` or `ArtifactPathService` report paths.
- Manifest digest is over canonical JSON minus `manifest_digest`; one append-only `run.manifest.recorded` binds path, digest, case id/digest, input-hash digest, and pre-record event stream.
- No HTML/report snapshot/coverage-projection writers in Task 3.6 run path; `_RENDERER_REGISTRY` is empty; rendered fixtures fail closed before project create.
- User stdout/status/`audit.md` are native Chinese; machine tokens stay on stderr/JSON.

These first-run properties do **not** survive the resume probe above, so they cannot carry acceptance.

### 5. Isolated wheel / `ci-workflow fixture run` / `project create`

From `pyproject.toml`, `uv_build` ships only module `ci_workflow`. Repo-root `schemas/`, `fixtures/`, `policies/`, `migrations/` are not package data. Loaders still use `Path(__file__).resolve().parents[3]`:

- `fixture_runner.py`: `schemas/fixture-case.schema.json`, `fixtures/catalog.yaml`
- `run_service.py`: `policies/gates/{A,B,C}-v1.yaml`
- `project_service.py` / `storage/migrations.py`: contract schema and SQL migrations

Installed `site-packages/ci_workflow/application/*.py` → `parents[3]` is not the repo. A bare wheel would fail `project create` and `fixture run` before any Task 3.6 graph work.

`package-manifest.json` lists `schemas/fixture-case.schema.json` but **does not** list `fixtures/` at all. Plan Task 9.5 is the explicit installable bundle (“只含新代码、合同、schema、policy、资产和测试 fixture”). The same `parents[3]` pattern predates 3.6 (`project_service`, migrations).

**Decision:** wheel/data-file absence is a **deferred bundle concern (Task 9.5)**, not a Task 3.6 P1, provided Codex agrees Task 3.6 acceptance is source-tree `uv run` rather than a fresh-install wheel. It is still a verification item: if the chair treats “wheel 内容和差异检查通过” in `context/ci_phase3_task36_context.md` as a 3.6 gate, this becomes P1.

### P2

1. FX05 never asserts a schema-invalid catalog row, though `_validate_catalog` does schema-validate.
2. `run_fixture_case` never checks `case["expected"]["outcome"]` against `run_result.outcome`; catalog contract is digest-bound but not enforced after the run.
3. Stale docs: `test_fixture_run_cli.py` module docstring says renderer check **before** catalog validation; EX01 module docstring says `completed` while the test asserts `running`.

## Evidence And Assumptions

- Sources: current dirty `run_service.py`, `fixture_runner.py`, `cli.py`, four exact test files, `schemas/fixture-case.schema.json`, `fixtures/catalog.yaml`, `package-manifest.json`, `pyproject.toml`, Task 3.6 plan nodes, Task 9.5 bundle deferral.
- Assumption: exact pytest nodes are green on this tree (context already said so; source matches those assertions). Green exact tests are not acceptance.
- Assumption: Shell rejection is session read-only policy, not a product pass.
- Did not recompute catalog `case_digest` / universe SHA-256 live.
- Did not read other conference outputs.

## Risks, Gaps, And Verification Needs

- Codex must actually run: the four exact files; then a temp no-draft A fixture project; then `run_project(..., resume=True)` with a **new** `RunContext` pointing at the same universe file; then `ci-workflow project run --resume` on that project; compare `run_id`, `node_summary`, current events, checkpoint, `outputs`, `mtime_ns`, and whether `current_run.json` still hashes `blockers/A/v1/*`.
- Repeat failed-universe then CLI `--resume` after creating the file; expect fail-closed, not `running`.
- Isolated wheel install outside the repo: `ci-workflow project create` and `ci-workflow fixture run --case no-draft-a-empty ...`. Treat failure as 9.5 unless the chair promotes it.
- Focused Ruff/mypy/full pytest were not run here.

## Recommended Next Step

Codex should **reject** Task 3.6. Do not treat EX01–EX02/FX01–FX06 as acceptance. Required repair is production resume semantics: honor `--resume`, rebind universe input from the project, emit an honest current-run decision/event/checkpoint and blocker binding, and add the fresh-`RunContext` plus CLI resume probes. Wheel data files stay Task 9.5 unless Codex explicitly pulls them into 3.6. After repair, re-run this conference probe; do not accept on worker claims or exact-node green alone.
