# Conference Context: ci-phase9-task92-incremental-refresh-review

Created: 2026-09-01 02:17:04 CST
Objective: 独立复核 Task 9.2 增量刷新最终实现：重点挑战真实门槛结果绑定、影响报告闭包、独立科学质控、不可变历史、快照中断恢复、站点优先范围与中文用户阻断说明；只审查，不修改文件。
Task type: `complex_delivery_conference`
Risk: `medium`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`general_single_object`) with no sub-venue chair. Its effective `CST` route chain is `codebuddy-cli/deepseek-v4-flash:max -> grok-build/grok-4.6:medium -> cursor/cursor-grok-4.6:medium -> openai-codex/gpt-5.6-luna:max`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-phase9-task92-incremental-refresh`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `zcode/glm-5.3-flash`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §17.2。
- `.trellis/tasks/09-01-phase-9-task-92-incremental-refresh/{prd,design,implement}.md`。
- `src/ci_workflow/{application/refresh_service.py,graph/impact.py,graph/definitions/refresh.py}`。
- `tests/integration/test_incremental_refresh.py` 与命名回归套件。
- `runs/execution/ci-phase9-task92-incremental-refresh/worker_01.md` 至 `worker_03.md`。
- Do not add production paths unless the user explicitly authorized reading them for this task.

## Scope

- In scope: 增量刷新合同、影响闭包、门槛/快照/质控绑定、不可变历史、恢复与站点式 HTML 范围。
- Out of scope: 监测、宿主适配、PDF/PPT 导出、用户可见页面视觉修改。

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.

## Parallel Work Rule

For logic-heavy, rigor-sensitive, or artifact-heavy tasks, each participant independently runs the whole bounded workflow and writes a separate output. Leads compare after all available participant outputs are in or explicitly marked pending.

## Timeout Policy

- Participant soft wait: 60 minutes.
- Large-task participant wait: 120 minutes.
- Chair hard wait: 120 minutes.
- Failure rule: Do not fail a model for slow response alone; fail only on terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no useful progress after the high-budget same-session recovery loop. A catalog/auth/transport health preflight timeout or malformed response is diagnostic and must still allow one live route attempt; explicit user routes also proceed when the catalog is stale or incomplete, while a genuinely missing CLI or native transport boundary may block. If a resumable session exists after a step/size boundary, continue it before fallback; repeated identical output/tool evidence triggers the no-progress breaker.
- Pass/turn boundary: one conference prompt is one conference pass. The
  `--max-turns` value controls internal Agent tool-calling turns and is never
  set to 1 for substantive conference execution; generated participant and
  chair commands use the route budgets recorded by the guard.

## Risk Boundaries

- External Agents are advisory; Codex remains final authority.
- Codex owns visual/browser/PPT/PDF/rendered checks, live authority checks, final clinical/regulatory conclusions, and production writes.
- Do not mark a slow model failed solely due to latency.

## Loop Log

- 2026-09-01 02:17:04 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
- 2026-09-01: 首轮完成，Codex 按异议修订实现并完成扩大回归。
- 2026-09-01: 第二轮沿用同一 CodeBuddy 会话，撤回已修复的核心异议并提出三个补充边界；Codex 已修复并记录 57 项聚焦验收、289 项完整集成验收。
- 2026-09-01: 最终修订完成：科学质控引用核对已锁定证据快照；缺失正文对象失败关闭；质控有效期在接受时核验；每个页面必须显式投影到格式；联合刷新和质控否决/过期已有测试；同一父版本的第二个未完成计划不能占用同一子版本。最终复验为 58 项聚焦验收、290 项完整集成验收、目标 Ruff/mypy 与包完整性全部通过。

## Final Verification Request

请沿用当前会话，仅复核最新工作树而非沿用前一轮行号缓存：

1. 逐项确认前轮 S1、S3、S4、S5、S7 是否已由当前源码和测试闭合。
2. 对 S2 仅判断边界是否明确：影响图完整登记由编排层负责；服务负责图内闭包、相邻层边、每页到格式投影和 HTML-only 校验，不从存储层猜测遗漏关系。
3. 读取执行 metrics/review，确认 58 项聚焦验收、290 项完整集成、Ruff、mypy、包完整性证据已记录。
4. 返回最终 Pass / revise 结论及仍阻断 Task 9.2 收口的真实问题；不要重复已被当前代码修复的旧发现。
