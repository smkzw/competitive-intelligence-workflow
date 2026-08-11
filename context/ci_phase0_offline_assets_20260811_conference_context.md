# Conference Context: ci_phase0_offline_assets_20260811

Created: 2026-08-11 14:52:05
Objective: 独立只读验收离线 Logo、ECharts 6.1.0 与中文 HTML-PPT 固定运行时，主动验证来源、离线性、跨浏览器行为和假绿边界
Task type: `high_risk_contradiction_review`
Risk: `high`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

    - Visual/design/HTML/PPT tasks use a Codex-led panel with no sub-venue chair: Pi/Oh My Pi `kimi-code/k3-256k` (high). If unavailable, the runner tries Grok Build `grok-4.5`, then Cursor CLI `cursor-grok-4.5-high`, then Pi/OpenCode Go `gpt-5.6-luna` (max), then Pi/Kimi `k3-256k` (high).
- Chinese labels or Chinese sentence review is handled directly by Codex and does not start a conference.
    - Other complex tasks use a Codex-chaired panel with no sub-venue chair. Participant 1 is Pi/Alibaba `qwen3.8-max` (xhigh) during the Beijing 22:00-07:00 window, and outside that window its exact Qwen Max node is replaced by Pi/cms-smk `cms-model` (high); its remaining fallbacks are Pi/cms-smk `cms-model` (high), Pi/cms-smk `deepseek-v4-flash` (max), Pi/OpenCode Go `deepseek-v4-flash` (max), and Pi/DeepSeek `deepseek-v4-flash` (max). Participant 2 is Grok Build `grok-4.5`, with Cursor CLI `cursor-grok-4.5-high` and Pi/cms-router `minimax-m3` as fallbacks. Codex remains the final authority. The explicit Luna native/CLI compatibility route remains available for execution roles that declare Codex subAgent.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Source Of Truth

- 已批准实施计划 Task 0.3：`../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md`
- 产品规格：`docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- 决策记录：`docs/decisions/0003-offline-presentation-assets.md`
- 项目设计合同：`contracts/kangzhe/manifest.json`、`contracts/kangzhe/design.md`、`contracts/kangzhe/design_specs/**`
- 离线资产：`assets/brand/**`、`assets/third-party/echarts/**`、`assets/html-ppt/**`
- 机械验收：`tests/contract/test_offline_assets.py`、`tests/acceptance/test_html_ppt_runtime_smoke.py`、`tests/fixtures/html-ppt-runtime/index.html`、`tests/fixtures/offline-echarts/index.html`
- 当前实现者验证锚点：专项 43 passed；仓内全量 49 passed；Ruff、mypy、uv lock/sync 和旧依赖扫描通过。以上只是待独立复核的生产者声明。

## Scope

- 范围内：逐字节摘要与许可、manifest 是否形成闭合来源链、离线 ECharts SVG 真实加载、HTML-PPT 固定画布/翻页/页码/深链/预览/逐字稿/演讲者视图/计时/双窗同步、中文原生界面、测试假绿和真实浏览器差异。
- 范围外：A/B/C 报告内容或页面实现、PPTX/PDF、通用设计规范修改、网络检索、安全专项测试、Task 0.4。

## Success Criteria

- 两名独立参与者分别返回可审计结论或明确的终态故障；不得读取对方输出。
- 每名参与者至少亲自重跑静态合同与一条真实浏览器路径，并主动构造或论证一个假绿变异；只读、不改项目文件。
- 对来源摘要、许可、离线网络、中文界面、固定画布和演讲者功能给出逐项结论；发现 P0/P1 时 Task 0.3 不得接受。
- Codex 复核发现、重跑决定性检查并打开真实截图；参与者不代替最终接受。

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

- 2026-08-11 14:52:05: Conference initialized by `hermes_workflow_guard.py init-conference`.
- 2026-08-11: Pi live route 在健康探测超时后成功；初审发现 Logo source 悬空 P1。
- 2026-08-11: Grok 两次因 `plan` 权限模式在工具前取消；保持同 session 改为自动批准只读命令后完成，独立发现相同 P1。
- 2026-08-11: Codex 以 RED→GREEN 修复 source 路径与合同；两名参与者在各自原 session 负向复验均 PASS（P0=0、P1=0）。
- 2026-08-11: Codex 复跑 43 项专项、49 项全量、Ruff、mypy、uv lock/sync、Node 语法与旧依赖扫描并人工查看三张真实截图；Task 0.3 接受，未接受报告实产物。
