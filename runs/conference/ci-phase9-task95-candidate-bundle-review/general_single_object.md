I'll re-verify the repaired Task 9.5 evidence on disk against the seven closure checks, without reusing the prior summary.Receipts already show interruption/recovery fields; next I'll inspect argv, recovery digests, install root, and the no-spoon-feed prompt path.I'll dig into the Skill steps, host-smoke prompt builder, archive-binding tests, and Hermes resume evidence next.I have enough independent disk evidence for the seven closure checks; drafting the updated conference output now.

# Conference Participant Output: ci-phase9-task95-candidate-bundle-review - general_single_object

## Boundary Check

- Same-session directed re-review; no task restart, no new conference, no source/install/external writes.
- Read only the authorized Task 9.5 paths plus the listed canonical install root in read-only mode.
- Did not reuse prior-pass conclusions as authority; re-checked current disk state.
- Codex remains final acceptance authority; this output is advisory only.
- Runner-owned report path not written by tools.

## Independent Work Product

### Re-review conclusion

**可接受（advisory accept）。**  
上一轮最高影响缺陷在当前磁盘证据上已实质闭合：完整 no-draft→补件恢复→站点 HTML→项目验证路径、去 fixture-argv spoon-feeding、安装 CLI/中文说明入包、archive↔dist 绑定、规范 `.cc-switch` 三真实宿主通过。仍有非阻断残留（见下），但不构成再次拒绝 Task 9.5 的充分理由。

### Gate-by-gate re-check of prior defects

| # | Prior defect / checkpoint | Result | Current evidence |
|---|---|---|---|
| 1 | Full real-host path: initial evidence-block + zero draft → fixed supplement → explicit reopen/rebind → site HTML → project verify + digest bind | **Closed** | Each receipt has `interruption.{outcome=evidence_blocked, no_draft=true, report_file_count=0, exit_code=4}` then `recovery.reason=user_material_accepted` with reopen/rebind digests; final `run.{outcome=rendered, exit_code=0, state=complete, artifacts=[html]}`. Project `state/host-smoke-v1.json` shows `project_verified=true`. Overview HTML sha `ec9c83…cfa7` matches disk for all three hosts. No PDF/PPTX under project reports. |
| 2 | Remove exact fixture-argv spoon-feeding; Skill self-discovery | **Closed (material)** | Prompt now: read installed `SKILL.md`「候选包宿主验收」, “自行发现并运行已安装入口”; no `fixture run --case …` argv in host prompt. `SKILL.md` owns the recovery command template. Residual: prompt still hints `…/bin/ci-workflow` path. |
| 3 | `tools/install_bundle.py` + Chinese install/acceptance docs in bundle closure | **Closed** | Bundle file count 374; allowlist includes `tools/install_bundle.py`, `docs/user-guide/install.md`, `docs/acceptance/host-smoke/README.md`. `verify_bundle.py` → `BUNDLE_OK` for sha `50a91aac…e8c3`. Install guide uses CLI, not inline Python import. |
| 4 | `archive.json` binds current dist/package/case; tests fail-close stale archive | **Closed** | Archive sha == on-disk dist == claimed `50a91aac…e8c3`; case digest `88471657…cdf1` matches catalog `host-smoke-v1`; package_manifest sha `d1672be7…7ed0` matches installed `package-manifest.json` and all receipts. `test_archived_real_host_receipts_are_complete_when_present` now asserts dist sha equality, `acceptance_status=accepted`, `real_host_pass`, all checks true, interruption/recovery/final fields. Residual: test does not explicitly assert archive `package_manifest_sha256`/catalog case digest equality (manual verify passed). |
| 5 | Canonical `.cc-switch` install; PATH hosts; distinct process/session/run; `batch.real_host_pass=true` | **Closed** | Install root present; `shared`/`omp` link to version `50a91aac…`; projects under that root. Hosts `path_resolved` to `~/.local/bin/{codex,hermes,omp}`. Distinct pids `{41892,43194,44231}`, launcher session ids, final run ids, and interruption run ids. `batch.json` and `archive.json` both `real_host_pass=true`. |
| 6 | Hermes first provider 404 then same session `20260901_094921_a92463` with usable model; not new session; not “no materials” | **Conditionally closed / partial evidence** | Successful Hermes argv proves `--resume 20260901_094921_a92463 --provider openai-codex --model gpt-5.6-luna`; stderr echoes same `session_id`. Final path is rendered HTML after evidence-block, not “未检索到资料”. **Missing in authorized evidence:** archived text/log of the first-attempt default-provider **404** itself. Only resume+provider switch + prior version dir gone (`915e93e5…`) is on disk. |
| 7 | First release fixed to site HTML; no user ask for PDF/PPT | **Closed** | Public Skill: “首版固定生成站点式网页报告，不询问 PDF、HTML 演示稿或可编辑 PPTX.” Catalog/smoke outputs `["html"]` only; archive `html_only=true`; project outputs html only. |

### Highest remaining objections (non-blocking)

1. **Hermes first-failure 404 lacks primary artifact** in the authorized archive. Safe provisional path: accept same-session recovery as proven; if Codex needs audit-grade failure genealogy, attach the failed first Hermes stderr/receipt as sidecar later—not a Task 9.5 reopen by itself.
2. **Soft entry-path hint remains** (`候选运行入口位于 …/bin/ci-workflow`). Better than argv spoon-feeding; Skill still owns steps. Optional later hardening: omit absolute entry path and require Skill-local discovery only.
3. **Install guide remains engineer-facing** (`uv`, pytest, host-smoke commands). Prior “no Python import / no missing CLI / packaged Chinese docs” bar is met; full non-technical UX is still imperfect.
4. **Archive test binding** is strong on dist sha + receipt semantics; could additionally pin `package_manifest_sha256` and catalog `case_digest` to close residual drift windows.

### What changed enough to reverse prior “do not accept”

- Recovery path now exists end-to-end in scenario runner, Skill, receipts, and filesystem HTML.
- Real-host prompt no longer injects the exact fixture command.
- Install CLI + docs are inside the movable package.
- Evidence root is the canonical `.cc-switch` install of the current bundle digest, not only `/tmp`.
- Archive acceptance is bound to current dist sha by test.

## Evidence And Assumptions

### Evidence (re-verified)

- Dist/actual/sidecar/archive bundle sha: `50a91aac3e0050887ae48e29e921a45cf540d986b418eaac8d4af068f6a3e8c3`.
- `BUNDLE_OK … files=374`.
- Canonical install version directory name == bundle sha; OMP link resolves into that version.
- Receipts: interruption no-draft → recovery reopen/rebind → rendered HTML artifact digest match on disk.
- Prompt language checked programmatically: no fixture-argv spoon tokens; Skill-discovery language present.
- `batch.real_host_pass=true`; three PATH hosts; distinct process/session/run.
- Hermes successful argv includes `--resume 20260901_094921_a92463` and provider/model override.

### Assumptions

- Codex’s narrative that the Hermes first failure was specifically endpoint 404 is trusted only insofar as same-session resume+provider switch is evidenced; the 404 string itself was not found in authorized files.
- Focused `63 passed, 1 skipped` / ruff / mypy claims were **not** fully re-executed in this pass; archive-binding and recovery assertions were inspected in source, and bundle verify was re-run. Not treating the numeric test tally as independently proven.

### Inferences

- Prior “accepted too early / no-draft-only” objection is resolved by the new interruption+recovery receipt contract and project HTML outputs.
- Remaining gaps are documentation/genealogy polish, not false-green of the candidate package’s core Task 9.5 exit.

## Risks, Gaps, And Verification Needs

- If auditors require proof that Hermes technical failure was classified correctly at first attempt, archive the failed attempt stdout/stderr; current package only proves successful same-session continuation.
- Optional: tighten archive tests to assert `package_manifest_sha256` and catalog `case_digest` equality, not only cross-receipt consistency + dist sha.
- Optional UX: further simplify `docs/user-guide/install.md` for non-engineers; not required to keep Task 9.5 advisory-green given CLI packaging.

### Bounded questions for Codex (optional, non-blocking)

1. Do you want the Hermes first-failure 404 transcript attached as an acceptance sidecar, or is same-session resume evidence enough?
2. Is the remaining absolute entry-path hint in the host prompt accepted as Skill bootstrap, or should a follow-up remove it?

## Recommended Next Step

1. **Codex may accept Task 9.5** on this evidence set, subject to Codex’s own final authority checks.
2. Treat residuals (Hermes 404 transcript, soft path hint, non-technical install polish) as post-accept follow-ups unless Codex wants them as exit gates.
3. Do not reopen the previous no-draft-only / argv-spoon-feed / missing-install-CLI / tmp-only / unbound-archive blockers; those are closed on current disk.
