# Task Context: ci_phase1_task16_capability_preflight

Created: 2026-08-11 21:29:21
Objective: 实现用户选择驱动的能力预检、选择性阻断与恢复重排
Task type: `finite_code_task`
Risk: `medium`
Selected agent route: `cms-smk` / `deepseek-v4-flash` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §§6.2、6.3、10.1。
- `/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 1.6 CP01–CP08。
- `docs/decisions/0004-phase-1-contract-boundaries.md`。
- 已接受的项目合同、可移动项目服务、包清单、康哲四格式合同和 Task 1.5 恢复边界。

## Scope

- In scope: 选择驱动的类型化能力矩阵、基础文件/脚本、来源网络/浏览器、文档/OCR、HTML 浏览器、PDF、HTML-PPT、PPTX/Office 适用性检查；项目合同/内联两入口；选择性阻断；环境修复后的局部下游重排；中文用户指引。
- Out of scope: 完整项目控制图、重试/路由诊断、来源检索、证据门槛、报告生成、真实格式验收和任何安全测试。

## Success Criteria

- CP01–CP08 每个精确 node 均先 `1 failed` 后 `1 passed`；整套能力合同通过。
- 未选择的来源/文档/OCR/格式能力为 `not_applicable`，不得阻断；缺 PPT Master/Office 只阻断 PPTX。
- HTML 默认包含；A/B/C × 所选格式均有明确 ready/blocked 结果；阻断说明使用简洁中文，说明影响与用户下一步。
- 项目合同与内联选择产生相同能力摘要；真实 `local` 全矩阵预检写出 schema 合法 JSON。
- 能力修复只重排此前失败能力及已经解除全部阻断的下游节点；仍有其他阻断时不提前重排。
- 精确测试、全库回归、Ruff、strict mypy、包校验和独立可执行审查通过。

## Risk Boundaries

- 只写当前新架构仓库和 pytest/`.artifacts` 临时文件；旧工程与外部项目只读。
- 不做重型格式生成或安全扫描；实机预检只验证能力可用性。
- 独立审查者只读；Codex 负责最终接受。

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, or malformed probe output must be recorded and followed by one real route attempt. Only a missing executable or explicit invalid/retired/unlisted model may stop before that attempt.

## Loop Log

- 2026-08-11 21:29:21: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- CP01–CP08 分别取得预期 `1 failed`（目标模块不存在），实现后分别 `1 passed`。
- 整套能力测试 `11 passed`，全库 `132 passed`；Ruff、strict mypy、包校验通过。
- 真实运行 `local` + A/B/C + HTML/PDF/HTML-PPT/PPTX，结果全部可用并写入 `.artifacts/preflight-final.json`；没有静默忽略的技术阻断。
- 独立首轮与同 session 修订复核均 PASS，无 P0/P1。按审查实测补充：网络预检三次短退避后才阻断；LibreOffice/soffice 不再自动冒充目标 Office；最终网络阻断消息明确告知已连续尝试 3 次。
- 实机最终口径：本次适用的 10 项能力全部 ready；登录浏览器和 OCR 因未选择准确为 not_applicable，不得表述为 12 项全部 ready。
