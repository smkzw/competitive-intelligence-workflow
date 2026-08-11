# Codex Review: ci_phase2_task25_china_sources

Date: 2026-08-12
Delegated-agent output: `runs/pi_ci_phase2_task25_china_sources.md`

## Verdict

PASS。Task 2.5 可接受；Task 2.6–2.7 与 Phase 2 真实编排未提前接受。

## Boundary Check

- 本轮独立验收通过 Hermes 兼容执行会话运行，Codex 保留最终接受权。
- 审查者全程只读，runner 只写报告与原始流。首轮和补充轮复用同一 OpenCode Go session `019ff18c-07bf-7000-a6f2-7599e684805c`。
- 北京夜间有效路由为 `opencode-go/deepseek-v4-flash:max`。模型目录健康检查 90 秒超时后按合同进行一次真实路线尝试并成功；无 fallback、无因延迟重发。

## Codex Verification

- Codex 与独立审查者分别运行 CN01–CN07 组合 7 项、全库 173 项、Ruff、strict mypy、包校验和差异检查，全部通过。
- Codex 另行真实构建 sdist 与 wheel，并检查 wheel 内确含 `china_registries.py`、`company.py`、`authoritative_wechat.py`，排除“包校验通过但新增连接器未入包”的假绿。
- CDE/NMPA 事件职责、CTR 页面版本与字段定位、原文不可变、页面未公示和技术失败分层、DXY 二次参考角色、企业/topline/会议成熟度、五个指定公众号四域限制以及 CDE 指南生命周期均有正反向机械断言。
- 首轮两项 P2 均转为反例测试并修复：NMPA 不得承载 CDE 专有事件；国内药品参考页必须绑定当前来源策略。原 session 复核 P0/P1/P2=0。
- 当前没有用户界面或格式产物，不适用视觉、浏览器、PPT、PDF 验收。

## Delegated-Agent Output Review

首轮报告 PASS、P0=0、P1=0、P2=2，缺陷均有代码位置和对抗探查；修复后同 session 报告 PASS、P0/P1/P2=0。审查者没有把连接器的离线合同冒充实时网页成功，也没有提前接受后续摄取、事实链或报告层。

## Residual Risk

- 真实中国网页的验证码、访问限制和页面结构变化仍需在后续真实路线编排中证明进入技术诊断而非“未公开”。
- `ChinaDrugReferenceVersion.create` 的未知内部枚举值当前以 KeyError 失败关闭；不面向用户，作为非阻断程序员层改进留待统一错误适配。
