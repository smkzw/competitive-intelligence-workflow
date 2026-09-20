# Conference Context: ci-phase8-task81-native-pdf-visual-review

Created: 2026-08-31 01:21:05 CST
Objective: 以真实医学经理视角独立审阅 Task 8.1 当前原生 PDF 垂直样例，核对中文原生、信息密度、字体字号、图表与表格可读性、纵横页切换、书签/页码、当前渲染和康哲设计语言；生成者不得自签接受。
Task type: `visual_delivery_conference`
Risk: `medium`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.


## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`visual_single_object`) with no sub-venue chair. Its effective `CST` route chain is `grok-build/grok-4.6:high -> cursor/cursor-grok-4.6:high -> codebuddy-cli/glm-5.3-flash:max -> openai-codex/gpt-5.6-terra:medium`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-phase8-task81-native-pdf-slice`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `cursor/default`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- Candidate and delivery file: `tmp/pdfs/native-pdf-vertical-slice.pdf` and `output/pdf/native-pdf-vertical-slice.pdf`; both must equal SHA-256 `b32d7c390ec3d456a5b47c63f996537c360ce7ac0bb3068784c624ed8e9cbbbe`.
- Current SHA-bound renders: `reviews/ci-phase8-task81-native-pdf-slice/b32d7c390ec3d456a5b47c63f996537c360ce7ac0bb3068784c624ed8e9cbbbe/renders/`.
- Task contract: `.trellis/tasks/08-31-phase-8-task-81-native-pdf-slice/{prd,design,implement,checkpoint}.md`.
- Design authority: `contracts/kangzhe/design_specs/{core,project_profile,track_stream,track_pdf}.md`.
- Structure/text evidence: `tests/renderers/test_pdf_vertical_slice.py`, `tests/acceptance/test_native_pdf_slice.py`, and `fixtures/synthetic/pdf-native-slice/`.
- Do not add production paths unless the user explicitly authorized reading them for this task.

## Scope

- In scope: current four-page PDF only; Chinese-native wording, medical-manager readability, information hierarchy, Kangzhe visual language, chart/table clarity, page orientation, bookmarks/page numbers, native text/vector structure, and fixture identity clarity.
- Out of scope: A/B/C full PDF templates, new clinical claims, external registry research, HTML-PPT/PPTX, security testing, or source-code edits by the reviewer.

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- The pinned tmp/output hashes match; all four SHA-bound pages are freshly rendered and contain no high/critical visual or user-language blocker.

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

- 2026-08-31 01:21:05 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
