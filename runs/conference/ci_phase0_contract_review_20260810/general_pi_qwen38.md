I now have complete evidence for all findings. Let me compose the report. Key findings:

1. **Task 0.1**: PASS WITH REQUIRED REPAIR — scanner works correctly (verified), but has two real coverage gaps that could produce false-greens.
2. **Task 0.2**: PASS — frozen sync verified, all hashes/versions/licenses consistent.
3. **Task 0.3**: ADR-0002 reconciliation claim FULLY REPRODUCED — hashes, line counts, single-word drift, hypothetical corrected hash all match exactly.

Let me write the report.

---

# Conference Participant Output: ci_phase0_contract_review_20260810 - general_pi_qwen38

## Boundary Check

- **Effective route accepted**: `cms-smk/cms-model` (daytime CMS replacement for the declared `qwen3.8-max`). Did not attempt provider/model switching. Task contract and tools policy preserved.
- **Workspace boundary respected**: All reads, scans, hashes, and diffs executed inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- **Only workspace-external read exception exercised**: the two Kangzhe candidates at `/Users/smkzw/Documents/康哲项目资料/模版/design_share_v2.md` and `.../design_v2.md` (read-only `stat`/`realpath`/`shasum`/`diff`/`grep` only; no modification, no copy, no derived artifact saved to disk outside `/tmp` ephemeral scratch). No sibling files in that directory were opened.
- **No production writes**: no files modified. ADR-0002 left untracked as found. `implement.md` not touched. Runner-managed report path not written by me; full report returned inline.
- **No other participant output consulted.**
- Did not read any Agent system prompt other than workspace `AGENTS.md`.

## Independent Work Product

### Task 0.1 — Independent Repo & Approved Baseline

**Verdict: PASS WITH REQUIRED REPAIR** (deterministic closure achieved; two coverage gaps that could later produce false-greens).

Re-run results (observed):

| Check | Command | Result |
|---|---|---|
| Scanner (real legacy root) | `CI_WORKFLOW_LEGACY_ROOT=…竞品调研工作流 .venv/bin/python tools/check_no_legacy_refs.py --root .` | `LEGACY_REF_OK … scanned_without_runtime_dependency=true`, exit 0 ✅ |
| Migration test | `pytest tests/migration/test_no_legacy_runtime_dependency.py` | passed ✅ |
| Manifest schema validity | `jsonschema.validate` over all 4 entries | 4/4 VALID ✅ |
| Repo spec copy hash | `shasum -a 256 docs/specs/…v1.2.md` | `f96be175464d06f4a4b2075f020016148e3ac864d07b7ffe05a27db476ca465f` ✅ matches ADR-0000 and manifest item 0 |

Scanner mechanics independently audited (`tools/check_no_legacy_refs.py:91-135`): it keys on the **full absolute resolved legacy path** (`legacy_text = str(legacy_root.resolve())`), not the bare substring `竞品调研工作流`. I confirmed the spec body line containing `竞品调研工作流` (design-v1.2.md:11) does **not** contain the absolute path, so it is correctly *not* flagged. The historical-surface carve-out (`HISTORICAL_ROOTS = {docs, fixtures}`) requiring a `historical:` marker is also exercised by the test. The symlink-to-outside (`EXTERNAL_RUNTIME_SYMLINK`) branch is covered. The scanner logic is sound.

**P1-G1 — Manifest schema is not enforced by any test (latent false-green).** `migration/legacy_manifest.{jsonl,schema.json}` exist and I validated all 4 entries by hand against the schema, but `grep -rn "legacy_manifest" tests/` finds **no test** that loads the JSONL and validates it. The schema enforces `runtime_dependency: const false`, `status` enum, `source_sha256` pattern, and `category` enum — none of which is currently guarded by the suite. A future edit that flips `runtime_dependency` to `true` or corrupts a sha256 would pass `pytest` green.
- **Locator**: absence of test; schema at `migration/legacy_manifest.schema.json:1-31`, data at `migration/legacy_manifest.jsonl:1-4`.
- **Minimal repair**: add `tests/migration/test_legacy_manifest_contract.py` that loads every non-empty line of `legacy_manifest.jsonl`, validates each against `legacy_manifest.schema.json` via `jsonschema`, asserts the entry count is the expected N (currently 4), and asserts every `status=="copied_verified"` item's `source_sha256` matches the actual `target_path` file's `sha256`. This binds the schema to the suite and prevents silent contract drift.

**P1-G2 — No test asserts the repo spec copy hash equals ADR-0000's recorded hash.** ADR-0000 records `f96be175464d…` and I reproduced it, but nothing in `tests/` pins it. If the spec copy drifts (e.g., a well-intentioned edit), the "byte-identical to approved baseline" claim in ADR-0000 decision 2 becomes unenforced.
- **Locator**: `docs/decisions/0000-design-v1.2-approval.md:7,21-23`; no corresponding test.
- **Minimal repair**: add a contract test that reads `docs/specs/competitive-intelligence-workflow-design-v1.2.md`, computes sha256, and asserts equality to the literal `f96be175464d06f4a4b2075f020016148e3ac864d07b7ffe05a27db476ca465f`. Pin the literal as a module constant with a comment pointing to ADR-0000.

Note (not a finding, context only): `ruff check .` reports 284 errors, but all are in vendored `.trellis/scripts/task.py`; `ruff check tools tests migration` is clean. mypy on `tools` clean. venv runs Python 3.13.13 which is within `>=3.12,<3.14`.

### Task 0.2 — Tech Stack & Dependencies

**Verdict: PASS.** Frozen sync, versions, licenses, and the lock file all close.

Re-run results (observed):

| Check | Command | Result |
|---|---|---|
| Dependency contract test | `pytest tests/contract/test_dependency_manifest.py` | passed ✅ |
| Lock frozen | `uv lock --check` | `Resolved 39 packages`, exit 0 ✅ |
| Env matches lock | `uv sync --frozen --dry-run` | `Would make no changes` ✅ |
| Full suite | `pytest -q` | 2 passed ✅ |

Cross-validation I performed against `pyproject.toml` `[tool.ci-workflow.dependencies]` vs `uv.lock`:

| Package | pyproject pin | metadata version | lock version | metadata license | match |
|---|---|---|---|---|---|
| pydantic | 2.13.4 | 2.13.4 | 2.13.4 | MIT | ✅ |
| jinja2 | 3.1.6 | 3.1.6 | 3.1.6 | BSD-3-Clause | ✅ |
| reportlab | 5.0.0 | 5.0.0 | 5.0.0 | BSD-3-Clause | ✅ |
| pypdf | 6.15.0 | 6.15.0 | 6.15.0 | BSD-3-Clause | ✅ |
| pdfplumber | 0.11.10 | 0.11.10 | 0.11.10 | MIT | ✅ |
| playwright | 1.61.0 | 1.61.0 | 1.61.0 | Apache-2.0 | ✅ |
| pyyaml | 6.0.3 | 6.0.3 | 6.0.3 | MIT | ✅ |
| jsonschema | 4.26.0 | 4.26.0 | 4.26.0 | MIT | ✅ |
| pytest | 9.1.1 | 9.1.1 | 9.1.1 | MIT | ✅ |
| ruff | 0.16.2 | 0.16.2 | 0.16.2 | MIT | ✅ |
| mypy | 2.3.0 | 2.3.0 | 2.3.0 | MIT | ✅ |

All 11 direct deps: pin == metadata.version == lock version; all licenses in `APPROVED_LICENSES = {Apache-2.0, BSD-3-Clause, MIT}`; `requires-python == ">=3.12,<3.14"`; no duplicate-version packages in lock; `echarts` asset block matches ADR-0001. The test at `test_dependency_manifest.py:34-75` correctly asserts `set(runtime_by_name) == REQUIRED_RUNTIME_DEPENDENCIES` (exact-set, not subset) and `set(metadata) == set(all_requirements)`, so a name/version mismatch or a metadata entry without a corresponding pin fails. This is a genuine closure, not a false-green.

One observation (not a P0/P1, not blocking): `uv.lock` package records carry no `license` field (0/39 have it). The license truth-source is the hand-curated `[tool.ci-workflow.dependencies]` metadata, cross-checked by the contract test against the `APPROVED_LICENSES` set but **not** against PyPI metadata. ADR-0001 treats this as acceptable ("由合同测试与 uv.lock 双重核对"). I flag it only so Codex knows the license claim is metadata-asserted, not lock-proven; no change recommended for Phase 0.

### Task 0.3 — Kangzhe Contract Reconciliation (decision material only; NOT approved)

**Verdict on the reconciliation claim: PASS — independently and exactly reproduced.** Status remains "等待用户确认" as ADR-0002 states; I do **not** treat it as approved.

#### Stable double-read — both passes identical (observed)

| Role | inode | bytes | lines | mtime | sha256 (read 1 = read 2) |
|---|---:|---:|---:|---|---|
| share `design_share_v2.md` | 61096016 | 316,474 | 4,416 | 2026-08-10 17:54:49.643694160 +0800 | `069f18d5cbfd9a4760f73e53d6b5f54149c44918337ad9c9ff8640389f1b203b` |
| local `design_v2.md` | 61096015 | 320,568 | 4,468 | 2026-08-10 17:54:49.643715660 +0800 | `efa4324aa4a29790da3315bf0cf1fc6d08f4ed25071e3c4f32cf67f4cdb7da2c` |

`path`, `realpath`, inode, size, mtime_ns, and sha256 were all stable across two reads. **No drift.** Matches ADR-0002 §2 table exactly.

#### Common-body anchors (observed)

- share common body: from line **8** to EOF → 4,409 lines / 314,754 bytes → sha256 `caa235370b0653376249416e6871922b6136c54839d050bdcde657138bacb253`
- local common body: from line **60** to EOF → 4,409 lines / 314,754 bytes → sha256 `470a769fe857b558ada91a3f636e5f844a3a58abb551242765df16a0eaa53a20`
- Bodies are equal length; byte-identical except exactly **one** line. Matches ADR-0002 §4.

#### Unique diff — exactly one word, one line (observed)

```diff
- share body line 235 / file line 242: …（经验法则：首屏蓝系像素占比 ≳ 暖橙黄 数倍且暖色 <3% 即失败）…
+ local body line 235 / file line 294: …（经验阈值：首屏蓝系像素占比 ≳ 暖橙黄 数倍且暖色 <3% 即失败）…
```

`diff` reports `1 file changed, 1 insertion(+), 1 deletion(-)`. The only delta is `经验法则` (share) vs `经验阈值` (local). This is a content rule in §0.8.2 (观感 P0 navy-blue failure heuristic). Matches ADR-0002 §4 diff block exactly (its "share 第 242 行 / local 第 294 行" absolute line numbers reproduce).

#### Hypothetical corrected share hash (observed)

I applied the recommended one-word fix in memory (`经验法则` → `经验阈值`, single occurrence confirmed) and recomputed:

- corrected share **full-file** sha256 → `5318be3cf3bd87ac029e0249823322a85a32c3c74fdd00287db82baac6b6a36d` ✅ matches ADR-0002 §5 prediction exactly
- corrected share **common body** sha256 → `470a769fe857b558ada91a3f636e5f844a3a58abb551242765df16a0eaa53a20` ✅ == local body sha256 (convergence proven)
- byte length unchanged: 316,474 → 316,474 (法 and 阈 are both single CJK chars; equal UTF-8 width).

The ADR-0002 reconciliation arithmetic is **correct and reproducible**. The recommended `经验阈值` wording is the semantically tighter choice (the clause gives a measurable pixel-ratio threshold, not a heuristic "rule"). The proposed execution order (fix one word → re-run stable double-read → write measured hashes to manifest → copy + package assets → run tests) is the correct sequence and correctly insists on **measured** hashes over the predicted ones at packaging time.

**P1-G3 — §16.6 of the approved spec carries now-stale Kangzhe hashes; no guard reconciles them.** The approved, frozen spec (`docs/specs/…-v1.2.md:717-719`) pins the *old* candidate hashes:
- share `113cc55f39d4…`, local `8d8dc9f67478…`, common body `49c39fc20944…`.

The live files are v2.1 and now hash to `069f18d5…` / `efa4324a…`. ADR-0002 §1 transparently records this drift and correctly does **not** fabricate a line-level diff against the unrecoverable old bytes. But §16.6 literals remain the contract text in the *approved* spec, and `grep -rn "113cc55f\|8d8dc9f6\|49c39fc2" tests/ tools/` finds **no test** that binds a packaged `design_share_v2.md`/`design_v2.md` to either the old or the new literals. Consequence: once Task 0.3 copies the (corrected) v2.1 files into `contracts/kangzhe/`, nothing fails-closed against the stale §16.6 literals — a false-green is possible if the packaging step forgets to refresh the manifest hashes.
- **This is the highest-impact gap I found.** It is not a defect in ADR-0002 (which is honest about the drift); it is a missing forward guard.
- **Locator**: `docs/specs/competitive-intelligence-workflow-design-v1.2.md:717-719` (stale literals) + `docs/decisions/0002-kangzhe-contract-reconciliation.md:11-14` (old-vs-current table) + absence of test.
- **Minimal repair (post user-confirmation, pre-packaging)**: add `tests/contract/test_kangzhe_design_contract.py` that (a) reads the packaged `contracts/kangzhe/design_share_v2.md` and `design_v2.md`, (b) asserts their measured sha256 equals the values recorded in the package manifest, and (c) asserts the measured common-body sha256 equals the manifest's common-body literal — with the literals sourced from the **confirmed** ADR-0002 §5 (post-fix), not from §16.6. Separately, Codex should decide (bounded question Q1 below) whether to refresh §16.6 via a new ADR or to leave §16.6 as historical and let ADR-0002 supersede it; either way the test must cite the authoritative source.

## Evidence And Assumptions

**Observed (directly executed this pass):**
- Scanner, both contract tests, full suite, `uv lock --check`, `uv sync --frozen --dry-run`, ruff (scoped), mypy: all as reported above.
- Two stable reads of both Kangzhe files with `stat`/`realpath`/`shasum`; byte-level `diff`; in-memory one-word substitution and hash recomputation.
- Manifest schema validation via `jsonschema` (4/4 valid).
- Repo spec copy sha256 == ADR-0000 recorded hash == manifest item 0 `source_sha256`.
- `git ls-files docs/decisions/` → ADR-0002 is **untracked** (consistent with "decision material, not yet user-confirmed").

**Assumptions (stated, not independently verified):**
- `[INFERENCE]` The `historical:` marker convention is the intended escape hatch for docs that legitimately cite the legacy path; the test at `test_no_legacy_runtime_dependency.py:48-61` confirms the scanner honors it. I assume this is the accepted policy, not an oversight.
- `[INFERENCE]` License claims in `[tool.ci-workflow.dependencies]` are taken as truth per ADR-0001; I did not fetch each PyPI project's license metadata to independently confirm (out of Phase 0 scope; no discrepancy found among approved-license set).
- `[INFERENCE]` ADR-0002's statement that "旧候选的字节副本未保存在可核验工作区" is accepted; I confirmed no byte-copy of the v1.2-era candidates exists under `migration/` or `docs/`. A line-level diff against the old hashes is therefore genuinely impossible, and ADR-0002's refusal to fabricate one is correct.

## Risks, Gaps, And Verification Needs

**P0 findings: none.** Nothing blocks Phase 0 acceptance of Task 0.1/0.2 closure or the Task 0.3 *decision material* (the material is honest, reproducible, and explicitly un-approved).

**P1 findings (each with locator + minimal repair above):**
- **P1-G1** — Manifest JSONL not validated by any test → silent contract drift possible. Repair: new `test_legacy_manifest_contract.py`.
- **P1-G2** — Repo spec copy hash not pinned by any test → "byte-identical baseline" unenforced. Repair: hash-assertion contract test.
- **P1-G3** *(highest impact)* — §16.6 stale Kangzhe hashes vs live v2.1 files; no packaging guard reconciles them → false-green at Task 0.4 packaging. Repair: packaging-time hash contract test + Codex decision on §16.6 disposition.

**Highest-impact defect / uncertainty:** P1-G3. The Task 0.3 reconciliation itself is flawless; the risk is *downstream*: the approved spec still names the old hashes, and nothing currently fail-closes a packaged file against the confirmed new ones. This is exactly the class of gap that produces a Phase 0 false-green — the numbers in the ADR are right, but no automated gate enforces them once files are copied.

**Challenge to a plausible assumption:** One might assume that because ADR-0002 records the new hashes, copying the corrected files is safe. It is safe *only if* a test binds the packaged bytes to those recorded hashes. Today no such test exists. The recommended `经验阈值` fix is semantically correct, but its value collapses if the packaging step can silently ship a different byte stream.

## Recommended Next Step

1. **For Codex (bounded questions):**
   - **Q1 (blocks Task 0.4 packaging, not Task 0.3 decision):** §16.6 of the approved spec still pins the *old* Kangzhe hashes (`113cc55f…` / `8d8dc9f6…` / `49c39fc2…`). After user confirmation of the one-word fix, should the §16.6 literals be refreshed via a **new ADR** (superseding, per ADR-0000 decision 2 which forbids editing the approved baseline body), or should §16.6 be left as historical and ADR-0002 + the package manifest treated as the authoritative hash source? Safe provisional path: leave §16.6 untouched (do not edit the approved baseline), record confirmed hashes in ADR-0002 §5 and the package manifest, and enforce via a new contract test that cites the manifest — not §16.6.
   - **Q2 (non-blocking):** Confirm the intended Phase 0 test-file scope for the two new contract tests (P1-G1 manifest, P1-G2 spec hash) — should they land under `tests/contract/` alongside `test_dependency_manifest.py`, and should they be added in the current Task 0.1/0.2 closure or deferred to a Task 0.1/0.2 hardening step before Task 0.4?

2. **For the user (via Codex):** ADR-0002 is ready for the confirmation decision. The single-word `经验法则 → 经验阈值` fix on the share file is reproducible and converges the common body exactly. No change to any value, visual requirement, or product semantics. Recommend Codex present ADR-0002 §3–§5 to the user for explicit approval, then execute ADR-0002 §5's 5-step order with **measured** (not predicted) hashes.

3. **Sequencing:** Do **not** enter Task 0.4 until (a) user confirms the wording, (b) P1-G3's packaging hash test exists, and (c) P1-G1/G2 contract tests are added so the Phase 0 baseline is self-defending. ADR-0002 correctly already blocks copying/packaging before confirmation — that gate must hold.

**Per-task summary verdicts:**
- **Task 0.1:** `PASS WITH REQUIRED REPAIR` — closure real; add manifest-schema test (P1-G1) and spec-hash pin test (P1-G2).
- **Task 0.2:** `PASS` — no P0/P1.
- **Task 0.3 decision material:** `PASS` — reconciliation claim exactly reproduced (hashes, line counts, anchors, single-word diff, hypothetical corrected share hash `5318be3c…` and converged common-body `470a769f…` all confirmed); status correctly remains un-approved; add forward packaging hash guard (P1-G3).
