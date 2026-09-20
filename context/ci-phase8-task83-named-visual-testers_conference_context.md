# Conference Context: ci-phase8-task83-named-visual-testers

Created: 2026-08-31 08:21:54 CST
Objective: 由三名用户点名的独立真实医学经理逐页审阅 Task 8.3 三份锁定 PDF 的 54 张当前页图及标准阅读器可读性证据，识别裁切、重叠、黑块、乱码、不可读图表、页眉页脚、页码、续表表头和中文原生表达问题；只读，不修改锁定 PDF。
Task type: `visual_delivery_conference`
Risk: `medium`
Conference mode: `parallel`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.


## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`visual_single_object`) with no sub-venue chair. Its effective `CST` route chain is `kimi-code/k3-256k:medium -> openai-codex/gpt-5.6-terra:medium`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-phase8-task83-pdf-reader-acceptance`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `openai-codex/gpt-5.6-luna`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- 锁定 PDF：`output/pdf/A类-特应性皮炎竞品全景.pdf`、`output/pdf/B类-特应性皮炎临床试验结果比较.pdf`、`output/pdf/C类-特应性皮炎临床试验设计比较.pdf`。
- 当前验收证据：`docs/acceptance/runs/8.3/verification/`，包括 A10、B24、C20 共 54 张原始页图、逐页文本、结构报告、缺陷清单与 contact sheet。
- 设计合同：`contracts/kangzhe/design_specs/core.md`、`project_profile.md`、`track_stream.md`、`track_pdf.md`。
- Task 8.3 产品边界：`.trellis/tasks/08-31-phase-8-task-83-pdf-reader-acceptance/prd.md` 与 `design.md`。
- Do not add production paths unless the user explicitly authorized reading them for this task.

## Scope

- In scope: 逐页确认裁切、重叠、黑块、乱码、文字与图表可读性、页码、页眉页脚、续表表头、中文原生表达，以及检索/书签/方向等标准阅读器证据是否充分。
- Out of scope: 修改三份锁定 PDF、重做医学内容、重新评价 Task 8.2 已锁定的数值披露状态、联网搜索或安全测试。

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

- 2026-08-31 08:21:54 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
