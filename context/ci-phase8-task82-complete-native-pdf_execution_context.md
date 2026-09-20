# Execution Context: ci-phase8-task82-complete-native-pdf

Created: 2026-08-31 01:47:21 CST
Objective: 完成 Task 8.2：锁定唯一 three-report-complete A/B/C 基准快照，复用已验证的 ReportLab 原生 PDF 引擎，按 PDF01–PDF09 生成三份完整、高信息密度、可检索、带书签和续表的 A/B/C PDF，并完成覆盖与逐页视觉验收。
Task type: `visual_report_structure`
Risk: `medium`
Execution module trigger: Codex identified 4 independent work items, which is greater than two.
Route schedule: `night`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `cursor/default -> opencode-go/muse-spark-1.2-contributor:xhigh -> codebuddy-cli/glm-5.3-flash:max -> openai-codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `visual_executor` -> `pi` / `cursor` / `default`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- Approved rebuild plan: `/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md`, Phase 8 Task 8.2 / PDF01–PDF09. This is planning input only; this governed packet is the execution authority.
- Active Trellis contract: `.trellis/tasks/08-31-phase-8-task-82-complete-native-pdf/{task.json,prd.md,design.md,implement.md,checkpoint.md}`.
- Project-owned design authority, read in this order: `contracts/kangzhe/design_specs/ROUTER.md`, `contracts/kangzhe/design_specs/core.md`, `contracts/kangzhe/design_specs/project_profile.md`, `contracts/kangzhe/design_specs/track_stream.md`, `contracts/kangzhe/design_specs/track_pdf.md`; brand asset: `contracts/kangzhe/design_specs/assets/logo_bot.svg`.
- Reuse the accepted Task 8.1 native ReportLab implementation under `src/ci_workflow/renderers/pdf_native/` and its tests under `tests/renderers/` and `tests/acceptance/`; do not create a second PDF engine.
- Current A/B/C report projections and portal fixtures under `src/ci_workflow/renderers/portal/`, `src/ci_workflow/reports/`, and `fixtures/positive/` may be read as content-responsibility references. They are not independent cross-format baselines.
- The new `fixtures/synthetic/three-report-complete/` case becomes the sole Task 8.2 cross-format baseline only after its manifest, per-file SHA-256 values, entity counts, coverage set, and current run binding are generated and verified.
- Audience-facing constraints: native searchable/selectable Chinese text, vector charts, bookmarks, page numbers, repeated headers and explicit `续表`; figure before full table; treatment and control arms, denominator, population, timepoint, and disclosure state preserved; missing values display `未公开`; no workflow, prompt, gate, log, snapshot slug, or engineering label in audience text.
- PDF typography floor: body >= 9.5 pt; table/axis labels >= 8.5 pt; references >= 7.5 pt. Full A/B/C reports must be high-density without carrying forward the small-fixture whitespace residual accepted for Task 8.1.

### Authorized Read/Write Paths

- `fixtures/synthetic/three-report-complete/`
- `fixtures/catalog.yaml`
- `src/ci_workflow/renderers/pdf_native/`
- `src/ci_workflow/renderers/pdf/`
- `tests/pdf/`
- `tests/integration/test_fixture_case_contracts.py`
- `schemas/fixture-case.schema.json`
- `src/ci_workflow/application/fixture_runner.py`
- `src/ci_workflow/application/run_service.py`
- `src/ci_workflow/cli.py`
- `tools/verify_pdf.py`
- `.artifacts/pdf-complete/`
- `docs/acceptance/runs/8.2/`
- `tmp/pdfs/`
- `output/pdf/`

Workers may read the source-of-truth and reference paths listed above, but may write only the authorized read/write paths. Preserve unrelated user changes. Do not add production paths or install dependencies. The application/schema paths are authorized only for the smallest coherent multi-report/native-PDF registration and current run-manifest binding needed by the exact Task 8.2 fixture contract; do not broaden CLI behavior beyond this case contract. Worker 04 is verification-focused: it may add the shared verification utility and tests, but must not silently rewrite report content to make checks pass.

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 建立并锁定 three-report-complete 基准 fixture、逐文件摘要、实体计数、GateSpec 预期和当次 run/manifest 绑定；先完成精确 RED/GREEN。
2. 实现 A/B 原生 PDF 投影：A 类完整 profile、疗效、安全性和矩阵；B 类疗效、纵向、安全性、矩阵、基线、完成处置与试验档案。
3. 实现 C 原生 PDF 投影：设计图谱、人群、入排、干预、终点/时间/访视/统计、逐试验详情、模式与多路径。
4. 实现共享原生图表、表格、书签与 coverage projection，对三份当前 PDF 运行 pypdf/pdftotext/pdftoppm 全页验证并只报告缺陷。

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
