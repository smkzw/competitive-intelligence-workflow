# Conference Context: ci_phase3_task34_acceptance

Created: 2026-08-13 01:24:45
Objective: 独立验收 Task 3.4 类型化控制图是否真实满足 v1.2 与批准计划，重点识别状态、身份、节点合同、跨运行和检查点恢复假绿；只读，不修改文件
Task type: `complex_delivery_conference`
Risk: `high`
Conference mode: `parallel`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

    - Visual/design/HTML/PPT tasks use a Codex-led panel with no sub-venue chair: Pi/Oh My Pi `kimi-code/k3-256k` (high). If unavailable, the runner tries Grok Build `grok-4.6` (high), then the distinct Cursor `cursor-grok-4.6-high` route, then the distinct Pi/OpenCode Go `gpt-5.6-luna` (max) route. The Codex subAgent Luna route remains a separate native/CLI compatibility path.
- Chinese labels or Chinese sentence review is handled directly by Codex and does not start a conference.
    - Other complex tasks use a Codex-chaired panel with no sub-venue chair. Participant 1 is Pi/Alibaba `qwen3.8-max` (xhigh) during the Beijing 22:00-07:00 window. Outside that window its exact Qwen Max node is replaced by Pi/OpenCode Go `deepseek-v4-flash` (max); during the night window, every exact Pi/cms-smk `deepseek-v4-flash` node is replaced by the same Pi/OpenCode Go route. Its remaining fallbacks are Pi/cms-smk `deepseek-v4-flash` (max) and Pi/OpenCode Go `deepseek-v4-flash` (max), with effective-route deduplication. Participant 2 is Grok Build `grok-4.6` (high), with the distinct Cursor `cursor-grok-4.6-high` and Pi/cms-router `minimax-m3` as fallbacks. Codex remains the final authority. The explicit Luna native/CLI compatibility route remains available for execution roles that declare Codex subAgent.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §5.3、§10.1–10.2、附录 E。
- 批准计划 Task 3.4 的精确合同已抄录在主会场计划；计划原文件在工作区外，不授权参与者读取。
- `context/ci_phase3_task34_context.md`：Task 3.4 固定范围和 GT01–GT11 接受条件。
- `src/ci_workflow/graph/`：待验收生产实现；`tests/graph/`：待验收 11 个精确节点。
- `src/ci_workflow/domain/enums.py`、`storage/event_store.py`、`storage/checkpoint_store.py`、`ingestion/manual_inbox.py`：既有应用合同与共存边界。
- 当前代码尚未提交；参与者只能读取与执行临时测试，不读取任何工作者报告或另一参与者输出。

## Scope

- In scope: 状态迁移矩阵、实际当前状态核验、触发与结构化守卫、事件/项目/运行/请求身份、节点合同与完成事件、A/B/C 状态隔离、检查点和 publish/move/approve/delete 幂等、与既有业务事件共存、计划精确节点可执行性。
- In scope: 通过临时目录和只读命令进行对抗探针；区分“测试写了”与“生产合同真实成立”。
- Out of scope: 修改任何文件、Task 3.5 部分交付编排、Task 3.6 CLI/fixture、Task 3.7 科学质控实现、报告门户与视觉、安全测试、联网研究。

## Success Criteria

- 逐条核对 11 个批准 node id、v1.2 字面矩阵和 `missing=0 extra=0`；测试不得从生产表反向生成期望。
- 独立执行精确测试与必要反例，结论按 P0/P1/P2 分级；P0/P1 任一存在即 `FAIL`。
- 验证控制图不能乱序/伪造当前状态、不能跨项目/跨运行污染、同输入输出漂移失败关闭、同事件重放不重复。
- 验证共享 EventStore 中的非图业务事件可共存、未知图事件失败关闭、检查点崩溃窗口四类副作用收敛。
- 判断 NodeContract 与默认执行器是否形成 Task 3.4 要求的最小可用控制图；不得因 Task 3.5/3.6 未实现而误报，但也不得把本应属于 3.4 的本体缺失推后。
- 每名参与者返回 `PASS/FAIL; P0=n; P1=n; P2=n` 与文件/行号/命令证据；不修改文件。

## Parallel Work Rule

For logic-heavy, rigor-sensitive, or artifact-heavy tasks, each participant independently runs the whole bounded workflow and writes a separate output. Leads compare after all available participant outputs are in or explicitly marked pending.

## Timeout Policy

- Participant soft wait: 60 minutes.
- Large-task participant wait: 120 minutes.
- Chair hard wait: 120 minutes.
- Failure rule: Do not fail a model for slow response alone; fail only on terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no useful progress after the high-budget same-session recovery loop. A catalog/auth/transport health preflight timeout or malformed response is diagnostic and must still allow one live route attempt; only a missing CLI or an explicitly invalid, retired, or unlisted model may block before live dispatch. If a resumable session exists after a step/size boundary, continue it before fallback; repeated identical output/tool evidence triggers the no-progress breaker.
- Pass/turn boundary: one conference prompt is one conference pass. The
  `--max-turns` value controls internal Agent tool-calling turns and is never
  set to 1 for substantive conference execution; generated participant and
  chair commands use the route budgets recorded by the guard.

## Risk Boundaries

- External Agents are advisory; Codex remains final authority.
- Codex owns visual/browser/PPT/PDF/rendered checks, live authority checks, final clinical/regulatory conclusions, and production writes.
- Do not mark a slow model failed solely due to latency.

## Loop Log

- 2026-08-13 01:24:45: Conference initialized by `hermes_workflow_guard.py init-conference`.
- 2026-08-13 02:37: Pi/Qwen 与 Grok Build 原会话完成最终修复复核，均为 PASS、P0/P1=0；Codex 完成精确、全库、静态和包检查并接受 Task 3.4。
