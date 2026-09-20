# Codex Execution Plan: ci-r2-r3-html-browser-repair-20260905

Objective: 在批准版 v1.3 HTML-only 合同下修复 A/B/C 门户真实浏览器回归：迁移明确过时的 12 页、雷达图和默认展开表格断言，保留并修复真正的临床可读性、证据下钻、键盘操作、图表表格一致性与响应式缺陷；不得触碰真实旧根、外部真实验收项目或排除格式代码。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | A 门户：核对 11 页现合同，迁移旧 evidence 第 12 页与默认展开表格断言，修复仍真实存在的分页、中文标签和疗效页面浏览器缺陷；只改 A/共享必要文件。 | `runs/execution/ci-r2-r3-html-browser-repair-20260905/worker_01.md` |
| `worker_02` | B 门户：诊断并修复气泡图临床数值可见性、数据依据抽屉、键盘/焦点、显式零与缺失、产品筛选和图表表格语义一致性；不得弱化医学语义边界。 | `runs/execution/ci-r2-r3-html-browser-repair-20260905/worker_02.md` |
| `worker_03` | C 与共享图表层：迁移 C 的旧 12 页合同为批准的 11 页，删除雷达图验收责任，保持表格默认折叠，并修复真实 C 首屏、响应式、证据抽屉和剩余八类 ECharts 同步缺陷。 | `runs/execution/ci-r2-r3-html-browser-repair-20260905/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

Codex will diff each isolated copy against the dispatch baseline, selectively apply only
contract-consistent patches to the primary worktree, rerun the affected Chromium/WebKit suites,
inspect representative rendered pages, run the formal deterministic gate, and keep the external
real-project digest failures open until fresh projects are regenerated. Worker self-reports are
not acceptance.
