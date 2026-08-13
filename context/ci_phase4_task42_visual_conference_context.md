# Conference Context: ci_phase4_task42_visual

Created: 2026-08-14 01:30:34
Objective: 以真实资深医学经理视角独立试用并审评 Task 4.2 康哲多页面门户壳层
Task type: `html_ppt_visual_browser`
Risk: `high`
Conference mode: `parallel`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- 用户明确指定三条相互独立的视觉试用路线：CodeBuddy CLI `kimi-k2.6`、Pi `cms-router/minimax-m3`、Grok Build `grok-4.6:high`。
- 三条路线均启用各自可用的视觉/浏览器工具，扮演真实资深医学经理；不设置隐式 fallback，不用其他模型冒充指定路线。
- Codex 主会场负责对模型意见做边界裁定、真实截图复看、确定性浏览器回归与最终接受。
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Source Of Truth

- `.trellis/tasks/08-13-phase-4-common-report-portal/prd.md`
- `context/ci_phase4_task42_context.md`
- 项目冻结康哲站点合同与 `.artifacts/task42-portal/current/` 当前站点、六张截图。

## Scope

- In scope：Logo、标题层级、21 页分组导航、搜索、当前态、页面互通、1024 折叠、中文原生、空壳信息节奏。
- Out of scope：Task 4.3 筛选/网址状态、Task 4.4 图表/完整表、Task 4.5 证据抽屉、真实临床数据、PDF/PPT、安全测试。

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

- 2026-08-14 01:30:34: Conference initialized by `hermes_workflow_guard.py init-conference`.
- 2026-08-14 01:31: 三条用户指定路线均先做独立健康检查并启动真实审查。
- 2026-08-14 01:47: CodeBuddy 与 Pi 复用原会话第二轮 PASS；Grok 两次工具边界取消后在同一会话第三轮返回完整 PASS。
