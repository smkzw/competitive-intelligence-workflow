# Task Context: ci_phase5_a_zero_result_evidence_refresh

Created: 2026-08-28 01:54:02
Objective: 对A类特应性皮炎报告中19个零结果产品逐产品复核药物-适应症-试验身份，并检索登记、主要论文、监管材料、会议或公司披露及批准中文权威来源；保存可追溯检索回执，区分未公开、未找到、访问受限、技术失败、已取得未解析和已解析未投影；不得直接生成报告。
Task type: `competitive_intelligence`
Risk: `high`
Selected agent route: `codex` / `codex-main` / `high`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `fixtures/positive/a-atopic-dermatitis/research-content.json`
- `fixtures/positive/a-atopic-dermatitis/curated-result-evidence.json`
- `.trellis/tasks/08-28-phase-5-report-a-data-matrix-recheck/evidence/zero-result-coverage.md`
- 上述清单引用的 NCBI、ClinicalTrials.gov、同行评议主文与官方监管披露版本。
- Do not add production paths unless the user has explicitly authorized reading them for this task.

## Scope

- In scope: 原 19 个零结果产品的身份、结果来源、精确数值、缺失分类和 A 类候选事实链；首页/安全性页矩阵适配复核。
- Out of scope: B/C 类报告、PDF/PPT、正式入口替换、安全性专项测试。

## Success Criteria

- 每个原零结果产品都有可审计状态，已公开关键结果不得继续以“暂无公开”呈现。
- 所有新增数值均绑定试验、组别、时间点、来源版本和精确定位。
- 首页与安全性页在默认桌面宽度无需横向拖动。
- 所有异常证据缺口关闭且独立科学/视觉复核接受后，才允许生成正式报告。

## Risk Boundaries

- Do not write to production paths until Codex review gate passes and writable paths are explicit.
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, malformed output, or a stale/incomplete catalog must be recorded and followed by one real route attempt. Explicit user-selected routes are not blocked merely because the catalog does not list them; only a missing executable or native transport boundary may stop before that attempt.

## Loop Log

- 2026-08-28 01:54:02: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-28：确认 19 个零结果产品中存在遗漏既往结果试验及错误适应症绑定，不再将“登记未张贴结果”等同于“无公开结果”。
- 2026-08-28：形成 4 个产品的候选事实链，修复 Bempikibart 试验身份；43 项联合回归通过，页面宽度实际验证通过。
- 2026-08-28：关键证据门槛仍未通过，正式报告生成保持关闭。
