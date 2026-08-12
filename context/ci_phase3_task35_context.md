# Task Context: ci_phase3_task35

Created: 2026-08-13 02:41:07
Objective: 按批准计划实现 Task 3.5：A/B/C 报告与 HTML/PDF/HTML-PPT/PPTX 格式独立部分交付、独立阻断、终态区分和显式重新打开恢复
Task type: `finite_code_task`
Risk: `high`
Selected agent route: `opencode-go` / `deepseek-v4-flash` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §3.3、§10.1–10.2、§19.2：部分交付、终态阻断、格式隔离与显式重新打开。
- 批准实施计划 Task 3.5：只新增 `graph/recovery.py` 与两份场景测试。
- 已接受 Task 3.4 提交 `a978cde4ba3193d273c7d6b04de5860e80243277`：固定迁移表、结构化守卫、规范状态、GraphExecutor、检查点与副作用幂等。
- `context/ci_phase3_task34_acceptance_2026-08-13.md`：Task 3.4 已接受边界和移交到 3.5/3.7 的 P2。
- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/{prd.md,implement.md,task.json}`：Phase 3 任务状态。

## Scope

- In scope: `src/ci_workflow/graph/recovery.py`、`tests/graph/test_partial_delivery.py`、`tests/graph/test_partial_delivery_blocked.py`；如公共导出确有必要，可最小更新 `src/ci_workflow/graph/__init__.py`。
- In scope: 从 GraphExecutor 的规范状态机械派生聚合条件，不能让调用者自报“仍在运行/均已就绪”等布尔值；每个报告、每个格式用稳定对象身份独立判断。
- In scope: A 已完成、B 阻断、C 运行中；HTML 已交付、PPTX 因 PPT Master 不可用而阻断；项目仍是 `partially_delivered`，不得误记 complete 或 terminal blocked。
- In scope: 当已有交付、剩余选定对象全部穷尽阻断且无运行对象时，项目进入 `partial_delivery_blocked`；没有交付的终态阻断只能是 `blocked`。
- In scope: 报告阻断不撤销其他报告，格式阻断不撤销已交付格式；改变输出选择必须是新合同版本；阻断态只能通过用户材料、环境/生成器修复或新合同版本显式重新打开。
- In scope: 重放同一协调动作不重复事件；同身份载荷漂移失败关闭。阻断版本保持可审计，不原地伪装为 queued。
- Out of scope: Task 3.6 fixture/project CLI、Task 3.7 科学质控、报告门户/四格式渲染、PPT Master 实际调用、浏览器/PDF/PPT/视觉验收、安全测试。

## Success Criteria

- 两个计划场景测试先在缺实现时真实 RED，再 GREEN；测试通过真实 `GraphExecutor.submit()` 和规范 EventStore/CheckpointStore 驱动，不直接改 state dict。
- 部分交付判断覆盖 selected reports × mandatory HTML × selected optional formats 的完整选择矩阵；不能通过删掉失败对象、忽略 PPTX 或临时改选择获得完成。
- `partially_delivered` 与 `partial_delivery_blocked` 机械区分：前者仍有可继续对象，后者无运行对象且剩余选定对象已终态阻断。
- 显式 reopen 只重开对应失败对象/新版本及其下游；已交付 HTML 仍为 delivery_ready，不回滚、不重复发布。
- Task 3.5 精确套件、Task 3.4 图回归、全库 pytest、Ruff、strict mypy、包校验和 diff 检查通过；独立审查 P0/P1=0 后才接受。

## Risk Boundaries

- 只写本任务明确文件及 runner 记录；不写真实项目/生产路径。
- 不做安全测试；非法状态、幂等与恢复属于用户功能正确性，不是安全扩项。
- `recovery.py` 只编排规范状态，不持有科学事实，不生成用户报告，不在用户界面暴露 `gate`、`signal`、状态枚举等后台语言。
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, or malformed probe output must be recorded and followed by one real route attempt. Only a missing executable or explicit invalid/retired/unlisted model may stop before that attempt.

## Loop Log

- 2026-08-13 02:41:07: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-13 02:42: 完整读取最新全局 `/Users/smkzw/.codex/AGENTS.md` 与项目覆盖规则；全局文件 SHA-256 为 `94503e32ac8bedee377ad013be9c66ea80df9f9cb09bdc4d2b018e4840a2fbd0`，本任务按其执行/会商、长等待、原会话恢复和 Token 节省机制运行。
- 2026-08-13 02:45: 读取批准 Task 3.5、v1.2 部分交付合同和已接受 Task 3.4 状态/守卫；外部方案决策复用 v1.2 附录 E，不增加图框架依赖。
- 2026-08-13 03:00–04:55: Pi/OpenCode Go 同一执行会话实现部分交付协调器并完成三轮定向修复；未 fallback。首轮独立验收发现合同漂移、重开代次、格式阻断版本和报告重绑完整性问题；Grok Build 另发现“首次交付与其余对象同时穷尽”无法从 `running`/`awaiting_user` 到达 `partial_delivery_blocked`。
- 2026-08-13 04:20: 将上述死锁判定为 v1.2 §10.2 状态表勘误：新增 `running`、`awaiting_user` 直接到 `partial_delivery_blocked` 的两条声明边，复用既有机械守卫，不伪造 `partially_delivered` 中间态。
- 2026-08-13 05:00–05:42: Pi/Qwen 与 Grok Build 均沿用原验收会话复核，未 fallback。Pi 独立临时探针结论 `PASS；P0=0；P1=0；P2=2`；Grok 最终补全结论 `PASS；P0=0；P1=0；P2=1`。Grok 未取得修复后 pytest 退出码，此项未作为接受证据。
- 2026-08-13 05:45: Codex 独立复跑图测试 13 项、全库 445 项、Ruff、strict mypy、compileall、wheel 内容和差异检查，全部通过；实现提交 `854aaa14277c8f14c83807b639b9e53274429f8a`。Task 3.5 接受，下一步 Task 3.6。
