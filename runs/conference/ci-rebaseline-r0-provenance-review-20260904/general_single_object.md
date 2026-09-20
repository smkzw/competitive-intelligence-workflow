Full gate results are in. I'll fold them into the audit and return the completed participant report—still read-only.# Conference Participant Output: ci-rebaseline-r0-provenance-review-20260904 - general_single_object

## Boundary Check
- Role: `general_single_object` / Pi / cursor / default; read-only audit only.
- Stayed inside workspace `.`; did not inspect external backup directories or the real forbidden legacy root.
- Did not edit, stage, commit, reset, clean, or delete any artifact.
- Did not write `runs/conference/ci-rebaseline-r0-provenance-review-20260904/general_single_object.md`; this response is the report payload for the runner.
- Treated `runs/execution/ci-rebaseline-rebuild-20260904/worker_01.md` as a claim under audit, not authority.
- External backup physical RO verification remains Codex-owned and is **not** claimed here.

## Independent Work Product

### Verdict: **VETO**
R0 is substantially remediated and quality-green on a dirty tree, but it is **not** acceptably closed while (1) a residual zero-contact hole remains in legacy symlink handling and (2) the R0 SoT governance record still omits the R0.4 disk-hygiene contract. Do **not** treat current quality-green as release/RC.

### Highest-impact defect
**P1 — zero-contact claim is incomplete.**  
Legacy **marker** matching is lexical (`os.path.abspath(os.path.expanduser(...))`) and avoids `resolve/exists/stat` for marker construction. But repo symlink outsideness still does:

```126:129:tools/check_no_legacy_refs.py
            target = path.resolve(strict=False)
            if not _is_within(target, root):
                findings.append(
                    Finding("EXTERNAL_RUNTIME_SYMLINK", relative, f"target={target}")
```

Synthetic reproduction (temp tree only): a repo symlink pointing at a synthetic legacy directory is detected as `EXTERNAL_RUNTIME_SYMLINK`, and the detail shows an absolute resolved target under the temp legacy path. That means detection can filesystem-touch an outside/legacy-shaped target via `Path.resolve`. Marker lexicalization ≠ airtight zero-contact.

**Remediation:** classify symlink outsideness with `os.readlink` + lexical `abspath`/`expanduser` join; do not `resolve`/`stat`/`exists` the target; add a focused negative test that a repo symlink to a synthetic legacy path is fail-closed **without** resolving into that target.

### Second P1
**P1 — R0 provenance SoT omits R0.4 disk-hygiene.**  
`plans/codex_execution_ci-rebaseline-rebuild-v3.md` contains `R0.4`; `docs/governance/r0-provenance-and-quality-gate.md` has **no** `R0.4` and no disk/cleanup/hygiene binding (`gov_has_R0.4 False`, `gov_has_disk False`). Plan-level safeguards are not enough while this packet declares the governance doc as R0 SoT.

**Remediation:** bind allow/deny deletion classes and “no legacy-root inventory/cleanup” into `docs/governance/r0-provenance-and-quality-gate.md`; optionally add a non-mutating contract assertion on those deny phrases.

### Claim-by-claim audit

| Claim | Result | Evidence |
|---|---|---|
| Dirty tree preserved; no reset/checkout/clean | **Pass (workspace)** | `HEAD=bb27ec9d750cf02fb64da5dfe665b2f4b262922d`; `CLEAN_TREE_FAIL entries=6647`; `git diff --check` clean; tree still dirty. |
| Pre-change inventory limitation disclosed | **Pass** | Inventory remains path/status ledger; governance correctly does not claim pre-worker byte backup. |
| 422-file “release” set demoted | **Pass** | Both JSONs: `state=dirty-baseline`, `requires_clean_commit_for_release=True`, 422 files. Verifier `--require-clean` → `SOURCE_SET_FAIL ...不能证明发布就绪` exit 1. `gate.sh --require-clean --source-set ...` → `GATE_USAGE_ERROR ...不能与 --require-clean 组合为发布证明` exit 2. |
| Strict quality gate truthful; no false RC | **Pass (workspace)** | Full `bash tools/gate.sh` → `GATE_OK status=quality-only steps=4` (ruff OK; mypy strict **191** files; **858** passed; `LEGACY_REF_OK`). Success labels only `quality-only` / `clean-quality-only`. `--require-clean` alone on dirty tree → `GATE_FAIL ... clean_required=1`. |
| Global mypy suppression removed; ReportLab ignores scoped | **Pass** | No global ignore path in live gate command; scoped ignores: **31** `import-untyped` across **10** `pdf_native` files + **2** `[misc]`. |
| Immutable recovery snapshot contract | **Pass (workspace receipt only)** / **Codex-owned external** | Receipt `status=verified_read_only_recovery_snapshot`, `writable_nodes=0`, `files=19498`. Physical backup/manifest RO not re-verified outside workspace. |
| Disk-hygiene cannot authorize unsafe deletion | **Policy text elsewhere Pass; R0 binding VETO/P1** | Plan has R0.4; R0 governance binding missing. |
| `worker_01` trustworthy as authority | **Reject** | Superseded/stale vs current demotion + dual-flag rejection + current gate semantics. |

### P2 defects
1. Dead/unreachable `gate.sh` forwarding of `--require-clean` into source-set args (~line 107) after early dual-flag reject (~52).
2. `NO_GATE_SH_TESTS`: no contract test executes `bash tools/gate.sh --require-clean --source-set ...` expecting `GATE_USAGE_ERROR`.
3. Governance documents 31 `import-untyped` ignores but omits the 2 `[misc]` ReportLab ignores.

### Objections / decision points for Codex
- Do **not** accept `LEGACY_REF_OK` as proof of airtight zero-contact while symlink `resolve` remains.
- Do **not** accept “R0 complete because `GATE_OK quality-only`.”
- Do **not** treat receipt `writable_nodes=0` as participant-verified physical backup state.
- **Must-fix before clearing VETO:** lexicalize symlink escape detection + test; bind R0.4 into R0 governance SoT — **or** Codex must explicitly accept residual risk in writing.

### Bounded questions for Codex
1. Is residual `Path.resolve` on repo symlinks a blocking zero-contact P1 for M1, or an accepted detection tradeoff?
2. Must R0.4 land in `r0-provenance-and-quality-gate.md` before R0 PASS, or is plan §R0.4 alone sufficient with written disposition?
3. Please re-confirm external backup/manifest hashes and `writable_nodes=0` on disk.

**Safe provisional path:** keep R0 **not accepted**; preserve dirty tree; allow quality-only gate use; forbid cleanup/release actions that assume airtight zero-contact or historical-set release readiness.

## Evidence And Assumptions
**Evidence:**
- Completed full gate: `GATE_OK status=quality-only steps=4` (ruff; mypy 191; pytest 858; legacy OK), wall ~68.6s.
- Dirty-tree: `CLEAN_TREE_FAIL entries=6647`; `bash tools/gate.sh --require-clean` → `GATE_FAIL ... clean_required=1`.
- Dual-flag reject: `GATE_USAGE_ERROR` exit 2; verifier `--require-clean` exit 1.
- Source-set demotion markers confirmed on both JSON docs (422 / dirty-baseline / requires_clean true).
- Symlink residual confirmed by source inspection + synthetic escape finding with resolved absolute target.
- `gov_has_R0.4 False`; `plan_has_R0.4 True`.
- `NO_GATE_SH_TESTS` confirmed.
- `HEAD` unchanged `bb27ec9...`; `git diff --check` exit 0.
- Note: one earlier piped `--require-clean` probe showed shell `exit=0` after `GATE_FAIL` because `| tail` masked the gate exit code; the failure text itself is authoritative, and the dual-flag re-run above correctly returned exit 2.

**Assumptions:**
- Current workspace bytes beat narrative claims.
- External backup state matches receipt only if Codex re-confirms.
- `Path.resolve` on a symlink target is contact; lexical marker construction without resolve/stat/exists is non-contact.

**Uncertainty:** whether Codex already accepted the symlink-resolve residual; whether any post-receipt R0 doc edits are intentionally excluded from the recovery point.

## Risks, Gaps, And Verification Needs
- **Risk:** false confidence in zero-contact while escape symlinks would probe outside/legacy-shaped targets.
- **Risk:** operators reuse obsolete worker recipes if they ignore current gate/verifier errors.
- **Gap:** R0 governance vs plan split-brain on disk hygiene.
- **Gap:** no shell-level regression for dual-flag reject.
- **Still needed (Codex):** physical backup/manifest re-anchor; final acceptance only after P1 repairs or explicit residual-risk acceptance.
- **Not verified here:** visual/PDF/PPT/RC; R2–R6; real legacy absence.

## Recommended Next Step
1. Codex: **hold R0 acceptance (VETO stands)** pending P1 repairs or explicit written residual-risk acceptance.
2. Authorized edit round (not this participant): lexicalize symlink detection + test; bind R0.4 into `docs/governance/r0-provenance-and-quality-gate.md`; optionally fix P2 dead code / shell negative test / `[misc]` docs.
3. Re-run: migration legacy tests, `tools/check_no_legacy_refs.py`, focused governance tests, and `bash tools/gate.sh`.
4. Codex-only: re-anchor external backup/manifest physical verification; then decide PASS.
5. Continue forbidding any use of the 422-file historical set, `GATE_OK quality-only`, or dirty tree as release/RC evidence.
