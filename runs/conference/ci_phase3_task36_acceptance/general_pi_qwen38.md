All verification complete. Compiling the final report.

---

# Conference Participant Output: ci_phase3_task36_acceptance - general_pi_qwen38

**Verdict: FAIL** — P0=0, **P1=2**, P2=4, P3=4. Independent re-execution confirms the 9 exact tests and 454-suite green, but two user-functional defects survive the suite: (1) resume/re-run with unchanged inputs reports `evidence_blocked` without executing the gate, without an event trail, and without regenerating the blocker package; (2) the built wheel omits `schemas/`, `fixtures/`, `policies/`, `migrations/` — `fixture run` (this task's flagship command) is dead on install.

## Boundary Check

- Read-only audit; no source edits. Disposable runs confined to `/tmp/pi36-*` and the renewable `.artifacts/no-draft-a-empty`.
- Did not read any worker/other-participant report; no production paths touched.
- No final visual/PPT/browser acceptance performed (Codex-owned).

## Independent Work Product

**1. Sources inspected (all Task 3.6 files):** `application/run_service.py` (1187 ln), `application/fixture_runner.py` (381 ln), `schemas/fixture-case.schema.json`, `fixtures/catalog.yaml`, `fixtures/synthetic/no-draft-a-empty/inputs/universe.json` (full), all four integration test files, `cli.py` diff, `pyproject.toml`, `package-manifest.json`, plan Task 3.6 section.

**2. Re-execution (not claimed counts):**

| Check | Result |
|---|---|
| 4 exact integration files | `9 passed in 9.71s` |
| Full suite | `454 passed in 45.94s` |
| Strict mypy `src` | `Success: no issues found in 65 source files` |
| Ruff on Task 3.6 files | `All checks passed!` (repo-wide errors only in `.codebuddy/hooks` tooling) |
| `package verify --root .` | `PACKAGE_OK` exit 0 |
| Exact acceptance command, fresh dir `/tmp/pi36-fresh` | exit **4**, Chinese guidance, manifest binds run_id/case_digest/input hashes/event digest; artifacts = `blockers/A/v1/{audit.json,audit.md}` + records; **no `reports/A/v1`, no HTML, no coverage-projection** (FX06 negative contract holds) |
| Same command on existing `.artifacts/no-draft-a-empty` | exit **2** `CONTRACT_ERROR 项目目录不是空目录` — not idempotent |
| Isolated wheel (fresh venv, cwd outside repo) | `fixture run` exit **2** `无法读取 catalog：…/lib/python3.12/fixtures/catalog.yaml`; `project create` exit **2** `项目数据库无法初始化` (migrations missing) |

**3. Probing beyond the suite (fresh, disposable projects):**

- **P1-1 — Phantom resume verdict (API, fresh RunContext per run):** run 1 (valid universe input) → `evidence_blocked`, 5 nodes completed, blocker package written. Run 2 `resume=True`, unchanged input → `universe` node **reused** (`_run_node` returns stored outputs without calling `_handler_universe`), so `ctx.universe_evidence` stays `None` → `gate:A` **skipped**, no report transitions, no blocker write. Outcome `evidence_blocked` is derived solely from history (`_derive_full_family_state` over all events). Run 2 manifest: `event_count=0`, `checkpoint_id=None`, `outputs=[]`, `node_summary={intake:reused, preflight:reused, universe:reused, gate:A:skipped}` — internally inconsistent claim (skipped gate + blocked verdict) with zero current-run evidence. A plain re-run (no `--resume`) produces **byte-identical behavior** — the `resume` flag is inert (only written into the manifest). None of the 9 tests cover the unchanged-input resume path (EX02 only covers resume-after-**failure**); the content-change path (EX02 run 3) only works because the digest differs.
- **P1-2 — Wheel dead on install:** `uv build` wheel contains **0** `schemas/`, `fixtures/`, `policies/`, `migrations/`, `assets/` entries; `[tool.uv.build-backend]` has no `include`/package-data, so `uv_build` ships only the module. All six data lookups use `Path(__file__).resolve().parents[3]` (fixture_runner ×2, run_service policies, project_service schema, manual_inbox, migrations) — in site-packages `parents[3]` resolves to the site-packages/lib dir, not a data root. `package-manifest.json` `components.schemas` explicitly declares `schemas/fixture-case.schema.json` — shipping intent exists; the build config omission contradicts it.
- **P2-1 — CLI resume no-op:** `project run` RUN1 (fresh project): 4 events, `running`/exit 0. `project run --resume` RUN2: `event_count=0`, `checkpoint=None`, `outputs=[]`, same message "项目已启动，证据采集工作正在进行中" + exit 0 — nothing started or runs.
- **P2-2 — Uncaught integrity error:** `BlockerPackageIntegrityError(RuntimeError)` (blocker_audit.py:744) is not a `RunError`; a run that re-executes the gate with a partially missing blocker package (`audit.json`/`audit.md` deleted, dirs intact — passes `verify_project_workspace`) raises an unhandled traceback, exit 1, no Chinese message, no defined exit code.
- **P2-3 — RunContext mutation:** `run_project` sets `ctx.universe_evidence` as a side effect; reusing one `RunContext` across runs (probe 2) made run 2 execute the gate/blocker-write where a fresh context skips them. Behavior depends on caller object reuse.
- **P2-4 — Acceptance command not idempotent** (see table above); plan says Codex cleans `.artifacts/no-draft-a-empty`, so documented, but the documented success-criteria command fails on second invocation.

**4. Wheel decision (asked question):** **P1, not a later-bundle concern.** `fixture run` is a Task 3.6-delivered user command whose *only* data sources are the three omitted artifacts; the acceptance criteria require "真实运行" and "wheel 内容和差异检查通过", and package-manifest declares the schema as a component. The *fix* is bundle-level (uv_build include + a data-root helper replacing the six `parents[3]` lookups, e.g. `importlib.resources`), but acceptance cannot pass while the flagship command is unconditionally exit-2 on install. It is P1 rather than P0 because the primary dev mode (`uv run`, source tree) works and no data is at risk.

## Evidence And Assumptions

- All run/exit-code/mft claims above are from my own executions (exact commands in the table; probe scripts at `/tmp/pi36_resume_probe*.py`, `/tmp/pi36_cli_probe*.py`, `/tmp/pi36-fresh`, `/tmp/pi36-wheel-run`).
- [INFERENCE] CLI exit code 3 (`renderer_unavailable`) mapping is correct by code reading only — no rendered case exists in the real catalog, so no end-to-end CLI trigger exists (FX02 tests the Python exception).
- [INFERENCE] `_check_renderer_availability` ordering (content validation first, renderer second) is safe; the FX02 docstring's claim ("必须先于内容级校验") contradicts the implementation — documentation staleness, no functional impact.
- [INFERENCE] `logs/run_summary.md` remains "暂无运行记录" after real runs because only `status.md` is written by `_finalize_run` — run record lives in `events/events.jsonl` + manifest; cosmetic staleness.

## Risks, Gaps, And Verification Needs

- **P1-1 remedy:** on resume, when a reused node's downstream must be re-evaluated, either (a) re-execute gate/recovery/blocker-write when outcome is `evidence_blocked` (regenerate package if missing), or (b) record an explicit `outcome=inherited` distinct from a freshly-evaluated verdict and still regenerate the blocker package. Add a test: resume with unchanged input after success → gate executes or outcome is honestly derived, event_count > 0, blocker files present.
- **P1-2 remedy:** `[tool.uv.build-backend] include = ["schemas/**", "fixtures/**", "policies/**", "migrations/**", "assets/**", "skills/**"]` + data-root helper; re-run isolated-wheel `fixture run` and `project create`.
- Verification needs: real-project resume (Task 3.7+ wiring universe inputs) will inherit P1-1 — fix before then.
- **Most important objections:** (1) the 9-test suite is genuinely strong on the *covered* axes (tamper/mtime/deletion, digest binding, catalog uniqueness, no-draft negatives) but the highest-value user path — re-running an existing blocked project — is untested and broken in two different ways (phantom verdict; uncaught traceback on partial corruption). (2) The wheel omission makes the "wheel 内容和差异检查" acceptance criterion hollow as implemented.

## Recommended Next Step

Codex: accept P1-1/P1-2 remediation tasks before formal acceptance; P2s can be tracked. Bounded questions:
1. Resume semantics — must a resumed run re-execute the evidence path when reporting `evidence_blocked` (my recommendation), or is inheriting the prior verdict acceptable if the manifest explicitly marks the inheritance? P1-1 severity depends on this.
2. Wheel data scope — confirm all of `schemas/fixtures/policies/migrations/assets/skills` (per package-manifest inventory) should ship; if the wheel is explicitly deferred to the bundle task, record that decision and its tracked defect instead of silent omission.
3. `project run` exit semantics on no-universe-input projects — plan EX01 asserts `running`/exit 0; is that final, or should automation get a distinct "pending, no evidence pipeline" code/text?

Read-only; no source edits performed.
