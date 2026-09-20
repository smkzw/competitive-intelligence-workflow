Continuation round 2 — verifying Codex's dispositions against the current code. Key new claims to verify: (2) the unique `(project_id, report_kind, report_version)` constraint in `migrations/0003_gates_snapshots.sql`, (5) schema-level QC binding fields, and that repairs don't introduce new failures.

Confirmed: `UNIQUE (project_id, report_kind, report_version)` at `migrations/0003_gates_snapshots.sql:22` — two v2 rows were indeed impossible. My round-1 D2 "duplicate v2 rows" claim is corrected; the residual window now fails closed via IntegrityError. Now verifying the schema changes (Q3 binding fields).

Schema confirmed updated (Q3 binding fields at lines 243-253). Spot-checking the packaged copy, then the contract test updates.

Contract test updated (320-323). Now verifying the publish entry flow ordering (rejection before candidate locking) in current code.

Publish ordering confirmed. One last check — that the integration test's `_publish_materials` fixture was updated with the QC binding fields (else tests would be inconsistent).

QC fixture binds candidate correctly (144-151). One consistency check remains — the new claim-existence check requires `target_id ∈ manifest.claim_ids`, so the v1 fixture's claim_ids must contain the test target ids.

All fixtures are coherent (v1 manifest now carries `_TARGET_ID`). Verification of all eight dispositions is complete. Returning the updated report.

# Conference Participant Output: ci-phase9-task91-correction-approval-review - general_single_object

## Boundary Check

- Read-only continuation round 2, same session. No files modified, no files written (report returned inline; the runner owns the output path).
- Files re-read from the assigned list: `migrations/0003_gates_snapshots.sql` (new), `schemas/correction-proposal.schema.json` (changed), `src/ci_workflow/schemas/correction-proposal.schema.json` (changed), `tests/contract/test_correction_proposal_contract.py` (changed), `tests/integration/test_correction_service.py` (changed fixtures + 3 new tests), `src/ci_workflow/application/correction_service.py` (re-verified all repair regions). `prd.md`, `design.md`, `graph/definitions/correction.py`, `snapshot_store.py`, `test_correction_flow.py`, and the context file were unchanged from round 1 and their earlier reads remain valid.
- Bash remains denied in this session: **I cannot execute pytest/mypy/Ruff**. Codex's runtime evidence (31 Task 9.1 tests, Ruff, target mypy, 16 regression tests) is recorded as Codex/implementer-run evidence, not independently reproduced by me. All repair assessments below are static verification against current code + test code.
- I do not claim final acceptance; Codex owns it.

## Independent Work Product

Updated verdict: **可接受（ACCEPT），无阻断问题**。全部 8 项处置逐一静态核验：7 项成立，1 项（D2）经核对数据库唯一约束后确认比我上一轮报告的更完整——我撤回上一轮"同一版本可登记两行"的残留论断。下列每项均区分 证据 / 推断 / 建议。

### 处置 1（D1 当前版本绑定）— 核验通过 ✅
证据：`correction_service.py:627-631` 按 `snapshot_id != latest_snapshot_id` 拒绝过期包；`_latest_snapshot_id`（634-656）逐行 `ReportSnapshotManifest.model_validate(manifest_json)`（其 `created_at` 经 `snapshot_store.py` 的 `_offset_datetime` 强制带时区偏移），按 manifest 自身 `created_at` 取最大，注册行存 `manifest.created_at.isoformat()`（1316）。测试 `test_current_snapshot_accepts_a_second_correction_after_publish`（test_correction_service.py:282-307）发布 v2 后对新版本提交并断言 SUBMITTED；fixture 自洽（v2 manifest `claim_ids` 含 `_SECOND_TARGET_ID`，新目标存在性检查可通过）。
推断：修复确实关闭了"首次发布后最新版本不可提交"的失败路径。
新增风险检查：`_latest_snapshot_id` 对损坏 manifest_json 失败关闭（652-654）——可接受，无新缺陷。

### 处置 2（D2 发布幂等）— 核验通过，并修正我上一轮论断 ✅（强于预期）
证据：`migrations/0003_gates_snapshots.sql:22` 存在 `UNIQUE (project_id, report_kind, report_version)` —— 我上一轮未读 0003，误报"两个 v2 行可能"；该论断撤回。重复版本 INSERT 在 `_register_new_version`（1319-1322）被 `sqlite3.IntegrityError` 捕获为 `CorrectionPublishError "新版本登记与既有版本冲突"` 并走 `_record_publish_failure` 入账。不同材料的拒绝（1229-1233 `published_version.snapshot_id != candidate.snapshot_id`）位于候选快照锁定（1248-1254）**之前**；测试 `test_published_recovery_rejects_different_materials_for_same_approval`（350-393）monkeypatch `_claim` 后断言拒绝且快照目录无新文件。
残留（LOW，可接受，建议记录）：最窄窗口（INSERT 已提交、published 事件未追加、以**不同**材料重试）中 `published_version` 仍为 None，1229-1233 不触发，候选文件 B 会在 INSERT 冲突前被锁定到磁盘——副作用仅为：一个未登记的内容寻址候选文件（对 `_latest_snapshot_id` 不可见）+ 一条失败事件；无重复版本、无状态损坏、旧版本不动。这是失败关闭的可接受表现。

### 处置 3（D3 add_evidence 恢复）— 核验通过 ✅
证据：`correction_service.py:780-794` 存在恢复路径——证据记录已追加且状态仍为 `needs_evidence` 时重放确定性迁移（`correction-evidence-submit` 与主路径同一 request_id，执行器幂等去重）。测试 `test_add_evidence_retry_recovers_transition_after_interruption`（310-347）monkeypatch `_transition` 抛错后重试，断言回到 `submitted` 且仅一条证据记录。无新缺陷。

### 处置 4（Q2 claim 目标存在性）— 核验通过 ✅
证据：`correction_service.py:710-711` 提交时校验 `target_id in manifest.claim_ids`；v1/v2 测试 fixture 的 claim_ids 已同步（`_prepare_project` 现用 `(_TARGET_ID, "c2")`，v2 用 `[_TARGET_ID, _SECOND_TARGET_ID, "c2-corrected"]`），fixture 与新检查一致。
推断：Codex 关于 fact/chart_point/matrix_cell 无法在提交层校验的理由成立——报告快照清单只枚举 claim_ids，不枚举图点/矩阵单元/事实。这些目标类型继续依赖 validate 步骤的完整核验声明（locator/identity/context/impact）。建议：将"非 claim 目标的存在性校验依赖快照枚举扩展（Phase 9.2+）"记入任务记录。

### 处置 5（Q3 独立质控绑定）— 核验通过 ✅
证据：服务层 `correction_service.py:1198-1199` 要求 `reviewed_snapshot_id` + `reviewed_snapshot_content_digest`，1224-1228 与候选快照身份绑定；1204-1207 校验带时区偏移时间；1202-1203 拒绝 reviewer==报告负责人。Schema（`schemas/correction-proposal.schema.json:234-254`）与打包副本（`src/ci_workflow/schemas/correction-proposal.schema.json:243-252`）均新增并 required 这两个字段；合同测试在 `test_publish_fails_closed_without_prerequisites` 增加缺失字段负例（320-323）；集成 fixture `_publish_materials`（144-151）按候选计算绑定。
残留（LOW）：`rebuilt_artifacts`（artifact_id+sha256）仍为不透明自证，且**不持久化**——published 事件载荷只含 published_version/approval_id/publish_key，schema 的 `rebuild_receipt`（views_rebuilt/rebuilt_at）没有服务侧生产者。即"重建回执"的耐久记录缺失。与处置 6（无导出器）同源，建议记入 9.2/9.4。

### 处置 6（Q1 导出器边界）— 接受 Codex 裁决 ✅
记录：9.1 冻结并校验 schema（合同测试 + 打包副本逐字一致测试仍在）；宿主/站点导出适配器为 Phase 9.4 交付。验收 6 的"自包含修订包通过 schema"在 9.1 由 schema + 合同测试承担。建议在任务记录中显式写明"生产者属 9.4"，避免验收回溯。

### 处置 7（Q4 所有者身份）— 接受 Codex 裁决，附加建议 ✅
记录：仓库无独立报告负责人注册表，9.1 保留显式提供的 owner（first-writer-wins 语义已在前轮描述），身份绑定要求记入 Phase 9.4。附加：Schema 根字段无 `report_owner_id`/`submitted_by`，9.4 若要落地身份绑定需扩 schema（触发 `schema_version` 升版）——建议在 9.4 计划里显式列出。

### 处置 8（Codex 运行时证据）— 记录，非我复现
Codex 报告 31 项 Task 9.1 测试 + Ruff + 目标 mypy + 16 项共享回归通过。静态交叉核对（fixture 与检查一致性、新测试与修复路径一致性）未发现矛盾；但我无法在本会话执行测试，该证据保持"Codex 侧已运行、我侧未复现"状态。

### 挑战性复核（对处置的对抗性检查）
- 对 D1 修复：检查 `_latest_snapshot_id` 是否可能选中"未发布候选"——它只读已登记行（report_snapshots），发布失败的候选文件不可见；无回归。
- 对 D2 修复：检查拒绝是否可能在锁文件之后——1229-1233 在 1248-1254 之前，测试断言目录不变；最窄窗口的杂散文件无害且不进入版本清单；无回归。
- 对 D3 修复：恢复路径与主路径共用 request_id，若执行器已接受则返回既有事件、不再重复保存（`_save` 幂等投影覆盖）；无回归。
- 对 Q3 修复：新增必填字段会使旧版导出的包（无 reviewed_snapshot_*）在 schema 校验下失败——这是期望的收紧；服务与测试 fixture 已同步，无回归。

## Evidence And Assumptions

- 证据：上述全部行引用来自本会话对当前文件的读取；处置 1/3/4/5 与 Codex 描述逐条对应；处置 2 的数据库唯一约束为新增核验依据。
- 推断 vs 证据：所有修复评估为静态结论；D2 最窄窗口的行为（杂散文件 + 失败事件）为推断（该窗口无测试覆盖），但失败关闭方向由唯一约束 + IntegrityError 捕获保证。
- 假设：Codex 运行时证据真实（31+16 测试、Ruff、mypy 通过）；我无法复核。
- 未验证：本会话无任何测试执行；`test_correction_flow.py` 与 `graph/definitions/correction.py` 本轮未变动（与上轮读取一致）。

## Risks, Gaps, And Verification Needs

- 已无阻断风险。剩余均为记录型（LOW）：D2 最窄窗口杂散文件；rebuilt_artifacts 不持久化且 rebuild_receipt 无服务侧生产者；非 claim 目标存在性依赖 9.2 快照枚举；Q4 身份绑定需 9.4 扩 schema。
- 验证需求：Codex 已运行全套测试——建议补一条覆盖"INSERT 已提交、事件未追加、不同材料重试"的最窄窗口测试（monkeypatch `_append_business_event` 对 `correction.revision.published` 抛错），把该窗口从推断变为测试断言（断言失败关闭且目录多出的候选文件不进入版本清单）。此为非阻断建议。
- 工作树 dirty 573 paths：与本次审查无关，提交前由 Codex 确认改动归属。

## Recommended Next Step

1. 接受本轮审查结论：8 项处置全部核验通过，无阻断问题；验收可基于 Codex 已运行的 31+16 测试与上述静态核验进行。
2. 若在 9.1 收口前有余量：补 D2 最窄窗口测试（上述）；否则将其与 rebuilt_artifacts 持久化、非 claim 目标存在性、Q4 身份绑定一并记入 9.2/9.4 任务记录。
3. 在任务记录中显式写入：验收 6 的修订包生产者属 9.4；schema 若在 9.4 增加 owner 字段需升 `schema_version`。
4. 我的结论仍以 Codex 的测试执行为最终验收依据；我不做最终验收声明。
