# Task Context: ci_phase1_task15_event_snapshot

Created: 2026-08-11 20:50:03
Objective: 实现规范事件、检查点、幂等恢复、不可变快照与附录C产物清单合同
Task type: `finite_code_task`
Risk: `medium`
Selected agent route: `cms-smk` / `deepseek-v4-flash` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §§3.2、6.2、7、8.1、15.2、附录 C。
- `/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 1.5。
- `docs/decisions/0004-phase-1-contract-boundaries.md`。
- Task 1.1–1.4 已接受的项目合同、相对路径、SQLite 真源、内容寻址来源与证据片段身份。

## Scope

- In scope: 规范事件 JSONL、项目内检查点、事件幂等重放、不可变证据/报告快照、附录 C 产物清单及其 schema/Pydantic 双合同。
- Out of scope: Task 1.6 能力预检、工作流完整状态图、检索/分析/报告生成、LangGraph 适配器、任何安全测试。

## Success Criteria

- 事件只追加，顺序稳定；同一幂等键同一载荷不重复写入或重复副作用，不同载荷冲突失败关闭。
- 删除任何宿主/框架私有缓存后，仅凭项目 `events/events.jsonl` 与 `state/checkpoints/*.json` 可恢复相同状态。
- 检查点绑定已应用事件、状态摘要和项目/run 身份；篡改、跳号或不匹配不得恢复。
- 证据与报告快照以规范 JSON 摘要锁定；相同内容身份稳定，不同内容新建版本，旧快照不覆盖，读回复核摘要。
- artifact manifest 包含实施计划列出的附录 C 全部字段；任一缺失、旧 run/快照/摘要、伪 accepted 或绝对路径均失败关闭。
- 精确测试、Phase 1 当前回归、Ruff、strict mypy、包校验和独立可执行审查通过。

## Risk Boundaries

- 只写当前新架构仓库与 pytest 临时项目；旧工程只读。
- 不采用 LangGraph 或任何新依赖；框架私有缓存不进入规范恢复链。
- 不新增安全测试，不实现 Task 1.6+。
- 独立审查者只读；Codex 保留最终接受权。

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, or malformed probe output must be recorded and followed by one real route attempt. Only a missing executable or explicit invalid/retired/unlisted model may stop before that attempt.

## Loop Log

- 2026-08-11 20:50:03: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-11 21:00:35: Task 1.5 精确测试 3 passed、全库 121 passed；产品范围 Ruff、strict mypy、包校验和 Trellis 校验通过。仓库根 Ruff 额外纳入 `.trellis/` 与 `.codebuddy/` 上游脚手架并报告 284 条既有风格告警，已诊断为检查边界错误，未批量改写脚手架。
- 2026-08-11 21:27: 独立首轮与同 session 修订复核均 PASS，无 P0/P1。已补 `ManifestWriteContext` 关闭旧 run/旧快照接受路径，补崩溃窗口幂等恢复测试，并在 ADR 0004 固定 SQLite 查询索引与不可变规范清单的同 ID/摘要互验义务。
- 后续挂账：run service 必须从项目运行注册表生成当前写入上下文；若未来允许同项目多进程事件写入，必须先引入单写入者队列或跨进程锁。
