所有检查均已通过，worktree 的差异正好是那两个分配的制品。工作已完成——以下是执行报告。

# 执行输出：ci-phase9-task91-correction-approval - worker_03

## 边界与上下文检查

- 已读初始读集两文件（`context/..._execution_context.md`、`plans/codex_execution_....md`）；按 Source of Truth 扩读：`.trellis/tasks/08-31-phase-9-task-91-correction-approval/{prd,design,implement}.md`、`docs/specs/competitive-intelligence-workflow-design-v1.2.md`（§10.2 迁移表、§17.1）、`docs/decisions/0013-site-first-v1-delivery-scope.md`、`migrations/0005_corrections_idempotency.sql`、`src/ci_workflow/graph/{types,state,transitions,guards,registry,reducer,executor,definitions/__init__,definitions/new_report}.py`、`src/ci_workflow/storage/event_store.py`、`src/ci_workflow/domain/{enums,ids}.py`、`tests/graph/{test_transition_matrix,test_checkpoint_replay}.py`。
- 关键现状：六状态修订族（`revision_approval`）的迁移边与守卫已在工作树中冻结（`transitions.py` 的 `REVISION_APPROVAL_TRANSITIONS`、`guards.py` 的 8 个 `g_revision_*`、GT05 字面 fixture），属未提交的用户/Codex 权威改动，全部保留未动。协同工件的 `schemas/correction-proposal.schema.json` 与 `application/correction_service.py` 在本次执行时点尚不存在（worker_01/02 的并行工作项），本任务不依赖、未触碰。
- 仅创建两个授权工件；未修改任何既有文件（`new_report.py`、`guards.py`、`transitions.py` 的 M 状态均为执行前既有脏改动）。

## 已执行工作

按指派工作项 3 完成（TDD 语义上对应 implement.md 的「graph definitions + 集成测试」两步）：

1. **`src/ci_workflow/graph/definitions/correction.py`（新建，196 行）**：修订控制图定义。不声明任何新状态规则，只建立五类服务操作 → 八条已冻结迁移边的唯一绑定（`CorrectionTransitionBinding`：operation/disposition/from/to/trigger/guard_id）：
   - `validate` 三分支（needs_more_evidence / validation_rejected / validation_passed）、`add_evidence`（needs_evidence→submitted）、`record_owner_decision` 三分支（decision_approve/reject/needs_evidence）、`publish`（approved→published）。
   - `submit` 明确为起始状态建立而非迁移边：`INITIAL_STATE` 复用冻结 `FAMILY_DEFAULT_STATES["revision_approval"]="submitted"`（导入时 isinstance 收窄，缺失即 `ValueError` 失败关闭）。
   - 导入期 `_validate_bindings_against_frozen_registry()`：与 `TRANSITION_REGISTRY.declared_edges()` 逐边核对 trigger/guard_id，缺边、漂移、重复绑定、覆盖不全、起始态操作误绑边一律导入即失败关闭——修订服务因此不可能绕开或曲解 v1.2 字面迁移表。
   - `binding_for` / `bindings_for_operation` 未知组合失败关闭；`guard_spec_for` 返回冻结注册表中的同一 `GuardSpec`（引用而非复制守卫规则）。
2. **`tests/integration/test_correction_flow.py`（新建，586 行，6 个顶层测试）**，用真实 `GraphExecutor`+`EventStore` 驱动，证据 fixture 复用 GT05 字面证据（导入 `GT05_VALID_EVIDENCE`/`GT05_REVISION_FIXTURE`，不复制、不从生产反向生成）：
   - 绑定↔v1.2 字面 fixture 逐边相等（missing=0 extra=0）、submit 不绑边、验证/批准守卫分离、发布前置条件由复用守卫声明（`required_true` 三键 + `approval_id`）。
   - 全部 8 条合法迁移经真实执行器接受（三条建议覆盖含补证回环、所有者要求补证、所有者显式拒绝三条路径），接受边集合与绑定集合完全相等，归约状态逐一正确（published/rejected/rejected）。
   - 验证不能批准：验证通过证据驱动批准边 → `guard_failed:missing_evidence:owner_explicit_decision`；无批准方向、矛盾决定标志均拒绝；`submitted/needs_evidence→approved` 未声明直达一律 `undeclared_transition`，拒绝后状态不变。
   - 发布前置条件缺一失败关闭：三前置键逐个缺失（missing_evidence）、显式 False（guard_not_satisfied）、缺批准 ID（missing_evidence:approval_id）、`validated_pending_user_approval→published` 未声明；全部满足才接受，`published` 为终态（published→published 未声明）。
   - 追加式历史：补证回环×2 + 所有者要求补证全程事件流前缀稳定（sequence+digest 不变只增）；验证拒绝保留全部历史，`rejected` 无出边不可复活。
   - 幂等重放与批准 ID 发布：同一发布请求精确重放返回原事件零新增；同 request_id 漂移载荷 → `EventConflictError`；`revision.approve` 副作用经 `IdempotentSideEffects` 按 approval_id 幂等（重放不重复登记、同 ID 不同决定 → `SideEffectConflictError`），规范状态副作用账本按批准 ID 记录。

## 工件与证据

- `src/ci_workflow/graph/definitions/correction.py` — 新建，196 行。
- `tests/integration/test_correction_flow.py` — 新建，586 行。
- 无其他文件被创建或修改；git status 确认仅这两个 `??` 新文件。

## 命令与观察

- `uv run python -m py_compile src/ci_workflow/graph/{guards,transitions,registry,executor}.py` → OK（先前疑似的 guards.py 缩进异常经核查为误读，文件无问题）。
- `uv run pytest tests/integration/test_correction_flow.py -q` → **6 passed in 0.12s**。
- `uv run mypy src/ci_workflow/graph/definitions/correction.py tests/integration/test_correction_flow.py` → **两个新文件 0 错误**（strict 模式；跟随导入报出的 69 个错误全部位于 4 个未触碰的既有依赖文件：`tests/graph/test_transition_matrix.py`、`tests/graph/_qc_authorization_fixture.py`、`tests/integration/test_no_draft_when_blocked.py`、`tests/integration/test_scientific_qc_gate.py`；已单独验证 `test_transition_matrix.py + _qc_authorization_fixture.py` 脱离我的文件独立复现 7 个错误，属工作树既有基线，非本任务引入）。
- `uv run ruff check` + `ruff format --check` 两个新文件 → 全部通过。
- 回归（implement.md 回归步）：`uv run pytest tests/graph tests/integration/test_sqlite_migrations.py tests/integration/test_event_checkpoint_replay.py tests/integration/test_correction_flow.py -q` → **50 passed in 96.48s**（含 GT01–GT06 迁移矩阵冻结、节点合同、检查点/事件重放幂等、SQLite 迁移 0005）。

## 阻碍或缺失环境

- 无阻塞。两点供 Codex 裁量：
  1. **既有基线（观察，非本任务引入）**：上述 4 个测试文件存在 69 个 mypy strict 错误（含工作树未提交的 GT05 扩展部分），与本任务工件无关；是否在 Task 9.1 内修复由 Codex 决定。
  2. **并行协调点（推断）**：worker_02 的 correction service 应通过 `ci_workflow.graph.definitions.correction` 的 `binding_for`/`guard_spec_for` 驱动迁移（不自行写 trigger/guard 字符串）；所有者身份校验（只有报告所有者可提交决定）属服务层职责，图守卫只强制决定证据标志；服务层发布幂等按设计用 `idempotency_keys` 表与图层 `revision.approve` 批准账本（approval_id 键）双重收敛。

## 重新运行请求或下一步

- 可选复跑命令：`uv run pytest tests/integration/test_correction_flow.py -q`、`uv run ruff check src/ci_workflow/graph/definitions/correction.py tests/integration/test_correction_flow.py`、`uv run mypy` 同前（过滤本两文件应为 0 错误）。
- 无需重跑请求。若 Codex 希望，我可在同一会话内：待 worker_02 的 `correction_service.py` 落地后，为本集成测试补一段服务层接线冒烟（不改变现有 6 个测试）；或将本文件中对 GT05 fixture 的导入断言改为本地字面副本（若 Codex 认为集成测试不应耦合单元测试 fixture 模块）。当前实现保持最小一致 diff，等待 Codex 验收。
