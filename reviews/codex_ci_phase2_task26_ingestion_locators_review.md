# Codex Review: ci_phase2_task26_ingestion_locators

Date: 2026-08-12
Delegated-agent output: `runs/pi_ci_phase2_task26_ingestion_locators.md`

## Verdict

PASS。Task 2.6 可接受；Task 2.7 与真实 HTML/PDF 抽取质量未提前接受。

## Boundary Check

- 本轮独立验收通过 Hermes 兼容执行会话运行，Codex 保留最终接受权。
- 审查者全程只读，runner 只写报告与原始流。三轮复用同一 OpenCode Go session `019ff1a4-cd94-7000-b9f0-fb96b0772b41`。
- 北京夜间有效路由为 `opencode-go/deepseek-v4-flash:max`；诊断超时后真实路线成功，无 fallback、无因延迟重发。

## Codex Verification

- Codex 与独立审查者分别运行 IF01–IF05 组合 5 项、全库 178 项、Ruff、strict mypy、包校验和差异检查，全部通过。
- 未知分类、孤立补充材料、用户原文件名/规范名/摘要/父子身份、登记数组路径、网页同名标题、PDF 页表行列、跨版本和全部坐标篡改均有机械断言。
- 首轮及补充轮累计 3 个 P2 均转为反例测试并修复；最终原 session 复核 P0/P1/P2=0。
- Codex 真实构建 sdist 与 wheel，并确认三个新增摄取模块都进入 wheel。
- 本任务没有用户界面或格式产物，不适用视觉、浏览器、PPT、PDF 成品验收；测试中的 PDF 是结构定位合同，不冒充真实抽取质量。

## Delegated-Agent Output Review

首轮报告 PASS/P2=2，第二轮因一个残余 P2 正确判 FAIL，第三轮 PASS/P0=P1=P2=0；每个结论都有实测篡改输出。审查者没有提前接受事实层或真实解析器，缺陷分级和范围判断可信。

## Residual Risk

- Task 2.7 必须在事实入口机械要求 locator 可重开且重开原值与片段原文一致，不能仅检查 locator 存在。
- 真实网页标题切分与 PDF 表格识别质量仍需在后续代表性 fixture 和端到端路线中验收。
