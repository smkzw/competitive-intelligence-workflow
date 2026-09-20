# Execution Context: ci-r2-r3-html-browser-repair-20260905

Created: 2026-09-05 02:09:03 CST
Objective: 在批准版 v1.3 HTML-only 合同下修复 A/B/C 门户真实浏览器回归：迁移明确过时的 12 页、雷达图和默认展开表格断言，保留并修复真正的临床可读性、证据下钻、键盘操作、图表表格一致性与响应式缺陷；不得触碰真实旧根、外部真实验收项目或排除格式代码。
Task type: `html_ppt_visual_browser`
Risk: `medium`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.
Route schedule: `off_peak`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `zcode/glm-5.3-flash:max -> opencode-go/muse-spark-1.3-contributor:xhigh -> openai-codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `visual_executor` -> `zcode` / `zcode` / `GLM-5.3-Flash`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.3.md` and
  `plans/competitive-intelligence-workflow-roadmap-v1.3.md` are normative.
- Current renderers, `assets/portal/`, `fixtures/catalog.yaml`, and browser tests are
  implementation evidence. Older test names or comments saying 12 pages, radar, or
  default-expanded tables are not authority when they conflict with v1.3.
- The preserved external Task 10.2 real-project roots are read-only historical evidence and
  are outside worker scope. Digest failures there must not be bypassed or rewritten.
- Current RED baseline: the selected HTML browser matrix produced 462 passed / 91 failed.
  Chromium and WebKit 26.5 are installed. The formal deterministic gate independently passed.

## Authorized Worker Changes

- Worker 01 may edit only A renderer/report modules, A browser/acceptance tests, and a shared
  portal file when the A failure cannot be fixed locally. It must not alter B/C semantics.
- Worker 02 may edit only B renderer/report modules, B browser/acceptance tests, and shared
  portal evidence-drawer/chart code required by a demonstrated B failure.
- Worker 03 may edit only C renderer/report modules, C browser/acceptance tests, shared
  chart/evidence-drawer browser tests, and shared portal code required by those failures.
- All workers run focused Chromium and WebKit checks in their isolated copy. They may not edit
  package/catalog digests, real-source acceptance logic, external acceptance projects,
  PDF/HTML-PPT/PPTX code, governance records, or release state.

## Risk Boundaries

- No production writes.
- The forbidden legacy root must not be read, inventoried, resolved, existence-checked, or
  mentioned in commands. Work only in the runner-provided isolated copy of the new repository.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. A 门户：核对 11 页现合同，迁移旧 evidence 第 12 页与默认展开表格断言，修复仍真实存在的分页、中文标签和疗效页面浏览器缺陷；只改 A/共享必要文件。
2. B 门户：诊断并修复气泡图临床数值可见性、数据依据抽屉、键盘/焦点、显式零与缺失、产品筛选和图表表格语义一致性；不得弱化医学语义边界。
3. C 与共享图表层：迁移 C 的旧 12 页合同为批准的 11 页，删除雷达图验收责任，保持表格默认折叠，并修复真实 C 首屏、响应式、证据抽屉和剩余八类 ECharts 同步缺陷。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
