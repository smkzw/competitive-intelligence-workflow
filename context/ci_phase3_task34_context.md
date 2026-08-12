# Task Context: ci_phase3_task34

Created: 2026-08-13 00:12:48
Objective: 按批准计划实现 Task 3.4：以 v1.2 固定迁移表构建应用持有的类型化控制图、完整节点合同、默认执行器和检查点重放幂等，并以 GT01–GT11 精确测试接受
Task type: `finite_code_task`
Risk: `high`
Selected agent route: `opencode-go` / `deepseek-v4-flash` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §6.2、§8.4、§9、§10.1–10.2、附录 E。
- 批准实施计划 Task 3.4（GT01–GT11）；本上下文已逐项固定测试名、文件和退出条件。
- `src/ci_workflow/domain/enums.py` 与 `tests/unit/test_state_enums.py`：九组互不混用的状态类型。
- `src/ci_workflow/storage/event_store.py`：唯一追加式事件真源、事件身份和幂等冲突合同。
- `src/ci_workflow/storage/checkpoint_store.py`：规范检查点、事件前缀验证和崩溃重放合同。
- `src/ci_workflow/ingestion/manual_inbox.py`：已接受下载状态机行为；Task 3.4 的通用迁移表不得与它漂移。
- Task 3.1/3.2/3.3 已接受且不可改写；当前 `main` 锚点为 `9049e4f`。

## Fixed GT01–GT11 Contract

- GT01–GT05 的期望边与守卫必须在测试中以 v1.2 字面 fixture 固定；测试不得从生产 registry/transition map 反向生成期望。
- GT06 遍历九组枚举。后五组运行状态的未声明边写确定性拒绝事件；前四组证据状态不由运行图改写，因此任一状态迁移尝试都拒绝并写事件。跨枚举同值也必须拒绝。
- 项目初始 `None -> running` 是显式创建边；所有表中“任一未完成态”按固定源集合展开，不能用宽松通配符绕过 guard。
- 报告 `scientific_qc` 接受才到 `snapshot_locked`；可修复否决只回 `recovering`，不可修复且恢复穷尽才到 `evidence_blocked`；`snapshot_locked -> superseded` 保留旧版本。
- 格式状态按 `queued -> generating -> quality_check -> passed -> delivery_ready`；格式阻断/重开独立，`delivery_ready -> superseded`。
- 下载状态图必须覆盖 Task 3.3 全链；修订批准必须把验证与用户批准分离，并以批准/发布 ID 幂等。
- 每条接受或拒绝事件保存 family/object、前后状态、trigger、guard evidence、actor、time、idempotency key；内部事件不直接作为用户报告文案。
- 节点合同至少固定：node_id/version、typed inputs/outputs、completion predicate、reads/writes、retry policy、declared errors、idempotency material、side-effect class、report/artifact scope。
- A/B/C 可读同一证据快照/事实/声明，但 gate、候选快照、分析和格式状态键必须按报告隔离；一个报告阻断不得改写另一个报告状态。
- 检查点重放必须证明 publish/move/approve/delete 四类副作用使用稳定幂等键；同事件重放不重复，载荷漂移失败关闭。

## Scope

- In scope: `src/ci_workflow/graph/{__init__,types,state,transitions,guards,registry,reducer,executor}.py`、`src/ci_workflow/graph/definitions/{__init__,new_report}.py`、三份计划测试 `tests/graph/test_transition_matrix.py`、`test_graph_node_contracts.py`、`test_checkpoint_replay.py`。
- In scope: 固定迁移矩阵、守卫求值、声明/非法迁移事件、节点合同 registry、A/B/C 分支隔离、基于既有 EventStore/CheckpointStore 的本地默认执行器、四类副作用幂等协议。
- Out of scope: Task 3.5 部分交付场景编排与 `recovery.py`、Task 3.6 project/fixture CLI、Task 3.7 scientific-QC verifier、报告/格式渲染、LangGraph 适配器、外部联网、用户目录交互优化、安全测试。
- Out of scope: 修改九组枚举、Task 3.1–3.3 规则/证据/补件行为或现有测试以换取通过。

## Success Criteria

- GT01–GT11 每个精确 node 先在缺实现时取得真实 RED，再全部 GREEN；最终三文件命令通过并输出字面 fixture 的 `missing=0 extra=0` 语义。
- 所有声明边有唯一 guard id 和实际守卫；guard 证据缺失、矛盾、跨对象或跨 family 时失败关闭并写拒绝事件。
- 九组枚举的全部未声明笛卡尔积均确定性拒绝；同一次拒绝重放不重复事件，身份相同载荷不同触发 EventConflict。
- 节点合同覆盖 intake/preflight/universe/route、ingest/extract/resolve/gate/recovery、snapshot/QC/analyze/format/acceptance；不能仅保存 node 名。
- GT10 机械证明共享证据、分离 gate/report/artifact 状态；不能靠文档声称隔离。
- GT11 在“副作用成功、检查点未保存”崩溃窗口重放 publish/move/approve/delete，四类各只执行一次；内容漂移拒绝。
- Task 3.4 精确套件、Task 3.1–3.3 回归、全库 pytest、Ruff、strict mypy、包校验和 diff 检查通过；独立审查 P0/P1=0 后才接受。

## Risk Boundaries

- 只写本任务列明的 graph 源文件、三份 graph 测试和 runner 报告；不写真实项目或生产路径。
- 不做安全测试；路径、原子性、非法边拒绝和副作用不重复属于用户功能/恢复合同。
- 默认执行器只编排应用能力，不拥有或复制科学事实；事实、声明、快照继续由既有数据层持有。
- 不引入外部图依赖。附录 E 已完成并冻结当前架构决策：应用持有类型图，本地默认执行器为基线，LangGraph 仅是未来可选适配器。假设未变，本任务不重复外部选型扫描。
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, or malformed probe output must be recorded and followed by one real route attempt. Only a missing executable or explicit invalid/retired/unlisted model may stop before that attempt.

## Loop Log

- 2026-08-13 00:12:48: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-13 00:20: Task 3.3 提交和清理后工作树为 clean；读取 v1.2 固定迁移表、九组枚举、EventStore 与 CheckpointStore，确认当前没有 `graph/` 生产实现或 `tests/graph/`。
- 2026-08-13 00:20: 外部方案决策复用 v1.2 附录 E；本任务不采用新依赖，不重开 LangGraph 选型。
- 2026-08-13 02:37: 同一执行会话完成节点身份、共享事件库原始事件校验与副作用目标一致性修复；Pi/Qwen、Grok Build 原审查会话最终均为 PASS，P0/P1=0。Codex 复跑 GT01–GT11、443 项全库、Ruff、strict mypy 与 wheel 检查后接受，提交 `a978cde`；下一步 Task 3.5。
