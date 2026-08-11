# Codex Review: ci_phase0_renderer_boundary_review_20260811

Date: 2026-08-11

## Verdict

`PASS WITH TASK 0.3 STILL OPEN`：结构化医学内容、确定性渲染器、跨页可重算语义和独立真实产物验收的职责边界已写入 ADR/Trellis，并经隔离 Luna 检查者在 FAIL→修复→同会话复核后接受。康哲 design_specs 仍不稳定，未复制、未冻结、未进入 Task 0.4。

## Independent Review

- 首选原生 Luna 探测被当前 App 子任务接口明确拒绝；按全局路由合同使用 Codex CLI 兼容模式，不换模型。
- 检查会话：`019fee44-1f71-7820-b0da-b075c930af27`，模型 `gpt-5.6-luna`，effort `max`。
- 首轮 FAIL：
  1. ADR 0002 顶部仍把历史 §§6–9 称为当前决定；
  2. ADR 0004 未明确覆盖跨页可见定量结论的一致性，而 S1 实产物已有 5/9 与 6/9 矛盾。
- 最小修复后，同一会话 PASS；结果保存在 `runs/conference/ci_phase0_renderer_boundary_review_20260811/luna_check.md`。

## Hermes Route Boundary

本次没有派发 Hermes：声明的高风险矛盾复核首选路由是隔离的 Codex Luna；原生接口拒绝该模型后，按既定合同转入同模型 Codex CLI 兼容路径，没有改用 Hermes 或替换模型。守卫初始化产生但未实际派发的其他会商壳已清理。

## Codex Verification

- 直接复核 S1 进程、日志、文件计数、HTML-PPT 源码、浏览器行为和可见字号/逐字稿。
- 直接从 RACI 九行重算运营 A 为 6，与页面 5/9 摘要形成可复现反例。
- `pytest` 6 passed；Ruff passed；mypy passed；`LEGACY_REF_OK`；`uv lock --check` passed；`git diff --check` passed。
- v1.2 批准规格未修改；`contracts/kangzhe` 不存在；上游 design_specs 未修改。

## Boundary Check

- 保留 HTML 门户、原生 PDF、HTML-PPT、PPT Master PPTX 四条原生轨；PPTX 不由确定性渲染器伪造。
- 用户可见语言仍要求中文原生，程序状态、日志标签、提示词片段和无必要英文不进入报告。
- 不新增安全专项工作。
- 本结论不接受 S1 产物，也不代表 Phase 0 完成；Task 0.3 仍等待上游修正和用户精确确认。
