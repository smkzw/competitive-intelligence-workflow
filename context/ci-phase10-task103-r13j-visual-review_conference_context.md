# Conference Context: ci-phase10-task103-r13j-visual-review

Created: 2026-09-02 05:56:35 CST
Objective: 从资深中文临床试验医学经理视角，使用 ego(lite) 真实浏览 Task 10.3 R13j A/B/C 站点，独立审评交互、横向比较、设计细节、中文表达、默认视野可读性与康哲设计一致性；只验收 HTML，不涉及 PDF/PPT。
Task type: `visual_delivery_conference`
Risk: `medium`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`visual_single_object`) with no sub-venue chair. Its effective `CST` route chain is `google-antigravity/gemini-3.7-flash:high -> kimi-code/kimi-for-coding:high -> openai-codex/gpt-5.6-terra:medium`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-phase10-task103-html-host-full-matrix`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `zcode/glm-5.3-flash`, `openai-codex/gpt-5.6-luna`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- `.trellis/tasks/09-01-phase-10-task-103-html-host-full-matrix/{prd,design,implement}.md`
- `contracts/kangzhe/design_specs/project_profile.md`
- `docs/decisions/0012-pre-delivery-visual-finalization-loop.md`
- `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.3-20260902-r13j/project/reports/A/v-fixture-001/html/`
- `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.3-20260902-r13j/project/reports/B/v-fixture-001/html/`
- `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.3-20260902-r13j/project/reports/C/v-fixture-001/html/`
- `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.3-20260902-r13j/ego-a-overview.png`
- `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.3-20260902-r13j/ego-b-overview.png`
- `/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.3-20260902-r13j/ego-c-design-map.png`
- `http://127.0.0.1:8783/reports/A/v-fixture-001/html/overview.html`
- `http://127.0.0.1:8783/reports/B/v-fixture-001/html/overview.html`
- `http://127.0.0.1:8783/reports/C/v-fixture-001/html/overview.html`
- 上述隔离验收目录已获授权只读；不得扩展到生产目录。

## Scope

- In scope：仅使用 ego(lite) 浏览 A/B/C 当前站点；在 1024/1280/1440/1920 宽度审查默认视野、图表、表格、筛选和下钻。重点核对 A 气泡图产品洞察，B 模糊匹配后的真正横向图表、基线和试验完成情况，C 全设计字段横向矩阵与研究详情。
- In scope：检查中文原生表达、康哲视觉规范、信息密度、图表先于表格、整页与关键矩阵无需横向拖动，以及未公开状态是否科学清晰。
- Out of scope：任何写操作、来源科学事实重新检索、PDF/HTML-PPT/PPTX、安全专项测试、旧工程迁移或删除。

## Success Criteria

- 必须实际启用 ego(lite)；不得使用 Playwright、Chrome 控制、WebKit、Selenium 或其他浏览器替代。若 ego(lite) 不可用，明确阻断，不得从源码推断视觉通过。
- 以真实医学经理使用路径完成 A/B/C 代表性页面和交互，不把“页面可加载”当作产品验收。
- 分别给出 A/B/C 的 P0/P1/P2 用户可见缺陷、证据和通过/否决建议；无问题也需列出实际查看页面和交互。
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

- 2026-09-02 05:56:35 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
