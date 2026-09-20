所有检查均已通过。最终报告如下。

# 执行输出：ci-phase9-task91-correction-approval - worker_01

## 边界与上下文检查

- 以有限执行者身份运行；仅执行工作项 1：`实现 correction-proposal schema、包清单登记与合同测试，禁止用户可见工程化标签`。工作项 2 (append-only correction service) 和 3 (graph definitions + integration tests) 未被触动，留给 worker_02/worker_03 处理。
- 初始读取集已全部消耗：`context/…_execution_context.md`，`plans/codex_execution_ci-phase9-task91-correction-approval.md`。额外的上下文读取（已记录在报告中）：`.trellis/tasks/08-31-phase-9-task-91-correction-approval/{prd.md,design.md,implement.md}`；`docs/specs/competitive-intelligence-workflow-design-v1.2.md` §17.1/§10.2 修订章节 (grep-定位)；`docs/decisions/0013-site-first-v1-delivery-scope.md`；`migrations/0005_corrections_idempotency.sql`；`src/ci_workflow/graph/{transitions.py,guards.py}`；`src/ci_workflow/domain/{enums.py,ids.py}`；现有的 schema 清单、清单测试和打包复制约定。未读取生产路径或旧工作区；未执行网络操作。
- 按照指示保留了已污染的工作树。我对已追踪文件唯一的修改是在现有的已污染 `package-manifest.json` 中增加了一行；所有其他工件均为新文件。

## 已执行工作

1. **`schemas/correction-proposal.schema.json`** (new, hand-authored Draft 2020-12, following the `gate-override.schema.json` compact style). It encodes the full `design.md` 数据合同:
   - Required bindings: `schema_version`, `proposal_id`, `project_id`, `report_kind(A/B/C)`, `report_version`, `snapshot_id`, `snapshot_content_digest` (64-hex), `state`, `target`, `current_visible_value`, `user_reason_zh`, `submitted_at`, `publish_idempotency_key`, `impact_set`; plus `anyOf` requiring `proposed_value` or `proposed_explanation_zh` (建议值或解释).
   - `state` enum is byte-equal to the frozen six-state `RevisionApprovalState` contract (`submitted / needs_evidence / rejected / validated_pending_user_approval / approved / published`).
   - `target` requires `target_type ∈ {fact, claim, chart_point, matrix_cell}` (§17.1 target vocabulary) and a `target_id` matching the existing `stable_id` convention `^[a-z][a-z0-9-]*_[0-9a-f]{24}$`, plus a user-readable `target_label_zh`.
   - Append-oriented optional structures: `attachments` (link/file with conditional required url/file_name), `evidence_items` (each with a retrievable anchor: url or source_version_id), `conflicts`, `validation` (five named checks; **disposition enum is `needs_evidence/rejected/validated_pending_user_approval` only — no approval value exists**), `owner_decision` (approve/reject/needs_evidence; `approval_id` required exactly when approving), `rebuild_receipt`, `independent_qc` (`qc_result` const `accepted`), publish binding fields, `prior_proposal_id` (前后版本关系).
   - Fail-closed conditionals: `published` ⇒ new snapshot id+digest, rebuild receipt (≥1 view), independent QC accepted, published version id and timestamp all required; `approved|published` ⇒ `owner_decision.decision == "approve"` (validation can never approve); `validated_pending_user_approval` ⇒ validation record with matching disposition; `rejected` ⇒ validation rejection or explicit owner rejection.
   - **禁止用户可见工程化标签**: a `$defs/InternalLabelGuard` (`not`-enum of all internal vocabulary: 6 states, dispositions, decisions, target types, attachment kinds, `accepted`) is applied to every user-visible field; prose fields (`*_zh`) additionally require at least one Han character. Display values (`current_visible_value`/`proposed_value`) deliberately allow digits/Latin (report values shown verbatim, e.g. "ORR 45%") while still rejecting internal labels.
2. **`src/ci_workflow/schemas/correction-proposal.schema.json`** — byte-identical packaged copy (verified with `cmp`; matches the `scientific-qc-verdict` sync-copy convention).
3. **`package-manifest.json`** — registered `schemas/correction-proposal.schema.json` in `components.schemas`. This is mandatory: `test_package_manifest.py` asserts declared schemas == all `schemas/**/*.schema.json` + `contracts/**/*.schema.json` on disk.
4. **`tests/contract/test_correction_proposal_contract.py`** (new, 18 tests) — schema self-check; packaged-copy byte identity; manifest registration; state enum cross-checked against `ci_workflow.domain.enums.RevisionApprovalState`; full lifecycle positive vector (submitted → validated → approved → published); negative vectors for: missing proposed value/explanation, non-conforming `target_id`, malformed attachment/evidence shapes, validation disposition `approved` (rejected by enum) and validation-only path to `approved` state, approval without owner decision or without `approval_id`, each of the six publish prerequisites deleted individually, empty rebuild, vetoed QC, bad digest, unexplained `rejected` state, `validated_pending_user_approval` without matching validation, engineering labels in user-visible fields, ASCII-only prose, naive timestamps (explicit UTC-offset pattern), and guard-vocabulary coverage of the runtime enum.

## 工件与证据

| 文件 | 状态 |
|---|---|
| `schemas/correction-proposal.schema.json` | new (untracked) |
| `src/ci_workflow/schemas/correction-proposal.schema.json` | new (untracked), byte-identical to above |
| `tests/contract/test_correction_proposal_contract.py` | new (untracked) |
| `package-manifest.json` | 1 line added to `components.schemas` (file already dirty with user edits, preserved) |

Schema ↔ contract traceability: six states = v1.2 §10.2 修订审批族 / `RevisionApprovalState`; publish prerequisites = PRD 验收 #4 and guard `g_revision_approved_published` (`new_snapshot_built`, `affected_artifacts_rebuilt`, `independent_qc_passed`, `approval_id`); approval separation = PRD #3; append-only evidence/conflicts = `g_revision_needs_evidence_submitted` semantics; publish idempotency key = §17.1 发布幂等键; stable target ID = `domain/ids.stable_id`.

## 命令与观察

- `uv run pytest tests/contract/test_correction_proposal_contract.py -q` → **18 passed**.
- `uv run pytest tests/contract/test_package_manifest.py -q` → **1 passed** (manifest equality holds with the new registration).
- `uv run pytest tests/contract -q` → 206 passed, **3 failed**: `test_design_contract_hashes.py` (2) and `test_offline_assets.py` (1). Observation (evidence): those test files reference neither `package-manifest.json` nor any correction schema (grep: zero hits), and the failures are hash/boundary mismatches in `contracts/kangzhe/*` and `assets/html-ppt/*` — all listed as pre-modified in the initial git status. Inference: pre-existing dirty-worktree drift, untouched and preserved per the boundary. Uncertainty: none material; I did not run a stash-based control because the worktree contains authoritative user edits that must not be disturbed.
- `uv run ruff check tests/contract/test_correction_proposal_contract.py` → passed.
- `uv run mypy tests/contract/test_correction_proposal_contract.py` alone → 1 `import-untyped` error on `ci_workflow.domain.enums`; identical error occurs on the pre-existing `test_scientific_qc_verdict_contract.py` in isolated mode (installed dist lacks `py.typed` — pre-existing condition). With source on the path, the repo-standard resolution: `uv run mypy src/ci_workflow/domain/enums.py tests/contract/test_correction_proposal_contract.py` → **Success: no issues found**.
- `cmp` of the two schema copies → byte-identical.

## 阻碍或缺失环境

无阻碍。在我的 18 个合同测试、包清单测试、Ruff 和 mypy 目标范围检查全部通过之前，没有任何内容被阻塞。3 个失败的合同测试被诊断（见上文）为在我分配的范围之外，属于预先存在的工作树漂移——根据“不扩大范围”的规则，未采取修复行动；已向 Codex 标记以供知晓。

## 重跑请求或下一步

- 无需重跑。下一步是 Codex 验收；worker_02 可以基于此 Schema 构建 `application/correction_service.py`（submit/add_evidence/validate/record_owner_decision/publish 的确定性幂等键在 `publish_idempotency_key` 和 `owner_decision.approval_id` 字段中已有定义），worker_03 可以通过针对 `state` 枚举和已测试的条件规则的 `graph/definitions/correction.py` 来复用这些声明。
- 给 Codex 的一项设计说明，供验收时考虑：Schema 要求从创建时就存在 `publish_idempotency_key`（design.md 在最小合同中列出了它；在提交时确定性地推导它可以保证检查点重放安全）。如果 worker_02 更倾向于仅在发布时派生它，那么只需一行 Schema 修改，移动一个条件语句——在此标记，以免默认决定被默默接受。
