I'll run a governance-linked re-review of the repaired Task 9.5 package against the new conference brief, starting with the assigned context and plan.Retrying with the available Read/Shell tools for the governance re-review.Governance lag looks like the remaining blocker; I'll confirm Skill HTML-only language and parent-task linkage before drafting.# Conference Participant Output: ci-phase9-task95-candidate-bundle - general_single_object

## Boundary Check

- Role: `general_single_object` / Pi / cursor / default; same-session governance association re-review; no new implementation.
- Read set: conference context + main-venue plan; SoT limited to Task 9.5 contract, current dist/archive/receipts, tools, Skill/install docs, and read-only `.cc-switch` install.
- Prior `-review` output treated only as defect locator, not as proof.
- No source/install/external writes; no visual/clinical/regulatory final acceptance.
- Trellis task-creation UX does not apply inside this conference worker boundary.

## Independent Work Product

### Re-review conclusion

**技术证据：可接受（Pass）。治理收口：仍需修复。**

当前候选包、规范安装与三真实宿主完整阻断→补件恢复→站点 HTML 路径在磁盘上自洽；但 Trellis 任务状态 / PK 勾选仍未与 `archive.acceptance_status=accepted` 对齐。Codex 可接受工程证据，但不应在治理字段未同步前把 Task 9.5 记为 completed。

### Checklist vs current disk

| Codex checklist item | Result | Evidence |
|---|---|---|
| dist / sidecar / archive / install version digest = `50a91aac…e8c3` | **Pass** | Actual, sidecar, archive, and `.cc-switch/.../shared` version name all match; `BUNDLE_OK` files=374 |
| Three PATH real hosts; distinct process/session/run | **Pass** | `path_resolved` for `~/.local/bin/{codex,hermes,omp}`; pids `{41892,43194,44231}`; distinct launcher session ids and final run ids; `batch.real_host_pass=true` |
| Each receipt: initial zero-draft block → fixed supplement → reopen/rebind → final HTML | **Pass** | All three: `interruption={evidence_blocked,no_draft=true,report_file_count=0,exit=4}` → `recovery.reason=user_material_accepted` with reopen/rebind digests → `run={rendered,exit=0,state=complete,artifacts=[html]}`; overview HTML sha matches disk; `project_verified=true` |
| Public Skill + Chinese install docs HTML-only | **Pass** | Skill: “首版固定…不询问 PDF/HTML 演示稿/PPTX”; install.md declares 站点式 HTML only; archive `html_only=true`; project reports have 0 pdf/pptx |
| Independent Pass/Fail for Codex closeout | **Conditional** | Engineering Pass; governance Fail until Trellis sync |

### Highest-impact remaining defect (governance)

**Archive accepted vs Trellis still open.**

- `docs/acceptance/host-smoke/archive.json`: `acceptance_status=accepted`, `real_host_pass=true`.
- `.trellis/tasks/09-01-phase-9-task-95-candidate-bundle/task.json`: `status=in_progress`, `completedAt=null`.
- `implement.md`: PK01–PK06 and final closeout checkbox all still `[ ]`.
- Parent `.trellis/tasks/08-10-ci-workflow-rebuild/implement.md` still has unchecked `Phase 9：…候选包`; parent `task.json` still `current_task: 9.5`.

This is the main governance-association gap for this packet. Leaving it open creates dual truth: acceptance archive says done, Trellis says not.

**Remediation:** After Codex’s own deterministic re-checks, mark PK01–PK06 done, set task `completed`, clear/advance parent `current_task`, and only then treat Phase 9 Task 9.5 as closed.

### Prior technical defects — still closed on re-verify

1. Full real-host recovery path: still present end-to-end (scenario record + receipts + HTML on disk).
2. Fixture-argv spoon-feeding: still absent; prompts use Skill 「候选包宿主验收」 + “自行发现”. Soft residual: absolute `…/bin/ci-workflow` hint remains.
3. `tools/install_bundle.py` + Chinese install/acceptance docs: inside bundle allowlist/closure.
4. Archive↔dist binding: sha equality holds; archived-receipt test requires dist sha + accepted + interruption/recovery/final fields.
5. Canonical `.cc-switch` install: present and digest-aligned.
6. Hermes same-session resume `20260901_094921_a92463` with `--provider openai-codex --model gpt-5.6-luna`: still in successful receipt argv/stderr. First-failure 404 transcript still not archived (non-blocking residual from prior review).
7. First-release site HTML only: Skill + install docs + outputs confirm; no user PDF/PPT ask.

### Challenge to “just mark accepted”

Do **not** treat `archive.json=accepted` alone as Trellis completion. The conference objective is governance association; unchecked PK boxes after a green archive is exactly the class of drift that later Phase 10 rehearsal will misread.

## Evidence And Assumptions

### Evidence

- Bundle/archive/install digest: `50a91aac3e0050887ae48e29e921a45cf540d986b418eaac8d4af068f6a3e8c3`.
- `verify_bundle.py` → `BUNDLE_OK … files=374`.
- Bundle includes `tools/install_bundle.py`, `docs/user-guide/install.md`, `docs/acceptance/host-smoke/README.md`.
- Three receipts verified: interruption no-draft → recovery → rendered HTML; artifact sha `ec9c83db…cfa7` matches all three project overview files.
- No spoon-fed `fixture run --case` in host prompts; Skill-discovery language present.
- Hermes successful argv includes `--resume 20260901_094921_a92463`.
- Trellis task/implement still unfinished despite archive accepted.

### Assumptions

- No live host re-run in this governance pass; judgment uses current archived receipts + install filesystem + bundle verify.
- Prior review’s “advisory accept on engineering” still holds; this packet adds governance linkage as the decisive remaining gate.
- Focused pytest/ruff/mypy tallies not re-executed here.

### Inferences

- Engineering exit for Task 9.5 is met on current evidence.
- Governance exit is not met until Trellis fields catch up.
- Safe provisional status for Codex synthesis: **engineering Pass / governance pending closeout**.

## Risks, Gaps, And Verification Needs

- Dual-status risk if someone closes Phase 9 from archive alone or keeps reinventing from unchecked PKs.
- Optional residuals (non-blocking): Hermes first-404 transcript sidecar; remove soft entry-path hint; further non-engineer install UX.
- Codex should re-run its checklist deterministic checks (digest equality, receipt interruption/recovery/final fields, PATH provenance) before flipping Trellis to completed.

### Bounded questions for Codex

1. Will you treat Trellis PK/task status sync as a hard closeout gate for this packet, or only as post-accept bookkeeping?
2. Do you still want the Hermes first-failure 404 transcript attached before Task 9.5 completion, or is same-session resume evidence enough?

## Recommended Next Step

1. Codex independently re-checks digest/receipt/install checklist items (already green on this pass).
2. **Required for governance close:** update Task 9.5 `implement.md` PK01–PK06 + final checkbox, set `task.json` to `completed` with `completedAt`, and advance parent Phase 9/current_task markers.
3. Keep technical residuals as optional follow-ups, not reopeners of the candidate-package engineering gate.
4. Final acceptance remains with Codex; advisory participant verdict = **Pass on package evidence, Fail-closed on governance sync until Trellis is updated**.
