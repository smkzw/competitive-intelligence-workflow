# Conference Context: ci-phase8-task85-html-ppt-visual-review

Created: 2026-08-31 11:34:14 CST
Objective: 独立审阅 Task 8.5 A/B/C 单文件 HTML-PPT 当前候选的中文医学经理可读性、康哲母版一致性、图表真实性、页码和离线交互合同，判断是否存在必须在进入 Task 8.6 前关闭的确定性阻断项；不执行 8.6 全页终验。
Task type: `html_ppt_visual_browser`
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

- Linked execution task: `ci-phase8-task85-html-ppt-projections`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `grok-build/grok-4.6`, `cursor/cursor-grok-4.6`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- `output/html-ppt/report-a.html` and `.manifest.json` (20 slides; input SHA-256 `988c1607e08c7f9747a6feb493dcdaf66b6ccd7c26cafefe96e956622196fa1a`).
- `output/html-ppt/report-b.html` and `.manifest.json` (24 slides; input SHA-256 `eeae14ce581aeacc6c098cde5f45571e4d0f88d2cc5877cba5429654448381d1`).
- `output/html-ppt/report-c.html` and `.manifest.json` (18 slides; input SHA-256 `a59d7f88b3d8a2e163422c01f0d0981aa64bf2610cc6bb41852c58e9561ed2e6`).
- `docs/acceptance/runs/8.5/projection-contract.md`, `candidate-inventory.md`, `browser-contract-evidence.md`, and the 1440×900 screenshots in `docs/acceptance/runs/8.5/screenshots/`.
- `contracts/kangzhe/design_specs/ROUTER.md`, `core.md`, `project_profile.md`, `track_htmlppt.md`, `htmlppt_fx.md` are the project-local visual authority.
- `tests/html_ppt/` and the locked input JSON files named by the manifests are deterministic evidence; the report HTML must not be treated as its own scientific source.
- Do not add production paths unless the user explicitly authorized reading them for this task.

## Scope

- In scope: read-only real-browser review of the current single-file A/B/C candidates, including representative screenshots and any additional slide needed to verify a suspected defect; Chinese medical-manager readability; 1280×720 deck behavior in a 1440×900 viewport; Kangzhe master consistency; chart values/labels and disclosure-state semantics; exact page number rendering; offline navigation and presenter-note access.
- Out of scope: editing any artifact; using the user-named Task 8.6 final testers; claiming all-page final visual acceptance; production installation; PDF/PPTX generation; clinical/regulatory sign-off; web research.

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- Report every deterministic blocker with slide id, browser/viewport, observed evidence, and smallest repair. Separate 8.5 blocking defects from 8.6 polish recommendations.

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

- 2026-08-31 11:34:14 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
