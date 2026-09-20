Trellis SessionStart ✓

Proceeding as bounded conference participant `general_single_object` for `ci-phase10-task105-cutover-tools`. Reading the initial read set first.

Reading the source-of-truth packet now — task contract, tools, tests, and docs.

Bash is not permitted in this session; using Glob/Read for the audit instead.

Key discrepancy spotted in the CLI test expectations vs `main()` output strings. Verifying by grep and continuing the read set.

The grep contradicts my earlier read of `legacy_cutover.py` around line 692. Re-reading that region to reconcile.

File content differs from my first read — the current version has a `_success_signal` helper. Reading the remainder to confirm `main()`.

The file changed between my reads (a `_success_signal` repair landed). Re-reading the full current file plus the rest of the receipt packet.

Receipt packet remaining files — catalog, schema, digest implementation, docs, package manifest, and the Task 10.4 checkpoint.

Now the digest implementation, catalog schema, package manifest, and Task 10.4 checkpoint.

Let me verify dependency declarations and bundle inclusion for the two new tools, then check ruff/mypy config scope.

Final evidence sweep — who consumes the two new tools, and any hardcoded legacy paths.

One more consistency check on the required-v12 catalog fragment and its consumers.

Audit complete. I have read the full packet: task contract (prd/design/implement/task.json), `tools/legacy_cutover.py` (current 750-line bytes), `tools/verify_release_receipts.py`, `schemas/release-case-receipt.schema.json`, `schemas/host-receipt.schema.json`, `schemas/acceptance-catalog.schema.json`, `fixtures/acceptance/catalog.yaml` (all 18 required-v12 cases), `src/ci_workflow/application/acceptance_catalog.py`, both test files, `docs/acceptance/legacy-cutover-tooling.md`, `package-manifest.json`, `tests/contract/test_package_manifest.py`, bundle allowlist, and the Task 10.4 checkpoint. Bash is permission-denied in this session, so no test execution was possible; this is a static read-only audit of current disk bytes.

---

# Conference Participant Output: ci-phase10-task105-cutover-tools - general_single_object

## Boundary Check

- **Read set respected**: read only `context/ci-phase10-task105-cutover-tools_conference_context.md` and `plans/codex_main_venue_ci-phase10-task105-cutover-tools.md` plus the packet's source-of-truth files (Task 10.5 contract, both tools, both schemas, catalog, digest impl, tests, docs, manifest, Task 10.4 checkpoint). No production paths read; no real legacy root inspected, inventoried, or touched.
- **No writes**: zero file modifications. The only Bash attempts (directory listing) were permission-denied; I substituted Glob/Grep/Read. I did not attempt to bypass that denial.
- **No conferences, no tool rediscovery, no web scans.**
- **No source edits** — bounded-repair authority remains with Codex.
- **Not writing the runner-managed report path**; complete report returned inline.
- Evidence-integrity note (boundary-relevant): during my pass, `tools/legacy_cutover.py` changed between my first full read (734 lines, `main()` printing raw JSON, no `_success_signal`) and my second read (750 lines, `_success_signal` present, `main()` printing the signal at line 741). Current disk bytes are authoritative for this audit; the mutation implies a repair landed during the conference window (see Finding 9 and Question 4).

## Independent Work Product

### 1. Objective restated (my framing)

Acceptance gate: a read-only, whole-contract audit of Task 10.5's precise cutover tooling + required-v12 owner-stage release-receipt closure, challenging: (a) zero touch of the real legacy root, (b) frozen Task 10.7/10.8 CLI compatibility, (c) multi-root registry, (d) no sensitive-content reads, (e) fail-closed path/symlink/inode/authorization/recovery/idempotence/residue semantics, (f) pre-RC vs release-receipt layering with correct `pending_future_owner` / `not_applicable` semantics. Acceptable only if P0/P1 = 0.

### 2. Verdict

**P0 = 0, P1 = 0 on the current bytes.** Three P2s and several P3s follow; none blocks acceptance, but two should be resolved before Task 10.7 freezes the CLI contract, and one requires a Codex semantic decision. All six challenge areas of the objective hold under static analysis, with the caveats below. **Runtime verification (pytest/ruff/mypy on current bytes) could not be performed by me (Bash denied) and remains Codex's check.**

### 3. Per-challenge-area findings

**(a) Real legacy root zero-touch — PASS.** No default path anywhere in `tools/legacy_cutover.py` (verified: `--legacy-root`/`--registry` are required, mutually exclusive; `apply`/`validate`/`absence-check` take only explicit files). `registry_for_legacy_root` requires an explicit existing non-symlink dir. All 10 tests in `tests/migration/test_legacy_cutover.py` build fixtures exclusively under `tmp_path` (verified line-by-line: `_fixture`, `_registry`, `test_partial_apply...` etc.); the CLI test passes only `tmp_path` arguments. `tests/migration/test_no_legacy_runtime_dependency.py` also uses `tmp_path`. No hardcoded user paths in the tool. The only path that could ever touch a real root is Task 10.7's own deliberate invocation — out of Task 10.5 scope. Task 10.4 checkpoint confirms the real root was unmodified and unread-executed.

**(b) Frozen CLI compatibility — PASS with one overclaim (P2).** `test_cli_matches_frozen_task_107_and_108_argument_contract` (lines 230-318) pins: `inventory --legacy-root|--registry --manifest/--output`, `validate --manifest --authorization? --legacy-root? --recovery-receipt --output?`, `apply --manifest --authorization --validation-receipt? --receipt/--output`, `absence-check --manifest --scan-root? --output?`. Current `_parser()` matches; `_success_signal` output now matches the test's asserted strings (`CUTOVER_INVENTORY_OK mutated=0`, `CUTOVER_VALIDATE_OK escapes=0 credentials=0 recovery=passed`, `CUTOVER_APPLY_OK`, `LEGACY_ABSENCE_OK`). **P2: the success signal hardcodes `escapes=0 credentials=0` without computing either.** Escapes are true-by-construction (any escape raises before success). But "credentials=0" is a security claim with no detector behind it: vacuously true under `--legacy-root` (metadata-only, nothing read), and **false in general** under an explicit content-mode registry where `_directory_digest`/`file_digest` hash file bytes that may include credential-like files. An automation consumer grepping `credentials=0` would be misled. Fix now (before Task 10.7 freezes on it): make the signal mode-aware, drop the credential claim, or reword to `content_read=no|yes`.

**(c) Multi-root registry — PASS with nuance (P3).** `approved_roots` is a list; `_containing_root` picks the longest lexical match; duplicate roots rejected; per-entry root containment enforced; registry digest binds the whole multi-root payload. Nuance: `_reject_symlink_ancestors` checks the approved root and ancestors *within* it, but not symlinks *above* the root (e.g., macOS `/tmp -> /private/tmp`; or a segment between two overlapping approved roots). This is mitigated because `realpath` is recorded at inventory and recomputed at validate/apply, so a retargeted parent symlink changes `realpath` and trips the drift comparison (fail-closed). Recommend documenting this boundary rather than changing code.

**(d) No sensitive-content reads — PASS under the contract's two modes.** `--legacy-root` shorthand: all entries `hash_mode: metadata` (pinned by `test_legacy_root_shortcut_never_reads_unknown_file_content`); metadata digest = mode/size/type (+link text for symlinks) — no content bytes. Explicit registry: `content` mode is opt-in and requires human review of the registry JSON (documented in code comment and doc); `_directory_digest` under content mode recursively reads **all** nested file contents — this is the one place sensitive content could be read, and it is gated only by reviewer discipline. This matches PRD ("Exact content hashing is opt-in via an explicit reviewed registry") — accepted, but I flag it as the single sharpest corner of the "never read" claim.

**(e) Fail-closed semantics — PASS, verified line-by-line.**
- Path escape: `_absolute_clean_path` (absolute, no `..`) + `_containing_root` containment; tested.
- Symlink: root itself must not be a symlink (`_reject_symlink_ancestors` lines 113-118, added since the execution audit); entry ancestors checked; leaf symlinks only read-link-target + unlinked, never followed; kind-vs-observation consistency check in `build_inventory`; tested (alias-root, kind drift).
- Inode/device/type/digest drift: `validate_cutover`/`validate_inventory`/`apply_cutover` re-observe and compare the full entry dict including `device`/`inode`/`realpath`/`sha256`; tested (content mutation → 漂移).
- Authorization: self-digest + `inventory_sha256` + `registry_sha256` + exact `actions` list equality; tested.
- Recovery: consumer contract `_verify_recovery` (kind `recovery-package-v1`, status `passed`, lowercase 64-hex sha256, tz-aware ISO8601; unknown fields rejected); gate failures tested via parametrized `test_recovery_receipt_gate_fails_closed`.
- Idempotence: `apply_cutover` second run reports `already_absent`/`retained`; tested. Partial-failure resume: children-first ordering by path depth; `_matches_directory_after_child_deletes` (sha256-exempt for directories) enables resumption with the same authorization; tested (`test_partial_apply_is_fail_closed_and_same_authorization_resumes`).
- Residue: `absence_check` fails on any still-existing registered entry **including `retain`** (pinned by `test_absence_check_does_not_treat_retain_as_absent`); final gate must use a full-disposition registry (documented in design.md) — this resolves the earlier retain-absence "deadlock" concern by contract, not by code.
- Structural contradictions: delete-parent+retain-child rejected; duplicate entry_id/path rejected; all-empty inventory rejected.
- TOCTOU residue: between `lstat` and `unlink`/`rmdir`, a swap is bounded — `unlink` on a symlink removes the link (never the target), `rmdir` on a symlink fails `ENOTDIR`, and the post-delete `exists()/is_symlink()` check re-arms; the doc honestly states digests are "漂移可见性，不是数字签名".

**(f) Pre-RC vs release-receipt layering and pending/not_applicable semantics — PASS with one open semantic decision (P2).**
- Layering: catalog `receipt.schema` must equal `schemas/host-receipt.schema.json` (pre-RC host envelope, pinned per case); the final owner-stage envelope is `release-case-receipt.schema.json`, verified with `additionalProperties: false`, status-conditional `allOf`, tz-aware `issued_at`, self-`receipt_digest`.
- Bindings verified: case_id, release_scope, owner_task, catalog_sha256 (file bytes), case_digest (recomputed via `compute_case_digest` with `case_digest` excluded, reports/formats sorted, inputs path-sorted), package_manifest_sha256, release_candidate_sha256, input_sha256 (recomputed from sorted inputs), plus schema-required run_id/session_id/artifact_sha256/verdict_sha256/project_contract_sha256/not_applicable_reason_zh/issued_at.
- `pending_future_owner` never closes: any status ≠ `accepted` (except the restricted `not_applicable`) raises `未在 owner 阶段 accepted`; tested.
- `not_applicable` restricted: requires catalog `execution_scope == conditional-extension` **and** a `not_applicable` string, binds `project_contract_sha256` to the actual contract file and reason equality to the catalog string; catalog-side rules additionally pinned by `test_fixture_catalog.py::_assert_required_owner_and_state_rules` (only `optional-adapter-recovery` may be conditional-extension/not_applicable; E1 reason must mention 合同摘要). Tested with five mutation cases.
- Path hardening: `_safe_receipt_path` rejects symlink root/receipt/ancestors and enforces resolution inside the receipts root; tested.

### 4. Findings register

| ID | Sev | Finding | Recommendation |
|---|---|---|---|
| F1 | P2 | `apply_cutover` accepts `validation=None` and CLI `apply` accepts no `--validation-receipt`, while `docs/acceptance/legacy-cutover-tooling.md` states "apply 只接受已经验证的同一授权链". Security impact is nil (apply re-verifies inventory digest, authorization chain, and live FS drift itself), but the doc contract is stronger than enforcement — a Task 10.8 automation could skip the formal validation step. | Freeze now: make `--validation-receipt` required in the CLI contract (and `validation` required in `apply_cutover`), or reword the doc to "授权链匹配 + 当前状态无漂移". |
| F2 | P2 | `CUTOVER_VALIDATE_OK ... credentials=0` is asserted without any credential-detection logic; false for content-mode registries. | Make the signal mode-aware or drop the credential claim (see challenge (b)). |
| F3 | P2 | Aggregator never cross-checks catalog `receipt.owner_status` (`pending_future_owner`) against receipt `status`; a case still declared pending in the catalog can be closed by an `accepted` release receipt. Catalog-side semantics are pinned by `test_fixture_catalog.py`, but the aggregator is decoupled from them. Possibly intentional (catalog stays pending; the release receipt is the RC-time artifact) — needs Codex's ruling. | Either enforce "accepted requires catalog owner_status ∈ {current_owner, verified}" (if the catalog is expected to transition at freeze), or document explicitly that the decoupling is intentional and that closure authority is the governed receipts-root + freeze record, not the catalog field. |
| F4 | P3 | `--scan-root` on `absence-check` is a containment sanity gate only; it never scans for unregistered remnants (registered-only is per PRD). Flag name over-promises. | Document as sanity gate; optionally rename. |
| F5 | P3 | Recovery-package receipt has a consumer contract only (`_verify_recovery`); no schema file and no producer exists in Task 10.5. | Task 10.6 must define the producer contract with at least `receipt_kind/status/recovery_package_sha256/issued_at`; record in 10.5 checkpoint as cross-task dependency. |
| F6 | P3 | Catalog `receipt.relative_path` (e.g. `docs/acceptance/receipts/required-v12/<case>.json`) is never consumed; aggregator locates receipts as `<case_id>.json` flat under `receipts_root`. Works in practice only if the runner points `receipts_root` at the case-id directory level. | Document the flat `<case_id>.json` contract in the acceptance note, or honor `relative_path`. |
| F7 | P3 | `validate_inventory` accepts `legacy_root=None` (CLI `validate` without `--authorization` and without `--legacy-root` issues a receipt with no root binding). Fail-closed downstream (apply re-checks), but the receipt over-promises. | Require either `--authorization` or `--legacy-root` in the CLI contract. |
| F8 | P3 | `_safe_receipt_path` propagates `FileNotFoundError` (not `ReceiptClosureError`) when `receipts_root` is missing; caught in CLI `main` but inconsistent in library use. | Wrap in `ReceiptClosureError`. |
| F9 | P3 | `tools/legacy_cutover.py` changed during my pass (734→750 lines; `_success_signal` added). The recorded "24 focused + 162 regressions passed" predates or coincides with this byte change — unverifiable by me. | Codex: confirm whether a bounded repair landed in-window and re-run the suites on current bytes; record it in the checkpoint. |
| F10 | P3 | `_directory_digest` under `content` mode reads the full nested tree (O(tree), includes any sensitive bytes); the two new tools and `legacy-cutover-tooling.md` are not declared in `package-manifest.json` nor in the bundle allowlist (consistent: they are governance tools, not runtime components; `release-case-receipt.schema.json` **is** declared, so the manifest schema-closure test holds). | No change needed; note in checkpoint that tools are intentionally repo-local. |

### 5. Highest-impact objections (ranked)

1. **F2 — a false security claim in the frozen CLI success signal.** This is the item most likely to be consumed blindly by Task 10.7/10.8 automation. Cheap to fix now.
2. **F1 — doc-vs-code contract looseness on the validation receipt.** If left, Task 10.8 ships a weaker gate than the approval note promises.
3. **F3 — owner-stage semantics ambiguity.** Not a defect under the "visibility, not signature" doctrine, but the closure's authority ultimately rests on the governed process that writes `receipts_root`; the aggregator only detects drift. Codex should record the receipts-root path + freeze run evidence explicitly, or a future reviewer will ask exactly this question.
4. **F9 — evidence-integrity during the conference window.** My audit is of bytes that changed mid-pass; the recorded test results must be re-pinned to the frozen bytes.

## Evidence And Assumptions

**Evidence (observation, from current disk bytes):**
- `tools/legacy_cutover.py` (750 lines): `_parser()` subcommands/flags at 663-686; `_success_signal` at 689-702; `main()` prints signal at 741, `LEGACY_CUTOVER_FAIL` on `CutoverError` at 743; fail-closed checks as cited per line group above.
- `tools/verify_release_receipts.py`: binding loop 164-177; not_applicable gate 179-189; pending/status gate 191-194; `_safe_receipt_path` 77-93; catalog schema re-validation 109-121.
- `schemas/release-case-receipt.schema.json`: `additionalProperties: false`, 19 required fields, status `enum` incl. `pending_future_owner`/`rejected`, `allOf` accepted/not_applicable branches, tz pattern on `issued_at`.
- `fixtures/acceptance/catalog.yaml`: 18 required-v12 cases; all `receipt.schema == schemas/host-receipt.schema.json`; only `optional-adapter-recovery` has `execution_scope: conditional-extension` + `not_applicable`; `legacy-absence` owner_task `phase-10-task-108-legacy-absence`; others `phase-10-task-106-rc-freeze`.
- `tests/migration/test_legacy_cutover.py`: 10 tests, all tmp_path-only; CLI contract test 230-318; retain-absence pin 221-228; recovery-gate negative params 320-338.
- `tests/acceptance/test_required_receipt_closure.py`: 8 tests incl. schema strictness, pending rejection, owner/input/not_applicable drift, digest drift, symlink escape.
- `docs/acceptance/legacy-cutover-tooling.md`: boundary statement (no real-root execution), mechanical verification block (pytest/ruff/mypy/check_no_legacy_refs), honesty note on digest-vs-signature.
- `package-manifest.json`: declares `schemas/release-case-receipt.schema.json`; `tests/contract/test_package_manifest.py` enforces `declared_schema == actual_schema`; `tools/bundle_contract.py` DEFAULT_ALLOWLIST does not include the two tools or the acceptance note.
- Task 10.4 checkpoint: 28-manifest closure; six sensitive carriers sentinel-only; conference review P0/P1/P2=0; real root untouched.

**Assumptions (inference, labeled):**
- The catalog `case_digest` values in `catalog.yaml` match `compute_case_digest` on current bytes (Task 10.1's `test_fixture_catalog.py` and Task 10.5's closure test both depend on it; Codex's recorded passing suites support this, but I could not re-run).
- The current `_success_signal` bytes are the intended frozen form (they postdate the execution audit).
- `docs/acceptance/legacy-cutover-tooling.md` wording is the acceptance note of record for contract interpretation.

**Uncertainty:** All runtime claims (tests passing, ruff/mypy, digests) are unverified by me — Bash was permission-denied; I made no attempt to work around it.

## Risks, Gaps, And Verification Needs

1. **Test execution on current bytes (blocking for Codex, not for my verdict):** re-run `uv run pytest tests/migration/test_legacy_cutover.py tests/acceptance/test_required_receipt_closure.py tests/contract/test_package_manifest.py -q`, plus ruff/mypy/`check_no_legacy_refs.py`, and the 162-regression suite, then record results against the frozen SHA of the five files. My static audit says the code and tests are mutually consistent, but I cannot attest to pass/fail.
2. **CLI contract decision before Task 10.7:** F1 (validation-receipt mandatory?) and F2 (credentials claim) must be settled while the contract is still soft.
3. **Owner-stage semantics ruling (F3):** document whether catalog `owner_status` is expected to transition at RC freeze and whether the aggregator should enforce it.
4. **Closure governance:** record receipts-root path, freeze run/session IDs, and the producing process in the RC freeze record; state explicitly that receipt digests are drift-detection, not signatures.
5. **Recovery-package contract:** Task 10.6 must add a producer + schema for `recovery-package-v1`; 10.5's consumer contract is frozen and sufficient.
6. **Real-root claim:** keep the Task 10.5 checkpoint's "真实旧根未读取执行、未修改、未删除" statement tied to the recorded suite runs, not just to code shape.

## Recommended Next Step

Accept Task 10.5 as **P0/P1 = 0 on current bytes**, conditional on Codex: (1) re-running the focused + regression suites on the frozen file bytes and recording results (F9); (2) resolving F1/F2 in the CLI contract before Task 10.7 (recommend: require `--validation-receipt` on apply; drop or mode-gate `credentials=0` in the success signal); (3) ruling on F3 and recording the governance boundary; (4) noting F5 (recovery producer) as a Task 10.6 dependency in the checkpoint. No P0/P1 repairs are required by my pass; the P2s are contract-freezing items, not correctness defects. My next bounded action: none pending — awaiting Codex's decisions on the three questions below.

**Bounded questions for Codex:**
1. Should `apply`/CLI require `--validation-receipt` (frozen now), or should the acceptance note be reworded to match the current optional-validation code? (F1)
2. Should the `CUTOVER_VALIDATE_OK` signal drop `credentials=0` / become mode-aware, and do you confirm no credential-content guarantee is intended beyond the metadata-sentinel `--legacy-root` path? (F2)
3. Is the decoupling of catalog `receipt.owner_status` from the release-receipt closure intentional, and what governs the transition to closure at RC freeze (frozen catalog vs governed receipts-root)? (F3)
4. Did a bounded repair (the `_success_signal` addition) land during the conference window, and do the recorded suite results correspond to the current 750-line file bytes? (F9)
