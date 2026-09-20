# Conference Context: ci-phase8-task86-visual-final

Created: 2026-08-31 13:25:12 CST
Objective: 以真实中文资深医学经理视角审阅 A/B/C 62 页 HTML-PPT 在四视口与双浏览器的最终原图，核对康哲设计规范、中文原生表达、图表与表格可读性、视觉层级、信息密度和跨页一致性；只报告缺陷，不替代 Codex 终验
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

- Linked execution task: `ci-phase8-task86-visual-baseline`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `grok-build/grok-4.6`, `cursor/cursor-grok-4.6`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- Final candidate HTML and locked hashes:
  - `output/html-ppt/report-a.html` — `718705c6d1aa1347907b600e27a9753230f8ad93afb17a0cfa73f44eb164d7a6`
  - `output/html-ppt/report-b.html` — `2bf6a334fd484f1df99bca363f1425503f83e9aa9727a73986a6fcd846c3a406`
  - `output/html-ppt/report-c.html` — `e284dec451cc8355a5ebdd376a903785b3a10e984a9a6bae9bc3c73a61a8f342`
- Full 62-page, four-viewport, two-browser ledger and 496 originals. The final
  collection is split by browser because the combined process terminated after
  336 screenshots without writing a ledger; both browser-specific runs completed:
  - `docs/acceptance/runs/8.6/visual-final-4-chromium/visual-baseline-ledger.md`
  - `docs/acceptance/runs/8.6/visual-final-4-chromium/visual-baseline-ledger.json`
  - `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/` — 248 originals
  - `docs/acceptance/runs/8.6/visual-final-4-webkit/visual-baseline-ledger.md`
  - `docs/acceptance/runs/8.6/visual-final-4-webkit/visual-baseline-ledger.json`
  - `docs/acceptance/runs/8.6/visual-final-4-webkit/screenshots/` — 248 originals
- Project-owned Kangzhe design specification:
  - `contracts/kangzhe/design_specs/project_profile.md`
  - `contracts/kangzhe/design_specs/core.md`
  - `contracts/kangzhe/design_specs/track_htmlppt.md`
  - `contracts/kangzhe/design_specs/htmlppt_fx.md`
- Trellis acceptance contract:
  - `.trellis/tasks/08-31-phase-8-task-86-html-ppt-visual-acceptance/prd.md`
  - `.trellis/tasks/08-31-phase-8-task-86-html-ppt-visual-acceptance/design.md`
- Connectivity evidence: MiniMax and CodeBuddy passed exact title/page recognition;
  Cursor/default failed twice in the same session and is excluded from acceptance voting.

## Scope

- In scope: inspect every Chromium 1920×1080 original at minimum, then use the
  1280×800 and 2048×1024 originals for typography and non-16:9 stress checks;
  inspect WebKit originals where layout differs or the ledger indicates risk.
- In scope: visual hierarchy, typography, spacing, density, native Chinese medical
  language, chart/table legibility, label ownership, page-to-page consistency,
  and whether the deck supports fast medical-manager scanning.
- Out of scope: editing source, changing medical data, security testing, ranking
  products, or treating automatic defect count as final acceptance.

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- The participant records every reviewed page id, browser, viewport, and original
  screenshot path; sampling alone is not a complete pass.
- Any P0/P1 issue includes visible evidence and a bounded repair; a PASS must state
  that all 62 pages were inspected and no P0/P1 remains.

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

- 2026-08-31 13:25:12 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
- 2026-08-31: First conference pass identified chart semantics, heatmap-state,
  endpoint wording, and path-layout issues. Codex repaired the confirmed issues,
  regenerated all three decks, and completed two browser-specific 248-image
  four-viewport collections with zero automatic defect hits. The combined collector
  interruption is retained as technical diagnostic evidence, not treated as a
  content-search or visual failure.
- 2026-08-31: 第二轮会商后修复 A 类临床开发组合页的无意义小数、
  A 类疗效—安全性矩阵标签与横轴刻度邻近问题，并生成 `visual-final-4-*`
  最终原图。Codex 逐页查看 Chromium 1920×1080 的全部 62 页，复核 A13/A14
  在双浏览器四视口下的 16 张原图，并对 9 个高密度或本轮改动页面补看
  Chromium 1280×800、Chromium 2048×1024 与 WebKit 1920×1080。
  最终台账自动缺陷为 0，人工终验未见 P0/P1/P2。
