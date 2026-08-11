# Codex Review: ci_phase2_task27_facts_claims

Date: 2026-08-12
Delegated-agent output: `runs/pi_ci_phase2_task27_facts_claims.md`

## Verdict

PASS。Task 2.7 可接受；Phase 2 真实来源 fixture、Phase 3 GateSpec 与报告层未提前接受。

## Boundary Check

- 本轮独立验收通过 Hermes 兼容执行会话运行，Codex 保留最终接受权。
- 审查者全程只读，runner 只写报告与原始流；三轮复用 OpenCode Go session `019ff1c2-a806-7000-847e-0deedae9f560`。
- 北京夜间有效路由为 `opencode-go/deepseek-v4-flash:max`；健康目录检查超时仅作诊断，真实路线成功，无 fallback。

## Codex Verification

- Codex 与独立审查者分别运行 ER01–ER04 组合 4 项、全库 182 项、Ruff、strict mypy、包校验和差异检查，全部通过。
- 原文/摘要/来源版本错配、次日身份漂移、重复规范化、冲突先到先得、零值/未报告混写、非接受事实进入声明、计算矛盾值和未标识 AI 综合判断均有机械断言。
- 首轮及补充轮累计 9 个 P2 均转为反例测试并修复；最终原 session 复核 P0/P1/P2=0。
- Codex 真实构建 sdist 与 wheel，并确认四个新增事实/声明模块进入 wheel。
- 本任务没有用户界面或格式产物，不适用视觉、浏览器、PPT、PDF 成品验收；合成事实测试不冒充真实临床来源质量。

## Delegated-Agent Output Review

首轮报告 PASS/P2=6，第二轮因 3 个残余 P2 正确判 FAIL，第三轮 PASS/P0=P1=P2=0；每轮都有实测攻击输入。审查者没有提前接受 GateSpec、报告层或真实来源抽取，缺陷范围和分级可信。

## Residual Risk

- Phase 2 退出门仍须运行来源原文到实体、片段、事实和声明的真实 fixture，不能用本任务合成测试替代。
- JSON schema 负责可机械表达的传输合同；跨对象事实接受状态与计算输入一致性仍由 Pydantic/capability 运行时强制。
