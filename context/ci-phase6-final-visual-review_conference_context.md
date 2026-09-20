# Conference Context: ci-phase6-final-visual-review

Created: 2026-08-30 16:28:55 CST
Objective: 以资深临床试验医学经理视角，对当前B类PNH站点新摘要f094848b的真实截图、响应式搜索、键盘交互和信息呈现进行独立视觉接受审阅
Task type: `visual_delivery_conference`
Risk: `medium`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`visual_single_object`) with no sub-venue chair. Its effective `CST` route chain is `kimi-code/k3-256k:medium -> openai-codex/gpt-5.6-terra:medium`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-phase6-final-render-evidence`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `openai-codex/gpt-5.6-luna`, `grok-build/grok-4.6`, `cursor-cli/cursor-grok-4.6`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- 当前候选报告（只读）：`output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh-interaction-repair-20260830/artifacts/report-b-pnh/`
- 当前候选摘要：`f094848b41cf9c66ae8c3ecfb58e0305d5a531f477e6e6cdaa5e05ea3694060e`
- 视觉计划：`output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh-interaction-repair-20260830/reviews/visual-finalization/visual-plan.json`（规范化摘要 `29d32a55edfd673ba5123dd4fa8a5d35764fd2815132f6b2b4377be87c107e7d`）
- 浏览器实测记录：`output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh-interaction-repair-20260830/reviews/visual-finalization/browser-metrics.json`（文件摘要 `cfe8dc516ff399d888d9d8c1879a63d3b38c2f6fef6f94f95dd7c2a8173ed168`）
- 渲染证据：`output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh-interaction-repair-20260830/reviews/visual-finalization/render-evidence.json`（规范化摘要 `ea91e7f9e0c0a0afa304d2044d8897a98c1f5747b376f10d6696f6429ba85b22`）
- 真实截图目录：`output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh-interaction-repair-20260830/reviews/visual-finalization/screenshots/`（40 张；默认页面覆盖 Chromium/WebKit × 768/1024/1440，另含响应式搜索截图）
- 交互修复验证：`runs/execution/ci-phase6-interaction-repair/worker_03.md`
- 视觉执行复核：`runs/execution/ci-phase6-final-render-evidence/worker_01_followup_01.md`、`worker_02_followup_02.md`、`worker_03_followup_01.md`

## Scope

- 范围内：以不熟悉计算机操作、视觉敏感的资深临床试验医学经理视角，审阅首页、安全性、疗效、安全性－疗效矩阵、基线、试验完成情况等页面的默认信息层级、中文自然度、图表与表格可读性、响应式布局；核验 768/1024/1440 三种视口和 Chromium/WebKit；实际复核菜单展开后的全局搜索、键盘打开证据详情、Escape 关闭搜索等交互。
- 必须重点判断：首页与安全性页的安全性矩阵是否在默认视野中完整可读，是否仍需横向拖动；大量疗效/安全性数值缺失的问题是否在当前候选中表现为不合理空白或误导性展示。
- 范围外：修改任何源代码或候选报告、补充医学证据、重新生成数据、接受 Phase 6、写入正式视觉签收文件。发现问题只记录可复现证据与建议，由 Codex 决定是否修订。

## Success Criteria

- 独立审阅者实际打开截图或报告，而不是仅复述已有测试结论。
- 对七个视觉验收维度分别给出“接受/阻断”，并说明证据：文字、版式与间距、配色、图表、表格、交互、中文原生表达。
- 对 768/1024/1440 的安全性矩阵、响应式搜索和键盘交互给出可核验结论；若阻断，指出页面、视口、引擎和复现路径。
- 明确区分“数据确未公开”“抓取/抽取缺失”“视觉上看似缺失”，不得把空白页面误判为可接受。
- 只读完成，不修改候选报告；Codex 保留最终签收权。

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

- 2026-08-30 16:28:55 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
- 2026-08-30: 第一轮独立审阅对摘要 `f094848b…` 给出阻断：768 表格容器隐藏末列、菜单展开未聚焦搜索、Chromium Escape 可能清空并重开结果。
- 2026-08-30: 三项缺陷已转为 Chromium/WebKit 真实 Playwright 测试，修复后 16/16 通过；新候选位于 `output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh-responsive-visual-evidence-20260830/`，摘要 `f1b37ba4745997df319485fb6e929e24ed1153d0304376f6740c45fda3800381`。
- 新候选视觉策划：`b-pnh-responsive-visual-evidence-20260830/reviews/visual-finalization/visual-plan.json`，规范化摘要 `8b920c69639545a06c2094c56e7b2d6e421ddacdf6eb400ea676b52d7e0e7afa`。
- 新候选浏览器记录：`b-pnh-responsive-visual-evidence-20260830/reviews/visual-finalization/browser-metrics.json`，文件摘要 `9d6cb1c9f06eb8c5c5d79a6395cb6880a4908ef2ba88fd45d9b6e1b60916a6f2`；覆盖 24 路由 × 2 引擎 × 3 宽度共 144 个目标和 150 张截图。
- 新候选渲染证据：`b-pnh-responsive-visual-evidence-20260830/reviews/visual-finalization/render-evidence.json`，文件摘要 `0e11681c5b45febd2328ad299fe35868d6639f9e5c374cf452fbeb31d2348f0d`。
- 第二轮必须在原会商 session 内只读复核新候选，不能把第一轮旧摘要结论直接沿用为新候选结论。
