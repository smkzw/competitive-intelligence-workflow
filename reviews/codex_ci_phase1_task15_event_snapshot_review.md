# Codex Review: ci_phase1_task15_event_snapshot

Date: 2026-08-11
Delegated-agent outputs: `runs/pi_ci_phase1_task15_event_snapshot.md`, `runs/pi_ci_phase1_task15_event_snapshot_followup.md`

## Verdict

PASS。Task 1.5 可以接受；能力预检、控制图业务状态、来源检索、报告分析与任何报告渲染仍未接受。

## Boundary Check

- 本任务通过全局 Hermes workflow guard 与 conference session runner 初始化、预检和留痕；实际只读验收角色按有限代码路由由 Pi harness 执行，Codex 保留最终接受权。
- 两轮独立验收均为只读；审查前后工作树产品变更集合一致。runner 只增加声明的报告、原始记录和能力健康记录。
- 首选 `Pi/cms-smk/deepseek-v4-flash:max` 的模型目录诊断超时后，runner 按规则仍进行真实调用；该调用返回码为 0 但运行时身份与声明不一致，无法建立可信可恢复验收会话，随后使用已声明的 `Pi/opencode-go/deepseek-v4-flash:max` fallback。
- 修订复核直接恢复同一 `opencode-go` session `019ff0f5-cb8e-7000-b9af-83c470d08999`，没有废弃原会话或另开 reviewer。
- 产品改动仅覆盖 Task 1.5 的事件、检查点、快照、产物清单、五份 schema、相应测试与 Phase 1 边界 ADR；旧工程只读，未做安全测试或提前实现 Task 1.6+。

## Codex Verification

- 精确测试：`3 passed in 0.11s`。
- 全库回归：`121 passed in 5.41s`。
- 产品范围 Ruff：通过；strict mypy：19 个源文件无问题；包校验：`PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4`；`git diff --check` 通过。
- 仓库根 Ruff 曾把 `.trellis/` 与 `.codebuddy/` 上游脚手架纳入产品规则，出现 284 条既有风格告警；定位为检查边界错误后改用冻结的 `src tests` 范围，未批量改写脚手架。
- 直接核对 ADR 0004，确认 SQLite 科学/查询层、JSONL 运行历史和不可变清单职责分离；不存在要求 Task 1.5 将同一清单无条件复制到 SQLite 的合同。
- Codex 根据首轮攻击补上 `ManifestWriteContext`：已接受清单必须与当前写入上下文的项目、合同、报告、截止时点、代码/包、运行及五类快照/覆盖身份逐项一致；缺上下文、旧 run 或旧报告快照均失败关闭。
- 新增崩溃窗口回归：副作用完成后、检查点保存前中断，再重放同一事件；调用方按 `idempotency_key` 去重后业务效果恰好一次。代码没有虚构外部系统与本地检查点的原子事务。

## Delegated-Agent Output Review

首轮独立审查真实攻击了篡改、跳号、尾部截断、跨 run 交错、重复幂等键、旧 run/快照、伪接受、绝对路径、产物篡改和 schema 漂移，结论为无 P0/P1、可接受但有两个 P2 边界。Codex 没有直接降级接受：旧 run/快照问题以写入上下文实现并测试；SQLite/清单双真相风险以 ADR 固定未来服务的同 ID 与摘要互验义务；崩溃窗口以类型合同和恢复测试补齐。原审查者在同一 session 增量复核后再次 PASS，无 P0/P1。

## Residual Risk

- `ManifestWriteContext` 的“当前”身份必须由后续 run service 从项目运行注册表构造，存储层只验证清单与上下文一致；后续应用层不得接受调用方自报的旧 run。
- 未来报告/产物服务若同时写 SQLite 查询索引与规范清单，必须按 ADR 0004 同稳定 ID、同摘要互验，并加入孤儿/漂移失败关闭测试。
- 当前默认确定性执行器是单写入者；若未来引入同项目多进程并发写事件，必须先增加跨进程锁或单写入者队列，不能把读取时失败关闭当作正常并发策略。
