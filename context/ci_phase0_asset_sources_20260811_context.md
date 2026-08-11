# Task Context: ci_phase0_asset_sources_20260811

Created: 2026-08-11 08:17:57
Objective: 只读核验 Phase 0 正式 Logo、ECharts 6.1.0 与 HTML-PPT 离线运行时的官方来源、许可证、内容边界和可移植封装方案，不复制或封装受保护资产。
Task type: `code_open_audit`
Risk: `medium`
Selected agent route: `codex` / `codex-main` / `high`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- 已批准实施计划 Task 0.3 与 `docs/decisions/0001-technology-stack.md`、`0002-kangzhe-contract-reconciliation.md`。
- 本机只读候选：`/Users/smkzw/.cc-switch/skills/kangzhe-ppt-design/assets/logo_bot.svg`、`/Users/smkzw/.cc-switch/skills/html-ppt/`。
- Logo 官方地址：`https://web.cms.net.cn/wp-content/themes/qnz/assets/img/logo_bot.svg`，以实时响应和实际 SVG 字节为准。
- ECharts 只采用 Apache ECharts 官方 GitHub 仓库、官方 npm 包元数据与 Apache-2.0 LICENSE；版本固定 6.1.0。
- `html-ppt` 的本机 `SKILL.md`、`LICENSE`、`assets/runtime.js`、`assets/base.css` 和 presenter-mode 指南；只抽取康哲合同允许的运行时能力。

## Scope

- In scope：来源可达性、当前摘要、文件类型、Logo viewBox、许可证、版本、运行时模块依赖、绝对路径/CDN/视觉主题耦合和最小离线文件清单。
- Out of scope：复制或修改康哲主合同；把候选资产写入活动包；报告生成；视觉主题选择；安全专项测试；进入 Task 0.4。

## Success Criteria

- Logo 官网响应与本机缓存逐字节或结构差异得到明确结论；网络失败与内容变化分开记录。
- ECharts 6.1.0 的官方发行物、classic bundle 文件名、许可证和摘要来源可复现。
- HTML-PPT 最小运行时保留/删除能力、依赖文件、许可证和包内相对路径方案明确，不把通用主题或 CDN 带入康哲交付。
- 结论写入新仓决策材料并通过 Codex review gate；未获合同确认前不产生活动资产。

## Risk Boundaries

- 所有外部和本机候选只读；只允许写入新仓 `context/`、`docs/decisions/`、`reviews/`、`metrics/` 与 Trellis 检查点。
- 不采用闭源或来源不明的运行时代码；不把网络可达性等同于内容真实性。
- 不执行安全专项测试；仅验证功能、可移植性、许可证和离线完整性。
- Codex owns verification and acceptance；当前研究不能替代用户对最新康哲合同组合的确认。

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, or malformed probe output must be recorded and followed by one real route attempt. Only a missing executable or explicit invalid/retired/unlisted model may stop before that attempt.

## Loop Log

- 2026-08-11 08:17:57: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-11 08:20: Verified the official CMS Logo twice; official bytes, global Skill cache and current `design_specs` asset all share SHA-256 `8d16d3ae...`.
- 2026-08-11 08:21: Verified ECharts 6.1.0 tag, official npm integrity, Apache-2.0 license and browser classic bundle; selected `dist/echarts.min.js` for later packaging.
- 2026-08-11 08:23: Fully read the upstream HTML-PPT runtime and isolated the Kangzhe-compatible derivative boundary: preserve navigation/presenter, remove themes/demo animation/broken overview, fix per-slide numbering and localize presenter UI.
- 2026-08-11 08:24: Detected a new upstream contract state rather than trusting the previous snapshot: both root contracts are now stubs and `design_specs/` is the single portable authority. Current S1 product validation is still running; local_map L.5 retains an obsolete twin-body rule.
- 2026-08-11 08:27: Wrote ADR 0003 and updated ADR 0002, migration registration and Trellis checkpoint. No candidate asset or upstream contract was copied or modified.
- 2026-08-11 08:28: Initial repository regression exposed unstable migration item-id renaming; retained the historical IDs and changed only their current role/hash/status.
