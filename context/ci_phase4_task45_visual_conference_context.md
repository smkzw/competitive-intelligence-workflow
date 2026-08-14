# Conference Context: ci_phase4_task45_visual

Created: 2026-08-14 11:02:57
Objective: 以真实资深医学经理角色独立试用 Task 4.5 数据依据面板、固定对照和交互闭环
Task type: `visual_delivery_conference`
Risk: `high`
Conference mode: `parallel`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

    - Visual/design/HTML/PPT tasks use a Codex-led panel with no sub-venue chair: Pi/Oh My Pi `kimi-code/k3-256k` (high). If unavailable, the runner tries Grok Build `grok-4.6` (high), then the distinct Cursor `cursor-grok-4.6-high` route, then the distinct Pi/OpenCode Go `gpt-5.6-luna` (max) route. The Codex subAgent Luna route remains a separate native/CLI compatibility path.
- Chinese labels or Chinese sentence review is handled directly by Codex and does not start a conference.
    - Other complex tasks use a Codex-chaired panel with no sub-venue chair. Participant 1 is Pi/Alibaba `qwen3.8-max` (xhigh) -> Pi/OpenCode Go `deepseek-v4-flash` (max) during the Beijing 22:00-07:00 window; daytime is Pi/CMS-SMK `deepseek-v4-flash` (max) -> Pi/OpenCode Go `deepseek-v4-flash` (max). Participant 2 is Grok Build `grok-4.6` (high), with the distinct Cursor `cursor-grok-4.6-high` and Pi/cms-router `minimax-m3` as fallbacks. Codex remains the final authority. The explicit Luna native/CLI compatibility route remains available for execution roles that declare Codex subAgent.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Source Of Truth

- 设计合同：`docs/specs/competitive-intelligence-workflow-design-v1.2.md` §15.4–15.6。
- 实施合同：`../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 4.5。
- Trellis：`.trellis/tasks/08-13-phase-4-common-report-portal/{prd.md,task.json}`。
- 本次待审站点：`http://127.0.0.1:8765/efficacy.html`、`baseline.html`、`disposition.html`。
- 待审站点落盘：`.artifacts/task45-evidence-drawer/current/review-site/`；8 张初始截图在同层 `screenshots/`，截图不能替代亲自操作。
- 已有确定性锚点：292 项联合聚焦、931 项全库、152 项最新 Task 4.5/合同、Ruff、strict mypy、资产镜像/manifest、包 API 烟测均通过。

## Scope

- In scope：以不熟悉计算机和 AI、视觉敏感、懒于学习复杂操作的中国资深临床试验医学经理身份，真实浏览三页并操作图点、热图/状态矩阵、表格数据单元、固定对照、筛选、网址刷新/复制/前进后退、Esc/焦点；评价信息查找速度、中文自然度、视觉层级、数据可核对性和异常反馈。
- 每位审评者必须在 1280×900 与 1024×768 至少各完成一次真实页面操作，保存自己生成的原分辨率截图与简短操作轨迹到 `runs/conference/ci_phase4_task45_visual/<role>_evidence/`。
- Out of scope：修改源码、A/B/C 完整业务页面、PDF/PPT、真实临床结论、安全测试、生产路径或远程发布。

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- 每路必须明确 PASS / REVISE / BLOCK，并按 P0/P1/P2 列出可复现问题；不能只说“页面能显示/流程跑通”。
- 至少覆盖：一眼找到入口；图/热图/表格打开同条数据；固定两条后比较定义/时间点/分母/冲突；未公开/不适用/技术暂不可用的理解；1024 宽可读性；Esc 返回；网址刷新与前进后退；筛选后不错误保留或扩大范围。

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

- 2026-08-14 11:02:57: Conference initialized by `hermes_workflow_guard.py init-conference`.
- 2026-08-14 11:06: Codex 生成最新 review-site 并启动本地只读 HTTP 服务 127.0.0.1:8765；三条用户显式视觉路线均要求 health-check 后真实尝试，不使用默认日夜替换或隐式 fallback。
- 2026-08-14 12:20: 首轮三路均生成真实截图并给出 REVISE；Codex 接受其共同指出的临床语义和图表一致性缺陷，未接受 Phase 6 范围外扩。
- 2026-08-14 13:50: R2 同会话复核确认首批硬伤消失，同时发现筛选图形残留、口径提示与移除说明假绿；MiniMax 输出截断，保留原会话待恢复。
- 2026-08-14 14:55: R3 站点 `127.0.0.1:8767`；三路在原会话完成 1280×900、1024×768 实际操作并一致 PASS。MiniMax 在原会话恢复完整报告；无 fallback。
- 2026-08-14 15:05: Codex 独立查看 R3 口径提示、筛选说明和 1024 连续点图截图；会议接受。
