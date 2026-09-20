# Conference Context: ci-phase8-task82-final-visual-review

Created: 2026-08-31 03:27:46 CST
Objective: 以资深中国临床医学经理视角，对Task 8.2当前A/B/C三类原生PDF共55页进行独立逐页视觉与科学表达验收审阅，重点核对图表诚实性、中文原生表达、信息密度、跨页连续性、裁切重叠和康哲设计规范一致性；不得修改文件或代替Codex最终验收
Task type: `visual_report_structure`
Risk: `medium`
Conference mode: `parallel`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.


## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`visual_single_object`) with no sub-venue chair. Its effective `CST` route chain is `grok-build/grok-4.6:high -> cursor/cursor-grok-4.6:high -> codebuddy-cli/glm-5.3-flash:max -> openai-codex/gpt-5.6-terra:medium`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-phase8-task82-complete-native-pdf`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `cursor/default`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- Current PDFs and immutable fingerprints:
  - A: `.artifacts/pdf-complete/reports/A/v-fixture-001/report.pdf` — `4c2f5c3268ba25bf357d048b6f198028a64997943e8e04e94f289cf1df6413b5`
  - B: `.artifacts/pdf-complete/reports/B/v-fixture-001/report.pdf` — `b4b3631975a3ee7a626a07dd5db3f21969c4f9f43562b22d145a65908fe2d771`
  - C: `.artifacts/pdf-complete/report-c.pdf` — `e804c44a5a341f028d2b0a64f7a992dd63c73c408e8c69f84fc4515fbc5e35ad`
- Current 144-dpi page renders: `docs/acceptance/runs/8.2/verification/{A,B,C}/renders/page-*.png`.
- Machine verification summary: `docs/acceptance/runs/8.2/verification/summary.json`.
- Project-owned design contract: `contracts/kangzhe/design_specs/core.md`, `track_pdf.md`, and `project_profile.md`.
- Do not add production paths unless the user explicitly authorized reading them for this task.

## Scope

- In scope: all 55 current PDF pages; visual hierarchy, chart honesty, readability, Chinese-native medical expression, whitespace balance, continuation logic, clipping/overlap, and design-contract consistency.
- Out of scope: source edits, new data collection, security testing, HTML/PPT acceptance, and production writes.

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- Every page is explicitly reviewed; each blocker cites report and page; B page 5 single-timepoint semantics and C page 13 sample-size bubble identity are independently checked.

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

- 2026-08-31 03:27:46 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
