# Conference Context: ci-1007-current-navigation-security-v1

Created: 2026-10-08 22:47:14 CST
Objective: 独立挑战已冻结current报告读取与真实事实编辑导航的安全及身份边界，仅单一对象，不代签科学/浏览器/发布
Task type: `C03`
Risk: `high`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`evidence_single_object`) with no sub-venue chair. Its effective `CST` route chain is `codebuddy/codebuddy-cli/deepseek-v4.1-flash:max -> zcode/zcode/glm-5.3-flash:max -> grok/grok-build/grok-4.7:high -> pi/cursor/grok-4.7-high:high -> pi/openai-codex/gpt-6.1-sol:high`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-1007-current-navigation-security-v1`
- Execution evidence status: `no linked execution packet`
- Excluded route identities: none
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. The complete agent/provider/model boundary is retained, and effort differences do not bypass deduplication.

## Source Of Truth

- User 20261008 resumed 1007V1 implementation, English root only. Current tracked baseline e1a0126; dirty owned navigation patch is the frozen object. User five unrelated files are not in scope.
- src/ci_workflow/application/user_fact_edit_server.py SHA a8e1b65c0c905dcf00da8bc00e85c1312a509d064420ba9910134497de62d14a
- src/ci_workflow/renderers/portal/assets/portal.js SHA e2d52a9fe62f9ee388a7800e631d74dc57d4c3fa651b585575c80470e4f4def8
- src/ci_workflow/renderers/portal/assets/report-a.js SHA ed141dfcca54747b56650d9520902339d8cb8ea4ea753329d2ab905c28176fbf
- src/ci_workflow/renderers/portal/assets/evidence-drawer.js SHA a794704e9380b3f44b73b0dd2085c2e0da7dcc5ba8650e249760dcddcd78adcd
- tests/integration/test_1007_current_report_edit_navigation.py SHA 66d72bd61597d5a4d365bc336b8f499279ca5936a9df34262e02112c4c8e0c9d
- Dependencies may be read: application/user_fact_edit.py (lock/current_facts/bound builder); latest_delivery.py and delivered_artifacts.py (committed selector/manifests/_ordinary); renderers/portal/report_b.py (_b_source_view_row); tests/integration/test_w04_user_fact_edit.py (_project); test_1007_real_fact_editor.py and test_1007_historical_save_retry.py. All under src/ci_workflow or tests in this English root.
- PRD/DESIGN/ACCEPTANCE in packets/2026-09-22-sol-delivery describe current facts/source layering; no clinical or visual acceptance is assigned.

## Scope

- In scope: one new GET surface under the existing loopback editor; exact Host/session, manifest-listed web-only resources, current generation, file/hash/symlink validation under existing writer lock; trusted escaped runtime metadata and exact B domain->view identity; shared native edit links; old-version rejection and post-save fresh links; static shares unchanged/read-only.
- Out of scope: arbitrary file serving, original sources/science adoption, new services/frameworks, static share editing, broad redesign, installation/threehosts/24 portals/RC, old Chinese workspace and user dirty files. No writes; return report to runner.
- Optional ONLY bounded regression: .venv/bin/python -m pytest -q tests/integration/test_1007_current_report_edit_navigation.py --tb=short (creates ordinary pytest scratch, no real-project mutation). Existing owner related HTTP/JS/editor/history batch ran 45PASS85.06s, scope only; do not infer browser or independent acceptance from it.

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.

## Conference Pass Rule

This packet uses one serial Codex-led conference object. Each declared role receives one complete prompt and may use multiple internal tool turns. Codex decides whether a same-session follow-up is needed after reviewing the result; follow-ups do not create a new conference or change the route identity.

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

- 2026-10-08 22:47:14 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
