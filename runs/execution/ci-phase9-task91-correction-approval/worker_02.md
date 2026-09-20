# Execution Output: ci-phase9-task91-correction-approval - worker_02

## Boundary And Context Check

- 只读取了初始读集两份文件（execution context、execution plan）及任务合同授权的源真源：`.trellis/tasks/08-31-phase-9-task-91-correction-approval/{prd,design,implement}.md`、`docs/specs/competitive-intelligence-workflow-design-v1.2.md`（§17.1、§10.2 修订审批族相关行，grep 定位）、`migrations/0003/0004/0005/0006/0008`、`src/ci_workflow/graph/{transitions,guards,registry,types,state,reducer,executor}.py`、`src/ci_workflow/storage/{event_store,sqlite,content_store,snapshot_store,migrations,checkpoint_store}.py`、`src/ci_workflow/application/{project_service,run_service,source_research_service}.py`（约定参考）、`src/ci_workflow/domain/{ids,enums,contracts}.py`、`src/ci_workflow/ingestion/manual_inbox.py`（服务先例）、`pyproject.toml`。
- 未读 `.codex/AGENTS.md`、`.hermes/SOUL.md`；未读兄弟 worker 报告；未做会议。
- 未修改任何既有文件（工作区既有脏状态与未跟踪文件全部保持原样）。我新增的文件恰好两个（见下）。
- 执行过程中发现 worker_01（`schemas/correction-proposal.schema.json` + 源码副本 + 合同测试）与 worker_03（`graph/definitions/correction.py` + `tests/integration/test_correction_flow.py`）的产物已在本工作区落地，仅作只读观察用于集成验证，未改动。

## Work Performed

实现分配项：“实现追加式 correction service、事件与幂等发布，复用现有 SQLite/内容摘要约定”。

**新增 `src/ci_workflow/application/correction_service.py`（约 1271 行，含文档）**，要点：

1. **不另造状态机**：五个服务操作（`submit` / `add_evidence` / `validate` / `record_owner_decision` / `publish`）的全部状态迁移经既有 `GraphExecutor.submit(TransitionRequest)` 走 `revision_approval` 族；触发词与守卫 ID 直接取自冻结的 `REVISION_APPROVAL_TRANSITIONS` 声明边（`_revision_edge` 查表），守卫由执行器按 `GUARD_SPECS` 求值并在归约/重放时重求值，伪造迁移失败关闭。
2. **追加式事件真源**：提交/补证据/发布登记/发布失败写业务事件（`correction.proposal.submitted`、`correction.evidence.appended`、`correction.revision.published`、`correction.publish.failed`），运行标识固定 `corrections`；批准复用既有 `revision.approve` 副作用事件与 `IdempotentSideEffects` 审批账本（`state/approvals.jsonl`）。`load()` 从事件流重建建议合同（`_rebuild_from_events`），`correction_proposals` 表仅作当前投影，漂移/滞后自动自愈——覆盖“事件已写、投影未存”的全部崩溃窗口。
3. **幂等**：每个操作以确定性幂等键登记进迁移 0005 的 `idempotency_keys` 追加式账本（本服务为该表首个使用者）：精确重放返回既有结果，同键不同载荷 `CorrectionConflictError` 失败关闭；建议 ID/证据 ID/验证 ID/批准 ID 全部由 `stable_id` 内容寻址派生，重复提交/批准/发布不重复创建版本或产物。发布幂等键为 `correction.publish:{approval_id}`，批准时写入合同。
4. **提交绑定核验**：修订包必须绑定当前项目（事件流项目身份校验）与当前快照（文件字节 SHA-256 复核 → `ReportSnapshotManifest` 校验 → `compute_locked_snapshot` 身份复算 → 必须是该项目该报告的最新快照，过期快照拒绝并给出中文指引）。
5. **发布前置缺一失败关闭**（PRD 验收 4）：批准材料 → 状态必须 `approved`/`published` → 新快照经 `SnapshotStore.lock_report_snapshot` 内容寻址锁定且实质内容（claim_ids/evidence/claim/coverage 快照、数据截止）必须与旧版不同、版本必须更新 → 重建回执逐条校验（artifact_id + 小写 SHA-256）→ 独立质控（verdict_id + verdict_digest SHA-256 + 审阅者）→ 守卫 `g_revision_approved_published` 迁移 → `report_snapshots` 按主键幂等登记新版本（`snapshot_locked`，如 v1→v2，与既有 `source_research_service` 登记约定一致）。任何前置失败：批准状态保留、追加 `correction.publish.failed` 原因事件、不回写旧快照；已登记结果的重放短路返回。
6. **验证与批准分离**（PRD 验收 3）：`validate` 的结果只能是 `needs_evidence`/`rejected`/`validated_pending_user_approval`，无批准路径；`record_owner_decision` 校验 `decided_by == report_owner_id`（提交时登记的所有者）。守卫证据互斥对（如 `decision_approve`/`decision_reject`）由守卫合同强制。
7. 用户可见文案只有自然中文（`state_progress_zh` 状态转译），机器状态仅存于合同字段。

**新增 `tests/integration/test_correction_service.py`**：单顶层测试节点、9 组子用例，覆盖 PRD 验收 1–6 的服务层等价物：提交绑定（重复提交/摘要不符/过期快照/跨项目拒绝）、验证处置与不能批准、补证据回到 submitted 且历史不覆盖、仅所有者可决定与精确重放、发布三前置逐一失败关闭且批准保留、发布登记 v1+v2 并存且旧快照字节不变、重复发布零新增、投影删除后从事件流重建并恢复发布、终态保护与用户可见中文不泄漏内部状态词。

## Artifacts And Evidence

- `src/ci_workflow/application/correction_service.py`（新增，未跟踪）
- `tests/integration/test_correction_service.py`（新增，未跟踪）
- 无其他文件改动；`git status` 显示的既有脏工作区与未跟踪文件未触碰。

## Commands And Observations

- `uv run pytest tests/integration/test_correction_service.py -q` → **1 passed**（两轮修复后：修正了建议 ID 未含快照摘要导致错误摘要声明被既有建议短路、以及 `idempotency_keys` 禁删触发器下重设恢复窗口用例）。
- `uv run pytest tests/integration/test_correction_flow.py tests/contract/test_correction_proposal_contract.py tests/integration/test_correction_service.py -q` → **25 passed**：与 worker_01/worker_03 落地产物同场全绿，三个工作项互不冲突（worker_03 驱动 GraphExecutor 与其 definitions，worker_01 用 jsonschema 自包含校验，均不导入我的服务）。
- `uv run mypy src/ci_workflow/application/correction_service.py tests/integration/test_correction_service.py`（strict）→ **Success: no issues found in 2 source files**。注：`uv run mypy src/` 基线本身有 75 处既有错误，故按“目标范围”执行。
- `uv run ruff check` + `ruff format`（两个新文件）→ **All checks passed**。
- 回归（implement.md 指定范围）：`uv run pytest tests/graph/test_transition_matrix.py tests/graph/test_checkpoint_replay.py tests/integration/test_event_checkpoint_replay.py tests/integration/test_sqlite_migrations.py tests/integration/test_append_only_records.py tests/contract/test_package_manifest.py -q` → **16 passed**（88.9s）。

**观察（证据，非指令）**：worker_01 的导出 schema 与我的服务内部合同存在字段命名/结构差异——schema 用 `report_kind`/`snapshot_content_digest`/`user_reason_zh`/`target{...}` 对象/单条 `validation`（disposition 含 `validated_pending_user_approval`）/`rebuild_receipt.views_rebuilt`，且 `publish_idempotency_key` 在导出包中为必填；我的内部模型用 `report`/`snapshot_sha256`/`rationale_zh`/平铺 target/`validations` 元组（outcome `passed`）/重建回执参数，发布幂等键在批准时写入。两者语义一致但字面不同，宿主桥接摄取（Phase 9.4）时需要一层导出映射或由 Codex 裁决统一命名。schema 要求导出包必带发布幂等键，而服务在批准时才产生它——建议 Codex 指定导出构建方（worker_01）在未批准态的取值约定。

## Blockers Or Missing Environment

- 无阻塞。环境齐备（uv 0.11.7、pytest 9.1.1、mypy strict、ruff 0.16.2）。
- 不确定项（供 Codex 验收裁量）：① 上述 schema/服务字段漂移；② 发布的“独立质控”仅校验结论材料（verdict_id/digest/审阅者），未强制审阅者与批准者不同——守卫合同本身不要求，若需要强独立性约束请明示；③ 发布中断窗口 B（迁移已接受、登记未落库）由幂等登记+重放恢复覆盖，但黑盒测试只能覆盖窗口 A（投影丢失）。

## Rerun Requests Or Next Step

- 无需重跑。Codex 可直接复核两个新文件并运行上述四组命令复现证据。
- 待 Codex 裁决：是否将服务内部合同字段对齐 worker_01 导出 schema（或在服务侧补 `to_package_document()` 导出映射）；该改动若指派，我可在同边界内以最小 diff 完成。
- 按回滚点约定：未接入 CLI 与站点按钮；`tests/integration/test_correction_flow.py`（worker_03 范围）与 schema（worker_01 范围）均未由我改动。
