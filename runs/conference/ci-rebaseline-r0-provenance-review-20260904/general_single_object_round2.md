Full gate evidence is in (191/860/`GATE_OK quality-only`). Returning the completed round-2 PASS report.# Conference Participant Output: ci-rebaseline-r0-provenance-review-20260904 - general_single_object - round 2

## Boundary Check
- Same-session round 2; read-only re-audit only.
- Stayed inside workspace `.`; did not inspect the external recovery backup or the forbidden legacy root.
- Did not follow symlinks or resolve their targets during this audit (source inspection + pytest synthetic temps + non-resolving component/gate commands only).
- Did not edit any workspace artifact; did not write `runs/conference/ci-rebaseline-r0-provenance-review-20260904/general_single_object_round2.md`.
- Physical backup matching / writable-node RO remains Codex-owned; not claimed here.
- Final R0 acceptance remains Codex-owned.

## Independent Re-audit

### 1) Zero-contact symlink lexicalization — **Remediated**
**Evidence:** `tools/check_no_legacy_refs.py` now uses `_lexical_symlink_target()` with `os.readlink` + lexical `abspath`; symlink outsideness uses that helper, not `path.resolve()`. Remaining `.resolve()` calls are only on the **workspace scan root** (`root.resolve()` / `args.root.resolve()`), not legacy/symlink targets.  
**Test:** `test_external_runtime_symlink_is_classified_without_resolving_target` present; focused suite including it: **10 passed**.

### 2) R0.4 disk-hygiene SoT binding — **Remediated**
**Evidence:** `docs/governance/r0-provenance-and-quality-gate.md` §10 `## 10. 里程碑磁盘卫生（R0.4）` binds allow class (current-task, exact path, reproducible), deny/retain (normative docs, checkpoints, manifests, receipts, scientific evidence, fixtures, current+previous recovery points; no broad glob/`git clean`), evidence-before-cleanup (`已经由摘要或哈希替代`), reclaimed-byte accounting, and no-legacy inventory (`真实旧根不属于空间盘点对象`).  
**Contract:** `test_r0_disk_hygiene_is_fail_closed_and_excludes_legacy_root` present and covered by the focused 10-pass run.

### 3) Gate dual-flag reject / dead forwarding — **Remediated**
**Evidence:** early reject at `gate.sh` line 52 before any quality step (`usage_before_steps True`; first `run_step ruff` at line 96). Dead `source_args+=(--require-clean)` **absent**. Shell negative test `test_gate_rejects_historical_source_set_clean_claim_before_running_steps` present. Live re-run: `GATE_USAGE_ERROR ...` / `dual_flag_exit=2`.

### 4) ReportLab ignore truthfulness — **Remediated**
**Evidence:** governance declares both ignore classes; disk recount matches **`{'import-untyped': 31, 'misc': 2}`** across 10 `pdf_native` files. Live gate command remains `mypy ... --strict ...` with `no-global-ignore` in scope string.

### 5) Consolidated quality gate truthfulness — **Remediated / corroborated**
**Evidence (this round, completed full gate + independent re-runs):**
- Full `bash tools/gate.sh` → `GATE_OK status=quality-only steps=4` / `GATE_EXIT=0`
- Scope: `ruff=src,tests,tools mypy=src,tools,strict,no-global-ignore tests=tests/unit,tests/contract legacy=check_no_legacy_refs clean=not-required`
- Ruff OK; mypy strict **191** files; unit+contract **860 passed**; `LEGACY_REF_OK`
- Independent component re-runs also: 860 / mypy 191 / ruff OK / legacy OK
- Dirty tree preserved: `HEAD=bb27ec9d750cf02fb64da5dfe665b2f4b262922d`; `DIFF_CHECK_EXIT=0`
- Success labels remain `quality-only` only; no release/RC claim

**Challenge vs round-1 VETO:** Round-1 P1s (symlink `resolve`, missing R0.4 SoT) and P2s (dead require-clean forwarding, missing shell negative test, undocumented `[misc]`) are absent from current bytes. Do not restate them as open defects.

**Residual observation (non-blocking):** R0.4 contract asserts the strongest deny/retain phrases; optional hardening could also require the evidence-before-cleanup / reclaimed-byte phrases literally. Policy text already contains them. Not enough to VETO.

## Evidence And Assumptions
**Evidence:** source corroboration of the five remediations; focused pytest **10 passed**; dual-flag live reject exit 2; completed full gate `GATE_OK quality-only steps=4` with **191/860**; independent component re-runs matching; HEAD/`diff --check` checks; ignore-code recount.

**Assumptions:** current workspace bytes beat prior narratives; `os.readlink` + `abspath` without `realpath`/`Path.resolve` on targets is non-follow; receipt external path claims remain Codex-owned anchors.

**Uncertainty:** physical backup/manifest RO and `writable_nodes=0` not re-verified outside workspace (by design).

## Remaining Risks Or Gaps
- Codex still must re-anchor external backup/manifest physical state before final R0 disposition.
- R0 remains a preservation/quality baseline, not HTML-only release closure; historical 422-file sets stay demoted.
- Optional hardening: broaden the R0.4 contract phrase assertions.

## Updated Verdict
**PASS**

## Recommended Next Step
1. Codex: incorporate this round-2 PASS; complete the Codex-owned external backup/manifest RO re-anchor.
2. If that physical check holds, Codex may dispose R0 as accepted for M1 continuation.
3. Keep forbidding any interpretation of `GATE_OK quality-only`, the dirty tree, or the 422-file historical sets as release/RC evidence.
4. Optional non-blocking cleanup: broaden the R0.4 contract phrase assertions; no further participant edit authorized in this round.
