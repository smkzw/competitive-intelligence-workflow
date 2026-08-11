# Codex Review: ci_phase2_task24_foreign_connectors

Date: 2026-08-11
Delegated-agent output: `runs/pi_ci_phase2_task24_foreign_connectors.md`

## Verdict

PASS。Task 2.4 可接受；Task 2.5 中国连接器及 Phase 2 真实编排未提前接受。

## Boundary Check

- Hermes reviewer 全程只读，runner 只写其报告与原始流。首轮与补充轮使用同一 OpenCode Go session `019ff176-4098-7000-a137-78698e26dd5b`。
- 夜间有效路由为 `opencode-go/deepseek-v4-flash:max`。模型目录健康检查 90 秒超时后按全局合同进行一次真实路线尝试并成功建立该 session；无 fallback、无因延迟重发。补充复核直接恢复同一 session。

## Codex Verification

- Codex 与 reviewer 分别运行 FG01–FG07 组合 7 项、全库 166 项、Ruff、strict mypy、包校验与差异检查，全部通过。
- Codex 实时诊断确认 ClinicalTrials.gov 两页非空且分页身份不同、PubMed NCT 检索非空并由项目解析器只返回请求的 5 个文章 PMID、FDA 指南页含草案/定稿、状态、发布日期和 docket 字段。实时诊断与离线测试分轨。
- NCT 来源身份、不可变登记版本、精确字段路径、NCT—PMID 未分类边、PubMed 主要/事后/综述/方案角色、方案字段来源白名单、补充材料免下载、监管声明域和 FDA 指南生命周期均有机械断言。
- 当前没有用户界面或格式产物，不适用视觉、浏览器、PPT、PDF 验收。

## Delegated-Agent Output Review

首次报告 PASS、P0=0、P1=0、P2=3。Codex 在本任务内修复补充材料覆盖方案字段、指南替代环、同系列多个当前版本，并将缺引文 PMID 改为保留关系且显式标记未提供；同 session 第二轮复核 PASS、P0=0、P1=0、P2=0。报告有代码位置、实际命令和对抗探查支撑，无越权修改或外部时效性结论。

## Residual Risk

- 连接器当前提供请求规格、纯解析、版本与来源门控；三次重试、两条替代、双轮饱和、cutoff 和来源审计对象的真实编排仍须在 Task 2.5–2.7 与 Phase 2 端到端验收证明不可绕过。
- `ClassifiedPublication.role` 到 `EvidenceContribution.source_role` 的接线必须在 Task 2.7 以 `can_replace_primary_report` 门控；当前仅接受连接器边界，不提前接受下游接线。
