Bash is unavailable; I'll use Read/Glob/Grep for this read-only audit.

Initial packet loaded: manifest has 28 entries (10 migrated, 18 not_migrated, 6 sensitive-class). Now reading the deterministic closure tests and scanner.

Closure tests are strong. Now checking the scanner, the task tree for 10.4/10.5/10.8 boundaries, and prior review history.

Now verifying migrated target existence and the archive.

All migrated targets exist. Now checking the contract/acceptance tests to independently validate the "59 tests" claim and the enforcement wiring.

Grep output too broad. Counting tests in just the Task 10.4 relevant files.

Counting tests across the likely 59-test suite (migration + contract + negative regressions).

Cross-checking the kangzhe digest chain and the D01-D70 archive.

The 59-test claim is traceable (12 migration + 47 related). Now reading the prior review history to identify the P1/P2 findings that were repaired.

P1/P2 repairs confirmed in current files (sentinel markers pinned + documented, provenance note in migration.md, corrected anchors). Verifying spec anchors, fixture scanner-safety, and the prior round-2 delta verdict.

Round-2 delta confirms all P1/P2 closures. Final spot-checks: no stale `#203-迁移范围` anchors repo-wide, and no legacy-root literals in runtime surfaces that the scanner would flag.

All checks complete. Compiling the final report.

---

# Conference Participant Output: ci-phase10-task104-migration-manifest - general_single_object

## Boundary Check

- **CWD only, read-only**: All reads confined to `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`. Zero writes; report returned inline (runner-managed path untouched).
- **Initial read set**: both assigned files read (`context/ci-phase10-task104-migration-manifest_conference_context.md`, `plans/codex_main_venue_ci-phase10-task104-migration-manifest.md`). Nothing outside the workspace read; legacy root and upstream 康哲 template dir not accessed (Codex-owned live authority).
- **Tool limitation**: `Bash` denied in this non-interactive session → could not execute pytest, `tools/check_no_legacy_refs.py`, or SHA-256. Hash/tests-green evidence rests on Codex's recorded runs (see Evidence) plus my structural verification. No conferences started, no internet, no AGENTS.md reads beyond injected context.

## Independent Work Product

### A. Objective decomposition and audit result

| Objective element | Verdict | Evidence |
|---|---|---|
| 59 项测试 | **TRACEABLE, not reproducible from packet** | Prior Codex review record states "Final combined migration, design-contract, and fixture regression suite: 59 passed in 8.04 seconds, including the absolute-path assertion" (`reviews/codex_conference_ci-phase10-task104-migration-manifest-review_review.md:30`); prior participant recorded 12 migration + 47 related regressions. Migration suite statically counted = 12 (test_manifest_closure.py: 9 incl. 3 parametrized; test_legacy_manifest_contract.py: 1; test_no_legacy_runtime_dependency.py: 2). Exact composition of the 47 and the invoking command are **not recorded in the packet** → see Q1. |
| 精确白名单/排除 | **VERIFIED** | 28 records: exactly 10 `migrated` (exact-set pinned by `APPROVED_MIGRATED_ITEMS`, test_manifest_closure.py:16-27), 18 `not_migrated` covering all 11 `REQUIRED_EXCLUSION_CATEGORIES` (test:28-40, 106-116). All excluded records have `new_path`/`target_sha256` null + `transformation:"none"` (test + schema allOf). Unique item_ids, absolute `old_path`/`old_realpath` (test:79-80 — the round-2 "P3 non-absolute-asserted" note is now stale; the absolute-path assertion exists in the current file). All 10 targets exist, in-repo, non-symlink, digest-match enforced (test:93-103). |
| 敏感哨兵 | **VERIFIED** | 6 sensitive records (4× session_state/cache_state = `f8af859b…b0af8`, 2× plaintext_credentials = `1f3aeb15…`). Repaired D1 is real: markers pinned in test (`SENSITIVE_SENTINEL_MARKERS`, test:42-46) with exact `sha256(marker.encode())` equality (test:129) and published in `docs/acceptance/migration.md:26` with the UTF-8 recipe + no-credential statement. All 6 keep `sensitive_class`/`redacted_sentinel`/`not_migrated`/“未读取”. |
| D01–D70 非运行归档 | **VERIFIED** | `archives/decision-context/ci_workflow_rearchitecture_20260809_context.md` exists; contains D01…D70 sections (grep-verified D01-D09, D70). Non-runtime by three mechanisms: `runtime_dependency:false` on the record, `archives/` in scanner's `NON_RUNTIME_TOP_LEVELS`, and migration.md:12 statement. Codex-recorded ledger sha `cbc2942e…` matches manifest source/target sha (verbatim copy). |
| P0/P1/P2 = 0 | **VERIFIED (with two P3 observations)** | All three prior findings closed in current files: D1 sentinel pinning (test + doc), D2 core-contract provenance (`migration.md:37` observation-vs-snapshot distinction; ADR 0002 §11 records `acdd64bf…` — grep-verified), D3 anchors (`#203-切换门槛` spec:845, `#204-删除旧工程` spec:858 both exist; `#203-迁移范围` has zero matches repo-wide). New P3 observations in §C. |
| 不越界到 10.5/10.8 | **VERIFIED** | No 10.5/10.8 task dirs exist in `.trellis/tasks/` (phase-10 = 101, 102×2, 103, 104 only). `migration/` contains only schema + jsonl (no cutover/delete tooling). migration.md:5, 50-55 explicitly defer inventory/apply to 10.5 and `legacy-absence` to 10.8; PRD non-goals prohibit delete/cutover/RC-freeze. The `legacy-absence` fixture exists but is a scenario input, not a closure claim. |

### B. Independent cross-checks (beyond prior review)

1. **Kangzhe digest chain is internally consistent across the two manifests**: migration manifest target_sha256 for `kangzhe-core-design-contract` (43a82032…), `kangzhe-site-design-contract` (29961fc8…), `kangzhe-verified-logo` (8d16d3ae…) match `contracts/kangzhe/manifest.json` `runtime.files` entries exactly; both wrapper source_sha256 (e513b4c5…) match `source.compatibility_stubs`. ADR 0002 records the same core.md source digest (`acdd64bf…`) and stub digest. The D2 source-chain question is closed by documentation, not by silent data change.
2. **Fixture source binding**: `fixtures/negative/legacy-a-five-products-zero-trials/sample.json` embeds `source_sha256: 48f23f41…` matching the manifest's record — the "provenance not replaced" claim in `fixtures/negative/README.md:3` is consistent (though not mechanically asserted — see C2).
3. **Scanner-surface hygiene**: outside docs/fixtures, every hit for the legacy name is the product name (e.g., `src/ci_workflow/cli.py:584` description, contracts headers, SKILL.md:6) with no trailing-slash/absolute-path marker the scanner would flag; the only skipped file (`migration/legacy_manifest.jsonl`) carries the absolute paths. Consistent with the recorded `LEGACY_REF_OK`.
4. **No claim/reality overreach**: every failure-mode claim in migration.md:48 (unknown fields, dup IDs, whitelist expansion, missing exclusion categories, target escape/symlink, digest drift, new_path on excluded, sensitive file digests, legacy runtime deps) maps to an actually-enforced test or schema rule. Verified individually.

### C. Highest-impact objections / new observations (all P3, non-blocking)

- **O1 (P3, asymmetry in the sentinel scheme)**: the 4 non-sensitive `redacted_sentinel` records (`legacy-global-fact-base` c954a21b…, `legacy-task-runs-and-report-outputs` abc796e3…, `legacy-absolute-path-bindings` a26b795d…, `legacy-top-level-documents` 19f6c6b7…) use unique digests that no test pins and no published marker recomputes (markers exist only for the 3 sensitive categories). A silent digest edit on these 4 records would pass every test. No doc overclaim (migration.md scopes pinning to sensitive markers), but the asymmetry means "把真实文件摘要标成哨兵会因精确值不匹配而失败" does not hold for these 4 rows. → Q2.
- **O2 (P3, documentary digests unpinned)**: the `legacy-negative-regression-assertions` `source_set` digest (f546d930…) and the fixture sample.json `source_sha256` fields are asserted nowhere (target-file digest bdc28853… *is* pinned). Documentary provenance, low risk; Task 10.5 re-measurement makes these moot.
- **O3 (P3, partial kangzhe coverage in this manifest)**: the migration manifest registers only 2 of the 4 same-digest compatibility stubs; the full 4-stub set lives in `contracts/kangzhe/manifest.json:12-17`. Acceptable (kangzhe dir is not the legacy root; `validation_evidence` cites the kangzhe manifest), but a reader auditing "all wrappers excluded" must consult both files. Intent confirmation optional.

## Evidence And Assumptions

- **Observation (direct reads)**: migration/legacy_manifest.jsonl (28 records, all fields); legacy_manifest.schema.json (allOf constraints); test_manifest_closure.py (full — marker pinning, exact whitelist/exclusion sets, absolute-path assertion at :79-80); test_legacy_manifest_contract.py; test_no_legacy_runtime_dependency.py; tools/check_no_legacy_refs.py (full design: skipped file, non-runtime top-levels, historical marking); test_approved_spec_hash.py (pins spec f96be175…); test_design_contract_hashes.py (10 tests); test_legacy_negative_regressions.py (6-class closure); fixtures/negative/README.md + one sample.json; contracts/kangzhe/manifest.json (stubs + runtime.files digests); ADR 0002 §11 digests; spec §20.3/20.4 headings (845/858); docs/acceptance/migration.md (full); archived ledger D01-D70; task 10.4 prd/design/implement/task.json; phase-10 task inventory (no 10.5/10.8).
- **Sourced fact (Codex-recorded, not executed by me)**: 59 passed / Ruff / `LEGACY_REF_OK`; ledger sha `cbc2942e…` (837 lines); migration suite 12 passed. Sentinel digests `f8af859b…`/`1f3aeb15…` inferred (marked) from exact marker text + exact-equality assertion + green recorded run — I could not recompute them.
- **Assumptions**: (1) migration.md is the authoritative human-readable interpretation of the manifest; (2) "59" = 12 migration + 47 related regressions per prior review records; (3) prior review files are advisory history, current files authoritative (per conference context) — current files re-verified directly.

## Risks, Gaps, And Verification Needs

1. **Hash/test-green evidence is Codex-run, not self-run** (Bash denied): the sentinel digests, target digests, 59-test green, and `LEGACY_REF_OK` rest on Codex's recorded runs. My confirmation is structural (exact markers in two places, exact equality assertions, consistent digest reuse, consistent cross-manifest values), not computational. Verification need: Codex re-confirms the two acceptance commands in migration.md:40-41 against the current tree before final acceptance.
2. **Reproducibility of "59"** (Q1): the exact pytest invocation is not in the packet or the acceptance doc. If the acceptance note is the durable governance record, the command should be appended so the number is auditable.
3. **Legacy-root content claims are dated observations**: source_sha256 of not_migrated collections, realpath claims, and the "zero symlinks" observation were recorded by Task 10.4 workers from read-only observation; they are evidence for Task 10.5 cross-checking, not permanent guarantees. Task 10.5 must re-measure before any apply.
4. **Out-of-workspace facts I cannot check**: upstream 康哲 template dir state (stub digests recorded, not re-observed), legacy root existence/integrity, credential-carrier presence. Codex-owned.

## Recommended Next Step

**Finding counts: P0 = 0, P1 = 0, P2 = 0** (two P3 observations: O1/O2 unpinned documentary digests, O3 partial kangzhe coverage — all non-blocking).

**Verdict: ACCEPT** — conditional only on Codex confirming the recorded 59-test + `LEGACY_REF_OK` runs against the current tree (same two commands in migration.md), per the chair's verification domain. Boundary discipline held: manifest closure does not authorize real inventory, cutover, deletion, RC freeze, `legacy-absence` closure, or product acceptance.

**Decision points for Codex**:
- **Q1**: Record the exact pytest invocation (or run-log path) behind the 59-test claim in `docs/acceptance/migration.md`, so the acceptance number is reproducible? (P3, ~1 line.)
- **Q2**: For the 4 unpinned non-sensitive `redacted_sentinel` records (O1) — document them explicitly as non-recomputable disposition declarations (recommended, matches current doc semantics), or pin markers like the sensitive class? (P3, either is safe.)
- **Q3**: Confirm the two unnamed old-root decision-adjacent docs (提问与决策记录.md, 数据采集策略审计与重构计划.md) are intentionally covered only by the `legacy-top-level-documents` sentinel collection (prior D6 note; non-blocking).

**Most important objection restated**: the manifest and its closure tests are substantively sound and now match every claim in the acceptance doc; the only genuine auditability weakness is the undocumented composition of the 59-test suite and the unpinned documentary digests — both cheap, neither blocking.
