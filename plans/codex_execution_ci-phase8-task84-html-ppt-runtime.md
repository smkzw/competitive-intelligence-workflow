# Codex Execution Plan: ci-phase8-task84-html-ppt-runtime

Objective: 完成 Phase 8 Task 8.4：审计并构建独立离线的 1280×720 HTML-PPT 固定运行时，复用 html-ppt 交互能力但锁定项目康哲设计合同，不复用门户/PDF页面，并建立真实浏览器验收证据。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 审计现有 assets/html-ppt 候选与项目 design_specs/htmlppt、html-ppt runtime 的差距，给出并实施最小一致修补。 | `runs/execution/ci-phase8-task84-html-ppt-runtime/worker_01.md` |
| `worker_02` | 完成固定画布、#/N 深链、键盘翻页、页码、进度、N 笔记、S 讲者双窗、计时与离线单页预览的独立运行时合同。 | `runs/execution/ci-phase8-task84-html-ppt-runtime/worker_02.md` |
| `worker_03` | 补齐 Chromium/WebKit 多视口、file:// 零远程依赖、讲者同步及离线 ECharts SVG 的自动化测试和可审计证据。 | `runs/execution/ci-phase8-task84-html-ppt-runtime/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

已完成。详见 `reviews/codex_execution_ci-phase8-task84-html-ppt-runtime_review.md` 和 `docs/acceptance/runs/8.4/verdict.md`。
