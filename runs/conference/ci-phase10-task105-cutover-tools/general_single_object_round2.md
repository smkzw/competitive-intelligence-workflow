Targeted continuation round 2 — verifying only the F1-F4 deltas on current bytes, no broad rediscovery.

Two claimed doc items (repo-local tools, Task 10.6 producer dependency) not visible in the acceptance note grep — checking the task packet and any other location.

Verification complete. All deltas confirmed on current bytes with one documentation discrepancy found. Final report:

---

# Conference Participant Output: ci-phase10-task105-cutover-tools - general_single_object

## Boundary Check

- Targeted continuation round 2, same session. No broad rediscovery; only the F1-F4 deltas re-read: `tools/legacy_cutover.py` (preauthorization/content_mode occurrences via grep + previously re-read full bytes), `tools/verify_release_receipts.py` (owner_status gates, missing-root wrap), both test files, `docs/acceptance/legacy-cutover-tooling.md`, catalog owner_status values, and the Task 10.5 packet (prd/design/implement/task.json) for cross-references.
- Read-only; no edits, no writes, no real legacy root access; Bash still permission-denied (all evidence static). Codex's rerun of focused tests/Ruff/mypy is taken as runner-recorded evidence, not independently re-executable by me.

## Independent Work Product

### Final severity counts (current frozen bytes)

**P0 = 0 · P1 = 0 · P2 = 0.** No remaining concrete blocker for Task 10.5 acceptance. Three P3-level residuals follow (none blocking; two are documentation/coverage items, one is a cross-task handoff).

### Direct verification of F1-F3 (Codex's resolutions)

**F1 — CLOSED. Authorization chain is coherent and acyclic.**
- Directed graph verified on current bytes: `inventory + recovery → validate_inventory` (legacy_cutover.py:478) → preauthorization receipt with `validation_sha256` + computed `content_mode` (496-509) → `_verify_authorization` requires `preauthorization_validation_sha256` (388, 404-408) → `validate_cutover` re-derives the preauthorization from a live drift-checked re-observation and rejects any authorization not bound to it (456-464) → validation receipt binds inventory+authorization+recovery+content_mode (465-475) → `apply_cutover` (577) verifies authorization, optionally `_verify_validation` (585, 512-549), and falls back to `authorization["preauthorization_validation_sha256"]` for the apply receipt's `validation_sha256` (637-641).
- **No circular dependency:** the authorization binds only the preauthorization digest, never the validation receipt; the validation receipt binds the authorization; apply may use either path but both terminate at the same authorization chain. The test helper builds the same DAG (`_authorization` → `validate_inventory` first, test_legacy_cutover.py:87-94). Docs line 11-12 state the interface exactly as implemented (`apply --manifest --authorization --receipt` with optional `--validation-receipt` as extra recheck).
- Current-state re-observation: satisfied at every stage — `validate_inventory` (489-495) and `apply_cutover` (590-597) both re-`lstat` and compare full entry dicts (device/inode/type/sha256/realpath) against the inventory; drift fails closed.

**F2 — CLOSED.** Success signal emits only provable facts: `CUTOVER_VALIDATE_OK escapes=0 recovery=passed content_mode={metadata_only|explicit_content} inventory_sha256=...` (legacy_cutover.py:711-716); `content_mode` is derived from actual entry hash_modes (502-506) and propagated into both validate receipt builders (472, 502) and `_verify_validation` bindings (524, 538, 546) — no KeyError path. CLI test pins both the signal prefix and `content_mode=metadata_only` (test_legacy_cutover.py:278-279). Docs line 17 disclaims unprovable credential counts.

**F3 — CLOSED.** Verifier reads `catalog_owner_status` (verify_release_receipts.py:185): not_applicable requires `owner_status == "not_applicable"` (189-190); accepted requires `owner_status ∈ {pending_future_owner, current_owner, verified}` (197-198). Catalog data consistent: 5× `current_owner`, 12× `pending_future_owner`, 1× `not_applicable` (optional-adapter-recovery); no case digests needed mutation because the status was already part of each frozen case's digest payload — the doc (line 31) records the immutability doctrine and the governed acceptance-root/freeze-record authority boundary. `pending_future_owner` receipt status still never closes (199-201).

**F4 — PARTIALLY documented (one gap found).**
- Code: `_safe_receipt_path` wraps missing receipts root as `ReceiptClosureError` (80-83) — verified.
- Docs: `--scan-root` sanity-gate semantics (line 17) and flat `case-receipts/<case_id>.json` contract (line 23) — verified present.
- **Not found anywhere in the acceptance note or Task 10.5 packet:** the "repo-local governance tools" statement and the "Task 10.6 recovery-producer dependency" (no mention of `10.6`, 恢复包生产者/本地工具/打包 in `legacy-cutover-tooling.md`, prd.md, design.md, implement.md, or task.json; no Task 10.5 checkpoint file exists yet — implement.md F06 is still unchecked). The doc's line 42 references Task 10.7/10.8 needing 最终 RC、恢复包和用户授权, but not the producer contract gap.

### New/remaining P3 residuals (non-blocking)

1. **P3 — owner_status gates lack dedicated negative tests.** The two new rejection branches (189-190, 197-198) are only positively exercised by the happy path; no mutation test flips a catalog owner_status to a disallowed value. Recommend two small tests before freeze.
2. **P3 — Task 10.6 recovery-producer handoff is recorded nowhere.** The consumer contract (`_verify_recovery`: kind/status/passed/sha256/issued_at, unknown-field rejection) is frozen and tested, but the producer obligation (schema file + builder in Task 10.6) should be written into the acceptance note or the pending Task 10.5 checkpoint so it cannot be lost.
3. **P3 — "repo-local governance tools" claim is undocumented.** The two tools and the acceptance note are absent from `package-manifest.json` components and the bundle allowlist; if that exclusion is intentional (they are governance tools, not runtime components), one sentence in the acceptance note makes it auditable.

## Evidence And Assumptions

- **Evidence (observation):** grep/read citations above; catalog owner_status distribution (grep: 5× current_owner @ 101/160/219/278/338; not_applicable @ 1132; 12× pending_future_owner); docs lines 11-12, 17, 23, 31, 42; Codex's recorded focused-test/Ruff/mypy rerun (runner evidence, not independently executed by me).
- **Inference (labeled):** Codex's F1-F3 resolutions are the semantic rulings of record; the doc's line-31 doctrine answers my round-1 question 3 (decoupling intentional, allowlist enforced, authority via governed acceptance root + freeze record).
- **Uncertainty:** runtime pass/fail on the current bytes remains Codex-verifiable only; I have no Bash. Case-digest recomputation after the catalog owner_status baseline is enforced by Task 10.1's `test_fixture_catalog.py`, which I could not execute.

## Risks, Gaps, And Verification Needs

1. Codex: run the expanded final regression on the frozen bytes and record file SHAs + results in the pending Task 10.5 checkpoint (implement.md F06 is still open).
2. Codex: add the two owner_status-gate negative tests (P3, cheap, recommended before freeze).
3. Codex: record the Task 10.6 recovery-producer handoff and the repo-local tools doctrine in the acceptance note or checkpoint (P3).
4. No P0/P1/P2 remains; nothing blocks the acceptance verdict from my side.

## Recommended Next Step

Accept Task 10.5 at **P0=0, P1=0, P2=0** on the current frozen bytes. Codex's remaining actions are process/completeness items, not defects: (1) expanded regression on frozen bytes + checkpoint creation with F06 closure (真实旧根未触碰证明), (2) the two P3 negative tests, (3) the two one-line documentation records (Task 10.6 producer handoff; repo-local tools). No further delta from me unless Codex requests a third pass.

**Bounded questions for Codex (final):**
1. Should I treat the missing Task 10.6-producer and repo-local-tools documentation as covered by the upcoming F06 checkpoint (recommended), or does Codex want them added to the acceptance note before freeze?
2. Confirm the expanded regression run will bind to the current bytes (post-owner_status edits) so the recorded results are the acceptance-pinning results.

Report complete for the runner; Codex remains final authority.
