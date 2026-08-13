All checks complete. Compiling the revised verdict.

---

# Conference Participant Output: ci_phase3_task36_acceptance - general_pi_qwen38 (reverify)

**Revised verdict: PASS** — P0=0, **P1=0**, P2=4, P3=4. Prior P1-1 (phantom resume verdict) and P1-2 (wheel data) are resolved per the new tree and the new packaging boundary; all four re-test requirements pass with independent re-execution. Residual P2s are integrity-edge cases with concrete remedies; none blocks acceptance under the P0/P1=0 gate.

## Boundary Check

- Same independent reviewer session; read only previously authorized Task 3.6 sources/tests/context/plan + current diff. No worker/other-reviewer reports; no source edits; no network/visual/security work.
- Disposable runs confined to `/tmp/pi36-rev*`.

## Independent Work Product

**Diff since prior review** (all in authorized set): `run_service.py` 1187→1538 ln — non-resume on used projects now fails closed; resume auto-binds `evidence/library/universe.json`, hydrates evidence, and `_check_resume_terminal` fails closed on changed evidence with explicit reopen guidance; `run.node.reused` + `run.terminal_decision.recorded` events; `reused_artifacts` manifest section with sha/byte/mtime binding and tamper checks in `validate_run_manifest`; `decision:<kind>: preserved` semantics; terminal-decision event binding (source decision event, `decision_source` current/reused, `gate_input_digest`). `fixture_runner.py` adds expected-outcome enforcement. `test_cli_command_catalog.py` adds a real CLI resume test. FX02 docstring now matches implementation (content validation first, then renderer check) — stale-doc item resolved.

**Re-execution (all mine):**

| Check | Result |
|---|---|
| 4 exact integration files + CLI catalog test | `13 passed in 14.59s` |
| Full suite | `456 passed in 52.22s` (was 454) |
| Ruff on all Task 3.6 files | clean; strict mypy `src` | clean |
| CLI: fixture run (fresh) | exit 4, Chinese guidance, blocker package only |
| CLI: `project run --resume` unchanged input | exit 4, "证据不足" text, **no "已启动"**; manifest `outputs=[]`, `reused_artifacts` = both blocker files (sha/byte/mtime_ns), `node_summary` all reused + `decision:A=preserved`, `event_count=6`, checkpoint present; events = `run.node.reused`×5 + `run.terminal_decision.recorded`×1 + `run.manifest.recorded`×1, **zero** `graph.node.completed`; `validate_run_manifest` OK |
| Post-run tamper | validate fails (`复用产物摘要不匹配`); restore + exact `os.utime` mtime → validates again |
| Delete canonical universe → resume | exit 2, `CONTRACT_ERROR …请恢复该文件后重新 --resume，或使用显式的项目重新打开流程` |
| Changed evidence (`evidence_id`) → resume | exit 2, `CONTRACT_ERROR 宇宙证据内容已变化…请勿用 --resume 直接重跑；请使用显式的项目重新打开流程重新核对证据`; no events appended |
| Non-resume on used project | exit 2, `CONTRACT_ERROR 项目已有历史运行记录，不能直接重新开始。请使用 --resume…` — the flag is now meaningful |
| Wheel (fresh build) | new members `application/run_service.py`, `application/fixture_runner.py` present; still zero `schemas/fixtures/policies/migrations/` data — **no new data-read dependency added by this fix round** (same six `parents[3]` lookups as before, all predating Task 3.6) |

## Findings

**P1 — none.** All four mandated re-test areas pass (evidence above + EX02 runs 1–4, FX01 outcome-mismatch, FX05, CLI resume test).

**P2-1 — Pre-run blocker drift is certified as a reused artifact.** Tamper `blockers/A/v1/audit.md` *before* `--resume`: baseline captures the tampered file, `_collect_outputs` classifies it as "unchanged" → `reused_artifacts` records the **tampered** sha, terminal-decision event binds it, `validate_run_manifest` passes, tamper persists, CLI still exits 4 pointing the user at it. Post-run tamper is rejected, pre-run drift is adopted. Remedy: on preserved-decision resume, recompute the deterministic package content from the bound evidence and compare sha per file; mismatch → fail closed with the same restore/reopen guidance family.

**P2-2 — Stale `RunContext` reuse bypasses the changed-evidence guard.** Probe E: run 1 hydrates `ctx.universe_evidence`; evidence file then changes; run 2 `resume=True` reusing the *same* ctx → `_check_resume_terminal` compares against the **cached** (stale) digest → passes; universe re-runs but `_handler_universe` skips re-hydration (`is None` short-circuit) → gate reused against stale evidence; manifest certifies the old digest over new content. CLI is unaffected (fresh ctx per invocation); API-level footgun that Task 3.7+ real projects will hit. Remedy: hydrate unconditionally whenever a universe path is bound (drop both `is None` short-circuits).

**P2-3 — Blocker-package drift exceptions unmapped.** Fresh project with manually drifted blocker files → uncaught `BlockerAuditDriftError` (plain `RuntimeError`, not `RunError`) → raw traceback if reachable via CLI; message is informative Chinese but no defined exit code. Missing-file case is now pre-empted with clean `ContractConfigError`; only manual pre-seeding of drifted files reaches this. Remedy: wrap blocker-package write failures into `ContractConfigError` (exit 2, restore guidance).

**P2-4 — `fixture run` not idempotent** (unchanged from prior review): second invocation on `.artifacts/no-draft-a-empty` → exit 2 `项目目录不是空目录` instead of exit 4. Plan documents Codex cleanup of the renewable dir; still a user-facing surprise. Remedy: document `rm -rf` or auto-clean the acceptance dir before run.

**P3:** (1) `logs/run_summary.md` stays `暂无运行记录` after real runs (record lives in events + manifest); (2) CLI exit 3 (`renderer_unavailable`) never exercised end-to-end — no rendered case in the real catalog, FX02 tests the exception only; (3) "项目已启动，证据采集工作正在进行中" wording over-promises on the no-evidence path (plan-sanctioned `running`/exit 0, downgraded from prior P2); (4) invalid-date rejection paths (`_parse_case_dates`, schema formats) not directly asserted. Forward note: `_collect_outputs` now scans only `blockers/` — Task 3.7+ must re-add `reports/` collection.

## Evidence And Assumptions

- All exit codes/event counts/manifest fields above from my own runs (probes `/tmp/pi36_reverify{1,2,3}.py`, projects `/tmp/pi36-rev{1,2,3a..3e}`).
- Wheel data omission: retained as a **mandatory Task 9.5 verification item** (schemas/fixtures/policies/migrations/assets/skills + six `parents[3]` lookups), not a Task 3.6 P1 per the explicit boundary; this round's source added no new repo-relative data reads, so the boundary is not worsened.
- [INFERENCE] P2-2 is API-reachable only (CLI builds fresh ctx); [INFERENCE] P2-3 reachability requires manual file pre-seeding outside any documented flow.

## Risks, Gaps, And Verification Needs

- P2-1/P2-2 both touch resume-evidence integrity: recommend remediation before Task 3.7+ wires universe inputs into real projects (add the two probes as regression tests — drift-before-resume rejection; stale-ctx resume after evidence change).
- Verification need: rerun isolated-wheel `fixture run` at Task 9.5 and confirm data-root resolution via the new helper.

## Recommended Next Step

Accept Task 3.6 (P0=P1=0). Track P2-1/P2-2 as required pre-Task-3.7 remediation, P2-3/P2-4 as bundle/UX items, and the wheel data bundle as a Task 9.5 gate with the listed verification. Questions for Codex: (1) is drift-before-resume rejection in scope for Task 3.6, or deferred with P2-1 accepted? (2) confirm the `reports/` collection removal in `_collect_outputs` is a deliberate Task-3.6 scoping (no report outputs) rather than a regression to restore in 3.7?
